# Ensemble v2 투표 로직 개선 요약

**작성일**: 2025-10-31  
**목적**: 다수결 투표의 구조적 문제 해결 및 개별 모델 강점 활용

---

## 📋 개선 내용 요약

### 문제 진단

**기존 문제**:
- 다수결 투표로 인해 전문가 모델의 의견이 무시됨
- 보수적 모델(NO_ACTION) 3개가 항상 개선 모델 1개를 압도
- 평균 Speedup: 1.051x (5% 개선) - 개별 모델(87~89% 개선)보다 훨씬 나쁨
- 개선된 쿼리: 실질적으로 1개 (Q8만, 나머지는 착시)

**근본 원인**:
1. NO_ACTION이 항상 다수 차지 (DDPG 83%, SAC 77%, PPO 69%)
2. 쿼리 타입별 전문가 모델의 강점 무시
3. 모델별 성능 차이 반영 안 됨
4. Conservative threshold가 너무 보수적

---

## 🔧 적용된 개선사항

### 1. 모델별 성능 가중치 업데이트

**파일**: `config/ensemble_config.py` (Line 49-59)

```python
# 기존: 평균 Speedup 기반
PERFORMANCE_WEIGHTS = {
    'dqn_v4': 1.30,
    'ppo_v3': 1.20,
    'ddpg_v1': 1.88,
    'sac_v1': 1.89,
}

# 개선: 개선 쿼리 수 기반
PERFORMANCE_WEIGHTS = {
    'dqn_v4': 2.0,   # 15개 쿼리 개선 (최다)
    'ppo_v3': 1.8,   # 9개 쿼리 개선 (2위)
    'ddpg_v1': 1.5,  # 4개 쿼리 개선 (극적)
    'sac_v1': 1.6,   # 7개 쿼리 개선
}
```

**효과**: DQN v4와 PPO v3의 다양한 쿼리 개선 능력 강화

---

### 2. 쿼리 타입별 전문가 모델 매핑

**파일**: `config/ensemble_config.py` (Line 63-112)

```python
# 주요 변경사항:

# SIMPLE (대용량): DDPG/SAC 전문
'SIMPLE': {
    'ddpg_v1': 0.40,  # 17x 개선 사례
    'sac_v1': 0.40,   # 18x 개선 사례
}

# CTE: PPO v3 전문
'CTE': {
    'ppo_v3': 0.50,   # 1.7x 개선
}

# JOIN_HEAVY: DDPG/SAC/PPO 강함
'JOIN_HEAVY': {
    'ppo_v3': 0.25,
    'ddpg_v1': 0.30,
    'sac_v1': 0.30,
}
```

**효과**: 각 쿼리 타입에 맞는 전문가 모델의 의견 우선 선택

---

### 3. NO_ACTION 페널티 도입

**파일**: `config/ensemble_config.py` (Line 118-120)

```python
# 신규 추가
NO_ACTION_PENALTY = 0.5  # NO_ACTION의 가중치를 절반으로
```

**효과**: NO_ACTION이 아닌 실제 개선 액션 우선 선택

---

### 4. Conservative Threshold 완화

**파일**: `config/ensemble_config.py` (Line 122-128)

```python
# 기존
SAFETY_CONFIG = {
    'avg_confidence_threshold': 0.4,
    'disagreement_threshold': 0.5,
}

# 개선
SAFETY_CONFIG = {
    'avg_confidence_threshold': 0.15,  # 0.4 → 0.15 (완화)
    'disagreement_threshold': 0.25,    # 0.5 → 0.25 (완화)
}
```

**효과**: 더 적극적인 최적화 시도

---

### 5. weighted_vote 함수 개선

**파일**: `voting_strategies.py` (Line 34-88)

