# -*- coding: utf-8 -*-
"""
DQN v4 평가 결과 차트 생성 스크립트
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
from pathlib import Path

# 한글 폰트 설정
mpl.rcParams['font.family'] = 'Malgun Gothic'  # Windows
mpl.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

# 출력 디렉토리 설정
OUTPUT_DIR = Path("Apollo.ML/RLQO/DQN_v4/charts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 데이터 로드
results_df = pd.read_csv("Apollo.ML/artifacts/RLQO/evaluation_results_v4_20251028_211549.csv")
summary_df = pd.read_csv("Apollo.ML/artifacts/RLQO/evaluation_summary_v4_20251028_211549.csv")

# 모델별 데이터 분리
sim_data = results_df[results_df.index < 30].copy()
final_data = results_df[results_df.index >= 30].copy()

sim_data['model'] = 'DQN v4 Sim'
final_data['model'] = 'DQN v4 Final'

# Query index 재설정
final_data['query_idx'] = final_data['query_idx'].values

print("=" * 80)
print("DQN v4 평가 차트 생성 중...")
print("=" * 80)

# ============================================================================
# 차트 1: 모델 성능 비교 (주요 메트릭)
# ============================================================================
print("\n[1/7] 모델 성능 비교 차트 생성 중...")

fig, axes = plt.subplots(2, 3, figsize=(15, 10))
fig.suptitle('DQN v4 모델 성능 비교 (Sim vs Final)', fontsize=16, fontweight='bold')

metrics = [
    ('win_rate', 'Win Rate', '%'),
    ('avg_speedup', 'Average Speedup', 'x'),
    ('avg_compatibility', 'Compatibility', '%'),
    ('avg_consistency', 'Consistency', 'score'),
    ('failure_rate', 'Failure Rate', '%'),
    ('avg_improvement', 'Avg Improvement', '%')
]

for idx, (col, title, unit) in enumerate(metrics):
    ax = axes[idx // 3, idx % 3]
    
    values = summary_df[col].values
    # inf 값 처리
    values_clean = np.where(np.isinf(values), 10.0, values)  # inf는 10으로 표시
    
    if 'rate' in col or 'compatibility' in col or 'consistency' in col:
        values_clean = values_clean * 100  # 퍼센트로 변환
    
    colors = ['#3498db', '#e74c3c']
    bars = ax.bar(summary_df['model_name'], values_clean, color=colors, alpha=0.8, edgecolor='black')
    
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_ylabel(f'Value ({unit})', fontsize=10)
    ax.set_ylim(0, max(values_clean) * 1.2 if max(values_clean) > 0 else 100)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 값 표시
    for bar, val in zip(bars, values_clean):
        height = bar.get_height()
        if np.isinf(values[list(bars).index(bar)]):
            label = 'inf'
        elif 'rate' in col or 'compatibility' in col or 'consistency' in col:
            label = f'{val:.1f}%'
        else:
            label = f'{val:.2f}'
        ax.text(bar.get_x() + bar.get_width()/2., height,
                label, ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'model_comparison.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'model_comparison.png'}")

# ============================================================================
# 차트 2: Query별 Speedup 비교 (Sim vs Final)
# ============================================================================
print("\n[2/7] Query별 Speedup 비교 차트 생성 중...")

# Speedup 값 정제 (inf, 극단값 처리)
sim_data['speedup_clean'] = sim_data['speedup'].apply(
    lambda x: 50 if np.isinf(x) or x > 50 else (0.01 if x < 0.01 else x)
)
final_data['speedup_clean'] = final_data['speedup'].apply(
    lambda x: 50 if np.isinf(x) or x > 50 else (0.01 if x < 0.01 else x)
)

fig, ax = plt.subplots(figsize=(16, 6))

query_indices = sim_data['query_idx'].unique()
x = np.arange(len(query_indices))
width = 0.35

sim_speedups = [sim_data[sim_data['query_idx'] == idx]['speedup_clean'].iloc[0] for idx in query_indices]
final_speedups = [final_data[final_data['query_idx'] == idx]['speedup_clean'].iloc[0] for idx in query_indices]

bars1 = ax.bar(x - width/2, sim_speedups, width, label='DQN v4 Sim', 
               color='#3498db', alpha=0.8, edgecolor='black')
bars2 = ax.bar(x + width/2, final_speedups, width, label='DQN v4 Final', 
               color='#e74c3c', alpha=0.8, edgecolor='black')

ax.axhline(y=1.0, color='green', linestyle='--', linewidth=2, label='Baseline (1.0x)')
ax.set_xlabel('Query Index', fontsize=12, fontweight='bold')
ax.set_ylabel('Speedup (x)', fontsize=12, fontweight='bold')
ax.set_title('DQN v4: Query별 Speedup 비교 (Sim vs Final)', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(query_indices, rotation=45, ha='right')
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.set_ylim(0, 55)

# inf 표시
for idx, (bar1, bar2) in enumerate(zip(bars1, bars2)):
    if np.isinf(sim_data.iloc[idx]['speedup']):
        ax.text(bar1.get_x() + bar1.get_width()/2., bar1.get_height() + 1,
                '∞', ha='center', va='bottom', fontsize=10, fontweight='bold', color='blue')
    if np.isinf(final_data.iloc[idx]['speedup']):
        ax.text(bar2.get_x() + bar2.get_width()/2., bar2.get_height() + 1,
                '∞', ha='center', va='bottom', fontsize=10, fontweight='bold', color='red')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'speedup_by_query.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'speedup_by_query.png'}")

# ============================================================================
# 차트 3: Top 10 Best Queries (Final)
# ============================================================================
print("\n[3/7] Top 10 Best Queries 차트 생성 중...")

# inf 값을 제외하고 정렬
final_valid = final_data[~np.isinf(final_data['speedup']) & ~final_data['failed']].copy()
top_10 = final_valid.nlargest(10, 'speedup')

# inf 값 추가
final_inf = final_data[np.isinf(final_data['speedup'])].copy()
if len(final_inf) > 0:
    final_inf['speedup_display'] = 50
    top_10 = pd.concat([final_inf, top_10]).head(10)
else:
    top_10['speedup_display'] = top_10['speedup']

fig, ax = plt.subplots(figsize=(10, 6))

y_pos = np.arange(len(top_10))
speedups = top_10['speedup_display'] if 'speedup_display' in top_10.columns else top_10['speedup']

bars = ax.barh(y_pos, speedups, color='#2ecc71', alpha=0.8, edgecolor='black')

ax.set_yticks(y_pos)
ax.set_yticklabels([f"Query {idx}" for idx in top_10['query_idx']], fontsize=10)
ax.invert_yaxis()
ax.set_xlabel('Speedup (x)', fontsize=12, fontweight='bold')
ax.set_title('DQN v4 Final: Top 10 Best Performing Queries', fontsize=14, fontweight='bold')
ax.grid(axis='x', alpha=0.3, linestyle='--')

# 값 표시
for idx, (bar, row) in enumerate(zip(bars, top_10.itertuples())):
    width = bar.get_width()
    if np.isinf(row.speedup):
        label = '∞ (0ms)'
    else:
        label = f'{row.speedup:.2f}x'
    ax.text(width + 1, bar.get_y() + bar.get_height()/2.,
            label, ha='left', va='center', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'top_10_best_queries.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'top_10_best_queries.png'}")

# ============================================================================
# 차트 4: Top 10 Worst Queries (Final)
# ============================================================================
print("\n[4/7] Top 10 Worst Queries 차트 생성 중...")

worst_10 = final_data.nsmallest(10, 'speedup')

fig, ax = plt.subplots(figsize=(10, 6))

y_pos = np.arange(len(worst_10))
speedups = worst_10['speedup']

bars = ax.barh(y_pos, speedups, color='#e74c3c', alpha=0.8, edgecolor='black')

ax.set_yticks(y_pos)
ax.set_yticklabels([f"Query {idx}" for idx in worst_10['query_idx']], fontsize=10)
ax.invert_yaxis()
ax.set_xlabel('Speedup (x)', fontsize=12, fontweight='bold')
ax.set_title('DQN v4 Final: Top 10 Worst Performing Queries', fontsize=14, fontweight='bold')
ax.grid(axis='x', alpha=0.3, linestyle='--')
ax.axvline(x=1.0, color='green', linestyle='--', linewidth=2, label='Baseline (1.0x)')
ax.legend()

# 값 표시
for idx, (bar, row) in enumerate(zip(bars, worst_10.itertuples())):
    width = bar.get_width()
    label = f'{row.speedup:.3f}x'
    ax.text(width + 0.01, bar.get_y() + bar.get_height()/2.,
            label, ha='left', va='center', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'top_10_worst_queries.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'top_10_worst_queries.png'}")

# ============================================================================
# 차트 5: Speedup 분포 히스토그램
# ============================================================================
print("\n[5/7] Speedup 분포 히스토그램 생성 중...")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle('DQN v4: Speedup 분포', fontsize=16, fontweight='bold')

# Sim
sim_speedups_valid = sim_data[~np.isinf(sim_data['speedup'])]['speedup']
axes[0].hist(sim_speedups_valid, bins=20, color='#3498db', alpha=0.7, edgecolor='black')
axes[0].axvline(x=1.0, color='green', linestyle='--', linewidth=2, label='Baseline (1.0x)')
axes[0].axvline(x=sim_speedups_valid.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {sim_speedups_valid.mean():.2f}x')
axes[0].set_xlabel('Speedup (x)', fontsize=12)
axes[0].set_ylabel('Frequency', fontsize=12)
axes[0].set_title('DQN v4 Sim', fontsize=12, fontweight='bold')
axes[0].legend()
axes[0].grid(axis='y', alpha=0.3)

# Final
final_speedups_valid = final_data[~np.isinf(final_data['speedup']) & ~final_data['failed']]['speedup']
axes[1].hist(final_speedups_valid, bins=20, color='#e74c3c', alpha=0.7, edgecolor='black')
axes[1].axvline(x=1.0, color='green', linestyle='--', linewidth=2, label='Baseline (1.0x)')
axes[1].axvline(x=final_speedups_valid.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {final_speedups_valid.mean():.2f}x')
axes[1].set_xlabel('Speedup (x)', fontsize=12)
axes[1].set_ylabel('Frequency', fontsize=12)
axes[1].set_title('DQN v4 Final', fontsize=12, fontweight='bold')
axes[1].legend()
axes[1].grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'speedup_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'speedup_distribution.png'}")

# ============================================================================
# 차트 6: Baseline vs Optimized Time 산점도
# ============================================================================
print("\n[6/7] Baseline vs Optimized Time 산점도 생성 중...")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('DQN v4: Baseline vs Optimized Time', fontsize=16, fontweight='bold')

# Sim
sim_valid = sim_data[~np.isinf(sim_data['agent_time']) & (sim_data['agent_time'] < 1000)].copy()
axes[0].scatter(sim_valid['baseline_time'], sim_valid['agent_time'], 
                c='#3498db', alpha=0.6, s=100, edgecolors='black', linewidth=1)
max_time = max(sim_valid['baseline_time'].max(), sim_valid['agent_time'].max())
axes[0].plot([0, max_time], [0, max_time], 'r--', linewidth=2, label='y=x (No improvement)')
axes[0].set_xlabel('Baseline Time (ms)', fontsize=12)
axes[0].set_ylabel('Optimized Time (ms)', fontsize=12)
axes[0].set_title('DQN v4 Sim', fontsize=12, fontweight='bold')
axes[0].legend()
axes[0].grid(alpha=0.3)

# Final
final_valid = final_data[~np.isinf(final_data['agent_time']) & (final_data['agent_time'] < 1000) & ~final_data['failed']].copy()
axes[1].scatter(final_valid['baseline_time'], final_valid['agent_time'], 
                c='#e74c3c', alpha=0.6, s=100, edgecolors='black', linewidth=1)
max_time = max(final_valid['baseline_time'].max(), final_valid['agent_time'].max())
axes[1].plot([0, max_time], [0, max_time], 'r--', linewidth=2, label='y=x (No improvement)')
axes[1].set_xlabel('Baseline Time (ms)', fontsize=12)
axes[1].set_ylabel('Optimized Time (ms)', fontsize=12)
axes[1].set_title('DQN v4 Final', fontsize=12, fontweight='bold')
axes[1].legend()
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'baseline_vs_optimized.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'baseline_vs_optimized.png'}")

# ============================================================================
# 차트 7: 성능 카테고리 분포 (Pie Chart)
# ============================================================================
print("\n[7/7] 성능 카테고리 분포 차트 생성 중...")

def categorize_speedup(speedup, failed):
    if failed:
        return 'Failed'
    elif np.isinf(speedup) or speedup >= 10:
        return 'Excellent (10x+)'
    elif speedup >= 1.5:
        return 'Good (1.5x-10x)'
    elif speedup >= 0.9:
        return 'Maintained (0.9x-1.5x)'
    elif speedup >= 0.5:
        return 'Degraded (0.5x-0.9x)'
    else:
        return 'Severely Degraded (<0.5x)'

sim_data['category'] = sim_data.apply(lambda row: categorize_speedup(row['speedup'], row['failed']), axis=1)
final_data['category'] = final_data.apply(lambda row: categorize_speedup(row['speedup'], row['failed']), axis=1)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('DQN v4: Performance Category Distribution', fontsize=16, fontweight='bold')

colors = ['#2ecc71', '#3498db', '#95a5a6', '#e67e22', '#e74c3c', '#9b59b6']

# Sim
sim_counts = sim_data['category'].value_counts()
sim_explode = tuple([0.05 if i == 0 else 0 for i in range(len(sim_counts))])
axes[0].pie(sim_counts, labels=sim_counts.index, autopct='%1.1f%%', 
            colors=colors[:len(sim_counts)], explode=sim_explode,
            startangle=90, textprops={'fontsize': 10, 'fontweight': 'bold'})
axes[0].set_title('DQN v4 Sim', fontsize=12, fontweight='bold')

# Final
final_counts = final_data['category'].value_counts()
final_explode = tuple([0.05 if i == 0 else 0 for i in range(len(final_counts))])
axes[1].pie(final_counts, labels=final_counts.index, autopct='%1.1f%%', 
            colors=colors[:len(final_counts)], explode=final_explode,
            startangle=90, textprops={'fontsize': 10, 'fontweight': 'bold'})
axes[1].set_title('DQN v4 Final', fontsize=12, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'performance_categories.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'performance_categories.png'}")

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

