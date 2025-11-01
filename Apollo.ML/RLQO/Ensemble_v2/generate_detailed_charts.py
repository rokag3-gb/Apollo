# -*- coding: utf-8 -*-
"""
Ensemble v2 상세 메트릭 차트 생성
Logical Reads, CPU Time, Execution Time 비교
"""

import json
import matplotlib.pyplot as plt
import numpy as np
import os

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 결과 파일 로드
results_dir = os.path.join(os.path.dirname(__file__), 'results')
detailed_path = os.path.join(results_dir, 'oracle_ensemble_detailed_results.json')

with open(detailed_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

query_summaries = data['query_summaries']

# 차트 저장 디렉토리
charts_dir = os.path.join(results_dir, 'charts')
os.makedirs(charts_dir, exist_ok=True)

# 1. Execution Time: Base vs Optimized (Top 10 improved queries)
fig, ax = plt.subplots(figsize=(14, 8))

# 개선율 기준 정렬
improved_queries = [q for q in query_summaries if q['oracle_mean_speedup'] > 1.05]
improved_queries.sort(key=lambda x: x['oracle_mean_speedup'], reverse=True)
top_10 = improved_queries[:10]

query_labels = [f"Q{q['query_idx']}" for q in top_10]
baseline_times = [q['baseline_metrics']['elapsed_time_ms'] for q in top_10]
optimized_times = [q['oracle_optimized_metrics']['elapsed_time_ms'] for q in top_10]
speedups = [q['oracle_mean_speedup'] for q in top_10]

x = np.arange(len(query_labels))
width = 0.35

bars1 = ax.bar(x - width/2, baseline_times, width, label='Baseline', color='#ff6b6b', alpha=0.8)
bars2 = ax.bar(x + width/2, optimized_times, width, label='Optimized', color='#1dd1a1', alpha=0.8)

ax.set_xlabel('쿼리', fontsize=12, fontweight='bold')
ax.set_ylabel('Execution Time (ms)', fontsize=12, fontweight='bold')
ax.set_title('Top 10 개선 쿼리: Baseline vs Oracle Optimized (Execution Time)', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(query_labels, rotation=45)
ax.legend()
ax.grid(axis='y', alpha=0.3)

# Speedup 값 표시
for i, (bar1, bar2, speedup) in enumerate(zip(bars1, bars2, speedups)):
    height = max(bar1.get_height(), bar2.get_height())
    ax.text(i, height, f'{speedup:.2f}x', ha='center', va='bottom', 
            fontsize=10, fontweight='bold', color='#2ed573')

plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'execution_time_comparison_top10.png'), dpi=300, bbox_inches='tight')
print("[OK] Chart: execution_time_comparison_top10.png")
plt.close()

# 2. Logical Reads 비교 (변화가 있는 쿼리만)
queries_with_reads_change = [q for q in query_summaries 
                              if abs(q['improvement_pct']['logical_reads']) > 1.0]

if queries_with_reads_change:
    fig, ax = plt.subplots(figsize=(12, 6))
    
    query_labels = [f"Q{q['query_idx']}" for q in queries_with_reads_change]
    baseline_reads = [q['baseline_metrics']['logical_reads'] for q in queries_with_reads_change]
    optimized_reads = [q['oracle_optimized_metrics']['logical_reads'] for q in queries_with_reads_change]
    
    x = np.arange(len(query_labels))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, baseline_reads, width, label='Baseline', color='#feca57', alpha=0.8)
    bars2 = ax.bar(x + width/2, optimized_reads, width, label='Optimized', color='#48dbfb', alpha=0.8)
    
    ax.set_xlabel('쿼리', fontsize=12, fontweight='bold')
    ax.set_ylabel('Logical Reads', fontsize=12, fontweight='bold')
    ax.set_title('Logical Reads 비교: Baseline vs Optimized (변화 있는 쿼리)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(query_labels, rotation=45)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, 'logical_reads_comparison.png'), dpi=300, bbox_inches='tight')
    print("[OK] Chart: logical_reads_comparison.png")
    plt.close()
else:
    print("[INFO] No significant logical reads changes")

# 3. CPU Time 비교 (변화가 있는 쿼리)
queries_with_cpu_change = [q for q in query_summaries 
                           if q['baseline_metrics']['cpu_time_ms'] > 0 
                           and abs(q['improvement_pct']['cpu_time']) > 5.0]

if queries_with_cpu_change:
    fig, ax = plt.subplots(figsize=(12, 6))
    
    query_labels = [f"Q{q['query_idx']}" for q in queries_with_cpu_change]
    baseline_cpu = [q['baseline_metrics']['cpu_time_ms'] for q in queries_with_cpu_change]
    optimized_cpu = [q['oracle_optimized_metrics']['cpu_time_ms'] for q in queries_with_cpu_change]
    
    x = np.arange(len(query_labels))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, baseline_cpu, width, label='Baseline', color='#ff9ff3', alpha=0.8)
    bars2 = ax.bar(x + width/2, optimized_cpu, width, label='Optimized', color='#54a0ff', alpha=0.8)
    
    ax.set_xlabel('쿼리', fontsize=12, fontweight='bold')
    ax.set_ylabel('CPU Time (ms)', fontsize=12, fontweight='bold')
    ax.set_title('CPU Time 비교: Baseline vs Optimized (변화 있는 쿼리)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(query_labels, rotation=45)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, 'cpu_time_comparison.png'), dpi=300, bbox_inches='tight')
    print("[OK] Chart: cpu_time_comparison.png")
    plt.close()
else:
    print("[INFO] No significant CPU time changes")

# 4. 개선율 분포 (Execution Time, Logical Reads, CPU Time)
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))

