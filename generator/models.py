from pydantic import BaseModel, Field
from typing import Optional, Dict, List

class GenerateRequest(BaseModel):
    # Режим 1: генерация по CWE
    cwe_id: str = Field(..., example="CWE-787", description="CWE identifier")
    cwe_name: str = Field(..., example="Out-of-bounds Write", description="CWE name")
    context: Optional[str] = Field(None, description="Additional context for generation")

    class Config:
        json_schema_extra = {
            "example": {
                "cwe_id": "CWE-787",
                "cwe_name": "Out-of-bounds Write",
                "context": "C/C++ buffer overflow detection"
            }
        }


class RefineRequest(BaseModel):
    # Режим 2: рефайнмент существующего правила
    cwe_id: str = Field(..., example="CWE-787")
    cwe_name: str = Field(..., example="Out-of-bounds Write")
    current_rule: str = Field(..., description="Current CodeQL rule text")
    metrics: Dict[str, float] = Field(..., description="Current metrics: precision, recall, specificity")
    target_metrics: Dict[str, float] = Field(..., description="Target metrics to achieve")
    feedback: Optional[str] = Field(None, description="Additional refinement feedback")

    class Config:
        json_schema_extra = {
            "example": {
                "cwe_id": "CWE-787",
                "cwe_name": "Out-of-bounds Write",
                "current_rule": "import cpp\nfrom...",
                "metrics": {"precision": 0.55, "recall": 0.45, "specificity": 0.70},
                "target_metrics": {"precision": 0.75, "recall": 0.65, "specificity": 0.80},
                "feedback": "Too many false positives"
            }
        }


class RuleResponse(BaseModel):
    # Ответ с готовым правилом
    status: str = Field(..., example="success", description="success or failed")
    rule: Optional[str] = None
    attempts: int
    max_attempts: int
    errors: List[str] = []
    metadata: Dict = {}


class HealthResponse(BaseModel):
    # Проверка работоспособности
    status: str
    service: str
    version: str
    llm_provider: str
