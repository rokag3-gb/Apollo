# -*- coding: utf-8 -*-
"""
Ensemble v1: Configuration

4개 모델의 경로와 앙상블 설정을 정의합니다.
"""

import os

# 프로젝트 루트 경로
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, 'Apollo.ML', 'artifacts', 'RLQO', 'models')

# 모델 경로 (Real DB Fine-tuned 모델)
MODEL_PATHS = {
    'dqn_v3': os.path.join(ARTIFACTS_DIR, 'dqn_v3_final.zip'),
    'ppo_v3': os.path.join(ARTIFACTS_DIR, 'ppo_v3_realdb_50k.zip'),
    'ddpg_v1': os.path.join(ARTIFACTS_DIR, 'ddpg_v1_realdb_50k.zip'),
    'sac_v1': os.path.join(ARTIFACTS_DIR, 'sac_v1_realdb_50k.zip'),
}

# 모델 타입 정의
MODEL_TYPES = {
    'dqn_v3': 'discrete',   # DQN - Discrete action space
    'ppo_v3': 'discrete',   # PPO - Discrete action space (with masking)
    'ddpg_v1': 'continuous', # DDPG - Continuous action space
    'sac_v1': 'continuous',  # SAC - Continuous action space
}

# Voting 전략
VOTING_STRATEGIES = {
    'majority': 'majority_voting',      # 다수결 투표
    'weighted': 'weighted_voting',      # 가중치 기반 투표
    'equal': 'equal_weighted',          # 균등 가중치
    'performance': 'performance_based', # 성능 기반 가중치
    'query_type': 'query_type_based',   # 쿼리 타입별 가중치
}

# 모델별 기본 성능 가중치 (평가 보고서 기반)
# DQN v3: Mean Speedup ~1.15x
# PPO v3: Mean Speedup ~1.20x
# DDPG v1: Mean Speedup ~1.88x
# SAC v1: Mean Speedup ~1.50x (추정)
PERFORMANCE_WEIGHTS = {
    'dqn_v3': 1.15,
    'ppo_v3': 1.20,
    'ddpg_v1': 1.88,
    'sac_v1': 1.50,
}

# 쿼리 타입별 모델 가중치
# CTE 쿼리에 강한 모델, JOIN_HEAVY에 강한 모델 등
QUERY_TYPE_WEIGHTS = {
    'CTE': {
        'dqn_v3': 0.15,
        'ppo_v3': 0.40,  # PPO가 CTE에 강함
        'ddpg_v1': 0.25,
        'sac_v1': 0.20,
    },
    'JOIN_HEAVY': {
        'dqn_v3': 0.10,
        'ppo_v3': 0.15,
        'ddpg_v1': 0.45,  # DDPG가 복잡한 JOIN에 강함
        'sac_v1': 0.30,
    },
    'AGGREGATE': {
        'dqn_v3': 0.20,
        'ppo_v3': 0.25,
        'ddpg_v1': 0.25,
        'sac_v1': 0.30,  # SAC가 집계 쿼리에 강함 (추정)
    },
    'SIMPLE': {
        'dqn_v3': 0.35,  # 단순 쿼리는 DQN으로 충분
        'ppo_v3': 0.35,
        'ddpg_v1': 0.15,
        'sac_v1': 0.15,
    },
    'SUBQUERY': {
        'dqn_v3': 0.20,
        'ppo_v3': 0.30,
        'ddpg_v1': 0.30,
        'sac_v1': 0.20,
    },
    'WINDOW': {
        'dqn_v3': 0.15,
        'ppo_v3': 0.25,
        'ddpg_v1': 0.35,
        'sac_v1': 0.25,
    },
    'DEFAULT': {
        'dqn_v3': 0.20,
        'ppo_v3': 0.25,
        'ddpg_v1': 0.35,
        'sac_v1': 0.20,
    }
}

# Confidence Threshold
# 이 값보다 낮은 confidence를 가진 모델의 투표는 제외
CONFIDENCE_THRESHOLD = 0.1

# 평가 설정
EVAL_CONFIG = {
    'n_queries': 30,
    'n_episodes': 10,  # 빠른 검증용 (최종: 30 episodes)
    'max_steps': 10,
    'verbose': True,
}

# 결과 저장 경로
RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
CHARTS_DIR = os.path.join(RESULTS_DIR, 'charts')

# 출력 파일
OUTPUT_FILES = {
    'results_json': os.path.join(RESULTS_DIR, 'ensemble_voting_results.json'),
    'comparison_csv': os.path.join(RESULTS_DIR, 'ensemble_comparison.csv'),
    'detailed_json': os.path.join(RESULTS_DIR, 'detailed_results.json'),
}

