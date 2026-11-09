# DeepSight v2.1 — 얼굴 모자이크 정책 실험 및 CSV 분석

**프로젝트 상태:** D1 구현 완료 · C 핵심 검증 8/8 통과(사용자 Windows 로그) · A 문서·배포 표준화 완료. 완전한 비식별화 보증 제품은 아닙니다.

## 1. 기능 및 담당 파일

| 기능 | 파일 |
|---|---|
| 기존 Haar 단독 시험 | `source/main.py` → `outputs/first/` |
| 기존 YOLO+Haar 기준 시험 | `source/main_1_baseline.py` → `outputs/second-baseline/` |
| 실험용 4정책 추론 | `source/main_1.py` → `outputs/experiments/{정책}/` |
| 백업을 포함한 **공식 실행 진입점** | `scripts/run_experiment.py` |
| CSV 검증/오차분석/종합표 | `scripts/build_deepsight_reports.py` |
| 정답표와 기준 사진 | `data/ground_truth.csv`, `data/images/` |
| 수동 검수(입력) | `reviews/manual_review.csv` |
| 이전 실험 스냅샷 | `csv_backup/` |

## 2. 환경 준비 (Windows PowerShell)

```powershell
cd K:\LSK\pjt_DeepSight_v2
.\.venv\Scripts\Activate.ps1
python --version
python -m pip check
```

가상환경이 없는 경우에만 새로 만들고 `python -m pip install -r requirements.txt`로 설치하십시오. 기존 환경을 정상 사용 중이라면 재설치하지 않아도 됩니다.

## 3. 공식 실행

```powershell
python scripts\run_experiment.py --compare
```

기존 결과가 존재하면 백업 여부(Y/N)와 이전 실험 설명을 묻습니다. 백업 성공 후 새 실험 설명을 입력하면 20장 이미지에 4정책을 적용하고 CSV를 생성합니다. 실패하면 이전 백업 복원을 시도합니다.

CSV **분석만 다시 수행**할 때:

```powershell
python scripts\build_deepsight_reports.py --root . --strict
```

`python source\main_1.py --compare` 직접 실행은 백업 절차를 우회하므로 **공식 실험 명령으로 사용하지 않습니다.**

## 4. 출력 파일

- 정책별 `outputs/experiments/{legacy,yolo_only,haar_only,improved}/`: `detection_details.csv`, `face_mosaic_results.csv`, `processing_status.csv`, `evaluation_results.csv`, `test_cases.csv`, `test_cases_detailed.csv`, 모자이크 이미지
- 종합 `outputs/`: `policy_comparison.csv`, `policy_test_cases.csv`, `data_validation.csv`, `experiment_run.json`(공식 실험 성공 시)
- CSV의 `Exact Match`·`PASS`는 **얼굴 개수의 일치**를 뜻합니다. 실제 얼굴 위치와 비식별화 성공률은 별도 검수 대상입니다.

## 5. 공식 문서

- `docs/DeepSight_최종검증보고서.md`: 사용자 실환경 검증 8개 및 남은 제약
- `docs/DeepSight_CSV_명세서.md`: 파일·컬럼·생성 주체·검증 기준
- `docs/DeepSight_실험백업_사용설명서.md`: 백업, 이력, 오류, 복원 주의
- `docs/CHANGELOG.md`: 변경 이력
- `docs/README_D1_원본.md`: 이전 버전 README 보존

## 6. 자동 테스트

```powershell
python -m unittest discover -s tests -p test_d1_integration.py -v
python -m pytest tests/test_main_1.py -q
```

두 번째 명령은 `pytest` 설치가 필요할 수 있습니다. D1와 A 사본에서 각각 11개, 6개 통과 확인. A 환경에서 YOLO 추론을 다시 실행하지는 않았습니다.

## 7. 버전·데이터 시점 및 주의

- **v2.1은 문서·배포 표준화 버전**이며, D1 얼굴 검출 코드를 새로 수정한 버전이 아닙니다.
- 이 배포 ZIP의 CSV는 이전 D1 ZIP 시점 데이터(legacy 75%, YOLO 95%, Haar 50%, improved 85%)입니다.
- 사용자의 **2026-11-07 이후 Windows 실행 결과**(legacy 70%, YOLO 80%, Haar 55%, improved 80%)는 사용자가 공유한 로그를 통해 확인되었으나 **해당 최신 CSV·자동 백업 실물 파일은 이 ZIP에 반영되지 않았습니다**. 최신 실험 결과는 사용자 PC의 `outputs/`와 `csv_backup/`에서 별도 보존해야 합니다.
- 실험 결과는 얼굴 개수 일치율이며 완전한 비식별화 성공률이 아닙니다. 외부 공유 전에는 수동 검수해야 합니다.
