# DeepSight 04 — `img 해상도 조절.py` 프로그램 설명서

> 분석 대상: 첨부 `img 해상도 조절.py` · 방식: **입력 이미지의 긴 변을 지정한 픽셀 이하로 축소하는 사전 처리**

## 1. 목적

`data/images/` 폴더에 있는 큰 사진을 비율을 유지하며 일괄 축소합니다. 예를 들어 3000×2000 이미지에서 긴 변을 600px로 맞추면 600×400 크기가 됩니다. **모자이크·얼굴 검출 기능은 없습니다.**

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


## 2. 가장 중요한 주의사항

**현재 코드는 축소한 이미지를 입력 파일과 동일한 경로에 저장하므로 원본을 덮어씁니다. 실행 전 `data/images` 폴더를 통째로 백업하세요.** 원래 해상도로 복구하는 기능은 없습니다.

또한 소스의 설명 문구와 주석에는 **800px**이라고 적혀 있지만, 실제 적용값은 아래와 같이 **600px**입니다.

```python
MAX_IMAGE_SIZE = 600
```

따라서 현재 코드를 실행하면 긴 변이 600px을 초과하는 사진은 600px 이하로 줄어듭니다. 800px로 작업하려면 값을 `800`으로 변경하고 안내 문구도 함께 수정해야 합니다.

## 3. 실행 명령

```powershell
python 'source/img 해상도 조절.py'
```

사전에 `data/images/` 폴더가 실제로 있어야 합니다. 없으면 오류를 출력하고 종료합니다.

## 4. 처리 흐름

```text
data/images 검색 → 이미지 확장자 검사
→ 이름이 _mosaic로 끝나는 파일 제외
→ 사진을 읽고 (높이, 너비) 확인
→ 긴 변이 600px보다 크면 축소 비율 계산
→ INTER_AREA 방식으로 축소
→ 같은 원본 파일명에 덮어쓰기
→ 변환 개수와 건너뛴 개수 출력
```

## 5. 주요 함수

| 함수 | 역할 |
|---|---|
| `read_image(path)` | `np.fromfile + cv2.imdecode`로 한글 경로도 읽을 수 있도록 처리 |
| `save_image(path,image)` | `cv2.imencode + tofile`로 이미지 저장 |
| `main()` | 폴더/파일 검사, 축소, 원본 파일 덮어쓰기, 작업 건수 출력 |

### 축소 비율 계산

```python
h, w = image.shape[:2]
max_dim = max(w, h)
if max_dim > MAX_IMAGE_SIZE:
    scale = MAX_IMAGE_SIZE / max_dim
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized_image = cv2.resize(
        image, (new_w, new_h), interpolation=cv2.INTER_AREA
    )
    save_image(image_path, resized_image)
```

`INTER_AREA`는 일반적으로 이미지 축소에 적합한 OpenCV 보간 방식입니다. 단, 축소하면 작은 얼굴의 픽셀 정보가 손실될 수 있습니다.

## 6. 변환 예시 (`MAX_IMAGE_SIZE=600` 기준)

| 변환 전 크기 | 변환 후 크기(정수 버림) | 처리 |
|---|---|---|
| 3000×2000 | 600×400 | 축소 및 원본 덮어쓰기 |
| 1920×1080 | 600×337 | 축소 및 원본 덮어쓰기 |
| 400×600 | 400×600 | 그대로 유지 |
| 800×800 | 600×600 | 축소 및 원본 덮어쓰기 |

## 7. 출력과 재실행

- 결과 이미지의 **저장 위치는 입력 이미지 폴더와 동일**합니다.
- 별도의 `outputs/` 이미지나 CSV는 생성하지 않습니다.
- 첫 실행에서 600px 이하가 된 파일은 다음 실행 시 더 이상 축소되지 않습니다.
- 변환 성공 파일은 `processed_count`에, 작은 이미지·읽기 실패·저장 실패는 `skipped_count`에 집계됩니다.
- 폴더 탐색 순서는 별도 정렬하지 않았습니다.

## 8. 얼굴 인식 프로젝트에서 유의할 점

모자이크 프로젝트의 `MIN_FACE_SIZE`가 30px일 경우 원본에서 100px이던 얼굴도 사진 전체를 1/5로 줄이면 20px 정도가 되어 **검출 기준에서 제외될 수 있습니다**. 따라서 무조건 600px로 줄이는 것이 좋은 것은 아닙니다. 원본 이미지와 축소 이미지를 별도 폴더에 보관하고 동일한 정답표·동일한 모델 설정으로 검출 성능을 비교하는 실험이 필요합니다.

## 9. 추천 개선 방향 (현재 코드에 미반영)

1. 출력 폴더를 `data/resized_images/`처럼 따로 두고 원본을 보존.
2. `--size 800`처럼 명령행에서 긴 변 기준을 입력하도록 변경.
3. `MAX_IMAGE_SIZE`와 주석/출력 문구를 일치시킴.
4. 처리 전후 크기를 CSV로 기록해 실험 재현성을 확보.
5. 비교 실험에서는 원본 폴더를 유지하고 축소 사진을 **별도 입력 데이터셋**으로 사용.
