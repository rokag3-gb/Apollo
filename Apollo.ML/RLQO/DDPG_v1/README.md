# DDPG v1: Deep Deterministic Policy Gradient for Query Optimization

DQN v3와 PPO v3에 이어 **DDPG (Deep Deterministic Policy Gradient)** 알고리즘을 적용한 SQL Server 쿼리 최적화 시스템입니다.

## 주요 특징

### 1. Continuous Action Space (7차원)

기존 44개 discrete actions 대신 7개의 연속 변수로 표현:

```python
action_vector = [
    0.0~1.0,  # [0] MAXDOP: 1~10으로 변환
    0.0~1.0,  # [1] FAST: 0, 10, 20, ..., 100으로 변환
    0.0~1.0,  # [2] ISOLATION: 4가지 레벨
    0.0~1.0,  # [3] JOIN_HINT: 5가지 타입
    0.0~1.0,  # [4] OPTIMIZER_HINT: 11가지 힌트
    0.0~1.0,  # [5] COMPATIBILITY: 4가지 레벨
    0.0~1.0,  # [6] USE_RECOMPILE: binary
]
```

### 2. Actor-Critic 구조

- **Actor**: State → Continuous Action (deterministic policy)
- **Critic**: State + Action → Q-value
- **Target Networks**: Soft update (τ=0.001)로 학습 안정화

### 3. Off-Policy Learning

- **Experience Replay Buffer**: 100K transitions
- **샘플 효율성**: 과거 경험 재사용
- **OU Noise**: Ornstein-Uhlenbeck process로 탐험

### 4. 재사용 컴포넌트

- **State**: PPO v3의 18차원 actionable state
- **Reward**: PPO v3의 log scale normalized reward
- **Simulator**: DQN v3의 XGBoost 예측 모델

## 디렉토리 구조

```
DDPG_v1/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── action_decoder.py              # Continuous → Discrete 변환
├── env/
│   ├── __init__.py
│   ├── ddpg_sim_env.py                # Simulation 환경
│   └── ddpg_db_env.py                 # RealDB 환경
├── train/
│   ├── __init__.py
│   ├── ddpg_train_sim.py              # Simulation 학습 (100K)
│   ├── ddpg_train_realdb.py           # RealDB Fine-tuning (50K)
│   └── ddpg_evaluate.py               # 평가 스크립트
└── README.md
```

## 사용 방법

### 1. Simulation 학습 (100K steps)

```bash
cd C:\source\Apollo
python Apollo.ML/RLQO/DDPG_v1/train/ddpg_train_sim.py
```

- 예상 소요 시간: **30-45분**
- 출력 모델: `Apollo.ML/artifacts/RLQO/models/ddpg_v1_sim_100k.zip`
- XGBoost 예측 모델로 빠른 학습

### 2. RealDB Fine-tuning (50K steps)

```bash
python Apollo.ML/RLQO/DDPG_v1/train/ddpg_train_realdb.py
```

- 예상 소요 시간: **40-60분**
- 출력 모델: `Apollo.ML/artifacts/RLQO/models/ddpg_v1_realdb_50k.zip`
- 실제 SQL Server에서 쿼리 실행 및 fine-tuning

### 3. 모델 평가

```bash
python Apollo.ML/RLQO/DDPG_v1/train/ddpg_evaluate.py \
    --model Apollo.ML/artifacts/RLQO/models/ddpg_v1_realdb_50k.zip \
    --episodes 3 \
    --output ddpg_v1_results.json
```

출력:
- 평균/중앙값/최대/최소 Speedup
- 쿼리별 성능 분석
- 성능 분포 (탁월/양호/중립/저하)
- JSON 결과 파일

### 4. TensorBoard 모니터링

```bash
# Simulation
tensorboard --logdir Apollo.ML/artifacts/RLQO/tb/ddpg_v1_sim/

# RealDB
tensorboard --logdir Apollo.ML/artifacts/RLQO/tb/ddpg_v1_realdb/
```

