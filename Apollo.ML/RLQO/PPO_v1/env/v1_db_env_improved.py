# -*- coding: utf-8 -*-
"""
PPO v1 개선 RealDB 환경

실제 DB 환경에서 Query 타입별 보상 함수와 보수적 정책을 적용합니다.
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

from RLQO.DQN_v3.env.v3_db_env import QueryPlanDBEnvV3


class QueryPlanDBEnvV1Improved(QueryPlanDBEnvV3):
    """
    PPO v1 개선 RealDB 환경
    
    개선사항:
    - Query 타입 자동 분류
    - 타입별 보상 함수 적용
    - 보수적 정책 강제 (conservative_mode)
    """
    
    def __init__(self, 
                 query_list: list[str],
                 max_steps=10,
                 conservative_mode=True,
                 **kwargs):
        """
        Args:
            query_list: 쿼리 목록
            max_steps: 최대 스텝 수
            conservative_mode: True면 안전한 액션만 허용
            **kwargs: v3_db_env의 기타 파라미터
        """
        super().__init__(query_list, max_steps, **kwargs)
        
        from RLQO.PPO_v1.utils.query_classifier import classify_query
        
        # Query 타입 사전 분류
        self.query_types = [classify_query(q) for q in query_list]
        self.conservative_mode = conservative_mode
        self.current_query_type = None
        
        if self.verbose:
            print(f"[INFO] PPO v1 Improved RealDB Environment initialized")
            print(f"       Conservative mode: {conservative_mode}")
            print(f"       Query types: {set(self.query_types)}")
    
    def reset(self, seed=None, options=None):
        """환경 리셋 + Query 타입 설정"""
        obs, info = super().reset(seed, options)
        
        # 현재 쿼리 타입 설정
        query_idx = (self.current_query_ix - 1) % len(self.query_list)
        self.current_query_type = self.query_types[query_idx]
        
        info['query_type'] = self.current_query_type
        
        if self.verbose:
            print(f"[INFO] Query type: {self.current_query_type}")
        
        return obs, info
    
    def get_action_mask(self) -> np.ndarray:
        """
        보수적 모드에서는 안전한 액션만 허용
        기본 호환성 마스크와 AND 연산
        """
        # 기본 호환성 마스크 (쿼리별 호환 액션)
        base_mask = super().get_action_mask()
        
        if not self.conservative_mode:
            return base_mask
        
        from RLQO.PPO_v1.utils.query_classifier import QUERY_TYPE_SAFE_ACTIONS
        
        # Query 타입별 안전한 액션만 허용
        safe_actions = QUERY_TYPE_SAFE_ACTIONS.get(self.current_query_type, [])
        safe_mask = np.zeros(len(self.actions), dtype=np.float32)
        for action_id in safe_actions:
            safe_mask[action_id] = 1.0
        
        # 기본 마스크와 AND 연산 (둘 다 허용해야만 선택 가능)
        final_mask = base_mask * safe_mask
        
        if self.verbose:
            compatible_count = int(np.sum(base_mask))
            safe_count = int(np.sum(safe_mask))
            final_count = int(np.sum(final_mask))
            print(f"[MASK] Compatible: {compatible_count}, Safe: {safe_count}, Final: {final_count}")
        
        return final_mask
    
    def step(self, action_id):
        """
        액션 실행 + 개선된 보상 함수 적용
        """
        # 액션 정보 저장 (보상 계산에 필요)
        action = self.actions[action_id]
        action_name = action['name']
        
        # 메트릭 이전 상태 저장
        metrics_before = self.current_metrics.copy()
        
        # 부모 클래스의 step 실행
        obs, reward, terminated, truncated, info = super().step(action_id)
        
        # 개선된 보상 함수 적용
        if not info.get('invalid_action', False):
            from RLQO.PPO_v1.env.v1_reward_improved import calculate_reward_v1_improved
            
            reward = calculate_reward_v1_improved(
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
                print(f"[REWARD] Improved: {reward:.3f} (Type: {self.current_query_type}, Action: {action_name})")
        
        return obs, reward, terminated, truncated, info


if __name__ == '__main__':
    print("=== PPO v1 Improved RealDB Environment 테스트 ===\n")
    
    from RLQO.constants import SAMPLE_QUERIES
    
    # 환경 생성
    env = QueryPlanDBEnvV1Improved(
        query_list=SAMPLE_QUERIES[:2],  # 처음 2개 쿼리만 테스트
        max_steps=5,
        conservative_mode=True,
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
    print(f"Valid action IDs: {valid_actions[:10]}...")  # 처음 10개만
    
    # 액션 실행 테스트
    if len(valid_actions) > 0:
        action = valid_actions[0]
        print(f"\nValid action 테스트: {env.actions[action]['name']}")
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"Reward: {reward:.4f}")
        print(f"Metrics: {info.get('metrics', {})}")
    
    env.close()
    print("\n[SUCCESS] 개선된 RealDB 환경 테스트 완료!")

