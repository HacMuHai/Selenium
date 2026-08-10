@echo off
echo ========================================
echo    SETUP PROJECT - SELENIUM SCRAPER
echo ========================================
echo.

REM Kiểm tra Python đã cài chưa
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python chua duoc cai dat hoac chua duoc them vao PATH
    echo Vui long cai dat Python tu https://www.python.org/downloads/
    echo Va dam bao tich chon "Add Python to PATH"
    pause
    exit /b 1
)

echo [OK] Python da duoc cai dat
python --version

REM Kiểm tra pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip chua duoc cai dat
    pause
    exit /b 1
)

echo [OK] pip da san sang
echo.

REM Tạo virtual environment nếu chưa có
if not exist "venv" (
    echo [INFO] Dang tao virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Khong the tao virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment da duoc tao
) else (
    echo [INFO] Virtual environment da ton tai
)

echo.
echo [INFO] Dang kich hoat virtual environment...
call venv\Scripts\activate.bat

echo.
echo [INFO] Dang cap nhat pip...
python -m pip install --upgrade pip

echo.
echo [INFO] Dang cai dat dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo [ERROR] Co loi khi cai dat dependencies
    pause
    exit /b 1
)

echo.
echo ========================================
echo    SETUP HOAN TAT!
echo ========================================
echo.
echo BUOC TIEP THEO: sao chep .env.example thanh .env roi dien MONGO_URI
echo   copy .env.example .env
echo.
echo De chay du an (LUON chay tu thu muc goc cua repo):
echo   1. python -m src.main --help       - Xem tat ca flag
echo   2. python -m src.main              - Chay crawl
echo   3. uvicorn src.app:app --reload    - FastAPI server
echo   4. python -m pytest -q             - Chay test
echo.
echo Luu y: Moi lan mo terminal moi, can kich hoat venv:
echo   venv\Scripts\activate
echo.
pause
