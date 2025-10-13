# -*- coding: utf-8 -*-
"""
DQN v3: 개선된 실제 DB 환경
- 액션 호환성 체크 및 마스킹
- 베이스라인 시간 기반 Curriculum Learning
- TABLE_HINT 구현 (USE_NOLOCK)
- v3 보상 함수 적용
"""

import json
import os
import re
import gymnasium as gym
import joblib
import numpy as np
from gymnasium import spaces

import sys
import os
# 현재 스크립트의 디렉토리를 기준으로 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
apollo_ml_dir = os.path.join(current_dir, '..', '..')
rlqo_dir = os.path.join(current_dir, '..')
sys.path.append(apollo_ml_dir)
sys.path.append(rlqo_dir)

from RLQO.features.phase2_features import extract_features, XGB_EXPECTED_FEATURES
from RLQO.env.v3_reward import calculate_reward_v3
from db import connect, get_execution_plan, get_query_statistics
from config import load_config

# --- Helper Functions ---

def parse_statistics(stats_io: str, stats_time: str) -> dict:
    """SET STATISTICS IO, TIME 결과 문자열을 파싱하여 dict로 반환합니다."""
    metrics = {}
    logical_reads = sum(map(int, re.findall(r'logical reads (\d+)', stats_io)))
    metrics['logical_reads'] = logical_reads
    
    cpu_time_ms = 0.0
    elapsed_time_ms = 0.0
    
    execution_times_block = stats_time
    execution_times_match = re.search(r'SQL Server Execution Times:(.*)', stats_time, re.DOTALL)
    if execution_times_match:
        execution_times_block = execution_times_match.group(1)
    
    cpu_match = re.search(r'CPU time = (\d+\.?\d*)\s*(ms|s)', execution_times_block)
    if cpu_match:
        value = float(cpu_match.group(1))
        unit = cpu_match.group(2)
        if unit == 's':
            cpu_time_ms = value * 1000
        else:
            cpu_time_ms = value
    
    elapsed_match = re.search(r'elapsed time = (\d+\.?\d*)\s*(ms|s)', execution_times_block)
    if elapsed_match:
        value = float(elapsed_match.group(1))
        unit = elapsed_match.group(2)
        if unit == 's':
            elapsed_time_ms = value * 1000
        else:
            elapsed_time_ms = value
            
    metrics['cpu_time_ms'] = cpu_time_ms
    metrics['elapsed_time_ms'] = round(elapsed_time_ms, 4)
    return metrics

def apply_action_to_sql(sql: str, action: dict) -> str:
    """주어진 SQL에 Action(힌트/재작성)을 적용합니다."""
    action_type = action.get('type')
    action_value = action.get('value')
    
    # NO_ACTION인 경우 원본 반환
    if action_type == "BASELINE" or not action_value:
        return sql
    
    if action_type == "HINT":
        # 세미콜론이 있다면 그 앞에, 없다면 맨 뒤에 힌트 추가
        if ';' in sql:
            return sql.replace(';', f' {action_value};')
        else:
            return f"{sql} {action_value}"
    
    elif action_type == "TABLE_HINT":
        # NOLOCK 등의 테이블 힌트를 FROM 절 테이블에 추가
        # 예: "FROM dbo.table_name" -> "FROM dbo.table_name WITH (NOLOCK)"
        
        # 정규표현식으로 FROM 절의 첫 번째 테이블 찾기
        pattern = r'(FROM\s+(?:\w+\.)?\w+)(\s+\w+)?'
        
        def add_table_hint(match):
            table_part = match.group(1)  # "FROM dbo.exe_execution"
            alias_part = match.group(2) or ""  # " e" 또는 ""
            return f"{table_part} WITH ({action_value}){alias_part}"
        
        modified_sql = re.sub(pattern, add_table_hint, sql, count=1, flags=re.IGNORECASE)
        return modified_sql
    
    return sql

