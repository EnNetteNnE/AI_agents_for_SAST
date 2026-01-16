import re
import logging

logger = logging.getLogger(__name__)

def extract_codeql_from_response(response: str) -> str:
    #logger.info(response)
    """
    Извлечь CodeQL код из ответа LLM
    Удаляет markdown блоки и форматирование
    """
    # Удалить markdown блоки ```ql ... ```
    pattern = r'```(?:ql|codeql)?\n(.*?)\n```'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        logger.info("OK Найден код в блоке markdown")
        return match.group(1).strip()
    
    # Если нет блока, попробовать найти просто import ...
    if "import" in response:
        start = response.find("import")
        if start != -1:
            logger.info("OK Найден код, начинающийся с инструкции import")
            return response[start:].strip()
    
    logger.warning("! Блок кода не найден, возвращается полный ответ")
    return response.strip()
