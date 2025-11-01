# -*- coding: utf-8 -*-
"""
Ensemble v2 최종 보고서용 차트 생성
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
oracle_path = os.path.join(results_dir, 'oracle_ensemble_results.json')

with open(oracle_path, 'r', encoding='utf-8') as f:
    oracle_data = json.load(f)

# 차트 저장 디렉토리
charts_dir = os.path.join(results_dir, 'charts')
os.makedirs(charts_dir, exist_ok=True)

# 1. 전체 성능 비교 (Weighted vs Oracle)
fig, ax = plt.subplots(figsize=(10, 6))

methods = ['Weighted\n(Original)', 'Weighted\n(0.5 penalty)', 'Weighted\n(0.2 penalty)', 'Oracle\nEnsemble']
mean_speedups = [1.051, 1.346, 1.396, oracle_data['overall']['oracle_mean_speedup']]
win_rates = [19.7, 15.3, 11.7, oracle_data['overall']['oracle_win_rate'] * 100]

x = np.arange(len(methods))
width = 0.35

bars1 = ax.bar(x - width/2, mean_speedups, width, label='평균 Speedup', color=['#ff6b6b', '#feca57', '#48dbfb', '#1dd1a1'])
bars2_ax = ax.twinx()
bars2 = bars2_ax.bar(x + width/2, win_rates, width, label='Win Rate (%)', color=['#ff9ff3', '#feca57', '#48dbfb', '#54a0ff'], alpha=0.7)

ax.set_xlabel('앙상블 방식', fontsize=12, fontweight='bold')
ax.set_ylabel('평균 Speedup (배)', fontsize=12, fontweight='bold')
bars2_ax.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
ax.set_title('Ensemble v2 성능 비교: Weighted Voting vs Oracle Ensemble', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(methods)
ax.legend(loc='upper left')
bars2_ax.legend(loc='upper right')
ax.grid(axis='y', alpha=0.3)

# 값 표시
for bar in bars1:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.2f}x', ha='center', va='bottom', fontweight='bold')

for bar in bars2:
    height = bar.get_height()
    bars2_ax.text(bar.get_x() + bar.get_width()/2., height,
                  f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'performance_comparison.png'), dpi=300, bbox_inches='tight')
print("[OK] Chart 1: performance_comparison.png")
plt.close()

# 2. 쿼리 타입별 성능
fig, ax = plt.subplots(figsize=(12, 6))

type_stats = oracle_data['overall']['by_query_type']
types = list(type_stats.keys())
speedups = [type_stats[t]['mean_speedup'] for t in types]
win_rates = [type_stats[t]['win_rate'] * 100 for t in types]

# 정렬 (speedup 기준 내림차순)
sorted_indices = np.argsort(speedups)[::-1]
types = [types[i] for i in sorted_indices]
speedups = [speedups[i] for i in sorted_indices]
win_rates = [win_rates[i] for i in sorted_indices]

x = np.arange(len(types))
width = 0.35

bars1 = ax.bar(x - width/2, speedups, width, label='평균 Speedup', color='#1dd1a1')
bars2_ax = ax.twinx()
bars2 = bars2_ax.bar(x + width/2, win_rates, width, label='Win Rate (%)', color='#54a0ff', alpha=0.7)

ax.set_xlabel('쿼리 타입', fontsize=12, fontweight='bold')
ax.set_ylabel('평균 Speedup (배)', fontsize=12, fontweight='bold')
bars2_ax.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
ax.set_title('Oracle Ensemble: 쿼리 타입별 성능', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(types, rotation=45, ha='right')
ax.legend(loc='upper left')
bars2_ax.legend(loc='upper right')
ax.grid(axis='y', alpha=0.3)
ax.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label='Baseline')

# 값 표시
for bar in bars1:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.2f}x', ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'query_type_performance.png'), dpi=300, bbox_inches='tight')
print("[OK] Chart 2: query_type_performance.png")
plt.close()

# 3. 모델 선택 분포
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# 파이 차트
model_counts = oracle_data['overall']['model_selection_counts']
models = list(model_counts.keys())
counts = list(model_counts.values())
colors = ['#1dd1a1', '#54a0ff', '#ff6b6b', '#feca57']

wedges, texts, autotexts = ax1.pie(counts, labels=models, autopct='%1.1f%%',
                                     colors=colors[:len(models)], startangle=90,
                                     textprops={'fontsize': 12, 'fontweight': 'bold'})
ax1.set_title('Oracle Ensemble: 모델 선택 분포', fontsize=14, fontweight='bold')

# 바 차트
x = np.arange(len(models))
bars = ax2.bar(x, counts, color=colors[:len(models)])
ax2.set_xlabel('모델', fontsize=12, fontweight='bold')
ax2.set_ylabel('선택된 쿼리 수', fontsize=12, fontweight='bold')
ax2.set_title('모델별 선택 횟수', fontsize=14, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(models)
ax2.grid(axis='y', alpha=0.3)

# 값 표시
for bar in bars:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'{int(height)}개\n({height/30*100:.1f}%)',
             ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'model_selection_distribution.png'), dpi=300, bbox_inches='tight')
print("[OK] Chart 3: model_selection_distribution.png")
plt.close()

# 4. 쿼리별 Speedup (30개 전체)
fig, ax = plt.subplots(figsize=(16, 8))

query_summaries = oracle_data['query_summaries']
query_indices = [s['query_idx'] for s in query_summaries]
speedups = [s['oracle_mean_speedup'] for s in query_summaries]
colors_list = ['#1dd1a1' if s > 1.05 else '#feca57' if s >= 0.95 else '#ff6b6b' for s in speedups]

bars = ax.bar(query_indices, speedups, color=colors_list, edgecolor='black', linewidth=0.5)
ax.axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='Baseline (1.0x)')
ax.axhline(y=1.05, color='green', linestyle=':', linewidth=1, alpha=0.5, label='개선 기준 (1.05x)')
ax.axhline(y=0.95, color='orange', linestyle=':', linewidth=1, alpha=0.5, label='저하 기준 (0.95x)')

ax.set_xlabel('쿼리 인덱스', fontsize=12, fontweight='bold')
ax.set_ylabel('Oracle 평균 Speedup', fontsize=12, fontweight='bold')
ax.set_title('Oracle Ensemble: 전체 30개 쿼리 성능 (개선: 초록, 유지: 노랑, 저하: 빨강)', fontsize=14, fontweight='bold')
ax.set_xticks(query_indices)
ax.set_xticklabels(query_indices, fontsize=9)
ax.legend(loc='upper right')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'all_queries_speedup.png'), dpi=300, bbox_inches='tight')
print("[OK] Chart 4: all_queries_speedup.png")
plt.close()

print("\n[SUCCESS] All charts generated!")
print(f"Location: {charts_dir}")

