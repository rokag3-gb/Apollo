# SAC v1: Soft Actor-Critic

Maximum Entropy 강화학습을 사용하여 탐색과 활용의 균형을 자동으로 조정하는 모델입니다.

## 핵심 특징

### 1. Entropy-Regularized Objective
- 보상 최대화 + 엔트로피 최대화
- 다양한 액션 조합 탐색
- 지역 최적해 탈출

### 2. Automatic Temperature Tuning
- α (temperature) 파라미터 자동 조정
- 탐색-활용 균형 자동 학습
- 하이퍼파라미터 튜닝 불필요

### 3. Stochastic Policy
- 확률적 정책 (vs TD3/DDPG의 deterministic)
- 다양성 확보
- 강건성 향상

## 예상 성능

- **목표**: 1.9~2.1x
- **장점**: 새로운 액션 조합 발견 가능
- **적용**: 다양한 쿼리 타입에 균형 잡힌 성능

## 사용법

### 1. Simulation 학습

```bash
cd Apollo.ML/RLQO/SAC_v1
python train/sac_train_sim.py
```

### 2. Real DB Fine-tuning

```bash
python train/sac_train_realdb.py
```

### 3. 평가

```bash
python train/sac_evaluate.py
```

## 기술적 배경

SAC는 Maximum Entropy RL 프레임워크를 사용:

- **목표**: max E[Σ(r + α·H(π))]
- **H(π)**: 정책의 엔트로피 (다양성)
- **α**: 온도 파라미터 (자동 조정)

## DDPG/TD3와 비교

| 특징 | DDPG/TD3 | SAC |
|------|----------|-----|
| **정책** | Deterministic | Stochastic |
| **탐색** | Noise 추가 | Entropy 최대화 |
| **안정성** | 높음 | 매우 높음 |
| **다양성** | 제한적 | 매우 높음 |

## 참고 문헌

- Haarnoja et al. (2018). "Soft Actor-Critic Algorithms and Applications"
- Paper: https://arxiv.org/abs/1812.05905

