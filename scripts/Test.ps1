<#
.SYNOPSIS
    DeepSight의 Python 테스트와 Java 테스트를 실행합니다.

.DESCRIPTION
    테스트용 Python 패키지를 설치하고 pytest를 실행한 다음,
    Gradle Wrapper로 Java 테스트를 실행합니다.
    -Full 옵션을 지정하면 Java 테스트 전에 테스트용 Python 서버도 시작합니다.

.PARAMETER Full
    8091 포트에 테스트용 Python 서버를 실행하고 DS_FULL_TESTS를 true로 설정합니다.
    전체 테스트의 구체적인 범위는 실제 테스트 코드에서 결정됩니다.

.EXAMPLE
    .\scripts\Test.ps1

.EXAMPLE
    .\scripts\Test.ps1 -Full

.NOTES
    파일 위치: 프로젝트 루트\scripts\Test.ps1
    사전 준비: Setup.ps1 실행 및 config.ps1 설정
    Java 테스트 실행 시 web\gradlew.bat을 사용합니다.
    테스트 DB가 H2라는 마지막 안내는 이 파일의 출력 문구입니다.
    실제 DB 사용 여부는 Java 테스트 설정과 테스트 코드도 확인해야 합니다.
#>

param(
 [switch]$Full
)

# ============================================================
# 1. 공통 환경 불러오기 및 작업 폴더 이동
# ============================================================
# 점 소싱으로 프로젝트 경로, Python 경로, 환경 변수 등을 불러옵니다.
. (Join-Path $PSScriptRoot 'Environment.ps1')
Set-Location $ProjectRoot

# ============================================================
# 2. Python 테스트 의존성 설치 및 테스트 실행
# ============================================================
# 실행할 때마다 테스트용 requirements 파일을 기준으로 패키지를 설치합니다.
& $PythonExe -m pip install -r python_service\requirements-test.txt
if ($LASTEXITCODE) {
 throw 'Test dependency install failed'
}

# 추론 서비스와 legacy의 테스트를 실행합니다. -q는 출력량을 줄이는 옵션입니다.
& $PythonExe -m pytest python_service\tests legacy\tests -q
if ($LASTEXITCODE) {
 throw 'Python tests failed'
}

# ============================================================
# 3. -Full 옵션 지정 시 테스트용 Python 서버 실행
# ============================================================
$TestProcess = $null

try {
 if ($Full) {
  # 이 포트 검사는 Windows NetTCPIP 모듈의 명령을 사용합니다.
  if (Get-NetTCPConnection -LocalPort 8091 -State Listen -ErrorAction SilentlyContinue) {
   throw 'Test port 8091 is in use.'
  }

  # 아래 값은 앞의 pytest 실행 후, 테스트 서버와 Java 테스트 실행 전에 설정됩니다.
  # 원본과 동일하게 이 환경 변수들의 기존 값을 복원하는 처리는 포함하지 않습니다.
  $env:DS_FULL_TESTS = 'true'
  $env:DS_API_KEY = 'local-test-key'
  $env:DS_STORAGE = Join-Path $ProjectRoot 'build-verification\storage'

  New-Item -ItemType Directory -Force $env:DS_STORAGE | Out-Null

  # 테스트 서버는 127.0.0.1:8091에서 실행하며 출력과 오류를 별도 로그로 기록합니다.
  # PassThru로 받은 프로세스 객체는 마지막 종료 처리에 사용합니다.
  $TestProcess = Start-Process -FilePath $PythonExe -ArgumentList @('-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '8091') -WorkingDirectory (Join-Path $ProjectRoot 'python_service') -PassThru -RedirectStandardOutput (Join-Path $ProjectRoot 'logs\test-python.out.log') -RedirectStandardError (Join-Path $ProjectRoot 'logs\test-python.err.log')

  # 인증 헤더를 포함하여 /health 응답을 최대 30회 확인합니다.
  # 요청 타임아웃을 별도로 지정하지 않아 총 대기 시간이 30초를 넘을 수 있습니다.
  $Ready = $false
  for ($i = 0; $i -lt 30; $i++) {
   Start-Sleep -Seconds 1
   try {
    Invoke-RestMethod 'http://127.0.0.1:8091/health' -Headers @{ 'X-DS-Key' = 'local-test-key' } | Out-Null
    $Ready = $true
    break
   }
   catch {
    # 아직 응답하지 않으면 다음 반복에서 다시 시도합니다.
   }
  }

  if (!$Ready) {
   throw 'Test Python service not ready'
  }
 }
 else {
  # 기본 실행에서는 별도 테스트 서버를 띄우지 않습니다.
  $env:DS_FULL_TESTS = 'false'
 }

 # ========================================================
 # 4. Java 테스트 실행
 # ========================================================
 # 작업 위치를 web으로 옮기고, 성공·실패에 관계없이 원래 위치로 복귀합니다.
 Push-Location web
 try {
  # Gradle Daemon을 지속적으로 사용하는 옵션 없이 test 작업을 실행합니다.
  & .\gradlew.bat --no-daemon test
  if ($LASTEXITCODE) {
   throw 'Java tests failed'
  }
 }
 finally {
  Pop-Location
 }
}
finally {
 # ========================================================
 # 5. 테스트용 서버 종료
 # ========================================================
 # 테스트 성공·실패에 관계없이 이번에 시작한 테스트 서버를 정리합니다.
 if ($TestProcess) {
  # 직계 자식 중 명령줄에 프로젝트 경로가 있는 프로세스를 종료합니다.
  Get-CimInstance Win32_Process -Filter "ParentProcessId=$($TestProcess.Id)" |
          ForEach-Object {
           if ($_.CommandLine -and $_.CommandLine.Contains($ProjectRoot)) {
            Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
           }
          }

  Stop-Process -Id $TestProcess.Id -ErrorAction SilentlyContinue
 }
}

# ============================================================
# 6. 테스트 완료 안내
# ============================================================
Write-Host 'Tests completed. Test DB is H2; production MySQL is not modified.'
