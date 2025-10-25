# -*- coding: utf-8 -*-
"""
DDPG v1: Simulation Environment with Continuous Action Space

핵심 특징:
- Continuous action space: Box(0, 1, shape=(7,))
- State: 18차원 actionable state (PPO v3 재사용)
- Reward: Log scale normalized (PPO v3 재사용)
- Simulation: XGBoost 예측 모델 (DQN v3 재사용)
"""

import os
import sys
import pickle
import json
import numpy as np
import joblib
import gymnasium as gym
from gymnasium import spaces

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)

# Imports
from RLQO.DDPG_v1.config.action_decoder import ContinuousActionDecoder
from RLQO.PPO_v3.env.v3_actionable_state import ActionableStateEncoderV3
from RLQO.PPO_v3.env.v3_normalized_reward import calculate_reward_v3_normalized
from RLQO.DQN_v1.features.phase2_features import XGB_EXPECTED_FEATURES


class QueryPlanSimEnvDDPGv1(gym.Env):
    """
    DDPG v1 Simulation Environment
    
    특징:
    - Continuous action space (7차원)
    - 18차원 actionable state
    - XGBoost 시뮬레이션
    - Log scale normalized reward
    """
    
    def __init__(self,
                 query_list: list,
                 max_steps: int = 10,
                 verbose: bool = True):
        """
        Args:
            query_list: 30개 쿼리 리스트 (constants2.py)
            max_steps: 에피소드당 최대 스텝
            verbose: 로그 출력 여부
        """
        super().__init__()
        
        self.query_list = query_list
        self.max_steps = max_steps
        self.verbose = verbose
        
        # Action decoder
        self.action_decoder = ContinuousActionDecoder()
        
        # State encoder (PPO v3)
        self.state_encoder = ActionableStateEncoderV3()
        
        # XGB 모델 로드
        model_path = os.path.join(apollo_ml_dir, 'artifacts', 'model.joblib')
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"XGB 모델을 찾을 수 없습니다: {model_path}")
        self.xgb_model = joblib.load(model_path)
        
        # 실행 계획 캐시 로드 (PPO v3 캐시 사용)
        cache_path = os.path.join(apollo_ml_dir, 'artifacts', 'RLQO', 'cache', 'v3_plan_cache_ppo.pkl')
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                self.plan_cache = pickle.load(f)
            if self.verbose:
                print(f"[INFO] 캐시 로드 완료: {len(self.plan_cache)} entries")
        else:
            print(f"[WARN] 캐시 파일이 없습니다: {cache_path}")
            self.plan_cache = {}
        
        # Gym spaces
        # Action space: 7차원 continuous [0, 1]
        self.action_space = spaces.Box(
            low=0.0, 
            high=1.0, 
            shape=(7,), 
            dtype=np.float32
        )
        
        # Observation space: 18차원 actionable state [0, 1]
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(18,),
            dtype=np.float32
        )
        
        # Episode 변수
        self.current_query_ix = 0
        self.current_sql = ""
        self.current_step = 0
        self.baseline_metrics = {}
        self.current_metrics = {}
        self.current_hints = {}
        self.prev_action_vector = None
        self.prev_reward = 0.0
        
        if self.verbose:
            print(f"[INFO] DDPG v1 Simulation Environment initialized")
            print(f"  - Queries: {len(query_list)}")
            print(f"  - Action space: Continuous (7 dims)")
            print(f"  - Observation space: 18 dims")
    
    def _get_baseline_from_cache(self, sql: str) -> tuple:
        """캐시에서 베이스라인 메트릭을 가져옵니다."""
        cache_key = sql.strip()
        
        if cache_key in self.plan_cache:
            cached_data = self.plan_cache[cache_key]
            features = cached_data.get('observation', np.zeros(XGB_EXPECTED_FEATURES))
            metrics = cached_data.get('metrics', {
                'elapsed_time_ms': 100.0,
                'logical_reads': 1000,
                'cpu_time_ms': 70.0
            }).copy()
            
            # 안전 장치
            metrics['elapsed_time_ms'] = max(0.1, metrics['elapsed_time_ms'])
            metrics['logical_reads'] = max(1, metrics['logical_reads'])
            metrics['cpu_time_ms'] = max(0.1, metrics['cpu_time_ms'])
            
            return features, metrics
        else:
            # 기본값
            if self.verbose:
                print(f"[WARN] 캐시에 없는 쿼리: {sql[:50]}...")
            features = np.zeros(XGB_EXPECTED_FEATURES, dtype=np.float32)
            metrics = {
                'elapsed_time_ms': 100.0,
                'logical_reads': 1000,
                'cpu_time_ms': 70.0
            }
            return features, metrics
    
    def _simulate_query_with_hints(self, sql: str, hints: dict) -> dict:
        """
        XGB 모델을 사용하여 힌트 적용 후 성능을 시뮬레이션합니다.
        
        Args:
            sql: SQL 쿼리
            hints: 적용할 힌트들
        
        Returns:
            metrics: 예측된 성능 메트릭
        """
        # 베이스라인 features 가져오기
        baseline_features, _ = self._get_baseline_from_cache(sql)
        
        # 힌트에 따른 feature 수정
        modified_features = baseline_features.copy()
        
        # Feature indices (phase2_features.py 기준):
        # [2] parallelism_degree
        # [3] join_type_hash
        # [4] join_type_loop
        # [7] logical_reads
        # [8] cpu_time_ms
        # [9] elapsed_time_ms
        
        # MAXDOP 적용
        maxdop = hints.get('maxdop', 0)
        if maxdop > 0 and len(modified_features) > 2:
            modified_features[2] = float(maxdop)
        
        # JOIN 힌트 적용
        join_hint = hints.get('join_hint', 'none')
        if join_hint == 'hash' and len(modified_features) > 4:
            modified_features[3] = 1.0
            modified_features[4] = 0.0
        elif join_hint == 'loop' and len(modified_features) > 4:
            modified_features[3] = 0.0
            modified_features[4] = 1.0
        elif join_hint == 'merge' and len(modified_features) > 4:
            modified_features[3] = 0.0
            modified_features[4] = 0.0
        
        # FAST 힌트 적용 (estimated_rows 감소)
        fast_n = hints.get('fast_n', 0)
        if fast_n > 0 and len(modified_features) > 0:
            modified_features[0] = min(modified_features[0], float(fast_n))
        
        # XGB 예측
        try:
            predicted_time = self.xgb_model.predict([modified_features])[0]
            predicted_time = max(0.1, predicted_time)
            
            # 추가 힌트에 따른 조정
            improvement_factor = 1.0
            
            # Optimizer hints
            opt_hint = hints.get('optimizer_hint', 'NONE')
            if opt_hint in ['FORCESEEK', 'FORCESCAN']:
                improvement_factor *= 0.95  # 5% 개선
            elif opt_hint in ['ENABLE_QUERY_OPTIMIZER_HOTFIXES', 'FORCE_LEGACY_CARDINALITY_ESTIMATION']:
                improvement_factor *= 0.97  # 3% 개선
            
            # RECOMPILE
            if hints.get('use_recompile', False):
                improvement_factor *= 0.98  # 2% 개선 (파라미터 최적화)
            
            # ISOLATION (READ_UNCOMMITTED는 빠를 수 있음)
            isolation = hints.get('isolation', 'default')
            if isolation == 'READ_UNCOMMITTED':
                improvement_factor *= 0.90  # 10% 개선 (락 감소)
            elif isolation == 'SNAPSHOT':
                improvement_factor *= 1.05  # 5% 느림 (row versioning)
            
            predicted_time *= improvement_factor
            
            # Metrics 계산
            estimated_logical_reads = max(1, int(predicted_time * 10))
            estimated_cpu_time = max(0.1, predicted_time * 0.7)
            
            metrics = {
                'elapsed_time_ms': predicted_time,
                'logical_reads': estimated_logical_reads,
                'cpu_time_ms': estimated_cpu_time
            }
            
            return metrics
            
        except Exception as e:
            if self.verbose:
                print(f"[ERROR] XGB 예측 실패: {e}")
            return {
                'elapsed_time_ms': float('inf'),
                'logical_reads': 0,
                'cpu_time_ms': 0
            }
    
    def reset(self, seed=None, options=None):
        """에피소드 시작"""
        super().reset(seed=seed)
        
        # 쿼리 선택
        self.current_sql = self.query_list[self.current_query_ix]
        self.current_query_ix = (self.current_query_ix + 1) % len(self.query_list)
        
        self.current_step = 0
        self.prev_reward = 0.0
        self.prev_action_vector = None
        
        # 베이스라인 측정
        _, self.baseline_metrics = self._get_baseline_from_cache(self.current_sql)
        self.current_metrics = self.baseline_metrics.copy()
        
        # 초기 힌트 (아무것도 적용 안 함)
        self.current_hints = {
            'maxdop': 0,
            'fast_n': 0,
            'isolation': 'default',
            'join_hint': 'none',
            'optimizer_hint': 'NONE',
            'compatibility': 'COMPAT_140',
            'use_recompile': False
        }
        
        # 초기 state 생성
        state = self.state_encoder.encode_from_query_and_metrics(
            sql=self.current_sql,
            current_metrics=self.current_metrics,
            current_hints=self.current_hints,
            prev_action_id=-1,
            prev_reward=0.0
        )
        
        if self.verbose:
            query_idx = (self.current_query_ix - 1) % len(self.query_list)
            print(f"\n{'='*80}")
            print(f"Episode Start: Query {query_idx}")
            print(f"{'='*80}")
            print(f"SQL: {self.current_sql[:100]}...")
            print(f"Baseline: {self.baseline_metrics['elapsed_time_ms']:.2f} ms")
        
        info = {
            'query_idx': (self.current_query_ix - 1) % len(self.query_list),
            'baseline_time': self.baseline_metrics['elapsed_time_ms']
        }
        
        return state, info
    
    def step(self, action_vector: np.ndarray):
        """
        액션 실행
        
        Args:
            action_vector: [0~1]^7 continuous action
        
        Returns:
            observation, reward, terminated, truncated, info
        """
        self.current_step += 1
        
        # 1. Action decoding
        hints = self.action_decoder.decode(action_vector)
        
        # 2. 시뮬레이션 실행
        new_metrics = self._simulate_query_with_hints(self.current_sql, hints)
        
        # 3. Reward 계산 (PPO v3)
        reward = calculate_reward_v3_normalized(
            baseline_metrics=self.baseline_metrics,
            current_metrics=new_metrics,
            previous_metrics=self.current_metrics
        )
        
        # 4. State 업데이트
        self.current_metrics = new_metrics
        self.current_hints = hints
        
        # 5. 다음 state 생성
        next_state = self.state_encoder.encode_from_query_and_metrics(
            sql=self.current_sql,
            current_metrics=self.current_metrics,
            current_hints=self.current_hints,
            prev_action_id=-1,  # Continuous action이므로 ID 없음
            prev_reward=reward
        )
        
        # 6. Episode 종료 조건
        terminated = False
        truncated = self.current_step >= self.max_steps
        
        # 7. Info
        speedup = self.baseline_metrics['elapsed_time_ms'] / max(0.1, new_metrics['elapsed_time_ms'])
        
        info = {
            'step': self.current_step,
            'hints': hints,
            'action_description': self.action_decoder.get_action_description(action_vector),
            'baseline_time': self.baseline_metrics['elapsed_time_ms'],
            'current_time': new_metrics['elapsed_time_ms'],
            'speedup': speedup,
            'reward': reward
        }
        
        if self.verbose:
            print(f"\n--- Step {self.current_step} ---")
            print(f"Action: {info['action_description']}")
            print(f"Time: {new_metrics['elapsed_time_ms']:.2f} ms (Speedup: {speedup:.3f}x)")
            print(f"Reward: {reward:.4f}")
        
        self.prev_action_vector = action_vector
        self.prev_reward = reward
        
        return next_state, reward, terminated, truncated, info
    
    def render(self):
        """환경 렌더링 (선택사항)"""
        pass
    
    def close(self):
        """환경 종료"""
        pass


# Test code
if __name__ == '__main__':
    import sys
    import os
    
    # constants2.py에서 쿼리 로드
    sys.path.insert(0, os.path.join(apollo_ml_dir, 'RLQO'))
    from constants2 import SAMPLE_QUERIES
    
    print("=" * 80)
    print("DDPG v1 Simulation Environment Test")
    print("=" * 80)
    
    # 환경 생성
    env = QueryPlanSimEnvDDPGv1(
        query_list=SAMPLE_QUERIES,
        max_steps=5,
        verbose=True
    )
    
    print(f"\nAction space: {env.action_space}")
    print(f"Observation space: {env.observation_space}")
    
    # 1 에피소드 테스트
    obs, info = env.reset()
    print(f"\nInitial observation shape: {obs.shape}")
    print(f"Initial observation: {obs}")
    
    for step in range(3):
        # Random action
        action = env.action_space.sample()
        print(f"\nSampled action: {action}")
        
        obs, reward, terminated, truncated, info = env.step(action)
        
        if terminated or truncated:
            break
    
    print("\n" + "=" * 80)
    print("Test completed successfully!")
    print("=" * 80)

