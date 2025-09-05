Param (
    [string]$AssemblyInfoPath
)

# 기본값: 스크립트 루트 기준 상위 디렉토리의 AirBridge.Core/AssemblyInfo.cs
if (-not $AssemblyInfoPath) {
    $AssemblyInfoPath = Join-Path (Split-Path $PSScriptRoot -Parent) "AirBridge.Core\Model\AssemblyInfo.cs"
}

Write-Host "Updating AssemblyInfo at $AssemblyInfoPath"

# 현재 날짜 yyMM (예: 2508)
$yearMonth = (Get-Date -Format "yyMM")

# AssemblyInfo.cs 읽기 (UTF8로 명시적 읽기)
if (-not (Test-Path $AssemblyInfoPath)) {
    throw "AssemblyInfo.cs not found at $AssemblyInfoPath"
}
$content = [System.IO.File]::ReadAllText($AssemblyInfoPath, [System.Text.Encoding]::UTF8)

# 기존 값 추출
if ($content -match 'HeadVer_YearMonth.*=\s*(\d+);') {
    $oldYearMonth = [int]$matches[1]
} else {
    $oldYearMonth = $yearMonth
}

if ($content -match 'HeadVer_Build.*=\s*(\d+);') {
    $oldBuild = [int]$matches[1]
} else {
    $oldBuild = 0
}

# Build 번호 계산
if ($yearMonth -ne $oldYearMonth) {
    $newBuild = 1
} else {
    $newBuild = $oldBuild + 1
}

# Git SHA (7자리 short hash)
try {
    $gitSha = (git rev-parse --short=7 HEAD).Trim()
} catch {
    $gitSha = "unknown"
}

# 치환
$content = $content -replace 'HeadVer_YearMonth.*=\s*\d+;', "HeadVer_YearMonth { get; } = $yearMonth;"
$content = $content -replace 'HeadVer_Build.*=\s*\d+;', "HeadVer_Build { get; } = $newBuild;"
$content = $content -replace 'GitSha.*=\s*".*";', "GitSha { get; } = `"$gitSha`";"

# 파일 끝 정리 (연속된 개행 제거)
$content = $content -replace '\r?\n+$', ''

# 저장 (UTF8 BOM 없이 저장하여 한글 깨짐 방지)
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($AssemblyInfoPath, $content + "`n", $utf8NoBom)

Write-Host "Updated -> YearMonth=$yearMonth, Build=$newBuild, GitSha=$gitSha"