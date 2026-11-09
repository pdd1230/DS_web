<#
.SYNOPSIS
    DeepSight의 Python 추론 서버와 Spring Boot 웹 서버를 순서대로 시작합니다.

.DESCRIPTION
    설정·실행 환경·포트·JAR·DB 연결을 확인한 뒤 서버를 시작합니다.
    Python의 준비 상태를 먼저 확인하고 Spring Boot를 실행합니다.
    시작 중 오류가 발생하면 이 스크립트가 시작한 서버 프로세스를 종료합니다.

.PARAMETER Rebuild
    기존 JAR가 있어도 Gradle bootJar를 다시 실행합니다.

.PARAMETER NoBrowser
    서버는 실행하되 브라우저를 자동으로 열지 않습니다.

.EXAMPLE
    .\scripts\Start.ps1

.EXAMPLE
    .\scripts\Start.ps1 -NoBrowser

.NOTES
    파일 위치: 프로젝트 루트\scripts\Start.ps1
    사전 준비: Setup.ps1 실행, config.ps1 설정, DB 준비
    기존 JAR는 재사용하고, 없거나 -Rebuild 지정 시 Gradle로 빌드합니다.
    Windows PowerShell 5.1에서 한글을 읽도록 UTF-8 BOM으로 저장합니다.
#>

param(
    [switch]$NoBrowser,
    [switch]$Rebuild
)

# 공통 환경 스크립트를 현재 범위에 불러옵니다(점 소싱).
# 아래에서 사용하는 $ProjectRoot, $PythonExe 등의 정의는 해당 파일을 참조합니다.
. (Join-Path $PSScriptRoot 'Environment.ps1')
Set-Location $ProjectRoot

# ============================================================
# 1. 설정값 및 Python 실행 파일 확인
# ============================================================
# DB 비밀번호가 기본 안내값 그대로인지 확인합니다.
if ($env:DS_DB_PASSWORD -in @('CHANGE_ME', 'change me')) {
    throw 'Enter your DB password in config.ps1 first.'
}

# Python API 호출에 사용할 인증 키가 비어 있으면 중단합니다.
if ([string]::IsNullOrWhiteSpace($env:DS_API_KEY)) {
    throw 'DS_API_KEY is missing in config.ps1.'
}

if (!(Test-Path $PythonExe)) {
    throw 'Run scripts\Setup.ps1 first.'
}

# 설정 누락과 잘못된 포트는 서버 실행 전에 확인합니다.
foreach ($Name in @('DS_DB_HOST', 'DS_DB_PORT', 'DS_DB_NAME', 'DS_DB_USER', 'DS_WEB_PORT', 'DS_PYTHON_PORT')) {
    $Value = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "Required setting missing: $Name. Check config.ps1."
    }
}
foreach ($Name in @('DS_DB_PORT', 'DS_WEB_PORT', 'DS_PYTHON_PORT')) {
    $PortValue = 0
    $Value = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if (![int]::TryParse($Value, [ref]$PortValue) -or $PortValue -lt 1 -or $PortValue -gt 65535) {
        throw "Invalid port setting: $Name. Use an integer from 1 to 65535."
    }
}
if ([int]$env:DS_WEB_PORT -eq [int]$env:DS_PYTHON_PORT) {
    throw 'DS_WEB_PORT and DS_PYTHON_PORT must be different.'
}

