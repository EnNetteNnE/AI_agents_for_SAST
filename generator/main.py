#!/usr/bin/env python3

# CodeQL Rule Generator Microservice
# Два режима работы: генерация и рефайнмент правил


import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import uvicorn

from models import GenerateRequest, RefineRequest, RuleResponse, HealthResponse
from llm_service import MistralLLMService
from codeql_validator import CodeQLValidator
from prompts import get_generation_prompt, get_refinement_prompt
from logger import GenerationLogger
from utils import extract_codeql_from_response

# переменные окружения
load_dotenv()

# логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI
app = FastAPI(
    title="CodeQL Rule Generator",
    description="Microservice for generating and refining CodeQL rules using Mistral LLM",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Инициализация компонентов
try:
    GenerationLogger.initialize()
    llm_service = MistralLLMService()
    codeql_validator = CodeQLValidator(
    codeql_path="codeql",
    pack_dir="codeql_pack",
    db_path="cpp_test_db",  # БД для тестирования синтаксиса
)

    logger.info("OK Все компоненты успешно инициализированы")
except Exception as e:
    logger.error(f"ERROR Ошибка инициализации: {e}")
    raise

MAX_ATTEMPTS = 3
LLM_PROVIDER = "mistral"


async def generate_rule_iterative(
    mode: str,
    cwe_id: str,
    cwe_name: str,
    prompt_func,
    prompt_kwargs: dict
) -> tuple[bool, str, int, list]:
    """
    Итеративно генерирует правило с проверкой синтаксиса
    При ошибке компиляции, отправляет ошибку обратно в LLM для исправления
    
    Returns:
        (success, rule, attempts_count, errors_list)
    """
    rule = None
    errors = []
    llm_response = ""
    
    for attempt in range(1, MAX_ATTEMPTS + 1):
        logger.info(f"попытка {attempt}/{MAX_ATTEMPTS} для {cwe_id}")
        
        try:
            # Генерация через API
            prompt = prompt_func(**prompt_kwargs)
            llm_response, success = llm_service.call_mistral_api(prompt)
            
            if not success:
                error_msg = f"LLM API error: {llm_response}"
                logger.error(f"ERROR {error_msg}")
                errors.append(error_msg)
                
                # Лог неудачной попытки
                GenerationLogger.log_attempt(
                    mode=mode,
                    cwe_id=cwe_id,
                    cwe_name=cwe_name,
                    attempt=attempt,
                    llm_response="",
                    extracted_code="",
                    syntax_valid=False,
                    syntax_error=error_msg,
                    status="failed",
                    llm_provider=LLM_PROVIDER
                )
                continue
            
            # CodeQL код из ответа
            rule = extract_codeql_from_response(llm_response)
            logger.info(f"Извлеченный код ({len(rule)} символов)")
            
            # проверка синтаксиса
            is_valid, syntax_error = codeql_validator.validate_syntax(rule)
            
            # лог попытки
            GenerationLogger.log_attempt(
                mode=mode,
                cwe_id=cwe_id,
                cwe_name=cwe_name,
                attempt=attempt,
                llm_response=llm_response,
                extracted_code=rule,
                syntax_valid=is_valid,
                syntax_error=syntax_error,
                status="success" if is_valid else "failed",
                llm_provider=LLM_PROVIDER
            )
            
            if is_valid:
                logger.info(f"OK Действительное правило, сгенерированное при попытке {attempt}")
                return True, rule, attempt, []
            else:
                logger.warning(f"ERROR Синтаксическая ошибка при попытке {attempt}: {syntax_error}")
                errors.append(syntax_error)
                
                # ошибку компиляции в контекст для следующей попытки
                error_snippet = codeql_validator.extract_error_snippet(syntax_error)
                
                # обновление промпта с информацией об ошибке
                if mode == "refinement":
                    prompt_kwargs = {
                        **prompt_kwargs,
                        'feedback': f"Syntax error: {syntax_error_snippet}"
                    }
        
        except Exception as e:
            error_msg = f"Generation error: {str(e)}"
            logger.error(f"ERROR {error_msg}")
            errors.append(error_msg)
            
            GenerationLogger.log_attempt(
                mode=mode,
                cwe_id=cwe_id,
                cwe_name=cwe_name,
                attempt=attempt,
                llm_response="",
                extracted_code="",
                syntax_valid=False,
                syntax_error=error_msg,
                status="failed",
                llm_provider=LLM_PROVIDER
            )
    
    logger.error(f"ERROR Не удалось сгенерировать действительное правило после {MAX_ATTEMPTS} попыток")
    return False, None, MAX_ATTEMPTS, errors


@app.post("/generate", response_model=RuleResponse, tags=["Generation"])
async def generate_endpoint(request: GenerateRequest) -> RuleResponse:
    # Режим 1: Генерирует новое CodeQL правило на основе CWE

    logger.info(f"Запрос на генерацию: {request.cwe_id} - {request.cwe_name}")
    
    try:
        success, rule, attempts, errors = await generate_rule_iterative(
            mode="generation",
            cwe_id=request.cwe_id,
            cwe_name=request.cwe_name,
            prompt_func=get_generation_prompt,
            prompt_kwargs={
                "cwe_id": request.cwe_id,
                "cwe_name": request.cwe_name,
                "context": request.context or ""
            }
        )
        
        if success:
            return RuleResponse(
                status="success",
                rule=rule,
                attempts=attempts,
                max_attempts=MAX_ATTEMPTS,
                errors=[],
                metadata={
                    "cwe_id": request.cwe_id,
                    "cwe_name": request.cwe_name,
                    "mode": "generation",
                    "llm_provider": LLM_PROVIDER
                }
            )
        else:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": f"Failed to generate valid rule after {MAX_ATTEMPTS} attempts",
                    "errors": errors,
                    "cwe_id": request.cwe_id
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ERROR Непредвиденная ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/refine", response_model=RuleResponse, tags=["Refinement"])
async def refine_endpoint(request: RefineRequest) -> RuleResponse:
    
    # Режим 2: Рефайнит существующее CodeQL правило на основе метрик

    logger.info(f"Рефайнинг запроса: {request.cwe_id} - {request.cwe_name}")
    logger.info(
        f"   Текущие метрики: P={request.metrics.get('precision', 0):.1%}, "
        f"R={request.metrics.get('recall', 0):.1%}"
    )
    
    try:
        success, rule, attempts, errors = await generate_rule_iterative(
            mode="refinement",
            cwe_id=request.cwe_id,
            cwe_name=request.cwe_name,
            prompt_func=get_refinement_prompt,
            prompt_kwargs={
                "cwe_id": request.cwe_id,
                "cwe_name": request.cwe_name,
                "current_rule": request.current_rule,
                "metrics": request.metrics,
                "target_metrics": request.target_metrics,
                "feedback": request.feedback or ""
            }
        )
        
        if success:
            return RuleResponse(
                status="success",
                rule=rule,
                attempts=attempts,
                max_attempts=MAX_ATTEMPTS,
                errors=[],
                metadata={
                    "cwe_id": request.cwe_id,
                    "cwe_name": request.cwe_name,
                    "mode": "refinement",
                    "llm_provider": LLM_PROVIDER,
                    "previous_metrics": request.metrics,
                    "target_metrics": request.target_metrics
                }
            )
        else:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": f"Failed to refine rule after {MAX_ATTEMPTS} attempts",
                    "errors": errors,
                    "cwe_id": request.cwe_id
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ERROR Непредвиденная ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    # Проверка сервиса
    return HealthResponse(
        status="healthy",
        service="CodeQL Rule Generator",
        version="1.0.0",
        llm_provider=LLM_PROVIDER
    )


@app.get("/logs", tags=["Logs"])
async def get_logs(limit: int = 50):
    # Получить последние N логов в формате CSV
    logs = GenerationLogger.get_recent_logs(limit)
    return {
        "limit": limit,
        "content": logs,
        "log_file": str(GenerationLogger.LOG_FILE)
    }


@app.get("/", response_class=HTMLResponse, tags=["Documentation"])
async def root():
    """Интерактивная документация API"""
    return """
    <!DOCTYPE html>
    """


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"Запуск генератора CodeQL на {host}:{port}")
    uvicorn.run(app, host=host, port=port)
