# TD3 v1: Twin Delayed Deep Deterministic Policy Gradient

DDPG v1의 개선 버전으로, Q-value overestimation 문제를 해결하고 학습 안정성을 향상시킨 모델입니다.

## 핵심 개선사항

### 1. Twin Critic Networks
- 두 개의 Q-network (Q1, Q2) 사용
- 최소값을 선택하여 overestimation 방지
- DDPG의 주요 약점 해결

### 2. Delayed Policy Updates  
- Critic을 더 자주 업데이트 (policy_delay=2)
- Actor는 덜 자주 업데이트
- 학습 안정성 향상

### 3. Target Policy Smoothing
- Target action에 노이즈 추가
- 과적합 방지
- 일반화 성능 향상

## 예상 성능

- **목표**: 2.0~2.2x (DDPG v1 1.88x → 10~20% 추가 개선)
- **안정성**: DDPG v1보다 낮은 분산
- **적용 범위**: 복잡한 쿼리에 더 안정적 성능

## 사용법

### 1. Simulation 학습 (100k steps)

```bash
cd Apollo.ML/RLQO/TD3_v1
python train/td3_train_sim.py
```

예상 소요 시간: 30-60분

### 2. Real DB Fine-tuning (50k steps)

```bash
python train/td3_train_realdb.py
```

예상 소요 시간: 2-4시간

### 3. 평가 (30 queries × 30 episodes)

```bash
python train/td3_evaluate.py
```

예상 소요 시간: 2-3시간

## 하이퍼파라미터

- **Learning Rate**: 3e-4
- **Policy Delay**: 2 (TD3 특징)
- **Target Noise**: 0.2 (TD3 특징)
- **Batch Size**: 256
- **Buffer Size**: 1,000,000

## 파일 구조

```
TD3_v1/
├── config/
│   └── td3_config.py          # 하이퍼파라미터
├── env/
│   ├── td3_sim_env.py         # Simulation 환경
│   └── td3_db_env.py          # Real DB 환경
├── train/
│   ├── td3_train_sim.py       # Simulation 학습
│   ├── td3_train_realdb.py    # Real DB fine-tuning
│   └── td3_evaluate.py        # 평가
└── README.md
```

## 기술적 배경

TD3는 DDPG의 다음 문제들을 해결합니다:

1. **Overestimation Bias**: Twin Critics로 해결
2. **Training Instability**: Delayed Updates로 해결  
3. **Overfitting**: Target Policy Smoothing으로 해결

## 참고 문헌

- Fujimoto et al. (2018). "Addressing Function Approximation Error in Actor-Critic Methods"
- Paper: https://arxiv.org/abs/1802.09477

## 다음 단계

TD3 v1 학습 후:
1. SAC v1 학습 (entropy-regularized)
2. 5개 모델 (DQN, PPO, DDPG, TD3, SAC) 비교
3. Ensemble, Multi-Agent, Meta-Learning 구현

