# -*- coding: utf-8 -*-
"""
PPO v2 Simulation 환경

변경사항:
- State: 79차원 XGB features → 18차원 actionable features
- Reward: 정규화된 reward [-1, +1]
- Action: Query-Specific (5-7개)
"""

import sys
import os
import numpy as np
from gymnasium import spaces

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)

from RLQO.DQN_v3.env.v3_sim_env import QueryPlanSimEnvV3
from RLQO.PPO_v2.env.v2_actionable_state import ActionableStateEncoder
from RLQO.PPO_v2.env.v2_normalized_reward import calculate_reward_v2_normalized
from RLQO.PPO_v2.config.query_action_mapping import PHASE1_ACTIONS
from RLQO.PPO_v1.utils.query_classifier import classify_query


class QueryPlanSimEnvV2(QueryPlanSimEnvV3):
    """
    PPO v2 Simulation 환경
    
    핵심 개선:
    - State: 79차원 → 18차원 actionable features
    - Reward: Log scale 정규화 [-1, +1]
    - Action: Query 타입별 5개
    """
    
    def __init__(self, query_list, max_steps=10, **kwargs):
        # 부모 클래스 초기화
        super().__init__(query_list, max_steps, **kwargs)
        
        # State encoder 교체
        self.state_encoder = ActionableStateEncoder()
        
        # Observation space 재정의 (18차원, [0, 1] 범위)
        self.observation_space = spaces.Box(
            low=0.0, high=1.0,
            shape=(18,), dtype=np.float32
        )
        
        # Query-specific actions
        self.query_types = [classify_query(q) for q in query_list]
        self.phase1_actions = PHASE1_ACTIONS
        
        # 이력 추적
        self.prev_action_id = -1
        self.prev_reward = 0.0
        self.current_query_type = None
        self.previous_metrics = None
        
        if self.verbose:
            print(f"[INFO] PPO v2 Simulation Environment initialized")
            print(f"       State: 18 dimensions (actionable features)")
            print(f"       Reward: [-1, +1] (log scale normalized)")
            print(f"       Actions: 5-7 per query type")
    
    def reset(self, seed=None, options=None):
        """환경 리셋 + 18차원 state 생성"""
        # 부모 클래스 reset (베이스라인 측정 등)
        obs_79d, info = super().reset(seed, options)
        
        # Query 타입 설정
        query_idx = (self.current_query_ix - 1) % len(self.query_list)
        self.current_query_type = self.query_types[query_idx]
        
        # 이력 초기화
        self.prev_action_id = -1
        self.prev_reward = 0.0
        self.previous_metrics = self.baseline_metrics.copy()
        
        # 현재 힌트 상태 (초기: 힌트 없음)
        current_hints = {
            'maxdop': 0,
            'join_hint': 'none',
            'isolation_hint': False,
            'recompile': False,
            'optimize_for_unknown': False
        }
        
        # 18차원 state 생성
        obs_18d = self.state_encoder.encode_from_query_and_metrics(
            sql=self.current_sql,
            current_metrics=self.baseline_metrics,
            current_hints=current_hints,
            prev_action_id=self.prev_action_id,
            prev_reward=self.prev_reward
        )
        
        info['query_type'] = self.current_query_type
        
        if self.verbose:
            print(f"[RESET] Query {query_idx}: Type={self.current_query_type}")
            print(f"        Baseline: {self.baseline_metrics['elapsed_time_ms']:.1f}ms, "
                  f"{self.baseline_metrics['logical_reads']} reads")
            print(f"        State shape: {obs_18d.shape}")
        
        return obs_18d, info
    
    def get_action_mask(self):
        """Query 타입별 허용 액션만 마스킹 (5개)"""
        mask = np.zeros(19, dtype=np.float32)
        allowed_actions = self.phase1_actions.get(self.current_query_type, [])
        for action_id in allowed_actions:
            mask[action_id] = 1.0
        
        if self.verbose:
            print(f"[MASK] Type={self.current_query_type}, Allowed={len(allowed_actions)} actions: {allowed_actions}")
        
        return mask
    
    def step(self, action_id):
        """
        액션 실행 + 정규화된 보상 계산
        
        Args:
            action_id: 선택된 액션 ID (0-18)
        
        Returns:
            obs: 18차원 state
            reward: [-1, +1] 정규화된 보상
            terminated: 종료 여부
            truncated: 절단 여부
            info: 추가 정보
        """
        # 이전 메트릭 저장
        self.previous_metrics = self.current_metrics.copy()
        
        # 부모 클래스 step (XGB 시뮬레이션)
        obs_79d, _, terminated, truncated, info = super().step(action_id)
        
        # 정규화된 보상 계산
        reward = calculate_reward_v2_normalized(
            metrics_before=self.previous_metrics,
            metrics_after=info['metrics'],
            baseline_metrics=self.baseline_metrics,
            query_type=self.current_query_type,
            action_id=action_id
        )
        
        # 이력 업데이트
        self.prev_action_id = action_id
        self.prev_reward = reward
        
        # 현재 SQL에서 힌트 추출
        current_hints = self.state_encoder.extract_hints_from_sql(self.current_sql)
        
        # 18차원 state 생성
        obs_18d = self.state_encoder.encode_from_query_and_metrics(
            sql=self.current_sql,
            current_metrics=info['metrics'],
            current_hints=current_hints,
            prev_action_id=self.prev_action_id,
            prev_reward=self.prev_reward
        )
        
        if self.verbose:
            action_name = self.actions[action_id]['name']
            after_time = info['metrics']['elapsed_time_ms']
            baseline_time = self.baseline_metrics['elapsed_time_ms']
            speedup = baseline_time / max(after_time, 0.1)
            
            print(f"[STEP {self.current_step}] Action={action_name}, "
                  f"Time={after_time:.1f}ms (Speedup={speedup:.2f}x), "
                  f"Reward={reward:.3f}")
        
        return obs_18d, reward, terminated, truncated, info


if __name__ == '__main__':
    print("=== PPO v2 Simulation 환경 테스트 ===\n")
    
    from RLQO.constants import SAMPLE_QUERIES
    
    # 환경 생성
    env = QueryPlanSimEnvV2(
        query_list=SAMPLE_QUERIES[:2],  # 처음 2개 쿼리만 테스트
        max_steps=5,
        curriculum_mode=False,
        verbose=True
    )
    
    print(f"Action space: {env.action_space}")
    print(f"Observation space: {env.observation_space}")
    print(f"Observation shape: {env.observation_space.shape}\n")
    
    # 리셋 테스트
    obs, info = env.reset()
    print(f"\nReset 완료:")
    print(f"  Observation shape: {obs.shape}")
    print(f"  Query type: {info['query_type']}")
    print(f"  State range: [{obs.min():.3f}, {obs.max():.3f}]")
    
    # 액션 마스크 테스트
    action_mask = env.get_action_mask()
    valid_actions = np.where(action_mask == 1.0)[0]
    
    print(f"\nValid actions: {len(valid_actions)}/{len(env.actions)}")
    print(f"Valid action IDs: {valid_actions}")
    
    # 액션 실행 테스트
    if len(valid_actions) > 0:
        action = valid_actions[0]
        print(f"\nValid action 테스트: {env.actions[action]['name']}")
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"Reward: {reward:.4f}")
        print(f"Terminated: {terminated}")
        print(f"Observation shape: {obs.shape}")
    
    env.close()
    print("\n[SUCCESS] PPO v2 Simulation 환경 테스트 완료!")

