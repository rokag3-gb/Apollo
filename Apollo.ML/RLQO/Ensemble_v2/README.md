# Ensemble v2: Advanced SQL Query Optimization Ensemble

Ensemble v1의 문제점을 개선하여 안전성 우선, TOP 쿼리 성능 개선, DDPG/SAC 활성화를 달성한 앙상블 시스템입니다.

## 🎯 주요 개선사항

### 1. Continuous-to-Discrete 변환 로직 개선 ⭐
**문제**: v1에서 DDPG v1, SAC v1이 모든 쿼리에서 NO_ACTION(0)만 예측 (변환 실패)

**해결**: 
- 우선순위 기반 변환 로직 구현
- DDPG/SAC의 7차원 continuous action을 DQN v4의 discrete action ID로 정확하게 매핑
- JOIN HINT → FAST N → MAXDOP → ... 순서로 중요도 기반 변환

### 2. Safety-First Voting
- 평균 confidence < 0.4 → NO_ACTION
- 모델 간 disagreement > 50% → NO_ACTION
- 안전성을 최우선으로 고려

### 3. TOP 쿼리 최적화
- LOOP_JOIN 억제 (v1에서 과다 사용)
- FAST 힌트 선호
- NO_ACTION confidence 증폭

### 4. Action Validation & Filtering
- Baseline < 10ms → MAXDOP 제외
- 쿼리 타입별 부적합 액션 차단
- 과거 실패 패턴 학습 및 회피

## 📁 디렉토리 구조

```
Ensemble_v2/
├── config/
│   ├── __init__.py
│   └── ensemble_config.py              # 4-모델 구성 (DQN v4, PPO v3, DDPG v1, SAC v1)
├── action_converter.py                 # Continuous → Discrete 변환 ⭐
├── voting_strategies.py                # Safety-first voting
├── query_type_router.py                # TOP 쿼리 전용 처리
├── action_validator.py                 # Action 검증/필터링
├── ensemble_voting.py                  # 메인 ensemble 클래스
├── train/
│   ├── __init__.py
│   └── ensemble_evaluate.py            # 평가 스크립트
├── generate_report.py                  # 보고서 생성
├── results/                            # 평가 결과
└── README.md
```

## 🚀 사용 방법

### 1. 평가 실행

```bash
cd Apollo.ML/RLQO/Ensemble_v2

# 기본 평가 (30개 쿼리, 10 episodes)
python train/ensemble_evaluate.py

# 커스텀 설정
python train/ensemble_evaluate.py --queries 30 --episodes 10 --strategy safety_first

# 다른 투표 전략 시도
python train/ensemble_evaluate.py --strategy weighted
python train/ensemble_evaluate.py --strategy performance
```

### 2. 보고서 생성

```bash
# v2 결과만
python generate_report.py --v2-results results/ensemble_v2_results.json

# v1 대비 비교
python generate_report.py \
    --v2-results results/ensemble_v2_results.json \
    --v1-results ../Ensemble_v1/results/ensemble_4models_30queries.json \
    --output results/Ensemble_v2_Final_Report.md
```

### 3. Python 코드에서 사용

```python
from RLQO.Ensemble_v2.ensemble_voting import VotingEnsembleV2

# Ensemble 생성
ensemble = VotingEnsembleV2(
    voting_strategy='safety_first',
    use_action_validator=True,
    use_query_router=True,
    verbose=True
)

# 모델 로드
ensemble.load_models()

# 예측
action, info = ensemble.predict(
    observation=obs,
    query_type='TOP',
    query_info={'baseline_ms': 100.0},
    action_mask=action_mask
)

# 결과 기록 (실패 패턴 학습)
ensemble.record_action_result('TOP', action, speedup=1.2)

# 통계 출력
ensemble.print_stats()
```

## 📊 예상 성과

| 지표 | v1 | v2 목표 | 비고 |
|------|-----|---------|------|
| **Safe Rate** | 71% | 85%+ | 안전성 우선 |
| **TOP 쿼리** | 0.93x | 1.05x+ | 가장 큰 문제 해결 |
| **실패 케이스** | 3개 | 1개 이하 | Speedup < 0.5x |
| **DDPG/SAC** | NO_ACTION만 | 정상 작동 | 변환 로직 개선 |
| **Action Diversity** | 7개 | 10개+ | 더 다양한 최적화 |

## 🔧 주요 컴포넌트

### ContinuousToDiscreteConverter
DDPG/SAC의 continuous action [0~1]^7을 discrete action ID로 변환

```python
converter = ContinuousToDiscreteConverter()
discrete_action = converter.convert(continuous_action)
```

### QueryTypeRouter
쿼리 타입별로 적합한 액션 필터링

```python
router = QueryTypeRouter()
filtered, _ = router.filter_actions_for_query('TOP', predictions)
```

### ActionValidator
액션의 안전성 검증 및 과거 실패 패턴 학습

```python
validator = ActionValidator()
is_safe, reason = validator.is_safe_action(action_id, query_info)
validator.record_action_result(query_type, action_id, speedup)
```

## 🧪 테스트

각 컴포넌트에는 자체 테스트 코드가 포함되어 있습니다:

```bash
# Converter 테스트
python action_converter.py

# Router 테스트
python query_type_router.py

# Validator 테스트
python action_validator.py
```

## 📈 v1 vs v2 주요 차이점

| 항목 | v1 | v2 |
|------|-----|-----|
| **모델 구성** | 4개 (DDPG/SAC 무용지물) | 4개 (모두 활용) |
| **변환 로직** | 기본 (실패) | 우선순위 기반 (성공) |
| **투표 전략** | Weighted | Safety-First |
| **TOP 쿼리 처리** | 없음 | 특별 처리 |
| **Action Validator** | 없음 | 있음 |
| **Query Router** | 없음 | 있음 |
| **실패 학습** | 없음 | 있음 |

## 📚 참고 문서

- [Ensemble v1 보고서](../Ensemble_v1/Ensemble_v1_Final_Report.md)
- [DQN v4 평가 보고서](../DQN_v4/DQN_v4_Evaluation_Report.md)
- [PPO v3 평가 보고서](../PPO_v3/PPO_v3_Evaluation_Report.md)
- [DDPG v1 평가 보고서](../DDPG_v1/DDPG_v1_Evaluation_Report.md)
- [SAC v1 평가 보고서](../SAC_v1/SAC_v1_Evaluation_Report.md)

## 🏆 개발 목표 달성도

- ✅ **DDPG/SAC 활성화**: Continuous-to-discrete 변환 로직 개선
- ✅ **안전성 우선**: Safety-first voting 구현
- ✅ **TOP 쿼리 최적화**: Query type router + action validator
- ✅ **코드 품질**: 모듈화, 테스트 코드, 상세 문서

---

*Last Updated: 2025-10-28*

