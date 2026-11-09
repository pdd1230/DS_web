# DeepSight v2 — 통합 D1 실행 및 CSV 사용설명서

> 구현 범위: 자동 백업·실험 이력, 비교표 생성 책임 통일, 정책별 CSV 일관성 검증, 자동 평가·수동 검수 분리. **이 문서는 실행 가이드이며, 실제 모델 추론 실행 결과의 검증 여부는 검증 보고서를 참조**합니다.

## 1. 준비와 보존 원칙

- Python 가상환경을 활성화하고 프로젝트 `requirements.txt`에 따라 패키지를 준비합니다. PC에 모델 파일 `shared/models/yolov8n-face-lindevs.pt`가 있는지 확인하세요.
- 기존 `data/ground_truth.csv`, 이미지·모델, `csv_backup/`의 수동 백업, `outputs/first/`, `outputs/second-baseline/`은 수정하지 않습니다.
- **새 작업 전에 지금 프로젝트 ZIP 자체를 별도 위치에도 저장하는 것을 권장합니다.**
- 공식 비교 실험 명령은 다음과 같습니다. PowerShell의 작업 디렉터리는 프로젝트 루트로 설정합니다.

```powershell
cd K:\LSK\pjt_DeepSight_v2
.\.venv\Scripts\Activate.ps1
python scripts\run_experiment.py --compare
```

실제 경로가 다르면 `cd`만 해당 프로젝트 위치로 변경하세요. ZIP에 `.venv`는 포함되어 있지 않습니다.

## 2. 실행 대화 예시

```text
[기존 결과 발견] 파일 100여 개
기존 결과를 백업하시겠습니까? [Y/N, 기본 취소]: Y
백업할 이전 실험에 대한 주석을 입력하세요: YOLO 이미지 크기 960, conf 0.35 실험으로 추정(확인 필요)
[백업 완료] csv_backup/20261107_... (파일 해시 확인)
새 실험 목적·변경사항을 입력하세요: YOLO 이미지 크기 1280으로 변경하고 네 정책 비교
[새 실험] ...
[완료] 4개 정책 실행 및 분석 성공
```

- 기존 결과가 있을 때 `N` 또는 Enter, 혹은 백업 실패 시 **추론을 실행하지 않습니다**.
- 백업 주석과 새 실험 메모를 별도로 입력합니다. 이전 설정을 알 수 없다면 `미확인`이라고 입력하세요. 현재 소스 설정을 과거 설정으로 추정하지 않습니다.
- 새 실험은 백업 확인 후 실행되며, 추론 또는 분석 실패 시 기존 백업에서 출력 파일을 복원합니다. 복원 실패 시 백업 경로를 안내합니다.
- 기존 명령 `python source/main_1.py --compare`는 **경고만 표시**합니다. 백업 절차를 적용하려면 `run_experiment.py`를 사용해야 합니다.
- 현재 `run_experiment.py`는 **대화형 명령행 실행**을 전제로 하며, 무인 실행/예약 실행 시에는 기본적으로 취소됩니다.

## 3. 폴더별 역할

```text
pjt_DeepSight_v2/
├─ source/
│  ├─ main.py                        # outputs/first/ (변경 안 함)
│  ├─ main_1_baseline.py             # outputs/second-baseline/ (변경 안 함)
│  └─ main_1.py                      # 4개 정책 추론, 중복 종합표 출력 제거
├─ scripts/
│  ├─ run_experiment.py              # 통합 실험 관리자 (신규)
│  └─ build_deepsight_reports.py     # 정책별 CSV 검증 및 분석
├─ data/
│  ├─ images/
│  └─ ground_truth.csv              # 수기로 입력하는 유일한 GT
├─ reviews/
│  └─ manual_review.csv             # 사용자 수기 검수, 자동 덮어쓰기 없음
├─ csv_backup/
│  ├─ min_face_size=50  YOLO_CONFIDENCE=0.35/  # 이전 수동 백업 유지
│  └─ 2026..._xxxxxxx/
│     ├─ backup_manifest.json
│     ├─ experiment_note.md
│     ├─ previous_settings.json
│     └─ outputs_snapshot/          # CSV 및 정책별 모자이크 이미지
├─ logs/
│  └─ validation_errors.log         # 분석 실패 진단 (오류 발생 시)
└─ outputs/
   ├─ first/                        # 백업·분석에서 제외
   ├─ second-baseline/              # 백업·분석에서 제외
   ├─ experiments/
   │  ├─ legacy/
   │  ├─ yolo_only/
   │  ├─ haar_only/
   │  └─ improved/
   ├─ policy_comparison.csv         # 분석 프로그램만 생성, 11컬럼
   ├─ policy_test_cases.csv
   ├─ data_validation.csv          # 검증 통과 기록
   ├─ aggregate_status.csv         # 정책 일부만 있을 때 구식 종합표 주의 표시
   └─ experiment_run.json          # 현재 성공한 실험 설정과 입력 해시
```

각 정책 폴더에는 추론 CSV 4종(`detection_details.csv`, `face_mosaic_results.csv`, `processing_status.csv`, `evaluation_results.csv`)과 분석 CSV 2종(`test_cases.csv`, `test_cases_detailed.csv`), 모자이크 이미지가 저장됩니다.

## 4. 분석만 다시 수행할 때

```powershell
python scripts\build_deepsight_reports.py --root . --strict
```

