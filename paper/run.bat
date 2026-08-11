@echo off
REM Sinh toan bo hinh cho bai bao. Chay duoc tu bat ky thu muc nao:
REM     paper\run.bat        hoac      cd paper && run.bat
setlocal

REM `python -m paper.figures` can dung o thu muc CHA cua paper\ thi Python moi
REM thay `paper` la mot package. Tu chuyen vao do.
cd /d "%~dp0.."

set PY=python
if exist venv\Scripts\python.exe set PY=venv\Scripts\python.exe

%PY% -c "import matplotlib" >nul 2>&1
if errorlevel 1 (
  echo [LOI] Thieu thu vien. Chay truoc:
  echo        %PY% -m pip install -r paper\requirements.txt
  exit /b 1
)

%PY% -m paper.figures %*
