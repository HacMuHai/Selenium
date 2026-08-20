@echo off
echo ========================================
echo    CHAY DU AN - SELENIUM SCRAPER
echo ========================================
echo.

REM Kiểm tra virtual environment
if not exist "venv" (
    echo [ERROR] Virtual environment chua duoc tao
    echo Vui long chay setup.bat truoc
    pause
    exit /b 1
)

REM Kiểm tra file .env
if not exist ".env" (
    echo [ERROR] Chua co file .env
    echo Sao chep .env.example thanh .env roi dien MONGO_URI
    pause
    exit /b 1
)

REM Kích hoạt virtual environment
call venv\Scripts\activate.bat

REM Chạy script (chay tu repo root, KHONG phai python src\main.py)
echo [INFO] Dang chay du an...
echo.
python -m src.main --category tgdd-phu-kien

pause
