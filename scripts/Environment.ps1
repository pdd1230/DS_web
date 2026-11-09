<#
.SYNOPSIS
    DeepSight 스크립트에서 함께 사용하는 경로와 환경 변수를 설정합니다.
.DESCRIPTION
    config.ps1을 읽고 서버 주소, 저장 경로, Python 경로를 준비합니다.
    logs와 storage 폴더가 없으면 생성합니다.
.NOTES
    다른 스크립트에서 다음과 같이 점 소싱하여 사용합니다.
    . (Join-Path $PSScriptRoot 'Environment.ps1')
    점 소싱은 변수와 설정을 호출한 스크립트의 범위에 불러옵니다.
#>

# ============================================================
# 1. 오류 처리 및 프로젝트 경로 설정
# ============================================================
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$Config = Join-Path $ProjectRoot 'config.ps1'

# ============================================================
# 2. 사용자 설정 파일 확인 및 적용
# ============================================================
if (!(Test-Path $Config)) {
    throw 'Run scripts\Setup.ps1 first, then edit config.ps1.'
}

# DB 접속 정보, 포트, API 키 등 config.ps1의 설정을 불러옵니다.
. $Config

# ============================================================
# 3. 서버와 Python 프로세스에 전달할 환경 변수 설정
# ============================================================
$env:DS_HOME = $ProjectRoot
$env:DS_STORAGE = Join-Path $ProjectRoot 'storage'

# Python 추론 서버 주소와 Spring Boot용 MySQL JDBC 주소를 구성합니다.
$env:DS_PYTHON_URL = "http://127.0.0.1:$($env:DS_PYTHON_PORT)"
$env:DS_DB_URL = "jdbc:mysql://$($env:DS_DB_HOST):$($env:DS_DB_PORT)/$($env:DS_DB_NAME)?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Seoul"

# 서버 바인딩에 사용할 주소와 Python 표준 입출력 인코딩을 설정합니다.
$env:DS_BIND = '127.0.0.1'
$env:PYTHONIOENCODING = 'utf-8'

# ============================================================
# 4. 가상환경 경로 지정 및 작업 폴더 준비
# ============================================================
# 여기서는 Python 경로만 지정합니다. 가상환경 생성은 Setup.ps1의 역할입니다.
$PythonExe = Join-Path $ProjectRoot 'python_service\.venv\Scripts\python.exe'

# -Force로 이미 있는 폴더를 유지하고, Out-Null로 생성 결과 출력을 생략합니다.
New-Item -ItemType Directory -Force (Join-Path $ProjectRoot 'logs') | Out-Null
New-Item -ItemType Directory -Force $env:DS_STORAGE | Out-Null
