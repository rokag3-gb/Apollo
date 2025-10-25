# -*- coding: utf-8 -*-
"""
DDPG v1: RealDB Environment with Continuous Action Space

실제 SQL Server에 연결하여 쿼리를 실행하고 성능을 측정합니다.
"""

import os
import sys
import time
import re
import numpy as np
from gymnasium import spaces

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)

# Imports
import gymnasium as gym

from RLQO.DDPG_v1.config.action_decoder import ContinuousActionDecoder
from RLQO.PPO_v3.env.v3_actionable_state import ActionableStateEncoderV3
from RLQO.PPO_v3.env.v3_normalized_reward import calculate_reward_v3_normalized
from config import load_config
from db import connect, get_query_statistics


class QueryPlanRealDBEnvDDPGv1(gym.Env):
    """
    DDPG v1 RealDB Environment
    
    특징:
    - Continuous action space (7차원)
    - 18차원 actionable state
    - 실제 SQL Server 실행
    - Log scale normalized reward
    """
    
    @staticmethod
    def _convert_hints_for_state_encoder(hints: dict) -> dict:
        """
        DDPG v1의 hints를 PPO v3 state encoder가 기대하는 형식으로 변환
        
        Args:
            hints: action_decoder.decode()의 출력
        
        Returns:
            converted_hints: state encoder 호환 형식
        """
        # ISOLATION 문자열 → 숫자 변환
        isolation_map = {
            'default': 0,
            'READ_COMMITTED': 1,
            'READ_UNCOMMITTED': 2,
            'SNAPSHOT': 3
        }
        isolation_str = hints.get('isolation', 'default')
        isolation_num = isolation_map.get(isolation_str, 0)
        
        # OPTIMIZER_HINT 카운트 (간단히 NONE이 아니면 1)
        optimizer_hint = hints.get('optimizer_hint', 'NONE')
        advanced_hints = 0 if optimizer_hint == 'NONE' else 1
        
        return {
            'maxdop': hints.get('maxdop', 0),
            'fast_n': hints.get('fast_n', 0),
            'isolation': isolation_num,  # 숫자로 변환
            'join_hint': hints.get('join_hint', 'none'),
            'advanced_hints': advanced_hints  # 숫자로 변환
        }
    
    def __init__(self,
                 query_list: list,
                 max_steps: int = 10,
                 timeout_seconds: int = 30,
                 verbose: bool = True):
        """
        Args:
            query_list: 30개 쿼리 리스트
            max_steps: 에피소드당 최대 스텝
            timeout_seconds: 쿼리 타임아웃
            verbose: 로그 출력
        """
        super().__init__()
        
        self.query_list = query_list
        self.max_steps = max_steps
        self.timeout_seconds = timeout_seconds
        self.verbose = verbose
        
        # Action decoder
        self.action_decoder = ContinuousActionDecoder()
        
        # State encoder
        self.state_encoder = ActionableStateEncoderV3()
        
        # DB 연결 (DQN v3 방식 사용)
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        apollo_ml_dir_abs = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..'))
        config_path = os.path.join(apollo_ml_dir_abs, 'config.yaml')
        
        self.config = load_config(config_path)
        self.conn = connect(self.config.db, max_retries=3, retry_delay=5)
        
        # Gym spaces
        self.action_space = spaces.Box(
            low=0.0, 
            high=1.0, 
            shape=(7,), 
            dtype=np.float32
        )
        
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
            print(f"[INFO] DDPG v1 RealDB Environment initialized")
            print(f"  - Queries: {len(query_list)}")
            print(f"  - Action space: Continuous (7 dims)")
            print(f"  - Observation space: 18 dims")
            print(f"  - DB: {self.config.db.server}/{self.config.db.database}")
    
    def _apply_hints_to_sql(self, sql: str, hints: dict) -> str:
        """
        SQL에 힌트를 적용합니다.
        
        Args:
            sql: 원본 SQL
            hints: 적용할 힌트들
        
        Returns:
            modified_sql: 힌트가 적용된 SQL
        """
        sql = sql.strip()
        
        # SET 옵션들
        set_options = []
        
        # MAXDOP
        maxdop = hints.get('maxdop', 0)
        if maxdop > 0:
            set_options.append(f"SET MAXDOP {maxdop};")
        
        # ISOLATION LEVEL
        isolation = hints.get('isolation', 'default')
        if isolation == 'READ_UNCOMMITTED':
            set_options.append("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
        elif isolation == 'READ_COMMITTED':
            set_options.append("SET TRANSACTION ISOLATION LEVEL READ COMMITTED;")
        elif isolation == 'SNAPSHOT':
            set_options.append("SET TRANSACTION ISOLATION LEVEL SNAPSHOT;")
        
        # Query 힌트들
        query_hints = []
        
        # FAST
        fast_n = hints.get('fast_n', 0)
        if fast_n > 0:
            query_hints.append(f"FAST {fast_n}")
        
        # JOIN hint
        join_hint = hints.get('join_hint', 'none')
        if join_hint == 'hash':
            query_hints.append("HASH JOIN")
        elif join_hint == 'merge':
            query_hints.append("MERGE JOIN")
        elif join_hint == 'loop':
            query_hints.append("LOOP JOIN")
        elif join_hint == 'force_order':
            query_hints.append("FORCE ORDER")
        
        # Optimizer hint
        opt_hint = hints.get('optimizer_hint', 'NONE')
        if opt_hint != 'NONE':
            query_hints.append(opt_hint)
        
        # RECOMPILE
        if hints.get('use_recompile', False):
            query_hints.append("RECOMPILE")
        
        # COMPATIBILITY (OPTION 절에 추가하지 않고 SET으로 처리)
        compat = hints.get('compatibility', 'COMPAT_140')
        compat_level = int(compat.replace('COMPAT_', ''))
        set_options.append(f"ALTER DATABASE CURRENT SET COMPATIBILITY_LEVEL = {compat_level};")
        
        # SQL 수정
        modified_sql = ""
        
        # SET 옵션 추가
        if set_options:
            modified_sql = "\n".join(set_options) + "\n"
        
        # Query 힌트 추가
        if query_hints:
            # OPTION 절이 이미 있는지 확인
            if re.search(r'\bOPTION\s*\(', sql, re.IGNORECASE):
                # 기존 OPTION 절에 추가
                sql = re.sub(
                    r'\bOPTION\s*\(',
                    f"OPTION ({', '.join(query_hints)}, ",
                    sql,
                    flags=re.IGNORECASE
                )
            else:
                # 새로운 OPTION 절 추가
                # 세미콜론 제거
                sql = sql.rstrip(';')
                sql += f"\nOPTION ({', '.join(query_hints)});"
        
        modified_sql += sql
        
        return modified_sql
    
    def _execute_query(self, sql: str) -> dict:
        """
        쿼리 실행 및 성능 측정 (db.py의 get_query_statistics 사용)
        
        Returns:
            metrics: {'elapsed_time_ms', 'logical_reads', 'cpu_time_ms'}
        """
        try:
            # db.py의 get_query_statistics 사용 (DQN v3 방식)
            stats_io, stats_time = get_query_statistics(self.conn, sql)
            
            # Parse statistics
            elapsed_time_ms = 0.0
            logical_reads = 0
            cpu_time_ms = 0.0
            
            # Parse TIME statistics
            if stats_time:
                import re
                # SQL Server execution time: ... CPU time = X ms, elapsed time = Y ms
                time_match = re.search(r'CPU time = (\d+) ms.*?elapsed time = (\d+) ms', stats_time)
                if time_match:
                    cpu_time_ms = float(time_match.group(1))
                    elapsed_time_ms = float(time_match.group(2))
            
            # Parse IO statistics
            if stats_io:
                import re
                # Table 'XXX'. Scan count X, logical reads X, physical reads X
                reads_match = re.search(r'logical reads (\d+)', stats_io)
                if reads_match:
                    logical_reads = int(reads_match.group(1))
            
            # 기본값 설정 (파싱 실패 시)
            if elapsed_time_ms == 0:
                elapsed_time_ms = 100.0
            if logical_reads == 0:
                logical_reads = max(1, int(elapsed_time_ms * 10))
            if cpu_time_ms == 0:
                cpu_time_ms = max(0.1, elapsed_time_ms * 0.7)
            
            metrics = {
                'elapsed_time_ms': elapsed_time_ms,
                'logical_reads': logical_reads,
                'cpu_time_ms': cpu_time_ms
            }
            
            return metrics
            
        except Exception as e:
            if self.verbose:
                print(f"[ERROR] 쿼리 실행 실패: {e}")
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
        
        # 베이스라인 측정 (힌트 없이)
        self.baseline_metrics = self._execute_query(self.current_sql)
        self.current_metrics = self.baseline_metrics.copy()
        
        # 초기 힌트
        self.current_hints = {
            'maxdop': 0,
            'fast_n': 0,
            'isolation': 'default',
            'join_hint': 'none',
            'optimizer_hint': 'NONE',
            'compatibility': 'COMPAT_140',
            'use_recompile': False
        }
        
        # 초기 state (hints를 state encoder 형식으로 변환)
        state_encoder_hints = self._convert_hints_for_state_encoder(self.current_hints)
        state = self.state_encoder.encode_from_query_and_metrics(
            sql=self.current_sql,
            current_metrics=self.current_metrics,
            current_hints=state_encoder_hints,
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
        """액션 실행"""
        self.current_step += 1
        
        # 1. Action decoding
        hints = self.action_decoder.decode(action_vector)
        
        # 2. SQL 수정 및 실행
        modified_sql = self._apply_hints_to_sql(self.current_sql, hints)
        new_metrics = self._execute_query(modified_sql)
        
        # 3. Reward 계산 (PPO v3 - 파라미터 이름 맞춤)
        reward = calculate_reward_v3_normalized(
            metrics_before=self.current_metrics,
            metrics_after=new_metrics,
            baseline_metrics=self.baseline_metrics,
            query_type='SIMPLE',  # DDPG는 query type 구분 안 함
            action_id=-1  # Continuous action이므로 -1
        )
        
        # 4. State 업데이트
        self.current_metrics = new_metrics
        self.current_hints = hints
        
        # 5. 다음 state (hints를 state encoder 형식으로 변환)
        state_encoder_hints = self._convert_hints_for_state_encoder(hints)
        next_state = self.state_encoder.encode_from_query_and_metrics(
            sql=self.current_sql,
            current_metrics=self.current_metrics,
            current_hints=state_encoder_hints,
            prev_action_id=-1,
            prev_reward=reward
        )
        
        # 6. Episode 종료
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
        """렌더링"""
        pass
    
    def close(self):
        """환경 종료"""
        if self.conn:
            self.conn.close()
            if self.verbose:
                print("[INFO] DB 연결 종료")

