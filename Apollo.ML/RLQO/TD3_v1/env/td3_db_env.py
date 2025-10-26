# -*- coding: utf-8 -*-
"""
TD3 v1: Real DB Environment

TD3는 DDPG와 동일한 연속 액션 공간을 사용하므로
DDPG v1의 Real DB 환경을 그대로 재사용합니다.
"""

import os
import sys

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, rlqo_dir)

# Import DDPG v1 Real DB Environment
from RLQO.DDPG_v1.env.ddpg_db_env import QueryPlanDbEnvDDPGv1


class QueryPlanDbEnvTD3v1(QueryPlanDbEnvDDPGv1):
    """
    TD3 v1 Real DB Environment
    
    DDPG v1 DB Environment를 상속받아 사용.
    TD3는 알고리즘 차원에서 개선되었으므로 환경은 동일.
    
    TD3 개선사항 (Stable-Baselines3 TD3 알고리즘이 구현):
    1. Twin Critic Networks (Q1, Q2)
    2. Delayed Policy Updates (policy_delay=2)
    3. Target Policy Smoothing (target_policy_noise=0.2)
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # TD3 specific metadata
        self.metadata = {
            'name': 'TD3v1_RealDB',
            'algorithm': 'TD3',
            'features': [
                'Twin Critic Networks',
                'Delayed Policy Updates',
                'Target Policy Smoothing'
            ]
        }


# Convenience function
def make_td3_db_env(query_list, db_helper, max_steps=10, verbose=True):
    """
    TD3 v1 Real DB 환경 생성
    
    Args:
        query_list: 30개 쿼리 리스트
        db_helper: DB 연결 헬퍼
        max_steps: 에피소드당 최대 스텝
        verbose: 로그 출력 여부
    
    Returns:
        env: TD3 v1 Real DB Environment
    """
    return QueryPlanDbEnvTD3v1(
        query_list=query_list,
        db_helper=db_helper,
        max_steps=max_steps,
        verbose=verbose
    )


if __name__ == '__main__':
    print("TD3 v1 Real DB Environment")
    print("=" * 80)
    print("TD3는 DDPG v1 환경을 재사용하며, 알고리즘 차원에서 개선됩니다:")
    print("1. Twin Critic Networks - Q-value overestimation 방지")
    print("2. Delayed Policy Updates - 안정성 향상")
    print("3. Target Policy Smoothing - 과적합 방지")
    print("=" * 80)
    
    print("\n주의: Real DB 환경 테스트는 실제 DB 연결이 필요합니다.")
    print("학습 스크립트에서 사용하세요: train/td3_train_realdb.py")