# --- Gym Environment ---

class QueryPlanDBEnvV3(gym.Env):
    """
    DQN v3용 실제 DB 환경
    - 액션 호환성 체크 및 마스킹
    - 베이스라인 시간 기반 Curriculum Learning
    - TABLE_HINT 구현
    - v3 보상 함수 적용
    """
    def __init__(self, 
                 query_list: list[str], 
                 max_steps=10,
                 action_space_path='Apollo.ML/artifacts/RLQO/configs/v3_action_space.json',
                 compatibility_path='Apollo.ML/artifacts/RLQO/configs/v3_query_action_compatibility.json',
                 curriculum_mode=False,
                 verbose=True):
        super().__init__()
        
        # 1. DB 연결 및 모델/설정 로드
        self.config = load_config('Apollo.ML/config.yaml')
        self.db_connection = connect(self.config.db)
        self.xgb_model = joblib.load('Apollo.ML/artifacts/model.joblib')
        
        # 2. Action Space 로드 (v3: 19개 액션)
        with open(action_space_path, 'r') as f:
            self.actions = json.load(f)
        
        # 3. 호환성 매핑 로드
        with open(compatibility_path, 'r') as f:
            self.compatibility_map = json.load(f)
        
        # 4. Curriculum Learning 설정
        self.curriculum_mode = curriculum_mode
        self.query_list_original = query_list
        self.verbose = verbose
        
        if curriculum_mode:
            # 베이스라인 시간 측정하여 난이도 순 정렬
            print("베이스라인 시간 측정 중...")
            self.query_difficulties = self._measure_query_difficulties()
            
            # 베이스라인 시간 순으로 정렬 (빠른 쿼리 → 느린 쿼리)
            sorted_queries = sorted(enumerate(query_list), 
                                  key=lambda x: self.query_difficulties[x[0]])
            self.query_list = [q for _, q in sorted_queries]
            self.original_indices = [idx for idx, _ in sorted_queries]
            
            print(f"Curriculum Learning 활성화: {len(self.query_list)}개 쿼리")
            print("난이도 순 (빠른 → 느린):")
            for i, (orig_idx, difficulty) in enumerate(zip(self.original_indices, 
                                                          [self.query_difficulties[idx] for idx in self.original_indices])):
                print(f"  {i}: 쿼리 {orig_idx} ({difficulty:.1f}ms)")
        else:
            self.query_list = query_list
            self.original_indices = list(range(len(query_list)))
        
        # 5. 에피소드 변수
        self.current_query_ix = 0
        self.current_sql = ""
        self.max_steps = max_steps
        self.current_step = 0
        self.baseline_metrics = {}
        self.current_obs = None
        self.current_metrics = {}
        self.verbose = verbose
        
        # 6. Gym 인터페이스 정의
        self.action_space = spaces.Discrete(len(self.actions))
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(XGB_EXPECTED_FEATURES,), dtype=np.float32
        )

    def _measure_query_difficulties(self) -> dict:
        """모든 쿼리의 베이스라인 시간을 측정합니다."""
        difficulties = {}
        
        for i, sql in enumerate(self.query_list_original):
            try:
                obs, metrics = self._get_obs_from_db(sql)
                baseline_time = metrics.get('elapsed_time_ms', 1000)  # 기본값 1000ms
                difficulties[i] = baseline_time
                
                if self.verbose:
                    print(f"  쿼리 {i}: {baseline_time:.1f}ms")
                    
            except Exception as e:
                print(f"  쿼리 {i} 베이스라인 측정 실패: {e}")
                difficulties[i] = 1000  # 기본값
        
        return difficulties

    def _get_obs_from_db(self, sql: str) -> tuple[np.ndarray, dict]:
        """SQL을 실행하고 DB에서 관측값(State)과 통계(Metrics)를 가져옵니다."""
        try:
            plan_xml = get_execution_plan(self.db_connection, sql)
            stats_io, stats_time = get_query_statistics(self.db_connection, sql)
            
            if not plan_xml:
                if self.verbose:
                    print(f"[WARN] Failed to get execution plan for SQL: {sql[:100]}...")
                metrics = parse_statistics(stats_io, stats_time)
                return None, metrics
            
            metrics = parse_statistics(stats_io, stats_time)
            observation = extract_features(plan_xml, metrics)
            
            return observation, metrics
            
        except Exception as e:
            if self.verbose:
                print(f"[ERROR] DB execution failed: {e}")
                print(f"[ERROR] SQL: {sql[:200]}...")
            
            # 기본값 반환
            metrics = {
                'elapsed_time_ms': 1000.0,
                'logical_reads': 1000,
                'cpu_time_ms': 1000.0
            }
            observation = np.zeros(79, dtype=np.float32)
            return observation, metrics

    def get_action_mask(self) -> np.ndarray:
        """현재 쿼리에 호환되는 액션 마스크를 반환합니다."""
        current_query_idx = self.original_indices[self.current_query_ix]
        compatible_actions = self.compatibility_map[str(current_query_idx)]
        
        mask = np.zeros(len(self.actions), dtype=np.float32)
        for i, action in enumerate(self.actions):
            if action['name'] in compatible_actions:
                mask[i] = 1.0
        
        return mask

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # 다음 쿼리 선택
        self.current_sql = self.query_list[self.current_query_ix]
        self.current_query_ix = (self.current_query_ix + 1) % len(self.query_list)
        
        self.current_step = 0
        
        if self.verbose:
            current_query_idx = self.original_indices[self.current_query_ix - 1]
            print(f"\n----- New Episode: Optimizing Query {current_query_idx} -----")
            print(f"Original SQL: {self.current_sql[:150]}...")
        
        # 베이스라인 측정
        obs, metrics = self._get_obs_from_db(self.current_sql)
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
        
        # 3. SQL 수정
        modified_sql = apply_action_to_sql(self.current_sql, action)
        
        # 4. 실행 및 메트릭 수집
        metrics_before = self.current_metrics.copy()
        next_obs, metrics_after = self._get_obs_from_db(modified_sql)
        
        if next_obs is None:
            # 실행 실패 시
            reward = -10.0
            terminated = True
            self.current_obs = np.zeros(XGB_EXPECTED_FEATURES, dtype=np.float32)
            self.current_metrics = metrics_after
        else:
            # 5. 보상 계산 (v3: invalid_action=False)
            reward = calculate_reward_v3(
                metrics_before=metrics_before,
                metrics_after=metrics_after,
                baseline_metrics=self.baseline_metrics,
                step_num=self.current_step,
                max_steps=self.max_steps,
                action_safety_score=safety_score,
                invalid_action=False
            )
            
            # 6. 상태 업데이트
            self.current_obs = next_obs
            self.current_metrics = metrics_after
            
            terminated = False
        
        # 7. 종료 조건
        truncated = (self.current_step >= self.max_steps)
        
        if self.verbose:
            print(f"  - Executed SQL ({metrics_after.get('elapsed_time_ms', 0)} ms): {modified_sql[:100]}...")
        
        info = {
            "action": action_name,
            "metrics": metrics_after,
            "baseline_metrics": self.baseline_metrics,
            "safety_score": safety_score,
            "invalid_action": False
        }
        
        return self.current_obs, reward, terminated, truncated, info

    def close(self):
        if self.db_connection:
            self.db_connection.close()


if __name__ == '__main__':
    print("=== DQN v3 DB Environment 테스트 ===\n")
    
    import sys
    import os
    sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML'))
    
    from RLQO.constants import SAMPLE_QUERIES
    
    # 환경 생성
    env = QueryPlanDBEnvV3(
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
    print(f"Observation shape: {obs.shape if obs is not None else 'None'}")
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
    print("\n[SUCCESS] 테스트 완료!")
