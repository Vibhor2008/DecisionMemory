from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = ""
    assignee: str
    due_date: Optional[str] = None
    priority: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    status: str = "PENDING"   # PENDING, IN_PROGRESS, COMPLETED, BLOCKED

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class TaskResponse(TaskBase):
    id: int
    decision_id: int
    completed_at: Optional[str] = None
    notes: Optional[str] = ""
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class DecisionBase(BaseModel):
    title: str
    department: str = "General"
    category: str = "Strategy"
    problem_context: str
    decision_text: str
    reasoning: str
    rejected_alternatives: List[Dict[str, str]] = []  # [{"alternative": "GCP", "reason_rejected": "Setup takes 3 weeks"}]
    owner_name: str
    owner_role: Optional[str] = "Decision Owner"
    participants: List[str] = []
    source_type: str = "direct"  # "whatsapp", "meeting", "email", "call", "direct"
    raw_source_text: Optional[str] = ""
    decision_date: Optional[str] = None
    deadline_date: Optional[str] = None
    budget_or_cost: Optional[str] = ""
    status: str = "ACTIVE"  # "DRAFT", "ACTIVE", "IMPLEMENTED", "SUPERSEDED", "REVOKED"
    supersedes_id: Optional[int] = None
    expected_outcome: Optional[str] = ""
    outcome_status: str = "PENDING_EVALUATION"  # "PENDING_EVALUATION", "SUCCESS", "PARTIAL_SUCCESS", "FAILED", "ABANDONED"
    outcome_notes: Optional[str] = ""
    lessons_learned: Optional[str] = ""
    tags: List[str] = []

class DecisionCreate(DecisionBase):
    tasks: Optional[List[TaskCreate]] = []

class DecisionUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = None
    problem_context: Optional[str] = None
    decision_text: Optional[str] = None
    reasoning: Optional[str] = None
    rejected_alternatives: Optional[List[Dict[str, str]]] = None
    owner_name: Optional[str] = None
    owner_role: Optional[str] = None
    participants: Optional[List[str]] = None
    deadline_date: Optional[str] = None
    budget_or_cost: Optional[str] = None
    status: Optional[str] = None
    supersedes_id: Optional[int] = None
    expected_outcome: Optional[str] = None
    outcome_status: Optional[str] = None
    outcome_notes: Optional[str] = None
    lessons_learned: Optional[str] = None
    tags: Optional[List[str]] = None

class OutcomeEvaluationCreate(BaseModel):
    outcome_status: str  # "SUCCESS", "PARTIAL_SUCCESS", "FAILED", "ABANDONED"
    outcome_notes: str
    lessons_learned: Optional[str] = ""
    evaluated_by: Optional[str] = "Management"

class DecisionResponse(DecisionBase):
    id: int
    decision_code: str
    superseded_by_id: Optional[int] = None
    outcome_evaluated_at: Optional[str] = None
    outcome_evaluated_by: Optional[str] = None
    created_at: str
    updated_at: str
    task_count: int = 0
    completed_task_count: int = 0
    health_score: int = 100

    class Config:
        from_attributes = True

class DecisionDetailResponse(DecisionResponse):
    tasks: List[TaskResponse] = []
    audit_logs: List[Dict[str, Any]] = []
    active_conflicts: List[Dict[str, Any]] = []

class ChatParseRequest(BaseModel):
    chat_text: str
    source_channel: Optional[str] = "WhatsApp Chat"
    source_type: Optional[str] = "whatsapp"  # "whatsapp", "meeting", "voice", "document"

class ExtractedDecision(BaseModel):
    title: str
    department: str
    category: str
    problem_context: str
    decision_text: str
    reasoning: str
    rejected_alternatives: List[Dict[str, str]]
    owner_name: str
    participants: List[str]
    deadline_date: Optional[str] = None
    budget_or_cost: Optional[str] = ""
    expected_outcome: Optional[str] = ""
    tags: List[str]
    tasks: List[TaskCreate]
    confidence_score: float = 0.85

class ChatParseResponse(BaseModel):
    extracted: ExtractedDecision
    warnings: List[str] = []
    raw_message_count: int = 0
    participants_detected: List[str] = []

class ConflictCheckRequest(BaseModel):
    title: str
    decision_text: str
    department: Optional[str] = None
    category: Optional[str] = None
    current_id: Optional[int] = None  # If editing existing

class ConflictItem(BaseModel):
    conflicting_decision_id: int
    conflicting_decision_code: str
    conflicting_title: str
    conflict_type: str  # "DIRECT_CONFLICT", "REPEATED_DUPLICATE", "POLICY_COLLISION", "VENDOR_OVERLAP"
    severity: str       # "HIGH", "MEDIUM", "LOW"
    similarity_score: float
    explanation: str
    suggested_action: str

class ConflictCheckResponse(BaseModel):
    has_conflicts: bool
    conflict_count: int
    conflicts: List[ConflictItem]

class AskMemoryRequest(BaseModel):
    query: str
    department_filter: Optional[str] = None

class AskMemoryResponse(BaseModel):
    query: str
    answer: str
    relevant_decisions: List[DecisionResponse]
    synthesized_insights: List[str]

class ResolutionRequest(BaseModel):
    conflict_id: int
    resolution_type: str  # "SUPERSEDE_OLD", "SUPERSEDE_NEW", "ACKNOWLEDGE_EXCEPTION", "DISMISS"
    notes: Optional[str] = ""

class DashboardStats(BaseModel):
    total_decisions: int
    active_decisions: int
    implemented_decisions: int
    superseded_decisions: int
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int
    unresolved_conflicts: int
    pending_outcomes: int
    success_rate_percent: float
    decisions_by_dept: Dict[str, int]
    decisions_by_status: Dict[str, int]
    recent_activity: List[Dict[str, Any]]
