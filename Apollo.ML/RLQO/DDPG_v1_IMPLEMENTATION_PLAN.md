# DDPG v1 구현 계획

## 개요

DQN v3와 PPO v3에 이어 DDPG (Deep Deterministic Policy Gradient) 알고리즘을 적용한 쿼리 최적화 시스템을 구현합니다. Continuous action space를 활용하여 더 세밀한 최적화 제어를 시도합니다.

## 핵심 설계

### 1. Continuous Action Space (7차원)

기존 44개 discrete actions 대신 7개의 연속 변수로 표현:

```python
action_vector = [
    0.0~1.0,  # [0] MAXDOP: 1~10으로 변환
    0.0~1.0,  # [1] FAST: 0, 10, 20, ..., 100으로 변환
    0.0~1.0,  # [2] ISOLATION: 0(default), 1(READ_COMMITTED), 2(READ_UNCOMMITTED), 3(SNAPSHOT)
    0.0~1.0,  # [3] JOIN_HINT: none, hash, merge, loop, force_order
    0.0~1.0,  # [4] OPTIMIZER_HINT: 10가지 중 선택 (FORCESEEK, FORCESCAN 등)
    0.0~1.0,  # [5] COMPATIBILITY: COMPAT_LEVEL_130~160
    0.0~1.0,  # [6] USE_RECOMPILE: 0 or 1
]
```

### 2. 재사용 컴포넌트

- **State Encoder**: `PPO_v3/env/v3_actionable_state.py` (18차원)
- **Reward Function**: `PPO_v3/env/v3_normalized_reward.py` (log scale)
- **Query List**: `constants2.py` (30개 쿼리)
- **XGB Simulator**: `DQN_v3/env/v3_sim_env.py` (시뮬레이션 환경)

### 3. 주요 구현 파일

```
Apollo.ML/RLQO/DDPG_v1/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── action_decoder.py              # Continuous → Discrete 변환 로직
├── env/
│   ├── __init__.py
│   ├── ddpg_sim_env.py                # Simulation 환경 (Continuous action)
│   └── ddpg_db_env.py                 # RealDB 환경
├── train/
│   ├── __init__.py
│   ├── ddpg_train_sim.py              # Simulation 학습 (100K)
│   ├── ddpg_train_realdb.py           # RealDB Fine-tuning (50K)
│   └── ddpg_evaluate.py               # 평가 스크립트
└── README.md                          # 사용법 및 설명

Apollo.ML/artifacts/RLQO/configs/
└── v1_continuous_action_config.json   # 7차원 action space 정의
```

## 구현 단계

### Step 1: Action Decoder 구현

**파일**: `Apollo.ML/RLQO/DDPG_v1/config/action_decoder.py`

연속 action vector [0~1]^7을 실제 SQL 쿼리 힌트로 변환하는 디코더 구현:

```python
class ContinuousActionDecoder:
    def decode(self, action_vector: np.ndarray) -> dict:
        # action_vector: [0~1]^7
        # returns: {'maxdop': int, 'fast_n': int, 'isolation': str, ...}
```

핵심 로직:
- MAXDOP: `int(action[0] * 9) + 1` → 1~10
- FAST: `int(action[1] * 11) * 10` → 0, 10, 20, ..., 100
- ISOLATION: quantize to 4 levels
- JOIN/OPTIMIZER hints: discrete mapping

### Step 2: DDPG Simulation 환경

**파일**: `Apollo.ML/RLQO/DDPG_v1/env/ddpg_sim_env.py`

`QueryPlanSimEnvV3` (DQN v3)를 상속하되 action space를 continuous로 변경:

```python
class QueryPlanSimEnvDDPGv1(QueryPlanSimEnvV3):
    def __init__(self, query_list, max_steps=10, **kwargs):
        # Action space: Box(0, 1, shape=(7,))
        self.action_space = spaces.Box(low=0.0, high=1.0, shape=(7,), dtype=np.float32)
        # Observation space: 18차원 (PPO v3와 동일)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(18,), dtype=np.float32)
        # Action decoder
        self.action_decoder = ContinuousActionDecoder()
```

