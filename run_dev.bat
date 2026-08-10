@echo off
echo ========================================
echo    DEVELOPMENT MODE - SELENIUM SCRAPER
echo ========================================
echo.

REM Kiểm tra virtual environment
if not exist "venv" (
    echo [ERROR] Virtual environment chua duoc tao
    echo Vui long chay setup.bat truoc
    pause
    exit /b 1
)

REM Kích hoạt virtual environment
call venv\Scripts\activate.bat

REM Smoke test: 1 san pham, khong dung Mongo, hien Chrome, log DEBUG
echo [INFO] Dang chay smoke test (--limit 1 --no-db --no-headless)...
echo.
python -m src.main --limit 1 --no-db --no-headless --log-level DEBUG

pause
