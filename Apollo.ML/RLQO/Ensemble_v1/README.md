# Ensemble v1: Voting Ensemble for Query Optimization

## 개요

4개의 강화학습 모델(DQN v3, PPO v3, DDPG v1, SAC v1)을 결합하는 Voting Ensemble을 구현하여 쿼리 최적화 성능을 향상시킵니다.

## 모델 구성

### 사용 모델

1. **DQN v3** (Discrete Action Space)
   - Deep Q-Network
   - 개별 액션 선택에 특화
   - Mean Speedup: ~1.15x

2. **PPO v3** (Discrete Action Space with Masking)
   - Proximal Policy Optimization
   - 안전한 액션 선택 (액션 마스킹)
   - Mean Speedup: ~1.20x
   - CTE 쿼리에 강점

3. **DDPG v1** (Continuous Action Space)
   - Deep Deterministic Policy Gradient
   - 다중 액션 조합 가능
   - Mean Speedup: ~1.88x (최고 성능)
   - JOIN_HEAVY 쿼리에 강점

4. **SAC v1** (Continuous Action Space)
   - Soft Actor-Critic
   - Maximum Entropy로 탐색 강화
   - Mean Speedup: ~1.50x (추정)

## 투표 전략

### 1. Majority Voting
- 가장 많이 선택된 액션 선택
- 단순하고 견고함

### 2. Weighted Voting
- Confidence score로 가중치 부여
- 각 모델의 확신도 고려

### 3. Equal Weighted
- 모든 모델에 동일한 가중치
- 공정한 투표

### 4. Performance-Based
- 모델의 평균 성능으로 가중치 설정
- DDPG > SAC > PPO > DQN 순서

### 5. Query Type-Based
- 쿼리 타입별로 최적 모델에 높은 가중치
- CTE → PPO, JOIN_HEAVY → DDPG 등

## 디렉토리 구조

```
Ensemble_v1/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── ensemble_config.py          # 설정 (모델 경로, 가중치)
├── env/
│   ├── __init__.py
│   └── ensemble_env.py              # 환경 래퍼
├── ensemble_voting.py               # 핵심 Voting Ensemble 클래스
├── voting_strategies.py             # 투표 전략 함수들
├── visualize_ensemble.py            # 시각화 스크립트
├── train/
│   ├── __init__.py
│   └── ensemble_evaluate.py        # 평가 스크립트
├── results/
│   ├── ensemble_voting_results.json
│   ├── ensemble_comparison.csv
│   └── charts/                      # 생성된 차트들
├── Ensemble_Evaluation_Report.md   # 평가 보고서
└── README.md                        # 이 파일
```

## 사용 방법

### 1. 모델 로드 및 예측

```python
from RLQO.Ensemble_v1.ensemble_voting import VotingEnsemble

# Ensemble 생성
ensemble = VotingEnsemble(voting_strategy='weighted', verbose=True)
ensemble.load_models()

# 예측
action, info = ensemble.predict(observation, query_type='CTE')
print(f"Selected action: {action}")
print(f"Model predictions: {info['predictions']}")
print(f"Confidences: {info['confidences']}")
```

### 2. 평가 실행 (체크포인트 지원 🎯)

```bash
cd Apollo.ML/RLQO/Ensemble_v1/train
python ensemble_evaluate.py
```

**실행 정보**:
- 5가지 전략 모두 평가
- 약 1~2시간 소요 예상
- 결과: `results/ensemble_voting_results.json`, `results/ensemble_comparison.csv`

**🎯 체크포인트 기능**:
- ✅ 자동 저장: 각 쿼리 완료 후, 5 episodes마다
- ✅ 자동 재개: 중단 후 재실행 시 이어서 진행
- ✅ 전략별 저장: 각 전략마다 독립적인 체크포인트
- ✅ 위치: `results/checkpoints/checkpoint_<strategy>.json`

**중단 후 재개**:
1. Ctrl+C로 중단
2. 동일한 명령어로 재실행 → 자동으로 이어서 진행

