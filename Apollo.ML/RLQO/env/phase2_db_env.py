import json
import os
import re
import gymnasium as gym
import joblib
import numpy as np
from gymnasium import spaces

from RLQO.features.phase2_features import extract_features, XGB_EXPECTED_FEATURES
from RLQO.env.phase1_reward import calculate_reward
from db import connect, get_execution_plan, get_query_statistics
from config import AppConfig, load_config

# --- Helper Functions ---

def parse_statistics(stats_io: str, stats_time: str) -> dict:
    """SET STATISTICS IO, TIME 결과 문자열을 파싱하여 dict로 반환합니다."""
    metrics = {}
    # IO 파싱 (예: Table 'Worktable'. Scan count 0, logical reads 0, physical reads 0)
    logical_reads = sum(map(int, re.findall(r'logical reads (\d+)', stats_io)))
    metrics['logical_reads'] = logical_reads
    
    # TIME 파싱 (예: SQL Server Execution Times: CPU time = 0.123 ms,  elapsed time = 1.456 ms.)
    # [MOD] "SQL Server Execution Times:" 블록을 명시적으로 찾아 파싱하여
    # "parse and compile time"과의 혼동을 방지합니다.
    cpu_time_ms = 0.0
    elapsed_time_ms = 0.0

    # 'Execution Times' 블록을 먼저 찾습니다.
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
    metrics['elapsed_time_ms'] = round(elapsed_time_ms, 4) # 소수점 4자리까지 반올림
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
        self.config = load_config('Apollo.ML/config.yaml')
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
        self.baseline_metrics = {} # [NEW] 베이스라인 메트릭 저장
        
        # 3. Gym 인터페이스 정의
        self.action_space = spaces.Discrete(len(self.actions))
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(XGB_EXPECTED_FEATURES,), dtype=np.float32
        )

    def _get_obs_from_db(self, sql: str) -> tuple[np.ndarray, dict]:
        """SQL을 실행하고 DB에서 관측값(State)과 통계(Metrics)를 가져옵니다."""
        # [MOD] 실행 계획과 통계 수집을 분리된 함수로 호출
        plan_xml = get_execution_plan(self.db_connection, sql)
        stats_io, stats_time = get_query_statistics(self.db_connection, sql)
        
        if not plan_xml: # 쿼리 실행 실패 시
            print(f"Warning: Failed to get execution plan for SQL: {sql[:150]}...")
            # plan_xml이 없으면 다음 단계에서 에러가 나므로, 여기서 중단.
            # 하지만 통계는 유효할 수 있으므로, 통계만이라도 반환 (reward 계산 등에 사용될 수 있음)
            metrics = parse_statistics(stats_io, stats_time)
            return None, metrics
        
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
        print(f"\n----- New Episode: Optimizing Query {self.current_query_ix}/{len(self.query_list)} -----")
        print(f"Original SQL: {self.current_sql[:150]}...")
        obs, metrics = self._get_obs_from_db(self.current_sql)

        # 베이스라인 쿼리 실행 시간 로깅
        elapsed_time = metrics.get('elapsed_time_ms', 'N/A')
        print(f"  - Baseline Execution Time: {elapsed_time} ms")
        
        if obs is None: # 쿼리 실행 실패 시, 다시 리셋
            # return self.reset(seed=seed) # BUG: This causes infinite recursion
            raise RuntimeError(
                f"Failed to get initial observation from the database for query: {self.current_sql}. "
                "The query might be invalid or the table may not exist. Please check the DB and the query."
            )

        self.baseline_metrics = metrics # [NEW]
        self.current_metrics = metrics # [NEW]
        self.current_obs = obs

        return self.current_obs, {"metrics": metrics}

    def step(self, action_id):
        self.current_step += 1
        
        # 1. Action을 현재 SQL에 적용
        action = self.actions[action_id]
        modified_sql = apply_action_to_sql(self.current_sql, action)
        
        # 2. 수정된 SQL 실행 및 결과 관측
        next_obs, metrics = self._get_obs_from_db(modified_sql)
        
        # [NEW] 실행된 쿼리와 시간 로깅
        elapsed_time = metrics.get('elapsed_time_ms', 'N/A')
        print(f"  - Executed SQL ({elapsed_time} ms): {modified_sql[:150]}...")

        done = False
        reward = 0
        
        if next_obs is None: # 쿼리 실행 실패 (예: 잘못된 힌트)
            reward = -100.0 # 큰 페널티 (기존 -10.0)
            next_obs = self.current_obs # 상태는 그대로 유지
            done = True # 에피소드 종료
        else:
            # 3. 보상 계산 (실제 실행 시간 및 IO 기반)
            reward = calculate_reward(self.current_metrics, metrics)
            self.current_obs = next_obs
            self.current_metrics = metrics # [NEW] 다음 스텝을 위해 현재 메트릭 업데이트

        # 4. 종료 조건 확인
        terminated = done
        truncated = self.current_step >= self.max_steps
        
        info = {"metrics": metrics, "action_name": action['name'], "modified_sql": modified_sql}
        
        return self.current_obs, reward, terminated, truncated, info

    def close(self):
        self.db_connection.close()
