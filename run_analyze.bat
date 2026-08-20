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
    echo [INFO] Chua co model, dang train (khoang 30 giay)...
    REM KHONG ghi cung danh sach model: mac dinh cua lenh train la available_names(),
    REM them model moi vao registry la script nay tu co.
    python -m src.analyze train
)

echo.
echo [INFO] Mo trinh duyet: http://127.0.0.1:8000/analyze/report
echo [INFO] Nhan Ctrl+C de dung
echo.
start "" http://127.0.0.1:8000/analyze/report
python -m uvicorn src.app:app --port 8000

pause
