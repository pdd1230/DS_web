# DeepSight Web 1.0 — Spring Boot 4 + Python 얼굴 모자이크 실험실

기존 Python 프로젝트의 사진·정답표 → 이전 결과 보존 → 프로그램 실행 → 정책 비교 
→ 오답 분석 → 수동 검수 → 보고서 개정 과정을 웹으로 옮긴 소스 프로젝트입니다.

**JDK 17 / Spring Boot 4.0.9 / Gradle Wrapper 8.14.3 / Python 3.11.9 / MySQL**을 사용합니다. 
모델·기준 사진 20장·기존 Python 원본을 `legacy/`에 포함했습니다. 
웹캠·동영상·새 모델 학습·에이전트·외부 공개는 이번 범위에 포함하지 않습니다.

## 1. 처음 실행하기 — Windows PowerShell

ZIP을 풀어 다음 위치에 둔 경우입니다. 다른 드라이브도 사용할 수 있습니다.

```powershell
cd K:\LSK\DeepSight_Web
java -version
javac -version
py -3.11 --version
```

Java와 javac가 JDK 17인지, Python이 3.11.9인지 확인합니다. 
PC의 `JAVA_HOME`과 PATH는 JDK 17을 가리켜야 합니다. Gradle을 별도로 설치할 필요는 없습니다.

### 1-1. Python 가상환경·의존성 준비

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Setup.ps1
```

이 작업은 **이 프로젝트 전용** `.venv`와 `config.ps1`을 만듭니다. 
CPU용 PyTorch를 설치하므로 처음에는 다운로드 시간이 필요합니다. 
기존 다른 프로젝트의 가상환경이나 패키지를 제거하지 않습니다. `legacy/requirements.txt`의 
과거 전체 패키지 목록은 웹 프로젝트 설치에 사용하지 않습니다.

### 1-2. MySQL 준비

기존 MySQL 서버가 실행 중이어야 합니다. 관리자 계정으로 `sql/01_create_database.sql`을 실행해 
새 전용 DB와 계정을 준비합니다. SQL의 `CHANGE_ME`를 원하는 비밀번호로 먼저 수정하세요. 
기존 LOOK·DeepSight DB를 재사용하지 않는 구성이 기본입니다.

`config.ps1`을 열어 아래 내용을 실제 계정에 맞춥니다.

```powershell
$env:DS_DB_HOST = '127.0.0.1'
$env:DS_DB_PORT = '3306'
$env:DS_DB_NAME = 'deepsight_web'
$env:DS_DB_USER = 'deepsight'
$env:DS_DB_PASSWORD = '실제 비밀번호'
```

자동 생성된 `DS_API_KEY`는 Spring과 Python이 함께 사용하는 내부 통신 키입니다. 그대로 두세요. 
config.ps1에는 로컬 비밀번호가 들어가므로 배포용 ZIP에는 포함하지 않습니다.

**DB 자체는 SQL로 미리 생성합니다. 애플리케이션 테이블은 첫 서버 시작 시 Flyway가 자동 생성하고, 
이후에는 Hibernate가 스키마를 검증합니다.**

### 1-3. 서버 시작 — 명령 한 번

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Start.ps1
```

Gradle 빌드 → Python 준비 확인 → Spring 시작 → 브라우저 열기를 수행합니다.

- 접속: **http://127.0.0.1:8080**
- Python 내부 API: 127.0.0.1:8090
- DB: config.ps1 지정 MySQL
- 로그: `logs/python.*.log`, `logs/spring.*.log`

화면이 열려도 모델이나 DB가 정상인지 **환경 점검** 버튼으로 확인하세요. 기본 접속 범위는 같은 PC입니다. 
교실 다른 PC 접속과 외부 공개는 별도 인증·접근 범위를 정한 뒤 확장합니다.

```powershell
# 상태 확인
powershell -ExecutionPolicy Bypass -File .\scripts\Status.ps1
# 종료 (MySQL 서비스는 종료하지 않음)
powershell -ExecutionPolicy Bypass -File .\scripts\Stop.ps1
```

## 2. 첫 실험 — 기준 사진으로 실제 확인

