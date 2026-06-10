"""
Pointer Pointer Vision - FastAPI Backend
컴퓨터 비전을 활용한 인터랙티브 손가락 포인팅 시스템
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import cv2
import mediapipe as mp
import json
import os
import numpy as np
from pathlib import Path
from typing import Dict, Optional
import uvicorn
import base64

app = FastAPI(title="Pointer Pointer Vision")

# CORS 설정 (프론트엔드와 통신)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 (이미지, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# MediaPipe 초기화
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=True,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# MediaPipe Selfie Segmentation 초기화 (사람 segmentation)
mp_selfie_segmentation = mp.solutions.selfie_segmentation
selfie_segmentation = mp_selfie_segmentation.SelfieSegmentation(
    model_selection=1  # 0: 일반 모델, 1: 고품질 모델
)

# 전역 변수: 처리된 이미지 좌표 데이터
image_coords: Dict[str, Dict] = {}
COORDS_FILE = "image_coords.json"

# 전역 변수: 세그먼트 이미지 (일시적 저장, 하나만 유지)
current_segment_image: Optional[str] = None  # base64 인코딩된 세그먼트 이미지


def load_image_coords():
    """저장된 좌표 데이터 로드"""
    global image_coords
    if os.path.exists(COORDS_FILE):
        with open(COORDS_FILE, 'r', encoding='utf-8') as f:
            image_coords = json.load(f)
    return image_coords


def save_image_coords():
    """좌표 데이터 저장"""
    with open(COORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(image_coords, f, indent=2, ensure_ascii=False)


def extract_finger_coordinates(image_path: str) -> Optional[Dict]:
    """
    MediaPipe를 사용하여 손 이미지에서 손가락 끝점 좌표 추출
    
    Args:
        image_path: 이미지 파일 경로
        
    Returns:
        {'x': int, 'y': int, 'confidence': float} 또는 None
    """
    try:
        # 이미지 로드
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        h, w = img.shape[:2]
        
        # RGB로 변환 (MediaPipe는 RGB 사용)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 손 감지
        results = hands.process(img_rgb)
        
        if results.multi_hand_landmarks:
            # 첫 번째 손의 랜드마크 사용
            hand_landmarks = results.multi_hand_landmarks[0]
            
            # 검지 손가락 끝점 (landmark 8)
            finger_tip = hand_landmarks.landmark[8]
            
            # 픽셀 좌표로 변환 (0~1 정규화 좌표 → 픽셀 좌표)
            x = int(finger_tip.x * w)
            y = int(finger_tip.y * h)
            
            # 신뢰도 (visibility 사용)
            confidence = finger_tip.visibility
            
            return {
                'x': x,
                'y': y,
                'confidence': float(confidence)
            }
        else:
            return None
            
    except Exception as e:
        print(f"에러 발생 ({image_path}): {e}")
        return None


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """메인 웹페이지"""
    html_path = Path("templates/index.html")
    if html_path.exists():
        with open(html_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>Pointer Pointer Vision</h1><p>index.html 파일을 찾을 수 없습니다.</p>")


@app.post("/api/process-images")
async def process_images():
    """
    모든 손 이미지를 처리하여 좌표 추출
    """
    global image_coords
    image_coords = {}
    
    images_folder = Path("static/images")
    if not images_folder.exists():
        raise HTTPException(status_code=404, detail="static/images 폴더를 찾을 수 없습니다.")
    
    # 이미지 파일 목록
    image_files = [
        f for f in os.listdir(images_folder)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
    ]
    
    if not image_files:
        raise HTTPException(status_code=404, detail="이미지 파일을 찾을 수 없습니다.")
    
    processed_count = 0
    failed_count = 0
    
    for img_file in image_files:
        img_path = images_folder / img_file
        coords = extract_finger_coordinates(str(img_path))
        
        if coords:
            image_coords[img_file] = coords
            processed_count += 1
        else:
            failed_count += 1
    
    # 좌표 데이터 저장
    save_image_coords()
    
    return {
        "status": "success",
        "processed": processed_count,
        "failed": failed_count,
        "total": len(image_files),
        "coords": image_coords
    }


@app.get("/api/coords")
async def get_coords():
    """저장된 좌표 데이터 반환"""
    load_image_coords()
    return {
        "status": "success",
        "count": len(image_coords),
        "coords": image_coords
    }


@app.post("/api/find-match")
async def find_match(x: float, y: float):
    """
    마우스 커서 위치와 가장 가까운 손가락 좌표를 가진 이미지 찾기
    
    Args:
        x: 마우스 X 좌표
        y: 마우스 Y 좌표
    """
    global image_coords
    
    # 좌표 데이터가 없으면 파일에서 로드 시도
    if not image_coords:
        load_image_coords()
    
    # 여전히 비어있으면 에러
    if not image_coords:
        raise HTTPException(status_code=404, detail="처리된 이미지가 없습니다. /api/process-images를 먼저 실행하세요.")
    
    best_match = None
    min_distance = float('inf')
    
    # 모든 이미지와의 거리 계산
    for img_file, coords in image_coords.items():
        img_x = coords['x']
        img_y = coords['y']
        
        # 유클리드 거리 계산
        distance = np.sqrt((x - img_x)**2 + (y - img_y)**2)
        
        if distance < min_distance:
            min_distance = distance
            best_match = {
                "image": img_file,
                "distance": float(distance),
                "coords": coords
            }
    
    return {
        "status": "success",
        "best_match": best_match
    }


def create_cursor_heatmap(cursor_x: float, cursor_y: float, width: int = 1920, height: int = 1080) -> Optional[str]:
    """
    마우스 커서 위치를 중심으로 주변 이미지들의 분포를 히트맵으로 시각화
    
    Args:
        cursor_x: 마우스 X 좌표
        cursor_y: 마우스 Y 좌표
        width: 히트맵 너비
        height: 히트맵 높이
        
    Returns:
        base64 인코딩된 히트맵 이미지 또는 None
    """
    if not image_coords:
        load_image_coords()
    
    if not image_coords:
        return None
    
    # 빈 히트맵 생성 (검은색 배경)
    heatmap = np.zeros((height, width), dtype=np.float32)
    
    # 각 이미지의 손가락 위치와 마우스 위치의 거리를 계산하여 히트맵 생성
    for img_file, coords in image_coords.items():
        img_x = coords['x']
        img_y = coords['y']
        confidence = coords.get('confidence', 0.8)
        
        # 마우스 위치와 이미지 손가락 위치의 거리 계산
        distance = np.sqrt((cursor_x - img_x)**2 + (cursor_y - img_y)**2)
        
        # 거리가 가까울수록 높은 값 (최대 거리: 화면 대각선 길이)
        max_distance = np.sqrt(width**2 + height**2)
        normalized_distance = 1.0 - (distance / max_distance)  # 0~1 범위, 가까울수록 1에 가까움
        
        # 신뢰도와 거리를 결합하여 가중치 계산
        weight = confidence * normalized_distance
        
        # 가우시안 분산 크기: 거리가 가까울수록 작은 분산 (집중된 영역)
        # 마우스 위치 주변에 더 집중
        sigma = 100 * (1.0 - normalized_distance * 0.7) + 20  # 20~100 범위
        
        # 가우시안 분포 생성 (이미지 손가락 위치를 중심으로)
        y_coords, x_coords = np.ogrid[:height, :width]
        gaussian = weight * np.exp(
            -((x_coords - img_x)**2 + (y_coords - img_y)**2) / (2 * sigma**2)
        )
        
        # 히트맵에 추가
        heatmap += gaussian
    
    # 정규화 (0~255 범위로)
    if heatmap.max() > 0:
        heatmap = (heatmap / heatmap.max() * 255).astype(np.uint8)
    else:
        heatmap = heatmap.astype(np.uint8)
    
    # 컬러맵 적용 (JET: 파란색→녹색→노란색→빨간색)
    heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    
    # 마우스 위치 표시 (큰 빨간색 십자가)
    if 0 <= cursor_x < width and 0 <= cursor_y < height:
        cv2.line(heatmap_colored, 
                (int(cursor_x) - 20, int(cursor_y)), 
                (int(cursor_x) + 20, int(cursor_y)), 
                (0, 0, 255), 3)  # 빨간색 가로선
        cv2.line(heatmap_colored, 
                (int(cursor_x), int(cursor_y) - 20), 
                (int(cursor_x), int(cursor_y) + 20), 
                (0, 0, 255), 3)  # 빨간색 세로선
        cv2.circle(heatmap_colored, (int(cursor_x), int(cursor_y)), 15, (0, 0, 255), 2)  # 빨간색 원
    
    # 각 이미지 손가락 위치 표시
    for img_file, coords in image_coords.items():
        img_x = coords['x']
        img_y = coords['y']
        confidence = coords.get('confidence', 0.8)
        
        if 0 <= img_x < width and 0 <= img_y < height:
            # 마우스와의 거리에 따라 색상 변경
            distance = np.sqrt((cursor_x - img_x)**2 + (cursor_y - img_y)**2)
            max_distance = np.sqrt(width**2 + height**2)
            normalized_distance = distance / max_distance
            
            # 가까울수록 밝은 색 (흰색), 멀수록 어두운 색 (회색)
            color_intensity = int(255 * (1.0 - normalized_distance))
            color = (color_intensity, color_intensity, color_intensity)
            
            radius = int(5 + confidence * 8)
            cv2.circle(heatmap_colored, (img_x, img_y), radius, color, -1)
            cv2.circle(heatmap_colored, (img_x, img_y), radius + 2, (255, 255, 255), 1)
    
    # base64로 인코딩
    _, buffer = cv2.imencode('.png', heatmap_colored)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return img_base64


def create_dataset_heatmap(
    width: int = 1920, 
    height: int = 1080,
    mouse_x: float = 0,
    mouse_y: float = 0,
    img_width: int = 0,
    img_height: int = 0,
    img_display_width: float = 0,
    img_display_height: float = 0,
    img_left: float = 0,
    img_top: float = 0
) -> Optional[str]:
    """
    이미지 좌표와 마우스 좌표를 고려하여 데이터셋 히트맵 생성
    
    Args:
        width: 화면 너비
        height: 화면 높이
        mouse_x: 마우스 X 좌표 (이미지 좌표계)
        mouse_y: 마우스 Y 좌표 (이미지 좌표계)
        img_width: 원본 이미지 너비
        img_height: 원본 이미지 높이
        img_display_width: 화면에 표시된 이미지 너비
        img_display_height: 화면에 표시된 이미지 높이
        img_left: 이미지 왼쪽 위치
        img_top: 이미지 위쪽 위치
    """
    if not image_coords:
        load_image_coords()
    
    if not image_coords:
        return None
    
    # 빈 히트맵 생성 (검은색 배경)
    heatmap = np.zeros((height, width, 3), dtype=np.uint8)
    
    # 이미지 스케일 계산
    scale_x = img_width / img_display_width if img_display_width > 0 else 1
    scale_y = img_height / img_display_height if img_display_height > 0 else 1
    
    # 각 이미지의 손가락 위치를 화면 좌표로 변환하여 표시
    for img_file, coords in image_coords.items():
        img_x = coords['x']  # 원본 이미지 내부 좌표
        img_y = coords['y']
        confidence = coords.get('confidence', 0.8)
        
        # 이미지 좌표를 화면 좌표로 변환
        screen_x = img_left + (img_x / scale_x) if scale_x > 0 else img_x
        screen_y = img_top + (img_y / scale_y) if scale_y > 0 else img_y
        
        # 화면 범위 내에 있는지 확인
        if 0 <= screen_x < width and 0 <= screen_y < height:
            # 신뢰도에 따라 색상 결정
            color_intensity = int(255 * confidence)
            color = (0, color_intensity, 255 - color_intensity)  # 파란색-녹색 계열
            
            # 점 크기
            radius = int(5 + confidence * 10)
            cv2.circle(heatmap, (int(screen_x), int(screen_y)), radius, color, -1)
            cv2.circle(heatmap, (int(screen_x), int(screen_y)), radius + 2, (255, 255, 255), 2)
            
            # 이미지 이름 표시
            cv2.putText(heatmap, img_file[:15], 
                       (int(screen_x) + radius + 5, int(screen_y)), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    # 마우스 위치 표시 (빨간색 십자가)
    if img_width > 0 and img_height > 0:
        # 마우스 좌표를 화면 좌표로 변환
        mouse_screen_x = img_left + (mouse_x / scale_x) if scale_x > 0 else mouse_x
        mouse_screen_y = img_top + (mouse_y / scale_y) if scale_y > 0 else mouse_y
        
        if 0 <= mouse_screen_x < width and 0 <= mouse_screen_y < height:
            # 빨간색 십자가
            cv2.line(heatmap, 
                    (int(mouse_screen_x) - 20, int(mouse_screen_y)), 
                    (int(mouse_screen_x) + 20, int(mouse_screen_y)), 
                    (0, 0, 255), 3)
            cv2.line(heatmap, 
                    (int(mouse_screen_x), int(mouse_screen_y) - 20), 
                    (int(mouse_screen_x), int(mouse_screen_y) + 20), 
                    (0, 0, 255), 3)
            cv2.circle(heatmap, (int(mouse_screen_x), int(mouse_screen_y)), 15, (0, 0, 255), 2)
    
    # base64로 인코딩
    _, buffer = cv2.imencode('.png', heatmap)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return img_base64


@app.get("/api/get-dataset-heatmap")
async def get_dataset_heatmap(
    width: int = 1920,
    height: int = 1080,
    mouse_x: float = 0,
    mouse_y: float = 0,
    img_width: int = 0,
    img_height: int = 0,
    img_display_width: float = 0,
    img_display_height: float = 0,
    img_left: float = 0,
    img_top: float = 0
):
    """
    이미지 좌표와 마우스 좌표를 고려하여 데이터셋 히트맵 생성
    
    Args:
        width: 화면 너비
        height: 화면 높이
        mouse_x: 마우스 X 좌표 (이미지 좌표계)
        mouse_y: 마우스 Y 좌표 (이미지 좌표계)
        img_width: 원본 이미지 너비
        img_height: 원본 이미지 높이
        img_display_width: 화면에 표시된 이미지 너비
        img_display_height: 화면에 표시된 이미지 높이
        img_left: 이미지 왼쪽 위치
        img_top: 이미지 위쪽 위치
    """
    heatmap_base64 = create_dataset_heatmap(
        width, height, mouse_x, mouse_y,
        img_width, img_height,
        img_display_width, img_display_height,
        img_left, img_top
    )
    
    if heatmap_base64 is None:
        raise HTTPException(
            status_code=404, 
            detail="좌표 데이터가 없습니다. /api/process-images를 먼저 실행하세요."
        )
    
    return {
        "status": "success",
        "heatmap": f"data:image/png;base64,{heatmap_base64}",
        "width": width,
        "height": height,
        "point_count": len(image_coords)
    }


@app.get("/api/get-cursor-heatmap")
async def get_cursor_heatmap(x: float, y: float, width: int = 1920, height: int = 1080):
    """
    마우스 커서 위치를 중심으로 주변 이미지들의 분포를 히트맵으로 시각화
    
    Args:
        x: 마우스 X 좌표
        y: 마우스 Y 좌표
        width: 히트맵 너비 (기본값: 1920)
        height: 히트맵 높이 (기본값: 1080)
    """
    heatmap_base64 = create_cursor_heatmap(x, y, width, height)
    
    if heatmap_base64 is None:
        raise HTTPException(
            status_code=404, 
            detail="좌표 데이터가 없습니다. /api/process-images를 먼저 실행하세요."
        )
    
    return {
        "status": "success",
        "heatmap": f"data:image/png;base64,{heatmap_base64}",
        "cursor_x": x,
        "cursor_y": y,
        "width": width,
        "height": height,
        "point_count": len(image_coords)
    }


def segment_person(image_base64: str) -> Optional[np.ndarray]:
    """
    base64 인코딩된 이미지에서 사람만 추출 (배경 제거)
    
    Args:
        image_base64: base64 인코딩된 이미지 (data:image/... 형식 제거 필요)
        
    Returns:
        사람만 추출된 이미지 (RGBA, 배경은 투명) 또는 None
    """
    try:
        # base64 디코딩
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        image_data = base64.b64decode(image_base64)
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return None
        
        # RGB로 변환 (MediaPipe는 RGB 사용)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 사람 segmentation 수행
        results = selfie_segmentation.process(img_rgb)
        
        if results.segmentation_mask is None:
            return None
        
        # 마스크 가져오기 (0~1 범위)
        mask = results.segmentation_mask
        
        # 마스크를 0~255 범위로 변환
        mask_uint8 = (mask * 255).astype(np.uint8)
        
        # RGBA 이미지 생성 (알파 채널 = 마스크)
        img_rgba = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2RGBA)
        img_rgba[:, :, 3] = mask_uint8  # 알파 채널에 마스크 적용
        
        return img_rgba
        
    except Exception as e:
        print(f"[ERROR] 사람 segmentation 실패: {e}")
        return None


class CompositeRequest(BaseModel):
    """합성 요청 모델"""
    camera_image: str  # base64 인코딩된 웹캠 이미지
    hand_image: str  # 손 이미지 파일명
    finger_x: float  # 손가락 X 좌표 (이미지 내부 좌표)
    finger_y: float  # 손가락 Y 좌표 (이미지 내부 좌표)
    person_scale: float = 1.0  # 사람 크기 조절 (기본값: 1.0)


@app.post("/api/composite")
async def composite_person(request: CompositeRequest):
    """
    손 이미지에 사람 segment를 합성
    
    Args:
        request: 합성 요청 데이터
        
    Returns:
        합성된 이미지 (base64)
    """
    try:
        # 손 이미지 로드
        hand_image_path = Path("static/images") / request.hand_image
        if not hand_image_path.exists():
            raise HTTPException(status_code=404, detail=f"손 이미지를 찾을 수 없습니다: {request.hand_image}")
        
        hand_img = cv2.imread(str(hand_image_path))
        if hand_img is None:
            raise HTTPException(status_code=400, detail="손 이미지를 읽을 수 없습니다")
        
        # RGB로 변환
        hand_img_rgb = cv2.cvtColor(hand_img, cv2.COLOR_BGR2RGB)
        hand_h, hand_w = hand_img_rgb.shape[:2]
        
        # 사람 segment 추출
        person_img_rgba = segment_person(request.camera_image)
        if person_img_rgba is None:
            raise HTTPException(status_code=400, detail="사람을 추출할 수 없습니다")
        
        person_h, person_w = person_img_rgba.shape[:2]
        
        # 사람 크기 조절
        scale = request.person_scale
        new_person_w = int(person_w * scale)
        new_person_h = int(person_h * scale)
        
        if new_person_w > 0 and new_person_h > 0:
            person_img_rgba = cv2.resize(person_img_rgba, (new_person_w, new_person_h), interpolation=cv2.INTER_LINEAR)
        
        # 손가락 위치 계산 (이미지 좌표)
        finger_x = int(request.finger_x)
        finger_y = int(request.finger_y)
        
        # 사람 이미지를 손가락 위치에 배치 (중앙 정렬)
        person_x = finger_x - new_person_w // 2
        person_y = finger_y - new_person_h // 2
        
        # 결과 이미지 생성 (RGBA)
        result_img = np.zeros((hand_h, hand_w, 4), dtype=np.uint8)
        result_img[:, :, :3] = hand_img_rgb
        result_img[:, :, 3] = 255  # 완전 불투명
        
        # 사람 이미지를 합성
        # 사람 이미지가 손 이미지 범위 내에 있는 부분만 합성
        start_x = max(0, person_x)
        end_x = min(hand_w, person_x + new_person_w)
        start_y = max(0, person_y)
        end_y = min(hand_h, person_y + new_person_h)
        
        person_start_x = max(0, -person_x)
        person_end_x = person_start_x + (end_x - start_x)
        person_start_y = max(0, -person_y)
        person_end_y = person_start_y + (end_y - start_y)
        
        if start_x < end_x and start_y < end_y:
            # 알파 블렌딩
            person_region = person_img_rgba[person_start_y:person_end_y, person_start_x:person_end_x]
            result_region = result_img[start_y:end_y, start_x:end_x]
            
            # 영역 크기 확인
            if person_region.shape[0] > 0 and person_region.shape[1] > 0 and \
               result_region.shape[0] > 0 and result_region.shape[1] > 0:
                # 알파 채널 추출
                alpha = person_region[:, :, 3:4] / 255.0
                alpha_3d = np.repeat(alpha, 3, axis=2)
                
                # 알파 블렌딩: result = person * alpha + result * (1 - alpha)
                blended = (person_region[:, :, :3] * alpha_3d + result_region[:, :, :3] * (1 - alpha_3d)).astype(np.uint8)
                result_img[start_y:end_y, start_x:end_x, :3] = blended
        
        # RGB → BGR 변환 (OpenCV imencode는 BGR 형식을 기대함)
        result_img_bgr = cv2.cvtColor(result_img[:, :, :3], cv2.COLOR_RGB2BGR)
        result_img_bgra = cv2.cvtColor(result_img_bgr, cv2.COLOR_BGR2BGRA)
        result_img_bgra[:, :, 3] = result_img[:, :, 3]  # 알파 채널 복사
        
        # BGRA를 PNG로 인코딩하여 base64로 변환
        _, buffer = cv2.imencode('.png', result_img_bgra)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return {
            "status": "success",
            "composite_image": f"data:image/png;base64,{img_base64}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 합성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"합성 실패: {str(e)}")


class SegmentRequest(BaseModel):
    """세그먼트 요청 모델"""
    camera_image: str  # base64 인코딩된 웹캠 이미지


@app.post("/api/save-segment")
async def save_segment(request: SegmentRequest):
    """
    웹캠 이미지를 세그먼트 처리하여 일시적으로 저장
    (하나만 유지, 새로 저장하면 이전 것은 덮어씌워짐)
    
    Args:
        request: 세그먼트 요청 데이터
        
    Returns:
        세그먼트된 이미지 (base64)
    """
    global current_segment_image
    
    try:
        # 사람 segment 추출
        person_img_rgba = segment_person(request.camera_image)
        if person_img_rgba is None:
            raise HTTPException(status_code=400, detail="사람을 추출할 수 없습니다")
        
        # RGB → BGR 변환 (OpenCV imencode는 BGR 형식을 기대함)
        img_bgr = cv2.cvtColor(person_img_rgba[:, :, :3], cv2.COLOR_RGB2BGR)
        img_bgra = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2BGRA)
        img_bgra[:, :, 3] = person_img_rgba[:, :, 3]  # 알파 채널 복사
        
        # BGRA를 PNG로 인코딩하여 base64로 변환
        _, buffer = cv2.imencode('.png', img_bgra)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # 전역 변수에 저장 (이전 것은 덮어씌워짐)
        current_segment_image = f"data:image/png;base64,{img_base64}"
        
        return {
            "status": "success",
            "segment_image": current_segment_image
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 세그먼트 저장 실패: {e}")
        raise HTTPException(status_code=500, detail=f"세그먼트 저장 실패: {str(e)}")


@app.get("/api/get-segment")
async def get_segment():
    """
    현재 저장된 세그먼트 이미지 반환
    
    Returns:
        세그먼트 이미지 (base64) 또는 None
    """
    global current_segment_image
    
    if current_segment_image is None:
        return {
            "status": "success",
            "segment_image": None
        }
    
    return {
        "status": "success",
        "segment_image": current_segment_image
    }


@app.get("/api/health")
async def health_check():
    """서버 상태 확인"""
    return {"status": "ok", "message": "Pointer Pointer Vision API is running"}


if __name__ == "__main__":
    # 서버 시작 시 좌표 데이터 로드
    load_image_coords()
    
    # 개발 서버 실행
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # 개발 모드: 코드 변경 시 자동 재시작
    )

