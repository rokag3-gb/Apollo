# -*- coding: utf-8 -*-
"""
DQN v2: 실행 계획 사전 수집 스크립트
====================================
SAMPLE_QUERIES의 실행 계획을 미리 수집하여 캐싱합니다.
이후 시뮬레이션 학습에서 DB 접근 없이 사용할 수 있습니다.

실행 순서:
1. 원본 쿼리 11개 실행 계획 수집
2. 각 액션 적용 버전 실행 계획 수집 (11 × 9 = 99개)
3. pickle 파일로 저장
4. 총 DB 접근: ~110번 (약 2-3분 소요)
"""

import os
import sys
import pickle
from datetime import datetime
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML'))

from RLQO.constants import SAMPLE_QUERIES
from RLQO.DQN_v2.env.v2_db_env import apply_action_to_sql
from RLQO.DQN_v1.features.phase2_features import extract_features
from db import connect, get_execution_plan, get_query_statistics
from config import load_config
import json


def parse_statistics(stats_io: str, stats_time: str) -> dict:
    """통계 파싱 (phase2_db_env.py와 동일)"""
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
        cpu_time_ms = value * 1000 if unit == 's' else value
    
    elapsed_match = re.search(r'elapsed time = (\d+\.?\d*)\s*(ms|s)', execution_times_block)
    if elapsed_match:
        value = float(elapsed_match.group(1))
        unit = elapsed_match.group(2)
        elapsed_time_ms = value * 1000 if unit == 's' else value
    
    metrics['cpu_time_ms'] = cpu_time_ms
    metrics['elapsed_time_ms'] = round(elapsed_time_ms, 4)
    
    return metrics


