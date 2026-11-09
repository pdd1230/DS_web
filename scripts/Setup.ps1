<#
.SYNOPSIS
    DeepSight 프로젝트의 Python 실행 환경을 준비합니다.

.DESCRIPTION
    1. 프로젝트 루트 폴더로 이동
    2. 최초 실행 시 config.ps1 생성 및 API 키 추가
    3. Python 3.11.9 버전 확인
    4. Python 가상환경 생성
    5. CPU용 PyTorch 및 프로젝트 패키지 설치·검사

    이 스크립트는 DB 생성이나 서버 실행을 수행하지 않습니다.

.PARAMETER SkipPackages
    패키지 설치와 의존성 검사를 생략합니다.
    설정 파일 준비, Python 버전 확인, 가상환경 생성은 수행합니다.

.EXAMPLE
    .\scripts\Setup.ps1

.EXAMPLE
    .\scripts\Setup.ps1 -SkipPackages

.NOTES
    파일 위치: 프로젝트 루트\scripts\Setup.ps1
    사전 준비: Python 3.11.9 및 Python Launcher(py)
#>

param(
 [switch]$SkipPackages
)

# ============================================================
# 1. 기본 설정 및 작업 폴더 지정
# ============================================================

# PowerShell 명령에서 오류가 발생하면 스크립트를 중단합니다.
# 외부 프로그램(py, pip)의 실패 여부는 $LASTEXITCODE로 별도 확인합니다.
$ErrorActionPreference = 'Stop'

# $PSScriptRoot는 현재 스크립트가 있는 scripts 폴더입니다.
# 그 상위 폴더를 프로젝트 루트로 사용합니다.
$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $ProjectRoot

# ============================================================
# 2. 최초 실행 시 설정 파일 생성
# ============================================================

# 기존 config.ps1이 있으면 설정과 API 키를 그대로 유지합니다.
if (!(Test-Path 'config.ps1')) {
 Copy-Item config.ps1.example config.ps1

 # GUID 2개를 연결하여 64자리 API 키 문자열을 만듭니다.
 $secret = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')

 # 생성한 키를 설정 파일 끝에 추가합니다.
 # `$env의 백틱은 변수 확장을 막아 "$env:DS_API_KEY"를 글자로 기록합니다.
 Add-Content -Encoding UTF8 config.ps1 ("`n`$env:DS_API_KEY = '" + $secret + "'")
}

# ============================================================
# 3. Python 버전 확인
# ============================================================

# Python Launcher로 Python 3.11을 실행하고 정확한 버전을 확인합니다.
$version = & py -3.11 -c 'import platform; print(platform.python_version())'

# 원본과 동일하게 Python 3.11.9만 허용합니다.
# 설치된 Python 목록과 경로는 py -0p 명령으로 확인할 수 있습니다.
if ($LASTEXITCODE -ne 0 -or $version.Trim() -ne '3.11.9') {
 throw "Python 3.11.9 is required; found $version. Check py -0p."
}

# ============================================================
# 4. Python 가상환경 생성 및 실행 경로 지정
# ============================================================

# 가상환경의 python.exe가 없을 때만 새 가상환경을 만듭니다.
if (!(Test-Path 'python_service\.venv\Scripts\python.exe')) {
 & py -3.11 -m venv python_service\.venv

 if ($LASTEXITCODE) {
  throw 'venv failed'
 }
}

# 가상환경 활성화 없이도 이 실행 파일로 해당 환경의 pip를 사용합니다.
$Python = Join-Path $ProjectRoot 'python_service\.venv\Scripts\python.exe'

# ============================================================
# 5. 패키지 설치 및 의존성 검사
# ============================================================

# -SkipPackages 옵션이 없을 때만 아래 작업을 수행합니다.
if (!$SkipPackages) {
 # 5-1. CPU용 PyTorch 및 torchvision 설치
 & $Python -m pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu

 if ($LASTEXITCODE) {
  throw 'CPU torch install failed'
 }

 # 5-2. 프로젝트 requirements.txt에 지정된 패키지 설치
 & $Python -m pip install -r python_service\requirements.txt

 if ($LASTEXITCODE) {
  throw 'Python dependency install failed'
 }

 # 5-3. 설치된 패키지 간 의존성 충돌 및 누락 검사
 & $Python -m pip check

 if ($LASTEXITCODE) {
  throw 'Dependency consistency check failed'
 }
}

# ============================================================
# 6. 설치 후 사용자가 진행할 작업 안내
# ============================================================

# 다음 작업은 자동으로 실행하지 않고 안내만 출력합니다.
# ① config.ps1에서 DB 접속 정보 수정
# ② sql\01_create_database.sql을 최초 1회 실행
# ③ scripts\Start.ps1로 서버 시작
Write-Host 'Edit config.ps1 DB credentials. Run sql\01_create_database.sql once. Then run scripts\Start.ps1.'
