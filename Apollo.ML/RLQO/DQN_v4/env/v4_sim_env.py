# -*- coding: utf-8 -*-
"""
DQN v4: XGBoost 시뮬레이션 환경 (constants2.py 기반 30개 쿼리)
- 액션 호환성 체크 및 마스킹
- v4 보상 함수 적용
- 실제 DB 실행 없이 XGB 예측 모델로 쿼리 성능 시뮬레이션
- constants2.py의 30개 샘플 쿼리 사용
"""

import json
import os
import pickle
import gymnasium as gym
import joblib
import numpy as np
from gymnasium import spaces

import sys
import os
# 현재 스크립트의 디렉토리를 기준으로 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
# DQN_v4/env/ -> DQN_v4 -> RLQO -> Apollo.ML
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.append(apollo_ml_dir)
sys.path.append(rlqo_dir)

from RLQO.DQN_v1.features.phase2_features import XGB_EXPECTED_FEATURES
from RLQO.DQN_v4.env.v4_reward import calculate_reward_v4


def simulate_query_execution(xgb_model, current_features, action_features):
    """
    XGB 모델을 사용하여 액션 적용 후 쿼리 실행 시간을 예측합니다.
    
    Args:
        xgb_model: 학습된 XGBoost 모델
        current_features: 현재 상태의 특징 벡터 (79차원)
        action_features: 액션으로 인한 특징 변화
    
    Returns:
        predicted_metrics: 예측된 실행 메트릭 (elapsed_time_ms, logical_reads, cpu_time_ms)
    """
    # 액션 적용 후 특징 벡터 생성
    modified_features = current_features.copy()
    
    # === 액션별 특징 수정 ===
    # Feature indices (phase2_features.py 기준):
    # [0] estimated_rows
    # [1] estimated_cost
    # [2] parallelism_degree
    # [3] join_type_hash
    # [4] join_type_loop
    # [5] scan_type_index
    # [6] scan_type_table
    # [7] logical_reads
    # [8] cpu_time_ms
    # [9] elapsed_time_ms
    
    # MAXDOP 액션
    if 'parallelism_degree_change' in action_features:
        modified_features[2] = action_features['parallelism_degree_change']
    
    # JOIN 타입 액션
    if 'join_type_hash' in action_features:
        modified_features[3] = action_features['join_type_hash']
    if 'join_type_loop' in action_features:
        modified_features[4] = action_features['join_type_loop']
    
    # 스캔 타입 액션
    if 'scan_type_index' in action_features:
        modified_features[5] = action_features['scan_type_index']
    if 'scan_type_table' in action_features:
        modified_features[6] = action_features['scan_type_table']
    
    # 예측 실행
    try:
        predicted_time = xgb_model.predict([modified_features])[0]
        predicted_time = max(0.1, predicted_time)  # 0 이하 방지
        
        # 논리적 읽기와 CPU 시간 추정 (간단한 비례 관계 가정)
        estimated_logical_reads = max(1, int(predicted_time * 10))
        estimated_cpu_time = max(0.1, predicted_time * 0.7)
        
        predicted_metrics = {
            'elapsed_time_ms': predicted_time,
            'logical_reads': estimated_logical_reads,
            'cpu_time_ms': estimated_cpu_time
        }
        
        return predicted_metrics
        
    except Exception as e:
        print(f"XGB 예측 실패: {e}")
        return {
            'elapsed_time_ms': float('inf'),
            'logical_reads': 0,
            'cpu_time_ms': 0
        }


def map_action_to_features(action: dict) -> dict:
    """
    액션을 특징 변화로 매핑합니다.
    
    Args:
        action: 액션 딕셔너리
        
    Returns:
        action_features: 특징 변화 딕셔너리
    """
    action_name = action.get('name', '')
    action_features = {}
    
    # MAXDOP 액션들
    if action_name == 'SET_MAXDOP_1':
        action_features['parallelism_degree_change'] = 1.0
    elif action_name == 'SET_MAXDOP_4':
        action_features['parallelism_degree_change'] = 4.0
    elif action_name == 'SET_MAXDOP_8':
        action_features['parallelism_degree_change'] = 8.0
    
    # JOIN 힌트들
    elif action_name == 'USE_HASH_JOIN':
        action_features['join_type_hash'] = 1.0
        action_features['join_type_loop'] = 0.0
    elif action_name == 'USE_LOOP_JOIN':
        action_features['join_type_hash'] = 0.0
        action_features['join_type_loop'] = 1.0
    elif action_name == 'USE_MERGE_JOIN':
        action_features['join_type_hash'] = 0.0
        action_features['join_type_loop'] = 0.0
    
    # 스캔 힌트들
    elif action_name == 'USE_NOLOCK':
        action_features['scan_type_table'] = 1.0
        action_features['scan_type_index'] = 0.0
    
    # FAST n 힌트들 (TOP 쿼리에 효과적)
    elif action_name in ['FAST_10', 'FAST_50', 'FAST_100', 'FAST_200']:
        # FAST 힌트는 예상 행 수를 줄이는 효과
        fast_value = int(action_name.split('_')[1])
        action_features['estimated_rows'] = fast_value
    
    # 기타 액션들은 기본적으로 성능 개선 효과 가정
    elif action_name not in ['NO_ACTION']:
        # 작은 개선 효과 (5-10%)
        action_features['estimated_cost'] = 0.9
    
    return action_features


