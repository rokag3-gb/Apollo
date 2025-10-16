# -*- coding: utf-8 -*-
"""
Query-Action 매핑 정의

Query 타입별로 허용 액션과 위험 액션을 정의합니다.
"""

# Phase 1: 단일 힌트 액션 (학습 시작)
# 각 Query 타입별로 5개의 안전한 액션만 허용
PHASE1_ACTIONS = {
    'CTE': [0, 1, 7, 8, 18],           # MAXDOP 1/4, OPTIMIZE_FOR_UNKNOWN, DISABLE_PARAM_SNIFFING, NO_ACTION
    'JOIN_HEAVY': [3, 5, 7, 8, 18],    # USE_HASH_JOIN, USE_MERGE_JOIN, OPTIMIZE, DISABLE_PARAM, NO_ACTION
    'TOP': [14, 15, 16, 0, 18],        # FAST 10/50/100, MAXDOP 1, NO_ACTION
    'SIMPLE': [0, 1, 8, 12, 18]        # MAXDOP 1/4, DISABLE_PARAM, USE_NOLOCK, NO_ACTION
}

# 위험 액션 (강한 페널티 -1.0, Phase 1에서 제외)
QUERY_DANGEROUS_ACTIONS = {
    'CTE': [2, 4, 11],              # MAXDOP 8, USE_LOOP_JOIN, COMPAT_LEVEL_160
    'JOIN_HEAVY': [4, 11, 13],      # USE_LOOP_JOIN, COMPAT_LEVEL_160, RECOMPILE
    'TOP': [2, 3, 4, 6, 13],        # 높은 병렬화/무거운 조인/RECOMPILE
    'SIMPLE': [2, 4, 6, 11, 13]     # MAXDOP 8, LOOP JOIN, FORCE_ORDER, COMPAT_160, RECOMPILE
}


if __name__ == '__main__':
    print("=== Query-Action 매핑 테스트 ===\n")
    
    for query_type in ['CTE', 'JOIN_HEAVY', 'TOP', 'SIMPLE']:
        allowed = PHASE1_ACTIONS[query_type]
        dangerous = QUERY_DANGEROUS_ACTIONS[query_type]
        
        print(f"{query_type}:")
        print(f"  허용 액션 ({len(allowed)}개): {allowed}")
        print(f"  위험 액션 ({len(dangerous)}개): {dangerous}\n")
    
    # 검증: 허용과 위험이 겹치지 않는지 확인
    for query_type in PHASE1_ACTIONS.keys():
        allowed_set = set(PHASE1_ACTIONS[query_type])
        dangerous_set = set(QUERY_DANGEROUS_ACTIONS[query_type])
        overlap = allowed_set & dangerous_set
        
        if overlap:
            print(f"[ERROR] {query_type}: 허용과 위험 액션 겹침 {overlap}")
        else:
            print(f"[OK] {query_type}: 겹침 없음")

