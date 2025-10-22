# -*- coding: utf-8 -*-
"""
PPO v3: Query-Action 매핑 정의

30개 쿼리에 대한 타입 분류 및 액션 매핑
"""

# ==============================================================================
# 30개 쿼리 타입 분류 (constants2.py 기반)
# ==============================================================================

QUERY_TYPES = {
    0: 'JOIN_HEAVY',      # 5-way JOIN + GROUP BY + 집계
    1: 'CTE',             # CTE + 윈도우 함수
    2: 'SIMPLE',          # 전체 스캔
    3: 'TOP',             # TOP + 2-way JOIN (대용량)
    4: 'TOP',             # TOP + 3-way JOIN (매우 느림)
    5: 'SUBQUERY',        # NOT EXISTS
    6: 'SIMPLE',          # RAND() 함수
    7: 'JOIN_HEAVY',      # LEFT JOIN + GROUP BY + CASE
    8: 'CTE',             # CTE + LAG + 윈도우 함수
    9: 'TOP',             # TOP + GROUP BY (당일 거래량)
    10: 'TOP',            # TOP + GROUP BY (당일 거래대금)
    11: 'CTE',            # CTE (전일 대비 등락률)
    12: 'TOP',            # TOP + 서브쿼리 (포지션 평가)
    13: 'TOP',            # TOP + 단순 필터 (미체결 주문)
    14: 'TOP',            # TOP + 필터 (대량 주문)
    15: 'JOIN_HEAVY',     # TOP + 3-way JOIN (최근 거래 모니터링)
    16: 'JOIN_HEAVY',     # TOP + LEFT JOIN (주문 체결 내역)
    17: 'SUBQUERY',       # TOP + EXISTS
    18: 'SUBQUERY',       # TOP + IN
    19: 'WINDOW',         # 윈도우 함수 (계좌별 현금 잔액)
    20: 'AGGREGATE',      # GROUP BY (거래소별 종목 통계)
    21: 'TOP',            # TOP + 서브쿼리 (종목별 최근 가격)
    22: 'AGGREGATE',      # TOP + GROUP BY (고객별 계좌 요약)
    23: 'TOP',            # TOP + 단순 필터 (리스크 노출도)
    24: 'AGGREGATE',      # GROUP BY + PIVOT (주문 소스 분포)
    25: 'JOIN_HEAVY',     # GROUP BY + 다중 LEFT JOIN (종목 타입별 통계)
    26: 'JOIN_HEAVY',     # TOP + JOIN (마진 계좌)
    27: 'JOIN_HEAVY',     # TOP + JOIN (컴플라이언스 경고)
    28: 'JOIN_HEAVY',     # TOP + GROUP BY + LEFT JOIN (거래 원장 검증)
    29: 'AGGREGATE',      # TOP + GROUP BY + JOIN (변동성 분석)
}

# ==============================================================================
# Phase 1: Query 타입별 허용 액션 (학습 초기)
# ==============================================================================

