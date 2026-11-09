# DeepSight v2 — D1 통합 구현 변경 내역

| 파일 | 작업 | 기존 호환성 |
|---|---|---|
| `scripts/run_experiment.py` | 신규: 대화형 실행·기존 결과 감지·SHA-256 백업·이전/새 실험 주석·설정/모델/사진/GT 해시 기록·실패 시 복원 | `main_1.py --compare`를 내부에서 호출 |
| `source/main_1.py` | 종합 `policy_comparison.csv` 직접 저장 4줄 제거, 직접 실행 시 백업 관리 안내 추가 | 검출/모자이크/정책 선택/추론 설정 불변 |
| `scripts/build_deepsight_reports.py` | 4개 추론 CSV + GT 교차 검증, 분석 결과 일괄 준비·실패 시 롤백, 검증표, 수동 검수 병합 | `--root . --strict`, `test_cases.csv` 7개 컬럼, 종합 비교표 11개 컬럼 보존 |
| `reviews/manual_review.csv` | 신규 빈 입력 양식 | 분석 스크립트 읽기 전용 |
| `tests/test_d1_integration.py` | 신규 회귀·오류 주입 시험 | 기존 `tests/test_main_1.py` 보존 |
| `DeepSight_D1_통합_사용설명서.md` | 신규 운영 문서 | 한글 설명 |
| `DeepSight_D1_검증결과.md` | 신규 시험 보고서 | 실제 미검증 내용 구분 |

**수정 금지 대상 유지:** `source/main.py`, `source/main_1_baseline.py`, `data/ground_truth.csv`, 기준 사진, 모델, 종전 `csv_backup` 및 `outputs/first`, `outputs/second-baseline`.

**종합 비교표 생성 주체는 분석 스크립트로 단일화했습니다.** 기존 미승인 계획서는 원본 그대로 둡니다.
