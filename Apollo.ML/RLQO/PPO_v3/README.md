# PPO v3: Query Plan Optimization

PPO v2를 기반으로 쿼리 개수, Action Space, 학습 안정성을 대폭 개선한 버전입니다.

## 주요 개선사항

### 1. 쿼리 확장 (9개 → 30개)
- 기존 9개 쿼리 유지
- 신규 20개 쿼리 추가
- 다양한 쿼리 타입: CTE, JOIN_HEAVY, TOP, SIMPLE, AGGREGATE, WINDOW, SUBQUERY

### 2. Action Space 확장 (19개 → 44개)
- **FAST n** (10개): 10, 20, 30, 40, 50, 60, 70, 80, 90, 100
- **MAXDOP n** (10개): 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
- **ISOLATION LEVEL** (3개): READ_COMMITTED, READ_UNCOMMITTED, SNAPSHOT
- **고급 DBA 액션** (10개):
  - FORCESEEK, FORCESCAN
  - DISABLE_OPTIMIZER_ROWGOAL
  - ENABLE_QUERY_OPTIMIZER_HOTFIXES
  - KEEPFIXED_PLAN, FORCE_LEGACY_CARDINALITY_ESTIMATION
  - DISALLOW_BATCH_MODE, ALLOW_BATCH_MODE
  - ASSUME_JOIN_PREDICATE_DEPENDS_ON_FILTERS
  - ASSUME_MIN_SELECTIVITY_FOR_FILTER_ESTIMATES
- **기존 액션 유지** (11개): JOIN 힌트, 최적화 힌트, 호환성, RECOMPILE, NO_ACTION

### 3. 학습 안정성 개선
- **Gradient clipping**: max_grad_norm=0.5
- **Checkpoint frequency**: 5K → 3K steps
- **Early stopping**: 10 episodes patience
- **Action diversity monitoring**

### 4. 유지되는 핵심 요소
- 18차원 actionable state
- Log scale normalized reward [-1, +1]
- MaskablePPO 알고리즘
- Query 타입별 action masking
- Simulation (100K) → RealDB Fine-tuning (50K)

## 디렉토리 구조

```
PPO_v3/
├── config/
│   └── query_action_mapping_v3.py    # 30개 쿼리 타입 분류 및 액션 매핑
├── env/
│   ├── v3_actionable_state.py        # 18차원 state encoder (ISOLATION/FAST 추가)
│   ├── v3_normalized_reward.py       # Log scale reward 함수
│   ├── v3_sim_env.py                 # Simulation 환경
│   └── v3_db_env.py                  # RealDB 환경
└── train/
    ├── callbacks.py                  # Early stopping, Action diversity
    ├── v3_train_sim.py               # Simulation 학습 (100K steps)
    ├── v3_train_realdb.py            # RealDB Fine-tuning (50K steps)
    └── v3_evaluate.py                # 평가 및 분석
```

## 사용 방법

### 1. Simulation 학습 (100K steps)

```bash
python Apollo.ML/RLQO/PPO_v3/train/v3_train_sim.py
```

- 예상 소요 시간: 30-45분
- 출력 모델: `Apollo.ML/artifacts/RLQO/models/ppo_v3_sim_100k.zip`

### 2. RealDB Fine-tuning (50K steps)

```bash
python Apollo.ML/RLQO/PPO_v3/train/v3_train_realdb.py
```

- 예상 소요 시간: 30-60분
- 출력 모델: `Apollo.ML/artifacts/RLQO/models/ppo_v3_realdb_50k.zip`

### 3. 모델 평가

```bash
python Apollo.ML/RLQO/PPO_v3/train/v3_evaluate.py \
    --model Apollo.ML/artifacts/RLQO/models/ppo_v3_realdb_50k.zip \
    --episodes 3 \
    --output eval_results.json
```

### 4. 환경 테스트

```bash
# Simulation 환경 테스트
python Apollo.ML/RLQO/PPO_v3/train/v3_train_sim.py --test

# RealDB 환경 테스트
python Apollo.ML/RLQO/PPO_v3/train/v3_train_realdb.py --test
```

### 5. TensorBoard 모니터링

```bash
tensorboard --logdir Apollo.ML/artifacts/RLQO/tb/ppo_v3_sim/
tensorboard --logdir Apollo.ML/artifacts/RLQO/tb/ppo_v3_realdb/
```

## 하이퍼파라미터

### Simulation (100K steps)
- Learning Rate: 3e-4
- N Steps: 2048
- Batch Size: 64
- Entropy Coef: 0.03 (exploration)
- Max Grad Norm: 0.5

### RealDB Fine-tuning (50K steps)
- Learning Rate: 5e-5 (매우 낮음)
- N Steps: 256
- Batch Size: 32
- Entropy Coef: 0.005 (안정성 우선)
- Max Grad Norm: 0.5

## Action Space 설정 파일

- `Apollo.ML/artifacts/RLQO/configs/v3_action_space_ppo.json` - 44개 액션 정의
- `Apollo.ML/artifacts/RLQO/configs/v3_query_action_compatibility_ppo.json` - 쿼리-액션 호환성

## Query 타입 분류

30개 쿼리는 7가지 타입으로 분류됩니다:
- **CTE** (3개): 1, 8, 11
- **JOIN_HEAVY** (11개): 0, 3, 4, 7, 15, 16, 25, 26, 27, 28, 29
- **TOP** (12개): 3, 4, 9, 10, 12, 13, 14, 15, 21, 23, 26, 27
- **SIMPLE** (5개): 2, 6, 13, 14, 23
- **AGGREGATE** (5개): 0, 7, 9, 10, 20, 22, 24, 25, 28, 29
- **WINDOW** (3개): 1, 8, 19
- **SUBQUERY** (4개): 5, 17, 18, 21

## 성능 목표

- **평균 Speedup**: 1.2x ~ 1.5x
- **최대 Speedup**: 2.0x ~ 3.0x (특정 쿼리)
- **안정성**: 베이스라인 대비 성능 저하 최소화

## 문제 해결

### 모델 로드 실패
```bash
# Pre-trained 모델이 없는 경우 Simulation부터 학습
python Apollo.ML/RLQO/PPO_v3/train/v3_train_sim.py
```

### DB 연결 실패
- `Apollo.ML/config.yaml`에서 DB 연결 정보 확인
- SQL Server 실행 상태 확인

### 메모리 부족
- Batch size 감소: `REAL_BATCH_SIZE = 16`
- N steps 감소: `REAL_N_STEPS = 128`

## PPO v2 대비 변경사항

| 항목 | PPO v2 | PPO v3 |
|------|--------|--------|
| 쿼리 개수 | 9개 | 30개 |
| 액션 개수 | 19개 | 44개 |
| State 차원 | 18차원 | 18차원 (유지) |
| Gradient clipping | 없음 | 0.5 |
| Checkpoint 빈도 | 5K steps | 3K steps |
| FAST 값 | 10, 50, 100, 200 | 10~100 (10개) |
| MAXDOP 값 | 1, 4, 8 | 1~10 (10개) |
| ISOLATION | NOLOCK만 | 3가지 |
| 고급 DBA 액션 | 없음 | 10개 추가 |

## 참고

- PPO v2: `Apollo.ML/RLQO/PPO_v2/`
- 30개 쿼리: `Apollo.ML/RLQO/constants2.py`
- DQN v3 (참고): `Apollo.ML/RLQO/DQN_v3/`