PHASE1_ACTIONS = {
    # CTE 쿼리 (인덱스: 1, 8, 11)
    # - CTE는 윈도우 함수, 복잡한 서브쿼리 포함
    # - MAXDOP 제한, 윈도우 함수 최적화 중요
    'CTE': [
        10,  # MAXDOP 1
        11,  # MAXDOP 2
        13,  # MAXDOP 4
        27,  # OPTIMIZE_FOR_UNKNOWN
        28,  # DISABLE_PARAMETER_SNIFFING
        29,  # COMPAT_LEVEL_140
        30,  # COMPAT_LEVEL_150
        36,  # ENABLE_QUERY_OPTIMIZER_HOTFIXES
        43   # NO_ACTION
    ],
    
    # JOIN_HEAVY 쿼리 (인덱스: 0, 3, 4, 7, 15, 16, 25, 26, 27, 28, 29)
    # - 다중 조인, 대용량 테이블
    # - JOIN 힌트, 조인 순서, 카디널리티 추정 중요
    'JOIN_HEAVY': [
        10,  # MAXDOP 1
        13,  # MAXDOP 4
        14,  # MAXDOP 5
        23,  # HASH JOIN
        24,  # MERGE JOIN
        27,  # OPTIMIZE_FOR_UNKNOWN
        28,  # DISABLE_PARAMETER_SNIFFING
        34,  # FORCESCAN
        41,  # ASSUME_JOIN_PREDICATE_DEPENDS_ON_FILTERS
        43   # NO_ACTION
    ],
    
    # TOP 쿼리 (인덱스: 3, 4, 9, 10, 12, 13, 14, 15, 21, 23, 26, 27)
    # - TOP N 최적화, FAST 힌트 효과적
    # - FORCESEEK로 인덱스 활용
    'TOP': [
        0,   # FAST 10
        2,   # FAST 30
        4,   # FAST 50
        6,   # FAST 70
        9,   # FAST 100
        10,  # MAXDOP 1
        13,  # MAXDOP 4
        33,  # FORCESEEK
        35,  # DISABLE_OPTIMIZER_ROWGOAL
        43   # NO_ACTION
    ],
    
    # SIMPLE 쿼리 (인덱스: 2, 6, 13, 14, 23)
    # - 단순 스캔, 필터링
    # - 격리 수준, MAXDOP, FORCESCAN
    'SIMPLE': [
        10,  # MAXDOP 1
        11,  # MAXDOP 2
        13,  # MAXDOP 4
        20,  # ISOLATION READ_COMMITTED
        21,  # ISOLATION READ_UNCOMMITTED
        28,  # DISABLE_PARAMETER_SNIFFING
        34,  # FORCESCAN
        37,  # KEEPFIXED_PLAN
        43   # NO_ACTION
    ],
    
    # AGGREGATE 쿼리 (인덱스: 0, 7, 9, 10, 20, 22, 24, 25, 28, 29)
    # - GROUP BY, 집계 함수
    # - 병렬 처리, 배치 모드 효과적
    'AGGREGATE': [
        10,  # MAXDOP 1
        13,  # MAXDOP 4
        14,  # MAXDOP 5
        15,  # MAXDOP 6
        27,  # OPTIMIZE_FOR_UNKNOWN
        28,  # DISABLE_PARAMETER_SNIFFING
        34,  # FORCESCAN
        40,  # ALLOW_BATCH_MODE
        43   # NO_ACTION
    ],
    
    # WINDOW 쿼리 (인덱스: 1, 8, 19)
    # - ROW_NUMBER, LAG, OVER 절
    # - 윈도우 함수는 병렬화 제한적
    'WINDOW': [
        10,  # MAXDOP 1
        11,  # MAXDOP 2
        12,  # MAXDOP 3
        27,  # OPTIMIZE_FOR_UNKNOWN
        28,  # DISABLE_PARAMETER_SNIFFING
        29,  # COMPAT_LEVEL_140
        36,  # ENABLE_QUERY_OPTIMIZER_HOTFIXES
        37,  # KEEPFIXED_PLAN
        43   # NO_ACTION
    ],
    
    # SUBQUERY 쿼리 (인덱스: 5, 17, 18, 21)
    # - EXISTS, IN, NOT EXISTS
    # - 서브쿼리 최적화 중요
    'SUBQUERY': [
        10,  # MAXDOP 1
        13,  # MAXDOP 4
        27,  # OPTIMIZE_FOR_UNKNOWN
        28,  # DISABLE_PARAMETER_SNIFFING
        30,  # COMPAT_LEVEL_150
        33,  # FORCESEEK
        36,  # ENABLE_QUERY_OPTIMIZER_HOTFIXES
        42,  # ASSUME_MIN_SELECTIVITY_FOR_FILTER_ESTIMATES
        43   # NO_ACTION
    ]
}

# ==============================================================================
# 위험 액션 (Query 타입별 강한 페널티 -1.0)
# ==============================================================================

