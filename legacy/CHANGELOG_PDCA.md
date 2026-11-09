# DeepSight PDCA D 단계 변경 기록 — 2026-11-05

## 원본 보존
- `source/main_1_baseline.py`에 이전 실행 버전 보존.
- `source/main.py` 초판 보존.
- 사용자 요청대로 `run.bat` 미포함 (삭제 조치 유지).

## 변경 파일
1. `source/main_1.py`: 모델별 후보 데이터(신뢰도·좌표·출처)와 후보 선택 근거 기록, `--compare`, `--policy` 옵션, 처리 실패/얼굴 없음 구분, 정답 평가 시 처리 실패 제외, 분리된 비교 폴더 출력 추가.
2. `requirements.txt`: 2026-11-05에 추가로 받은 UTF-16 LE 원본을 **버전 변경 없이** UTF-8로 변환.
3. `README.md`: 현재 실행법, CSV 정의, 미검증 사항, 개인정보 및 수동 검수 조건을 갱신.
4. `tests/test_main_1.py`: `img_012` 통합 정책·Haar fallback·누락값·실패 평가 등 자동 테스트 추가.
5. `PDCA_검토평가_20261105.md`: 실행 및 검증 결과 요약.

## 정책 설명
- `legacy`(기본값): 과거 방식 보존; 학습/비교를 위한 기준선.
- `yolo_only`: YOLO만 채택.
- `haar_only`: Haar만 채택.
- `improved`: YOLO 검출이 존재하면 비중복 Haar를 수동 검수 대상으로 보류하고 최종 박스에서 제외; YOLO 검출이 없으면 Haar 보완 채택하되 검토 필요 표시.
- `improved`는 **실험안**으로 현장 검증과 얼굴 위치 수동 라벨 확인 전에는 자동 채택하지 않음.

## 완료/보류
- 완료: Python 컴파일, 단위 테스트 6종, 20장 Haar 실처리 시험, 의존성 파일 인코딩 교정.
- 보류: Ultralytics가 없는 작업 환경에서 YOLO 실제 추론 및 4정책 동시 비교. 사용자의 Windows PC에서 검증해야 함.
- 보류: 모자이크 강도·패딩 조정의 육안 평가 및 얼굴 위치 라벨 기반 Precision/Recall.