class QueryPlanSimEnvV4(gym.Env):
    """
    DQN v4용 XGBoost 시뮬레이션 환경 (constants2.py 기반 30개 쿼리)
    - 액션 호환성 체크 및 마스킹
    - v4 보상 함수 적용
    - 실제 DB 없이 빠른 학습 가능
    - constants2.py의 30개 샘플 쿼리 사용
    """
    
    def __init__(self, 
                 query_list: list[str],
                 max_steps=10,
                 action_space_path='Apollo.ML/artifacts/RLQO/configs/v4_action_space.json',
                 compatibility_path='Apollo.ML/artifacts/RLQO/configs/v4_query_action_compatibility.json',
                 cache_path='Apollo.ML/artifacts/RLQO/cache/v4_plan_cache.pkl',
                 curriculum_mode=False,
                 verbose=True):
        super().__init__()
        
        # 1. 액션 스페이스 로드
        action_space_full_path = os.path.join(apollo_ml_dir, action_space_path.replace('Apollo.ML/', ''))
        with open(action_space_full_path, 'r', encoding='utf-8') as f:
            self.actions = json.load(f)
        
        # 2. 호환성 매핑 로드
        compatibility_full_path = os.path.join(apollo_ml_dir, compatibility_path.replace('Apollo.ML/', ''))
        with open(compatibility_full_path, 'r', encoding='utf-8') as f:
            self.compatibility_map = json.load(f)
        
        # 3. XGB 모델 로드
        model_path = os.path.join(apollo_ml_dir, 'artifacts/model.joblib')
        self.xgb_model = joblib.load(model_path)
        
        # 4. 실행 계획 캐시 로드
        cache_full_path = os.path.join(apollo_ml_dir, cache_path.replace('Apollo.ML/', ''))
        if os.path.exists(cache_full_path):
            with open(cache_full_path, 'rb') as f:
                self.plan_cache = pickle.load(f)
        else:
            print(f"[WARN] 캐시 파일이 없습니다: {cache_full_path}")
            print(f"[INFO] 캐시 없이 기본값으로 실행합니다.")
            self.plan_cache = {}
        
        # 5. Curriculum Learning 설정
        self.curriculum_mode = curriculum_mode
        self.query_list_original = query_list
        
        if curriculum_mode:
            # 쿼리 길이 기반 난이도 정렬 (간단한 구현)
            sorted_queries = sorted(enumerate(query_list), key=lambda x: len(x[1]))
            self.query_list = [q for _, q in sorted_queries]
            self.original_indices = [idx for idx, _ in sorted_queries]
        else:
            self.query_list = query_list
            self.original_indices = list(range(len(query_list)))
        
        # 6. 에피소드 변수
        self.current_query_ix = 0
        self.current_sql = ""
        self.max_steps = max_steps
        self.current_step = 0
        self.baseline_metrics = {}
        self.current_obs = None
        self.current_metrics = {}
        self.verbose = verbose
        
        # 7. Gym 인터페이스 정의
        self.action_space = spaces.Discrete(len(self.actions))
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(XGB_EXPECTED_FEATURES,), dtype=np.float32
        )

    def get_action_mask(self) -> np.ndarray:
        """현재 쿼리에 호환되는 액션 마스크를 반환합니다."""
        current_query_idx = self.original_indices[self.current_query_ix]
        compatible_actions = self.compatibility_map[str(current_query_idx)]
        
        mask = np.zeros(len(self.actions), dtype=np.float32)
        for i, action in enumerate(self.actions):
            if action['name'] in compatible_actions:
                mask[i] = 1.0
        
        return mask

    def _get_obs_from_cache(self, sql: str) -> tuple[np.ndarray, dict]:
        """캐시에서 실행 계획과 메트릭을 가져옵니다."""
        cache_key = sql.strip()
        
        if cache_key in self.plan_cache:
            cached_data = self.plan_cache[cache_key]
            observation = cached_data['observation']
            metrics = cached_data['metrics'].copy()
            
            # 안전성을 위해 0 이하 값 방지
            metrics['elapsed_time_ms'] = max(0.1, metrics['elapsed_time_ms'])
            metrics['logical_reads'] = max(1, metrics['logical_reads'])
            metrics['cpu_time_ms'] = max(0.1, metrics['cpu_time_ms'])
            
            return observation, metrics
        else:
            print(f"[WARN] 캐시에 없는 쿼리: {sql[:50]}...")
            # 기본값 반환
            observation = np.zeros(XGB_EXPECTED_FEATURES, dtype=np.float32)
            metrics = {
                'elapsed_time_ms': 100.0,
                'logical_reads': 1000,
                'cpu_time_ms': 70.0
            }
            return observation, metrics

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # 다음 쿼리 선택
        self.current_sql = self.query_list[self.current_query_ix]
        self.current_query_ix = (self.current_query_ix + 1) % len(self.query_list)
        
        self.current_step = 0
        
        if self.verbose:
            current_query_idx = self.original_indices[self.current_query_ix - 1]
            print(f"\n----- New Episode: Simulating Query {current_query_idx} -----")
            print(f"SQL: {self.current_sql[:100]}...")
        
        # 베이스라인 측정 (캐시에서)
        obs, metrics = self._get_obs_from_cache(self.current_sql)
        self.baseline_metrics = metrics.copy()
        self.current_obs = obs
        self.current_metrics = metrics.copy()
        
        if self.verbose:
            print(f"Baseline: {metrics.get('elapsed_time_ms', 0):.1f}ms, "
                  f"{metrics.get('logical_reads', 0)} reads")
        
        # 액션 마스크 생성
        action_mask = self.get_action_mask()
        compatible_count = int(np.sum(action_mask))
        
        if self.verbose:
            print(f"Compatible actions: {compatible_count}/{len(self.actions)}")
        
        info = {
            'metrics': metrics,
            'action_mask': action_mask,
            'compatible_actions': compatible_count,
            'query_idx': self.original_indices[self.current_query_ix - 1]
        }
        
        return obs, info

    def step(self, action_id):
        # 1. 액션 정보 추출
        action = self.actions[action_id]
        action_name = action['name']
        safety_score = action.get('safety_score', 1.0)
        
        # 2. 액션 호환성 체크
        action_mask = self.get_action_mask()
        invalid_action = (action_mask[action_id] == 0)
        
        if invalid_action:
            # 호환되지 않는 액션 선택 시 즉시 페널티 반환
            reward = -15.0
            terminated = True
            truncated = False
            
            if self.verbose:
                print(f"  [INVALID] {action_name} - 호환되지 않는 액션")
            
            info = {
                "action": action_name,
                "metrics": self.current_metrics,
                "baseline_metrics": self.baseline_metrics,
                "safety_score": safety_score,
                "invalid_action": True
            }
            
            return self.current_obs, reward, terminated, truncated, info
        
        # 3. 액션을 특징 변화로 매핑
        action_features = map_action_to_features(action)
        
        # 4. XGB 모델로 시뮬레이션 실행
        metrics_before = self.current_metrics.copy()
        predicted_metrics = simulate_query_execution(
            self.xgb_model, 
            self.current_obs, 
            action_features
        )
        
        # 5. 보상 계산 (v4)
        reward = calculate_reward_v4(
            metrics_before=metrics_before,
            metrics_after=predicted_metrics,
            baseline_metrics=self.baseline_metrics,
            step_num=self.current_step,
            max_steps=self.max_steps,
            action_safety_score=safety_score,
            invalid_action=False
        )
        
        # 6. 상태 업데이트
        self.current_obs = self.current_obs  # 관찰값은 동일 (특징 변화는 내부적으로만 적용)
        self.current_metrics = predicted_metrics
        self.current_step += 1
        
        # 7. 종료 조건
        terminated = False
        truncated = (self.current_step >= self.max_steps)
        
        if self.verbose:
            print(f"  - Action: {action_name} -> {predicted_metrics.get('elapsed_time_ms', 0):.1f}ms "
                  f"(reward: {reward:.3f})")
        
        info = {
            "action": action_name,
            "metrics": predicted_metrics,
            "baseline_metrics": self.baseline_metrics,
            "safety_score": safety_score,
            "invalid_action": False
        }
        
        return self.current_obs, reward, terminated, truncated, info

    def close(self):
        pass


