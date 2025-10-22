# -*- coding: utf-8 -*-
"""
PPO v3 Simulation 환경

특징:
- 30개 쿼리 (constants2.py)
- 44개 액션
- 18차원 actionable state
- Log scale normalized reward
- Action masking (Query 타입별)
"""

import sys
import os
import numpy as np
import json
import joblib
from gymnasium import spaces

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)

# PPO v3 imports
from RLQO.PPO_v3.env.v3_actionable_state import ActionableStateEncoderV3
from RLQO.PPO_v3.env.v3_normalized_reward import calculate_reward_v3_normalized
from RLQO.PPO_v3.config.query_action_mapping_v3 import QUERY_TYPES, PHASE1_ACTIONS, get_query_type

# DQN v3 sim_env 재사용 (XGB 예측)
from RLQO.DQN_v3.env.v3_sim_env import QueryPlanSimEnvV3


class QueryPlanSimEnvPPOv3(QueryPlanSimEnvV3):
    """
    PPO v3 Simulation 환경
    
    핵심 개선:
    - State: 79차원 → 18차원 actionable features
    - Reward: Log scale 정규화 [-1, +1]
    - Action: Query 타입별 9~10개
    - Action Space: 44개 (FAST 10개, MAXDOP 10개, ISOLATION 3개, 고급 DBA 10개)
    """
    
    def __init__(self, query_list, max_steps=10, **kwargs):
        # 부모 클래스 초기화 (DQN v3 sim_env)
        # action_space_path를 PPO v3용으로 오버라이드
        import os
        import json
        
        # 절대 경로 생성
        current_dir = os.path.dirname(os.path.abspath(__file__))
        apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
        
        action_space_path = os.path.join(apollo_ml_dir, 'artifacts', 'RLQO', 'configs', 'v3_action_space_ppo.json')
        compatibility_path = os.path.join(apollo_ml_dir, 'artifacts', 'RLQO', 'configs', 'v3_query_action_compatibility_ppo.json')
        
        kwargs['action_space_path'] = action_space_path
        kwargs['compatibility_path'] = compatibility_path
        
        # PPO v3 전용 캐시 파일 경로 설정 (상대 경로로 전달)
        kwargs['cache_path'] = 'Apollo.ML/artifacts/RLQO/cache/v3_plan_cache_ppo.pkl'
        
        # UTF-8 인코딩으로 JSON 파일 미리 로드
        with open(action_space_path, 'r', encoding='utf-8') as f:
            actions_data = json.load(f)
        with open(compatibility_path, 'r', encoding='utf-8') as f:
            compatibility_data_raw = json.load(f)
            # 중첩된 구조에서 실제 compatibility 데이터 추출
            compatibility_data = compatibility_data_raw.get('compatibility', compatibility_data_raw)
        
        super().__init__(query_list, max_steps, **kwargs)
        
        # 미리 로드한 데이터로 덮어쓰기
        self.actions = actions_data
        self.compatibility_map = compatibility_data
        
        # PPO v3 State encoder 교체
        self.state_encoder = ActionableStateEncoderV3()
        
        # Observation space 재정의 (18차원, [0, 1] 범위)
        self.observation_space = spaces.Box(
            low=0.0, high=1.0,
            shape=(18,), dtype=np.float32
        )
        
        # Query-specific actions (PPO v3)
        self.query_types_ppo = [get_query_type(i) for i in range(len(query_list))]
        self.phase1_actions_ppo = PHASE1_ACTIONS
        
        # 이력 추적
        self.prev_action_id = -1
        self.prev_reward = 0.0
        self.current_query_type_ppo = self.query_types_ppo[0] if self.query_types_ppo else 'SIMPLE'
        self.previous_metrics = None
        
        if self.verbose:
            print(f"[INFO] PPO v3 Simulation Environment initialized")
            print(f"       State: 18 dimensions (actionable features)")
            print(f"       Reward: [-1, +1] (log scale normalized)")
            print(f"       Actions: 9~10 per query type")
            print(f"       Total actions: {len(self.actions)}")
            print(f"       Query types: {set(self.query_types_ppo)}")
    
    def reset(self, seed=None, options=None):
        """환경 리셋 + 18차원 state 생성"""
        # Query 타입 미리 설정
        next_query_idx = self.current_query_ix % len(self.query_list)
        self.current_query_type_ppo = self.query_types_ppo[next_query_idx]
        
        # 부모 클래스 reset (베이스라인 측정 등)
        obs_79d, info = super().reset(seed, options)
        
        # 이력 초기화
        self.prev_action_id = -1
        self.prev_reward = 0.0
        self.previous_metrics = self.baseline_metrics.copy()
        
        # 현재 힌트 상태 (초기: 힌트 없음)
        current_hints = {
            'maxdop': 0,
            'fast_n': 0,
            'isolation': 0,
            'join_hint': 'none',
            'advanced_hints': 0
        }
        
        # 18차원 state 생성
        obs_18d = self.state_encoder.encode_from_query_and_metrics(
            sql=self.current_sql,
            current_metrics=self.baseline_metrics,
            current_hints=current_hints,
            prev_action_id=self.prev_action_id,
            prev_reward=self.prev_reward
        )
        
        info['query_type_ppo'] = self.current_query_type_ppo
        info['query_index'] = next_query_idx
        
        if self.verbose:
            print(f"[RESET] Query {next_query_idx}: Type={self.current_query_type_ppo}")
            print(f"        Baseline: {self.baseline_metrics['elapsed_time_ms']:.1f}ms, "
                  f"{self.baseline_metrics['logical_reads']} reads")
            print(f"        State shape: {obs_18d.shape}")
        
        return obs_18d, info
    
    def get_action_mask(self):
        """Query 타입별 허용 액션만 마스킹 (9-10개)"""
        # PPO v3 호환성 맵 사용 (부모 클래스 호출 안 함)
        current_query_idx = self.original_indices[self.current_query_ix % len(self.query_list)]
        
        # 호환 액션 이름 리스트 가져오기
        compatible_action_names = self.compatibility_map.get(str(current_query_idx), [])
        
        # 호환성 마스크 생성 (액션 이름으로 비교)
        base_mask = np.zeros(len(self.actions), dtype=np.float32)
        for i, action in enumerate(self.actions):
            if action['name'] in compatible_action_names:
                base_mask[i] = 1.0
        
        # Query 타입별 Phase 1 액션만 허용
        type_mask = np.zeros(len(self.actions), dtype=np.float32)
        allowed_actions = self.phase1_actions_ppo.get(self.current_query_type_ppo, [])
        for action_id in allowed_actions:
            if action_id < len(self.actions):
                type_mask[action_id] = 1.0
        
        # 기본 마스크와 AND 연산
        final_mask = base_mask * type_mask
        
        if self.verbose:
            compatible_count = int(np.sum(base_mask))
            type_count = int(np.sum(type_mask))
            final_count = int(np.sum(final_mask))
            print(f"[MASK] Query {current_query_idx}, Type {self.current_query_type_ppo}")
            print(f"       Compatible: {compatible_count}, Type-specific: {type_count}, Final: {final_count}")
        
        return final_mask
    
    def step(self, action_id):
        """
        액션 실행 + 정규화된 보상 계산 (캐시 기반)
        
        Args:
            action_id: 선택된 액션 ID (0-43)
        
        Returns:
            obs: 18차원 state
            reward: [-1, +1] 정규화된 보상
            terminated: 종료 여부
            truncated: 절단 여부
            info: 추가 정보
        """
        # 이전 메트릭 저장
        self.previous_metrics = self.current_metrics.copy()
        
        # 1. 액션 정보 추출
        action = self.actions[action_id]
        action_name = action['name']
        
        # 2. 액션 호환성 체크
        action_mask = self.get_action_mask()
        invalid_action = (action_mask[action_id] == 0)
        
        if invalid_action:
            # 호환되지 않는 액션 선택 시 즉시 페널티 반환
            reward = -1.0  # 정규화된 최소 보상
            terminated = True
            truncated = False
            
            if self.verbose:
                print(f"[INVALID] {action_name} - 호환되지 않는 액션")
            
            # 현재 SQL에서 힌트 추출
            current_hints = self.state_encoder.extract_hints_from_sql(self.current_sql)
            
            # 18차원 state 생성
            obs_18d = self.state_encoder.encode_from_query_and_metrics(
                sql=self.current_sql,
                current_metrics=self.current_metrics,
                current_hints=current_hints,
                prev_action_id=action_id,
                prev_reward=reward
            )
            
            info = {
                "action": action_name,
                "metrics": self.current_metrics,
                "baseline_metrics": self.baseline_metrics,
                "invalid_action": True
            }
            
            return obs_18d, reward, terminated, truncated, info
        
        # 3. 액션 적용된 SQL 생성
        from RLQO.DQN_v3.env.v3_db_env import apply_action_to_sql
        modified_sql = apply_action_to_sql(self.current_sql, action)
        
        # 4. 캐시에서 실제 성능 데이터 가져오기
        _, metrics_after = self._get_obs_from_cache(modified_sql)
        
        # 5. 정규화된 보상 계산
        reward = calculate_reward_v3_normalized(
            metrics_before=self.previous_metrics,
            metrics_after=metrics_after,
            baseline_metrics=self.baseline_metrics,
            query_type=self.current_query_type_ppo,
            action_id=action_id
        )
        
        # 6. 상태 업데이트
        self.current_metrics = metrics_after
        self.current_step += 1
        self.current_sql = modified_sql  # SQL 업데이트 (힌트 누적)
        
        # 7. 이력 업데이트
        self.prev_action_id = action_id
        self.prev_reward = reward
        
        # 8. 현재 SQL에서 힌트 추출
        current_hints = self.state_encoder.extract_hints_from_sql(self.current_sql)
        
        # 9. 18차원 state 생성
        obs_18d = self.state_encoder.encode_from_query_and_metrics(
            sql=self.current_sql,
            current_metrics=metrics_after,
            current_hints=current_hints,
            prev_action_id=self.prev_action_id,
            prev_reward=self.prev_reward
        )
        
        # 10. 종료 조건
        terminated = False
        truncated = (self.current_step >= self.max_steps)
        
        if self.verbose:
            after_time = metrics_after['elapsed_time_ms']
            baseline_time = self.baseline_metrics['elapsed_time_ms']
            speedup = baseline_time / max(after_time, 0.1)
            
            print(f"[STEP {self.current_step}] Action={action_name}, "
                  f"Time={after_time:.1f}ms (Speedup={speedup:.2f}x), "
                  f"Reward={reward:.3f}")
        
        info = {
            "action": action_name,
            "metrics": metrics_after,
            "baseline_metrics": self.baseline_metrics,
            "invalid_action": False
        }
        
        return obs_18d, reward, terminated, truncated, info


