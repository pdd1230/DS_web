# DeepSight 01 — `main(10).py` 프로그램 설명서

> 분석 대상: 첨부 원본 `main(10).py` · 방식: **Haar Cascade 단독 얼굴 검출과 모자이크**

## 1. 프로그램 목적

사진 폴더에 있는 여러 이미지를 읽어 OpenCV의 **정면 얼굴 Haar Cascade**로 얼굴 위치를 찾아 모자이크한 이미지를 `outputs/`에 저장합니다. **정답표 비교나 CSV 성능평가는 구현되어 있지 않습니다.** 얼굴이 한 명도 검출되지 않아도 원본과 동일한 내용의 출력 이미지가 저장될 수 있습니다.

## 2. 한눈에 보는 처리 순서

```text
data/images 파일 탐색 → 파일명 숫자 기준 정렬 → 이미지 읽기
→ BGR을 회색조로 변환 → 히스토그램 평활화
→ Haar 정면 얼굴 검출 → 검출된 영역에 모자이크
→ 파일명_mosaic.jpg 저장 → 성공/실패 건수 출력
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


## 3. 실행 방법

파일을 `source/main(10).py`에 두었다면:

```powershell
python 'source/main(10).py'
```

다른 이름으로 저장했다면 해당 이름을 사용합니다. 입력 이미지 예: `data/images/img_001.jpg`. 출력 예: `outputs/img_001_mosaic.jpg`.

## 4. 주요 설정값과 의미

| 설정·인수 | 현재 값 | 설명 |
|---|---:|---|
| `INPUT_DIR` | `data/images` | 원본 이미지 폴더 |
| `OUTPUT_DIR` | `outputs` | 결과 저장 폴더 |
| `scaleFactor` | `1.1` | 얼굴 후보 탐색 시 크기 배율 |
| `minNeighbors` | `6` | 높은 값일수록 대체로 오검출을 줄이지만 미검출이 증가할 수 있음 |
| `minSize` | `(40,40)` | Haar가 탐색하는 최소 크기 |
| `mosaic_size` | `80` | 축소 비율의 분모, 클수록 대체로 큰 모자이크 픽셀 블록 생성 |

**주의:** `mosaic_size=80`은 블록이 정확히 80px이라는 의미가 아니라 `w // 80`, `h // 80`으로 축소할 때 사용하는 값입니다. 작은 얼굴일수록 사실상 한두 개의 큰 블록이 될 수 있습니다.

## 5. 함수별 상세 설명

| 함수 | 입력 | 동작 | 반환값·결과 |
|---|---|---|---|
| `natural_sort_key(path)` | 이미지 경로 | 파일명에 있는 마지막 숫자로 정렬 키 생성 | 정렬 키 |
| `read_image(path)` | 경로 | `np.fromfile`+`cv2.imdecode`로 한글 경로 이미지 읽기 | 이미지 또는 `None` |
| `save_image(path,image)` | 경로와 영상 배열 | `cv2.imencode`+`tofile`로 저장 | 성공 여부 `bool` |
| `mosaic_face(image,x,y,w,h,mosaic_size=80)` | 영상과 얼굴 좌표 | 얼굴을 작게 축소한 뒤 최근접 보간으로 확대 | 제자리에서 원본 배열 수정 |
| `main()` | 없음 | 폴더 생성·검출·모자이크·파일 저장·결과 요약 | 콘솔 출력 |

### 핵심 코드 이해

```python
faces = face_cascade.detectMultiScale(
    gray, scaleFactor=1.1, minNeighbors=6, minSize=(40, 40),
    flags=cv2.CASCADE_SCALE_IMAGE
)
for x, y, w, h in faces:
    mosaic_face(image, x, y, w, h, mosaic_size=80)
```

- `(x, y)`는 얼굴 사각형 왼쪽 위의 좌표입니다.
- `(w, h)`는 사각형의 너비와 높이입니다.
- 검출된 얼굴만 모자이크하므로 **미검출된 얼굴은 그대로 남습니다.**

## 6. 입·출력 및 재실행

- 입력: `data/images` 폴더의 지원 이미지.
- 출력: `outputs/원본파일명_mosaic.확장자`.
- 같은 파일명으로 다시 실행하면 **출력 이미지가 덮어써집니다.** 입력 원본은 이 코드에서 변경하지 않습니다.
- `success_count`는 이미지 **저장 성공 수**이고 얼굴 검출 성공 수가 아닙니다.
- `failed_count`는 이미지 읽기 또는 저장 실패 수입니다.

## 7. 검증 및 한계

1. 얼굴이 0명인 사진, 정면·측면 얼굴, 작은 얼굴, 여러 얼굴 사진을 각각 시험합니다.
2. 원본과 출력을 나란히 놓고 **얼굴 누락**, 배경 오검출, 모자이크 강도를 수동 검사합니다.
3. 정면용 Haar 모델만 사용하므로 측면·가려진 얼굴·어두운 사진에 취약할 수 있습니다.
4. 별도의 검출 좌표 CSV, 정답표 비교, 수동 검토 표시가 없습니다.
5. 자동 모자이크 결과만으로 개인정보 비식별화 완료를 보장할 수 없습니다.

## 8. 자주 발생하는 문제

| 증상 | 점검 |
|---|---|
| 이미지가 없다는 메시지 | `source/` 기준 한 단계 위의 `data/images/` 확인 |
| Haar 모델 로드 실패 | OpenCV 설치 상태와 `cv2.data.haarcascades` 확인 |
| 결과 사진에 얼굴이 남음 | 검출 자체가 누락되었을 수 있음. 수동 확인 필수 |
| 모자이크가 지나치게 강함 | `mosaic_size`를 낮춰 시험하고 비교 |

## 9. 학생 실습 과제

동일한 이미지 10~20장에 대해 전체 저장 건수와 실제 얼굴 검출 건수를 **구분**하여 기록하고, 정면/측면 얼굴에 따른 누락 사례를 분석해 보세요.
