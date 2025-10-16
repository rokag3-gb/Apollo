# -*- coding: utf-8 -*-
"""
PPO v1 RealDB 환경 (No Conservative Mode)

Conservative mode를 OFF로 하고 안전 보너스를 감소시킨 환경
"""

import sys
import os
import numpy as np

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)

from RLQO.PPO_v1.env.v1_db_env_improved import QueryPlanDBEnvV1Improved


class QueryPlanDBEnvV1NoConservative(QueryPlanDBEnvV1Improved):
    """
    PPO v1 RealDB 환경 (No Conservative Mode)
    
    v1_improved와의 차이:
    - 새로운 보상 함수 사용 (안전 보너스 감소: +2.0 → +0.5)
    - Conservative mode OFF (Action space 확장)
    """
    
    def __init__(self, 
                 query_list: list[str],
                 max_steps=10,
                 conservative_mode=False,  # 기본값 False
                 **kwargs):
        """
        Args:
            query_list: 쿼리 목록
            max_steps: 최대 스텝 수
            conservative_mode: False 권장 (Action space 확장)
            **kwargs: 기타 파라미터
        """
        super().__init__(query_list, max_steps, conservative_mode, **kwargs)
        
        if self.verbose:
            print(f"[INFO] Using No Conservative reward function")
            print(f"       Safety bonus: +0.5 (reduced from +2.0)")
    
    def step(self, action_id):
        """
        액션 실행 + No Conservative 보상 함수 적용
        """
        # 액션 정보 저장
        action = self.actions[action_id]
        action_name = action['name']
        
        # 메트릭 이전 상태 저장
        metrics_before = self.current_metrics.copy()
        
        # DQN v3 부모 클래스의 step 실행
        # (중간 부모인 v1_improved의 step을 건너뛰고, v3_db_env의 step을 호출)
        from RLQO.DQN_v3.env.v3_db_env import QueryPlanDBEnvV3
        obs, reward, terminated, truncated, info = QueryPlanDBEnvV3.step(self, action_id)
        
        # No Conservative 보상 함수 적용
        if not info.get('invalid_action', False):
            from RLQO.PPO_v1.env.v1_reward_noconservative import calculate_reward_v1_noconservative
            
            reward = calculate_reward_v1_noconservative(
                metrics_before=metrics_before,
                metrics_after=info['metrics'],
                baseline_metrics=self.baseline_metrics,
                query_type=self.current_query_type,
                action_id=action_id,
                action_name=action_name,
                step_num=self.current_step - 1,
                max_steps=self.max_steps
            )
            
            if self.verbose:
                print(f"[REWARD] No Conservative: {reward:.3f} (Type: {self.current_query_type}, Action: {action_name})")
        
        return obs, reward, terminated, truncated, info


if __name__ == '__main__':
    print("=== PPO v1 No Conservative RealDB Environment 테스트 ===\n")
    
    from RLQO.constants import SAMPLE_QUERIES
    
    # 환경 생성 (Conservative Mode OFF)
    env = QueryPlanDBEnvV1NoConservative(
        query_list=SAMPLE_QUERIES[:2],
        max_steps=5,
        conservative_mode=False,
        curriculum_mode=False,
        verbose=True
    )
    
    print(f"Action space: {env.action_space}")
    print(f"Observation space: {env.observation_space}")
    
    # 리셋 테스트
    obs, info = env.reset()
    print(f"\nReset 완료:")
    print(f"Observation shape: {obs.shape if obs is not None else 'None'}")
    print(f"Query type: {info['query_type']}")
    
    # 액션 마스크 테스트
    action_mask = env.get_action_mask()
    valid_actions = np.where(action_mask == 1.0)[0]
    
    print(f"\nValid actions: {len(valid_actions)}/{len(env.actions)}")
    print(f"Valid action IDs: {valid_actions[:10]}...")
    
    # 액션 실행 테스트
    if len(valid_actions) > 0:
        action = valid_actions[0]
        print(f"\nValid action 테스트: {env.actions[action]['name']}")
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"Reward: {reward:.4f}")
        print(f"Metrics: {info.get('metrics', {})}")
    
    env.close()
    print("\n[SUCCESS] No Conservative RealDB 환경 테스트 완료!")