if __name__ == '__main__':
    print("=" * 80)
    print(" PPO v3 Simulation 환경 테스트")
    print("=" * 80)
    
    # constants2.py에서 쿼리 로드
    sys.path.insert(0, os.path.join(apollo_ml_dir, 'RLQO'))
    from constants2 import SAMPLE_QUERIES
    
    print(f"\n총 쿼리 개수: {len(SAMPLE_QUERIES)}")
    
    # 환경 생성
    env = QueryPlanSimEnvPPOv3(
        query_list=SAMPLE_QUERIES[:3],  # 처음 3개 쿼리만 테스트
        max_steps=5,
        curriculum_mode=False,
        verbose=True
    )
    
    print(f"\nAction space: {env.action_space}")
    print(f"Observation space: {env.observation_space}")
    print(f"Observation shape: {env.observation_space.shape}")
    
    # 리셋 테스트
    obs, info = env.reset()
    print(f"\n[Reset 완료]")
    print(f"  Observation shape: {obs.shape}")
    print(f"  Query type: {info['query_type_ppo']}")
    print(f"  State range: [{obs.min():.3f}, {obs.max():.3f}]")
    
    # 액션 마스크 테스트
    action_mask = env.get_action_mask()
    valid_actions = np.where(action_mask == 1.0)[0]
    
    print(f"\n[Action Mask]")
    print(f"  Valid actions: {len(valid_actions)}/{len(env.actions)}")
    print(f"  Valid action IDs: {valid_actions}")
    
    # 액션 실행 테스트
    if len(valid_actions) > 0:
        action = valid_actions[0]
        print(f"\n[Action 실행] {env.actions[action]['name']}")
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"  Reward: {reward:.4f}")
        print(f"  Terminated: {terminated}")
        print(f"  Observation shape: {obs.shape}")
    
    env.close()
    
    print("\n" + "=" * 80)
    print(" ✓ PPO v3 Simulation 환경 테스트 완료!")
    print("=" * 80)

