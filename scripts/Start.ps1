<#
.SYNOPSIS
    DeepSight의 Python 추론 서버와 Spring Boot 웹 서버를 순서대로 시작합니다.

.DESCRIPTION
    설정·실행 환경·포트·JAR·DB 연결을 확인한 뒤 서버를 시작합니다.
    Python의 준비 상태를 먼저 확인하고 Spring Boot를 실행합니다.
    시작 중 오류가 발생하면 이 스크립트가 시작한 서버 프로세스를 종료합니다.

.PARAMETER NoBrowser
    서버는 실행하되 브라우저를 자동으로 열지 않습니다.

.EXAMPLE
    .\scripts\Start.ps1

.EXAMPLE
    .\scripts\Start.ps1 -NoBrowser

.NOTES
    파일 위치: 프로젝트 루트\scripts\Start.ps1
    사전 준비: Setup.ps1 실행, config.ps1 설정, DB 준비, IntelliJ에서 bootJar 실행
    이 스크립트는 Gradle 빌드를 수행하지 않고 기존 JAR를 실행합니다.
#>

param(
    [switch]$NoBrowser
)

# 공통 환경 스크립트를 현재 범위에 불러옵니다(점 소싱).
# 아래에서 사용하는 $ProjectRoot, $PythonExe 등의 정의는 해당 파일을 참조합니다.
. (Join-Path $PSScriptRoot 'Environment.ps1')
Set-Location $ProjectRoot

# ============================================================
# 1. 설정값 및 Python 실행 파일 확인
# ============================================================
# DB 비밀번호가 기본 안내값 그대로인지 확인합니다.
if ($env:DS_DB_PASSWORD -eq 'CHANGE_ME') {
    throw 'Enter your DB password in config.ps1 first.'
}

# Python API 호출에 사용할 인증 키가 비어 있으면 중단합니다.
if ([string]::IsNullOrWhiteSpace($env:DS_API_KEY)) {
    throw 'DS_API_KEY is missing in config.ps1.'
}

if (!(Test-Path $PythonExe)) {
    throw 'Run scripts\Setup.ps1 first.'
}

