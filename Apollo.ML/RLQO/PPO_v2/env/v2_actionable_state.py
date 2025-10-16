# -*- coding: utf-8 -*-
"""
Actionable State Encoder

행동 영향 반영형 State: 79차원 XGB features → 18차원 actionable features로 축소

핵심 철학: "행동으로 조정 가능한 지표만" 포함
"""

import numpy as np
import re
import sys
import os

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, apollo_ml_dir)

from RLQO.PPO_v1.utils.query_classifier import classify_query


class ActionableStateEncoder:
    """
    행동 영향 반영형 State Encoder
    
    State 구성 (18차원):
    [0-3]   Query 구조 (4): join_count, table_count, has_subquery, has_window
    [4-8]   현재 힌트 (5): maxdop, join_hint, isolation, recompile, optimize_for_unknown
    [9-11]  리소스 (3): log(time), log(io), log(cpu)
    [12-15] Query 타입 (4): is_cte, is_join_heavy, is_top, is_simple
    [16-17] 이력 (2): prev_action, prev_reward
    """
    
    def __init__(self):
        self.state_dim = 18
    
    def encode_from_query_and_metrics(
        self,
        sql: str,
        current_metrics: dict,
        current_hints: dict,
        prev_action_id: int = -1,
        prev_reward: float = 0.0
    ) -> np.ndarray:
        """
        SQL과 현재 메트릭에서 18차원 state 생성
        
        Args:
            sql: SQL 쿼리 문자열
            current_metrics: {'elapsed_time_ms', 'logical_reads', 'cpu_time_ms'}
            current_hints: {'maxdop', 'join_hint', 'isolation_hint', 'recompile', 'optimize_for_unknown'}
            prev_action_id: 이전 액션 ID (-1 ~ 18)
            prev_reward: 이전 보상 값
        
        Returns:
            state: (18,) numpy array, normalized [0, 1]
        """
        state = []
        
        # === 1. Query 구조 (4차원) - 행동 영향 반영 ===
        sql_upper = sql.upper()
        
        # JOIN 수 (JOIN 힌트가 영향)
        join_count = len(re.findall(r'\bJOIN\b', sql_upper))
        state.append(min(join_count / 5.0, 1.0))  # 정규화 [0, 1], 5개 이상은 1.0
        
        # 테이블 수
        from_count = len(re.findall(r'\bFROM\s+\w+', sql_upper))
        table_count = from_count + join_count
        state.append(min(table_count / 6.0, 1.0))  # 6개 이상은 1.0
        
        # 서브쿼리 존재 여부
        has_subquery = 1.0 if re.search(r'\(\s*SELECT\b', sql_upper) else 0.0
        state.append(has_subquery)
        
        # 윈도우 함수 존재 여부 (OVER 절)
        has_window = 1.0 if re.search(r'\bOVER\s*\(', sql_upper) else 0.0
        state.append(has_window)
        
        # === 2. 현재 힌트 상태 (5차원) - 행동의 직접 결과 ===
        # MAXDOP (0-8 → 0.0-1.0)
        maxdop = current_hints.get('maxdop', 0)
        state.append(maxdop / 8.0)
        
        # JOIN 힌트 (0=none, 1=hash, 2=merge, 3=loop, 4=force_order)
        join_hint_map = {'none': 0, 'hash': 1, 'merge': 2, 'loop': 3, 'force_order': 4}
        join_hint = current_hints.get('join_hint', 'none')
        state.append(join_hint_map.get(join_hint, 0) / 4.0)
        
        # Isolation/Lock 힌트
        isolation_hint = 1.0 if current_hints.get('isolation_hint', False) else 0.0
        state.append(isolation_hint)
        
        # RECOMPILE 힌트
        has_recompile = 1.0 if current_hints.get('recompile', False) else 0.0
        state.append(has_recompile)
        
        # OPTIMIZE FOR UNKNOWN 힌트
        has_opt_unknown = 1.0 if current_hints.get('optimize_for_unknown', False) else 0.0
        state.append(has_opt_unknown)
        
        # === 3. 리소스 지표 (3차원) - 행동으로 변화, log scale 정규화 ===
        # Log scale: variance 감소 + gradient 안정화
        elapsed_time = current_metrics.get('elapsed_time_ms', 1.0)
        state.append(np.log1p(elapsed_time) / 10.0)  # log(1+x) / 10
        
        logical_reads = current_metrics.get('logical_reads', 1)
        state.append(np.log1p(logical_reads) / 15.0)  # log(1+x) / 15
        
        cpu_time = current_metrics.get('cpu_time_ms', 1.0)
        state.append(np.log1p(cpu_time) / 10.0)
        
        # === 4. Query 타입 (4차원) - 원-핫 인코딩 ===
        query_type = classify_query(sql)
        type_map = {'CTE': 0, 'JOIN_HEAVY': 1, 'TOP': 2, 'SIMPLE': 3}
        type_onehot = np.zeros(4)
        type_onehot[type_map[query_type]] = 1.0
        state.extend(type_onehot)
        
        # === 5. 변동 이력 (2차원) ===
        # 이전 액션 정규화 (-1 ~ 18 → 0.0 ~ 1.0)
        prev_action_norm = (prev_action_id + 1) / 19.0
        state.append(prev_action_norm)
        
        # 이전 보상 클리핑 및 정규화 ([-1, +1] → [0, 1])
        prev_reward_clip = np.clip(prev_reward, -1.0, 1.0)
        prev_reward_norm = (prev_reward_clip + 1.0) / 2.0  # [-1, 1] → [0, 1]
        state.append(prev_reward_norm)
        
        return np.array(state, dtype=np.float32)
    
    def extract_hints_from_sql(self, sql: str) -> dict:
        """
        SQL에서 현재 적용된 힌트 추출
        
        Returns:
            hints: {'maxdop', 'join_hint', 'isolation_hint', 'recompile', 'optimize_for_unknown'}
        """
        sql_upper = sql.upper()
        
        hints = {
            'maxdop': 0,
            'join_hint': 'none',
            'isolation_hint': False,
            'recompile': False,
            'optimize_for_unknown': False
        }
        
        # MAXDOP 추출
        maxdop_match = re.search(r'MAXDOP\s+(\d+)', sql_upper)
        if maxdop_match:
            hints['maxdop'] = int(maxdop_match.group(1))
        
        # JOIN 힌트
        if 'HASH JOIN' in sql_upper or 'USE HINT.*HASH' in sql_upper:
            hints['join_hint'] = 'hash'
        elif 'MERGE JOIN' in sql_upper:
            hints['join_hint'] = 'merge'
        elif 'LOOP JOIN' in sql_upper:
            hints['join_hint'] = 'loop'
        elif 'FORCE ORDER' in sql_upper:
            hints['join_hint'] = 'force_order'
        
        # 기타 힌트
        if 'NOLOCK' in sql_upper or 'READUNCOMMITTED' in sql_upper:
            hints['isolation_hint'] = True
        
        if 'RECOMPILE' in sql_upper:
            hints['recompile'] = True
        
        if 'OPTIMIZE FOR UNKNOWN' in sql_upper:
            hints['optimize_for_unknown'] = True
        
        return hints