# 로그 폴더를 준비합니다. 이미 존재해도 그대로 사용합니다.
New-Item -ItemType Directory -Path (Join-Path $ProjectRoot 'logs') `
    -Force | Out-Null

# ============================================================
# 2. Java 실행 가능 여부 및 Python 버전 확인
# ============================================================
foreach ($CommandName in @('java', 'javac')) {
    if (!(Get-Command $CommandName -CommandType Application -ErrorAction SilentlyContinue)) {
        throw "$CommandName is missing from PATH. Install/configure JDK 17 first."
    }
}

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

# 다른 가상환경이 활성화되어 있어도 프로젝트 전용 Python으로 검사합니다.
Write-Host "Using Python: $PythonExe"
& $PythonExe -c 'import fastapi, uvicorn, numpy, cv2, PIL, ultralytics, torch, torchvision'
if ($LASTEXITCODE) {
    throw 'Python package import failed. Run scripts\Setup.ps1 and review the error above.'
}

# 모든 실험의 결과 이력에 원본 소스·모델 해시를 기록하므로 함께 필요합니다.
foreach ($RelativePath in @(
    'python_service\app.py',
    'python_service\core.py',
    'python_service\runner.py',
    'legacy\source\main.py',
    'legacy\source\main_1.py',
    'legacy\source\main_1_baseline.py',
    'legacy\scripts\build_deepsight_reports.py',
    'legacy\shared\models\yolov8n-face-lindevs.pt'
)) {
    if (!(Test-Path (Join-Path $ProjectRoot $RelativePath) -PathType Leaf)) {
        throw "Required project file missing: $RelativePath. Restore it before starting."
    }
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
# 4. 기존 JAR 재사용 또는 최초/명시적 빌드
# ============================================================
$WebDirectory = Join-Path $ProjectRoot 'web'
$Jar = Join-Path $WebDirectory 'build\libs\deepsight-web-1.0.0.jar'
$NeedsBuild = $Rebuild -or !(Test-Path $Jar -PathType Leaf)
if (!$NeedsBuild -and (Get-Item $Jar).Length -eq 0) {
    $NeedsBuild = $true
}

if ($NeedsBuild) {
    # clone 후 web/build가 없어도 Gradle이 생성합니다.
    foreach ($RelativePath in @('gradlew.bat', 'build.gradle', 'settings.gradle',
        'gradle\wrapper\gradle-wrapper.jar', 'gradle\wrapper\gradle-wrapper.properties')) {
        if (!(Test-Path (Join-Path $WebDirectory $RelativePath) -PathType Leaf)) {
            throw "Build file missing: web\$RelativePath. Check the repository contents."
        }
    }

    if ($Rebuild) {
        Write-Host 'Rebuilding Spring Boot JAR (-Rebuild)...'
    }
    else {
        Write-Host 'No usable JAR found. Building Spring Boot JAR...'
    }

    # 호출 위치와 관계없이 web을 기준으로 빌드하고 원래 위치로 복귀합니다.
    Push-Location $WebDirectory
    try {
        & .\gradlew.bat --no-daemon bootJar
        if ($LASTEXITCODE -ne 0) {
            throw "Gradle bootJar failed (exit code: $LASTEXITCODE)."
        }
    }
    catch {
        # 빌드 실패 시 남아 있는 이전 JAR로 조용히 실행하지 않습니다.
        throw ("Build failed: " + $_.Exception.Message +
            ' Check the Gradle output, JDK 17, network access, and local execution policy. ' +
            'If command execution is blocked, build bootJar in IntelliJ, then run Start.ps1 without -Rebuild.')
    }
    finally {
        Pop-Location
    }

    if (!(Test-Path $Jar -PathType Leaf)) {
        throw "Build completed but the expected JAR is missing: $Jar. Check web/build.gradle."
    }
    if ((Get-Item $Jar).Length -eq 0) {
        throw "The built JAR is empty: $Jar. Rebuild it before starting."
    }
}
else {
    Write-Host 'Reusing existing JAR. Use -Rebuild after changing Java code or web resources.'
}
Write-Host "Using JAR: $Jar"

# ============================================================
# 5. DB 서버의 TCP 접속 가능 여부 확인
# ============================================================
# DB 호스트와 포트에 TCP 연결이 되는지 확인합니다.
# DB 계정 로그인, 스키마 존재 여부, 테이블 상태까지 검사하지는 않습니다.
$DbCheck = New-Object System.Net.Sockets.TcpClient

try {
    # 접속 대기가 길어지지 않도록 최대 5초로 제한합니다.
    $ConnectTask = $DbCheck.ConnectAsync($env:DS_DB_HOST, [int]$env:DS_DB_PORT)
    if (!$ConnectTask.Wait(5000)) {
        throw 'MySQL connection timed out (5 seconds).'
    }
    $ConnectTask.GetAwaiter().GetResult() | Out-Null
}
catch {
    throw ("MySQL is not reachable at $($env:DS_DB_HOST):$($env:DS_DB_PORT). " +
        'Check the MySQL service and config.ps1. Details: ' + $_.Exception.Message)
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
