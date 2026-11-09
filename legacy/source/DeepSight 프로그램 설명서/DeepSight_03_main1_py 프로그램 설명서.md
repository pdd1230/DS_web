# DeepSight 03 — `main_1(3).py` 프로그램 설명서 (PDCA v2)

> 분석 대상: 첨부 `main_1(3).py` · 방식: **YOLOv8-Face + Haar Cascade 얼굴 검출의 4개 정책 비교**

## 1. 목적

단순히 얼굴을 가리는 것에서 더 나아가, **검출 후보의 출처와 채택 이유, 처리 실패 여부, 정책별 정답 일치율**을 기록하는 실험용 프로그램입니다. `--compare` 실행 시 같은 사진에 대한 YOLO/Haar 추론 결과를 공유하여 네 가지 정책을 비교합니다.

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


## 2. 실행 명령어

첨부 파일명을 변경하지 않고 `source/`에 둔 경우:

```powershell
# 기본: 기존 통합 정책 1개 실행
python 'source/main_1(3).py'

# 4개 정책을 한 번에 평가
python 'source/main_1(3).py' --compare

# 개선 정책 1개만 시험
python 'source/main_1(3).py' --policy improved

# YOLO 단독 정책 1개만 시험
python 'source/main_1(3).py' --policy yolo_only
```

소스 상단의 실행 예시는 `source/main_1.py` 파일명을 가정합니다. 사용자가 파일명을 `main_1.py`로 바꾸어 저장했다면 위 명령도 `python source/main_1.py ...`로 변경합니다.

## 3. 처리 흐름

```text
입력 폴더 검색 → 사진 읽기
→ YOLO 얼굴 후보 + Haar 얼굴 후보 추출 (이미지당 각 1회)
→ 후보 크기/비율 필터 및 IoU 비교
→ 선택한 정책으로 후보 채택/제외 결정
→ 얼굴 모자이크 + Face 번호 + 빨간 박스
→ 정책별 이미지·상세 CSV·상태 CSV 저장
→ 정답표와 얼굴 수 비교
→ (비교 모드) policy_comparison.csv 생성
```

## 4. 네 가지 정책 비교

| 정책 | 얼굴 후보 선택 방식 | 해석 시 주의 |
|---|---|---|
| `legacy` | YOLO 후보 + 겹치지 않는 Haar 후보, 최종 중복 제거 | Haar 오검출을 포함할 수 있음 |
| `yolo_only` | YOLO 후보만 사용 | YOLO가 놓친 얼굴을 Haar가 보충하지 않음 |
| `haar_only` | Haar 후보만 사용 후 중복 제거 | Haar 특유의 오검출·누락 가능 |
| `improved` | YOLO 후보 우선, YOLO가 하나라도 있으면 비중복 Haar 후보는 **자동 채택하지 않고 검토 표시**; YOLO가 전혀 없을 때 Haar를 보완 채택 | 이름은 `improved`지만 실제 정확도 우위가 보장되는 것은 아님 |

`improved`는 Haar가 추가로 찾은 얼굴을 수동 검토 대상으로 둘 수 있으므로 **최종 자동 얼굴 수가 더 작아질 수 있습니다**. 처리 정책과 실제 비식별화 완성도는 별도 평가해야 합니다.

## 5. 최신 업로드 소스의 핵심 설정

| 상수 | 현재 값 | 의미 |
|---|---:|---|
| `MIN_FACE_SIZE` | **30** | 가로·세로 최소 30px |
| `MIN_FACE_ASPECT / MAX_FACE_ASPECT` | 0.60 / 1.40 | 박스 가로세로 비율 범위 |
| `FRONTAL_NEIGHBORS / PROFILE_NEIGHBORS` | 9 / 9 | Haar 후보 필터링 |
| `YOLO_CONFIDENCE` | **0.20** | YOLO 최소 신뢰도 |
| `YOLO_IMAGE_SIZE` | 960 | 추론 이미지 크기 설정 |
| `YOLO_NMS_IOU` | 0.50 | YOLO 예측 내부의 중복제거 기준 |
| `YOLO_HAAR_IOU_THRESHOLD` | 0.30 | YOLO/Haar 중복 판단 기준 |
| `MOSAIC_SIZE` | 6 | 모자이크 축소 인수 |
| `FACE_PADDING_RATIO` | 0.00 | 모자이크 영역 추가 여백 없음 |
| `dedupe`의 `threshold` | 0.40 | 최종 후보 간 중복 처리 |