**체크포인트 관리**:
```bash
# 체크포인트 목록 및 진행률 확인
python manage_checkpoints.py list

# 특정 전략의 상세 정보
python manage_checkpoints.py details weighted

# 특정 전략의 체크포인트 삭제 (처음부터 재시작)
python manage_checkpoints.py delete weighted

# 모든 체크포인트 삭제
python manage_checkpoints.py delete-all
```

또는 Python에서:

```python
from RLQO.Ensemble_v1.train.ensemble_evaluate import evaluate_ensemble

results = evaluate_ensemble(
    voting_strategy='weighted',
    n_queries=30,
    n_episodes=10,
    verbose=True,
    resume=True  # 체크포인트에서 재개
)
```

### 3. 여러 전략 비교

```python
from RLQO.Ensemble_v1.train.ensemble_evaluate import compare_strategies

strategies = ['majority', 'weighted', 'equal', 'performance', 'query_type']
comparison_results = compare_strategies(
    strategies=strategies,
    n_queries=30,
    n_episodes=10
)
```

### 4. 시각화 생성

```bash
cd Apollo.ML/RLQO/Ensemble_v1
python visualize_ensemble.py
```

## 평가 메트릭

1. **Mean Speedup**: 평균 속도 향상률
2. **Median Speedup**: 중앙값 속도 향상률
3. **Win Rate**: 베이스라인 대비 개선된 쿼리 비율
4. **Safe Rate**: 성능 저하가 10% 이내인 비율
5. **Model Agreement**: 모델들이 일치하는 정도

## 예상 성능

- **목표 Mean Speedup**: 2.0~2.3x
- **현재 최고 단일 모델**: DDPG v1 (1.88x)
- **예상 개선**: 10~20% 추가 향상
- **안정성**: 단일 모델 대비 분산 감소

## 주요 특징

### 1. 다양성 (Diversity)
- Discrete (DQN, PPO) + Continuous (DDPG, SAC) 모델 결합
- 서로 다른 학습 알고리즘의 강점 활용

### 2. 적응성 (Adaptability)
- 쿼리 타입별 최적 모델 선택
- Confidence threshold로 불확실한 예측 제외

### 3. 견고성 (Robustness)
- 단일 모델의 실패에 강함
- 여러 모델의 합의로 안정적 성능

### 4. 해석 가능성 (Interpretability)
- 각 모델의 예측과 confidence 추적
- 모델 간 합의도 분석 가능

## 한계점

1. **추론 시간**: 4개 모델을 모두 실행하므로 단일 모델보다 느림
2. **메모리 사용**: 4개 모델을 메모리에 로드해야 함
3. **Continuous → Discrete 변환**: DDPG/SAC의 연속 액션을 이산 액션으로 변환하는 과정에서 정보 손실 가능

## 향후 개선 방향

1. **Meta-Learning**: 쿼리 특성에 따라 자동으로 최적 모델 선택
2. **Multi-Agent**: 순차적으로 여러 모델이 협력하여 최적화
3. **Online Learning**: 실시간 피드백으로 가중치 동적 조정
4. **Model Distillation**: 4개 모델의 지식을 1개의 경량 모델로 압축

## 참고 자료

- DQN v3 평가 보고서: `Apollo.ML/RLQO/DQN_v3/DQN_v3_Evaluation_Report.md`
- PPO v3 평가 보고서: `Apollo.ML/RLQO/PPO_v3/PPO_v3_Evaluation_Report.md`
- DDPG v1 평가 보고서: `Apollo.ML/RLQO/DDPG_v1/DDPG_v1_Evaluation_Report.md`
- SAC v1 평가 보고서: `Apollo.ML/RLQO/SAC_v1/SAC_v1_Evaluation_Report.md`
- 모델 비교: `Apollo.ML/RLQO/Initial_Model_Comparison.md`

## 라이선스

이 프로젝트는 Apollo 프로젝트의 일부입니다.

