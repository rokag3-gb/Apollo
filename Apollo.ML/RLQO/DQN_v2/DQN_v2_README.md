# DQN v2: Sim-to-Real 하이브리드 강화학습

## 📋 개요

DQN v2는 **시뮬레이션(XGB 예측 모델)**과 **실제 DB 환경**을 결합한 2단계 하이브리드 학습 전략을 사용합니다.

### 핵심 아이디어
- **Phase A**: XGB 예측 모델(R² = 0.9955)을 시뮬레이터로 사용하여 200K 타임스텝 고속 학습
- **Phase B**: 실제 DB 환경에서 10K 타임스텝 Fine-tuning으로 시뮬레이션 오차 보정

### v1/v1.5 대비 주요 개선점

| 항목 | v1/v1.5 | v2 |
|------|---------|-----|
| **학습량** | 5K 타임스텝 | 210K 타임스텝 (42배) |
| **학습 시간** | 3-5시간 | 3-5시간 (동일) |
| **보상 함수** | 단순 선형 | 비선형 + 다차원 메트릭 |
| **실패 페널티** | -100 (가혹함) | -10 ~ -18 (점진적) |
| **탐험 전략** | 90%까지 탐험 | 50%까지 탐험 |
| **환경** | 실제 DB만 | Sim(200K) + Real(10K) |

---

## 🗂️ 파일 구조

```
Apollo.ML/RLQO/
├── env/
│   ├── v2_reward.py          # 개선된 보상 함수
│   └── v2_sim_env.py          # XGB 시뮬레이션 환경
├── train/
│   ├── v2_train_dqn.py        # 하이브리드 학습 파이프라인
│   └── v2_evaluate.py         # 성능 평가 스크립트
└── DQN_v2_README.md           # 이 파일
```

---

## 🚀 사용법

### 1. 사전 요구사항

```bash
# 필요한 패키지가 설치되어 있는지 확인
pip install stable-baselines3 gymnasium joblib xgboost pandas numpy
```

**중요**: XGB 예측 모델이 필요합니다!
- 경로: `Apollo.ML/artifacts/model.joblib`
- R² = 0.9955 수준의 모델이 있어야 합니다

### 2. 전체 학습 파이프라인 실행

```bash
cd C:\source\Apollo
python Apollo.ML/RLQO/train/v2_train_dqn.py
```

**예상 소요 시간**: 3-5시간
- Phase A (Sim): 1-2시간
- Phase B (Real): 2-3시간

### 3. 단계별 실행 (선택사항)

#### SimulXGB만 실행 (시뮬레이션 학습)
```bash
python Apollo.ML/RLQO/train/v2_train_dqn.py --phase SimulXGB
```

#### RealDB만 실행 (Fine-tuning)
```bash
# SimulXGB가 완료된 후
python Apollo.ML/RLQO/train/v2_train_dqn.py --phase RealDB
```

### 4. 성능 평가

#### 전체 모델 비교 (v1, v1.5, v2)
```bash
python Apollo.ML/RLQO/train/v2_evaluate.py --mode full
```

#### v2 모델만 빠른 테스트
```bash
python Apollo.ML/RLQO/train/v2_evaluate.py --mode quick
```

---

## 📊 학습 모니터링

### TensorBoard로 학습 곡선 확인

```bash
tensorboard --logdir=Apollo.ML/artifacts/RLQO/tb/dqn_v2/
```

브라우저에서 `http://localhost:6006` 접속

### 체크포인트

학습 중 자동으로 체크포인트가 저장됩니다:

- **Phase A**: 20K 타임스텝마다 저장
  - 경로: `Apollo.ML/artifacts/RLQO/models/checkpoints/dqn_v2_sim/`
  
- **Phase B**: 2K 타임스텝마다 저장
  - 경로: `Apollo.ML/artifacts/RLQO/models/checkpoints/dqn_v2_real/`

### 최종 모델

- **시뮬레이션 모델**: `Apollo.ML/artifacts/RLQO/models/dqn_v2_sim.zip`
- **최종 모델**: `Apollo.ML/artifacts/RLQO/models/dqn_v2_final.zip`

---

## 🧪 단위 테스트

### v2_reward.py 테스트
```bash
python Apollo.ML/RLQO/env/v2_reward.py
```

**예상 출력**:
```
1. 큰 개선 (50% 시간 감소):
   보상: 1.5000 (예상: 양수 + 보너스)

2. 작은 개선 (10% 시간 감소):
   보상: 0.0950 (예상: 작은 양수)
...
✅ 테스트 완료!
```

