<#
.SYNOPSIS
    DeepSight의 MySQL 데이터와 storage 폴더를 백업합니다.
.DESCRIPTION
    기록된 서버 PID가 실행 중인지 확인하고 DB 덤프와 파일 복사를 수행합니다.
    백업 파일별 SHA256 해시를 manifest.json에 기록합니다.
.PARAMETER Destination
    백업할 새 폴더 경로입니다. 생략하면 프로젝트의 backups 아래에 생성합니다.
.EXAMPLE
    .\scripts\Backup.ps1
.EXAMPLE
    .\scripts\Backup.ps1 -Destination 'E:\DeepSight_Backup_01'
.NOTES
    mysqldump 명령을 실행할 수 있어야 합니다.
    먼저 Stop.ps1로 DeepSight를 종료해야 하며 MySQL 서버는 실행 중이어야 합니다.
    오류 발생 시 생성된 백업 폴더는 자동 삭제되지 않습니다.
#>

param(
 [string]$Destination = ''
)

# ============================================================
# 1. 공통 설정 적용 및 서버 실행 여부 확인
# ============================================================
. (Join-Path $PSScriptRoot 'Environment.ps1')
$StateFile = Join-Path $ProjectRoot 'logs\processes.json'

# 기록된 PID가 하나라도 실행 중이면 백업을 중단합니다.
# 여기서는 시작 시각 비교나 기록되지 않은 서버 프로세스 검색은 하지 않습니다.
if (Test-Path $StateFile) {
 $Entries = Get-Content -Raw $StateFile | ConvertFrom-Json

 foreach ($Entry in $Entries) {
  if (Get-Process -Id $Entry.id -ErrorAction SilentlyContinue) {
   throw 'Stop DeepSight before backup to keep DB and files consistent.'
  }
 }
}

# ============================================================
# 2. 백업 경로 결정 및 검사
# ============================================================
# 경로를 생략하면 실행 시각으로 새 백업 폴더 이름을 만듭니다.
if (!$Destination) {
 $Destination = Join-Path $ProjectRoot ('backups\' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
}

# 절대 경로로 변환하고 끝의 경로 구분자를 제거하여 비교합니다.
$Destination = [System.IO.Path]::GetFullPath($Destination).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
$StorageRoot = [System.IO.Path]::GetFullPath($env:DS_STORAGE).TrimEnd([System.IO.Path]::DirectorySeparatorChar)

# storage 자신이나 그 내부로 백업하여 자기 자신을 복사하는 상황을 방지합니다.
if ($Destination.Equals($StorageRoot, [System.StringComparison]::OrdinalIgnoreCase) -or $Destination.StartsWith($StorageRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
 throw 'Backup destination must be outside storage.'
}

# 기존 폴더에 덮어쓰지 않고 새 폴더만 사용합니다.
if (Test-Path $Destination) {
 throw 'Destination already exists.'
}

New-Item -ItemType Directory $Destination | Out-Null

# ============================================================
# 3. MySQL 데이터 덤프
# ============================================================
# 기존 MYSQL_PWD 값을 보관했다가 작업 종료 시 복원합니다.
$OldPassword = $env:MYSQL_PWD

try {
 # mysqldump가 환경 변수에서 접속 비밀번호를 읽도록 설정합니다.
 $env:MYSQL_PWD = $env:DS_DB_PASSWORD

 # DB를 database.sql에 기록합니다.
 # --single-transaction: InnoDB 등 트랜잭션 지원 테이블의 일관된 덤프에 사용합니다.
 # --no-tablespaces: 테이블스페이스 정보를 제외합니다.
 # --set-gtid-purged=OFF: GTID_PURGED 설정을 덤프에 추가하지 않습니다.
 # --default-character-set=utf8mb4: 덤프 연결의 문자 집합을 지정합니다.
 # --result-file: PowerShell의 출력 리디렉션 대신 mysqldump가 파일에 직접 씁니다.
 & mysqldump --host=$env:DS_DB_HOST --port=$env:DS_DB_PORT --user=$env:DS_DB_USER --single-transaction --no-tablespaces --set-gtid-purged=OFF --default-character-set=utf8mb4 ('--result-file=' + (Join-Path $Destination 'database.sql')) $env:DS_DB_NAME

 # 외부 프로그램은 종료 코드로 성공 여부를 별도 확인합니다.
 if ($LASTEXITCODE) {
  throw 'mysqldump failed; this backup is incomplete.'
 }

 # 덤프 파일이 없거나 비어 있으면 불완전한 백업으로 처리합니다.
 if (!(Test-Path (Join-Path $Destination 'database.sql')) -or (Get-Item (Join-Path $Destination 'database.sql')).Length -eq 0) {
  throw 'Database dump is empty; this backup is incomplete.'
 }

 # ========================================================
 # 4. 저장 파일 복사 및 해시 목록 생성
 # ========================================================
 Copy-Item -Recurse $env:DS_STORAGE (Join-Path $Destination 'storage')

 # 파일별 상대 경로와 SHA256 값을 기록합니다.
 # manifest.json을 쓰기 전에 목록을 수집하므로 목록 파일 자신의 해시는 포함되지 않습니다.
 Get-ChildItem -Recurse -File $Destination |
         ForEach-Object {
          [pscustomobject]@{
           Path = $_.FullName.Substring($Destination.Length + 1)
           SHA256 = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
          }
         } |
         ConvertTo-Json |
         Set-Content -Encoding UTF8 (Join-Path $Destination 'manifest.json')

 Write-Host "Backup complete: $Destination. Copy it to a separate drive."
}
finally {
 # 성공·실패 여부에 관계없이 기존 비밀번호 환경 변수 값을 복원합니다.
 $env:MYSQL_PWD = $OldPassword
}
