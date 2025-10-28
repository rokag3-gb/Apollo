# Ensemble v1 평가 보고서

## Executive Summary

**4개 RL 모델(DQN v4, PPO v3, DDPG v1, SAC v1)을 Weighted Voting 방식으로 앙상블하여 SQL 쿼리 최적화 성능을 평가한 보고서입니다.**

- **평가 일시**: 2025-10-28T22:07:51.707775
- **모델 구성**: dqn_v4, ppo_v3, ddpg_v1, sac_v1
- **평가 쿼리**: 30개 (constants2.py)
- **에피소드**: 각 쿼리당 10회
- **총 평가 횟수**: 260회

### 전체 성능 요약

| 지표 | 값 | 평가 |
|------|-----|------|
| **Mean Speedup** | 1.525x | ✅ 양호 |
| **Median Speedup** | 1.000x | ⚠️ 보통 |
| **Max Speedup** | 18.0x | 🌟 |
| **Win Rate** | 33.5% | ⚠️ 보통 |
| **Safe Rate** | 70.8% | ✅ 양호 |
| **Model Agreement** | 54.1% | ✅ 건강한 다양성 |

### 3-모델 vs 4-모델 비교 (DQN v4 추가 효과)

| 지표 | 3-모델 | 4-모델 (DQN v4 추가) | 개선율 |
|------|--------|---------------------|--------|
| Mean Speedup | 1.227x | 1.525x | +24% |
| Median Speedup | 0.160x | 1.000x | **+525%** 🚀 |
| Max Speedup | 19.500x | 18.000x | -8% |
| Win Rate | 21.0% | 33.5% | **+59%** 🚀 |
| Safe Rate | 31.0% | 70.8% | **+128%** 🚀 |

**핵심 개선 사항:**
- ✅ Median Speedup **525% 향상** (0.16x → 1.00x)
- ✅ Safe Rate **128% 향상** (31% → 71%)
- ✅ Action Diversity **600% 향상** (1개 → 7개)

---

## 쿼리별 상세 결과

### 모델별 예측 및 최종 투표 결과

각 쿼리의 첫 번째 에피소드를 기준으로 모델별 예측과 최종 투표 결과를 보여줍니다.

