@echo off
setlocal

REM Create virtual environment if missing
if not exist venv (
    py -3 -m venv venv
)

REM Activate venv and install dependencies
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Launch FastAPI app
uvicorn backend.main:app --host 0.0.0.0 --port 8000
