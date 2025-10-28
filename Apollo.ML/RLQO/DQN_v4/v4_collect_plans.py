# -*- coding: utf-8 -*-
"""
DQN v4: 실행 계획 사전 수집 스크립트 (constants2.py 기반 30개 쿼리)
====================================
constants2.py의 SAMPLE_QUERIES의 실행 계획을 미리 수집하여 캐싱합니다.
- 호환 액션만 수집 (호환성 매핑 기반)
- 베이스라인 시간 측정하여 난이도 순 저장
- 5회 실행 중앙값 유지

실행 순서:
1. 원본 쿼리 30개 실행 계획 수집
2. 각 쿼리별 호환 액션만 적용 버전 실행 계획 수집
3. pickle 파일로 저장
4. 총 DB 접근: ~300번 이상 (약 3-4시간 소요 예상)
"""

import os
import sys
import pickle
import json
from datetime import datetime
import pandas as pd
import numpy as np

# 현재 스크립트의 디렉토리를 기준으로 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
# DQN_v4/ -> RLQO -> Apollo.ML
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(apollo_ml_dir)
sys.path.append(rlqo_dir)

from RLQO.constants2 import SAMPLE_QUERIES
from RLQO.DQN_v4.env.v4_db_env import apply_action_to_sql
from RLQO.DQN_v1.features.phase2_features import extract_features
from db import connect, get_execution_plan, get_query_statistics
from config import load_config


def parse_statistics(stats_io: str, stats_time: str) -> dict:
    """통계 파싱 (v3_db_env.py와 동일)"""
    import re
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


def collect_query_plan_with_median(conn, sql: str, num_runs: int = 5) -> dict:
    """
    쿼리를 여러 번 실행하여 중앙값을 계산합니다.
    
    Args:
        conn: DB 연결
        sql: 실행할 SQL
        num_runs: 실행 횟수
        
    Returns:
        중앙값 기반 메트릭과 실행 계획
    """
    all_metrics = []
    plan_xml = None
    
    for run in range(num_runs):
        try:
            # 실행 계획 수집 (첫 번째 실행에서만)
            if run == 0:
                plan_xml = get_execution_plan(conn, sql)
            
            # 통계 수집
            stats_io, stats_time = get_query_statistics(conn, sql)
            metrics = parse_statistics(stats_io, stats_time)
            
            # 안전성을 위해 0 이하 값 방지
            metrics['elapsed_time_ms'] = max(0.1, metrics['elapsed_time_ms'])
            metrics['logical_reads'] = max(1, metrics['logical_reads'])
            metrics['cpu_time_ms'] = max(0.1, metrics['cpu_time_ms'])
            
            all_metrics.append(metrics)
            
        except Exception as e:
            print(f"    실행 {run+1} 실패: {e}")
            continue
    
    if not all_metrics:
        print(f"    모든 실행 실패!")
        return None
    
    # 중앙값 계산
    median_metrics = {}
    for key in ['elapsed_time_ms', 'logical_reads', 'cpu_time_ms']:
        values = [m[key] for m in all_metrics]
        median_metrics[key] = np.median(values)
    
    # 실행 계획에서 특징 추출
    if plan_xml:
        try:
            observation = extract_features(plan_xml, median_metrics)
        except Exception as e:
            print(f"    특징 추출 실패: {e}")
            observation = np.zeros(79, dtype=np.float32)
    else:
        observation = np.zeros(79, dtype=np.float32)
    
    return {
        'observation': observation,
        'metrics': median_metrics,
        'plan_xml': plan_xml,
        'runs': len(all_metrics)
    }


