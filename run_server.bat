@echo off
chcp 65001 >nul
cd /d "%~dp0"

set SHARE_MODE=%1
if "%SHARE_MODE%"=="" set SHARE_MODE=public

REM venv 확인
if not exist "venv\Scripts\python.exe" (
    echo venv가 없습니다. 먼저 아래를 실행하세요:
    echo   python -m venv venv
    echo   venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

REM zrok 경로 탐색
set ZROK_CMD=
if exist "zrok.exe" (
    set ZROK_CMD=zrok.exe
) else (
    where zrok >nul 2>&1
    if %ERRORLEVEL%==0 set ZROK_CMD=zrok
)

if "%ZROK_CMD%"=="" (
    echo zrok을 찾을 수 없습니다. PATH에 추가하거나 zrok.exe를 프로젝트 폴더에 넣어주세요.
    pause
    exit /b 1
)

REM zrok 활성화
%ZROK_CMD% status >nul 2>&1
if %ERRORLEVEL% neq 0 (
    if "%ZROK_TOKEN%"=="" (
        echo ZROK_TOKEN 환경 변수가 없습니다.
        echo   set ZROK_TOKEN=your_token_here
        pause
        exit /b 1
    )
    %ZROK_CMD% enable %ZROK_TOKEN%
    if %ERRORLEVEL% neq 0 (
        echo zrok 활성화 실패
        pause
        exit /b 1
    )
)

REM 서버 실행
start "FastAPI Server" /min venv\Scripts\python.exe app.py
timeout /t 3 /nobreak >nul
echo 서버 시작: http://localhost:8000

REM zrok 공유
if "%SHARE_MODE%"=="public" (
    %ZROK_CMD% share public http://localhost:8000
) else (
    %ZROK_CMD% share private http://localhost:8000
)