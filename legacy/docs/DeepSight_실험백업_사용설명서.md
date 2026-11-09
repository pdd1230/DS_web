# DeepSight v2.1 — 실험 자동 백업·실행·복원 안내

## 안전한 기본 명령

프로젝트 루트(`K:\LSK\pjt_DeepSight_v2` 등)에서 가상환경 활성화 후:

```powershell
python scripts\run_experiment.py --compare
```

기존 결과가 있으면 **백업 Y/N** 질문이 나타납니다. `N` 또는 공백은 실행 취소. `Y`이면 이전 실험에 대한 주석을 작성하고, 4정책 결과 이미지/CSV 및 종합 결과를 백업·해시 확인한 뒤 새 실험 목적을 입력합니다. 백업 실패 시 추론을 시작하지 않습니다.

## 실제 백업 대상

- `outputs/experiments/` 하위의 현재 모든 파일
- `outputs/policy_comparison.csv`, `policy_test_cases.csv`, `data_validation.csv`, `aggregate_status.csv`, `experiment_run.json` 중 존재하는 파일
- **제외**: `outputs/first/`, `outputs/second-baseline/`, `data/images/`, `shared/models/`, `reviews/manual_review.csv`

## 백업 폴더

```text
csv_backup/YYYYMMDD_HHMMSS_고유ID/
├── outputs_snapshot/
│   ├── experiments/
│   │   ├── legacy/
│   │   ├── yolo_only/
│   │   ├── haar_only/
│   │   └── improved/
│   ├── policy_comparison.csv
│   └── ...
├── backup_manifest.json      # 파일 상대 경로·크기·SHA-256
├── experiment_note.md        # 사용자가 적은 이전 실험 설명
└── previous_settings.json    # 이전 실행 기록이 없으면 '미확인'
```

현재 실행 설정, 원본 사진/소스/모델 해시 등은 **성공한 새 실험**의 `outputs/experiment_run.json`에 기록됩니다. `previous_settings.json`은 이전 실행 자료가 확인되지 않을 때 현재 설정으로 값을 꾸며 넣지 않습니다.

## 복원 및 사고 대응

1. 공식 실행 도중 추론/분석 오류가 발생하고 이전 스냅샷이 있으면 프로그램이 자동 복원을 시도합니다.
2. 복원 실패 시 백업 폴더는 보존되므로 **다시 실험을 실행하지 말고**, 오류 로그와 백업 ID를 기록합니다.
3. **수동 복원은 실험 결과를 덮어쓰는 파괴적 작업입니다.** A 단계에서는 사용자 PC 전체 스냅샷을 직접 복원하는 시험을 완료하지 않았으므로, 수동 복원 명령을 일반 실행 방법으로 제공하지 않습니다. 별도 복사본에서 검증한 뒤 수행하세요.
4. 백업 무결성 수동 확인: `backup_manifest.json`의 `files[].path`에 대응하는 `outputs_snapshot` 파일을 읽어 SHA-256 해시를 다시 계산하여 비교합니다.
5. 오래된 백업은 임의 삭제하지 마세요. 특히 예전 `csv_backup/min_face_size=50  YOLO_CONFIDENCE=0.35/` 수동 백업도 별도 보존합니다.

## 실험을 비교할 때

- 각 실험마다 이전 설정·새 실험 목적·모델·신뢰도·최소 얼굴 크기·입력 해상도를 구분해 기록합니다.
- **하나의 변수만 바꾼 실험**은 원인 해석에 유리합니다.
- 모델 파일·원본 이미지·수기 정답표 자체는 스냅샷에 복사되지 않으므로 별도로 보존해야 동일 입력 조건을 장기 재현할 수 있습니다.
- `source/main_1.py --compare`를 직접 실행하면 사전 백업 확인을 우회할 수 있습니다. 공식 명령만 사용합니다.

## 정상/오류 메시지

| 표시 | 의미 | 조치 |
|---|---|---|
| `[기존 결과 발견]` | 이전 실험 존재 | Y/N 결정 |
| `[백업 완료]` | 파일 복사 및 해시 확인 | 새 실험 주석 입력 |
| `[취소]` | 백업 거부/설명 없음 | 결과 변경 없이 종료 |
| `[백업 실패]` | 백업 불가 | 출력 폴더 권한·공간 점검, 새 추론 금지 |
| `[검증 실패]` | CSV 불일치 | 해당 정책·파일의 원인 조사, 원본 수정은 신중히 |
| `[실험 실패]` | 추론 또는 분석 실패 | 자동 복원 결과 확인 |