1. **사진·정답표** → **첨부 기준 사진 20장 등록**을 누릅니다.
2. 사진과 정답표가 검증되어 등록되는지 확인합니다.
3. **프로그램 실행** → ‘4정책 비교’를 선택합니다.
4. 데이터셋을 선택하고 실험 이름·목적·보존 설명을 입력합니다. 처음에는 기본 설정을 그대로 사용합니다.
5. 이전 결과 보존 확인을 체크하고 **실제 프로그램 실행**을 누릅니다.
6. 대기 → 실행 → DB 수집 → `COMPLETED`와 실행 로그를 확인합니다.
7. **이미지·결과 비교**에서 `img_001.jpg` 등 사진과 정책을 선택합니다. 이미지를 누르면 확대됩니다.
8. **오답 분석**에서 과다·과소·실패·미검수 조건을 선택합니다.
9. **수동 검수**에서 누락·오탐·품질·의견을 저장합니다.
10. **분석만 재실행** 후 보고서가 r1 → r2로 바뀌고 r1도 남아 있는지 확인합니다.
11. **보고서·보존 자료**에서 CSV·이미지·검증 자료·ZIP을 받습니다.
12. 서버를 종료했다가 다시 켜서 같은 실험을 조회합니다.

1장만 시험하려면 기준 사진 중 한 장을 골라 새 데이터셋으로 올리고, 그 파일에 해당하는 정답 행만 들어 있는 CSV를 함께 등록하세요.
모든 사진은 정답표와 정확히 1:1로 대응해야 합니다.

```csv
파일명,실제 얼굴 수,scene,note
img_001.jpg,1,측면,밝은 조명
```

## 3. 실행할 수 있는 프로그램

| 화면의 선택 | 실제 처리 | 결과 |
|---|---|---|
| 초기 Haar | `legacy/source/main.py`를 작업 경로에 연결해 호출 | 기존 모자이크 이미지 + 웹 보조 평가 |
| YOLO+Haar 기준 | `legacy/source/main_1_baseline.py` 호출 | 기준 이미지·좌표·평가 CSV |
| 4정책 비교 | 기존 `main_1.py`의 `run()` + 기존 분석기 | 정책별 이미지·추론 CSV·종합 보고서 |
| 분석만 재실행 | 기존 `build_deepsight_reports.py`의 `analyze()` | 검수 반영한 새 보고서 개정 |
| 첨부 과거 결과 가져오기 | 첨부 출력 복사·검증·보고서 등록 | ‘과거 자료·설정 미확인’으로 구분 |

4정책 웹 실행은 대화형 `run_experiment.py`에 터미널 입력을 흘려보내지 않습니다. 
그 절차를 웹의 보존 확인·설명·해시 검증·격리 작업 공간으로 옮기고, 추론·분석 코드는 직접 재사용합니다. 기존 CLI는 `legacy/`에 그대로 보관했습니다.

초기 `main.py`는 좌표 CSV를 만들지 않습니다. 웹은 원본 프로그램 로그에서 얼굴 수를 가져오며 
**없는 좌표나 신뢰도를 만들어 넣지 않습니다.** 초기 과거 출력에 개수 기록이 없으면 이미지 조회만 제공하고 예측은 ‘평가 불가’로 표시합니다.

과거 결과 가져오기는 첨부 기준 사진·정답표를 등록한 데이터셋에서 사용하세요. 
모델·현재 설정을 과거 실행 당시 정보처럼 표시하지 않습니다. `legacy/csv_backup/`의 기존 스냅샷은 
원본 자료로 보관하며 웹 실험으로 자동 재평가하지 않습니다. 백업에는 당시 사진·정답이 함께 없을 수 있기 때문입니다.

## 4. 프로젝트 구조

```text
DeepSight_Web/
  README.md
  config.ps1.example
  legacy/                    기존 원본·사진·모델·과거 출력
  python_service/
    app.py                   인증·작업 대기열·상태 API
    runner.py                원본 프로그램 연동·결과 정규화·개정 게시
    core.py                  경로·해시·CSV·사진/정답 검증
    requirements.txt
    tests/
  web/
    build.gradle
    gradlew.bat / gradlew
    gradle/wrapper/          Wrapper JAR 포함
    src/main/java/kr/deepsight/
    src/main/resources/
      templates/index.html
      static/app.js, app.css
      db/migration/V1__initial.sql
    src/test/java/kr/deepsight/WorkflowTest.java
  scripts/                   설치·시작·종료·점검·백업
  sql/01_create_database.sql
  docs/                      설계·검증·운영 문서
```

