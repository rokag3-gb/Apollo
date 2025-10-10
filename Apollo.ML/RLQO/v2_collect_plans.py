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

sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML'))

from RLQO.constants import SAMPLE_QUERIES
from RLQO.env.phase2_db_env import apply_action_to_sql
from RLQO.features.phase2_features import extract_features
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
    print(" DQN v2: 실행 계획 사전 수집")
    print("="*80)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"수집할 쿼리: {len(SAMPLE_QUERIES)}개")
    
    # 1. DB 연결
    print("\n[1/4] DB 연결 중...")
    config = load_config('Apollo.ML/config.yaml')
    db_connection = connect(config.db)
    print("[OK] DB 연결 완료")
    
    # 2. 액션 로드
    print("\n[2/4] 액션 로드 중...")
    with open('Apollo.ML/artifacts/RLQO/configs/phase2_action_space.json', 'r', encoding='utf-8') as f:
        actions = json.load(f)
    print(f"[OK] {len(actions)}개 액션 로드 완료")
    
    # 3. 실행 계획 수집
    print(f"\n[3/4] 실행 계획 수집 중 (총 {len(SAMPLE_QUERIES) * (len(actions) + 1)}개 예상)...")
    
    plan_cache = {}
    total_collected = 0
    failed_queries = []
    
    for q_idx, query in enumerate(SAMPLE_QUERIES):
        print(f"\n쿼리 {q_idx + 1}/{len(SAMPLE_QUERIES)}")
        print(f"  SQL: {query[:100]}...")
        
        # 3-1. 원본 쿼리 실행 계획 수집
        try:
            plan_xml = get_execution_plan(db_connection, query)
            stats_io, stats_time = get_query_statistics(db_connection, query)
            
            if plan_xml:
                metrics = parse_statistics(stats_io, stats_time)
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
                print(f"  [OK] Baseline: {metrics['elapsed_time_ms']:.2f} ms")
            else:
                print(f"  [WARN] Baseline: 실행 계획 없음")
                failed_queries.append((q_idx, 'baseline', query[:50]))
        
        except Exception as e:
            print(f"  [ERROR] Baseline: {e}")
            failed_queries.append((q_idx, 'baseline', str(e)))
        
        # 3-2. 각 액션 적용 버전 수집
        for action in actions:
            action_id = action['id']
            action_name = action['name']
            
            try:
                modified_sql = apply_action_to_sql(query, action)
                
                # 원본과 동일하면 스킵
                if modified_sql == query:
                    continue
                
                plan_xml = get_execution_plan(db_connection, modified_sql)
                stats_io, stats_time = get_query_statistics(db_connection, modified_sql)
                
                if plan_xml:
                    metrics = parse_statistics(stats_io, stats_time)
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
                    print(f"  [WARN] {action_name}: 실행 계획 없음")
            
            except Exception as e:
                # 실패는 조용히 넘어감 (잘못된 액션일 수 있음)
                pass
    
    # 4. 저장
    print(f"\n[4/4] 수집 결과 저장 중...")
    output_dir = "Apollo.ML/artifacts/RLQO/cache/"
    os.makedirs(output_dir, exist_ok=True)
    
    cache_path = f"{output_dir}plan_cache.pkl"
    with open(cache_path, 'wb') as f:
        pickle.dump(plan_cache, f)
    
    print(f"[OK] 저장 완료: {cache_path}")
    print(f"     파일 크기: {os.path.getsize(cache_path) / 1024:.1f} KB")
    
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
    print(f"[OK] 통계 저장: {stats_path}")
    
    # DB 연결 종료
    db_connection.close()
    
    # 5. 요약
    print("\n" + "="*80)
    print("수집 완료!")
    print("="*80)
    print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n수집 통계:")
    print(f"  - 총 수집: {total_collected}개")
    print(f"  - 성공률: {total_collected / (len(SAMPLE_QUERIES) * (len(actions) + 1)) * 100:.1f}%")
    
    if failed_queries:
        print(f"  - 실패: {len(failed_queries)}개")
        print("\n실패 목록:")
        for q_id, action, reason in failed_queries[:5]:  # 처음 5개만
            print(f"    Query {q_id}, {action}: {reason[:50]}...")
    
    print(f"\n다음 단계:")
    print(f"1. 캐시 확인: {stats_path}")
    print(f"2. 학습 시작: python Apollo.ML/RLQO/train/v2_train_dqn.py --phase A")
    print("="*80 + "\n")
    
    return plan_cache, stats_df


if __name__ == '__main__':
    try:
        cache, stats = collect_execution_plans()
        print("\n[SUCCESS] 실행 계획 수집 완료!")
        print(f"수집된 항목: {len(cache)}개")
        print("\n주요 통계:")
        print(stats.groupby('action_name')['elapsed_time_ms'].agg(['mean', 'min', 'max']).round(2))
    except Exception as e:
        print(f"\n[ERROR] 수집 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