QUERY_DANGEROUS_ACTIONS = {
    # CTE: 높은 병렬화, LOOP JOIN은 위험
    'CTE': [
        17,  # MAXDOP 8
        18,  # MAXDOP 9
        19,  # MAXDOP 10
        25,  # LOOP JOIN
        31,  # COMPAT_LEVEL_160
        32   # RECOMPILE
    ],
    
    # JOIN_HEAVY: LOOP JOIN, 과도한 병렬화 위험
    'JOIN_HEAVY': [
        18,  # MAXDOP 9
        19,  # MAXDOP 10
        25,  # LOOP JOIN
        26,  # FORCE JOIN ORDER (잘못된 순서 강제 시 위험)
        31,  # COMPAT_LEVEL_160
        32   # RECOMPILE
    ],
    
    # TOP: 과도한 FAST 값, 높은 병렬화
    'TOP': [
        17,  # MAXDOP 8
        18,  # MAXDOP 9
        19,  # MAXDOP 10
        23,  # HASH JOIN (TOP에는 부적합)
        25,  # LOOP JOIN
        32,  # RECOMPILE
        34   # FORCESCAN (TOP에는 SEEK가 더 적합)
    ],
    
    # SIMPLE: 높은 병렬화, 복잡한 힌트 불필요
    'SIMPLE': [
        17,  # MAXDOP 8
        18,  # MAXDOP 9
        19,  # MAXDOP 10
        25,  # LOOP JOIN
        26,  # FORCE JOIN ORDER
        31,  # COMPAT_LEVEL_160
        32   # RECOMPILE
    ],
    
    # AGGREGATE: 과도한 병렬화는 오버헤드
    'AGGREGATE': [
        18,  # MAXDOP 9
        19,  # MAXDOP 10
        25,  # LOOP JOIN
        31,  # COMPAT_LEVEL_160
        32,  # RECOMPILE
        39   # DISALLOW_BATCH_MODE (집계에는 배치 모드가 유리)
    ],
    
    # WINDOW: 높은 병렬화 비효율적
    'WINDOW': [
        16,  # MAXDOP 7
        17,  # MAXDOP 8
        18,  # MAXDOP 9
        19,  # MAXDOP 10
        25,  # LOOP JOIN
        31,  # COMPAT_LEVEL_160
        32   # RECOMPILE
    ],
    
    # SUBQUERY: 높은 병렬화, 잘못된 JOIN 힌트
    'SUBQUERY': [
        17,  # MAXDOP 8
        18,  # MAXDOP 9
        19,  # MAXDOP 10
        25,  # LOOP JOIN
        26,  # FORCE JOIN ORDER
        31,  # COMPAT_LEVEL_160
        32   # RECOMPILE
    ]
}

# ==============================================================================
# 헬퍼 함수
# ==============================================================================

def get_query_type(query_index: int) -> str:
    """
    쿼리 인덱스로 타입 조회
    
    Args:
        query_index: 쿼리 인덱스 (0-29)
    
    Returns:
        query_type: 쿼리 타입 문자열
    """
    return QUERY_TYPES.get(query_index, 'SIMPLE')


def get_allowed_actions(query_type: str) -> list:
    """
    Query 타입별 허용 액션 ID 리스트 반환
    
    Args:
        query_type: 쿼리 타입
    
    Returns:
        allowed_actions: 허용 액션 ID 리스트
    """
    return PHASE1_ACTIONS.get(query_type, PHASE1_ACTIONS['SIMPLE'])


def is_dangerous_action(query_type: str, action_id: int) -> bool:
    """
    특정 쿼리 타입에 대해 액션이 위험한지 확인
    
    Args:
        query_type: 쿼리 타입
        action_id: 액션 ID
    
    Returns:
        is_dangerous: 위험 여부
    """
    dangerous_actions = QUERY_DANGEROUS_ACTIONS.get(query_type, [])
    return action_id in dangerous_actions


if __name__ == '__main__':
    print("=" * 80)
    print(" PPO v3: Query-Action 매핑 테스트")
    print("=" * 80)
    
    # 타입별 쿼리 개수 확인
    type_counts = {}
    for query_idx, query_type in QUERY_TYPES.items():
        type_counts[query_type] = type_counts.get(query_type, 0) + 1
    
    print("\n[1] Query 타입 분포:")
    for query_type, count in sorted(type_counts.items()):
        print(f"  {query_type:15s}: {count:2d}개")
    print(f"  {'TOTAL':15s}: {len(QUERY_TYPES):2d}개")
    
    # 타입별 허용 액션 확인
    print("\n[2] Query 타입별 허용 액션 수:")
    for query_type in sorted(PHASE1_ACTIONS.keys()):
        allowed = PHASE1_ACTIONS[query_type]
        dangerous = QUERY_DANGEROUS_ACTIONS[query_type]
        print(f"  {query_type:15s}: 허용 {len(allowed):2d}개, 위험 {len(dangerous):2d}개")
    
    # 검증: 허용과 위험 액션이 겹치지 않는지 확인
    print("\n[3] 허용/위험 액션 겹침 검증:")
    all_valid = True
    for query_type in PHASE1_ACTIONS.keys():
        allowed_set = set(PHASE1_ACTIONS[query_type])
        dangerous_set = set(QUERY_DANGEROUS_ACTIONS[query_type])
        overlap = allowed_set & dangerous_set
        
        if overlap:
            print(f"  [ERROR] {query_type}: 겹침 발견 {overlap}")
            all_valid = False
        else:
            print(f"  [OK] {query_type}: 겹침 없음")
    
    if all_valid:
        print("\n" + "=" * 80)
        print(" ✓ 모든 검증 통과!")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print(" ✗ 검증 실패! 위 에러를 수정하세요.")
        print("=" * 80)

