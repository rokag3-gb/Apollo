# -*- coding: utf-8 -*-
"""
DQN v4: 쿼리별 액션 호환성 매핑 생성 스크립트 (constants2.py 기반 30개 쿼리)
=============================================
constants2.py의 SAMPLE_QUERIES를 분석하여 각 쿼리별로 호환되는 액션을 자동 결정합니다.

분석 기준:
- JOIN 존재 여부 → MERGE/HASH/LOOP JOIN 허용
- TOP 절 존재 → FAST n 허용  
- 서브쿼리/NOT EXISTS → FORCE ORDER 제외
- 매개변수 없는 쿼리 → OPTIMIZE_FOR_UNKNOWN 제외
"""

import os
import sys
import json
import re
from typing import List, Dict, Set

sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML'))
sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML', 'RLQO'))

from RLQO.constants2 import SAMPLE_QUERIES


def analyze_query_structure(sql: str) -> Dict[str, bool]:
    """
    SQL 쿼리의 구조를 분석하여 액션 호환성을 결정하는 특징을 추출합니다.
    
    Args:
        sql: 분석할 SQL 쿼리
        
    Returns:
        특징 딕셔너리 (has_join, has_top, has_subquery, has_parameters 등)
    """
    sql_upper = sql.upper()
    
    features = {
        'has_join': bool(re.search(r'\bJOIN\b', sql_upper)),
        'has_top': bool(re.search(r'\bTOP\s+\d+\b', sql_upper)),
        'has_subquery': bool(re.search(r'\bEXISTS\b|\bNOT\s+EXISTS\b|\bIN\s*\(', sql_upper)),
        'has_parameters': bool(re.search(r'@\w+', sql_upper)),  # 매개변수 존재 여부
        'has_order_by': bool(re.search(r'\bORDER\s+BY\b', sql_upper)),
        'has_group_by': bool(re.search(r'\bGROUP\s+BY\b', sql_upper)),
        'has_union': bool(re.search(r'\bUNION\b', sql_upper)),
        'has_cte': bool(re.search(r'\bWITH\b', sql_upper)),  # Common Table Expression
        'has_window_function': bool(re.search(r'\bOVER\s*\(', sql_upper)),
        'has_aggregation': bool(re.search(r'\b(COUNT|SUM|AVG|MIN|MAX)\s*\(', sql_upper))
    }
    
    return features


def get_compatible_actions(features: Dict[str, bool]) -> List[str]:
    """
    쿼리 특징을 바탕으로 호환되는 액션 목록을 반환합니다.
    
    Args:
        features: analyze_query_structure()에서 반환된 특징 딕셔너리
        
    Returns:
        호환되는 액션 이름 목록
    """
    compatible_actions = []
    
    # 기본적으로 항상 호환되는 액션들
    always_compatible = [
        'SET_MAXDOP_1', 'SET_MAXDOP_4', 'SET_MAXDOP_8',
        'OPTIMIZE_FOR_UNKNOWN', 'DISABLE_PARAMETER_SNIFFING',
        'COMPAT_LEVEL_140', 'COMPAT_LEVEL_150', 'COMPAT_LEVEL_160',
        'RECOMPILE', 'USE_NOLOCK', 'NO_ACTION'
    ]
    compatible_actions.extend(always_compatible)
    
    # JOIN이 있는 경우에만 호환되는 액션들
    if features['has_join']:
        compatible_actions.extend([
            'USE_HASH_JOIN', 'USE_LOOP_JOIN', 'USE_MERGE_JOIN', 'FORCE_JOIN_ORDER'
        ])
    
    # TOP 절이 있는 경우에만 호환되는 액션들
    if features['has_top']:
        compatible_actions.extend([
            'FAST_10', 'FAST_50', 'FAST_100', 'FAST_200'
        ])
    
    # 매개변수가 있는 경우에만 OPTIMIZE_FOR_UNKNOWN이 의미 있음
    # 매개변수가 없으면 제거
    if not features['has_parameters']:
        if 'OPTIMIZE_FOR_UNKNOWN' in compatible_actions:
            compatible_actions.remove('OPTIMIZE_FOR_UNKNOWN')
    
    # 서브쿼리나 NOT EXISTS가 있는 경우 FORCE_JOIN_ORDER는 의미 없음
    if features['has_subquery']:
        if 'FORCE_JOIN_ORDER' in compatible_actions:
            compatible_actions.remove('FORCE_JOIN_ORDER')
    
    return compatible_actions


def generate_compatibility_mapping() -> Dict[str, List[str]]:
    """
    모든 SAMPLE_QUERIES에 대해 호환성 매핑을 생성합니다.
    
    Returns:
        {query_index: [compatible_actions]} 형태의 딕셔너리
    """
    compatibility_map = {}
    
    print("=== DQN v4 쿼리별 액션 호환성 분석 (constants2.py 기반 30개 쿼리) ===\n")
    
    for i, sql in enumerate(SAMPLE_QUERIES):
        print(f"[인덱스 {i}] 쿼리 분석 중...")
        print(f"SQL: {sql[:100]}...")
        
        # 쿼리 구조 분석
        features = analyze_query_structure(sql)
        
        # 호환 액션 결정
        compatible_actions = get_compatible_actions(features)
        
        # 결과 저장
        compatibility_map[str(i)] = compatible_actions
        
        # 분석 결과 출력
        print(f"특징: {features}")
        print(f"호환 액션 ({len(compatible_actions)}개): {compatible_actions}")
        print("-" * 80)
    
    return compatibility_map


def save_compatibility_mapping(compatibility_map: Dict[str, List[str]], 
                             output_path: str) -> None:
    """
    호환성 매핑을 JSON 파일로 저장합니다.
    
    Args:
        compatibility_map: 호환성 매핑 딕셔너리
        output_path: 출력 파일 경로
    """
    # 디렉토리 생성
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # JSON 파일로 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(compatibility_map, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SUCCESS] 호환성 매핑 저장 완료: {output_path}")
    
    # 통계 출력
    total_queries = len(compatibility_map)
    avg_actions = sum(len(actions) for actions in compatibility_map.values()) / total_queries
    
    print(f"총 쿼리 수: {total_queries}")
    print(f"평균 호환 액션 수: {avg_actions:.1f}개")
    
    # 쿼리별 액션 수 분포
    action_counts = [len(actions) for actions in compatibility_map.values()]
    print(f"액션 수 범위: {min(action_counts)} ~ {max(action_counts)}개")


def main():
    """메인 실행 함수"""
    print("DQN v4 쿼리별 액션 호환성 매핑 생성 시작 (constants2.py 기반 30개 쿼리)...\n")
    
    # 호환성 매핑 생성
    compatibility_map = generate_compatibility_mapping()
    
    # 결과 저장
    output_path = 'Apollo.ML/artifacts/RLQO/configs/v4_query_action_compatibility.json'
    save_compatibility_mapping(compatibility_map, output_path)
    
    print("\n=== 생성된 호환성 매핑 요약 ===")
    for query_idx, actions in compatibility_map.items():
        print(f"쿼리 {query_idx}: {len(actions)}개 액션")
        print(f"  {actions}")
    
    print(f"\n[SUCCESS] 모든 작업 완료!")


if __name__ == "__main__":
    main()