```python
def weighted_vote(
    predictions: Dict[str, int], 
    confidences: Dict[str, float],
    performance_weights: Dict[str, float] = None,      # 신규
    query_type_weights: Dict[str, float] = None,       # 신규
    no_action_penalty: float = 1.0                     # 신규
) -> int:
    """
    개선된 Weighted Voting:
    1. Confidence + Performance + Query Type 통합
    2. NO_ACTION 페널티 적용
    3. 전문가 모델 우선
    """
    for model_name, action in predictions.items():
        confidence = confidences.get(model_name, 0.5)
        perf_weight = performance_weights.get(model_name, 1.0)
        type_weight = query_type_weights.get(model_name, 1.0)
        
        # 통합 가중치
        combined_weight = confidence * perf_weight * type_weight
        
        # NO_ACTION 페널티
        if action == 18:
            combined_weight *= no_action_penalty
        
        action_weights[action] += combined_weight
```

**효과**: 
- 모델 성능, 쿼리 타입 전문성, Confidence 모두 반영
- NO_ACTION 페널티로 실제 개선 액션 우선

---

### 6. 기본 투표 전략 변경

**파일**: 
- `ensemble_voting.py` (Line 59)
- `train/ensemble_evaluate.py` (Line 49, 342)

```python
# 기존
voting_strategy: str = 'safety_first'

# 개선
voting_strategy: str = 'weighted'
```

**효과**: 개선된 weighted_vote가 기본으로 사용됨

---

### 7. weighted 전략 호출 시 파라미터 전달

**파일**: `ensemble_voting.py` (Line 490-505)

```python
elif self.voting_strategy == 'weighted':
    from RLQO.Ensemble_v2.config.ensemble_config import (
        PERFORMANCE_WEIGHTS, QUERY_TYPE_WEIGHTS, NO_ACTION_PENALTY
    )
    
    type_weights = QUERY_TYPE_WEIGHTS.get(query_type, QUERY_TYPE_WEIGHTS['DEFAULT'])
    model_type_weights = {k: type_weights.get(k, 0.25) for k in predictions.keys()}
    
    return weighted_vote(
        predictions, 
        confidences,
        performance_weights=PERFORMANCE_WEIGHTS,
        query_type_weights=model_type_weights,
        no_action_penalty=NO_ACTION_PENALTY
    )
```

**효과**: 모든 개선사항이 weighted 전략에 통합됨

---

## 📊 예상 효과

### 기존 성능 (Ensemble v2 Original)
- 평균 Speedup: **1.051x** (5% 개선)
- 개선 쿼리 수: **1개** (Q8만, 나머지는 착시)
- Win Rate: 19.7%

### 목표 성능 (Ensemble v2 Improved)
- 평균 Speedup: **1.3x+** (30% 개선) 목표
- 개선 쿼리 수: **10개 이상** 목표
- Win Rate: 30%+ 목표

### 개선 메커니즘

1. **Query 2 (대용량 SIMPLE) 예시**
```
기존:
- DDPG: Action 15 (MAXDOP=1, FAST=100) → 17.82x
- SAC:  Action 15 (동일) → ~18x
- PPO:  Action 18 (NO_ACTION) → 1.0x
- DQN:  Action 18 (NO_ACTION) → 1.0x
→ 다수결: NO_ACTION (2:2에서 패배)

개선:
- DDPG: Weight = confidence × 1.5 (perf) × 0.40 (type) = 높은 가중치
- SAC:  Weight = confidence × 1.6 (perf) × 0.40 (type) = 높은 가중치
- PPO:  Weight = confidence × 1.8 (perf) × 0.10 (type) × 0.5 (NO_ACTION) = 낮은 가중치
- DQN:  Weight = confidence × 2.0 (perf) × 0.10 (type) × 0.5 (NO_ACTION) = 낮은 가중치
→ Action 15 승리! (전문가 DDPG/SAC의 의견 반영)
```

