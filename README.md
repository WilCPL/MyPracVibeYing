# 護理師排班系統（技術草稿版）

本專案提供最小可執行的後端 API 雛形，符合使用者提供的專業規格：涵蓋 Project/Version、分層規則、行事曆排班、匯入預覽、最佳化任務串流等。程式碼以 FastAPI 實作，內建 30 位測試護理師與預設班別，方便立即啟動與驗收。

> **重要**：目前為記憶體資料儲存與模擬最佳化，方便快速驗證 API 契約與流程。真實環境請接 RDBMS、排程器與 CP-SAT/ILP 求解器。

## 環境需求
- Python 3.10+
- pip 套件：`pip install -r requirements.txt`

## 啟動方式
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

啟動後可透過 `http://localhost:8000/docs` 查看 OpenAPI 互動文件。

## 功能摘要
- **Project/Version**：建立專案與版本，版本含 `snapshot_hash` 用來鎖定規則快照。
- **Master Data**：護理師、班別完整 CRUD；預載 30 位測試護理師與 6 個班別代碼。
- **Rules**：支援硬/軟/偏好、分層 scope 與覆寫鏈，提供 `/rules/effective` 輸出有效規則與 hash。
- **Calendar/Assignment**：依 version 列出排班，新增/修改/刪除皆執行硬性驗證（同日不可兩班）。
- **匯入預覽**：`/imports/nurses` 先預覽 CSV，`/imports/nurses/confirm` 才寫入。
- **最佳化串流**：`/optimizer-runs` 建立任務並以 SSE `/optimizer-runs/{id}/stream` 提供 phase/progress（目前為模擬）。

## 重要設計
- **分層規則**：依 scope 順序 GLOBAL→HOSPITAL→DEPARTMENT→TEAM→PERSON 合併，使用 `override_of_rule_id` 建立覆寫鏈並輸出 `snapshot_hash`。
- **硬性檢核**：手動排班會阻擋同日同人兩班，回應 409 與中文原因說明。
- **錯誤與日誌**：全域例外處理，使用 `logs/app.log` 保留技術細節，對 API 使用者回應友善訊息。
- **模擬提醒**：最佳化與資料存取目前為 in-memory 模擬，請在導入正式環境時更換實際排程引擎與持久層。

## 測試建議（對應規格）
- **規則覆寫**：新增 GLOBAL 及 DEPARTMENT 規則後呼叫 `/rules/effective`，確認覆寫鏈與 hash。
- **硬性阻擋**：同一天新增第二筆同人班別應得到 409 與原因。
- **SSE 串流**：呼叫 `/optimizer-runs` 後監聽 `/optimizer-runs/{id}/stream`，應收到 phase: finding_feasible → improving → finalizing → succeeded。