핵심 변경:
- `step()`: continuous action을 받아서 decode → discrete hints 적용
- PPO v3의 `ActionableStateEncoderV3` 재사용
- PPO v3의 `calculate_reward_v3_normalized` 재사용

### Step 3: DDPG RealDB 환경

**파일**: `Apollo.ML/RLQO/DDPG_v1/env/ddpg_db_env.py`

실제 DB 연결하여 쿼리 실행. Simulation 환경과 동일한 인터페이스:

```python
class QueryPlanRealDBEnvDDPGv1:
    # ddpg_sim_env.py와 동일한 구조
    # XGB 예측 대신 실제 SQL Server 실행
```

### Step 4: Simulation 학습 스크립트

**파일**: `Apollo.ML/RLQO/DDPG_v1/train/ddpg_train_sim.py`

Stable-Baselines3의 DDPG를 사용한 시뮬레이션 학습:

```python
from stable_baselines3 import DDPG
from stable_baselines3.common.noise import OrnsteinUhlenbeckActionNoise

# Hyperparameters
LEARNING_RATE = 1e-4
BUFFER_SIZE = 100_000
BATCH_SIZE = 128
GAMMA = 0.99
TAU = 0.001  # Soft update
TRAIN_FREQ = 1
GRADIENT_STEPS = 1

# OU Noise for exploration
action_noise = OrnsteinUhlenbeckActionNoise(
    mean=np.zeros(7), 
    sigma=0.2 * np.ones(7),
    theta=0.15
)

model = DDPG(
    "MlpPolicy",
    env,
    learning_rate=LEARNING_RATE,
    buffer_size=BUFFER_SIZE,
    batch_size=BATCH_SIZE,
    gamma=GAMMA,
    tau=TAU,
    action_noise=action_noise,
    tensorboard_log=TB_LOG_DIR,
    verbose=1
)

model.learn(total_timesteps=100_000)
```

주요 설정:
- Actor/Critic: MLP (256-128 hidden layers)
- Exploration: Ornstein-Uhlenbeck noise
- Experience Replay: 100K buffer
- Target networks: Soft update (τ=0.001)

### Step 5: RealDB Fine-tuning 스크립트

**파일**: `Apollo.ML/RLQO/DDPG_v1/train/ddpg_train_realdb.py`

Simulation에서 학습한 모델을 RealDB에서 fine-tuning:

```python
# Load pre-trained model
model = DDPG.load("artifacts/RLQO/models/ddpg_v1_sim_100k.zip", env=env)

# Fine-tuning hyperparameters (더 보수적)
model.learning_rate = 5e-5  # 매우 낮은 learning rate
model.action_noise = OrnsteinUhlenbeckActionNoise(
    mean=np.zeros(7), 
    sigma=0.1 * np.ones(7),  # 낮은 noise
    theta=0.15
)

model.learn(total_timesteps=50_000)
```

### Step 6: 평가 스크립트

**파일**: `Apollo.ML/RLQO/DDPG_v1/train/ddpg_evaluate.py`

30개 쿼리에 대한 성능 평가 및 분석:

```python
def evaluate_ddpg(model_path, episodes=3):
    model = DDPG.load(model_path)
    
    results = []
    for episode in range(episodes):
        for query_idx in range(30):
            obs = env.reset(query_idx=query_idx)
            # Noise 없이 deterministic action 사용
            action, _ = model.predict(obs, deterministic=True)
            # ... 성능 측정
    
    # 통계 분석
    - 평균 speedup
    - Query별 성능 비교
    - DQN v3, PPO v3와 비교
```

### Step 7: Action Config 파일

**파일**: `Apollo.ML/artifacts/RLQO/configs/v1_continuous_action_config.json`

7차원 action space의 의미와 변환 규칙을 JSON으로 정의:

