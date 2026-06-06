from pydantic import BaseModel
from typing import List, Optional, Dict

class DialogueTurn(BaseModel):
    model: str
    user: str

class EvaluationRequest(BaseModel):
    scenario: str
    personality: str

class StepDetail(BaseModel):
    passed: bool
    evidence: str

class FunctionalValidation(BaseModel):
    passed_steps: List[str]
    failed_steps: List[str]
    step_details: Dict[str, StepDetail]
    overall_functional_score: float
    completion_rate: float

class EvaluationResult(BaseModel):
    id: str
    name: str
    scenario: str
    personality: str
    status: str
    overall_score: float
    readiness_score: float
    readiness_comment: str
    scores: Dict[str, float]
    strengths: List[str]
    weaknesses: List[Dict[str, int | str]]
    critical_incidents: List[Dict[str, int | str]]
    improvement_suggestions: List[str]
    dialogue_history: List[DialogueTurn]
    created_at: str
    # 新增功能验证字段
    functional_validation: Optional[FunctionalValidation] = None

class EvaluationListResponse(BaseModel):
    items: List[EvaluationResult]
    total: int

class ScenarioInfo(BaseModel):
    key: str
    name: str
    description: str

class PersonalityInfo(BaseModel):
    key: str
    name: str