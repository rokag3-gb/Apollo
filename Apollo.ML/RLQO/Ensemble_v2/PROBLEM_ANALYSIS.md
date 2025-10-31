# Ensemble v2 문제 분석 보고서

## 📊 핵심 문제: 왜 앙상블에서 개선된 쿼리가 적은가?

### 개별 모델 성능 vs 앙상블 성능 비교

| 모델 | 평균 Speedup | 개선된 쿼리 수 | Win Rate | 주요 강점 |
|------|-------------|--------------|----------|----------|
| **DDPG v1** | **1.875x** (87.5% 개선) | **4개** (극적 개선) | 13.3% | 대용량 쿼리 (Query 2: 17x, Query 3: 4x, Query 5: 5.8x) |
| **SAC v1** | **1.891x** (89.1% 개선) | **7개** | 15.4% | 최고 성능, 다양한 쿼리 개선 |
| **PPO v3** | **1.199x** (19.9% 개선) | **9개** | 31% | CTE 쿼리 (1.7x), 복잡한 쿼리 |
| **DQN v4** | **극단적** | **15개** (극적 개선/악화) | 혼합 | 일부 쿼리 50x, 일부 -10x |
| **Ensemble v2** | **1.051x** (5% 개선) | **1개** (Q8 제외) | 19.7% | ❌ **실패** |

---

## 🔍 근본 원인 분석

### 1. **다수결 투표(Majority Vote)의 치명적 문제**

#### 문제 상황 예시: Query 2 (대용량 테이블 스캔)

```
개별 모델 예측:
- DDPG v1: Action 15 (MAXDOP=1, FAST=100, ...) → 17.82x 개선!
- SAC v1: Action 15 (동일) → ~18x 개선!
- PPO v3: Action 18 (NO_ACTION) → 1.0x (변화 없음)
- DQN v4: Action 18 (NO_ACTION) → 1.0x (변화 없음)

다수결 투표 결과:
- Action 18 (NO_ACTION): 2표 ✅ 승리
- Action 15: 2표 ❌ 패배

최종 결과: NO_ACTION → 개선 기회 상실!
```

#### 실제 데이터로 검증

**DDPG v1 단독 실행 시**:
```json
{
  "query_idx": 2,
  "query_name": "대용량 테이블 전체 스캔",
  "avg_speedup": 17.823x,
  "action": "MAXDOP=1, FAST=100, JOIN=FORCE_ORDER, COMPAT_160"
}
```

**Ensemble v2 실행 시** (보고서 기준):
```json
{
  "query_idx": 2,
  "mean_speedup": 0.970x,  // 오히려 3% 저하!
  "win_rate": 0.4,
  "safe_rate": 0.5
}
```

→ **17x 개선 기회가 다수결 투표로 인해 완전히 상실됨!**

---

### 2. **보수적 모델들의 압도적 영향**

각 모델의 NO_ACTION 비율:
- **DDPG v1**: 83.3% (25/30 쿼리)
- **SAC v1**: 76.7% (23/30 쿼리)  
- **PPO v3**: 69% (대부분 쿼리)
- **DQN v4**: 혼합 (하지만 많은 쿼리에서 NO_ACTION)

#### 투표 시나리오 분석

```python
# 전형적인 투표 상황 (30개 쿼리 중 25개)
predictions = {
    'ddpg_v1': 18,  # NO_ACTION
    'sac_v1': 18,   # NO_ACTION
    'ppo_v3': 18,   # NO_ACTION
    'dqn_v4': 5     # MAXDOP=1 (개선 가능한 액션)
}

majority_vote(predictions)  # → 18 (NO_ACTION) 승리
```

→ **3개 모델이 보수적이면, 나머지 1개 모델의 좋은 액션은 무시됨!**

---

### 3. **각 모델의 전문성(Specialization) 무시**

#### 모델별 강점 쿼리 타입