### v2_sim_env.py 테스트
```bash
python Apollo.ML/RLQO/env/v2_sim_env.py
```

**예상 출력**:
```
[SimEnv] XGB 모델 로드 완료
[SimEnv] Episode: Query 1/3
  Baseline: 45.23 ms
  Action: USE_HASH_JOIN, Time: 38.15 ms, Reward: 0.245
...
✅ 시뮬레이션 환경 테스트 완료!
```

---

## 📈 평가 메트릭

평가 스크립트는 다음 메트릭을 제공합니다:

| 메트릭 | 설명 |
|--------|------|
| **Win Rate** | 베이스라인보다 빠른 쿼리 비율 (%) |
| **Average Speedup** | 평균 속도 향상률 (%) |
| **Best Speedup** | 최대 속도 향상률 (%) |
| **Failure Rate** | 쿼리 실행 실패율 (%) |
| **Consistency** | 동일 쿼리에 대한 액션 일관성 (%) |

### 예상 결과 (목표)

| 모델 | Win Rate | Avg Speedup | Failure Rate |
|------|----------|-------------|--------------|
| v1 | 30-40% | +5-10% | 20-30% |
| v1.5 | 40-50% | +10-15% | 15-25% |
| **v2** | **60-70%** | **+20-30%** | **5-10%** |

---

## 🔧 하이퍼파라미터 튜닝

주요 하이퍼파라미터는 `v2_train_dqn.py` 상단에 정의되어 있습니다:

```python
# Phase A: 시뮬레이션
SIM_TIMESTEPS = 200_000
SIM_LEARNING_RATE = 1e-4
SIM_BUFFER_SIZE = 50_000
SIM_EXPLORATION_FRACTION = 0.5

# Phase B: Fine-tuning
REAL_TIMESTEPS = 10_000
REAL_LEARNING_RATE = 5e-5
```

**튜닝 가이드**:
- `SIM_TIMESTEPS`를 늘리면 학습 품질 향상 (시간 증가)
- `REAL_TIMESTEPS`는 DB 부하를 고려하여 조절
- `LEARNING_RATE`는 학습 불안정 시 낮춤

---

## ⚠️ 문제 해결

### 1. XGB 모델을 찾을 수 없음
```
✗ Phase A 모델을 찾을 수 없습니다: Apollo.ML/artifacts/model.joblib
```

**해결**: XGB 모델을 먼저 학습하세요
```bash
python Apollo.ML/enhanced_train.py
```

### 2. DB 연결 실패 (Phase B)
```
✗ 환경 생성 실패: DB 연결을 확인하세요.
```

**해결**: `config.yaml`의 DB 설정을 확인하세요

### 3. 메모리 부족
```
OutOfMemoryError: ...
```

**해결**: 배치 크기나 버퍼 크기를 줄이세요
```python
SIM_BUFFER_SIZE = 25_000  # 50000 → 25000
SIM_BATCH_SIZE = 64       # 128 → 64
```

### 4. 학습이 너무 느림 (Phase A)

**원인**: CPU 성능 부족

**해결**: 타임스텝 수를 줄이거나 병렬 처리 활성화
```python
SIM_TIMESTEPS = 100_000  # 200000 → 100000
```

---

## 📝 다음 단계

1. ✅ **학습 완료 후**: `v2_evaluate.py`로 성능 평가
2. ✅ **결과 분석**: TensorBoard와 평가 리포트 확인
3. ✅ **하이퍼파라미터 튜닝**: 필요 시 설정 조정 후 재학습
4. ✅ **프로덕션 배포**: 최종 모델을 실제 시스템에 적용

---

## 📚 참고 자료

- **Stable Baselines3 문서**: https://stable-baselines3.readthedocs.io/
- **Sim-to-Real Transfer**: 로보틱스 및 자율주행 분야의 검증된 기법
- **DQN 논문**: "Human-level control through deep reinforcement learning" (Nature, 2015)

---

## 💡 팁

1. **Phase A를 먼저 완료**한 후 Phase B를 실행하세요 (중간 결과 확인 가능)
2. **TensorBoard를 실행**하여 학습 중 실시간으로 진행 상황 모니터링
3. **체크포인트를 활용**하여 최적 모델 선택 (후반부가 항상 좋은 것은 아님)
4. **평가는 여러 번** 실행하여 일관성 확인 (랜덤성 존재)

---

**제작**: Apollo ML Team  
**버전**: 2.0  
**최종 업데이트**: 2025-10-10

