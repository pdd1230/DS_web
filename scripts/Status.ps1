<#
.SYNOPSIS
    Spring Boot의 상태 확인 API를 호출합니다.
.DESCRIPTION
    /api/health 응답을 JSON으로 출력합니다.
    Python 서버에 직접 요청하는 검사는 이 파일에 포함되어 있지 않습니다.
.EXAMPLE
    .\scripts\Status.ps1
.NOTES
    공통 환경 설정을 읽으므로 logs와 storage 폴더가 생성될 수 있습니다.
#>

# ============================================================
# 1. 공통 경로와 환경 변수 불러오기
# ============================================================
# 이 단계의 오류는 아래 API 요청용 catch에서 처리하지 않습니다.
. (Join-Path $PSScriptRoot 'Environment.ps1')

# ============================================================
# 2. Spring Boot 상태 조회 및 결과 출력
# ============================================================
try {
    # ConvertTo-Json의 Depth 6은 중첩된 응답을 JSON으로 변환하는 깊이입니다.
    Invoke-RestMethod "http://127.0.0.1:$($env:DS_WEB_PORT)/api/health" |
            ConvertTo-Json -Depth 6
}
catch {
    # API 요청 또는 결과 변환 중 오류가 발생하면 로그 확인을 안내합니다.
    Write-Host 'Spring is not responding. Check logs\spring.out.log.'
}