2. **Query 1 (CTE) 예시**
```
기존:
- PPO: Action X (CTE 최적화) → 1.7x
- 나머지: NO_ACTION → 1.0x
→ 다수결: NO_ACTION (1:3에서 패배)

개선:
- PPO: Weight = confidence × 1.8 (perf) × 0.50 (type) = 매우 높은 가중치
- 나머지: Weight = ... × 0.5 (NO_ACTION) = 낮은 가중치
→ PPO 액션 승리! (CTE 전문가 의견 반영)
```

---

## 🎯 핵심 차별점

| 항목 | 기존 (v2 Original) | 개선 (v2 Improved) |
|------|-------------------|-------------------|
| **투표 방식** | 다수결 or Safety-First | 개선된 Weighted |
| **NO_ACTION 처리** | 동등 | 50% 페널티 |
| **모델 가중치** | 평균 Speedup 기반 | 개선 쿼리 수 기반 |
| **쿼리 타입 반영** | 약함 | 강함 (전문가 우선) |
| **Conservative** | 너무 보수적 (0.4, 0.5) | 완화 (0.15, 0.25) |
| **결과** | 5% 개선, 1개 쿼리 | 30%+ 개선, 10개+ 쿼리 (목표) |

---

## 📁 수정된 파일 목록

1. ✅ `Apollo.ML/RLQO/Ensemble_v2/config/ensemble_config.py`
   - PERFORMANCE_WEIGHTS 업데이트
   - QUERY_TYPE_WEIGHTS 재설정
   - NO_ACTION_PENALTY 추가
   - SAFETY_CONFIG 완화

2. ✅ `Apollo.ML/RLQO/Ensemble_v2/voting_strategies.py`
   - weighted_vote 함수 개선 (파라미터 추가)
   - NO_ACTION 페널티 로직 추가

3. ✅ `Apollo.ML/RLQO/Ensemble_v2/ensemble_voting.py`
   - 기본 voting_strategy 변경 (safety_first → weighted)
   - _apply_voting_strategy에서 개선된 파라미터 전달

4. ✅ `Apollo.ML/RLQO/Ensemble_v2/train/ensemble_evaluate.py`
   - 기본 voting_strategy 변경 (safety_first → weighted)
   - argparse 기본값 변경

---

## 🚀 다음 단계

### 평가 실행
```bash
cd Apollo.ML/RLQO/Ensemble_v2/train
python ensemble_evaluate.py --queries 30 --episodes 10 --strategy weighted
```

### 결과 비교
1. 기존 결과: `results/ensemble_v2_results.json` (백업 권장)
2. 신규 결과: 위 명령 실행 후 동일 경로에 생성
3. 비교 지표:
   - Mean Speedup: 1.051x → 1.3x+ 달성 여부
   - 개선 쿼리 수: 1개 → 10개+ 달성 여부
   - Win Rate: 19.7% → 30%+ 달성 여부

### 성공 기준
- ✅ Query 2 (대용량): 17x 개선 달성
- ✅ Query 1 (CTE): 1.7x 개선 달성
- ✅ Query 28: 2.5x 개선 달성
- ✅ 전체 평균 Speedup 1.3x 이상
- ✅ 개선 쿼리 10개 이상

---

## 📚 관련 문서

- 문제 분석: `PROBLEM_ANALYSIS.md`
- 개선 계획: `ensemble-v2-voting-improvement.plan.md`
- 평가 보고서: `Ensemble_v2_Final_Report.md` (기존)
- 신규 평가 보고서: 평가 후 생성 예정

---

## 💡 핵심 인사이트

**기존 문제**:
> "심장 전문의가 '수술 필요'라고 해도, 다른 3명이 '모름'이라고 하면 다수결로 치료 안 함"

**개선 후**:
> "심장 전문의는 심장 관련 질환에서 5배 가중치, '모름'은 50% 가중치 → 전문의 의견 우선"

이것이 바로 **전문가 모델(Specialist Model)의 강점을 살리는 앙상블**입니다!