if __name__ == '__main__':
    print("=== Actionable State Encoder 테스트 ===\n")
    
    encoder = ActionableStateEncoder()
    
    # 테스트 SQL
    test_sql = """
    WITH ExecutionStats AS (
        SELECT 
            s.security_id,
            s.symbol,
            e.exec_price
        FROM dbo.exe_execution e
        JOIN dbo.ord_order o ON e.order_id = o.order_id
        JOIN dbo.ref_security s ON o.security_id = s.security_id
        WHERE e.exec_time >= DATEADD(HOUR, -24, GETDATE())
    )
    SELECT security_id FROM ExecutionStats
    """
    
    # 테스트 메트릭
    test_metrics = {
        'elapsed_time_ms': 25.0,
        'logical_reads': 1000,
        'cpu_time_ms': 18.0
    }
    
    # 테스트 힌트 (초기 상태: 힌트 없음)
    test_hints = {
        'maxdop': 0,
        'join_hint': 'none',
        'isolation_hint': False,
        'recompile': False,
        'optimize_for_unknown': False
    }
    
    # State 인코딩
    state = encoder.encode_from_query_and_metrics(
        sql=test_sql,
        current_metrics=test_metrics,
        current_hints=test_hints,
        prev_action_id=-1,
        prev_reward=0.0
    )
    
    print(f"State 차원: {state.shape}")
    print(f"State 값 범위: [{state.min():.3f}, {state.max():.3f}]")
    print(f"\nState 구성:")
    print(f"  [0-3]   Query 구조: {state[0:4]}")
    print(f"  [4-8]   현재 힌트: {state[4:9]}")
    print(f"  [9-11]  리소스(log): {state[9:12]}")
    print(f"  [12-15] Query 타입: {state[12:16]}")
    print(f"  [16-17] 이력: {state[16:18]}")
    
    print(f"\n[SUCCESS] 18차원 State 인코딩 완료!")
    
    # 힌트 추출 테스트
    test_sql_with_hints = test_sql + " OPTION (MAXDOP 4, RECOMPILE)"
    hints = encoder.extract_hints_from_sql(test_sql_with_hints)
    print(f"\n힌트 추출 테스트: {hints}")

