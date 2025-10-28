# -*- coding: utf-8 -*-
"""
Ensemble v1: Environment Wrapper

평가를 위한 환경 래퍼 및 유틸리티
"""

import os
import sys

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')
rlqo_dir = os.path.join(apollo_ml_dir, 'RLQO')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)


def create_dqn_env(queries, max_steps=10, verbose=False):
    """DQN v3 평가 환경 생성"""
    from RLQO.DQN_v3.env.v3_db_env import QueryPlanDBEnvV3
    return QueryPlanDBEnvV3(
        query_list=queries,
        max_steps=max_steps,
        verbose=verbose
    )


def create_ppo_env(queries, max_steps=10, verbose=False):
    """PPO v3 평가 환경 생성 (ActionMasker 적용)"""
    from RLQO.PPO_v3.env.v3_db_env import QueryPlanDBEnvPPOv3
    from sb3_contrib.common.wrappers import ActionMasker
    
    env = QueryPlanDBEnvPPOv3(
        query_list=queries,
        max_steps=max_steps,
        curriculum_mode=False,
        verbose=verbose
    )
    
    # PPO용 액션 마스크 적용
    def mask_fn(env):
        float_mask = env.get_action_mask()
        return float_mask.astype(bool)
    
    return ActionMasker(env, mask_fn)


def create_ddpg_env(queries, max_steps=10, verbose=False):
    """DDPG v1 평가 환경 생성"""
    from RLQO.DDPG_v1.env.ddpg_db_env import QueryPlanRealDBEnvDDPGv1
    return QueryPlanRealDBEnvDDPGv1(
        query_list=queries,
        max_steps=max_steps,
        verbose=verbose
    )


def create_sac_env(queries, max_steps=10, verbose=False):
    """SAC v1 평가 환경 생성"""
    from RLQO.SAC_v1.env.sac_db_env import make_sac_db_env
    return make_sac_db_env(
        query_list=queries,
        max_steps=max_steps,
        verbose=verbose
    )


def get_env_creator(model_name):
    """모델 이름에 따른 환경 생성 함수 반환"""
    creators = {
        'dqn_v3': create_dqn_env,
        'ppo_v3': create_ppo_env,
        'ddpg_v1': create_ddpg_env,
        'sac_v1': create_sac_env,
    }
    return creators.get(model_name)


def apply_action_to_query(query, action, model_type='discrete'):
    """
    액션을 쿼리에 적용
    
    Args:
        query: SQL 쿼리 문자열
        action: 액션 (discrete: int, continuous: np.array)
        model_type: 'discrete' or 'continuous'
    
    Returns:
        modified_query: 최적화된 쿼리
    """
    if model_type == 'discrete':
        # DQN, PPO의 경우
        from RLQO.DQN_v3.env.v3_db_env import apply_action_to_sql
        return apply_action_to_sql(query, action)
    
    elif model_type == 'continuous':
        # DDPG, SAC의 경우 - action decoder 사용
        from RLQO.DDPG_v1.config.action_decoder import decode_continuous_action
        hints = decode_continuous_action(action)
        
        # 힌트를 쿼리에 적용
        from RLQO.DDPG_v1.env.ddpg_db_env import apply_hints_to_sql
        return apply_hints_to_sql(query, hints)
    
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