## 하이퍼파라미터

### Simulation (100K steps)

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| Learning Rate | 1e-4 | Actor learning rate |
| Buffer Size | 100,000 | Replay buffer 크기 |
| Batch Size | 128 | Mini-batch 크기 |
| Gamma | 0.99 | Discount factor |
| Tau | 0.001 | Soft update coefficient |
| OU Sigma | 0.2 | OU noise standard deviation |
| OU Theta | 0.15 | OU noise mean reversion |

### RealDB Fine-tuning (50K steps)

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| Learning Rate | 5e-5 | **매우 낮은 learning rate** |
| Buffer Size | 50,000 | 더 작은 buffer |
| Batch Size | 64 | 더 작은 batch |
| Gamma | 0.99 | 동일 |
| Tau | 0.001 | 동일 |
| OU Sigma | 0.1 | **낮은 exploration noise** |
| OU Theta | 0.15 | 동일 |

## DQN v3, PPO v3와의 비교

| 특징 | DQN v3 | PPO v3 | **DDPG v1** |
|------|--------|--------|-------------|
| **알고리즘 타입** | Value-based | Policy-based | **Actor-Critic** |
| **Action Space** | Discrete (44개) | Discrete (44개) | **Continuous (7차원)** |
| **Policy 타입** | ε-greedy | Stochastic | **Deterministic** |
| **학습 방식** | Off-policy | On-policy | **Off-policy** |
| **Experience Replay** | ✅ | ❌ | **✅** |
| **Target Network** | ✅ Q-target | ❌ | **✅ Actor & Critic** |
| **탐험 전략** | ε-greedy | Entropy bonus | **OU Noise** |
| **State 차원** | 79 or 18 | 18 | **18** |
| **Reward** | v3 normalized | Log scale | **Log scale** |
| **샘플 효율성** | 중간 | 낮음 | **높음** |

## DDPG의 장점

### 1. 세밀한 제어
- Discrete: MAXDOP를 1, 2, 3, ..., 10 중 선택
- **Continuous**: MAXDOP를 1.0 ~ 10.0 사이 **임의의 실수값** 선택 가능
  - 예: 3.2, 5.7, 8.9 등
  - 디코더에서 실제 적용 시 정수로 변환

### 2. 샘플 효율성
- Off-policy + Replay buffer로 경험 재사용
- DQN처럼 과거 데이터 활용
- PPO보다 적은 샘플로 학습 가능

### 3. Deterministic Policy
- 평가 시 일관된 행동 (재현 가능)
- Noise 없이 순수 policy 사용
- 프로덕션 환경에 배포하기 용이

### 4. 확장성
- 액션 차원 추가가 용이
- 7차원 → 10차원으로 확장 간단
- Discrete action space는 조합 폭발 문제

## DDPG의 단점 및 대응

### 1. 학습 불안정성
- **문제**: Actor-Critic은 PPO보다 수렴이 어려움
- **대응**: Target network soft update (τ=0.001)
- **대응**: Lower learning rate (1e-4)

### 2. 탐색 부족
- **문제**: Deterministic policy라 exploration 어려움
- **대응**: Ornstein-Uhlenbeck noise 추가
- **대응**: Noise decay schedule 적용 가능

### 3. Q-value 과대평가
- **문제**: Critic이 Q-value를 과대평가할 수 있음
- **향후 개선**: TD3 (Twin Delayed DDPG) 적용 고려
  - Twin Critics (Q1, Q2)
  - Delayed policy updates
  - Target policy smoothing

## Action Decoder

7차원 continuous action을 SQL 힌트로 변환하는 방법:

