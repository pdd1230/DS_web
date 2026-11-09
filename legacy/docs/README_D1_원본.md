# DeepSight 얼굴 자동 모자이크 — PDCA 개선판 v2

> **대상**: 2조 DeepSight / Windows 11 / Python 3.11 가상환경 / 이미지 20장
>
> 이 프로젝트는 현재 **이미지 처리**를 검증합니다. 실시간 영상 추적·동영상 입력은 이번 개선 범위가 아닙니다.

## 1. 프로젝트 목적과 주요 파일

| 위치 | 내용 |
|---|---|
| `source/main_1.py` | 개선판: YOLOv8-Face + Haar, 4종 검출 정책, 검출 후보별 CSV, 실패 구분, 평가 |
| `source/main_1_baseline.py` | 사용자가 실제 실행한 기존 혼합 방식의 백업 |
| `source/main.py` | 기존 초판(참고용) |
| `data/images/img_001.jpg` ~ `img_020.jpg` | 검증 사진 20장 |
| `data/ground_truth.csv` | 이미지별 실제 얼굴 수 정답표 |
| `shared/models/yolov8n-face-lindevs.pt` | 얼굴 YOLO 모델 |
| `requirements.txt` | 새로 전달된 패키지 목록(38개)을 **같은 버전으로** UTF-8 변환 |
| `tests/test_main_1.py` | 모델을 불러오지 않고 실행 가능한 핵심 로직 단위 테스트 |
| `CHANGELOG_PDCA.md` / `PDCA_검토평가_20261105.md` | 수정 내역과 검증 결과 |

`run.bat`는 사용자 조치로 삭제 완료되었으므로 **재생성하지 않습니다**.

## 2. 설치(Windows PowerShell)

프로젝트가 `D:\LSK\pjt_DeepSight`에 위치한 경우:

```powershell
cd D:\LSK\pjt_DeepSight
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install -r requirements.txt
python -m pip check
```

- `.venv`가 이미 올바르게 구성된 경우 다시 만들지 않아도 됩니다.
- 최신 제공본의 원래 `requirements.txt`는 **UTF-16 LE**였지만, 이번 폴더의 파일은 **UTF-8(BOM 없음)**입니다.
- 패키지 목록은 제공본 그대로 유지했으며, 사용자의 Windows 환경에서 실제 재설치는 아직 하지 않았습니다.
- 설치 및 실제 YOLO 추론의 성공 여부는 Windows PyCharm에서 다시 확인해야 합니다.

## 3. 실행 방법

### 기존 검출 결과를 같은 방식으로 실행 (기본값)

```powershell
python source\main_1.py
```

기본 `legacy` 모드는 이전 YOLO + Haar 통합 정책을 따릅니다.
기존 위치 `outputs/`에 CSV와 모자이크 이미지를 기록하므로, 기존 결과를 보존하려면 먼저 백업하세요.

### 네 가지 방법을 한 번에 비교 — 가장 권장

```powershell
python source\main_1.py --compare
```

- 같은 이미지에 YOLO/Haar 추론을 1회씩 수행하고 결과를 4가지 정책에 재활용합니다.
- 실행 중 모델별 후보, 최종 개수, 처리 상태를 출력합니다.
- `outputs/experiments/legacy/`
- `outputs/experiments/yolo_only/`
- `outputs/experiments/haar_only/`
- `outputs/experiments/improved/`
- `outputs/policy_comparison.csv` — 4가지 정책 비교표

### 개선 정책만 실험

```powershell
python source\main_1.py --policy improved
```

**중요:** `improved`는 **실험용 정책**입니다. YOLO가 1개 이상 검출하면 겹치지 않는 Haar 후보를 자동으로 얼굴로 인정하지 않고 `haar_unverified_review`로 **보류**합니다. YOLO가 0개인 이미지에 대해서는 Haar 검출을 보완 채택합니다(`haar_fallback_review`). 이 방식은 `img_012` 같은 오검출을 줄일 가능성이 있지만 **실제 얼굴의 누락을 늘릴 수 있으므로 운영용 기본 정책으로 자동 승격하지 않았습니다.** 보류된 후보는 반드시 수동 검수해야 하며, 외부에 비식별화 완료 이미지로 게시하지 마세요.

## 4. 결과 CSV 읽는 방법

| 파일 | 용도 |
|---|---|
| `detection_details.csv` | 모든 YOLO/Haar 후보별 좌표, `selected`, `decision_reason`, `review_required`, YOLO confidence |
| `face_mosaic_results.csv` | 최종 채택 박스 좌표와 모자이크 결과 (기존 컬럼 호환) |
| `processing_status.csv` | `processed_detected`, `processed_no_face`, `read_failed`, `inference_failed`, `save_failed` 구분 |
| `evaluation_results.csv` | 정답 개수와 예측 개수 일치/과검출/미검출/평가 제외 |
| `policy_comparison.csv` | `--compare`에서 생성되는 정책별 요약 |

Haar에는 YOLO와 같은 의미의 신뢰도(confidence)가 없으므로 `confidence`를 빈 값으로 저장합니다.

**개수 일치율은 얼굴 검출 Precision/Recall과 다릅니다.** 실제 얼굴별 위치 정답 박스를 라벨링한 이후에만 TP/FP/FN을 계산할 수 있습니다.

## 5. 대표 오류 `img_012` 재확인

기존 로그: YOLO 1개, Haar 4개, 최종 3개(정답 1개). 두 오검출 박스는 `(133,357,94,94)`, `(145,484,89,89)`로 Haar에서 유래했습니다.

`--compare` 실행 뒤 `outputs/experiments/improved/detection_details.csv`에서 `img_012.jpg`를 찾아 보류 여부를 확인하세요. 개선 성능은 **실제 YOLO 실행과 결과 이미지 수동 검수까지 마친 후** 판정합니다.

## 6. 테스트

```powershell
python -m pytest tests -q
```

테스트 중 일부는 실제 Haar 모델과 `img_012.jpg`를 사용합니다. `pytest`가 설치되지 않은 경우 별도로 설치해야 하며 이번 제공된 `requirements.txt`에는 테스트용 pytest를 추가하지 않았습니다.

## 7. 검증·보안·개인정보 주의

- 자동으로 인식하지 못한 얼굴은 원본 그대로 남습니다. 비식별화를 보장하는 시스템으로 간주하지 마세요.
- `outputs/`의 모자이크 이미지는 사람이 검수한 뒤 사용해야 합니다.
- 원본/출력 사진은 촬영동의와 이용권한을 확인하고 외부 공개하지 마세요.
- **성능 개선 최종 확정 전**에는 원본 방식(`legacy`)을 기준선으로 유지하세요.
