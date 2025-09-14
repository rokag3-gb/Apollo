# Apollo.MLDL

SQL Server 실행계획 XML 데이터를 분석하여 XGBoost 회귀 모델로 쿼리 성능을 예측하는 머신러닝 프로젝트입니다.

## 🚀 주요 기능

- **SQL Server 실행계획 XML 파싱**: 복잡한 실행계획을 그래프 구조로 변환
- **풍부한 피처 엔지니어링**: 
  - 그래프 통계 특성 (노드 수, 엣지 수, 밀도 등)
  - 비용 관련 특성 (예상 비용, IO 비용, CPU 비용 등)
  - 연산자 특성 (PhysicalOp, LogicalOp, 병렬 처리 등)
  - 인덱스 특성 (클러스터드/논클러스터드, 스캔/시크 등)
- **XGBoost 회귀 모델**: 쿼리 실행 시간 예측
- **모듈화된 구조**: 각 기능별로 분리된 깔끔한 코드 구조

## 📋 요구사항

- Python 3.8 이상
- Windows 11 (PowerShell)
- SQL Server 데이터베이스 접근 권한

## 🛠️ 설치 및 설정

### 1. 자동 설정 (권장)

PowerShell에서 다음 명령어를 실행하세요:

```powershell
cd Apollo.MLDL
.\setup.ps1
```

### 2. 수동 설정

```powershell
# 패키지 설치
pip install -r requirements.txt

# 설정 테스트
python test_setup.py
```

## 📁 프로젝트 구조

```
Apollo.MLDL/
├── main.py              # 메인 실행 파일
├── config.py            # 설정 관리
├── config.yaml          # 설정 파일
├── db.py                # 데이터베이스 연결
├── plan_graph.py        # XML 파싱 및 그래프 변환
├── features.py          # 피처 엔지니어링
├── model.py             # XGBoost 모델 정의
├── train.py             # 모델 훈련
├── evaluate.py          # 모델 평가
├── requirements.txt     # 패키지 의존성
├── setup.ps1           # 자동 설정 스크립트
├── test_setup.py       # 설정 테스트
└── README.md           # 이 파일
```

## 🚀 사용법

### 1. 데이터 가져오기

SQL Server에서 실행계획 데이터를 가져옵니다:

```powershell
python main.py fetch
```

### 2. 피처 생성

실행계획 XML을 머신러닝 피처로 변환합니다:

```powershell
python main.py featurize
```

### 3. 모델 훈련

XGBoost 모델을 훈련합니다:

```powershell
python main.py train
```

### 4. 모델 평가

훈련된 모델을 평가합니다:

```powershell
python main.py eval --model artifacts/xgb_reg.joblib
```

### 고급 사용법

다른 설정 파일을 사용하려면 `--config` 옵션을 사용하세요:

```powershell
python main.py --config my_config.yaml fetch
python main.py --config my_config.yaml featurize
python main.py --config my_config.yaml train
python main.py --config my_config.yaml eval --model artifacts/xgb_reg.joblib
```

## ⚙️ 설정

`config.yaml` 파일에서 다음 설정을 조정할 수 있습니다:

- **데이터베이스 연결 정보**: 서버, 데이터베이스, 인증 정보
- **모델 하이퍼파라미터**: XGBoost 설정
- **피처 엔지니어링 옵션**: 어떤 특성을 추출할지 선택
- **훈련 설정**: 테스트 비율, 시드값 등

## 📊 출력 파일

- `artifacts/collected_plans.parquet`: 원본 실행계획 데이터
- `artifacts/features.parquet`: 추출된 피처 데이터
- `artifacts/xgb_reg.joblib`: 훈련된 모델
- `artifacts/feature_importance.csv`: 피처 중요도

## 🔧 문제 해결

### 일반적인 문제

1. **패키지 설치 오류**: `pip install --upgrade pip` 후 다시 시도
2. **데이터베이스 연결 오류**: `config.yaml`의 DB 설정 확인
3. **메모리 부족**: 배치 크기를 줄이거나 더 강력한 머신 사용

### 로그 확인

각 단계에서 상세한 로그가 출력되므로, 오류 발생 시 로그를 확인하세요.

## 📈 성능 최적화

- **병렬 처리**: XGBoost의 `n_jobs` 설정으로 CPU 코어 활용
- **메모리 관리**: 대용량 데이터의 경우 배치 처리 고려
- **피처 선택**: 중요도가 낮은 피처 제거로 모델 경량화

## 🤝 기여

버그 리포트나 기능 제안은 이슈로 등록해주세요.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