```json
{
  "action_dim": 7,
  "action_ranges": {
    "maxdop": {"index": 0, "min": 1, "max": 10, "type": "int"},
    "fast_n": {"index": 1, "values": [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]},
    "isolation": {"index": 2, "values": ["default", "READ_COMMITTED", "READ_UNCOMMITTED", "SNAPSHOT"]},
    "join_hint": {"index": 3, "values": ["none", "hash", "merge", "loop", "force_order"]},
    "optimizer_hint": {"index": 4, "values": ["NONE", "FORCESEEK", "FORCESCAN", "DISABLE_OPTIMIZER_ROWGOAL", "ENABLE_QUERY_OPTIMIZER_HOTFIXES", "KEEPFIXED_PLAN", "FORCE_LEGACY_CARDINALITY_ESTIMATION", "DISALLOW_BATCH_MODE", "ALLOW_BATCH_MODE", "ASSUME_JOIN_PREDICATE_DEPENDS_ON_FILTERS", "ASSUME_MIN_SELECTIVITY_FOR_FILTER_ESTIMATES"]},
    "compatibility": {"index": 5, "values": ["COMPAT_130", "COMPAT_140", "COMPAT_150", "COMPAT_160"]},
    "use_recompile": {"index": 6, "min": 0, "max": 1, "type": "binary"}
  }
}
```

### Step 8: README 작성

**파일**: `Apollo.ML/RLQO/DDPG_v1/README.md`

사용법, 하이퍼파라미터, DQN/PPO와의 비교, 실행 예시를 포함한 문서화

## 하이퍼파라미터 설정

### Simulation (100K steps)
- Learning Rate: 1e-4 (Actor), 1e-3 (Critic)
- Buffer Size: 100,000
- Batch Size: 128
- Gamma: 0.99
- Tau: 0.001 (Soft update)
- OU Noise: σ=0.2, θ=0.15

### RealDB Fine-tuning (50K steps)
- Learning Rate: 5e-5 (낮게 설정)
- Buffer Size: 50,000
- Batch Size: 64
- Gamma: 0.99
- Tau: 0.001
- OU Noise: σ=0.1 (낮은 exploration)

## 예상 실행 시간

- Simulation 학습: 30-45분 (100K steps)
- RealDB Fine-tuning: 40-60분 (50K steps, 실제 쿼리 실행 포함)
- 평가: 10-15분 (30 queries × 3 episodes)

## 성공 지표

- **평균 Speedup**: 1.2x ~ 1.5x (DQN/PPO와 동등 이상)
- **최대 Speedup**: 2.0x ~ 3.0x
- **안정성**: 베이스라인 대비 성능 저하 < 10%
- **탐색 효율**: Continuous space의 장점 활용 여부

## DQN v3, PPO v3와의 비교

| 특징 | DQN v3 | PPO v3 | **DDPG v1** |
|------|--------|--------|-------------|
| **알고리즘 타입** | Value-based | Policy-based | **Actor-Critic** |
| **Action Space** | Discrete (44개) | Discrete (44개) | **Continuous (7차원)** |
| **Policy 타입** | ε-greedy | Stochastic (확률적) | **Deterministic (결정적)** |
| **학습 방식** | Off-policy | On-policy | **Off-policy** |
| **Experience Replay** | ✅ 사용 | ❌ 미사용 | **✅ 사용** |
| **Target Network** | ✅ Q-target | ❌ 없음 | **✅ Actor & Critic** |
| **탐험 전략** | ε-greedy | Entropy bonus | **OU Noise** |
| **State 차원** | 79 or 18 | 18 | **18** |
| **Reward** | v3 normalized | Log scale | **Log scale** |

## DDPG의 장점

1. **세밀한 제어**: Continuous action space로 더 다양한 힌트 조합 탐색
2. **샘플 효율성**: Off-policy + Replay buffer로 경험 재사용
3. **Deterministic Policy**: 평가 시 일관된 행동 (재현 가능)
4. **확장성**: 액션 차원 추가가 용이

## DDPG의 단점 및 대응 방안