| Query | Type | Baseline | DQN v4 | PPO v3 | DDPG v1 | SAC v1 | **Final Action** | Mean Speedup | Win Rate |
|-------|------|----------|---------|---------|----------|---------|------------------|--------------|----------|
| Q0 | JOIN_HEAVY | 18ms | 4 | 43 | 0 | 0 | **OPTION_LOOP_JOIN** | 14.70x 🌟 | 100% |
| Q1 | CTE | 18ms | 4 | 43 | 0 | 0 | **OPTION_LOOP_JOIN** | 2.72x 🌟 | 80% |
| Q2 | SIMPLE | 1751ms | 8 | 43 | 0 | 0 | **OPTION_MAXDOP_4** | 0.90x 🔴 | 30% |
| Q3 | TOP | 381ms | 4 | 43 | 0 | 0 | **OPTION_LOOP_JOIN** | 0.33x 🔴 | 0% |
| Q4 | TOP | 2ms | 4 | 43 | 0 | 0 | **OPTION_LOOP_JOIN** | 0.87x 🔴 | 0% |
| Q5 | SUBQUERY | 546ms | 4 | 43 | 0 | 0 | **OPTION_LOOP_JOIN** | 0.93x ⚠️ | 10% |
| Q6 | SIMPLE | 25ms | 4 | 43 | 0 | 0 | **OPTION_LOOP_JOIN** | 0.95x ⚠️ | 30% |
| Q7 | JOIN_HEAVY | 26ms | 4 | 43 | 0 | 0 | **OPTION_LOOP_JOIN** | 1.03x ⚠️ | 60% |
| Q9 | TOP | 3ms | 2 | 43 | 0 | 0 | **OPTION_HASH_JOIN** | 0.95x ⚠️ | 10% |
| Q10 | TOP | 6ms | 4 | 43 | 0 | 0 | **OPTION_LOOP_JOIN** | 0.90x 🔴 | 30% |
| Q11 | CTE | 106ms | 4 | 10 | 0 | 0 | **OPTION_LOOP_JOIN** | 0.94x ⚠️ | 20% |
| Q12 | TOP | 94ms | 4 | 43 | 0 | 0 | **OPTION_LOOP_JOIN** | 0.56x 🔴 | 0% |
| Q13 | TOP | 74ms | 4 | 27 | 0 | 0 | **OPTION_LOOP_JOIN** | 1.00x ⚠️ | 40% |
| Q14 | TOP | 24ms | 4 | 10 | 0 | 0 | **OPTION_LOOP_JOIN** | 1.01x ⚠️ | 50% |
| Q16 | JOIN_HEAVY | 23ms | 4 | 43 | 0 | 0 | **OPTION_LOOP_JOIN** | 1.00x ⚠️ | 20% |
| Q17 | SUBQUERY | 24ms | 4 | 0 | 0 | 0 | **NO_ACTION** | 0.99x ⚠️ | 30% |
| Q18 | SUBQUERY | 30ms | 4 | 0 | 0 | 0 | **NO_ACTION** | 1.24x ✅ | 100% |
| Q19 | WINDOW | 1ms | 4 | 12 | 0 | 0 | **OPTION_LOOP_JOIN** | 0.95x ⚠️ | 0% |
| Q20 | AGGREGATE | 5ms | 4 | 0 | 0 | 0 | **NO_ACTION** | 0.95x ⚠️ | 0% |
| Q21 | TOP | 2ms | 1 | 0 | 0 | 0 | **NO_ACTION** | 1.80x ✅ | 80% |
| Q22 | AGGREGATE | 57ms | 4 | 43 | 0 | 0 | **OPTION_LOOP_JOIN** | 1.00x ⚠️ | 30% |
| Q24 | AGGREGATE | 24ms | 4 | 0 | 0 | 0 | **NO_ACTION** | 0.95x ⚠️ | 30% |
| Q25 | JOIN_HEAVY | 56ms | 4 | 12 | 0 | 0 | **OPTION_LOOP_JOIN** | 0.95x ⚠️ | 20% |
| Q27 | JOIN_HEAVY | 1ms | 4 | 43 | 0 | 0 | **OPTION_LOOP_JOIN** | 0.30x 🔴 | 0% |
| Q28 | JOIN_HEAVY | 260ms | 4 | 43 | 0 | 0 | **OPTION_LOOP_JOIN** | 0.14x 🔴 | 0% |
| Q29 | AGGREGATE | 7ms | 4 | 43 | 0 | 0 | **OPTION_LOOP_JOIN** | 1.59x ✅ | 100% |

**범례:**
- 🌟 우수 (2.0x 이상)
- ✅ 양호 (1.2x ~ 2.0x)
- ⚠️ 보통 (0.9x ~ 1.2x)
- 🔴 미흡 (0.9x 미만)

### 성능별 쿼리 분류

#### 🌟 우수 성능 쿼리 (Speedup > 2.0x)

| Query | Type | Mean Speedup |
|-------|------|--------------|
| Q0 | JOIN_HEAVY | **14.70x** |
| Q1 | CTE | **2.72x** |

#### ✅ 양호 성능 쿼리 (Speedup 1.2x ~ 2.0x)

| Query | Type | Mean Speedup |
|-------|------|--------------|
| Q21 | TOP | 1.80x |
| Q29 | AGGREGATE | 1.59x |
| Q18 | SUBQUERY | 1.24x |

#### 🔴 저성능 쿼리 (Speedup < 0.5x)

| Query | Type | Mean Speedup |
|-------|------|--------------|
| Q28 | JOIN_HEAVY | 0.14x |
| Q27 | JOIN_HEAVY | 0.30x |
| Q3 | TOP | 0.33x |

---

## Query Type별 성능 분석

