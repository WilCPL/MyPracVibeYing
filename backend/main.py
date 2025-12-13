import json
import logging
import os
import threading
import time
from datetime import date, datetime
from io import StringIO
from typing import Dict, List

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .datastore import store
from .schemas import (
    AssignmentCreate,
    CalendarView,
    NurseCreate,
    OptimizerRunCreate,
    ProjectCreate,
    ProjectVersionCreate,
    RuleCreate,
    ShiftCodeCreate,
    RuleScope,
    RuleSetBinding,
)

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("scheduler_app")

app = FastAPI(title="Nurse Scheduler", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url)
    return JSONResponse(
        status_code=500,
        content={
            "message": "系統發生未預期錯誤，請稍後再試或洽系統管理員。",
            "detail": str(exc),
        },
    )


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.post("/projects")
async def create_project(payload: ProjectCreate):
    project = store.create_project(payload)
    logger.info("create_project id=%s", project.id)
    return project


@app.get("/projects/{project_id}")
async def get_project(project_id: int):
    project = store.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project


@app.post("/projects/{project_id}/versions")
async def create_project_version(project_id: int, payload: ProjectVersionCreate):
    version = store.create_project_version(project_id, payload)
    if not version:
        raise HTTPException(status_code=404, detail="專案不存在")
    logger.info("project %s create version %s", project_id, version.version_no)
    return version


@app.get("/projects/{project_id}/versions")
async def list_project_versions(project_id: int):
    return store.list_project_versions(project_id)


@app.get("/nurses")
async def list_nurses():
    return store.list_nurses()


@app.post("/nurses")
async def create_nurse(payload: NurseCreate):
    nurse = store.create_nurse(payload)
    logger.info("create_nurse id=%s", nurse.id)
    return nurse


@app.put("/nurses/{nurse_id}")
async def update_nurse(nurse_id: int, payload: NurseCreate):
    nurse = store.update_nurse(nurse_id, payload)
    if not nurse:
        raise HTTPException(status_code=404, detail="護理師不存在")
    return nurse


@app.delete("/nurses/{nurse_id}")
async def delete_nurse(nurse_id: int):
    deleted = store.delete_nurse(nurse_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="護理師不存在")
    return {"message": "刪除成功"}


@app.get("/shift-codes")
async def list_shift_codes():
    return store.list_shift_codes()


@app.post("/shift-codes")
async def create_shift_code(payload: ShiftCodeCreate):
    shift = store.create_shift_code(payload)
    return shift


@app.put("/shift-codes/{shift_id}")
async def update_shift_code(shift_id: int, payload: ShiftCodeCreate):
    shift = store.update_shift_code(shift_id, payload)
    if not shift:
        raise HTTPException(status_code=404, detail="班別不存在")
    return shift


@app.delete("/shift-codes/{shift_id}")
async def delete_shift_code(shift_id: int):
    deleted = store.delete_shift_code(shift_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="班別不存在")
    return {"message": "刪除成功"}


@app.get("/rules")
async def list_rules():
    return store.list_rules()


@app.post("/rules")
async def create_rule(payload: RuleCreate):
    rule = store.create_rule(payload)
    return rule


@app.put("/rules/{rule_id}")
async def update_rule(rule_id: int, payload: RuleCreate):
    rule = store.update_rule(rule_id, payload)
    if not rule:
        raise HTTPException(status_code=404, detail="規則不存在")
    return rule


@app.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int):
    deleted = store.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="規則不存在")
    return {"message": "刪除成功"}


@app.get("/rules/effective")
async def effective_rules(department_id: str = None, project_id: int = None):
    effective = store.compute_effective_rules(department_id, project_id)
    snapshot = json.dumps([e.model_dump() for e in effective], ensure_ascii=False)
    hash_value = store._hash_snapshot(snapshot)
    return {"effective_rules": effective, "snapshot_hash": hash_value}


@app.post("/rule-bindings")
async def bind_rule_set(payload: RuleSetBinding):
    binding = store.bind_rule_set(payload)
    return binding


@app.get("/calendar")
async def get_calendar(project_version_id: int, view: str, date: date):
    assignments = store.list_assignments(project_version_id)
    return CalendarView(project_version_id=project_version_id, view=view, date=date, assignments=assignments)


@app.post("/assignments")
async def create_assignment(payload: AssignmentCreate):
    assignment, reason = store.create_assignment(payload)
    if not assignment:
        raise HTTPException(status_code=409, detail=reason)
    return assignment


@app.put("/assignments/{assignment_id}")
async def update_assignment(assignment_id: int, payload: AssignmentCreate):
    assignment, reason = store.update_assignment(assignment_id, payload)
    if reason == "not_found":
        raise HTTPException(status_code=404, detail="排班不存在")
    if not assignment:
        raise HTTPException(status_code=409, detail=reason)
    return assignment


@app.delete("/assignments/{assignment_id}")
async def delete_assignment(assignment_id: int):
    deleted = store.delete_assignment(assignment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="排班不存在")
    return {"message": "刪除成功"}


@app.post("/imports/nurses")
async def import_nurses(file: UploadFile = File(...)):
    content = await file.read()
    token, rows, errors = store.preview_nurse_import(content.decode("utf-8"))
    return {"token": token, "rows": rows, "errors": errors}


@app.post("/imports/nurses/confirm")
async def confirm_import(payload: Dict[str, List[Dict]]):
    try:
        rows = [NurseCreate(**row) for row in payload.get("rows", [])]
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to parse import rows")
        raise HTTPException(status_code=400, detail=f"匯入資料格式錯誤：{exc}")
    inserted = store.apply_import_preview(rows)
    return {"inserted": inserted}


@app.post("/optimizer-runs")
async def start_optimizer(payload: OptimizerRunCreate):
    run = store.create_optimizer_run(payload)
    logger.info("optimizer run created id=%s", run.id)
    threading.Thread(target=_simulate_optimizer, args=(run.id,), daemon=True).start()
    return run


def _simulate_optimizer(run_id: int) -> None:
    try:
        phases = ["finding_feasible", "improving", "finalizing"]
        for idx, phase in enumerate(phases, start=1):
            progress = int(idx / len(phases) * 100)
            store.advance_optimizer_run(run_id, progress, status=phase, log=f"phase={phase}")
            time.sleep(1)
        store.finalize_optimizer_run(run_id, version_id=None, status="succeeded")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Optimizer simulation error")
        store.advance_optimizer_run(run_id, progress=0, status="failed", log=str(exc))


@app.get("/optimizer-runs/{run_id}")
async def get_optimizer_run(run_id: int):
    run = store.optimizer_runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="任務不存在")
    return run


@app.get("/optimizer-runs/{run_id}/stream")
async def stream_optimizer(run_id: int):
    run = store.optimizer_runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="任務不存在")

    def event_stream():
        last_status = None
        while True:
            current = store.optimizer_runs.get(run_id)
            if not current:
                break
            payload = {
                "phase": current.status,
                "progress": current.progress,
                "best_score": 0,
                "hard_violations_count": 0,
                "soft_violations_topk": [],
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            if current.status in {"succeeded", "failed", "partial"}:
                break
            time.sleep(1)
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/optimizer-runs/{run_id}/cancel")
async def cancel_optimizer(run_id: int):
    run = store.optimizer_runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="任務不存在")
    store.finalize_optimizer_run(run_id, version_id=None, status="partial")
    return {"message": "已取消，已保留當前最佳解"}


if __name__ == "__main__":
    try:
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Server failed to start")
        raise SystemExit(1) from exc
