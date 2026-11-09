# DeepSight v2.1 — CSV 규격 및 검증 명세

## 데이터 흐름

`data/ground_truth.csv`(사람이 작성) → `source/main_1.py`(얼굴 검출 및 4종 정책 결과) → `scripts/build_deepsight_reports.py`(검증·자동 오차분석) → 정책별/종합 CSV.

`source/main.py`의 결과는 `outputs/first/`, `source/main_1_baseline.py`의 결과는 `outputs/second-baseline/`에 별도로 저장합니다. 두 폴더의 결과는 4정책 보고서의 직접 입력이 아닙니다.

## 입력과 생성 파일

| 파일 | 위치 | 담당/내용 | 필수 컬럼 |
|---|---|---|---|
| `ground_truth.csv` | `data/` | 수기 정답, 읽기 전용 | `파일명`, `실제 얼굴 수`; 선택 `scene`, `note` |
| `detection_details.csv` | `outputs/experiments/{정책}/` | 추론·후보 상세 | `image_name`, `detector`, `selected`, `review_required` (기타 좌표·사유 포함) |
| `face_mosaic_results.csv` | 위와 동일 | 최종 검출 얼굴별 좌표 또는 `no_face_detected` | `image_name`, `status`, `x`, `y`, `w`, `h` |
| `processing_status.csv` | 위와 동일 | 사진별 처리 상태 및 검출 수 | `image_name`, `processing_status`, `detected_count`, `error_message`, `manual_review_required` |
| `evaluation_results.csv` | 위와 동일 | 수기 정답과 검출 얼굴 개수 비교 | `filename`, `ground_truth`, `detected`, `evaluation`, `processing_status` |
| `test_cases.csv` | 위와 동일 | 자동 평가 기본표, 기존 **7개 컬럼 유지** | `test_id`, `scenario`, `expected_behavior`, `input_filename`, `actual_result`, `pass_fail`, `note` |
| `test_cases_detailed.csv` | 위와 동일 | 상세 오차·처리 상태·수동 검수 연결 | 7개 기본 컬럼 + `policy`, `ground_truth`, `detected`, `error`, `evaluation`, `processing_status`, `scene`, `gt_note`, `manual_review_required`, `candidate_summary`, `review_status`, `review_result`, `missing_faces`, `false_faces`, `mosaic_quality`, `review_note` |
| `data_validation.csv` | `outputs/` | 정책별 데이터 일관성 검사 결과 | `policy`, `filename`, `check_item`, `result`, `message` |
| `policy_comparison.csv` | `outputs/` | 4정책 종합 성능, 분석 전담 | `policy`, `total`, `evaluated`, `exact`, `over`, `under`, `failed`, `exact_match_pct`, `gt_total_faces`, `detected_total_faces`, `absolute_count_error` |
| `policy_test_cases.csv` | `outputs/` | 사진별 4정책 예측 및 오차 비교 | `policy`, `filename`, `ground_truth`, `scene`, `gt_note` 및 각 정책별 예측/오차 |
| `aggregate_status.csv` | `outputs/` | 일부 정책만 존재할 때 종합표 구식 가능성 표시 | `status`, `message` |
| `manual_review.csv` | `reviews/` | 사용자 수동 검수, **분석 프로그램은 읽기 전용** | `experiment_id`, `policy`, `filename`, `review_status`, `review_result`, `missing_faces`, `false_faces`, `mosaic_quality`, `review_note` |

## 주요 판정

- `Exact Match` / `PASS`: 한 사진의 **얼굴 개수**가 수기 정답과 동일. 얼굴 좌표 정답률이나 완전한 비식별화 보증이 아님.
- `Over-detection`/`Under-detection`: 예측 얼굴 수가 실제 얼굴 수보다 많거나 적음.
- `processed_no_face`: 파일 정상 처리, 선택한 얼굴 0개. 이는 정답이 0개라는 의미가 아님.
- `review_status`: 수동 검수 여부로, `manual_review_required`(검토 요청 필요 표시)와 구분해야 함.
- 정책은 `legacy`, `yolo_only`, `haar_only`, `improved`의 네 가지로 유지함.

## 데이터 일관성 검사

1. 정답 파일명 중복·누락·음수 얼굴 수 검사 및 평가/상태 파일명 일치 확인.
2. 평가 CSV와 처리 상태 CSV의 상태 일치 확인.
3. 최종 검출 수 = 최종 얼굴 좌표 행 수 = 선택된 후보 수 = 처리 상태 기록의 검출 수 확인.
4. 얼굴 0개 행, 정상 처리 시 오류 메시지, 실패 상태의 결과 잔존 여부 확인.
5. 검증 실패 시 기존 분석 보고서 갱신하지 않고 오류 보고. 파일별 단계적 반영 및 오류 시 복구를 사용하나 전원 장애까지 완전 원자성을 보증하지 않음.
6. `--strict`: 4개 정책 필수. `--strict` 없으면 없는 정책 건너뛰고, 종합표를 새로 만들지 않으며 `aggregate_status.csv`로 오래된 종합표 가능성을 알림.

## 생성 주체 및 보존 규칙

- `main_1.py`: 4종 추론 CSV 및 결과 이미지 생성. **종합 정책 비교표를 생성하지 않음**.
- `build_deepsight_reports.py`: `test_cases.csv`, `test_cases_detailed.csv`, `data_validation.csv`, `policy_comparison.csv`, `policy_test_cases.csv` 생성.
- 정답표·원본 사진·모델·기존 추론 CSV·수동 검수 파일은 분석기가 수정하지 않음.
- 자동 보고서 파일은 실행 시 갱신될 수 있으므로 이전 실행 결과는 공식 실험 관리자를 통해 사전 백업.
- CSV는 기본적으로 UTF-8 BOM 형식으로 생성됨(스프레드시트 호환 목적).
