# -*- coding: utf-8 -*-
"""
DDPG v1 평가 결과 차트 생성 스크립트
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
from pathlib import Path

# 한글 폰트 설정
mpl.rcParams['font.family'] = 'Malgun Gothic'  # Windows
mpl.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

# 출력 디렉토리 설정
OUTPUT_DIR = Path("Apollo.ML/RLQO/DDPG_v1/charts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 데이터 로드
with open("Apollo.ML/ddpg_v1_sim_eval_detailed.json", "r", encoding="utf-8") as f:
    sim_data = json.load(f)

with open("Apollo.ML/ddpg_v1_realdb_eval_detailed.json", "r", encoding="utf-8") as f:
    realdb_data = json.load(f)

print("=" * 80)
print("DDPG v1 평가 차트 생성 중...")
print("=" * 80)

# ============================================================================
# 차트 1: 모델 성능 비교 (Sim vs RealDB)
# ============================================================================
print("\n[1/6] 모델 성능 비교 차트 생성 중...")

fig, axes = plt.subplots(2, 3, figsize=(15, 10))
fig.suptitle('DDPG v1 모델 성능 비교 (Sim vs RealDB)', fontsize=16, fontweight='bold')

metrics = [
    ('mean_speedup', 'Mean Speedup', 'x'),
    ('median_speedup', 'Median Speedup', 'x'),
    ('max_speedup', 'Max Speedup', 'x'),
    ('std_speedup', 'Std Deviation', 'σ'),
    ('mean_improvement_pct', 'Mean Improvement', '%'),
]

model_names = ['Simulation', 'RealDB']
sim_values = [sim_data['overall'][metric] for metric, _, _ in metrics]
realdb_values = [realdb_data['overall'][metric] for metric, _, _ in metrics]

for idx, (metric, title, unit) in enumerate(metrics):
    ax = axes[idx // 3, idx % 3]
    
    values = [sim_values[idx], realdb_values[idx]]
    colors = ['#3498db', '#e74c3c']
    bars = ax.bar(model_names, values, color=colors, alpha=0.8, edgecolor='black')
    
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_ylabel(f'Value ({unit})', fontsize=10)
    ax.set_ylim(0, max(values) * 1.2 if max(values) > 0 else 10)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 값 표시
    for bar, val in zip(bars, values):
        height = bar.get_height()
        label = f'{val:.2f}'
        ax.text(bar.get_x() + bar.get_width()/2., height,
                label, ha='center', va='bottom', fontsize=10, fontweight='bold')

# 분포 차트
ax = axes[1, 2]
categories = ['Excellent\n(≥2.0x)', 'Good\n(1.5-2.0x)', 'Neutral\n(0.9-1.5x)', 'Degraded\n(<0.9x)']
sim_dist = [sim_data['distribution'].get('excellent', 0), 
            sim_data['distribution'].get('good', 0),
            sim_data['distribution'].get('neutral', 0),
            sim_data['distribution'].get('degraded', 0)]
realdb_dist = [realdb_data['distribution'].get('excellent', 0),
               realdb_data['distribution'].get('good', 0),
               realdb_data['distribution'].get('neutral', 0),
               realdb_data['distribution'].get('degraded', 0)]

x = np.arange(len(categories))
width = 0.35
bars1 = ax.bar(x - width/2, sim_dist, width, label='Sim', color='#3498db', alpha=0.8, edgecolor='black')
bars2 = ax.bar(x + width/2, realdb_dist, width, label='RealDB', color='#e74c3c', alpha=0.8, edgecolor='black')

ax.set_title('Performance Distribution', fontsize=12, fontweight='bold')
ax.set_ylabel('Count', fontsize=10)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=8)
ax.legend()
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'model_comparison.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'model_comparison.png'}")

# ============================================================================
# 차트 2: Query별 Speedup 비교 (Sim vs RealDB)
# ============================================================================
print("\n[2/6] Query별 Speedup 비교 차트 생성 중...")

fig, ax = plt.subplots(figsize=(16, 6))

query_indices = [q['query_idx'] for q in sim_data['query_summary']]
sim_speedups = [q['avg_speedup'] for q in sim_data['query_summary']]
realdb_speedups = [q['avg_speedup'] for q in realdb_data['query_summary']]

# Speedup 값 정제 (극단값 처리)
sim_speedups_clean = [min(s, 20) for s in sim_speedups]
realdb_speedups_clean = [min(s, 20) for s in realdb_speedups]

x = np.arange(len(query_indices))
width = 0.35

bars1 = ax.bar(x - width/2, sim_speedups_clean, width, label='Simulation', 
               color='#3498db', alpha=0.8, edgecolor='black')
bars2 = ax.bar(x + width/2, realdb_speedups_clean, width, label='RealDB', 
               color='#e74c3c', alpha=0.8, edgecolor='black')

ax.axhline(y=1.0, color='green', linestyle='--', linewidth=2, label='Baseline (1.0x)')
ax.axhline(y=2.0, color='orange', linestyle=':', linewidth=2, label='Excellent (2.0x)')
ax.set_xlabel('Query Index', fontsize=12, fontweight='bold')
ax.set_ylabel('Speedup (x)', fontsize=12, fontweight='bold')
ax.set_title('DDPG v1: Query별 Speedup 비교 (Sim vs RealDB)', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(query_indices, rotation=45, ha='right')
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.set_ylim(0, 22)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'speedup_by_query.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'speedup_by_query.png'}")

# ============================================================================
# 차트 3: Top 5 Best Queries (RealDB)
# ============================================================================
print("\n[3/6] Top 5 Best Queries 차트 생성 중...")

# Speedup 기준 상위 5개 추출
sorted_queries = sorted(realdb_data['query_summary'], key=lambda x: x['avg_speedup'], reverse=True)
top_5 = sorted_queries[:5]

fig, ax = plt.subplots(figsize=(10, 6))

y_pos = np.arange(len(top_5))
speedups = [q['avg_speedup'] for q in top_5]
query_names = [f"Q{q['query_idx']}: {q['query_name'][:30]}..." for q in top_5]

bars = ax.barh(y_pos, speedups, color='#2ecc71', alpha=0.8, edgecolor='black')

ax.set_yticks(y_pos)
ax.set_yticklabels(query_names, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel('Speedup (x)', fontsize=12, fontweight='bold')
ax.set_title('DDPG v1 RealDB: Top 5 Best Performing Queries', fontsize=14, fontweight='bold')
ax.grid(axis='x', alpha=0.3, linestyle='--')

# 값 표시
for bar, q in zip(bars, top_5):
    width = bar.get_width()
    improvement = q['improvement_pct']
    label = f'{q["avg_speedup"]:.2f}x (+{improvement:.0f}%)'
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

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle('DDPG v1: Speedup 분포', fontsize=16, fontweight='bold')

# Sim
sim_speedups_all = [q['avg_speedup'] for q in sim_data['query_summary']]
sim_speedups_valid = [s for s in sim_speedups_all if s <= 20]  # 극단값 제외
axes[0].hist(sim_speedups_valid, bins=20, color='#3498db', alpha=0.7, edgecolor='black')
axes[0].axvline(x=1.0, color='green', linestyle='--', linewidth=2, label='Baseline (1.0x)')
axes[0].axvline(x=sim_data['overall']['mean_speedup'], color='red', linestyle='--', 
                linewidth=2, label=f'Mean: {sim_data["overall"]["mean_speedup"]:.2f}x')
axes[0].set_xlabel('Speedup (x)', fontsize=12)
axes[0].set_ylabel('Frequency', fontsize=12)
axes[0].set_title('Simulation', fontsize=12, fontweight='bold')
axes[0].legend()
axes[0].grid(axis='y', alpha=0.3)

# RealDB
realdb_speedups_all = [q['avg_speedup'] for q in realdb_data['query_summary']]
realdb_speedups_valid = [s for s in realdb_speedups_all if s <= 20]
axes[1].hist(realdb_speedups_valid, bins=20, color='#e74c3c', alpha=0.7, edgecolor='black')
axes[1].axvline(x=1.0, color='green', linestyle='--', linewidth=2, label='Baseline (1.0x)')
axes[1].axvline(x=realdb_data['overall']['mean_speedup'], color='red', linestyle='--', 
                linewidth=2, label=f'Mean: {realdb_data["overall"]["mean_speedup"]:.2f}x')
axes[1].set_xlabel('Speedup (x)', fontsize=12)
axes[1].set_ylabel('Frequency', fontsize=12)
axes[1].set_title('RealDB', fontsize=12, fontweight='bold')
axes[1].legend()
axes[1].grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'speedup_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'speedup_distribution.png'}")

# ============================================================================
# 차트 5: 성능 카테고리 분포 (Pie Chart)
# ============================================================================
print("\n[5/6] 성능 카테고리 분포 차트 생성 중...")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('DDPG v1: Performance Category Distribution', fontsize=16, fontweight='bold')

colors = ['#2ecc71', '#3498db', '#95a5a6', '#e74c3c']
labels = ['Excellent\n(≥2.0x)', 'Good\n(1.5-2.0x)', 'Neutral\n(0.9-1.5x)', 'Degraded\n(<0.9x)']

# Sim
sim_dist_values = [sim_data['distribution'].get('excellent', 0),
                   sim_data['distribution'].get('good', 0),
                   sim_data['distribution'].get('neutral', 0),
                   sim_data['distribution'].get('degraded', 0)]
# 0인 값 제거
sim_labels = [labels[i] for i, v in enumerate(sim_dist_values) if v > 0]
sim_values = [v for v in sim_dist_values if v > 0]
sim_colors = [colors[i] for i, v in enumerate(sim_dist_values) if v > 0]
sim_explode = tuple([0.05 if i == 0 else 0 for i in range(len(sim_values))])

axes[0].pie(sim_values, labels=sim_labels, autopct='%1.1f%%', colors=sim_colors,
            explode=sim_explode, startangle=90, textprops={'fontsize': 10, 'fontweight': 'bold'})
axes[0].set_title('Simulation', fontsize=12, fontweight='bold')

# RealDB
realdb_dist_values = [realdb_data['distribution'].get('excellent', 0),
                      realdb_data['distribution'].get('good', 0),
                      realdb_data['distribution'].get('neutral', 0),
                      realdb_data['distribution'].get('degraded', 0)]
realdb_labels = [labels[i] for i, v in enumerate(realdb_dist_values) if v > 0]
realdb_values = [v for v in realdb_dist_values if v > 0]
realdb_colors = [colors[i] for i, v in enumerate(realdb_dist_values) if v > 0]
realdb_explode = tuple([0.05 if i == 0 else 0 for i in range(len(realdb_values))])

axes[1].pie(realdb_values, labels=realdb_labels, autopct='%1.1f%%', colors=realdb_colors,
            explode=realdb_explode, startangle=90, textprops={'fontsize': 10, 'fontweight': 'bold'})
axes[1].set_title('RealDB', fontsize=12, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'performance_categories.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'performance_categories.png'}")

# ============================================================================
# 차트 6: Action Application Frequency
# ============================================================================
print("\n[6/6] Action Application Frequency 차트 생성 중...")

fig, ax = plt.subplots(figsize=(10, 6))

# 액션이 적용된 쿼리 수 계산
sim_action_count = sum(1 for q in sim_data['query_summary'] if q['action'] is not None)
sim_no_action_count = len(sim_data['query_summary']) - sim_action_count
realdb_action_count = sum(1 for q in realdb_data['query_summary'] if q['action'] is not None)
realdb_no_action_count = len(realdb_data['query_summary']) - realdb_action_count

categories = ['Action Applied', 'NO_ACTION']
sim_counts = [sim_action_count, sim_no_action_count]
realdb_counts = [realdb_action_count, realdb_no_action_count]

x = np.arange(len(categories))
width = 0.35

bars1 = ax.bar(x - width/2, sim_counts, width, label='Simulation', 
               color='#3498db', alpha=0.8, edgecolor='black')
bars2 = ax.bar(x + width/2, realdb_counts, width, label='RealDB', 
               color='#e74c3c', alpha=0.8, edgecolor='black')

ax.set_ylabel('Query Count', fontsize=12, fontweight='bold')
ax.set_title('DDPG v1: Action Application Frequency', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.legend()
ax.grid(axis='y', alpha=0.3)

# 값 표시
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}', ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'action_frequency.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'action_frequency.png'}")

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

