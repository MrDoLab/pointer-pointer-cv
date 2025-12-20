@echo off
chcp 65001 >nul
REM ========================================
REM 서버 실행 및 zrok 공유 자동화 스크립트
REM ========================================
REM 이 스크립트는 다음을 자동으로 수행합니다:
REM 1. zrok 활성화 확인 및 활성화
REM 2. 로컬 서버 실행
REM 3. zrok으로 서버 공유

cd /d "%~dp0"

REM 공유 모드 확인 (기본값: public)
set SHARE_MODE=%1
if "%SHARE_MODE%"=="" set SHARE_MODE=public

echo.
echo ========================================
echo 서버 실행 및 zrok 공유 시작
echo ========================================
echo.
echo 공유 모드: %SHARE_MODE%
echo.

REM venv 확인
if not exist "venv\Scripts\python.exe" (
    echo [오류] venv가 생성되지 않았습니다.
    echo.
    echo 먼저 venv를 생성하세요:
    echo   python -m venv venv
    echo   venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM zrok 경로 찾기
set ZROK_CMD=

if exist "zrok_1.1.10_windows_amd64\zrok.exe" (
    set ZROK_CMD=zrok_1.1.10_windows_amd64\zrok.exe
) else if exist "zrok.exe" (
    set ZROK_CMD=zrok.exe
) else (
    where zrok >nul 2>&1
    if %ERRORLEVEL%==0 set ZROK_CMD=zrok
)

if "%ZROK_CMD%"=="" (
    echo [오류] zrok을 찾을 수 없습니다.
    echo.
    echo zrok이 필요합니다. zrok_1.1.10_windows_amd64 폴더를 확인하세요.
    echo.
    pause
    exit /b 1
)

REM 1. zrok 활성화 확인 및 활성화
echo [1/3] zrok 활성화 확인 중...
%ZROK_CMD% status >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [활성화] zrok 활성화 중...
    
    REM 환경 변수에서 zrok 토큰 읽기
    if "%ZROK_TOKEN%"=="" (
        echo [오류] ZROK_TOKEN 환경 변수가 설정되지 않았습니다.
        echo.
        echo 환경 변수 설정 방법:
        echo   1. 시스템 환경 변수 설정:
        echo      제어판 -^> 시스템 -^> 고급 시스템 설정 -^> 환경 변수
        echo      새로 만들기: 변수 이름=ZROK_TOKEN, 값=qXd1AdBG6VWs
        echo.
        echo   2. 또는 이 배치 파일 실행 전에:
        echo      set ZROK_TOKEN=qXd1AdBG6VWs
        echo      run_server.bat
        echo.
        pause
        exit /b 1
    )
    
    %ZROK_CMD% enable %ZROK_TOKEN%
    if %ERRORLEVEL% neq 0 (
        echo [오류] zrok 활성화 실패
        pause
        exit /b 1
    )
    echo [완료] 활성화 완료
) else (
    echo [확인] 이미 활성화되어 있습니다.
)
echo.

REM 2. 서버 실행 (백그라운드)
echo [2/3] 서버 실행 중...
echo.
echo 서버 주소: http://localhost:8000
echo.

start "FastAPI Server" /min venv\Scripts\python.exe app.py

REM 서버 시작 대기
echo 서버 시작 대기 중...
timeout /t 3 /nobreak >nul

REM 서버 확인
curl -s http://localhost:8000/api/health >nul 2>&1
if %ERRORLEVEL% neq 0 (
    curl -s http://localhost:8000/ >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [경고] 서버가 시작되지 않았습니다. 잠시 후 다시 시도하세요.
        timeout /t 2 /nobreak >nul
    )
)
echo [완료] 서버 실행 중
echo.

REM 3. zrok 공유
echo [3/3] zrok으로 서버 공유 중...
echo.
echo ========================================
echo 공유 URL이 생성되면 아래에 표시됩니다.
echo ========================================
echo.

if "%SHARE_MODE%"=="public" (
    %ZROK_CMD% share public http://localhost:8000
) else (
    %ZROK_CMD% share private http://localhost:8000
)

if %ERRORLEVEL%==0 (
    echo.
    echo ========================================
    echo 공유 완료!
    echo ========================================
    echo.
    echo 위에 표시된 URL을 다른 사람에게 공유하세요.
    echo 공유를 중지하려면 Ctrl+C를 누르세요.
) else (
    echo.
    echo [오류] 공유 실패
    pause
    exit /b 1
)
