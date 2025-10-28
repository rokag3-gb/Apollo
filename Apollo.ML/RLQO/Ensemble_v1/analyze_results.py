# -*- coding: utf-8 -*-
"""
Ensemble v1 결과 분석 스크립트
쿼리별 성능을 표로 출력
"""

import json
import os
import pandas as pd
import numpy as np

# 결과 파일 로드
results_file = os.path.join(
    os.path.dirname(__file__), 
    'results', 
    'ensemble_3models_30queries.json'
)

with open(results_file, 'r', encoding='utf-8') as f:
    results = json.load(f)

# 쿼리별 집계
query_summary = []

for q_idx_str, query_data in results['query_results'].items():
    q_idx = int(q_idx_str)
    
    # 해당 쿼리의 상세 결과
    query_details = [d for d in results['detailed_results'] if d['query_idx'] == q_idx]
    
    if not query_details:
        continue
    
    # 액션 집계
    actions = [d['action'] for d in query_details]
    action_counts = {}
    for action in set(actions):
        action_counts[action] = actions.count(action)
    
    # 가장 많이 선택된 액션
    most_common_action = max(action_counts, key=action_counts.get)
    
    # Speedup 통계
    speedups = [d['speedup'] for d in query_details]
    
    # 베이스라인 시간
    baseline_ms = query_details[0]['baseline_ms']
    
    query_summary.append({
        'Query_Index': f"Q{q_idx}",
        'Query_Type': query_data['query_type'],
        'Baseline_ms': f"{baseline_ms:.1f}",
        'Most_Common_Action': most_common_action,
        'Action_Distribution': f"{action_counts}",
        'Mean_Speedup': f"{query_data['mean_speedup']:.3f}x",
        'Median_Speedup': f"{query_data['median_speedup']:.3f}x",
        'Min_Speedup': f"{min(speedups):.3f}x",
        'Max_Speedup': f"{max(speedups):.3f}x",
        'Episodes': query_data['episodes'],
        'Win_Rate': f"{sum(1 for s in speedups if s > 1.0) / len(speedups) * 100:.0f}%",
        'Safe_Rate': f"{sum(1 for s in speedups if s >= 0.9) / len(speedups) * 100:.0f}%",
    })

# DataFrame 생성
df = pd.DataFrame(query_summary)

# 전체 출력
print("=" * 150)
print("Ensemble v1 (3-Model) 쿼리별 성능 분석")
print("=" * 150)
print(f"Models: {', '.join(results['models'])}")
print(f"Total Queries: {results['n_queries']}")
print(f"Episodes per Query: {results['n_episodes']}")
print(f"Total Evaluations: {len(results['detailed_results'])}")
print("=" * 150)
print()

# 표 출력 (pandas 설정)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

print(df.to_string(index=False))
print()

# 전체 요약
print("=" * 150)
print("Overall Summary")
print("=" * 150)
print(f"Mean Speedup:      {results['summary']['mean_speedup']:.3f}x")
print(f"Median Speedup:    {results['summary']['median_speedup']:.3f}x")
print(f"Max Speedup:       {results['summary']['max_speedup']:.3f}x")
print(f"Win Rate:          {results['summary']['win_rate']*100:.1f}%")
print(f"Safe Rate:         {results['summary']['safe_rate']*100:.1f}%")
print(f"Model Agreement:   {results['summary']['mean_agreement']*100:.1f}%")
print("=" * 150)
print()

# Action 분포
print("=" * 150)
print("Action Distribution (Overall)")
print("=" * 150)
action_counts = {}
for detail in results['detailed_results']:
    action = detail['action']
    action_counts[action] = action_counts.get(action, 0) + 1

for action, count in sorted(action_counts.items()):
    percentage = count / len(results['detailed_results']) * 100
    print(f"Action {action}: {count:3d} times ({percentage:5.1f}%)")
print("=" * 150)
print()

# Query Type별 성능
print("=" * 150)
print("Performance by Query Type")
print("=" * 150)

query_type_stats = {}
for detail in results['detailed_results']:
    qtype = detail['query_type']
    if qtype not in query_type_stats:
        query_type_stats[qtype] = []
    query_type_stats[qtype].append(detail['speedup'])

for qtype, speedups in sorted(query_type_stats.items()):
    mean_speedup = np.mean(speedups)
    win_rate = sum(1 for s in speedups if s > 1.0) / len(speedups) * 100
    print(f"{qtype:15s}: Mean {mean_speedup:.3f}x, Win Rate {win_rate:5.1f}%, Episodes {len(speedups):3d}")

print("=" * 150)

# CSV로도 저장
csv_file = os.path.join(os.path.dirname(__file__), 'results', 'ensemble_3models_summary.csv')
df.to_csv(csv_file, index=False, encoding='utf-8-sig')
print(f"\n[CSV saved to: {csv_file}]")

