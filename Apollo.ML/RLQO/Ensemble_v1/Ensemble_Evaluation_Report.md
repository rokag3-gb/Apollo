# Ensemble v1: Voting Ensemble 평가 보고서

## Executive Summary

본 보고서는 4개의 강화학습 모델(DQN v3, PPO v3, DDPG v1, SAC v1)을 결합한 Voting Ensemble의 성능을 평가합니다.

### 주요 성과

- **평가 대상**: 5가지 투표 전략 (Majority, Weighted, Equal, Performance, Query Type)
- **평가 쿼리**: 30개 쿼리
- **평가 에피소드**: 각 쿼리당 10 episodes (총 300회 평가)
- **목표**: 단일 모델 대비 안정적이고 향상된 성능

**결과 요약** (평가 후 업데이트 예정):
```
Strategy         Mean Speedup    Win Rate    Model Agreement
---------------------------------------------------------
Majority         [TBD]x          [TBD]%      [TBD]%
Weighted         [TBD]x          [TBD]%      [TBD]%
Equal            [TBD]x          [TBD]%      [TBD]%
Performance      [TBD]x          [TBD]%      [TBD]%
Query Type       [TBD]x          [TBD]%      [TBD]%
```

## 1. 방법론

### 1.1 Voting Ensemble 개요

Voting Ensemble은 여러 모델의 예측을 결합하여 최종 결정을 내리는 앙상블 기법입니다.

**핵심 아이디어**:
- 각 모델이 독립적으로 액션을 제안
- Confidence score 기반으로 가중치 부여
- 투표를 통해 최종 액션 선택

**장점**:
- 단일 모델의 약점 보완
- 다양한 전략의 강점 결합
- 안정적 성능 (분산 감소)

### 1.2 사용 모델

| 모델 | 타입 | Action Space | 평균 Speedup | 강점 |
|------|------|--------------|--------------|------|
| DQN v3 | Off-Policy | Discrete | ~1.15x | 개별 액션 선택 |
| PPO v3 | On-Policy | Discrete (Masked) | ~1.20x | CTE 쿼리, 안전성 |
| DDPG v1 | Off-Policy | Continuous | ~1.88x | JOIN_HEAVY, 다중 액션 |
| SAC v1 | Off-Policy | Continuous | ~1.50x | 탐색, AGGREGATE |

### 1.3 투표 전략

#### 1. Majority Voting
```python
action = most_common(predictions)
```
- 가장 많이 선택된 액션
- 단순하고 견고함

#### 2. Weighted Voting
```python
action = argmax(Σ confidence[m] * I(prediction[m] == action))
```
- Confidence score로 가중치 부여
- Q-value (DQN, DDPG, SAC) 또는 Policy probability (PPO) 사용

#### 3. Equal Weighted
```python
action = weighted_vote(predictions, weights=1.0)
```
- 모든 모델에 동일한 가중치

#### 4. Performance-Based
```python
weights = {dqn: 1.15, ppo: 1.20, ddpg: 1.88, sac: 1.50}
action = weighted_vote(predictions, weights)
```
- 모델의 평균 성능으로 가중치 설정

#### 5. Query Type-Based
```python
if query_type == 'CTE':
    weights = {dqn: 0.15, ppo: 0.40, ddpg: 0.25, sac: 0.20}
elif query_type == 'JOIN_HEAVY':
    weights = {dqn: 0.10, ppo: 0.15, ddpg: 0.45, sac: 0.30}
...
action = weighted_vote(predictions, weights)
```
- 쿼리 타입별 최적 모델에 높은 가중치

### 1.4 Confidence 계산

**Discrete 모델 (DQN, PPO)**:
- DQN: `confidence = Q(s, a) / max(Q(s, ·))`
- PPO: `confidence = π(a|s)` (policy probability)

**Continuous 모델 (DDPG, SAC)**:
- DDPG: `confidence = sigmoid(Q(s, μ(s)) / 10)`
- SAC: `confidence = sigmoid(Q(s, a) / 10)`

**Threshold**: Confidence < 0.1인 예측은 제외

