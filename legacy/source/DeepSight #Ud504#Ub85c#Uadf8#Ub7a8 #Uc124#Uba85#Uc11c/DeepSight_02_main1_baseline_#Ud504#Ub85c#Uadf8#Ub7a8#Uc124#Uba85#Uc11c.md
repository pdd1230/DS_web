# DeepSight 02 — `main_1_baseline.py` 프로그램 설명서

> 분석 대상: 첨부 `main_1_baseline.py` · 방식: **YOLOv8-Face + 정면/측면 Haar Cascade 통합 검출**, 정답표 평가

## 1. 목적과 주요 기능

이 파일은 YOLOv8-Face와 Haar Cascade로 사진의 얼굴을 검출하고, **중복 후보 제거 → 모자이크 → 얼굴 좌표 CSV 저장 → 정답표 대비 검출 인원 수 평가**까지 수행합니다. 첫 번째 프로그램보다 검출 채널과 평가 기능이 확장되었습니다.

```text
입력 사진
 ├─ YOLOv8-Face 후보 검출 (conf=0.35)
 └─ Haar 정면/좌·우 측면 후보 검출
           ↓
     크기·가로세로 비율 검증
           ↓
     IoU 중복제거 및 결합
           ↓
  모자이크 + 빨간 사각형 + Face 번호
           ↓
 결과 이미지 + 얼굴 좌표 CSV
           ↓
 ground_truth.csv와 얼굴 수 비교 → evaluation_results.csv
```

## 공통 프로젝트 구조와 준비

설명서는 **각 파일을 프로젝트의 `source/` 폴더에 배치했을 때**를 기준으로 작성했습니다. 업로드된 이름 그대로 `source/`에 복사하는 경우에는 아래 명령의 파일명도 그에 맞춰 사용하세요. 소스는 `Path(__file__).resolve().parent.parent`를 프로젝트 루트로 사용하므로 파일 위치가 중요합니다.

```text
pjt_DeepSight/
├─ source/
│  └─ [실행할 파이썬 파일]
├─ data/
│  ├─ images/                # 입력 사진
│  └─ ground_truth.csv       # 정답표: 평가 프로그램에서 사용
├─ shared/
│  └─ models/
│     └─ yolov8n-face-lindevs.pt
└─ outputs/                  # 생성 결과
```

PowerShell에서 프로젝트 루트로 이동한 후 **현재 가상환경을 활성화**하여 실행합니다.

```powershell
cd D:\LSK\pjt_DeepSight
.\.venv\Scripts\Activate.ps1
python -c "import cv2, numpy; print('OpenCV', cv2.__version__)"
```

`D:\LSK\pjt_DeepSight`는 예시 경로입니다. 실제 경로에 맞춰 바꾸세요. YOLO를 사용하는 파일은 `ultralytics`와 얼굴 전용 `.pt` 모델도 필요합니다. 설치 여부는 `python -c "import ultralytics; print(ultralytics.__version__)"`로 확인할 수 있습니다. 특정 버전의 호환성은 현재 가상환경에서 별도 점검해야 합니다.

지원하는 사진 형식은 JPG/JPEG/PNG/BMP/WEBP이며, 이름이 `_mosaic`로 끝나는 파일은 처리 대상에서 제외됩니다.


## 2. 실행

```powershell
python source/main_1_baseline.py
```

반드시 `shared/models/yolov8n-face-lindevs.pt` 모델이 존재해야 합니다. `ground_truth.csv`가 없으면 모자이크 작업은 수행하고 **평가만 건너뜁니다.**

## 3. 설정값

| 변수 | 업로드 소스 값 | 역할 |
|---|---:|---|
| `MIN_FACE_SIZE` | 50 | 얼굴 상자의 너비·높이가 각각 50px 이상이어야 함 |
| `MIN_FACE_ASPECT`, `MAX_FACE_ASPECT` | 0.60, 1.40 | 얼굴 후보의 가로/세로 비율 허용 범위 |
| `FRONTAL_NEIGHBORS`, `PROFILE_NEIGHBORS` | 9, 9 | Haar 검출 민감도 제어 |
| `YOLO_CONFIDENCE` | 0.35 | YOLO 모델 예측 신뢰도 하한 |
| `YOLO_IMAGE_SIZE` | 960 | YOLO 추론 입력 크기 |
| `YOLO_NMS_IOU` | 0.5 | YOLO 자체 NMS 중복 제거 임계치 |
| `YOLO_HAAR_IOU_THRESHOLD` | 0.30 | YOLO와 Haar가 같은 얼굴인지 판정 |
| `MOSAIC_SIZE` | 6 | 모자이크 픽셀 크기 제어 인수 |
| `FACE_PADDING_RATIO` | 0.00 | 얼굴 상자 주변 확장 비율(현재 없음) |
| `BOX_THICKNESS_RATIO` | 0.004 | 이미지 크기에 비례한 박스 선 두께 |

