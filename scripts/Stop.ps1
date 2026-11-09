<#
.SYNOPSIS
    기록된 DeepSight 서버 프로세스를 종료합니다.
.DESCRIPTION
    logs\processes.json의 PID와 시작 시각을 확인한 뒤 서버를 종료합니다.
    직계 자식 중 명령줄에 프로젝트 경로가 포함된 프로세스도 종료합니다.
    MySQL 서비스를 중지하는 명령은 포함되어 있지 않습니다.
.EXAMPLE
    .\scripts\Stop.ps1
#>

# ============================================================
# 1. 프로세스 기록 파일 경로 지정
# ============================================================
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$StateFile = Join-Path $ProjectRoot 'logs\processes.json'

# 기록 파일이 없으면 안내 후 종료합니다.
if (!(Test-Path $StateFile)) {
 Write-Host 'No recorded processes.'
 exit
}

# ============================================================
# 2. 기록된 PID와 시작 시각 확인
# ============================================================
$Entries = Get-Content -Raw $StateFile | ConvertFrom-Json

foreach ($Entry in $Entries) {
 # 이미 종료된 프로세스는 건너뜁니다.
 $Process = Get-Process -Id $Entry.id -ErrorAction SilentlyContinue
 if (!$Process) {
  continue
 }

 # PID가 다른 프로세스에 재사용되었으면 종료하지 않습니다.
 # 서버 시작 시 기록한 UTC 시각과 현재 프로세스의 시작 시각을 비교합니다.
 if ($Process.StartTime.ToUniversalTime().ToString('o') -ne $Entry.started) {
  Write-Host 'PID was reused; skipping.'
  continue
 }

 # ========================================================
 # 3. 해당 서버의 직계 자식과 서버 프로세스 종료
 # ========================================================
 # ParentProcessId로 직계 자식을 조회합니다. 모든 하위 계층을 재귀 탐색하지는 않습니다.
 $Children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$($Entry.id)"

 foreach ($Child in $Children) {
  # 명령줄에 프로젝트 경로가 있는 자식만 종료 대상으로 삼습니다.
  if ($Child.CommandLine -and $Child.CommandLine.Contains($ProjectRoot)) {
   Stop-Process -Id $Child.ProcessId -ErrorAction SilentlyContinue
  }
 }

 Stop-Process -Id $Entry.id -ErrorAction SilentlyContinue
}

# ============================================================
# 4. 기록 파일 삭제 및 결과 안내
# ============================================================
# 종료 명령의 오류는 위에서 무시하므로 이 안내만으로 종료 성공이 보장되지는 않습니다.
Remove-Item $StateFile
Write-Host 'DeepSight stopped. MySQL service remains running.'
