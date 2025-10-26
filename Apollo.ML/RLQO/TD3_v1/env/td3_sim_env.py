# -*- coding: utf-8 -*-
"""
TD3 v1: Simulation Environment

TD3는 DDPG와 동일한 연속 액션 공간 (Box[0,1]^7)을 사용하므로
DDPG v1의 simulation 환경을 그대로 재사용합니다.

차이점:
- TD3 알고리즘 자체가 Twin Critic, Delayed Update, Target Smoothing을 구현
- 환경은 동일하게 유지
"""

import os
import sys

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, rlqo_dir)

# Import DDPG v1 Simulation Environment
from RLQO.DDPG_v1.env.ddpg_sim_env import QueryPlanSimEnvDDPGv1


class QueryPlanSimEnvTD3v1(QueryPlanSimEnvDDPGv1):
    """
    TD3 v1 Simulation Environment
    
    DDPG v1 Sim Environment를 상속받아 사용.
    TD3는 알고리즘 차원에서 개선되었으므로 환경은 동일.
    
    TD3 개선사항 (Stable-Baselines3 TD3 알고리즘이 구현):
    1. Twin Critic Networks (Q1, Q2)
    2. Delayed Policy Updates (policy_delay=2)
    3. Target Policy Smoothing (target_policy_noise=0.2)
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # TD3 specific metadata (optional)
        self.metadata = {
            'name': 'TD3v1_Simulation',
            'algorithm': 'TD3',
            'features': [
                'Twin Critic Networks',
                'Delayed Policy Updates',
                'Target Policy Smoothing'
            ]
        }


# Convenience function
def make_td3_sim_env(query_list, max_steps=10, verbose=True):
    """
    TD3 v1 Simulation 환경 생성
    
    Args:
        query_list: 30개 쿼리 리스트
        max_steps: 에피소드당 최대 스텝
        verbose: 로그 출력 여부
    
    Returns:
        env: TD3 v1 Simulation Environment
    """
    return QueryPlanSimEnvTD3v1(
        query_list=query_list,
        max_steps=max_steps,
        verbose=verbose
    )


if __name__ == '__main__':
    print("TD3 v1 Simulation Environment")
    print("=" * 80)
    print("TD3는 DDPG v1 환경을 재사용하며, 알고리즘 차원에서 개선됩니다:")
    print("1. Twin Critic Networks - Q-value overestimation 방지")
    print("2. Delayed Policy Updates - 안정성 향상")
    print("3. Target Policy Smoothing - 과적합 방지")
    print("=" * 80)
    
    # Test environment creation
    from RLQO.constants2 import QUERY_LIST
    
    env = make_td3_sim_env(QUERY_LIST, max_steps=10, verbose=True)
    print(f"\n환경 생성 성공!")
    print(f"Action space: {env.action_space}")
    print(f"Observation space: {env.observation_space}")
    print(f"Metadata: {env.metadata}")