if __name__ == '__main__':
    print("=== DQN v4 Simulation Environment 테스트 ===\n")
    
    from RLQO.constants2 import SAMPLE_QUERIES
    
    # 환경 생성
    env = QueryPlanSimEnvV4(
        query_list=SAMPLE_QUERIES[:3],  # 처음 3개 쿼리만 테스트
        max_steps=5,
        curriculum_mode=True,
        verbose=True
    )
    
    print(f"Action space: {env.action_space}")
    print(f"Observation space: {env.observation_space}")
    
    # 리셋 테스트
    obs, info = env.reset()
    print(f"\nReset 완료:")
    print(f"Observation shape: {obs.shape}")
    print(f"Action mask: {info['action_mask']}")
    print(f"Compatible actions: {info['compatible_actions']}")
    
    # 액션 테스트
    action_mask = info['action_mask']
    valid_actions = np.where(action_mask == 1.0)[0]
    invalid_actions = np.where(action_mask == 0.0)[0]
    
    if len(valid_actions) > 0:
        print(f"\nValid action 테스트: {env.actions[valid_actions[0]]['name']}")
        obs, reward, terminated, truncated, info = env.step(valid_actions[0])
        print(f"Reward: {reward:.4f}")
    
    if len(invalid_actions) > 0:
        print(f"\nInvalid action 테스트: {env.actions[invalid_actions[0]]['name']}")
        obs, reward, terminated, truncated, info = env.step(invalid_actions[0])
        print(f"Reward: {reward:.4f}")
        print(f"Invalid action: {info['invalid_action']}")
    
    env.close()
    print("\n[SUCCESS] 시뮬레이션 환경 테스트 완료!")