**버전 구분:** 첨부한 baseline 소스는 `MIN_FACE_SIZE=50`, `YOLO_CONFIDENCE=0.35`입니다. 이 v2 소스는 각각 **30, 0.20**으로 조정된 상태입니다. 정책 변경 효과와 임계치 변경 효과를 분리하려면 두 버전의 설정을 동일하게 맞춘 뒤 비교해야 합니다.

## 6. 주요 함수 상세

| 함수 | 역할 |
|---|---|
| `FaceCandidate` | 후보의 검출기 이름, 박스, 신뢰도를 담는 불변 데이터 클래스 |
| `read_image / save_image` | 한국어 경로 이미지 처리 |
| `valid_face_box` | 얼굴 크기·영상 범위·모양 필터 |
| `box_iou / dedupe` | 검출 상자 겹침 계산과 중복 제거 |
| `get_haar_cascades` | 정면/측면 Haar 모델 로딩 |
| `detect_haar` | 정면 + 좌우 측면 검출 및 중복 제거 |
| `detect_yolo` | YOLO 모델 얼굴 후보와 신뢰도 추출 |
| `choose_candidates` | 정책별 채택·제외 이유와 수동 검토 여부 결정 |
| `expand_box / mosaic_face` | 모자이크 범위 조정 및 픽셀화 |
| `ground_truth_counts` | UTF-8 BOM 허용 CSV 정답표 읽기 |
| `write_csv` | UTF-8 BOM 포함 CSV 저장(엑셀 호환) |
| `evaluate` | 인원 수 일치/과검출/미검출/처리 실패 평가 |
| `run` | 이미지 검출 결과를 정책별로 재사용하고 파일 저장 |
| `main` | `--policy`, `--compare` CLI 인수 처리 |

## 7. 출력 경로와 파일 의미

**기본 실행 (`legacy` 단독)** 결과는 `outputs/` 바로 아래에 저장됩니다. **`--compare` 또는 다른 정책 단독 실행** 결과는 `outputs/experiments/<정책>/`에 저장됩니다.

```text
outputs/
├─ img_001_mosaic.jpg                  # legacy 단독 실행 시
├─ detection_details.csv               # 후보별 채택·제외 사유
├─ face_mosaic_results.csv             # 모자이크 적용 얼굴 좌표
├─ processing_status.csv               # 처리 실패 및 검토 상태
├─ evaluation_results.csv              # 얼굴 수 정답과 비교
├─ policy_comparison.csv               # --compare 실행 시 생성
└─ experiments/
   ├─ legacy/
   ├─ yolo_only/
   ├─ haar_only/
   └─ improved/
      ├─ img_001_mosaic.jpg
      ├─ detection_details.csv
      ├─ face_mosaic_results.csv
      ├─ processing_status.csv
      └─ evaluation_results.csv
```

`policy_comparison.csv`은 **`--compare`처럼 정책을 2개 이상 실행할 때만 새로 작성**됩니다. 단일 정책만 재실행하면 이전에 존재하던 비교 CSV가 자동 삭제·갱신되지 않습니다.

### CSV 주요 필드

| CSV | 중요한 열 | 뜻 |
|---|---|---|
| `detection_details.csv` | `detector`, `confidence`, `selected`, `decision_reason`, `review_required` | 어떤 모델이 검출했고 왜 채택/제외됐는지 |
| `face_mosaic_results.csv` | `image_name`, `face_index`, `x`, `y`, `w`, `h`, `status` | 최종 검출 얼굴 좌표 |
| `processing_status.csv` | `processing_status`, `detected_count`, `error_message`, `manual_review_required` | 사진별 처리/검토 상태 |
| `evaluation_results.csv` | `ground_truth`, `detected`, `evaluation`, `processing_status` | 정답과 예측 수 비교 |
| `policy_comparison.csv` | `policy`, `total`, `evaluated`, `exact`, `over`, `under`, `failed`, `exact_match_pct` | 정책별 종합 결과 |