## 2. 실험 설정

### 2.1 평가 환경

- **데이터베이스**: Real Trading DB (SQL Server)
- **쿼리 개수**: 30개 (SAMPLE_QUERIES from constants2.py)
- **에피소드 수**: 각 쿼리당 10 episodes
- **총 평가 횟수**: 30 queries × 10 episodes = 300
- **Baseline 측정**: 각 쿼리당 10회 실행 후 중앙값 사용

### 2.2 쿼리 분포

| Query Type | Count | Examples |
|------------|-------|----------|
| JOIN_HEAVY | 11    | Q0, Q7, Q15, Q16, Q25, Q26, Q27, Q28 |
| CTE        | 3     | Q1, Q8, Q11 |
| TOP        | 10    | Q3, Q4, Q9, Q10, Q12, Q13, Q14, Q21, Q23 |
| AGGREGATE  | 4     | Q20, Q22, Q24, Q29 |
| SUBQUERY   | 3     | Q5, Q17, Q18 |
| WINDOW     | 1     | Q19 |
| SIMPLE     | 2     | Q2, Q6 |

### 2.3 평가 메트릭

1. **Mean Speedup**: `Σ (baseline_time / optimized_time) / N`
2. **Median Speedup**: 중앙값 속도 향상률
3. **Max Speedup**: 최고 속도 향상률
4. **Win Rate**: `(개선된 쿼리 수) / (전체 쿼리 수)`
5. **Safe Rate**: 성능 저하가 10% 이내인 비율
6. **Model Agreement**: 모델들이 동일한 액션을 선택한 비율

## 3. 결과

### 3.1 전체 성능 요약

**[평가 후 업데이트]**

| Strategy | Mean Speedup | Median Speedup | Max Speedup | Win Rate | Safe Rate |
|----------|--------------|----------------|-------------|----------|-----------|
| Majority | [TBD]        | [TBD]          | [TBD]       | [TBD]    | [TBD]     |
| Weighted | [TBD]        | [TBD]          | [TBD]       | [TBD]    | [TBD]     |
| Equal    | [TBD]        | [TBD]          | [TBD]       | [TBD]    | [TBD]     |
| Performance | [TBD]     | [TBD]          | [TBD]       | [TBD]    | [TBD]     |
| Query Type | [TBD]      | [TBD]          | [TBD]       | [TBD]    | [TBD]     |

### 3.2 단일 모델 대비 비교

**[평가 후 업데이트]**

| Model/Ensemble | Mean Speedup | Win Rate | Notes |
|----------------|--------------|----------|-------|
| DQN v3         | 1.15x        | ~35%     | Baseline |
| PPO v3         | 1.20x        | ~40%     | CTE 강점 |
| DDPG v1        | 1.88x        | ~40%     | 최고 성능 |
| SAC v1         | 1.50x        | ~38%     | 탐색 강화 |
| **Ensemble (Best)** | **[TBD]x** | **[TBD]%** | **목표: >2.0x** |

### 3.3 쿼리별 상세 분석

**[평가 후 업데이트]**

Top 10 개선 쿼리:
```
Query  Type         Strategy    Speedup    Notes
-----  ----------   ---------   -------    -----
[TBD]  [TBD]        [TBD]       [TBD]x     [TBD]
...
```

Bottom 5 쿼리 (성능 저하):
```
Query  Type         Strategy    Speedup    Notes
-----  ----------   ---------   -------    -----
[TBD]  [TBD]        [TBD]       [TBD]x     [TBD]
...
```

### 3.4 쿼리 타입별 성능

**[평가 후 업데이트]**

| Query Type | Best Strategy | Mean Speedup | Count |
|------------|---------------|--------------|-------|
| CTE        | [TBD]         | [TBD]x       | 3     |
| JOIN_HEAVY | [TBD]         | [TBD]x       | 11    |
| AGGREGATE  | [TBD]         | [TBD]x       | 4     |
| TOP        | [TBD]         | [TBD]x       | 10    |
| SUBQUERY   | [TBD]         | [TBD]x       | 3     |
| WINDOW     | [TBD]         | [TBD]x       | 1     |
| SIMPLE     | [TBD]         | [TBD]x       | 2     |

