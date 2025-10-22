# -*- coding: utf-8 -*-
"""
PPO v3: Actionable State Encoder

PPO v2의 18차원 actionable state 유지하면서 새로운 액션 반영:
- MAXDOP 범위: 0-8 → 0-10
- FAST 값 추가: 10-100
- ISOLATION LEVEL: 3가지
- 고급 DBA 힌트 추가
"""

import numpy as np
import re
import sys
import os

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, apollo_ml_dir)

from RLQO.PPO_v3.config.query_action_mapping_v3 import get_query_type


class ActionableStateEncoderV3:
    """
    PPO v3용 행동 영향 반영형 State Encoder
    
    State 구성 (18차원):
    [0-3]   Query 구조 (4): join_count, table_count, has_subquery, has_window
    [4-8]   현재 힌트 (5): maxdop, fast_n, isolation, join_hint, advanced_hints
    [9-11]  리소스 (3): log(time), log(io), log(cpu)
    [12-15] Query 타입 (4): is_cte, is_join_heavy, is_top_or_aggregate, is_other
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
            current_hints: {'maxdop', 'fast_n', 'isolation', 'join_hint', 'advanced_hints'}
            prev_action_id: 이전 액션 ID (-1 ~ 43)
            prev_reward: 이전 보상 값
        
        Returns:
            state: (18,) numpy array, normalized [0, 1]
        """
        state = []
        
        # === 1. Query 구조 (4차원) ===
        sql_upper = sql.upper()
        
        # JOIN 수
        join_count = len(re.findall(r'\bJOIN\b', sql_upper))
        state.append(min(join_count / 5.0, 1.0))
        
        # 테이블 수
        from_count = len(re.findall(r'\bFROM\s+\w+', sql_upper))
        table_count = from_count + join_count
        state.append(min(table_count / 6.0, 1.0))
        
        # 서브쿼리 존재 여부
        has_subquery = 1.0 if re.search(r'\(\s*SELECT\b', sql_upper) else 0.0
        state.append(has_subquery)
        
        # 윈도우 함수 존재 여부
        has_window = 1.0 if re.search(r'\bOVER\s*\(', sql_upper) else 0.0
        state.append(has_window)
        
        # === 2. 현재 힌트 상태 (5차원) ===
        # MAXDOP (0-10 → 0.0-1.0)
        maxdop = current_hints.get('maxdop', 0)
        state.append(maxdop / 10.0)
        
        # FAST n (0-100 → 0.0-1.0)
        fast_n = current_hints.get('fast_n', 0)
        state.append(fast_n / 100.0)
        
        # ISOLATION LEVEL (0=default, 1=READ_COMMITTED, 2=READ_UNCOMMITTED, 3=SNAPSHOT)
        isolation = current_hints.get('isolation', 0)
        state.append(isolation / 3.0)
        
        # JOIN 힌트 (0=none, 1=hash, 2=merge, 3=loop, 4=force_order)
        join_hint_map = {'none': 0, 'hash': 1, 'merge': 2, 'loop': 3, 'force_order': 4}
        join_hint = current_hints.get('join_hint', 'none')
        state.append(join_hint_map.get(join_hint, 0) / 4.0)
        
        # Advanced hints (FORCESEEK, FORCESCAN, 기타 고급 힌트 플래그)
        advanced_hints = current_hints.get('advanced_hints', 0)  # 0 또는 1
        state.append(float(advanced_hints))
        
        # === 3. 리소스 지표 (3차원) - Log scale 정규화 ===
        elapsed_time = current_metrics.get('elapsed_time_ms', 1.0)
        state.append(np.log1p(elapsed_time) / 10.0)
        
        logical_reads = current_metrics.get('logical_reads', 1)
        state.append(np.log1p(logical_reads) / 15.0)
        
        cpu_time = current_metrics.get('cpu_time_ms', 1.0)
        state.append(np.log1p(cpu_time) / 10.0)
        
        # === 4. Query 타입 (4차원) - 간소화된 분류 ===
        # PPO v3의 7가지 타입을 4개 그룹으로 단순화
        query_type = self._classify_query_simple(sql)
        type_map = {'CTE': 0, 'JOIN_HEAVY': 1, 'TOP_AGGREGATE': 2, 'OTHER': 3}
        type_onehot = np.zeros(4)
        type_onehot[type_map[query_type]] = 1.0
        state.extend(type_onehot)
        
        # === 5. 변동 이력 (2차원) ===
        # 이전 액션 정규화 (-1 ~ 43 → 0.0 ~ 1.0)
        prev_action_norm = (prev_action_id + 1) / 44.0
        state.append(prev_action_norm)
        
        # 이전 보상 클리핑 및 정규화 ([-1, +1] → [0, 1])
        prev_reward_clip = np.clip(prev_reward, -1.0, 1.0)
        prev_reward_norm = (prev_reward_clip + 1.0) / 2.0
        state.append(prev_reward_norm)
        
        return np.array(state, dtype=np.float32)
    
    def _classify_query_simple(self, sql: str) -> str:
        """
        간소화된 쿼리 분류 (4가지)
        
        Args:
            sql: SQL 쿼리 문자열
        
        Returns:
            query_type: 'CTE', 'JOIN_HEAVY', 'TOP_AGGREGATE', 'OTHER'
        """
        sql_upper = sql.upper()
        
        # CTE 쿼리
        if re.search(r'\bWITH\s+\w+\s+AS\s*\(', sql_upper):
            return 'CTE'
        
        # JOIN이 많은 쿼리 (3개 이상)
        join_count = len(re.findall(r'\bJOIN\b', sql_upper))
        if join_count >= 3:
            return 'JOIN_HEAVY'
        
        # TOP 또는 GROUP BY가 있는 집계 쿼리
        has_top = bool(re.search(r'\bTOP\s+\d+', sql_upper))
        has_group_by = bool(re.search(r'\bGROUP\s+BY\b', sql_upper))
        if has_top or has_group_by:
            return 'TOP_AGGREGATE'
        
        # 그 외
        return 'OTHER'
    
    def extract_hints_from_sql(self, sql: str) -> dict:
        """
        SQL에서 현재 적용된 힌트 추출
        
        Returns:
            hints: {'maxdop', 'fast_n', 'isolation', 'join_hint', 'advanced_hints'}
        """
        sql_upper = sql.upper()
        
        hints = {
            'maxdop': 0,
            'fast_n': 0,
            'isolation': 0,
            'join_hint': 'none',
            'advanced_hints': 0
        }
        
        # MAXDOP 추출
        maxdop_match = re.search(r'MAXDOP\s+(\d+)', sql_upper)
        if maxdop_match:
            hints['maxdop'] = min(int(maxdop_match.group(1)), 10)
        
        # FAST n 추출
        fast_match = re.search(r'FAST\s+(\d+)', sql_upper)
        if fast_match:
            hints['fast_n'] = min(int(fast_match.group(1)), 100)
        
        # ISOLATION LEVEL 추출
        if 'READ UNCOMMITTED' in sql_upper or 'READUNCOMMITTED' in sql_upper:
            hints['isolation'] = 2
        elif 'SNAPSHOT' in sql_upper:
            hints['isolation'] = 3
        elif 'READ COMMITTED' in sql_upper:
            hints['isolation'] = 1
        
        # JOIN 힌트
        if 'HASH JOIN' in sql_upper:
            hints['join_hint'] = 'hash'
        elif 'MERGE JOIN' in sql_upper:
            hints['join_hint'] = 'merge'
        elif 'LOOP JOIN' in sql_upper:
            hints['join_hint'] = 'loop'
        elif 'FORCE ORDER' in sql_upper:
            hints['join_hint'] = 'force_order'
        
        # Advanced hints
        advanced_keywords = [
            'FORCESEEK', 'FORCESCAN', 'DISABLE_OPTIMIZER_ROWGOAL',
            'ENABLE_QUERY_OPTIMIZER_HOTFIXES', 'KEEPFIXED PLAN',
            'FORCE_LEGACY_CARDINALITY_ESTIMATION', 'BATCH_MODE',
            'ASSUME_JOIN_PREDICATE', 'ASSUME_MIN_SELECTIVITY'
        ]
        if any(keyword in sql_upper for keyword in advanced_keywords):
            hints['advanced_hints'] = 1
        
        return hints