def collect_execution_plans():
    """
    SAMPLE_QUERIES의 모든 실행 계획을 수집합니다.
    """
    print("\n" + "="*80)
    print(" DQN v2: Execution Plan Pre-Collection")
    print("="*80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Queries: {len(SAMPLE_QUERIES)}")
    
    # 1. DB 연결
    print("\n[1/4] Connecting to DB...")
    config = load_config('Apollo.ML/config.yaml')
    db_connection = connect(config.db)
    print("[OK] DB Connected")
    
    # 2. 액션 로드
    print("\n[2/4] Loading Actions...")
    with open('Apollo.ML/artifacts/RLQO/configs/v2_action_space.json', 'r', encoding='utf-8') as f:
        actions = json.load(f)
    print(f"[OK] {len(actions)} Actions Loaded (v2.1)")
    
    # 3. 실행 계획 수집
    print(f"\n[3/4] Collecting Execution Plans (Expected: {len(SAMPLE_QUERIES) * (len(actions) + 1)})...")
    
    plan_cache = {}
    total_collected = 0
    failed_queries = []
    
    for q_idx, query in enumerate(SAMPLE_QUERIES):
        print(f"\nQuery {q_idx + 1}/{len(SAMPLE_QUERIES)}")
        print(f"  SQL: {query[:100]}...")
        
        # 3-1. 원본 쿼리 실행 계획 수집 (5회 실행 후 중앙값)
        try:
            elapsed_times = []
            logical_reads_list = []
            cpu_times = []
            plan_xml = None
            
            # 5회 실행하여 안정적인 메트릭 수집
            for run in range(5):
                stats_io, stats_time = get_query_statistics(db_connection, query)
                if stats_io and stats_time:
                    metrics_run = parse_statistics(stats_io, stats_time)
                    elapsed_times.append(metrics_run.get('elapsed_time_ms', 0))
                    logical_reads_list.append(metrics_run.get('logical_reads', 0))
                    cpu_times.append(metrics_run.get('cpu_time_ms', 0))
            
            # 마지막 실행의 plan_xml 수집
            plan_xml = get_execution_plan(db_connection, query)
            
            if plan_xml and elapsed_times:
                # 중앙값 사용
                metrics = {
                    'elapsed_time_ms': float(np.median(elapsed_times)),
                    'logical_reads': int(np.median(logical_reads_list)),
                    'cpu_time_ms': float(np.median(cpu_times))
                }
                features = extract_features(plan_xml, metrics)
                
                plan_cache[f"query_{q_idx}_baseline"] = {
                    'query_text': query,
                    'query_id': q_idx,
                    'action_id': None,
                    'action_name': 'baseline',
                    'plan_xml': plan_xml,
                    'features': features,
                    'metrics': metrics
                }
                total_collected += 1
                print(f"  [OK] Baseline: {metrics['elapsed_time_ms']:.2f} ms (median of 5 runs)")
            else:
                print(f"  [WARN] Baseline: No execution plan")
                failed_queries.append((q_idx, 'baseline', query[:50]))
        
        except Exception as e:
            print(f"  [ERROR] Baseline: {e}")
            failed_queries.append((q_idx, 'baseline', str(e)))
        
        # 3-2. 각 액션 적용 버전 수집 (5회 실행 후 중앙값)
        for action in actions:
            action_id = action['id']
            action_name = action['name']
            
            try:
                modified_sql = apply_action_to_sql(query, action)
                
                # 원본과 동일하면 스킵
                if modified_sql == query:
                    continue
                
                elapsed_times = []
                logical_reads_list = []
                cpu_times = []
                plan_xml = None
                
                # 5회 실행하여 안정적인 메트릭 수집
                for run in range(5):
                    stats_io, stats_time = get_query_statistics(db_connection, modified_sql)
                    if stats_io and stats_time:
                        metrics_run = parse_statistics(stats_io, stats_time)
                        elapsed_times.append(metrics_run.get('elapsed_time_ms', 0))
                        logical_reads_list.append(metrics_run.get('logical_reads', 0))
                        cpu_times.append(metrics_run.get('cpu_time_ms', 0))
                
                # 마지막 실행의 plan_xml 수집
                plan_xml = get_execution_plan(db_connection, modified_sql)
                
                if plan_xml and elapsed_times:
                    # 중앙값 사용
                    metrics = {
                        'elapsed_time_ms': float(np.median(elapsed_times)),
                        'logical_reads': int(np.median(logical_reads_list)),
                        'cpu_time_ms': float(np.median(cpu_times))
                    }
                    features = extract_features(plan_xml, metrics)
                    
                    plan_cache[f"query_{q_idx}_action_{action_id}"] = {
                        'query_text': modified_sql,
                        'query_id': q_idx,
                        'action_id': action_id,
                        'action_name': action_name,
                        'plan_xml': plan_xml,
                        'features': features,
                        'metrics': metrics
                    }
                    total_collected += 1
                    
                    # 개선도 계산
                    baseline_time = plan_cache[f"query_{q_idx}_baseline"]['metrics']['elapsed_time_ms']
                    improvement = (baseline_time - metrics['elapsed_time_ms']) / baseline_time * 100
                    print(f"  [OK] {action_name}: {metrics['elapsed_time_ms']:.2f} ms ({improvement:+.1f}%)")
                else:
                    print(f"  [WARN] {action_name}: No execution plan")
            
            except Exception as e:
                # 실패는 조용히 넘어감 (잘못된 액션일 수 있음)
                pass
    
    # 4. 저장
    print(f"\n[4/4] Saving Results...")
    output_dir = "Apollo.ML/artifacts/RLQO/cache/"
    os.makedirs(output_dir, exist_ok=True)
    
    cache_path = f"{output_dir}plan_cache.pkl"
    with open(cache_path, 'wb') as f:
        pickle.dump(plan_cache, f)
    
    print(f"[OK] Saved: {cache_path}")
    print(f"     File Size: {os.path.getsize(cache_path) / 1024:.1f} KB")
    
    # 통계 저장 (CSV)
    stats_data = []
    for key, value in plan_cache.items():
        stats_data.append({
            'cache_key': key,
            'query_id': value['query_id'],
            'action_name': value['action_name'],
            'elapsed_time_ms': value['metrics']['elapsed_time_ms'],
            'logical_reads': value['metrics']['logical_reads'],
            'cpu_time_ms': value['metrics']['cpu_time_ms']
        })
    
    stats_df = pd.DataFrame(stats_data)
    stats_path = f"{output_dir}plan_cache_stats.csv"
    stats_df.to_csv(stats_path, index=False, encoding='utf-8-sig')
    print(f"[OK] Stats Saved: {stats_path}")
    
    # DB 연결 종료
    db_connection.close()
    
    # 5. 요약
    print("\n" + "="*80)
    print("Collection Complete!")
    print("="*80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nCollection Stats:")
    print(f"  - Total Collected: {total_collected}")
    print(f"  - Success Rate: {total_collected / (len(SAMPLE_QUERIES) * (len(actions) + 1)) * 100:.1f}%")
    
    if failed_queries:
        print(f"  - Failed: {len(failed_queries)}")
        print("\nFailed Queries (first 5):")
        for q_id, action, reason in failed_queries[:5]:
            print(f"    Query {q_id}, {action}: {reason[:50]}...")
    
    print(f"\nNext Steps:")
    print(f"1. Check cache: {stats_path}")
    print(f"2. Start training: python Apollo.ML/RLQO/train/v2_train_dqn.py --phase SimulXGB")
    print("="*80 + "\n")
    
    return plan_cache, stats_df


if __name__ == '__main__':
    try:
        cache, stats = collect_execution_plans()
        print("\n[SUCCESS] Execution Plan Collection Complete!")
        print(f"Total Items: {len(cache)}")
        print("\nKey Statistics:")
        print(stats.groupby('action_name')['elapsed_time_ms'].agg(['mean', 'min', 'max']).round(2))
    except Exception as e:
        print(f"\n[ERROR] Collection Failed: {e}")
        import traceback
        traceback.print_exc()