def main():
    """메인 실행 함수"""
    print("=== DQN v4 실행 계획 수집 시작 (constants2.py 기반 30개 쿼리) ===\n")
    
    # 1. 설정 로드
    config = load_config('Apollo.ML/config.yaml')
    conn = connect(config.db)
    
    # 2. 액션 스페이스와 호환성 매핑 로드
    # v4는 v3의 액션 스페이스와 호환성 매핑을 재사용하되, 30개 쿼리를 위해 재생성 필요
    with open('Apollo.ML/artifacts/RLQO/configs/v4_action_space.json', 'r') as f:
        actions = json.load(f)
    
    with open('Apollo.ML/artifacts/RLQO/configs/v4_query_action_compatibility.json', 'r') as f:
        compatibility_map = json.load(f)
    
    print(f"총 쿼리 수: {len(SAMPLE_QUERIES)}")
    print(f"총 액션 수: {len(actions)}")
    
    # 3. 캐시 딕셔너리 초기화
    plan_cache = {}
    query_difficulties = {}
    
    # 4. 원본 쿼리 실행 계획 수집
    print("\n[Step 1] 원본 쿼리 실행 계획 수집...")
    for i, sql in enumerate(SAMPLE_QUERIES):
        print(f"\n쿼리 {i} 수집 중...")
        print(f"SQL: {sql[:100]}...")
        
        result = collect_query_plan_with_median(conn, sql, num_runs=5)
        if result:
            plan_cache[sql.strip()] = result
            query_difficulties[i] = result['metrics']['elapsed_time_ms']
            print(f"  완료: {result['metrics']['elapsed_time_ms']:.1f}ms, "
                  f"{result['metrics']['logical_reads']} reads, "
                  f"{result['runs']}회 실행")
        else:
            print(f"  실패!")
    
    # 5. 호환 액션 적용 버전 수집
    print(f"\n[Step 2] 호환 액션 적용 버전 수집...")
    total_combinations = 0
    
    for i, sql in enumerate(SAMPLE_QUERIES):
        compatible_actions = compatibility_map[str(i)]
        print(f"\n쿼리 {i}: {len(compatible_actions)}개 호환 액션")
        
        for action_name in compatible_actions:
            # 액션 찾기
            action = None
            for a in actions:
                if a['name'] == action_name:
                    action = a
                    break
            
            if not action:
                print(f"  액션 {action_name}을 찾을 수 없음")
                continue
            
            # 액션 적용된 SQL 생성
            modified_sql = apply_action_to_sql(sql, action)
            cache_key = modified_sql.strip()
            
            if cache_key in plan_cache:
                print(f"  {action_name}: 이미 캐시됨")
                continue
            
            print(f"  {action_name} 수집 중...")
            result = collect_query_plan_with_median(conn, modified_sql, num_runs=5)
            
            if result:
                plan_cache[cache_key] = result
                total_combinations += 1
                print(f"    완료: {result['metrics']['elapsed_time_ms']:.1f}ms, "
                      f"{result['metrics']['logical_reads']} reads")
            else:
                print(f"    실패!")
    
    # 6. 결과 저장
    print(f"\n[Step 3] 결과 저장...")
    
    # 캐시 파일 저장
    cache_dir = 'Apollo.ML/artifacts/RLQO/cache'
    os.makedirs(cache_dir, exist_ok=True)
    
    cache_file = os.path.join(cache_dir, 'v4_plan_cache.pkl')
    with open(cache_file, 'wb') as f:
        pickle.dump(plan_cache, f)
    
    # 난이도 정보 저장
    difficulty_file = os.path.join(cache_dir, 'v4_query_difficulties.json')
    with open(difficulty_file, 'w') as f:
        json.dump(query_difficulties, f, indent=2)
    
    # 7. 통계 출력
    print(f"\n=== 수집 완료 ===")
    print(f"총 캐시된 쿼리: {len(plan_cache)}개")
    print(f"원본 쿼리: {len(SAMPLE_QUERIES)}개")
    print(f"액션 적용 쿼리: {total_combinations}개")
    print(f"캐시 파일: {cache_file}")
    print(f"난이도 파일: {difficulty_file}")
    
    # 난이도 순 정렬 출력
    print(f"\n=== 쿼리 난이도 순 (빠른 → 느린) ===")
    sorted_difficulties = sorted(query_difficulties.items(), key=lambda x: x[1])
    for i, (query_idx, difficulty) in enumerate(sorted_difficulties):
        print(f"{i+1}. 쿼리 {query_idx}: {difficulty:.1f}ms")
    
    conn.close()
    print(f"\n[SUCCESS] 모든 작업 완료!")


if __name__ == "__main__":
    main()
