# Apollo.MLDL 설정 스크립트 (PowerShell)
# Windows 11 PowerShell에서 실행

# UTF-8 인코딩 설정 (한글 출력 깨짐 방지)
# Windows 터미널에서 한글 출력을 위한 인코딩 설정
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
    [Console]::InputEncoding = [System.Text.Encoding]::UTF8
    
    # PowerShell 인코딩 설정
    $PSDefaultParameterValues['*:Encoding'] = 'utf8'
    
    # Windows 콘솔 코드페이지를 UTF-8로 설정 (Windows 10 1903+)
    if ([Environment]::OSVersion.Version.Build -ge 18362) {
        chcp 65001 | Out-Null
    }
} catch {
    Write-Warning "인코딩 설정 중 오류가 발생했습니다: $_"
}

Write-Host "Apollo.MLDL 프로젝트 설정 시작..." -ForegroundColor Green

# Python 가상환경 확인
Write-Host "`n1. Python 환경 확인..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version
    Write-Host "✅ Python 버전: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python이 설치되지 않았거나 PATH에 없습니다." -ForegroundColor Red
    Write-Host "Python 3.8 이상을 설치해주세요." -ForegroundColor Red
    exit 1
}

# pip 업그레이드
Write-Host "`n2. pip 업그레이드..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# 패키지 설치
Write-Host "`n3. 필수 패키지 설치..." -ForegroundColor Yellow
Write-Host "requirements.txt에서 패키지를 설치합니다..." -ForegroundColor Cyan

try {
    pip install -r requirements.txt
    Write-Host "✅ 패키지 설치 완료" -ForegroundColor Green
} catch {
    Write-Host "❌ 패키지 설치 실패" -ForegroundColor Red
    Write-Host "수동으로 설치해주세요: pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}

# 테스트 실행
Write-Host "`n4. 설정 테스트 실행..." -ForegroundColor Yellow
try {
    python test_setup.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 모든 테스트 통과!" -ForegroundColor Green
    } else {
        Write-Host "❌ 일부 테스트 실패" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ 테스트 실행 실패: $_" -ForegroundColor Red
}

# 사용법 안내
Write-Host "`n=== 사용법 ===" -ForegroundColor Cyan
Write-Host "1. 데이터 가져오기:" -ForegroundColor White
Write-Host "   python main.py fetch" -ForegroundColor Gray

Write-Host "`n2. 피처 생성:" -ForegroundColor White
Write-Host "   python main.py featurize" -ForegroundColor Gray

Write-Host "`n3. 모델 훈련:" -ForegroundColor White
Write-Host "   python main.py train" -ForegroundColor Gray

Write-Host "`n4. 모델 평가:" -ForegroundColor White
Write-Host "   python main.py eval --model artifacts/xgb_reg.joblib" -ForegroundColor Gray

Write-Host "`n고급 사용법 (다른 설정 파일 사용):" -ForegroundColor White
Write-Host "   python main.py --config my_config.yaml fetch" -ForegroundColor Gray

Write-Host "`n설정 완료!" -ForegroundColor Green