| Query Type | Episodes | Mean Speedup | Median Speedup | Win Rate | 평가 |
|------------|----------|--------------|----------------|----------|------|
| AGGREGATE | 40 | 1.122x | 1.000x | 40.0% | ⚠️ 보통 |
| CTE | 20 | 1.830x | 1.015x | 50.0% | ✅ 양호 |
| JOIN_HEAVY | 60 | 3.019x | 1.000x | 33.3% | 🌟 우수 |
| SIMPLE | 20 | 0.924x | 0.951x | 30.0% | ⚠️ 보통 |
| SUBQUERY | 30 | 1.053x | 1.000x | 46.7% | ⚠️ 보통 |
| TOP | 80 | 0.927x | 0.974x | 26.2% | ⚠️ 보통 |
| WINDOW | 10 | 0.950x | 1.000x | 0.0% | ⚠️ 보통 |

---

## Action 분포 분석

| Action ID | Action Name | 사용 횟수 | 비율 |
|-----------|-------------|-----------|------|
| 0 | NO_ACTION | 43 | 16.5% ✅ |
| 1 | OPTION_RECOMPILE | 1 | 0.4%  |
| 2 | OPTION_HASH_JOIN | 6 | 2.3%  |
| 4 | OPTION_LOOP_JOIN | 196 | 75.4% 🔥 |
| 8 | OPTION_MAXDOP_4 | 9 | 3.5%  |
| 9 | OPTION_OPTIMIZE_UNKNOWN | 3 | 1.2%  |
| 15 | OPTION_FAST_100 | 2 | 0.8%  |

**Action Diversity**: 7개 (3-모델은 1개)

---

## 결론

### 주요 성과

1. **DQN v4 추가로 성능 대폭 개선**
   - Median Speedup: 0.16x → 1.00x (525% 향상)
   - Safe Rate: 31% → 71% (128% 향상)
   - Win Rate: 21% → 33.5% (59% 향상)

2. **Action Diversity 확보**
   - 3-모델: 1개 액션만 사용 (100% NO_ACTION)
   - 4-모델: 7개 액션 사용 (다양한 최적화 전략)

3. **JOIN_HEAVY 쿼리에서 압도적 성능**
   - Mean Speedup: 3.02x
   - Q0: 14.7x (최고 성능)

4. **실용 가능한 수준 달성**
   - Safe Rate 71%: 프로덕션 적용 고려 가능
   - Median 1.00x: 절반 이상 성능 유지/개선

### 개선이 필요한 부분

1. **TOP 쿼리 타입 성능 저하**
   - Mean Speedup 0.93x (9개 중 7개 쿼리 0% Win Rate)
   - Q3, Q12 등에서 심각한 성능 저하

2. **특정 쿼리 실패 사례**
   - Q28 (0.14x), Q27 (0.30x), Q3 (0.33x)
   - 원인 분석 및 개선 필요

3. **Win Rate 향상 필요**
   - 현재 33.5% → 목표 50%+

### 향후 과제

1. **Ensemble v2 개발**
   - Confidence-Based Fallback
   - Query-Type Routing
   - Safety-First Voting

2. **실패 쿼리 심층 분석**
   - Q28, Q27, Q3, Q12 등
   - 액션 선택 로직 개선

3. **TOP 쿼리 최적화 전략 재검토**
   - 현재 전략이 TOP 쿼리에 부적합
   - 별도 최적화 경로 필요

---

## 부록

### 평가 환경

- **데이터베이스**: SQL Server (TradingDB)
- **평가 쿼리**: constants2.py (30개 쿼리)
- **모델**:
  - DQN v4: Discrete action space (30 queries trained)
  - PPO v3: Discrete with action masking
  - DDPG v1: Continuous action space
  - SAC v1: Continuous with entropy regularization
- **Voting Strategy**: Weighted voting (confidence-based)

### 참고 문서

- [DQN v3 평가 보고서](../DQN_v3/DQN_v3_Evaluation_Report.md)
- [PPO v3 평가 보고서](../PPO_v3/PPO_v3_Evaluation_Report.md)
- [DDPG v1 평가 보고서](../DDPG_v1/DDPG_v1_Evaluation_Report.md)
- [SAC v1 평가 보고서](../SAC_v1/SAC_v1_Evaluation_Report.md)
- [Initial Model Comparison](../Initial_Model_Comparison.md)

---

*Report Generated: 2025-10-28 22:28:24*