@echo off
echo ========================================
echo    PHAN TICH CAM XUC - TRANG THU NGHIEM
echo ========================================
echo.

if not exist "venv" (
    echo [ERROR] Chua co virtual environment. Chay setup.bat truoc.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

if not exist "models_store\metadata.json" (
    echo [INFO] Chua co model, dang train (khoang 15 giay)...
    python -m src.analyze train --models nb,svm,lstm
)

echo.
echo [INFO] Mo trinh duyet: http://127.0.0.1:8000/analyze/report
echo [INFO] Nhan Ctrl+C de dung
echo.
start "" http://127.0.0.1:8000/analyze/report
python -m uvicorn src.app:app --port 8000

pause
