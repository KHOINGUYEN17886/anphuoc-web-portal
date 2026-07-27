@echo off
REM ============================================================
REM  Keo nguoc du lieu Neon Cloud -> SQLite goc (MIRROR)
REM  Chay tu dong luc dang nhap Windows qua Task Scheduler,
REM  hoac bam tay khi can.
REM ============================================================
setlocal
cd /d "%~dp0"

REM Dung system Python 3.13 (co san psycopg2). Fallback ve 'python' tren PATH.
set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

REM Ghi log moi lan chay (append) de tien theo doi.
set "LOGDIR=%~dp0sync_logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOGFILE=%LOGDIR%\sync_from_neon.log"

echo. >> "%LOGFILE%"
echo ================= %DATE% %TIME% ================= >> "%LOGFILE%"
"%PYEXE%" "%~dp0sync_from_neon.py" >> "%LOGFILE%" 2>&1

endlocal
