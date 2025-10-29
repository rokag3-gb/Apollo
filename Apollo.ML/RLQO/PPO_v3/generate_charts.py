# -*- coding: utf-8 -*-
"""
PPO v3 평가 결과 차트 생성 스크립트
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
OUTPUT_DIR = Path("Apollo.ML/RLQO/PPO_v3/charts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 데이터 로드
with open("Apollo.ML/artifacts/RLQO/evaluation/ppo_v3_eval_20251023_154004.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 쿼리 타입 정보 추출
query_types = {
    '0': 'JOIN_HEAVY', '1': 'CTE', '2': 'SIMPLE', '3': 'JOIN_HEAVY',
    '4': 'JOIN_HEAVY', '5': 'SUBQUERY', '6': 'SIMPLE', '7': 'JOIN_HEAVY',
    '8': 'WINDOW', '9': 'AGGREGATE', '10': 'TOP', '11': 'CTE',
    '12': 'TOP', '13': 'TOP', '14': 'TOP', '15': 'JOIN_HEAVY',
    '16': 'JOIN_HEAVY', '17': 'SUBQUERY', '18': 'SUBQUERY', '19': 'WINDOW',
    '20': 'AGGREGATE', '21': 'TOP', '22': 'JOIN_HEAVY', '23': 'TOP',
    '24': 'AGGREGATE', '25': 'AGGREGATE', '26': 'JOIN_HEAVY', '27': 'JOIN_HEAVY',
    '28': 'JOIN_HEAVY', '29': 'AGGREGATE'
}

print("=" * 80)
print("PPO v3 평가 차트 생성 중...")
print("=" * 80)

# ============================================================================
# 차트 1: 쿼리 타입별 평균 Speedup
# ============================================================================
print("\n[1/6] 쿼리 타입별 평균 Speedup 차트 생성 중...")

# 타입별 그룹화
type_speedups = {}
for query_idx, query_data in data['query_results'].items():
    qtype = query_types.get(query_idx, 'UNKNOWN')
    if qtype not in type_speedups:
        type_speedups[qtype] = []
    type_speedups[qtype].append(query_data['avg_speedup'])

# 평균 계산
type_avg = {k: np.mean(v) for k, v in type_speedups.items()}
type_avg_sorted = dict(sorted(type_avg.items(), key=lambda x: x[1], reverse=True))

fig, ax = plt.subplots(figsize=(10, 6))

types = list(type_avg_sorted.keys())
speedups = list(type_avg_sorted.values())
colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(types)))

bars = ax.bar(types, speedups, color=colors, alpha=0.8, edgecolor='black')
ax.axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='Baseline (1.0x)')
ax.set_ylabel('Average Speedup (x)', fontsize=12, fontweight='bold')
ax.set_xlabel('Query Type', fontsize=12, fontweight='bold')
ax.set_title('PPO v3: 쿼리 타입별 평균 Speedup', fontsize=14, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
ax.legend()

# 값 표시
for bar, speedup in zip(bars, speedups):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{speedup:.3f}x', ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'speedup_by_query_type.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'speedup_by_query_type.png'}")

# ============================================================================
# 차트 2: Query별 평균 Speedup
# ============================================================================
print("\n[2/6] Query별 평균 Speedup 차트 생성 중...")

fig, ax = plt.subplots(figsize=(16, 6))

query_indices = list(range(30))
avg_speedups = [data['query_results'][str(i)]['avg_speedup'] for i in query_indices]
avg_speedups_clean = [min(s, 5) for s in avg_speedups]  # 극단값 제한

colors = ['#2ecc71' if s > 1.5 else '#3498db' if s > 1.0 else '#95a5a6' for s in avg_speedups]
bars = ax.bar(query_indices, avg_speedups_clean, color=colors, alpha=0.8, edgecolor='black')

ax.axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='Baseline (1.0x)')
ax.set_xlabel('Query Index', fontsize=12, fontweight='bold')
ax.set_ylabel('Average Speedup (x)', fontsize=12, fontweight='bold')
ax.set_title('PPO v3: Query별 평균 Speedup (30 episodes)', fontsize=14, fontweight='bold')
ax.set_xticks(query_indices)
ax.legend()
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'speedup_by_query.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'speedup_by_query.png'}")

# ============================================================================
# 차트 3: Top 10 Best Queries
# ============================================================================
print("\n[3/6] Top 10 Best Queries 차트 생성 중...")

query_perf = [(int(idx), data['query_results'][idx]['avg_speedup']) 
              for idx in data['query_results'].keys()]
query_perf_sorted = sorted(query_perf, key=lambda x: x[1], reverse=True)
top_10 = query_perf_sorted[:10]

fig, ax = plt.subplots(figsize=(10, 6))

y_pos = np.arange(len(top_10))
speedups = [s for _, s in top_10]
query_labels = [f"Query {idx} ({query_types.get(str(idx), 'N/A')})" for idx, _ in top_10]

bars = ax.barh(y_pos, speedups, color='#2ecc71', alpha=0.8, edgecolor='black')

ax.set_yticks(y_pos)
ax.set_yticklabels(query_labels, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel('Average Speedup (x)', fontsize=12, fontweight='bold')
ax.set_title('PPO v3: Top 10 Best Performing Queries', fontsize=14, fontweight='bold')
ax.grid(axis='x', alpha=0.3)

# 값 표시
for bar, speedup in zip(bars, speedups):
    width = bar.get_width()
    ax.text(width + 0.05, bar.get_y() + bar.get_height()/2.,
            f'{speedup:.3f}x', ha='left', va='center', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'top_10_best_queries.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'top_10_best_queries.png'}")

# ============================================================================
# 차트 4: Speedup 분포 히스토그램
# ============================================================================
print("\n[4/6] Speedup 분포 히스토그램 생성 중...")

all_speedups = []
for query_data in data['query_results'].values():
    all_speedups.extend(query_data['speedups'])

# 극단값 제외
all_speedups_clean = [s for s in all_speedups if 0 < s <= 10]

fig, ax = plt.subplots(figsize=(10, 6))

ax.hist(all_speedups_clean, bins=50, color='#3498db', alpha=0.7, edgecolor='black')
ax.axvline(x=1.0, color='green', linestyle='--', linewidth=2, label='Baseline (1.0x)')
ax.axvline(x=np.mean(all_speedups_clean), color='red', linestyle='--', 
           linewidth=2, label=f'Mean: {np.mean(all_speedups_clean):.3f}x')
ax.set_xlabel('Speedup (x)', fontsize=12, fontweight='bold')
ax.set_ylabel('Frequency', fontsize=12)
ax.set_title('PPO v3: Speedup 분포 (900 executions)', fontsize=14, fontweight='bold')
ax.legend()
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'speedup_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'speedup_distribution.png'}")

# ============================================================================
# 차트 5: Action 빈도 분석
# ============================================================================
print("\n[5/6] Action 빈도 분석 차트 생성 중...")

all_actions = []
for query_data in data['query_results'].values():
    all_actions.extend(query_data['actions'])

action_counts = Counter(all_actions)
action_counts_sorted = dict(sorted(action_counts.items(), key=lambda x: x[1], reverse=True))

# Top 15 액션만 표시
top_actions = list(action_counts_sorted.items())[:15]

fig, ax = plt.subplots(figsize=(12, 6))

actions = [f"Action {a}" for a, _ in top_actions]
counts = [c for _, c in top_actions]

bars = ax.bar(actions, counts, color='#9b59b6', alpha=0.8, edgecolor='black')
ax.set_xlabel('Action', fontsize=12, fontweight='bold')
ax.set_ylabel('Frequency', fontsize=12, fontweight='bold')
ax.set_title('PPO v3: Top 15 Action Frequency', fontsize=14, fontweight='bold')
ax.set_xticklabels(actions, rotation=45, ha='right')
ax.grid(axis='y', alpha=0.3)

# 값 표시
for bar, count in zip(bars, counts):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{count}', ha='center', va='bottom', fontsize=8, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'action_frequency.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'action_frequency.png'}")

# ============================================================================
# 차트 6: 쿼리 타입별 성능 분포 (Box Plot)
# ============================================================================
print("\n[6/6] 쿼리 타입별 성능 분포 차트 생성 중...")

# 타입별 모든 speedup 수집
type_all_speedups = {}
for query_idx, query_data in data['query_results'].items():
    qtype = query_types.get(query_idx, 'UNKNOWN')
    if qtype not in type_all_speedups:
        type_all_speedups[qtype] = []
    # 극단값 제외
    speedups_clean = [s for s in query_data['speedups'] if 0 < s <= 10]
    type_all_speedups[qtype].extend(speedups_clean)

# 박스플롯 데이터 준비
types_sorted = sorted(type_all_speedups.keys(), 
                     key=lambda x: np.median(type_all_speedups[x]), reverse=True)
data_for_plot = [type_all_speedups[t] for t in types_sorted]

fig, ax = plt.subplots(figsize=(12, 6))

bp = ax.boxplot(data_for_plot, labels=types_sorted, patch_artist=True,
                showfliers=False)  # outlier 숨김

# 색상 설정
colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(types_sorted)))
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

ax.axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='Baseline (1.0x)')
ax.set_ylabel('Speedup (x)', fontsize=12, fontweight='bold')
ax.set_xlabel('Query Type', fontsize=12, fontweight='bold')
ax.set_title('PPO v3: 쿼리 타입별 Speedup 분포 (Box Plot)', fontsize=14, fontweight='bold')
ax.legend()
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'speedup_boxplot_by_type.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ 저장 완료: {OUTPUT_DIR / 'speedup_boxplot_by_type.png'}")

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
print(f"  평균 Speedup: {np.mean(all_speedups_clean):.3f}x")
print(f"  중앙값 Speedup: {np.median(all_speedups_clean):.3f}x")
print(f"  표준편차: {np.std(all_speedups_clean):.3f}")
print(f"  최대 Speedup: {np.max(all_speedups_clean):.3f}x")
print(f"  최소 Speedup: {np.min([s for s in all_speedups if s > 0]):.3f}x")