`MIN_FACE_SIZE`와 YOLO 신뢰도를 낮추면 작은 얼굴 검출이 늘 수 있지만 **오검출도 늘 수 있습니다.**

## 4. 핵심 함수 설명

| 함수 | 설명 |
|---|---|
| `natural_sort_key` | 이미지 이름의 마지막 숫자를 기준으로 정렬 |
| `read_image`, `save_image` | 한국어 경로를 고려하여 이미지 읽고 저장 |
| `valid_face_box` | 얼굴 좌표가 이미지 안에 있고, 크기/비율 조건에 적합한지 검사 |
| `box_iou` | 두 상자의 교집합/합집합 비율(IoU) 산출 |
| `remove_duplicate_boxes` | 큰 영역부터 채택하고 IoU 0.40 이상인 중복 후보 제외 |
| `detect_faces` | Haar로 정면과 좌·우 측면 얼굴 검출, 후보 중복 제거 |
| `detect_yolo_faces` | YOLOv8-Face로 얼굴 좌표 예측 |
| `merge_face_boxes` | YOLO 우선, YOLO와 겹치지 않는 Haar 후보 추가, 최종 중복 제거 |
| `expand_box` | 얼굴 영역에 선택적 여백 추가 |
| `mosaic_face` | 얼굴 부분을 축소·재확대해 모자이크 |
| `evaluate_results` | 정답 파일과 최종 얼굴 개수를 비교해 평가 CSV 작성 |
| `main` | 모델 로딩부터 이미지 처리·CSV 저장·평가까지 전체 실행 |

## 5. 정답표와 평가

정답표 경로: `data/ground_truth.csv`. **정확한 열 이름은 `파일명`, `실제 얼굴 수`** 입니다.

```csv
파일명,실제 얼굴 수
img_001.jpg,2
img_002.jpg,0
```

각 파일의 예측 얼굴 수를 `face_mosaic_results.csv`의 `status=detected` 행 수로 계산합니다.

| 평가 | 의미 | 예시(정답→예측) |
|---|---|---|
| `Exact Match` | 정답과 예측 인원 수가 같음 | 2→2 |
| `Over-detection` | 예측이 정답보다 많음 | 2→3 |
| `Under-detection` | 예측이 정답보다 적음 | 2→1 |

**중요한 평가상 주의:** 이 버전은 정답표에 있는 모든 파일의 예상 검출 건수를 기본 0으로 초기화합니다. 읽기/추론 실패로 결과 행이 없는 파일도 경우에 따라 **0명으로 비교될 수 있어**, 처리 실패와 실제 얼굴 0명 검출을 구분하지 못합니다. 따라서 계산된 Exact Match 비율은 사람이 최종 검수해야 합니다. 얼굴 **인원 수 일치율**이지 얼굴 위치의 검출 정밀도·재현율은 아닙니다.

## 6. 출력 파일

```text
outputs/
├─ img_001_mosaic.jpg
├─ face_mosaic_results.csv  # 얼굴별 좌표와 검출 상태
└─ evaluation_results.csv   # 정답/예측 얼굴 수 및 평가
```

`face_mosaic_results.csv`에는 `image_name, image_width, image_height, face_index, x, y, w, h, box_x1, box_y1, box_x2, box_y2, status` 필드가 작성됩니다. 얼굴이 없으면 `status=no_face_detected` 행을 기록합니다. `img_012.jpg`에서는 YOLO·Haar·최종 좌표에 대한 상세 디버깅 로그를 출력합니다.

## 7. 재실행과 개선점

- 소스는 출력 CSV를 `'w'`로 열고 결과 이미지를 같은 이름으로 저장하므로 **매번 새 실행 결과로 덮어씁니다**.
- YOLO와 Haar를 함께 쓰면 누락이 줄 수도 있지만 **Haar의 오검출이 추가될 수 있습니다**.
- 정상 이미지와 읽기 실패를 구분해 별도 처리 상태 CSV를 남기는 개선이 필요합니다.
- 검출 근거와 후보별 채택/배제 이유를 추적하려면 다음 v2 프로그램을 사용합니다.
- `ground_truth.csv` 파일명은 실제 입력 이미지명과 정확히 일치해야 합니다.

## 8. 학생 확인 실습

동일한 사진 20장으로 `MIN_FACE_SIZE=50`, `YOLO_CONFIDENCE=0.35` 조건을 고정하고 정답 수/예측 수/오류 유형을 기록하세요. 임계치를 변경할 때는 **같은 사진과 같은 정답표**로 비교해야 합니다.