**처리 상태:** `processed_detected`(얼굴 검출 후 정상 저장), `processed_no_face`(0명 검출 후 정상 저장), `read_failed`(읽기 실패), `inference_failed`(추론 실패), `save_failed`(저장 실패).

## 8. 정답표와 성능 지표 해석

정답표 `data/ground_truth.csv`의 필수 헤더는 **`파일명`, `실제 얼굴 수`**입니다.

```csv
파일명,실제 얼굴 수
img_001.jpg,2
img_002.jpg,0
```

- `total`: 정답표에 등록된 이미지 수.
- `evaluated`: 실제 정상 처리되어 평가된 이미지 수.
- `exact`: 예측 얼굴 수가 정답과 동일한 이미지 수.
- `over`: 실제보다 많은 얼굴 수를 검출한 이미지 수.
- `under`: 실제보다 적은 얼굴 수를 검출한 이미지 수.
- `failed`: 처리 실패 또는 정답표 파일이 처리되지 않은 건수.
- `exact_match_pct = exact / evaluated × 100` (평가 건수가 0이면 값 없음).

예를 들어 `total=20, evaluated=20, exact=19, over=0, under=1, failed=0`이면 **얼굴 수 정확 일치율은 95%**입니다. 이것은 이미지별 인원 수 일치율이며, 얼굴 위치나 놓친 사람의 신원이 맞는지는 평가하지 않습니다.

## 9. 재실행 시 갱신 여부

- 같은 조건으로 `--compare`를 2~3회 실행할 경우 **같은 경로의 이미지와 4개 정책 CSV, `policy_comparison.csv`를 다시 씁니다**.
- 단일 `legacy` 실행은 `outputs/` 바로 아래의 결과만 갱신합니다.
- 단일 `--policy yolo_only`나 `--policy improved` 실행은 해당 정책 폴더만 갱신하고, 기존 `policy_comparison.csv`는 갱신하지 않습니다.
- 중간에 입력 사진을 삭제했다면, **지난 실행의 오래된 모자이크 이미지 파일이 출력 폴더에 남을 수 있습니다.** CSV는 해당 실행 대상에 관해 새로 작성되므로 이전 이미지와 혼동하지 마세요.
- 추론 모델이나 입력 사진, 설정값이 바뀌면 수치는 바뀔 수 있습니다. 반복 실행 결과가 반드시 같다고 보장하지는 않습니다.

## 10. 실험 설계와 검증

1. 정답표의 파일명·실제 얼굴 수를 사람이 다시 확인합니다.
2. 임계치를 고정한 채 `--compare`를 실행해 **정책 차이만** 비교합니다.
3. 다음에는 **정책을 고정**하고 `MIN_FACE_SIZE` 또는 `YOLO_CONFIDENCE` 중 하나씩 바꿔 비교합니다.
4. `exact_match_pct` 외에도 `over`, `under` 및 누락된 얼굴의 실제 이미지를 확인합니다.
5. `manual_review_required=yes`인 파일과 **얼굴 0명으로 판정된 파일**을 우선 수동 검토합니다.

### 중요한 한계

- `ground_truth.csv`가 없으면 평가 파일은 헤더만 남고 비교 수치의 근거가 없습니다.
- 정답표에 없는 입력 파일은 모자이크는 수행되지만 정답 일치율 평가 대상은 아닙니다.
- `improved` 정책에서 검토 대기된 Haar 후보는 자동 모자이크에 반영되지 않으므로 실제 사람의 얼굴이 남을 수 있습니다.
- **자동 모자이크는 완전한 비식별화를 보장하지 않습니다.** 배포 전에 원본 대조 및 수동 검수를 진행하세요.

## 11. 학생용 확인 질문

- `legacy`가 `yolo_only`보다 오검출이 많은 원인은 무엇일까요?
- `improved`가 더 낮은 Exact Match를 기록할 수도 있는 이유는 무엇일까요?
- 인원 수가 정확해도 개인정보 보호가 실패하는 사례는 어떤 것일까요?
