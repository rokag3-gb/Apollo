# -*- coding: utf-8 -*-
"""
SAC v1 평가 결과 차트 생성 스크립트
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
from pathlib import Path
from collections import Counter

# 한글 폰트 설정
mpl.rcParams['font.family'] = 'Malgun Gothic'  # Windows
mpl.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

# 출력 디렉토리 설정
OUTPUT_DIR = Path("Apollo.ML/RLQO/SAC_v1/charts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 데이터 로드
with open("Apollo.ML/sac_v1_realdb_eval.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 80)
print("SAC v1 평가 차트 생성 중...")
print("=" * 80)

# 데이터 전처리
# Query별 통계 계산
query_stats = {}
for result in data['detailed_results']:
    query_idx = result['query_idx']
    speedup = result['speedup']
    
    if query_idx not in query_stats:
        query_stats[query_idx] = {'speedups': [], 'actions': []}
    
    query_stats[query_idx]['speedups'].append(speedup)
    if result['action']:
        query_stats[query_idx]['actions'].append(result['action'])

# Query별 평균 계산
query_summary = []
for query_idx in range(30):
    speedups = query_stats[query_idx]['speedups']
    query_summary.append({
        'query_idx': query_idx,
        'avg_speedup': np.mean(speedups),
        'max_speedup': np.max(speedups),
        'std_speedup': np.std(speedups),
        'action_count': len(query_stats[query_idx]['actions'])
    })

# 전체 통계
all_speedups = [r['speedup'] for r in data['detailed_results']]
speedups_improved = [s for s in all_speedups if s > 1.0]

# ============================================================================
# 차트 1: 전체 성능 지표
# ============================================================================
print("\n[1/6] 전체 성능 지표 차트 생성 중...")

fig, axes = plt.subplots(2, 2, figsize=(12, 10))
fig.suptitle('SAC v1 RealDB: 전체 성능 지표', fontsize=16, fontweight='bold')

# 1. 주요 통계
ax = axes[0, 0]
stats = {
    'Mean\nSpeedup': np.mean(all_speedups),
    'Median\nSpeedup': np.median(all_speedups),
    'Max\nSpeedup': np.max(all_speedups),
    'Std\nDev': np.std(all_speedups)
}
bars = ax.bar(stats.keys(), stats.values(), color=['#3498db', '#2ecc71', '#e74c3c', '#f39c12'], 
              alpha=0.8, edgecolor='black')
ax.set_title('주요 통계', fontsize=12, fontweight='bold')
ax.set_ylabel('Value', fontsize=10)
ax.grid(axis='y', alpha=0.3)
for bar, val in zip(bars, stats.values()):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{val:.2f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

# 2. 성능 분포
ax = axes[0, 1]
categories = ['Excellent\n(≥2.0x)', 'Good\n(1.5-2.0x)', 'Moderate\n(1.05-1.5x)', 'Neutral\n(1.0x)']
excellent = sum(1 for s in all_speedups if s >= 2.0)
good = sum(1 for s in all_speedups if 1.5 <= s < 2.0)
moderate = sum(1 for s in all_speedups if 1.05 <= s < 1.5)
neutral = sum(1 for s in all_speedups if s == 1.0)
counts = [excellent, good, moderate, neutral]
colors = ['#2ecc71', '#3498db', '#f39c12', '#95a5a6']
bars = ax.bar(categories, counts, color=colors, alpha=0.8, edgecolor='black')
ax.set_title('성능 카테고리 분포', fontsize=12, fontweight='bold')
ax.set_ylabel('Count', fontsize=10)
ax.grid(axis='y', alpha=0.3)
for bar, count in zip(bars, counts):
    height = bar.get_height()
    pct = count / len(all_speedups) * 100
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{count}\n({pct:.1f}%)', ha='center', va='bottom', fontsize=8, fontweight='bold')

# 3. Win Rate
ax = axes[1, 0]
win_count = sum(1 for s in all_speedups if s > 1.0)
lose_count = sum(1 for s in all_speedups if s == 1.0)
sizes = [win_count, lose_count]
labels = [f'Improved\n{win_count} ({win_count/len(all_speedups)*100:.1f}%)', 
          f'Neutral\n{lose_count} ({lose_count/len(all_speedups)*100:.1f}%)']
colors_pie = ['#2ecc71', '#95a5a6']
ax.pie(sizes, labels=labels, colors=colors_pie, autopct='', startangle=90,
       textprops={'fontsize': 10, 'fontweight': 'bold'})
ax.set_title('Win Rate', fontsize=12, fontweight='bold')

# 4. Action Application Rate
ax = axes[1, 1]
action_applied = sum(1 for r in data['detailed_results'] if r['action'] is not None)
no_action = len(data['detailed_results']) - action_applied
sizes = [action_applied, no_action]
labels = [f'Action Applied\n{action_applied} ({action_applied/len(data["detailed_results"])*100:.1f}%)',
          f'NO_ACTION\n{no_action} ({no_action/len(data["detailed_results"])*100:.1f}%)']
colors_pie = ['#9b59b6', '#95a5a6']
ax.pie(sizes, labels=labels, colors=colors_pie, autopct='', startangle=90,
       textprops={'fontsize': 10, 'fontweight': 'bold'})
ax.set_title('Action Application Rate', fontsize=12, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'overall_statistics.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'overall_statistics.png'}")

# ============================================================================
# 차트 2: Query별 평균 Speedup
# ============================================================================
print("\n[2/6] Query별 평균 Speedup 차트 생성 중...")

fig, ax = plt.subplots(figsize=(16, 6))

query_indices = [q['query_idx'] for q in query_summary]
avg_speedups = [q['avg_speedup'] for q in query_summary]
avg_speedups_clean = [min(s, 25) for s in avg_speedups]  # 극단값 제한

colors = ['#2ecc71' if s >= 2.0 else '#3498db' if s > 1.0 else '#95a5a6' for s in avg_speedups]
bars = ax.bar(query_indices, avg_speedups_clean, color=colors, alpha=0.8, edgecolor='black')

ax.axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='Baseline (1.0x)')
ax.axhline(y=2.0, color='orange', linestyle=':', linewidth=2, label='Excellent (2.0x)')
ax.set_xlabel('Query Index', fontsize=12, fontweight='bold')
ax.set_ylabel('Average Speedup (x)', fontsize=12, fontweight='bold')
ax.set_title('SAC v1: Query별 평균 Speedup', fontsize=14, fontweight='bold')
ax.set_xticks(query_indices)
ax.legend()
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, 27)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'speedup_by_query.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'speedup_by_query.png'}")

# ============================================================================
# 차트 3: Top 5 Best Queries
# ============================================================================
print("\n[3/6] Top 5 Best Queries 차트 생성 중...")

query_summary_sorted = sorted(query_summary, key=lambda x: x['avg_speedup'], reverse=True)
top_5 = query_summary_sorted[:5]

fig, ax = plt.subplots(figsize=(10, 6))

y_pos = np.arange(len(top_5))
speedups = [q['avg_speedup'] for q in top_5]
query_labels = [f"Query {q['query_idx']}" for q in top_5]

bars = ax.barh(y_pos, speedups, color='#2ecc71', alpha=0.8, edgecolor='black')

ax.set_yticks(y_pos)
ax.set_yticklabels(query_labels, fontsize=10)
ax.invert_yaxis()
ax.set_xlabel('Average Speedup (x)', fontsize=12, fontweight='bold')
ax.set_title('SAC v1: Top 5 Best Performing Queries', fontsize=14, fontweight='bold')
ax.grid(axis='x', alpha=0.3)

# 값 표시
for bar, q in zip(bars, top_5):
    width = bar.get_width()
    label = f'{q["avg_speedup"]:.2f}x (Max: {q["max_speedup"]:.2f}x)'
    ax.text(width + 0.3, bar.get_y() + bar.get_height()/2.,
            label, ha='left', va='center', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'top_5_best_queries.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'top_5_best_queries.png'}")

# ============================================================================
# 차트 4: Speedup 분포 히스토그램
# ============================================================================
print("\n[4/6] Speedup 분포 히스토그램 생성 중...")

# 극단값 제외
all_speedups_clean = [s for s in all_speedups if s <= 25]

fig, ax = plt.subplots(figsize=(10, 6))

ax.hist(all_speedups_clean, bins=50, color='#3498db', alpha=0.7, edgecolor='black')
ax.axvline(x=1.0, color='green', linestyle='--', linewidth=2, label='Baseline (1.0x)')
ax.axvline(x=np.mean(all_speedups_clean), color='red', linestyle='--', 
           linewidth=2, label=f'Mean: {np.mean(all_speedups_clean):.2f}x')
ax.set_xlabel('Speedup (x)', fontsize=12, fontweight='bold')
ax.set_ylabel('Frequency', fontsize=12)
ax.set_title('SAC v1: Speedup 분포 (900 executions)', fontsize=14, fontweight='bold')
ax.legend()
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'speedup_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'speedup_distribution.png'}")

# ============================================================================
# 차트 5: Episode별 성능 추이
# ============================================================================
print("\n[5/6] Episode별 성능 추이 차트 생성 중...")

# Episode별 평균 speedup 계산
episode_stats = {}
for result in data['detailed_results']:
    episode = result['episode']
    speedup = result['speedup']
    
    if episode not in episode_stats:
        episode_stats[episode] = []
    episode_stats[episode].append(speedup)

episodes = sorted(episode_stats.keys())
mean_speedups = [np.mean(episode_stats[e]) for e in episodes]

fig, ax = plt.subplots(figsize=(12, 6))

ax.plot(episodes, mean_speedups, marker='o', linewidth=2, markersize=4, 
        color='#3498db', label='Mean Speedup')
ax.axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='Baseline (1.0x)')
ax.fill_between(episodes, 1.0, mean_speedups, where=[s > 1.0 for s in mean_speedups],
                alpha=0.3, color='green', label='Improvement')

ax.set_xlabel('Episode', fontsize=12, fontweight='bold')
ax.set_ylabel('Mean Speedup (x)', fontsize=12, fontweight='bold')
ax.set_title('SAC v1: Episode별 평균 Speedup 추이', fontsize=14, fontweight='bold')
ax.legend()
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'speedup_over_episodes.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'speedup_over_episodes.png'}")

# ============================================================================
# 차트 6: Query별 Action Application Rate
# ============================================================================
print("\n[6/6] Query별 Action Application Rate 차트 생성 중...")

query_action_rates = [(q['query_idx'], q['action_count'] / data['episodes'] * 100) 
                      for q in query_summary]

fig, ax = plt.subplots(figsize=(16, 6))

query_indices = [q[0] for q in query_action_rates]
action_rates = [q[1] for q in query_action_rates]

colors = ['#9b59b6' if r > 50 else '#3498db' if r > 0 else '#95a5a6' for r in action_rates]
bars = ax.bar(query_indices, action_rates, color=colors, alpha=0.8, edgecolor='black')

ax.set_xlabel('Query Index', fontsize=12, fontweight='bold')
ax.set_ylabel('Action Application Rate (%)', fontsize=12, fontweight='bold')
ax.set_title('SAC v1: Query별 Action 적용률', fontsize=14, fontweight='bold')
ax.set_xticks(query_indices)
ax.set_ylim(0, 110)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'action_rate_by_query.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'action_rate_by_query.png'}")

# ============================================================================
# 완료
# ============================================================================
print("\n" + "=" * 80)
print("✅ 모든 차트 생성 완료!")
print(f"✅ 저장 위치: {OUTPUT_DIR.absolute()}")
print("=" * 80)

# 생성된 파일 목록
print("\n생성된 파일:")
for file in sorted(OUTPUT_DIR.glob("*.png")):
    print(f"  - {file.name}")

# 통계 요약
print("\n📊 통계 요약:")
print(f"  전체 실행 횟수: {len(all_speedups)}")
print(f"  평균 Speedup: {np.mean(all_speedups):.3f}x")
print(f"  중앙값 Speedup: {np.median(all_speedups):.3f}x")
print(f"  표준편차: {np.std(all_speedups):.3f}")
print(f"  최대 Speedup: {np.max(all_speedups):.3f}x 🔥")
print(f"  Win Rate: {win_count}/{len(all_speedups)} ({win_count/len(all_speedups)*100:.1f}%)")
print(f"  Action Application Rate: {action_applied}/{len(data['detailed_results'])} ({action_applied/len(data['detailed_results'])*100:.1f}%)")

