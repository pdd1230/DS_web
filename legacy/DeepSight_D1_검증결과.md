# DeepSight v2 — 통합 D1 구현 검증 결과

## 1. 검증 범위

기존 ZIP의 실행 결과 20장 × 4개 정책을 사용해 CSV 분석 재현성을 확인하였으며, 실행 관리는 실제 모델 추론 대신 호출을 모의하는 테스트로 검증했습니다. 현재 실행 컨테이너에는 `ultralytics`가 설치되어 있지 않아 YOLO 가중치를 로딩한 실제 추론을 재실행하지 못했습니다. **사용자 Windows 환경의 실제 추론·속도·이미지 품질 검증은 C 단계 확인이 필요합니다.**

## 2. 기준 데이터 재현

| 정책 | 정답 일치 | 평가 이미지 | 얼굴 개수 일치율 | 검증 |
|---|---:|---:|---:|---|
| 기존 통합(legacy) | 15 | 20 | 75% | 통과 |
| YOLO 단독(yolo_only) | 19 | 20 | 95% | 통과 |
| Haar 단독(haar_only) | 10 | 20 | 50% | 통과 |
| 개선형(improved) | 17 | 20 | 85% | 통과 |

이 수치는 **ZIP 내부에 이미 있는 추론 CSV를 분석**해 재현한 결과입니다. 변경된 소스로 새 추론을 실행한 결과가 아닙니다.

## 3. 자동화 테스트

- 신규 `tests/test_d1_integration.py`: **11개 테스트 통과** (`python -m unittest discover -s tests -p test_d1_integration.py -v`)
- 기존 `tests/test_main_1.py`: **6개 테스트 통과** (`python -m pytest tests/test_main_1.py -q`)

| 번호 | 승인 계획의 합격 기준 | 확인 결과 |
|---|---|---|
| 1 | 백업 N/빈 입력 → 실행 취소 | **통과(모의 호출)** |
| 2 | 백업 실패/해시 오류 → 추론 금지 | **통과(복사 실패 주입, 추론 호출 0회 확인)** |
| 3 | 이전·새 실험 주석 구분 | **통과(모의 실행)** |
| 4 | 이번 실험 설정, 소스·모델·GT·사진 해시 | **통과(모의 실행)** |
| 5 | 모델 실제 추론, 4정책 모자이크 이미지 20장 | **미검증(ultralytics 미설치)**; 기존 이미지는 총 80장 보존 |
| 6 | `policy_comparison.csv` 생성 단일화, 11컬럼 | **통과(소스·CSV 분석 시험)** |
| 7 | GT 중복, 검출 수, 처리 상태 불일치 검출 | **통과(오류 주입 시험)** |
| 8 | 두 번째 정책 검증 실패 시 분석 출력 전부 보존 | **통과(오류 주입 시험)** |
| 9 | `--strict` 및 비엄격 모드 | **통과** |
| 10 | 수기 검수 재실행 후 보존 | **통과** |
| 11 | 실험 ID가 다른 수동 검수 미결합 | **통과**; 모델·입력 해시 변경 후 수기 연결 차단 **미구현(아래 제한사항)** |
| 12 | 프로젝트 ZIP 및 문서 | **통과(파일 생성 점검)** |

별도 시험: 결과 반영 중 오류를 주입하고 이전 분석 CSV를 복원하는 롤백 시험 **통과**. 추론 실행 실패 이후 기존 결과로 복원하는 모의 시험 **통과**.

## 4. 변경하지 않은 자료

- `data/ground_truth.csv`, `data/images/`, `shared/models/`
- `source/main.py`, `source/main_1_baseline.py`
- 기존 `csv_backup/`에 저장된 수동 백업
- `outputs/first/`, `outputs/second-baseline/`

## 5. 제약 및 C 단계 권장 검사

1. **실제 추론 미실행:** Windows 가상환경에서 `python scripts/run_experiment.py --compare` 실행 후 4정책 20장과 분석표 생성 여부 확인.
2. **실험 식별:** 수기 검수는 `experiment_id`로 연결되며, 이미 저장된 ID에 대해 입력/모델 해시가 달라졌는지 자동 대조하는 기능은 현재 구현되지 않았습니다. 원본 수정 후에는 새 실험 ID로 실행하세요.
3. **직접 실행 우회:** `python source/main_1.py --compare`는 경고만 하며 백업 확인 절차를 우회할 수 있습니다. 공식 실행 관리자를 사용하세요.
4. **원자적 일괄 반영:** 파일별 스테이징과 오류 시 롤백으로 구현했습니다. 갑작스러운 전원 차단 등 프로세스 외부 중단까지 모든 CSV의 완전한 원자성을 보증하지는 않습니다.
5. **수동 검수:** 별도 CSV 수기 입력 방식입니다. 웹 UI는 제공하지 않습니다.
6. **백업 범위:** 이전 `outputs/experiments`의 파일 및 종합 결과만 보존합니다. 모델·원본 사진은 해시만 기록하므로 변경에 대비한 별도 원본 보관이 필요합니다.
7. **비엄격 분석:** 정책 일부가 없을 때 기존 `policy_comparison.csv`를 제거하지 않으며 `aggregate_status.csv`로 구식 가능성을 알립니다.

## 6. C 단계 사용자 확인 명령

```powershell
python scripts\run_experiment.py --compare
python scripts\build_deepsight_reports.py --root . --strict
python -m unittest discover -s tests -p test_d1_integration.py -v
python -m pytest tests/test_main_1.py -q
```

위 명령은 **현재 프로젝트 루트**에서 실행해야 합니다. 실제 운영 중 기존 실험을 보존하려면 첫 번째 명령에서 반드시 백업 Y를 선택하고 주석을 남기세요.