1. **학습 불안정성**
   - 대응: Target network soft update (τ=0.001)
   - 대응: Gradient clipping

2. **탐색 부족**
   - 대응: Ornstein-Uhlenbeck noise 추가
   - 대응: Noise decay schedule

3. **Q-value 과대평가**
   - 향후 개선: TD3 (Twin Delayed DDPG) 적용 고려

## 참고 자료

- **DDPG 논문**: Lillicrap et al., "Continuous control with deep reinforcement learning" (2015)
  - arXiv: https://arxiv.org/abs/1509.02971
- **Stable-Baselines3 DDPG**: https://stable-baselines3.readthedocs.io/en/master/modules/ddpg.html
- **기존 구현**:
  - `Apollo.ML/RLQO/DQN_v3/`
  - `Apollo.ML/RLQO/PPO_v3/`

## 체크리스트

- [x] ContinuousActionDecoder 클래스 구현 (7차원 → discrete hints) ✅
- [x] v1_continuous_action_config.json 파일 생성 ✅
- [x] QueryPlanSimEnvDDPGv1 환경 구현 (continuous action space) ✅
- [x] QueryPlanRealDBEnvDDPGv1 환경 구현 ✅
- [x] Simulation 학습 스크립트 작성 (DDPG, 100K steps) ✅
- [x] RealDB Fine-tuning 스크립트 작성 (50K steps) ✅
- [x] 평가 스크립트 작성 및 성능 분석 ✅
- [x] DDPG_v1 README 작성 (사용법, 하이퍼파라미터, 비교) ✅

## 구현 완료 (2025-01-25)

모든 구현이 완료되었습니다!

### 생성된 파일
- `Apollo.ML/artifacts/RLQO/configs/v1_continuous_action_config.json`
- `Apollo.ML/RLQO/DDPG_v1/__init__.py`
- `Apollo.ML/RLQO/DDPG_v1/README.md`
- `Apollo.ML/RLQO/DDPG_v1/config/__init__.py`
- `Apollo.ML/RLQO/DDPG_v1/config/action_decoder.py`
- `Apollo.ML/RLQO/DDPG_v1/env/__init__.py`
- `Apollo.ML/RLQO/DDPG_v1/env/ddpg_sim_env.py`
- `Apollo.ML/RLQO/DDPG_v1/env/ddpg_db_env.py`
- `Apollo.ML/RLQO/DDPG_v1/train/__init__.py`
- `Apollo.ML/RLQO/DDPG_v1/train/ddpg_train_sim.py`
- `Apollo.ML/RLQO/DDPG_v1/train/ddpg_train_realdb.py`
- `Apollo.ML/RLQO/DDPG_v1/train/ddpg_evaluate.py`

### 테스트 결과
✅ Action Decoder: 성공
- 7차원 continuous action → SQL hints 변환 확인
- 예시: `[0.4, 0.5, 0.8, 0.2, 0.1, 0.75, 0.9]` → `MAXDOP=4, FAST=50, ISOLATION=SNAPSHOT, JOIN=HASH, OPT=FORCESEEK, COMPAT_160, RECOMPILE`

## 실행 명령어 (구현 완료 후)

### 1. Simulation 학습
```bash
cd C:\source\Apollo
python Apollo.ML/RLQO/DDPG_v1/train/ddpg_train_sim.py
```

### 2. RealDB Fine-tuning
```bash
python Apollo.ML/RLQO/DDPG_v1/train/ddpg_train_realdb.py
```

### 3. 모델 평가
```bash
python Apollo.ML/RLQO/DDPG_v1/train/ddpg_evaluate.py --model artifacts/RLQO/models/ddpg_v1_realdb_50k.zip --episodes 3
```

### 4. TensorBoard 모니터링
```bash
tensorboard --logdir Apollo.ML/artifacts/RLQO/tb/ddpg_v1_sim/
tensorboard --logdir Apollo.ML/artifacts/RLQO/tb/ddpg_v1_realdb/
```