### 3.5 모델 합의도 (Agreement) 분석

**[평가 후 업데이트]**

- **평균 합의도**: [TBD]%
- **완전 합의 (4/4)**: [TBD]% of cases
- **다수 합의 (3/4)**: [TBD]% of cases
- **분산 (2/2)**: [TBD]% of cases

**해석**:
- 높은 합의도 → 명확한 최적 액션
- 낮은 합의도 → 쿼리가 복잡하거나 여러 최적 액션 존재

## 4. 시각화

### 4.1 Speedup 분포

![Speedup Distribution](results/charts/speedup_distribution.png)

### 4.2 쿼리별 성능

![Query Performance](results/charts/query_performance_weighted.png)

### 4.3 액션 사용 분포

![Action Distribution](results/charts/action_distribution_weighted.png)

### 4.4 모델 합의도

![Model Agreement](results/charts/model_agreement.png)

### 4.5 쿼리 타입별 성능

![Query Type Performance](results/charts/query_type_performance_weighted.png)

### 4.6 전략 비교

![Strategy Comparison](results/charts/strategy_comparison.png)

## 5. 강점 및 약점

### 5.1 강점

**[평가 후 분석]**

1. **안정성**: 단일 모델 대비 분산 감소
2. **적응성**: 쿼리 타입별 최적 전략 선택
3. **견고성**: 단일 모델 실패에 강함
4. **다양성**: Discrete + Continuous 모델 결합

### 5.2 약점

**[평가 후 분석]**

1. **추론 시간**: 4개 모델 실행으로 지연 증가
2. **메모리**: 4개 모델 로드 필요
3. **복잡도**: 단일 모델 대비 구현 및 유지보수 복잡
4. **Continuous → Discrete 변환**: 정보 손실 가능

## 6. 결론 및 향후 연구

### 6.1 주요 발견

**[평가 후 업데이트]**

1. Voting Ensemble은 단일 모델 대비 [TBD]% 성능 향상
2. [TBD] 전략이 가장 우수한 성능 달성
3. [TBD] 쿼리 타입에서 특히 효과적
4. 모델 간 합의도가 높을수록 성능 향상 폭이 큼

### 6.2 실무 적용 권장사항

**[평가 후 업데이트]**

1. **추천 전략**: [TBD]
2. **적용 시나리오**: [TBD]
3. **주의사항**: [TBD]

### 6.3 향후 연구 방향

1. **Meta-Learning**: 쿼리 특성 자동 분석 및 모델 선택
2. **Multi-Agent**: 순차적 협력 최적화
3. **Online Learning**: 실시간 피드백으로 가중치 조정
4. **Model Distillation**: 경량화된 단일 모델로 압축
5. **Adaptive Threshold**: 동적 confidence threshold 조정

## 7. 참고 자료

### 7.1 관련 문서

- DQN v3: `Apollo.ML/RLQO/DQN_v3/DQN_v3_Evaluation_Report.md`
- PPO v3: `Apollo.ML/RLQO/PPO_v3/PPO_v3_Evaluation_Report.md`
- DDPG v1: `Apollo.ML/RLQO/DDPG_v1/DDPG_v1_Evaluation_Report.md`
- SAC v1: `Apollo.ML/RLQO/SAC_v1/SAC_v1_Evaluation_Report.md`
- 초기 비교: `Apollo.ML/RLQO/Initial_Model_Comparison.md`

### 7.2 데이터 파일

- 평가 결과: `results/ensemble_voting_results.json`
- 전략 비교: `results/ensemble_comparison.csv`
- 상세 결과: `results/detailed_results.json`

### 7.3 코드

- Ensemble 구현: `ensemble_voting.py`
- 투표 전략: `voting_strategies.py`
- 평가 스크립트: `train/ensemble_evaluate.py`
- 시각화: `visualize_ensemble.py`

---

**보고서 버전**: 1.0  
**작성일**: [평가 후 업데이트]  
**작성자**: Apollo ML Team

