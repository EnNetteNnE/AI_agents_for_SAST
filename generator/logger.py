import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class GenerationLogger:
    # записывает все попытки генерации и уточнения в формат CSV
    
    LOG_DIR = Path("logs")
    LOG_FILE = LOG_DIR / "generation.csv"
    
    HEADERS = [
        "timestamp",
        "mode",
        "cwe_id",
        "cwe_name",
        "attempt",
        "llm_provider",
        "llm_response_length",
        "extracted_code_length",
        "syntax_valid",
        "syntax_error",
        "final_rule_preview",
        "status",
        "metrics",
        "notes"
    ]
    
    @classmethod
    def initialize(cls):
        # инициализировать файл журнала
        cls.LOG_DIR.mkdir(exist_ok=True)
        
        if not cls.LOG_FILE.exists():
            with open(cls.LOG_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=cls.HEADERS)
                writer.writeheader()
            logger.info(f"Файл для логов создан: {cls.LOG_FILE}")
    
    @classmethod
    def log_attempt(
        cls,
        mode: str,
        cwe_id: str,
        cwe_name: str,
        attempt: int,
        llm_response: str,
        extracted_code: str,
        syntax_valid: bool,
        syntax_error: Optional[str] = None,
        status: str = "pending",
        llm_provider: str = "mistral",
        metrics: Optional[Dict] = None,
        notes: str = ""
    ):

        # 200 символов
        code_preview = extracted_code[:200].replace('\n', ' ') if extracted_code else ""
        
        row = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "cwe_id": cwe_id,
            "cwe_name": cwe_name,
            "attempt": attempt,
            "llm_provider": llm_provider,
            "llm_response_length": len(llm_response),
            "extracted_code_length": len(extracted_code),
            "syntax_valid": "yes" if syntax_valid else "no",
            "syntax_error": (syntax_error or "").replace('\n', ' ')[:200],
            "final_rule_preview": code_preview,
            "status": status,
            "metrics": json.dumps(metrics or {}, ensure_ascii=False),
            "notes": notes[:200]
        }
        
        with open(cls.LOG_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=cls.HEADERS)
            writer.writerow(row)
        
        logger.info(f"Зарегестрировано: {mode} попытка {attempt} для {cwe_id}")
    
    @classmethod
    def get_recent_logs(cls, n: int = 50) -> str:
        """Get last N log entries as CSV string"""
        if not cls.LOG_FILE.exists():
            return "No logs yet"
        
        with open(cls.LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # последние N строк + хедер
        recent = lines[-n:] if len(lines) > n else lines
        
        return ''.join(recent)
