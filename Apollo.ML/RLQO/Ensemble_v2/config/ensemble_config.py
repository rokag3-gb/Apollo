# -*- coding: utf-8 -*-
"""
Ensemble v2: Configuration

4개 모델의 경로와 앙상블 설정을 정의합니다.
v1과 달리 DDPG v1, SAC v1도 활용합니다 (continuous-to-discrete 변환으로).
"""

import os

# 프로젝트 루트 경로
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, 'Apollo.ML', 'artifacts', 'RLQO', 'models')

# 모델 경로 (Real DB Fine-tuned 모델)
MODEL_PATHS = {
    'dqn_v4': os.path.join(ARTIFACTS_DIR, 'dqn_v4_final.zip'),
    'ppo_v3': os.path.join(ARTIFACTS_DIR, 'ppo_v3_realdb_50k.zip'),
    'ddpg_v1': os.path.join(ARTIFACTS_DIR, 'ddpg_v1_realdb_50k.zip'),
    'sac_v1': os.path.join(ARTIFACTS_DIR, 'sac_v1_realdb_50k.zip'),
}

# 모델별 환경 타입 (각 모델이 사용하는 환경)
MODEL_ENV_TYPES = {
    'dqn_v4': 'dqn_v4',  # QueryPlanDBEnvV4 (79-dim observation, 30 queries)
    'ppo_v3': 'ppo',     # QueryPlanDBEnvPPOv3 (18-dim observation)
    'ddpg_v1': 'ddpg',   # QueryPlanRealDBEnvDDPGv1 (18-dim observation)
    'sac_v1': 'sac',     # make_sac_db_env (18-dim observation)
}

# 모델 타입 정의
MODEL_TYPES = {
    'dqn_v4': 'discrete',    # DQN v4 - Discrete action space (30 queries)
    'ppo_v3': 'discrete',    # PPO - Discrete action space (with masking)
    'ddpg_v1': 'continuous', # DDPG - Continuous action space (7-dim)
    'sac_v1': 'continuous',  # SAC - Continuous action space (7-dim)
}

# Voting 전략
VOTING_STRATEGIES = {
    'majority': 'majority_voting',      # 다수결 투표
    'weighted': 'weighted_voting',      # 가중치 기반 투표
    'equal': 'equal_weighted',          # 균등 가중치
    'performance': 'performance_based', # 성능 기반 가중치
    'query_type': 'query_type_based',   # 쿼리 타입별 가중치
    'safety_first': 'safety_first',     # 안전성 우선 (v2 신규)
}

# 모델별 기본 성능 가중치 (개선 쿼리 수 기반)
# DQN v4: 15개 쿼리 개선 (최다)
# PPO v3: 9개 쿼리 개선 (2위)
# DDPG v1: 4개 쿼리 개선 (극적 개선)
# SAC v1: 7개 쿼리 개선
PERFORMANCE_WEIGHTS = {
    'dqn_v4': 2.0,   # 15개 쿼리 개선 (최다)
    'ppo_v3': 1.8,   # 9개 쿼리 개선 (2위)
    'ddpg_v1': 1.5,  # 4개 쿼리 개선 (극적)
    'sac_v1': 1.6,   # 7개 쿼리 개선
}

# 쿼리 타입별 모델 가중치 (분석 보고서 기반 전문성 반영)
# v2 개선: 각 모델의 실제 강점 쿼리 타입에 가중치 집중
QUERY_TYPE_WEIGHTS = {
    'CTE': {
        'dqn_v4': 0.20,
        'ppo_v3': 0.50,  # PPO가 CTE에 강함 (1.7x 개선)
        'ddpg_v1': 0.15,
        'sac_v1': 0.15,
    },
    'JOIN_HEAVY': {
        'dqn_v4': 0.15,
        'ppo_v3': 0.25,  # 복잡한 쿼리 강함
        'ddpg_v1': 0.30,  # DDPG가 복잡한 JOIN에 강함
        'sac_v1': 0.30,   # SAC도 JOIN에 강함
    },
    'AGGREGATE': {
        'dqn_v4': 0.25,
        'ppo_v3': 0.30,
        'ddpg_v1': 0.20,
        'sac_v1': 0.25,
    },
    'SIMPLE': {
        'dqn_v4': 0.10,
        'ppo_v3': 0.10,
        'ddpg_v1': 0.40,  # 대용량 쿼리 전문 (17x 개선)
        'sac_v1': 0.40,   # 대용량 쿼리 전문 (18x 개선)
    },
    'SUBQUERY': {
        'dqn_v4': 0.25,
        'ppo_v3': 0.35,
        'ddpg_v1': 0.20,
        'sac_v1': 0.20,
    },
    'TOP': {
        'dqn_v4': 0.25,
        'ppo_v3': 0.35,
        'ddpg_v1': 0.20,
        'sac_v1': 0.20,
    },
    'WINDOW': {
        'dqn_v4': 0.20,
        'ppo_v3': 0.30,
        'ddpg_v1': 0.25,
        'sac_v1': 0.25,
    },
    'DEFAULT': {
        'dqn_v4': 0.25,
        'ppo_v3': 0.30,
        'ddpg_v1': 0.22,
        'sac_v1': 0.23,
    }
}

# Confidence Threshold
# v2: Safety-first 전략에 따라 threshold 상향
CONFIDENCE_THRESHOLD = 0.15  # v1: 0.1 → v2: 0.15 (더 보수적)

# NO_ACTION 페널티 (v2 개선)
# NO_ACTION(18번)의 투표 가중치를 낮춰서 실제 개선 액션을 우선 선택
NO_ACTION_PENALTY = 0.5  # NO_ACTION의 가중치를 절반으로

# Safety-First 설정 (v2 개선: Conservative threshold 완화)
SAFETY_CONFIG = {
    'avg_confidence_threshold': 0.15,  # 0.4 → 0.15 (완화)
    'disagreement_threshold': 0.25,    # 0.5 → 0.25 (완화)
    'use_action_validator': True,      # Action validator 사용
    'use_query_router': True,          # Query type router 사용
}

# TOP 쿼리 특별 설정 (v2 신규)
TOP_QUERY_CONFIG = {
    'allowed_actions': [14, 15, 16, 17, 18],  # FAST_10/50/100/200, NO_ACTION
    'boost_no_action': True,                   # NO_ACTION 선호도 증가
    'penalize_loop_join': True,                # LOOP_JOIN 억제
}

# Action Validator 설정 (v2 신규)
ACTION_VALIDATOR_CONFIG = {
    'min_baseline_for_maxdop': 10,      # Baseline < 10ms → MAXDOP 제외
    'failure_rate_threshold': 0.5,       # 실패율 > 50% → 제외
    'enable_failure_tracking': True,     # 실패 패턴 추적
}

# 평가 설정
EVAL_CONFIG = {
    'n_queries': 30,
    'n_episodes': 10,
    'max_steps': 10,
    'verbose': True,
}

# 결과 저장 경로
RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
CHARTS_DIR = os.path.join(RESULTS_DIR, 'charts')

# 출력 파일
OUTPUT_FILES = {
    'results_json': os.path.join(RESULTS_DIR, 'ensemble_v2_results.json'),
    'comparison_csv': os.path.join(RESULTS_DIR, 'ensemble_v2_comparison.csv'),
    'detailed_json': os.path.join(RESULTS_DIR, 'ensemble_v2_detailed.json'),
}

