# -*- coding: utf-8 -*-
"""
ISOLATION LEVEL 액션만 캐시에 추가하는 스크립트
"""

import os
import sys
import json
import pickle
from pathlib import Path

# 경로 설정
current_dir = Path(__file__).resolve().parent
apollo_ml_dir = current_dir.parent.parent
rlqo_dir = apollo_ml_dir / 'RLQO'

sys.path.insert(0, str(apollo_ml_dir))
sys.path.insert(1, str(rlqo_dir))

from RLQO.constants2 import SAMPLE_QUERIES
from RLQO.DQN_v3.env.v3_db_env import apply_action_to_sql
from RLQO.DQN_v1.features.phase2_features import extract_features
from db import connect, get_execution_plan, get_query_statistics
from config import load_config


def parse_statistics(stats_io: str, stats_time: str) -> dict:
    """통계 파싱"""
    import re
    metrics = {}
    
    # IO 통계
    logical_reads_match = re.search(r'logical reads (\d+)', stats_io)
    if logical_reads_match:
        metrics['logical_reads'] = int(logical_reads_match.group(1))
    
    # Time 통계
    cpu_time_match = re.search(r'CPU time = (\d+) ms', stats_time)
    elapsed_time_match = re.search(r'elapsed time = (\d+) ms', stats_time)
    
    if cpu_time_match:
        metrics['cpu_time_ms'] = int(cpu_time_match.group(1))
    if elapsed_time_match:
        metrics['elapsed_time_ms'] = int(elapsed_time_match.group(1))
    
    return metrics


def collect_query_plan_with_median(conn, sql, num_runs=5):
    """중위값 기준으로 쿼리 플랜 수집"""
    results = []
    
    for run in range(num_runs):
        try:
            plan_xml, success = get_execution_plan(conn, sql)
            if not success:
                continue
            
            stats_io, stats_time = get_query_statistics(sql)
            if not stats_io or not stats_time:
                continue
            
            metrics = parse_statistics(stats_io, stats_time)
            if 'elapsed_time_ms' in metrics:
                results.append({
                    'plan_xml': plan_xml,
                    'metrics': metrics,
                    'run': run + 1
                })
        except Exception as e:
            print(f"    Run {run+1} failed: {e}")
            continue
    
    if not results:
        return None
    
    # 중위값 선택
    results_sorted = sorted(results, key=lambda x: x['metrics']['elapsed_time_ms'])
    median_result = results_sorted[len(results_sorted) // 2]
    
    # observation 추가
    try:
        observation = extract_features(median_result['plan_xml'])
    except:
        observation = [0.0] * 79
    
    return {
        'plan_xml': median_result['plan_xml'],
        'metrics': median_result['metrics'],
        'observation': observation,
        'runs': [r['metrics']['elapsed_time_ms'] for r in results]
    }


def main():
    print("=" * 80)
    print(" ISOLATION LEVEL Actions - Cache Collection")
    print("=" * 80)
    
    # 설정 로드
    config_path = apollo_ml_dir / 'config.yaml'
    config = load_config(str(config_path))
    
    # DB 연결
    print("\n[1/4] Connecting to database...")
    conn = connect(config.db, max_retries=3, retry_delay=5)
    print("[OK] Connected")
    
    # 액션 스페이스 로드
    print("\n[2/4] Loading action space...")
    action_space_path = apollo_ml_dir / 'artifacts' / 'RLQO' / 'configs' / 'v3_action_space_ppo.json'
    
    with open(action_space_path, 'r', encoding='utf-8') as f:
        actions = json.load(f)
    
    # ISOLATION 액션만 필터링
    isolation_actions = [a for a in actions if a['type'] == 'ISOLATION']
    print(f"[OK] Found {len(isolation_actions)} ISOLATION actions")
    
    # 기존 캐시 로드
    print("\n[3/4] Loading existing cache...")
    cache_path = apollo_ml_dir / 'artifacts' / 'RLQO' / 'cache' / 'v3_plan_cache_ppo.pkl'
    
    if cache_path.exists():
        with open(cache_path, 'rb') as f:
            plan_cache = pickle.load(f)
        print(f"[OK] Loaded {len(plan_cache)} existing entries")
    else:
        print("[WARN] No existing cache, starting fresh")
        plan_cache = {}
    
    # 쿼리별 ISOLATION 액션 수집
    print(f"\n[4/4] Collecting ISOLATION actions for {len(SAMPLE_QUERIES)} queries...")
    print(f"Total: {len(SAMPLE_QUERIES)} queries x {len(isolation_actions)} actions = {len(SAMPLE_QUERIES) * len(isolation_actions)} entries")
    
    total_collected = 0
    total_skipped = 0
    
    for query_idx, sql in enumerate(SAMPLE_QUERIES):
        print(f"\n[Query {query_idx}/29]")
        
        for action in isolation_actions:
            action_name = action['name']
            
            # 액션 적용된 SQL 생성
            modified_sql = apply_action_to_sql(sql, action)
            cache_key = modified_sql.strip()
            
            if cache_key in plan_cache:
                print(f"  - {action_name}: Already cached")
                total_skipped += 1
                continue
            
            print(f"  {action_name} collecting...")
            result = collect_query_plan_with_median(conn, modified_sql, num_runs=5)
            
            if result:
                plan_cache[cache_key] = result
                total_collected += 1
                elapsed_time = result['metrics']['elapsed_time_ms']
                print(f"    [OK] {elapsed_time}ms (median of {len(result['runs'])} runs)")
            else:
                print(f"    [FAIL] Collection failed")
    
    # 캐시 저장
    print(f"\n{'='*80}")
    print(" Saving cache...")
    print(f"{'='*80}")
    
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, 'wb') as f:
        pickle.dump(plan_cache, f)
    
    print(f"[OK] Cache saved: {cache_path}")
    print(f"\nStatistics:")
    print(f"  - Total cache entries: {len(plan_cache)}")
    print(f"  - Newly collected: {total_collected}")
    print(f"  - Skipped (already cached): {total_skipped}")
    
    conn.close()
    print("\n[OK] Complete!")


if __name__ == '__main__':
    main()

