import csv
import hashlib
import os
import threading
import time
from datetime import date, datetime
from io import StringIO
from typing import Dict, List, Optional, Tuple

from .schemas import (
    Assignment,
    AssignmentCreate,
    EffectiveRule,
    Nurse,
    NurseCreate,
    OptimizerRun,
    OptimizerRunCreate,
    Project,
    ProjectCreate,
    ProjectVersion,
    ProjectVersionCreate,
    Rule,
    RuleCreate,
    RuleScope,
    RuleSetBinding,
    RuleType,
    ShiftCode,
    ShiftCodeCreate,
)


class DataStore:
    def __init__(self) -> None:
        self.projects: Dict[int, Project] = {}
        self.project_versions: Dict[int, ProjectVersion] = {}
        self.assignments: Dict[int, Assignment] = {}
        self.nurses: Dict[int, Nurse] = {}
        self.shift_codes: Dict[int, ShiftCode] = {}
        self.rules: Dict[int, Rule] = {}
        self.rule_set_bindings: Dict[int, RuleSetBinding] = {}
        self.optimizer_runs: Dict[int, OptimizerRun] = {}

        self._locks = {
            "project": threading.Lock(),
            "project_version": threading.Lock(),
            "assignment": threading.Lock(),
            "nurse": threading.Lock(),
            "shift_code": threading.Lock(),
            "rule": threading.Lock(),
            "optimizer": threading.Lock(),
        }
        self._sequences = {
            "project": 1,
            "project_version": 1,
            "assignment": 1,
            "nurse": 1,
            "shift_code": 1,
            "rule": 1,
            "optimizer": 1,
        }
        self._seed_shift_codes()
        self._seed_nurses()

    def _seed_shift_codes(self) -> None:
        defaults = [
            ("D", "早班", "08:00", "16:00", True),
            ("E", "小夜", "16:00", "00:00", True),
            ("N", "大夜", "00:00", "08:00", True),
            ("O", "休假", "00:00", "00:00", False),
            ("A", "年假", "00:00", "00:00", False),
            ("S", "病假", "00:00", "00:00", False),
        ]
        for code, name, start, end, working in defaults:
            self.create_shift_code(
                ShiftCodeCreate(
                    code=code,
                    name=name,
                    start_time=start,
                    end_time=end,
                    is_working=working,
                )
            )

    def _seed_nurses(self) -> None:
        csv_content = """employee_no,name,department,grade,can_night,skill_tags
E1001,王小明,ICU,N3,true,"IV,Respiratory"
E1002,李小華,ICU,N2,true,"IV"
E1003,陳怡君,ICU,N4,true,"Charge,Respiratory"
E1004,林雅婷,ICU,N1,false,"Newcomer"
E1005,張家豪,ICU,N2,true,"IV"
E1006,黃欣怡,ICU,N3,true,"Respiratory"
E1007,吳承翰,ICU,N2,true,"IV"
E1008,許雅雯,ICU,N3,true,"Charge"
E1009,鄭凱文,ICU,N1,false,"Newcomer"
E1010,謝佩珊,ICU,N2,true,"IV"
E1011,周子涵,ICU,N3,true,"Respiratory"
E1012,曾品妤,ICU,N4,true,"Charge,IV"
E1013,賴俊廷,ICU,N2,true,"IV"
E1014,彭婉如,ICU,N3,true,"Respiratory"
E1015,蔡宗翰,ICU,N2,true,"IV"
E1016,洪郁婷,ICU,N1,false,"Newcomer"
E1017,邱筱晴,ICU,N2,true,"IV"
E1018,郭柏廷,ICU,N3,true,"Respiratory"
E1019,蘇怡安,ICU,N2,true,"IV"
E1020,葉書妤,ICU,N4,true,"Leader,Charge"
E1021,潘志豪,ICU,N2,true,"IV"
E1022,許佳蓉,ICU,N3,true,"Respiratory"
E1023,何柏宇,ICU,N2,true,"IV"
E1024,楊詩涵,ICU,N1,false,"Newcomer"
E1025,張雅雯,ICU,N3,true,"Charge"
E1026,陳冠宇,ICU,N2,true,"IV"
E1027,李佩珊,ICU,N3,true,"Respiratory"
E1028,林冠廷,ICU,N2,true,"IV"
E1029,黃筱柔,ICU,N3,true,"Respiratory"
E1030,鄭雅文,ICU,Leader,true,"Leader,Charge"
"""
        reader = csv.DictReader(StringIO(csv_content))
        for row in reader:
            skills = [s.strip() for s in row["skill_tags"].split(",") if s.strip()]
            self.create_nurse(
                NurseCreate(
                    employee_no=row["employee_no"],
                    name=row["name"],
                    department_id=row["department"],
                    grade_code=row["grade"],
                    can_night=row["can_night"].lower() == "true",
                    skill_tags=skills,
                )
            )

    def _next_id(self, key: str) -> int:
        self._sequences[key] += 1
        return self._sequences[key] - 1

    def _timestamp(self) -> datetime:
        return datetime.utcnow()

    def _hash_snapshot(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Project CRUD
    def create_project(self, payload: ProjectCreate) -> Project:
        with self._locks["project"]:
            project_id = self._next_id("project")
            now = self._timestamp()
            project = Project(
                id=project_id,
                name=payload.name,
                date_start=payload.date_start,
                date_end=payload.date_end,
                department_id=payload.department_id,
                status=payload.status,
                created_at=now,
                updated_at=now,
            )
            self.projects[project_id] = project
            return project

    def update_project(self, project_id: int, payload: ProjectCreate) -> Optional[Project]:
        with self._locks["project"]:
            project = self.projects.get(project_id)
            if not project:
                return None
            now = self._timestamp()
            updated = project.model_copy(update={
                "name": payload.name,
                "date_start": payload.date_start,
                "date_end": payload.date_end,
                "department_id": payload.department_id,
                "status": payload.status,
                "updated_at": now,
            })
            self.projects[project_id] = updated
            return updated

    def delete_project(self, project_id: int) -> bool:
        with self._locks["project"]:
            return self.projects.pop(project_id, None) is not None

    # Project Versions
    def create_project_version(self, project_id: int, payload: ProjectVersionCreate) -> Optional[ProjectVersion]:
        if project_id not in self.projects:
            return None
        with self._locks["project_version"]:
            version_no = len([v for v in self.project_versions.values() if v.project_id == project_id]) + 1
            pv_id = self._next_id("project_version")
            version = ProjectVersion(
                id=pv_id,
                project_id=project_id,
                version_no=version_no,
                source=payload.source,
                note=payload.note,
                snapshot_hash=payload.snapshot_hash,
            )
            self.project_versions[pv_id] = version
            return version

    def list_project_versions(self, project_id: int) -> List[ProjectVersion]:
        return [v for v in self.project_versions.values() if v.project_id == project_id]

    # Nurses
    def list_nurses(self) -> List[Nurse]:
        return list(self.nurses.values())

    def create_nurse(self, payload: NurseCreate) -> Nurse:
        with self._locks["nurse"]:
            nurse_id = self._next_id("nurse")
            nurse = Nurse(
                id=nurse_id,
                employee_no=payload.employee_no,
                name=payload.name,
                department_id=payload.department_id,
                grade_code=payload.grade_code,
                can_night=payload.can_night,
                skill_tags=payload.skill_tags,
            )
            self.nurses[nurse_id] = nurse
            return nurse

    def update_nurse(self, nurse_id: int, payload: NurseCreate) -> Optional[Nurse]:
        with self._locks["nurse"]:
            nurse = self.nurses.get(nurse_id)
            if not nurse:
                return None
            updated = nurse.model_copy(update=payload.model_dump())
            self.nurses[nurse_id] = updated
            return updated

    def delete_nurse(self, nurse_id: int) -> bool:
        with self._locks["nurse"]:
            return self.nurses.pop(nurse_id, None) is not None

    # Shift codes
    def list_shift_codes(self) -> List[ShiftCode]:
        return list(self.shift_codes.values())

    def create_shift_code(self, payload: ShiftCodeCreate) -> ShiftCode:
        with self._locks["shift_code"]:
            shift_id = self._next_id("shift_code")
            shift = ShiftCode(
                id=shift_id,
                code=payload.code,
                name=payload.name,
                start_time=payload.start_time,
                end_time=payload.end_time,
                is_working=payload.is_working,
            )
            self.shift_codes[shift_id] = shift
            return shift

    def update_shift_code(self, shift_id: int, payload: ShiftCodeCreate) -> Optional[ShiftCode]:
        with self._locks["shift_code"]:
            shift = self.shift_codes.get(shift_id)
            if not shift:
                return None
            updated = shift.model_copy(update=payload.model_dump())
            self.shift_codes[shift_id] = updated
            return updated

    def delete_shift_code(self, shift_id: int) -> bool:
        with self._locks["shift_code"]:
            return self.shift_codes.pop(shift_id, None) is not None

    # Rules
    def list_rules(self) -> List[Rule]:
        return list(self.rules.values())

    def create_rule(self, payload: RuleCreate) -> Rule:
        with self._locks["rule"]:
            rule_id = self._next_id("rule")
            rule = Rule(
                id=rule_id,
                type=payload.type,
                scope=payload.scope,
                scope_id=payload.scope_id,
                key=payload.key,
                params=payload.params,
                weight=payload.weight,
                enabled=payload.enabled,
                priority=payload.priority,
                override_of_rule_id=payload.override_of_rule_id,
                effective_start=payload.effective_start,
                effective_end=payload.effective_end,
            )
            self.rules[rule_id] = rule
            return rule

    def update_rule(self, rule_id: int, payload: RuleCreate) -> Optional[Rule]:
        with self._locks["rule"]:
            rule = self.rules.get(rule_id)
            if not rule:
                return None
            updated = rule.model_copy(update=payload.model_dump())
            self.rules[rule_id] = updated
            return updated

    def delete_rule(self, rule_id: int) -> bool:
        with self._locks["rule"]:
            return self.rules.pop(rule_id, None) is not None

    # Rule set bindings
    def bind_rule_set(self, binding: RuleSetBinding) -> RuleSetBinding:
        self.rule_set_bindings[binding.project_id] = binding
        return binding

    def get_binding(self, project_id: int) -> Optional[RuleSetBinding]:
        return self.rule_set_bindings.get(project_id)

    def compute_effective_rules(self, department_id: Optional[str], project_id: Optional[int]) -> List[EffectiveRule]:
        binding = self.get_binding(project_id) if project_id else None
        include_scopes = binding.include_scopes if binding else [s for s in RuleScope]
        scoped_rules = [r for r in self.rules.values() if r.scope in include_scopes and r.enabled]
        scoped_rules.sort(key=lambda r: (self._scope_order(r.scope), r.priority, r.id))
        effective: Dict[str, EffectiveRule] = {}
        for rule in scoped_rules:
            key = rule.key
            override_chain: List[int] = []
            if key in effective and rule.override_of_rule_id:
                override_chain = effective[key].override_chain + [effective[key].source_rule_id]
            effective[key] = EffectiveRule(
                key=key,
                scope=rule.scope,
                value=rule.params if rule.type == RuleType.PREFERENCE else rule.params,
                source_rule_id=rule.id,
                override_chain=override_chain,
            )
        return list(effective.values())

    def _scope_order(self, scope: RuleScope) -> int:
        order = {
            RuleScope.GLOBAL: 0,
            RuleScope.HOSPITAL: 1,
            RuleScope.DEPARTMENT: 2,
            RuleScope.TEAM: 3,
            RuleScope.PERSON: 4,
        }
        return order.get(scope, 5)

    # Assignments
    def list_assignments(self, project_version_id: int) -> List[Assignment]:
        return [a for a in self.assignments.values() if a.project_version_id == project_version_id]

    def _validate_hard_constraints(self, payload: AssignmentCreate) -> Tuple[bool, str]:
        for assignment in self.list_assignments(payload.project_version_id):
            if assignment.nurse_id == payload.nurse_id and assignment.date == payload.date:
                return False, "同一天同一人不可排兩班"
        return True, ""

    def create_assignment(self, payload: AssignmentCreate) -> Tuple[Optional[Assignment], Optional[str]]:
        ok, reason = self._validate_hard_constraints(payload)
        if not ok:
            return None, reason
        with self._locks["assignment"]:
            assign_id = self._next_id("assignment")
            assignment = Assignment(
                id=assign_id,
                project_version_id=payload.project_version_id,
                nurse_id=payload.nurse_id,
                date=payload.date,
                shift_code=payload.shift_code,
                created_by=payload.created_by,
                created_at=self._timestamp(),
            )
            self.assignments[assign_id] = assignment
            return assignment, None

    def update_assignment(self, assignment_id: int, payload: AssignmentCreate) -> Tuple[Optional[Assignment], Optional[str]]:
        ok, reason = self._validate_hard_constraints(payload)
        if not ok:
            return None, reason
        with self._locks["assignment"]:
            assignment = self.assignments.get(assignment_id)
            if not assignment:
                return None, "not_found"
            updated = assignment.model_copy(
                update={
                    "project_version_id": payload.project_version_id,
                    "nurse_id": payload.nurse_id,
                    "date": payload.date,
                    "shift_code": payload.shift_code,
                    "created_by": payload.created_by,
                }
            )
            self.assignments[assignment_id] = updated
            return updated, None

    def delete_assignment(self, assignment_id: int) -> bool:
        with self._locks["assignment"]:
            return self.assignments.pop(assignment_id, None) is not None

    # Imports
    def preview_nurse_import(self, content: str) -> Tuple[str, List[NurseCreate], List[str]]:
        reader = csv.DictReader(StringIO(content))
        rows: List[NurseCreate] = []
        errors: List[str] = []
        for idx, row in enumerate(reader, start=2):
            try:
                if not row.get("employee_no") or not row.get("name"):
                    raise ValueError("employee_no 與 name 必填")
                payload = NurseCreate(
                    employee_no=row["employee_no"],
                    name=row["name"],
                    department_id=row.get("department", "ICU"),
                    grade_code=row.get("grade", "N1"),
                    can_night=row.get("can_night", "true").lower() == "true",
                    skill_tags=[s.strip() for s in row.get("skill_tags", "").split(",") if s.strip()],
                )
                rows.append(payload)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"第 {idx} 行錯誤：{exc}")
        token_source = f"{datetime.utcnow().isoformat()}-{len(rows)}-{len(errors)}"
        token = self._hash_snapshot(token_source)
        return token, rows, errors

    def apply_import_preview(self, rows: List[NurseCreate]) -> List[Nurse]:
        inserted = []
        for row in rows:
            inserted.append(self.create_nurse(row))
        return inserted

    # Optimizer
    def create_optimizer_run(self, payload: OptimizerRunCreate) -> OptimizerRun:
        with self._locks["optimizer"]:
            run_id = self._next_id("optimizer")
            run = OptimizerRun(
                id=run_id,
                project_id=payload.project_id,
                requested_version_no=payload.requested_version_no,
                params=payload.params,
                status="queued",
                progress=0,
                result_version_id=None,
                logs=[],
            )
            self.optimizer_runs[run_id] = run
            return run

    def advance_optimizer_run(self, run_id: int, progress: int, status: Optional[str] = None, log: Optional[str] = None) -> Optional[OptimizerRun]:
        run = self.optimizer_runs.get(run_id)
        if not run:
            return None
        updates = {"progress": progress}
        if status:
            updates["status"] = status
        if log:
            run.logs.append(log)
        updated = run.model_copy(update=updates)
        self.optimizer_runs[run_id] = updated
        return updated

    def finalize_optimizer_run(self, run_id: int, version_id: Optional[int], status: str) -> Optional[OptimizerRun]:
        run = self.optimizer_runs.get(run_id)
        if not run:
            return None
        updated = run.model_copy(update={"status": status, "progress": 100, "result_version_id": version_id})
        self.optimizer_runs[run_id] = updated
        return updated

    def list_optimizer_runs(self) -> List[OptimizerRun]:
        return list(self.optimizer_runs.values())


store = DataStore()
