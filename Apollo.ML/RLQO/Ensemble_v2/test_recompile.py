# -*- coding: utf-8 -*-
"""
OPTION (RECOMPILE) 추가 후 실제 실행 테스트
"""

import sys
import os

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
rlqo_dir = os.path.join(apollo_ml_dir, 'RLQO')
project_root = os.path.abspath(os.path.join(apollo_ml_dir, '..'))

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)

from RLQO.constants2 import SAMPLE_QUERIES
from RLQO.DQN_v4.env.v4_db_env import apply_action_to_sql
from db import connect, get_query_statistics

# 문제가 되는 쿼리들
problem_queries = [8, 11, 12, 15, 23, 26, 29]

# NO_ACTION (RECOMPILE만 추가)
no_action = {"type": "BASELINE", "value": ""}

print("="*80)
print("OPTION (RECOMPILE) 실제 실행 테스트")
print("="*80)

# DB 연결
try:
    from config import load_config
    config_path = os.path.join(apollo_ml_dir, 'config.yaml')
    config = load_config(config_path)
    conn = connect(config)
    print("[OK] DB 연결 성공\n")
except Exception as e:
    print(f"[ERROR] DB 연결 실패: {e}")
    sys.exit(1)

for q_idx in problem_queries[:3]:  # 처음 3개만 테스트
    print(f"\n{'='*80}")
    print(f"Query {q_idx}")
    print(f"{'='*80}")
    
    original_sql = SAMPLE_QUERIES[q_idx]
    print(f"Original SQL: {original_sql[:100]}...")
    
    # RECOMPILE 추가
    modified_sql = apply_action_to_sql(original_sql, no_action)
    print(f"\nModified SQL: {modified_sql[:200]}...")
    
    # 실행
    try:
        print("\n[실행 중...]")
        stats_io, stats_time = get_query_statistics(conn, modified_sql)
        
        print(f"\nStats IO: {stats_io[:100] if stats_io else '(empty)'}...")
        print(f"Stats TIME: {stats_time[:200] if stats_time else '(empty)'}...")
        
        if not stats_time:
            print("\n[ERROR] stats_time이 비어있음! → elapsed_time_ms = 0")
        else:
            # elapsed time 파싱
            import re
            elapsed_match = re.search(r'elapsed time = (\d+\.?\d*)\s*(ms|s)', stats_time)
            if elapsed_match:
                value = float(elapsed_match.group(1))
                unit = elapsed_match.group(2)
                elapsed_ms = value * 1000 if unit == 's' else value
                print(f"\n[OK] Elapsed time: {elapsed_ms} ms")
            else:
                print(f"\n[ERROR] elapsed time 파싱 실패!")
                
    except Exception as e:
        print(f"\n[ERROR] 실행 실패: {e}")

conn.close()
print("\n"+"="*80)
print("테스트 완료")
print("="*80)