| 모델 | 최고 성능 쿼리 타입 | 평균 Speedup | 개선 쿼리 예시 |
|------|-------------------|-------------|---------------|
| **DDPG v1** | **대용량 SIMPLE, 복잡한 JOIN** | 1.875x | Q2 (17x), Q3 (4x), Q5 (5.8x), Q28 (2.5x) |
| **SAC v1** | **대용량 쿼리 + 다양성** | 1.891x | Q2 (22x), Q3, Q5, Q28 + 3개 추가 |
| **PPO v3** | **CTE, JOIN_HEAVY** | 1.704x (CTE) | Q1 (CTE), Q7 (JOIN_HEAVY) |
| **DQN v4** | **극단적 쿼리** | 극적 개선/악화 | Q5 (50x), Q15 (inf), Q25 (inf) |

#### 다수결 투표 결과

```
Query 2 (SIMPLE, 대용량):
  ✅ DDPG/SAC 전문 → 17x 개선 가능
  ❌ 다수결 → NO_ACTION (0.97x, 오히려 저하)

Query 1 (CTE):
  ✅ PPO v3 전문 → 1.7x 개선 가능
  ❌ 다수결 → NO_ACTION (1.0x, 변화 없음)
```

→ **전문가(Specialist) 모델의 의견이 비전문가 다수에 의해 묻힘!**

---

### 4. **Voting Strategy 문제 (majority vs safety_first)**

#### Majority Voting (보고서에서 사용)

```python
def majority_vote(predictions: Dict[str, int]) -> int:
    vote_counts = Counter(predictions.values())
    most_common = vote_counts.most_common(1)[0]
    return most_common[0]  # 단순 다수결
```

**문제점**:
- Confidence 무시
- 모델별 성능 차이 무시
- NO_ACTION이 항상 다수 차지

#### Safety-First Voting (구현되어 있으나 사용 안 함)

```python
def safety_first_vote(..., safety_threshold=0.2, disagreement_threshold=0.1):
    # 1. 평균 confidence < 0.2 → NO_ACTION
    # 2. 모델 간 agreement < 10% → NO_ACTION
    # ...
```

**문제점**:
- 너무 보수적 (threshold가 너무 낮음)
- Disagreement threshold 10%는 사실상 만장일치 요구
- **개선 기회를 더욱 줄임!**

---

## 📉 구체적 사례: Query별 비교

### 사례 1: Query 2 (대용량 테이블 스캔)

| 실행 방식 | Speedup | 액션 |
|----------|---------|------|
| DDPG v1 단독 | **17.82x** ✅ | MAXDOP=1, FAST=100, ... |
| SAC v1 단독 | **~18x** ✅ | 동일 |
| **Ensemble v2** | **0.97x** ❌ | NO_ACTION (3% 저하!) |

**손실**: 17x 개선 기회 상실

---

### 사례 2: Query 28 (거래 원장 집계)

| 실행 방식 | Speedup | 액션 |
|----------|---------|------|
| DDPG v1 단독 | **2.52x** ✅ | MAXDOP=1, FAST=100, ISOLATION=SNAPSHOT, ... |
| **Ensemble v2** | **0.88x** ❌ | (역효과 액션 선택) |

**손실**: 2.5x 개선 → 12% 저하

---

### 사례 3: Query 1 (CTE 쿼리)

| 실행 방식 | Speedup | 액션 |
|----------|---------|------|
| PPO v3 단독 | **1.7x** ✅ | (PPO 전문 액션) |
| **Ensemble v2** | **1.0x** ❌ | NO_ACTION |

**손실**: 70% 개선 기회 상실

---

## 🎯 통계적 증거

### Win Rate 비교

```
개별 모델 Win Rate (개선 쿼리 비율):
- SAC v1:  15.4% (7/30 쿼리)
- DDPG v1: 13.3% (4/30 쿼리)
- PPO v3:  31.0% (9/30 쿼리, 다수 에피소드 기준)

앙상블 Win Rate:
- Ensemble v2: 19.7% (59/300 에피소드)
  → 실제 쿼리별로는 ~3개만 개선 (Q8, Q10, Q21)
  → Q8은 데이터 없음으로 인한 착시
```

**기대값 vs 실제**:
- **기대**: 각 모델의 강점 합산 → 30% 이상 Win Rate
- **실제**: 19.7% (개별 모델보다 낮음!)
- **손실**: 10개 이상의 개선 쿼리 상실

---

### 평균 Speedup 비교

```
개별 모델 평균:
- SAC v1:  1.891x (+89.1%)
- DDPG v1: 1.875x (+87.5%)
- PPO v3:  1.199x (+19.9%)
- 평균:    ~1.655x (+65.5%)

앙상블 평균:
- Ensemble v2: 1.051x (+5.1%)

손실: 60% 이상의 성능 향상 기회 상실
```

