# DeepSight 정답표·정책 비교·오차분석 자동 생성 프로그램

## 목적
수기로 작성한 `data/ground_truth.csv`를 기준으로 `outputs/experiments/`에 저장된 네 정책의 `evaluation_results.csv`, `face_mosaic_results.csv`, `detection_details.csv`를 교차 검증하고, 정책별 테스트 결과와 종합 비교표를 생성합니다. **원본 정답표, 모델, 이미지, 기존 3종 CSV는 변경하지 않습니다.**

## 경로 구조
```text
pjt_DeepSight/
├─ data/
│  └─ ground_truth.csv                 # 수기 작성, 수정하지 않음
├─ scripts/
│  └─ build_deepsight_reports.py      # 제공 스크립트를 여기에 저장
└─ outputs/
   ├─ experiments/
   │  ├─ legacy/
   │  │  ├─ detection_details.csv
   │  │  ├─ face_mosaic_results.csv
   │  │  ├─ evaluation_results.csv
   │  │  ├─ test_cases.csv           # 새로 생성
   │  │  └─ test_cases_detailed.csv  # 새로 생성
   │  ├─ yolo_only/ (위와 동일)
   │  ├─ haar_only/ (위와 동일)
   │  └─ improved/ (위와 동일)
   ├─ policy_comparison.csv            # 네 정책이 모두 있으면 생성
   └─ policy_test_cases.csv            # 이미지별 네 정책 결과 비교
```

## 실행
프로젝트 루트에서 가상환경 활성화 후:
```powershell
python scripts\build_deepsight_reports.py --root . --strict
```
정책 파일이 일부만 있으면 `--strict`를 빼면 해당 정책만 처리하고, **4개 정책의 종합 비교표는 생성하지 않습니다.**

## 파일별 역할
- `ground_truth.csv`: 사람이 직접 기록한 `파일명`, `실제 얼굴 수`, `scene`, `note`. **유일한 정답 기준**.
- `detection_details.csv`: 모델별 후보, 채택 여부, 제외 이유, 검수 필요 여부. 원인 분석의 단서이나 실제 누락 얼굴의 위치를 보장하지 않음.
- `face_mosaic_results.csv`: 최종 채택 얼굴 좌표(한 얼굴당 한 행). 얼굴 없음을 나타내는 `no_face_detected` 행은 0개로 계산.
- `evaluation_results.csv`: 이미지별 정답 수/검출 수/Exact Match·Over-detection·Under-detection 및 처리 상태.
- `test_cases.csv`: 기존 T01~T06 빈 양식의 **7개 컬럼을 유지**하고 실제 이미지 수만큼 T001, T002...를 생성. `PASS`는 개수 일치, `FAIL`은 개수 불일치 또는 미평가.
- `test_cases_detailed.csv`: 위 7개 컬럼에 정책명, 수치 오차, 처리 상태, 촬영 조건, 후보 요약 등을 추가.
- `policy_comparison.csv`: 정책별 이미지 수, 평가 가능 수, 일치/과검출/미검출/실패, 일치율, 절대 개수 오차 합계.
- `policy_test_cases.csv`: 한 이미지에서 4개 정책 예측 수와 오차를 한 줄에 배치.

## 유의 사항
1. `test_cases.csv`는 기존 파일 이름으로 **다시 생성되어 덮어써집니다**. 원본 수기 작성 양식 또는 기존 수정 파일이 있다면 백업하세요.
2. 평가의 `Exact Match`는 **이미지 내 얼굴 개수 일치**만 뜻하며, 검출 박스와 실제 얼굴의 1:1 대응 또는 비식별화 성공을 검증하지 않습니다. `img_020.jpg`와 같은 미검출 사례는 원본과 결과 이미지를 육안 비교해야 합니다.
3. 네 정책을 비교하려면 **같은 입력 사진, 같은 GT, 같은 모델/실행 조건**을 사용해야 합니다. 특히 정책 외에 신뢰도·입력 해상도 등이 바뀌면 정책 효과만 비교한 것이 아닙니다.
4. 파일명 불일치, 중복, 정답 불일치, 세 결과 CSV의 검출 개수 모순이 발견되면 조용히 보정하지 않고 오류로 중지합니다.
5. 원본 CSV 중 일부에 `ground_truth`와 다른 처리 상태가 포함되어 있다면 해당 입력 데이터부터 점검하세요.