- 이미 생성된 추론 CSV 4종과 GT를 읽고 분석 CSV를 만듭니다. 모델 실행은 필요 없습니다.
- `--strict`: 4개 정책 폴더가 모두 존재해야 합니다. `--strict`를 생략하면 **정책 폴더 자체가 없는 경우만** 건너뛰며, 4정책 종합표는 새로 만들지 않습니다. 기존 종합표가 남아 있으면 `aggregate_status.csv`에서 구식 가능성을 표시합니다.
- 손상되거나 누락된 필수 CSV가 있는 **존재하는 정책 폴더**는 실패합니다.
- 분석 실패 시 기존 분석 CSV 파일은 변경하지 않고 `logs/validation_errors.log`에 오류를 남깁니다.
- `processing_status.csv`는 원본 추론 기록으로 읽기 전용입니다.

## 5. CSV 컬럼과 의미

| 파일 | 담당 | 목적 |
|---|---|---|
| `data/ground_truth.csv` | 사람 | 사진별 실제 얼굴 수·촬영 조건·비고 |
| `detection_details.csv` | `main_1.py` | 검출 후보와 채택/제외 이유 |
| `face_mosaic_results.csv` | `main_1.py` | 최종 채택한 얼굴 좌표 |
| `processing_status.csv` | `main_1.py` | 처리 성공/실패·검수 필요 여부 |
| `evaluation_results.csv` | `main_1.py` | 정답과 검출 개수 비교 |
| `test_cases.csv` | 분석 스크립트 | 기존 7컬럼, 자동 PASS/FAIL(개수 비교) |
| `test_cases_detailed.csv` | 분석 스크립트 | 후보·개수 오차·상태·수기 검수 결합 |
| `policy_comparison.csv` | **분석 스크립트만** | 4개 정책 성능 종합, 11컬럼 |
| `policy_test_cases.csv` | 분석 스크립트 | 동일 사진의 4개 정책 예측 및 오차 비교 |
| `data_validation.csv` | 분석 스크립트 | GT·추론 CSV 4종의 일관성 검증 통과 기록 |

`test_cases.csv`의 7개 컬럼은 `test_id, scenario, expected_behavior, input_filename, actual_result, pass_fail, note`이며 **영문 컬럼명은 기존 연동 호환성 때문에 유지**합니다.

> **PASS는 얼굴 개수 일치만 의미**합니다. 잘못된 얼굴을 잡았지만 개수가 같을 수도 있으므로, 검출 좌표 정확성이나 얼굴 비식별화 완전성을 증명하지 않습니다.

## 6. 수동 검수 작성 방법

`reviews/manual_review.csv` 파일을 엑셀이나 메모장으로 열어 헤더 아래에 행을 추가합니다. **이 파일은 생성된 보고서가 아니고 사람이 관리하는 원본**입니다.

```csv
experiment_id,policy,filename,review_status,review_result,missing_faces,false_faces,mosaic_quality,review_note
20261107_180000_ab12cd34,yolo_only,img_020.jpg,검수완료,미검출,1,0,보완 필요,좌측 얼굴 1개 누락
```

- `experiment_id`는 **현재 성공한 실험의** `outputs/experiment_run.json`에 있는 값을 그대로 입력합니다. 실험 ID를 잘못 입력하면 해당 결과에 수동 검수가 병합되지 않습니다.
- `policy`는 `legacy`, `yolo_only`, `haar_only`, `improved` 중 하나를 입력합니다.
- `filename`은 GT 파일명과 일치해야 합니다.
- 수동 검수 내용은 기존 `reviews/manual_review.csv`에 그대로 남으며 분석 스크립트가 덮어쓰지 않습니다.
- 실험 ID가 이미 있는 검수 내용을 상세 결과에 반영하려면 다음처럼 분석 명령을 사용합니다.

```powershell
python scripts\build_deepsight_reports.py --root . --strict --experiment-id 20261107_180000_ab12cd34
```

- 검수를 하지 않았다면 `review_status=미검수`이고, 자동 PASS/FAIL과 독립적입니다.
- 모자이크된 결과를 직접 열고 검토하기 전에는 실제 누락/오검출 개수를 추측해 입력하지 마세요.

## 7. 백업 확인 및 복원

백업에 있는 `backup_manifest.json`에는 파일마다 `path`, `size`, `sha256`이 기록됩니다. 이전 실험 설정이 존재하지 않으면 `previous_settings.json`에는 `미확인`으로 기록합니다.

복원은 기존 출력에 덮어쓰는 작업이므로, **다른 백업을 만든 후** 아래 순서로 진행하세요.

1. 실행 중인 추론/분석 프로그램이 없는지 확인합니다.
2. `csv_backup/<실험ID>/outputs_snapshot/experiments/`를 `outputs/experiments/`로 복사합니다.
3. 같은 백업 아래 `outputs_snapshot/`에 있는 정책 비교표와 검증표를 `outputs/`에 복사합니다.
4. `backup_manifest.json`에 있는 해시와 복원 파일을 비교하여 손상이 없는지 확인합니다.
5. `outputs/first/`, `outputs/second-baseline/`, `reviews/manual_review.csv`는 복원하지 않습니다.

**수동 복원 시 주의:** 이전에 없던 결과 파일은 직접 정리해야 완전한 복원이 됩니다. 관리 프로그램은 실행 실패 시 기존 결과의 파일 구성에 맞춰 자동 복원합니다.

## 8. 주의사항

- ZIP 속 원래 `csv_backup` 수동 보관 자료는 수정하지 않습니다.
- 예전 직접 실행의 결과에는 실험 ID가 없을 수 있습니다. 이 경우 수동 검수는 연결되지 않으며 과거 설정을 현재 설정으로 소급 추정하지 않습니다.
- 백업은 원본 사진이나 YOLO 모델 파일을 통째로 복사하지 않고 **파일명·크기·해시**를 기록합니다. 원본/모델이 바뀌었다면 동일 실험을 재현하기 어려우므로 별도 보관이 필요합니다.
- 사람이 평가한 얼굴 좌표 GT가 없으므로 모자이크의 완전한 성공률은 계산하지 않습니다.