# Execution Time 개선율
time_improvements = [q['improvement_pct']['elapsed_time'] for q in query_summaries]
ax1.hist(time_improvements, bins=20, color='#1dd1a1', alpha=0.7, edgecolor='black')
ax1.axvline(x=0, color='red', linestyle='--', linewidth=2, label='No Change')
ax1.set_xlabel('개선율 (%)', fontsize=11, fontweight='bold')
ax1.set_ylabel('쿼리 수', fontsize=11, fontweight='bold')
ax1.set_title(f'Execution Time 개선율 분포\n평균: {np.mean(time_improvements):.1f}%', 
              fontsize=12, fontweight='bold')
ax1.legend()
ax1.grid(alpha=0.3)

# Logical Reads 개선율
reads_improvements = [q['improvement_pct']['logical_reads'] for q in query_summaries]
ax2.hist(reads_improvements, bins=20, color='#48dbfb', alpha=0.7, edgecolor='black')
ax2.axvline(x=0, color='red', linestyle='--', linewidth=2, label='No Change')
ax2.set_xlabel('개선율 (%)', fontsize=11, fontweight='bold')
ax2.set_ylabel('쿼리 수', fontsize=11, fontweight='bold')
ax2.set_title(f'Logical Reads 개선율 분포\n평균: {np.mean(reads_improvements):.1f}%', 
              fontsize=12, fontweight='bold')
ax2.legend()
ax2.grid(alpha=0.3)

# CPU Time 개선율
cpu_improvements = [q['improvement_pct']['cpu_time'] for q in query_summaries 
                    if q['baseline_metrics']['cpu_time_ms'] > 0]
if cpu_improvements:
    ax3.hist(cpu_improvements, bins=20, color='#54a0ff', alpha=0.7, edgecolor='black')
    ax3.axvline(x=0, color='red', linestyle='--', linewidth=2, label='No Change')
    ax3.set_xlabel('개선율 (%)', fontsize=11, fontweight='bold')
    ax3.set_ylabel('쿼리 수', fontsize=11, fontweight='bold')
    ax3.set_title(f'CPU Time 개선율 분포\n평균: {np.mean(cpu_improvements):.1f}%', 
                  fontsize=12, fontweight='bold')
    ax3.legend()
    ax3.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'improvement_distribution.png'), dpi=300, bbox_inches='tight')
print("[OK] Chart: improvement_distribution.png")
plt.close()

# 5. Metrics Correlation (Speedup vs Baseline Time)
fig, ax = plt.subplots(figsize=(10, 8))

baseline_times = [q['baseline_metrics']['elapsed_time_ms'] for q in query_summaries if q['baseline_metrics']['elapsed_time_ms'] > 0]
speedups = [q['oracle_mean_speedup'] for q in query_summaries if q['baseline_metrics']['elapsed_time_ms'] > 0]
query_types = [q['query_type'] for q in query_summaries if q['baseline_metrics']['elapsed_time_ms'] > 0]

# 쿼리 타입별 색상
type_colors = {
    'SIMPLE': '#1dd1a1',
    'SUBQUERY': '#48dbfb',
    'TOP': '#feca57',
    'JOIN_HEAVY': '#ff6b6b',
    'CTE': '#54a0ff',
    'AGGREGATE': '#ff9ff3',
    'WINDOW': '#a29bfe'
}

for qtype in set(query_types):
    indices = [i for i, t in enumerate(query_types) if t == qtype]
    x_vals = [baseline_times[i] for i in indices]
    y_vals = [speedups[i] for i in indices]
    ax.scatter(x_vals, y_vals, label=qtype, color=type_colors.get(qtype, '#95a5a6'), 
               s=100, alpha=0.7, edgecolors='black')

ax.axhline(y=1.0, color='red', linestyle='--', linewidth=2, alpha=0.5, label='No Improvement')
ax.set_xlabel('Baseline Execution Time (ms)', fontsize=12, fontweight='bold')
ax.set_ylabel('Oracle Speedup', fontsize=12, fontweight='bold')
ax.set_title('Speedup vs Baseline Time (쿼리 타입별)', fontsize=14, fontweight='bold')
ax.set_xscale('log')
ax.set_yscale('log')
ax.legend(loc='best')
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'speedup_vs_baseline.png'), dpi=300, bbox_inches='tight')
print("[OK] Chart: speedup_vs_baseline.png")
plt.close()

print(f"\n[SUCCESS] All detailed charts generated!")
print(f"Location: {charts_dir}")