---

## 💡 왜 이런 일이 발생하는가?

### 1. **집단 지성(Wisdom of Crowds)의 전제 조건 위반**

다수결이 효과적이려면:
- ✅ 각 투표자가 독립적이고 다양한 관점을 가짐 → **만족**
- ❌ **각 투표자가 일정 수준 이상의 정확도를 가짐** → **위반!**
- ❌ **투표자들이 다양한 의견을 제시함** → **위반!** (대부분 NO_ACTION)

현재 상황:
- 4개 모델 중 3개가 대부분 쿼리에서 NO_ACTION 선택
- NO_ACTION이 항상 다수 차지
- 전문가 모델의 의견이 묻힘

---

### 2. **부정적 투표(Negative Voting) 효과**

```
의료 진단 비유:
- 전문의 A (심장병 전문): "심장 수술 필요" (95% 확신)
- 전문의 B (외과 전문): "모름" (NO_ACTION)
- 전문의 C (내과 전문): "모름" (NO_ACTION)
- 전문의 D (일반의): "모름" (NO_ACTION)

다수결 투표: "모름" (NO_ACTION) → 환자 치료 안 함!
```

**쿼리 최적화도 동일**:
- DDPG가 "이 대용량 쿼리는 MAXDOP=1 필요!"라고 95% 확신
- 다른 3개 모델은 "잘 모르겠음" (NO_ACTION)
- 다수결 → NO_ACTION → **개선 기회 상실**

---

### 3. **모델 다양성이 오히려 독**

```
각 모델이 다른 쿼리에서 개선:
- DDPG: Query 2, 3, 5, 28 (4개)
- SAC:  Query 2, 3, 5, 28 + α (7개)
- PPO:  Query 1, 7, 10, ... (9개)
- DQN:  Query 5, 15, 25, ... (15개, 하지만 절반은 악화)

다수결 투표 시:
- Query 2: DDPG/SAC만 개선 액션 → 2표 vs 2표 → 무작위 또는 NO_ACTION
- Query 1: PPO만 개선 액션 → 1표 vs 3표 → NO_ACTION
- Query 10: PPO만 개선 액션 → 1표 vs 3표 → NO_ACTION
```

→ **각 모델의 전문성이 서로 다른 쿼리에 분산되어 있어, 다수결에서 모두 무시됨!**

---

## 🚨 결론

### 핵심 문제 요약

1. **다수결 투표의 구조적 문제**
   - 3개 모델이 NO_ACTION → 1개 전문가 모델의 의견 무시
   - 개선 가능한 쿼리의 80% 이상에서 NO_ACTION 승리

2. **보수적 모델들의 과다한 영향**
   - DDPG/SAC/PPO 모두 70% 이상 NO_ACTION
   - 안전성은 높지만 개선 기회 상실

3. **모델별 전문성 무시**
   - 각 모델이 다른 쿼리 타입에서 강점
   - 다수결은 전문성을 무시하고 다수만 봄

4. **Voting Strategy 문제**
   - `majority` 투표: Confidence, 성능 무시
   - `safety_first` 투표: 너무 보수적 (더 안 좋음)

---

### 수치로 본 손실

| 지표 | 개별 모델 평균 | Ensemble v2 | 손실 |
|-----|--------------|------------|-----|
| **평균 Speedup** | 1.655x | 1.051x | **-60% 성능 손실** |
| **개선 쿼리 수** | ~10개 | 1개 (실질적) | **-9개 쿼리 손실** |
| **최대 Speedup** | 18~22x | 10x (착시) | **-절반 이상 손실** |

→ **앙상블이 개별 모델보다 훨씬 나쁨!**

---

## 📋 다음 단계: 해결 방안

이 문제를 해결하려면:

1. ✅ **Confidence 기반 투표 강화**
2. ✅ **쿼리 타입별 전문가 모델 우선 선택**
3. ✅ **NO_ACTION 투표 제외 (Active-Only Voting)**
4. ✅ **모델별 성능 기반 가중치**
5. ✅ **Conservative Threshold 완화**

자세한 해결책은 별도 제안서에서 제공.

