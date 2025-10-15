# -*- coding: utf-8 -*-
"""
Query 타입 분류 시스템

Query를 4가지 타입으로 분류하고, 각 타입별로 안전한/위험한 액션을 정의합니다.
"""

import re


def classify_query(sql: str) -> str:
    """
    SQL 쿼리를 타입별로 분류합니다.
    
    Args:
        sql: SQL 쿼리 문자열
    
    Returns:
        'CTE', 'JOIN_HEAVY', 'TOP', 'SIMPLE' 중 하나
    """
    sql_upper = sql.upper()
    sql_clean = re.sub(r'--.*$', '', sql_upper, flags=re.MULTILINE)  # 주석 제거
    sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)  # 블록 주석 제거
    
    # CTE 쿼리: WITH ... AS 패턴
    if re.search(r'\bWITH\s+\w+\s+AS\s*\(', sql_clean):
        return 'CTE'
    
    # JOIN_HEAVY: 3개 이상 테이블 조인
    join_count = len(re.findall(r'\bJOIN\b', sql_clean))
    if join_count >= 3:
        return 'JOIN_HEAVY'
    
    # TOP 쿼리: TOP n 절 포함
    if re.search(r'\bTOP\s+\d+', sql_clean):
        return 'TOP'
    
    # SIMPLE: 나머지
    return 'SIMPLE'


# Query 타입별 안전한 액션 정의
# 각 타입에 맞는 힌트만 선택하도록 제한
QUERY_TYPE_SAFE_ACTIONS = {
    'CTE': [
        0,   # SET_MAXDOP_1 (안전한 단일 스레드)
        7,   # OPTIMIZE_FOR_UNKNOWN
        8,   # DISABLE_PARAMETER_SNIFFING
        9,   # COMPAT_LEVEL_140 (안정적)
        13,  # RECOMPILE (CTE는 때때로 필요)
        18   # NO_ACTION (항상 안전)
    ],
    'JOIN_HEAVY': [
        3,   # USE_HASH_JOIN (대용량 조인에 좋음)
        5,   # USE_MERGE_JOIN (정렬된 데이터에 좋음)
        6,   # FORCE_JOIN_ORDER (조인 순서 제어)
        7,   # OPTIMIZE_FOR_UNKNOWN
        8,   # DISABLE_PARAMETER_SNIFFING
        18   # NO_ACTION
    ],
    'TOP': [
        14,  # FAST_10 (TOP 쿼리에 최적)
        15,  # FAST_50
        16,  # FAST_100
        17,  # FAST_200
        0,   # SET_MAXDOP_1 (안정성)
        7,   # OPTIMIZE_FOR_UNKNOWN
        18   # NO_ACTION
    ],
    'SIMPLE': [
        0,   # SET_MAXDOP_1
        1,   # SET_MAXDOP_4 (적당한 병렬화)
        7,   # OPTIMIZE_FOR_UNKNOWN
        8,   # DISABLE_PARAMETER_SNIFFING
        12,  # USE_NOLOCK (단순 SELECT에는 괜찮음)
        18   # NO_ACTION
    ]
}

# Query 타입별 위험한 액션 정의 (강한 페널티 적용)
QUERY_TYPE_DANGEROUS_ACTIONS = {
    'CTE': [
        2,   # SET_MAXDOP_8 (CTE에서 과도한 병렬화는 위험)
        4,   # USE_LOOP_JOIN (Nested Loop는 CTE에 비효율적)
        11,  # COMPAT_LEVEL_160 (최신 버전은 불안정할 수 있음)
    ],
    'JOIN_HEAVY': [
        4,   # USE_LOOP_JOIN (대용량 조인에 매우 느림)
        11,  # COMPAT_LEVEL_160
        13,  # RECOMPILE (복잡한 조인에서는 오버헤드)
    ],
    'TOP': [
        2,   # SET_MAXDOP_8 (TOP 쿼리에 과도한 병렬화)
        3,   # USE_HASH_JOIN (TOP은 FAST hint가 더 적합)
        4,   # USE_LOOP_JOIN
        6,   # FORCE_JOIN_ORDER (TOP과 충돌 가능)
        13,  # RECOMPILE
    ],
    'SIMPLE': [
        2,   # SET_MAXDOP_8 (단순 쿼리에 과도한 병렬화)
        4,   # USE_LOOP_JOIN
        6,   # FORCE_JOIN_ORDER (단순 쿼리에 불필요)
        11,  # COMPAT_LEVEL_160
        13,  # RECOMPILE (단순 쿼리에 불필요한 오버헤드)
    ]
}


def get_safe_actions(query_type: str) -> list[int]:
    """Query 타입에 대한 안전한 액션 리스트 반환"""
    return QUERY_TYPE_SAFE_ACTIONS.get(query_type, QUERY_TYPE_SAFE_ACTIONS['SIMPLE'])


def get_dangerous_actions(query_type: str) -> list[int]:
    """Query 타입에 대한 위험한 액션 리스트 반환"""
    return QUERY_TYPE_DANGEROUS_ACTIONS.get(query_type, QUERY_TYPE_DANGEROUS_ACTIONS['SIMPLE'])


def is_action_safe(query_type: str, action_id: int) -> bool:
    """특정 액션이 Query 타입에 안전한지 확인"""
    return action_id in get_safe_actions(query_type)


def is_action_dangerous(query_type: str, action_id: int) -> bool:
    """특정 액션이 Query 타입에 위험한지 확인"""
    return action_id in get_dangerous_actions(query_type)


if __name__ == '__main__':
    # 테스트
    from RLQO.constants import SAMPLE_QUERIES
    
    print("=" * 80)
    print("Query 타입 분류 테스트")
    print("=" * 80)
    
    for i, query in enumerate(SAMPLE_QUERIES):
        query_type = classify_query(query)
        safe_actions = get_safe_actions(query_type)
        dangerous_actions = get_dangerous_actions(query_type)
        
        print(f"\nQuery {i}: {query_type}")
        print(f"  SQL: {query[:80]}...")
        print(f"  안전한 액션 수: {len(safe_actions)}")
        print(f"  위험한 액션 수: {len(dangerous_actions)}")
    
    print("\n[SUCCESS] 분류 테스트 완료!")