# 로그 폴더를 준비합니다. 이미 존재해도 그대로 사용합니다.
New-Item -ItemType Directory -Path (Join-Path $ProjectRoot 'logs') `
    -Force | Out-Null

# ============================================================
# 2. Java 실행 가능 여부 및 Python 버전 확인
# ============================================================
# javac 실행 성공 여부를 확인합니다. Java 버전이 17인지 직접 비교하지는 않습니다.
& javac -version
if ($LASTEXITCODE) {
    throw 'JDK 17 (including javac) is required in PATH.'
}

# 프로젝트 가상환경의 Python이 정확히 3.11.9인지 확인합니다.
$PythonVersion = & $PythonExe -c 'import platform; print(platform.python_version())'
if ($LASTEXITCODE) {
    throw 'Python version check failed.'
}

if (($PythonVersion | Out-String).Trim() -ne '3.11.9') {
    throw 'The project venv must use Python 3.11.9.'
}

# ============================================================
# 3. 웹 서버와 Python 서버의 포트 사용 여부 확인
# ============================================================
# NetTCPIP 모듈 없이 .NET 기능으로 현재 TCP 수신 포트를 조회합니다.
$NetworkInfo = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties()
$ListeningPorts = @(
$NetworkInfo.GetActiveTcpListeners() |
        ForEach-Object { $_.Port }
)

# 사용할 포트가 이미 열려 있으면 서버 시작을 중단합니다.
foreach ($Port in @($env:DS_WEB_PORT, $env:DS_PYTHON_PORT)) {
    if ($ListeningPorts -contains [int]$Port) {
        throw "Port $Port is already in use. Run scripts\Stop.ps1 or change the configuration."
    }
}

# ============================================================
# 4. IntelliJ에서 미리 빌드한 JAR 파일 확인
# ============================================================
# gradlew.bat은 실행하지 않습니다. 아래 경로의 JAR가 미리 준비되어 있어야 합니다.
$Jar = Join-Path $ProjectRoot 'web\build\libs\deepsight-web-1.0.0.jar'

if (!(Test-Path $Jar -PathType Leaf)) {
    throw 'JAR file missing. Run bootJar in IntelliJ first.'
}

Write-Host "Using built JAR: $Jar"

# ============================================================
# 5. DB 서버의 TCP 접속 가능 여부 확인
# ============================================================
# DB 호스트와 포트에 TCP 연결이 되는지 확인합니다.
# DB 계정 로그인, 스키마 존재 여부, 테이블 상태까지 검사하지는 않습니다.
$DbCheck = New-Object System.Net.Sockets.TcpClient

try {
    $DbCheck.Connect($env:DS_DB_HOST, [int]$env:DS_DB_PORT)
}
finally {
    # 접속 성공·실패에 관계없이 검사에 사용한 연결 자원을 해제합니다.
    $DbCheck.Dispose()
}

# ============================================================
# 6. Python과 Spring Boot 순차 실행
# ============================================================
# 실패 시 이번에 시작한 프로세스를 정리할 수 있도록 변수를 준비합니다.
$PythonProcess = $null
$JavaProcess = $null

try {
    # 6-1. 가상환경의 Python으로 Uvicorn 서버를 실행합니다.
    # 표준 출력과 오류 출력은 각각 별도 로그 파일에 저장합니다.
    $PythonStartOptions = @{
        FilePath               = $PythonExe
        ArgumentList           = @(
            '-m', 'uvicorn', 'app:app',
            '--host', '127.0.0.1',
            '--port', $env:DS_PYTHON_PORT
        )
        WorkingDirectory       = Join-Path $ProjectRoot 'python_service'
        PassThru               = $true
        RedirectStandardOutput = Join-Path $ProjectRoot 'logs\python.out.log'
        RedirectStandardError  = Join-Path $ProjectRoot 'logs\python.err.log'
    }

    Write-Host 'Starting Python service...'
    # @변수명은 해시테이블의 항목을 명령의 인수로 전달하는 문법입니다.
    # PassThru로 받은 프로세스 객체를 이용해 종료 여부와 PID를 확인합니다.
    $PythonProcess = Start-Process @PythonStartOptions

    $Ready = $false

    # 6-2. Python의 /health 응답을 최대 40회 확인합니다.
    # 매회 1초 대기하며 HTTP 요청 시간도 추가되므로 총 40초보다 길어질 수 있습니다.
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Seconds 1

        if ($PythonProcess.HasExited) {
            throw 'Python failed. See logs\python.err.log.'
        }

        $Health = $null

        try {
            # X-DS-Key 헤더로 인증 키를 전달합니다.
            # 백틱(`)은 하나의 명령을 다음 줄로 이어 쓰는 기호입니다.
            $Health = Invoke-RestMethod `
                -Uri "$($env:DS_PYTHON_URL)/health" `
                -Headers @{ 'X-DS-Key' = $env:DS_API_KEY } `
                -TimeoutSec 2 `
                -ErrorAction Stop
        }
        catch {
            continue
        }

        # 응답을 받았어도 얼굴 모델이 없으면 시작을 중단합니다.
        if (!$Health.modelExists) {
            throw 'Face model missing. Check the model path.'
        }

        $Ready = $true
        break
    }

    if (!$Ready) {
        throw 'Python readiness timeout. See logs\python.err.log.'
    }

    Write-Host 'Python service ready.'

    # 6-3. 준비된 JAR를 java -jar로 실행합니다.
    # JAR 경로에 공백이 있어도 전달되도록 경로를 큰따옴표로 감쌉니다.
    $JavaStartOptions = @{
        FilePath               = 'java'
        ArgumentList           = @('-jar', ('"' + $Jar + '"'))
        WorkingDirectory       = $ProjectRoot
        PassThru               = $true
        RedirectStandardOutput = Join-Path $ProjectRoot 'logs\spring.out.log'
        RedirectStandardError  = Join-Path $ProjectRoot 'logs\spring.err.log'
    }

    Write-Host 'Starting Spring Boot...'
    $JavaProcess = Start-Process @JavaStartOptions

    # 6-4. Stop.ps1에서 사용할 PID와 UTC 시작 시각을 기록합니다.
    $ProcessRecords = @(
        @{
            id      = $PythonProcess.Id
            started = $PythonProcess.StartTime.ToUniversalTime().ToString('o')
        }
        @{
            id      = $JavaProcess.Id
            started = $JavaProcess.StartTime.ToUniversalTime().ToString('o')
        }
    )

    # 프로세스 정보를 JSON 형식으로 logs\processes.json에 저장합니다.
    $ProcessRecords |
            ConvertTo-Json |
            Set-Content -Encoding UTF8 `
            -Path (Join-Path $ProjectRoot 'logs\processes.json')

    # 6-5. Spring Boot의 API 응답으로 준비 상태를 확인합니다.
    $Url = "http://127.0.0.1:$($env:DS_WEB_PORT)"
    $Ready = $false

    # 최대 90회 확인합니다. 각 요청 시간 때문에 총 대기 시간은 90초를 넘을 수 있습니다.
    for ($i = 0; $i -lt 90; $i++) {
        Start-Sleep -Seconds 1

        if ($JavaProcess.HasExited) {
            throw 'Spring failed. See logs\spring.out.log and logs\spring.err.log.'
        }

        try {
            Invoke-RestMethod `
                -Uri "$Url/api/datasets" `
                -TimeoutSec 2 `
                -ErrorAction Stop | Out-Null

            $Ready = $true
            break
        }
        catch {
            continue
        }
    }

    if (!$Ready) {
        throw 'Spring readiness timeout. See logs\spring.out.log and logs\spring.err.log.'
    }

    Write-Host "DeepSight ready: $Url"

    # 6-6. 기본 동작은 브라우저 열기이며, -NoBrowser 지정 시 생략합니다.
    if (!$NoBrowser) {
        Start-Process $Url
    }
}
catch {
    # 시작 과정에서 오류가 발생하면 이번에 시작한 서버를 종료합니다.
    # 오류 정리 중의 종료 실패는 무시하고 마지막에 원래 오류를 다시 전달합니다.
    if ($JavaProcess -and !$JavaProcess.HasExited) {
        Stop-Process -Id $JavaProcess.Id -ErrorAction SilentlyContinue
    }

    if ($PythonProcess -and !$PythonProcess.HasExited) {
        Stop-Process -Id $PythonProcess.Id -ErrorAction SilentlyContinue
    }

    throw
}
