from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RuleType(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"
    PREFERENCE = "PREFERENCE"


class RuleScope(str, Enum):
    GLOBAL = "GLOBAL"
    HOSPITAL = "HOSPITAL"
    DEPARTMENT = "DEPARTMENT"
    TEAM = "TEAM"
    PERSON = "PERSON"


class Project(BaseModel):
    id: int
    name: str
    date_start: date
    date_end: date
    department_id: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1)
    date_start: date
    date_end: date
    department_id: Optional[str] = None
    status: str = "draft"


class ProjectVersion(BaseModel):
    id: int
    project_id: int
    version_no: int
    source: str
    note: Optional[str] = None
    snapshot_hash: str


class ProjectVersionCreate(BaseModel):
    source: str = Field(..., examples=["manual", "optimizer"])
    note: Optional[str] = None
    snapshot_hash: str


class Nurse(BaseModel):
    id: int
    employee_no: str
    name: str
    department_id: str
    grade_code: str
    can_night: bool
    skill_tags: List[str] = []


class NurseCreate(BaseModel):
    employee_no: str
    name: str
    department_id: str
    grade_code: str
    can_night: bool
    skill_tags: List[str] = []


class ShiftCode(BaseModel):
    id: int
    code: str
    name: str
    start_time: str
    end_time: str
    is_working: bool


class ShiftCodeCreate(BaseModel):
    code: str
    name: str
    start_time: str
    end_time: str
    is_working: bool


class Assignment(BaseModel):
    id: int
    project_version_id: int
    nurse_id: int
    date: date
    shift_code: str
    created_by: str
    created_at: datetime


class AssignmentCreate(BaseModel):
    project_version_id: int
    nurse_id: int
    date: date
    shift_code: str
    created_by: str = "system"


class Rule(BaseModel):
    id: int
    type: RuleType
    scope: RuleScope
    scope_id: Optional[str]
    key: str
    params: dict
    weight: Optional[int]
    enabled: bool
    priority: int
    override_of_rule_id: Optional[int]
    effective_start: Optional[date]
    effective_end: Optional[date]


class RuleCreate(BaseModel):
    type: RuleType
    scope: RuleScope
    scope_id: Optional[str] = None
    key: str
    params: dict
    weight: Optional[int] = None
    enabled: bool = True
    priority: int = 0
    override_of_rule_id: Optional[int] = None
    effective_start: Optional[date] = None
    effective_end: Optional[date] = None


class RuleSetBinding(BaseModel):
    project_id: int
    include_scopes: List[RuleScope]


class OptimizerRun(BaseModel):
    id: int
    project_id: int
    requested_version_no: int
    params: dict
    status: str
    progress: int
    result_version_id: Optional[int]
    logs: List[str]


class OptimizerRunCreate(BaseModel):
    project_id: int
    requested_version_no: int
    params: dict = {}


class EffectiveRule(BaseModel):
    key: str
    scope: RuleScope
    value: dict
    source_rule_id: int
    override_chain: List[int] = []


class NurseImportPreview(BaseModel):
    token: str
    rows: List[NurseCreate]
    errors: List[str]


class CalendarView(BaseModel):
    project_version_id: int
    view: str
    date: date
    assignments: List[Assignment]

