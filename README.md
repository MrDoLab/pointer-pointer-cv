# Pointer Pointer Vision

> SKKU Computer Vision 수강 과목 최종 프로젝트 (2025-1)  
> [pointerpointer.com](https://pointerpointer.com)을 MediaPipe + FastAPI로 직접 구현

컴퓨터 비전을 활용한 인터랙티브 손가락 포인팅 시스템

## 프로젝트 소개

MediaPipe Hands를 사용하여 손 이미지에서 손가락 위치를 감지하고, 사용자의 마우스 커서 위치와 매칭시켜 해당 위치를 가리키는 손 이미지를 실시간으로 표시하는 웹 애플리케이션입니다.

원본 [pointerpointer.com](https://pointerpointer.com)의 개념을 컴퓨터 비전 기술로 구현한 버전입니다.

## 주요 기능

- ✅ 실시간 마우스 위치 추적 및 손 이미지 매칭
- ✅ MediaPipe 기반 정확한 손가락 감지
- ✅ 웹캠 세그먼테이션 및 이미지 합성
- ✅ 히트맵 시각화
- ✅ zrok을 통한 네트워크 공유

## 기술 스택

- **백엔드**: FastAPI
- **컴퓨터 비전**: MediaPipe Hands, MediaPipe Selfie Segmentation
- **이미지 처리**: OpenCV, NumPy
- **프론트엔드**: HTML, CSS, JavaScript

## 설치 방법

### 1. 가상환경 생성 및 패키지 설치

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 이미지 준비

`static/images/` 폴더에 손 사진을 넣어주세요.

- 권장: 20~30장 이상
- 형식: JPG, PNG, JPEG
- 해상도: 최소 640x480 이상
- 다양한 각도와 위치의 손가락 포인팅 사진

### 3. zrok 환경 변수 설정 (선택사항)

네트워크 공유 기능을 사용하려면:

```bash
# Windows 환경 변수 설정
set ZROK_TOKEN=your_token_here
```

또는 시스템 환경 변수로 설정:
- 제어판 → 시스템 → 고급 시스템 설정 → 환경 변수
- 변수 이름: `ZROK_TOKEN`
- 변수 값: zrok 토큰

## 실행 방법

### 로컬 실행

```bash
venv\Scripts\python.exe app.py
```

브라우저에서 `http://localhost:8000` 접속

### 네트워크 공유 (zrok)

```bash
run_server.bat
```

이 스크립트는 다음을 자동으로 수행합니다:
1. zrok 활성화 확인 및 활성화
2. 로컬 서버 실행
3. zrok으로 서버 공유

## 사용 방법

1. 웹페이지 접속 후 **"이미지 처리 시작"** 버튼 클릭
2. 모든 손 이미지에서 손가락 좌표가 추출됩니다
3. 마우스를 움직이면 해당 위치를 가리키는 손 이미지가 자동으로 표시됩니다
4. **"웹캠 켜기"** 버튼으로 웹캠 기능 사용 가능
5. **"📷 캡처"** 버튼으로 웹캠 이미지를 세그먼트하여 손 이미지에 합성

## 프로젝트 구조

```
pointer-pointer-cv/
├── app.py                    # FastAPI 백엔드
├── requirements.txt          # 패키지 의존성
├── run_server.bat            # 서버 실행 및 zrok 공유
├── static/
│   └── images/              # 손 이미지 저장 폴더 (사용자가 준비)
├── templates/
│   └── index.html           # 웹 프론트엔드
└── zrok_1.1.10_windows_amd64/
    └── zrok.exe             # zrok 실행 파일
```

## API 엔드포인트

- `POST /api/process-images` - 모든 이미지 처리 및 좌표 추출
- `GET /api/coords` - 저장된 좌표 데이터 조회
- `POST /api/find-match` - 마우스 위치와 가장 가까운 이미지 찾기
- `POST /api/save-segment` - 웹캠 이미지 세그먼트 처리
- `POST /api/composite` - 손 이미지에 사람 합성
- `GET /api/get-dataset-heatmap` - 데이터셋 히트맵 생성
- `GET /api/health` - 서버 상태 확인

## 문제 해결

### 손을 감지하지 못하는 경우
- 밝고 균일한 조명에서 촬영
- 단순한 배경 사용
- 손가락이 명확하게 보이도록 촬영

### 서버가 시작되지 않는 경우
- 포트 8000이 사용 중인지 확인
- 모든 라이브러리가 설치되었는지 확인: `pip list`

### zrok 연결 실패
- `ZROK_TOKEN` 환경 변수가 설정되었는지 확인
- zrok이 활성화되었는지 확인: `zrok_1.1.10_windows_amd64\zrok.exe status`

## 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.
