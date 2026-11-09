# 운영·백업·복원

## 실행 전

- Python 3.11.9, JDK17(java와 javac), MySQL 접속 정보를 확인한다.
- `config.ps1`의 DB 비밀번호와 자동 생성 내부 키를 사용한다.
- `scripts/check_environment.py`로 패키지와 모델 해시를 확인한다.
- 기본 포트 8080/8090을 다른 프로그램이 쓰면 config.ps1에서 변경한다.
- CPU 순차 처리이므로 실행 요청이 많으면 대기한다. 중복 클릭으로 새 요청 ID를 만들지 않는다.

## 로그와 상태

- Spring 기동 실패: `logs/spring.out.log`, `logs/spring.err.log`.
- Python 기동 실패: `logs/python.err.log`.
- 실제 추론/분석: 웹 ‘실험 상세’의 실행 로그와 `storage/runs/{id}/logs/`.
- `Access denied`: DB 계정·호스트·비밀번호·전용 DB 권한 확인.
- `Unknown database`: DB 생성 SQL을 먼저 실행.
- Flyway 스키마 오류: 기존 다른 프로젝트 테이블이 있는 DB에 임의로 연결하지 않았는지 확인. 기존 마이그레이션 파일을 운영 DB 생성 후 수정하지 않는다.
- `IMPORT_FAILED`: 실험 상세에서 DB 수집 복구. 추론을 반복할 필요가 없다.
- Python 재시작 중단: 실패 이유 확인 후 ‘설정 복제·새 실행’. 이전 완료 결과는 유지.

## 일관된 전체 백업

실험별 이력 보존은 같은 디스크의 기록이다. 디스크 고장에 대비하려면 DB와 파일을 함께 다른 장치로 복사한다.

1. 실행 중 작업이 끝났는지 확인한다.
2. `Stop.ps1`로 Spring·Python을 종료한다. MySQL은 실행 상태로 둔다.
3. MySQL의 `mysqldump`가 PATH에 있는 상태에서 다음을 실행한다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Backup.ps1 -Destination E:\DeepSightBackup\20261107
```

4. `database.sql`, `storage/`, `manifest.json`이 있는지 확인하고 별도 드라이브로 보관한다. 파일 수·해시도 확인한다.
5. 배포한 프로젝트 ZIP과 사용자 설정은 별도로 보관한다. `config.ps1`에는 비밀번호가 있으므로 전달 대상을 제한한다.
6. 백업 후 `Start.ps1`로 다시 시작한다.

백업 스크립트는 실패하면 성공 메시지를 출력하지 않는다. 실패 도중 만들어진 폴더는 불완전 백업으로 취급하고 다음 시도에 다른 폴더를 사용한다.

## 복원

운영 파일을 바로 덮어쓰기 전에 별도 위치와 새 DB에서 확인한다.

1. 앱을 중지하고 기존 DB와 storage를 별도 보존한다.
2. 같은 버전 프로젝트 ZIP을 새 위치에 풀고 Python 환경을 준비한다.
3. MySQL에 비어 있는 복원용 DB를 생성한다.
4. MySQL Workbench의 Server → Data Import에서 `database.sql`을 복원용 DB에 가져온다. CLI 사용 시 mysql의 `source` 명령으로 덤프를 실행할 수도 있다.
5. 백업의 storage 전체를 새 프로젝트 storage로 복사한다. 파일을 골라 일부만 옮기지 않는다.
6. manifest.json의 각 SHA256을 원본과 대조한다.
7. 새 config.ps1을 복원 DB에 연결하고 서버를 시작한다.
8. 과거 실험·원본·결과·검수·보고서 개정과 ZIP 다운로드를 확인한다.
9. 확인 후 실제 사용 경로와 DB를 전환한다.

추가로 Linux의 MySQL8.4.11에서 실제 덤프·별도 DB/파일 경로 복원·재조회가 통과했다. 사용자 Windows에서 Backup.ps1 전체를 실행한 것은 아니므로 실제 운영 전 위 절차를 사용자 PC에서 한 번 확인해야 한다.

백업 대상은 절대 경로로 정규화한다. storage 폴더 내부로의 백업은 재귀 복사를 방지하기 위해 거절한다. 매니페스트 경로는 백업 루트를 기준으로 한 상대 경로로 기록하며, 덤프 파일이 없거나 비어 있으면 성공 처리하지 않는다.

## 기존 프로젝트 자료

`legacy/`는 첨부 원본과 과거 출력의 보관본이다. 새로운 웹 실행은 이 폴더의 outputs에 쓰지 않는다. 과거 결과 가져오기는 원본 사진·정답 일치를 검사한다. 과거 `csv_backup/`에는 당시 사진과 정답·설정이 빠질 수 있어 새 성능 지표로 자동 재평가하지 않는다. 보고서 화면의 ‘기존 CLI 백업’에서 원본 목록·설명을 보고 무결성 검증 후 ZIP으로 받을 수 있다. 원본 백업을 계속 보관하고 자료 시점을 확인한 후 별도 데이터셋·실험으로 옮긴다.