`storage/`, `logs/`, `.venv/`, `config.ps1`, Gradle 캐시와 빌드 산출물은 실행 후 생깁니다. 
ZIP에는 포함하지 않습니다. 첫 빌드는 Gradle·Maven 의존성을 다운로드합니다.

## 5. 저장·정답·실험 보존 규칙

- 데이터셋은 저장될 때 확정된 **버전 하나**입니다. 정답표를 수정하면 새 데이터셋 행과 파일 사본을 만듭니다.
- 실험마다 UUID를 발급하고 입력 사진·정답을 복사합니다.
- 이전 완료 보고서의 파일 크기·해시를 검증하고 새 실험에 보존 설명과 참조 매니페스트를 남깁니다.
- 같은 요청 ID를 다시 보내면 같은 실험을 반환해 중복 실행을 방지합니다.
- CPU 작업자는 한 개입니다. 작업마다 별도 Python 프로세스를 실행하므로 원본 코드의 전역 경로·설정이 다른 실험과 섞이지 않습니다. 모델은 실험마다 한 번 로드합니다.
- 보고서는 `runs/{실험ID}/reports/r0001`, `r0002`처럼 보관합니다. 새 보고서 게시가 실패해도 이전 완료 결과는 남습니다.
- DB 저장이 실패한 작업은 `IMPORT_FAILED`로 표시합니다. **DB 수집 복구**를 누르면 기존 Python 완료 산출물을 다시 수집합니다.
- Python 재시작으로 중단된 작업은 실패로 기록하고 로그를 보존합니다. 추론 재시도는 **설정 복제·새 실행**으로 새 실험을 만듭니다.
- 실패 시 검출 수를 0으로 바꾸지 않습니다. 정상 처리된 얼굴 0개와 처리 실패는 다릅니다.

## 6. 수동 기동 — 문제를 분리해서 확인할 때

두 PowerShell 창에서 각각 프로젝트 루트로 이동합니다. 창마다 환경을 불러와야 합니다.

```powershell
# 창 1: Python
. .\scripts\Environment.ps1
& $PythonExe -m uvicorn app:app --app-dir .\python_service --host 127.0.0.1 --port $env:DS_PYTHON_PORT
```

```powershell
# 창 2: Spring Boot
. .\scripts\Environment.ps1
cd web
.\gradlew.bat bootRun
```

## 7. 테스트와 검증 범위

추가 확인에서 **실제 MySQL8.4.11의 생성·저장·재시작 조회·별도 DB 복원**이 Linux 환경에서 통과했습니다. 
Windows 실행 여부와 구분한 세부 결과는 **docs/VALIDATION.md**를 보세요. 
테스트가 통과했다고 사용자 PC의 Windows·MySQL에서도 확인을 마쳤다는 뜻은 아닙니다.

```powershell
# Python 계약 테스트 및 기존 원본 테스트
.\python_service\.venv\Scripts\python.exe -m pip install -r .\python_service\requirements-test.txt
.\python_service\.venv\Scripts\python.exe -m pytest .\python_service\tests -q
.\python_service\.venv\Scripts\python.exe -m pytest .\legacy\tests -q
# Java 기동·스키마 테스트 (테스트 DB만 H2)
cd web
.\gradlew.bat test
```

실제 운영은 MySQL 설정만 사용합니다. MySQL 연결 실패 시 H2로 바꿔 실행하지 않습니다.

## 8. 문서

- `docs/ARCHITECTURE.md`: 구성·통신·저장·오류 복구
- `docs/TABLES.md`: 구현 테이블 정의
- `docs/VALIDATION.md`: 실제 통과·미확인 항목
- `docs/PDCA_RESULT.md`: 단계별 산출물과 남은 검증
- `docs/OPERATIONS.md`: 백업·복원·장애 조치
- `docs/PLAN.md`: 승인 기준이 된 원래 계획

얼굴 개수 일치는 완전한 비식별화 보증이 아닙니다. 원본과 결과를 직접 비교하고 누락·오탐·모자이크 품질을 기록하세요.

### 통합 테스트 재현

```powershell
# 테스트용 Python 포트 8091과 H2 DB로 실제 모델까지 실행
powershell -ExecutionPolicy Bypass -File .\scripts\Test.ps1 -Full
```

이 테스트는 프로젝트의 `build-verification/storage`에 데이터를 만듭니다. 
운영 MySQL과 운영 storage를 변경하지 않습니다. 실제 모델을 사용하므로 일반 단위 테스트보다 오래 걸립니다.
