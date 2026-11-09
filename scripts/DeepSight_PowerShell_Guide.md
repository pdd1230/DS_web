# DeepSight PowerShell 스크립트 간단 안내

7개 스크립트는 프로젝트의 환경 준비, 서버 시작·확인·종료, 백업을 담당합니다. 파일은 프로젝트의 `scripts` 폴더에 두고, 아래 명령은 **프로젝트 루트 폴더의 PowerShell**에서 실행합니다.

## 1. 프로그램별 역할

| 파일 | 주요 역할 | 사용 시점 |
|---|---|---|
| `Setup.ps1` | 설정 파일과 API 키를 최초 생성하고, Python 3.11.9 가상환경·CPU용 PyTorch·필수 패키지를 준비 | 최초 설치 또는 환경 재설정 |
| `Environment.ps1` | `config.ps1`을 읽고 공통 경로·환경 변수·서버 주소를 설정하며 `logs`, `storage` 폴더를 준비 | 다른 스크립트에서 자동 호출 |
| `Start.ps1` | 설정·환경·포트·JAR·DB TCP 연결을 확인하고 Python → Spring Boot 순서로 실행 | 서버 시작 |
| `Status.ps1` | Spring Boot의 `/api/health`를 호출하고 응답을 JSON으로 표시 | 실행 상태 확인 |
| `Stop.ps1` | 기록된 PID와 시작 시각을 확인하고 서버 및 조건에 맞는 직계 자식 프로세스를 종료 | 서버 종료 |
| `Backup.ps1` | MySQL을 `database.sql`로 내보내고 `storage`를 복사한 뒤 파일별 SHA256 목록을 생성 | 서버 종료 후 백업 |
| `Test.ps1` | 테스트 의존성 설치 후 Python pytest와 Gradle Java 테스트 실행. `-Full`이면 테스트용 Python 서버도 실행 | 기능 검증 |

**최신 Test.ps1 반영:** 기본 실행은 Python·Java 테스트를 수행합니다. `-Full` 실행은 8091 포트에 테스트용 Python 서버를 시작한 뒤 Java 테스트를 수행하고 서버를 정리합니다. 일반 서비스 시작은 `Start.ps1`을 사용합니다.

## 2. 기본 실행 순서

### ① 최초 환경 준비

```powershell
.\scripts\Setup.ps1
```

이후 `config.ps1`의 DB 접속 정보를 수정하고, `sql\01_create_database.sql`을 최초 1회 실행합니다. IntelliJ에서 `bootJar`를 실행하여 다음 JAR도 준비합니다.

```text
web\build\libs\deepsight-web-1.0.0.jar
```

### ② 서버 시작

```powershell
.\scripts\Start.ps1
```

Python의 `/health` 응답과 모델 존재 여부를 확인한 뒤 Spring Boot를 실행합니다. Spring Boot의 `/api/datasets` 응답까지 확인되면 접속 주소를 출력하고 브라우저를 엽니다.

### ③ 상태 확인

```powershell
.\scripts\Status.ps1
```

### ④ 서버 종료

```powershell
.\scripts\Stop.ps1
```

MySQL 서비스는 종료하지 않습니다.

### ⑤ 백업

```powershell
.\scripts\Backup.ps1
```

기본 저장 위치는 `backups\yyyyMMdd_HHmmss`입니다. 백업 폴더에는 `database.sql`, `storage` 폴더, `manifest.json`이 생성됩니다. `mysqldump` 명령을 사용할 수 있어야 하며, MySQL 서버는 실행 중이어야 합니다.

## 3. 테스트 실행

```powershell
.\scripts\Test.ps1
.\scripts\Test.ps1 -Full
```

Python 테스트 성공 후 Java 테스트를 실행합니다. Java 테스트에는 `web\gradlew.bat`을 사용하므로 Gradle 실행이 가능한 환경이 필요합니다. `-Full`은 8091 포트가 비어 있어야 하며, 테스트용 저장 경로는 `build-verification\storage`입니다.

- 테스트 서버 로그: `logs\test-python.out.log`, `logs\test-python.err.log`
- 마지막 안내에는 H2 사용이라고 표시되지만, 실제 DB 격리는 테스트 설정과 소스 확인이 필요합니다.
- `-Full`에서 변경한 API 키·저장 경로 등의 환경 변수는 스크립트 종료 후 자동 복원되지 않습니다.

## 4. 선택 옵션

| 명령 | 의미 |
|---|---|
| `.\scripts\Setup.ps1 -SkipPackages` | 패키지 설치와 의존성 검사를 생략하고 나머지 환경 준비 수행 |
| `.\scripts\Start.ps1 -NoBrowser` | 서버를 시작하되 브라우저 자동 열기 생략 |
| `.\scripts\Backup.ps1 -Destination 'E:\DeepSight_Backup_01'` | 지정한 새 폴더에 백업. 기존 폴더나 `storage` 내부 경로는 사용할 수 없음 |

## 5. 주요 로그와 확인 사항

| 파일 | 내용 |
|---|---|
| `logs\python.out.log`, `logs\python.err.log` | Python 서버의 표준 출력·오류 |
| `logs\spring.out.log`, `logs\spring.err.log` | Spring Boot의 표준 출력·오류 |
| `logs\processes.json` | 종료 처리에 사용하는 서버 PID·시작 시각 |

- `Start.ps1`은 Gradle 빌드를 수행하지 않으므로 소스 변경 후에는 JAR를 다시 빌드해야 합니다.
- 시작 전 DB 검사는 TCP 연결 확인이며, 계정·비밀번호·테이블의 정상 여부를 모두 검증하는 것은 아닙니다.
- `Status.ps1`은 Spring Boot에 요청하며 Python 서버를 직접 검사하지 않습니다.
- 이 문서는 소스 확인을 기준으로 작성했습니다. 실제 Windows 실행 검증은 수행하지 않았습니다.
