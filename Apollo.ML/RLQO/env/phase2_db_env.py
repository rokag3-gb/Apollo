import json
import os
import re
import gymnasium as gym
import joblib
import numpy as np
from gymnasium import spaces

from RLQO.features.phase2_features import extract_features, XGB_EXPECTED_FEATURES
from RLQO.env.phase1_reward import calculate_reward
from db import connect, execute_query
from config import AppConfig

# --- Helper Functions ---

def parse_statistics(stats_io: str, stats_time: str) -> dict:
    """SET STATISTICS IO, TIME 결과 문자열을 파싱하여 dict로 반환합니다."""
    metrics = {}
    # IO 파싱 (예: Table 'Worktable'. Scan count 0, logical reads 0, physical reads 0)
    logical_reads = sum(map(int, re.findall(r'logical reads (\d+)', stats_io)))
    metrics['logical_reads'] = logical_reads
    
    # TIME 파싱 (예: SQL Server Execution Times: CPU time = 0 ms,  elapsed time = 0 ms.)
    cpu_time = sum(map(int, re.findall(r'CPU time = (\d+) ms', stats_time)))
    elapsed_time = sum(map(int, re.findall(r'elapsed time = (\d+) ms', stats_time)))
    metrics['cpu_time_ms'] = cpu_time
    metrics['elapsed_time_ms'] = elapsed_time
    return metrics

def apply_action_to_sql(sql: str, action: dict) -> str:
    """주어진 SQL에 Action(힌트/재작성)을 적용합니다."""
    action_type = action.get('type')
    action_value = action.get('value')
    
    if action_type == "HINT":
        # 세미콜론이 있다면 그 앞에, 없다면 맨 뒤에 힌트 추가
        if ';' in sql:
            return sql.replace(';', f' {action_value};')
        else:
            return f"{sql} {action_value}"
    
    elif action_type == "TABLE_HINT":
        target_table = action.get('target_table')
        if target_table:
            # ex: "Users WITH (INDEX...)" or "Users WITH (NOLOCK)"
            if 'WITH' in action_value:
                 # Users -> Users WITH (NOLOCK)
                return sql.replace(target_table, action_value)
            else:
                # Users -> Users WITH (NOLOCK)
                return sql.replace(target_table, f"{target_table} {action_value}")

    elif action_type == "REWRITE":
         # 예: "SELECT *" -> "SELECT user_id, ..."
        if 'SELECT *' in sql.upper():
             return sql.upper().replace('SELECT *', f'SELECT {action_value}')

    return sql # 적용할 수 없는 경우 원본 반환

# --- Gym Environment ---

class QueryPlanDBEnv(gym.Env):
    """
    실제 DB(샌드박스)와 연동하여 쿼리 계획을 최적화하는 세미-온라인 환경.
    """
    def __init__(self, query_list: list[str], max_steps=10):
        super().__init__()
        
        # 1. DB 연결 및 모델/설정 로드
        self.config = AppConfig.load()
        self.db_connection = connect(self.config.db)
        self.xgb_model = joblib.load('Apollo.ML/artifacts/model.joblib')
        
        with open('Apollo.ML/artifacts/RLQO/configs/phase2_action_space.json', 'r') as f:
            self.actions = json.load(f)
        
        # 2. 쿼리 목록 및 에피소드 변수
        self.query_list = query_list
        self.current_query_ix = 0
        self.current_sql = ""
        self.max_steps = max_steps
        self.current_step = 0
        
        # 3. Gym 인터페이스 정의
        self.action_space = spaces.Discrete(len(self.actions))
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(XGB_EXPECTED_FEATURES,), dtype=np.float32
        )

    def _get_obs_from_db(self, sql: str) -> tuple[np.ndarray, dict]:
        """SQL을 실행하고 DB에서 관측값(State)과 통계(Metrics)를 가져옵니다."""
        plan_xml, stats_io, stats_time = execute_query(self.db_connection, sql)
        if not plan_xml: # 쿼리 실행 실패 시
            return None, {}
        
        metrics = parse_statistics(stats_io, stats_time)
        
        # phase2_features.py의 함수를 사용하여 XML에서 피처 추출
        # (주의: 이 함수는 XML을 입력으로 받도록 수정 필요)
        observation = extract_features(plan_xml, metrics) 
        
        return observation, metrics

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # 다음 쿼리를 선택하여 에피소드 시작
        self.current_sql = self.query_list[self.current_query_ix]
        self.current_query_ix = (self.current_query_ix + 1) % len(self.query_list)
        
        self.current_step = 0
        
        # 베이스라인 (힌트 없는) 상태/비용 측정
        obs, metrics = self._get_obs_from_db(self.current_sql)
        if obs is None: # 쿼리 실행 실패 시, 다시 리셋
            return self.reset(seed=seed)

        self.baseline_cost = self.xgb_model.predict(obs.reshape(1, -1))[0]
        self.current_obs = obs

        return self.current_obs, {"metrics": metrics}

    def step(self, action_id):
        self.current_step += 1
        
        # 1. Action을 현재 SQL에 적용
        action = self.actions[action_id]
        modified_sql = apply_action_to_sql(self.current_sql, action)
        
        # 2. 수정된 SQL 실행 및 결과 관측
        next_obs, metrics = self._get_obs_from_db(modified_sql)
        
        done = False
        reward = 0
        
        if next_obs is None: # 쿼리 실행 실패 (예: 잘못된 힌트)
            reward = -10.0 # 큰 페널티
            next_obs = self.current_obs # 상태는 그대로 유지
            done = True # 에피소드 종료
        else:
            # 3. 보상 계산 (XGBoost 모델 사용)
            cost_before = self.xgb_model.predict(self.current_obs.reshape(1, -1))[0]
            cost_after = self.xgb_model.predict(next_obs.reshape(1, -1))[0]
            reward = calculate_reward(cost_before, cost_after)
            self.current_obs = next_obs

        # 4. 종료 조건 확인
        terminated = done
        truncated = self.current_step >= self.max_steps
        
        info = {"metrics": metrics, "action_name": action['name'], "modified_sql": modified_sql}
        
        return self.current_obs, reward, terminated, truncated, info

    def close(self):
        self.db_connection.close()
