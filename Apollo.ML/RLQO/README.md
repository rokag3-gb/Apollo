# RLQO (Reinforcement Learning for Query Optimization)

SQL Server 쿼리 최적화를 위한 강화학습 기반 시스템입니다.

## 폴더 구조

```
RLQO/
├── constants.py              # 공통 상수 및 샘플 쿼리
├── DQN_v1/                   # DQN Phase 1 & 2
│   ├── env/                  # 환경 (phase1_query_plan_env, phase2_db_env)
│   ├── features/             # 특징 추출 (phase1_features, phase2_features)
│   ├── train/                # 훈련 스크립트
│   └── evaluate_agent.py     # 평가 스크립트
├── DQN_v2/                   # DQN v2 (확장된 Action Space)
│   ├── env/                  # 환경 (v2_sim_env, v2_db_env, v2_reward)
│   ├── train/                # 훈련/평가/시각화
│   ├── v2_collect_plans.py   # 실행 계획 수집
│   ├── v2_quick_test.py      # 빠른 테스트
│   └── DQN_v2_README.md      # v2 상세 문서
└── DQN_v3/                   # DQN v3 (액션 호환성 + Curriculum)
    ├── env/                  # 환경 (v3_sim_env, v3_db_env, v3_reward)
    ├── train/                # 훈련/평가
    ├── v3_collect_plans.py   # 실행 계획 수집
    └── v3_generate_compatibility.py  # 호환성 매핑 생성
```

## 버전별 특징

### DQN v1 (Phase 1 & 2)
- **Phase 1**: XGBoost 시뮬레이션 환경
- **Phase 2**: 실제 DB 환경
- 기본 액션 스페이스 (MAXDOP, JOIN 힌트)
- 간단한 보상 함수 (실행 시간 + I/O)

### DQN v2
- 확장된 액션 스페이스 (15개 액션)
- 안전성 점수 기반 보상 함수
- Curriculum Learning 지원
- 하이브리드 학습 파이프라인 (시뮬레이션 → 실제 DB)

### DQN v3
- 쿼리별 액션 호환성 체크 및 마스킹
- 개선된 보상 함수 (성능 + 안정성 + 일관성)
- TABLE_HINT 구현 (USE_NOLOCK)
- 베이스라인 시간 기반 Curriculum Learning

## 실행 방법

### 프로젝트 루트에서 실행

모든 스크립트는 프로젝트 루트(`C:\source\Apollo`)에서 실행해야 합니다.

```bash
# DQN v1 훈련
python Apollo.ML/RLQO/DQN_v1/train/phase1_train_dqn.py

# DQN v1 평가
python Apollo.ML/RLQO/DQN_v1/evaluate_agent.py

# DQN v2 훈련 (시뮬레이션)
python Apollo.ML/RLQO/DQN_v2/train/v2_train_dqn.py --phase Simul

# DQN v2 훈련 (실제 DB)
python Apollo.ML/RLQO/DQN_v2/train/v2_train_dqn.py --phase RealDB

# DQN v2 평가
python Apollo.ML/RLQO/DQN_v2/train/v2_evaluate.py

# DQN v3 훈련 (시뮬레이션)
python Apollo.ML/RLQO/DQN_v3/train/v3_train_dqn.py --phase Simul

# DQN v3 훈련 (실제 DB)
python Apollo.ML/RLQO/DQN_v3/train/v3_train_dqn.py --phase RealDB

# DQN v3 평가
python Apollo.ML/RLQO/DQN_v3/train/v3_evaluate.py
```

## 공유 리소스

### constants.py
모든 버전에서 공유하는 상수 및 샘플 쿼리가 정의되어 있습니다.

### phase2_features.py (DQN_v1)
v2와 v3도 이 파일의 특징 추출 함수를 공유합니다.

## 다음 단계

DQN 알고리즘 구현이 완료되었으며, 이제 다음 알고리즘 구현을 준비할 수 있습니다:
- **PPO (Proximal Policy Optimization)**
- **DDPG (Deep Deterministic Policy Gradient)**

