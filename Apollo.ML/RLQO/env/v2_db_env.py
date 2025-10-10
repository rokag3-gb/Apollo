# -*- coding: utf-8 -*-
"""
DQN v2: 개선된 실제 DB 환경
- 확장된 Action Space (15개 액션)
- 안전성 점수 기반 보상
- Curriculum Learning 지원
"""

import json
import os
import re
import gymnasium as gym
import joblib
import numpy as np
from gymnasium import spaces

from RLQO.features.phase2_features import extract_features, XGB_EXPECTED_FEATURES
from RLQO.env.v2_reward import calculate_reward_v2
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
        # NOLOCK 등의 테이블 힌트
        # 실제 테이블 이름을 찾아서 WITH (NOLOCK) 추가
        # 간단한 구현: FROM 절의 첫 테이블에만 적용
        pass  # 복잡하므로 생략
    
    return sql

# --- Gym Environment ---

class QueryPlanDBEnvV2(gym.Env):
    """
    DQN v2용 실제 DB 환경
    - 확장된 Action Space (15개)
    - 안전성 점수 기반 보상
    - Curriculum Learning 지원
    """
    def __init__(self, 
                 query_list: list[str], 
                 max_steps=10,
                 action_space_path='Apollo.ML/artifacts/RLQO/configs/v2_action_space.json',
                 curriculum_mode=False,
                 verbose=True):
        super().__init__()
        
        # 1. DB 연결 및 모델/설정 로드
        self.config = load_config('Apollo.ML/config.yaml')
        self.db_connection = connect(self.config.db)
        self.xgb_model = joblib.load('Apollo.ML/artifacts/model.joblib')
        
        # 2. Action Space 로드 (v2: 15개 액션)
        with open(action_space_path, 'r') as f:
            self.actions = json.load(f)
        
        # 3. Curriculum Learning 설정
        self.curriculum_mode = curriculum_mode
        self.query_list_original = query_list
        
        if curriculum_mode:
            # 쿼리를 난이도별로 정렬 (간단한 구현: 쿼리 길이로 추정)
            sorted_queries = sorted(enumerate(query_list), key=lambda x: len(x[1]))
            self.query_list = [q for _, q in sorted_queries]
            self.curriculum_stage = 0  # 0: 쉬운 쿼리, 1: 중간, 2: 어려운 쿼리
        else:
            self.query_list = query_list
        
        # 4. 에피소드 변수
        self.current_query_ix = 0
        self.current_sql = ""
        self.max_steps = max_steps
        self.current_step = 0
        self.baseline_metrics = {}
        self.current_obs = None
        self.current_metrics = {}
        self.verbose = verbose
        
        # 5. Gym 인터페이스 정의
        self.action_space = spaces.Discrete(len(self.actions))
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(XGB_EXPECTED_FEATURES,), dtype=np.float32
        )

    def _get_obs_from_db(self, sql: str) -> tuple[np.ndarray, dict]:
        """SQL을 실행하고 DB에서 관측값(State)과 통계(Metrics)를 가져옵니다."""
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

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # 다음 쿼리 선택
        self.current_sql = self.query_list[self.current_query_ix]
        self.current_query_ix = (self.current_query_ix + 1) % len(self.query_list)
        
        self.current_step = 0
        
        if self.verbose:
            print(f"\n----- New Episode: Optimizing Query {self.current_query_ix}/{len(self.query_list)} -----")
            print(f"Original SQL: {self.current_sql[:150]}...")
        
        # 베이스라인 측정
        self.current_obs, self.baseline_metrics = self._get_obs_from_db(self.current_sql)
        
        if self.current_obs is None:
            # 실패 시 더미 관측값 반환
            self.current_obs = np.zeros(XGB_EXPECTED_FEATURES, dtype=np.float32)
        
        self.current_metrics = self.baseline_metrics.copy()
        
        if self.verbose:
            print(f"  - Baseline Execution Time: {self.baseline_metrics.get('elapsed_time_ms', 0)} ms")
        
        return self.current_obs, {"metrics": self.baseline_metrics}

    def step(self, action_id):
        self.current_step += 1
        
        # 1. Action 적용
        action = self.actions[action_id]
        action_name = action['name']
        safety_score = action.get('safety_score', 1.0)
        
        # 2. SQL 수정
        modified_sql = apply_action_to_sql(self.current_sql, action)
        
        # 3. 실행 및 메트릭 수집
        metrics_before = self.current_metrics.copy()
        next_obs, metrics_after = self._get_obs_from_db(modified_sql)
        
        if next_obs is None:
            # 실행 실패 시
            reward = -10.0
            terminated = True
            self.current_obs = np.zeros(XGB_EXPECTED_FEATURES, dtype=np.float32)
            self.current_metrics = metrics_after
        else:
            # 4. 보상 계산 (v2: 안전성 점수 포함)
            reward = calculate_reward_v2(
                metrics_before=metrics_before,
                metrics_after=metrics_after,
                baseline_metrics=self.baseline_metrics,
                step_num=self.current_step,
                max_steps=self.max_steps,
                action_safety_score=safety_score
            )
            
            # 5. 상태 업데이트
            self.current_obs = next_obs
            self.current_metrics = metrics_after
            
            terminated = False
        
        # 6. 종료 조건
        truncated = (self.current_step >= self.max_steps)
        
        if self.verbose:
            print(f"  - Executed SQL ({metrics_after.get('elapsed_time_ms', 0)} ms): {modified_sql[:100]}...")
        
        info = {
            "action": action_name,
            "metrics": metrics_after,
            "baseline_metrics": self.baseline_metrics,
            "safety_score": safety_score
        }
        
        return self.current_obs, reward, terminated, truncated, info

    def close(self):
        if self.db_connection:
            self.db_connection.close()