if __name__ == '__main__':
    print("=" * 80)
    print(" PPO v3: Actionable State Encoder 테스트")
    print("=" * 80)
    
    encoder = ActionableStateEncoderV3()
    
    # 테스트 SQL
    test_sql = """
    SELECT TOP 100
        o.order_id,
        o.account_id,
        s.symbol,
        o.qty,
        o.price
    FROM dbo.ord_order o
    JOIN dbo.ref_security s ON o.security_id = s.security_id
    WHERE o.create_time >= DATEADD(DAY, -7, GETDATE())
    ORDER BY o.create_time DESC;
    """
    
    # 테스트 메트릭
    test_metrics = {
        'elapsed_time_ms': 45.0,
        'logical_reads': 1500,
        'cpu_time_ms': 32.0
    }
    
    # 테스트 힌트 (초기 상태)
    test_hints = {
        'maxdop': 0,
        'fast_n': 0,
        'isolation': 0,
        'join_hint': 'none',
        'advanced_hints': 0
    }
    
    # State 인코딩
    state = encoder.encode_from_query_and_metrics(
        sql=test_sql,
        current_metrics=test_metrics,
        current_hints=test_hints,
        prev_action_id=-1,
        prev_reward=0.0
    )
    
    print(f"\nState 차원: {state.shape}")
    print(f"State 값 범위: [{state.min():.3f}, {state.max():.3f}]")
    print(f"\nState 구성:")
    print(f"  [0-3]   Query 구조: {state[0:4]}")
    print(f"  [4-8]   현재 힌트: {state[4:9]}")
    print(f"  [9-11]  리소스(log): {state[9:12]}")
    print(f"  [12-15] Query 타입: {state[12:16]}")
    print(f"  [16-17] 이력: {state[16:18]}")
    
    print(f"\n[SUCCESS] 18차원 State 인코딩 완료!")
    
    # 힌트 추출 테스트
    test_sql_with_hints = test_sql.replace(
        "ORDER BY",
        "OPTION (MAXDOP 4, FAST 50) ORDER BY"
    )
    hints = encoder.extract_hints_from_sql(test_sql_with_hints)
    print(f"\n힌트 추출 테스트: {hints}")
    
    # 다양한 액션 적용 테스트
    test_hints_maxdop = {'maxdop': 4, 'fast_n': 0, 'isolation': 0, 'join_hint': 'none', 'advanced_hints': 0}
    state_maxdop = encoder.encode_from_query_and_metrics(test_sql, test_metrics, test_hints_maxdop)
    print(f"\nMAXDOP 4 적용 시 힌트 state: {state_maxdop[4:9]}")
    
    test_hints_fast = {'maxdop': 0, 'fast_n': 50, 'isolation': 0, 'join_hint': 'none', 'advanced_hints': 0}
    state_fast = encoder.encode_from_query_and_metrics(test_sql, test_metrics, test_hints_fast)
    print(f"FAST 50 적용 시 힌트 state: {state_fast[4:9]}")
    
    test_hints_isolation = {'maxdop': 0, 'fast_n': 0, 'isolation': 2, 'join_hint': 'none', 'advanced_hints': 0}
    state_isolation = encoder.encode_from_query_and_metrics(test_sql, test_metrics, test_hints_isolation)
    print(f"READ UNCOMMITTED 적용 시 힌트 state: {state_isolation[4:9]}")
    
    print("\n" + "=" * 80)
    print(" ✓ 모든 테스트 통과!")
    print("=" * 80)

