# Pointer Pointer Vision

SKKU Intelligent Vision 수업 프로젝트 (2025-1)

[pointerpointer.com](https://pointerpointer.com)을 보고 만든 프로젝트입니다. 원본은 각 픽셀 좌표마다 사진을 수동으로 태깅해서 Voronoi Grid로 매핑하는 방식인데, 여기서는 MediaPipe로 손가락 끝 좌표를 자동 추출해서 이미지만 추가하면 바로 동작하도록 만들었습니다. 웹캠으로 본인 사진이 손 이미지에 합성되는 기능도 추가했습니다.

## 동작 방식

1. `static/images/`에 손가락으로 가리키는는 사진들을 준비
2. 서버 시작 시 MediaPipe Hands로 각 이미지의 손가락 끝 좌표를 추출해서 캐싱
3. 마우스가 움직일 때마다 유클리드 거리 기반으로 가장 가까운 이미지를 찾아서 표시
4. 웹캠을 켜면 MediaPipe Selfie Segmentation으로 사람 영역을 추출해서 손 이미지에 합성

## 기술 스택

- FastAPI, MediaPipe Hands, MediaPipe Selfie Segmentation, OpenCV, NumPy

## 실행

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 로컬 실행
venv\Scripts\python.exe app.py

# zrok으로 외부 공유 (ZROK_TOKEN 환경 변수 필요)
run_server.bat
```

서버 시작 후 http://localhost:8000 접속
