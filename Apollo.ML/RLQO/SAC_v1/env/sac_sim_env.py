# -*- coding: utf-8 -*-
"""
SAC v1: Simulation Environment

SAC는 DDPG와 동일한 연속 액션 공간 (Box[0,1]^7)을 사용하지만
Stochastic policy를 학습합니다.

차이점:
- SAC 알고리즘이 Entropy-regularized objective 사용
- Stochastic policy (vs DDPG의 deterministic)
- Automatic temperature tuning
- 환경 자체는 동일
"""

import os
import sys

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, rlqo_dir)

# Import DDPG v1 Simulation Environment
from RLQO.DDPG_v1.env.ddpg_sim_env import QueryPlanSimEnvDDPGv1


class QueryPlanSimEnvSACv1(QueryPlanSimEnvDDPGv1):
    """
    SAC v1 Simulation Environment
    
    DDPG v1 Sim Environment를 상속받아 사용.
    SAC는 알고리즘 차원에서 개선되었으므로 환경은 동일.
    
    SAC 개선사항 (Stable-Baselines3 SAC 알고리즘이 구현):
    1. Entropy-regularized objective (탐색 장려)
    2. Automatic temperature tuning (α 자동 조정)
    3. Stochastic policy (확률적 액션 선택)
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # SAC specific metadata
        self.metadata = {
            'name': 'SACv1_Simulation',
            'algorithm': 'SAC',
            'features': [
                'Maximum Entropy RL',
                'Automatic Temperature Tuning',
                'Stochastic Policy'
            ]
        }


# Convenience function
def make_sac_sim_env(query_list, max_steps=10, verbose=True):
    """
    SAC v1 Simulation 환경 생성
    
    Args:
        query_list: 30개 쿼리 리스트
        max_steps: 에피소드당 최대 스텝
        verbose: 로그 출력 여부
    
    Returns:
        env: SAC v1 Simulation Environment
    """
    return QueryPlanSimEnvSACv1(
        query_list=query_list,
        max_steps=max_steps,
        verbose=verbose
    )


if __name__ == '__main__':
    print("SAC v1 Simulation Environment")
    print("=" * 80)
    print("SAC는 DDPG v1 환경을 재사용하며, 알고리즘 차원에서 개선됩니다:")
    print("1. Entropy-regularized RL - 탐색 장려")
    print("2. Automatic temperature tuning - α 자동 조정")
    print("3. Stochastic policy - 확률적 액션 선택")
    print("=" * 80)
    
    # Test environment creation
    from RLQO.constants2 import SAMPLE_QUERIES
    
    env = make_sac_sim_env(SAMPLE_QUERIES, max_steps=10, verbose=True)
    print(f"\n환경 생성 성공!")
    print(f"Action space: {env.action_space}")
    print(f"Observation space: {env.observation_space}")
    print(f"Metadata: {env.metadata}")