```python
from RLQO.DDPG_v1.config.action_decoder import ContinuousActionDecoder

decoder = ContinuousActionDecoder()

# Random action
action = np.array([0.4, 0.5, 0.8, 0.2, 0.1, 0.75, 0.9])

# Decode
hints = decoder.decode(action)
# {
#   'maxdop': 4,                    # int(0.4 * 9) + 1
#   'fast_n': 50,                   # values[int(0.5 * 11)]
#   'isolation': 'SNAPSHOT',        # values[int(0.8 * 4)]
#   'join_hint': 'hash',            # values[int(0.2 * 5)]
#   'optimizer_hint': 'FORCESEEK',  # values[int(0.1 * 11)]
#   'compatibility': 'COMPAT_160',  # values[int(0.75 * 4)]
#   'use_recompile': True           # 0.9 >= 0.5
# }

# Get description
desc = decoder.get_action_description(action)
# "MAXDOP=4, FAST=50, ISOLATION=SNAPSHOT, JOIN=HASH, OPT=FORCESEEK, COMPAT_160, RECOMPILE"
```

## 성공 지표

### 목표 성능

- **평균 Speedup**: 1.2x ~ 1.5x (DQN/PPO와 동등 이상)
- **최대 Speedup**: 2.0x ~ 3.0x
- **안정성**: 베이스라인 대비 성능 저하 < 10%
- **탐색 효율**: Continuous space의 장점 활용

### 비교 기준

DQN v3, PPO v3 결과와 비교하여:
- 평균 성능이 동등 이상인가?
- 특정 쿼리에서 더 나은 성능을 보이는가?
- 학습 시간/샘플 효율성은 어떠한가?

## 문제 해결

### 1. 모델 로드 실패

```bash
# Simulation부터 학습
python Apollo.ML/RLQO/DDPG_v1/train/ddpg_train_sim.py
```

### 2. DB 연결 실패

- `Apollo.ML/config.yaml`에서 DB 연결 정보 확인
- SQL Server 실행 상태 확인
- `Apollo.Core/Credential/Secret.cs`에서 credentials 확인

### 3. 메모리 부족

- Batch size 감소: `BATCH_SIZE = 64`
- Buffer size 감소: `BUFFER_SIZE = 50_000`

### 4. 학습이 느림

- Simulation 환경 사용 (XGBoost 예측)
- RealDB는 fine-tuning 단계에서만 사용
- Timesteps 감소 고려

### 5. 성능이 나쁨

- 더 많은 timesteps 학습
- Learning rate 조정
- Noise 파라미터 조정 (σ, θ)

## 향후 개선 방향

### 1. TD3 (Twin Delayed DDPG)

DDPG의 개선 버전:
- Twin Critics (Q1, Q2) → 과대평가 방지
- Delayed policy updates → 안정성 ↑
- Target policy smoothing → 노이즈 정규화

### 2. SAC (Soft Actor-Critic)

- Entropy maximization
- Stochastic policy (DDPG는 deterministic)
- 더 강건한 학습

### 3. Multi-task Learning

- 여러 쿼리 타입 동시 학습
- Transfer learning
- Meta-learning

### 4. Curriculum Learning

- 쿼리 난이도별 점진적 학습
- Baseline 시간 기반 정렬
- 동적 난이도 조정

## 참고 자료

### 논문

- **DDPG**: Lillicrap et al., "Continuous control with deep reinforcement learning" (2015)
  - arXiv: https://arxiv.org/abs/1509.02971
- **TD3**: Fujimoto et al., "Addressing Function Approximation Error in Actor-Critic Methods" (2018)
  - arXiv: https://arxiv.org/abs/1802.09477

### 구현

- **Stable-Baselines3 DDPG**: https://stable-baselines3.readthedocs.io/en/master/modules/ddpg.html
- **DQN v3**: `Apollo.ML/RLQO/DQN_v3/`
- **PPO v3**: `Apollo.ML/RLQO/PPO_v3/`

### 기타

- **Ornstein-Uhlenbeck Process**: https://en.wikipedia.org/wiki/Ornstein%E2%80%93Uhlenbeck_process
- **Actor-Critic Methods**: http://incompleteideas.net/book/RLbook2020.pdf (Chapter 13)

## 라이선스

MIT License

## 작성자

Apollo Team - 2024

