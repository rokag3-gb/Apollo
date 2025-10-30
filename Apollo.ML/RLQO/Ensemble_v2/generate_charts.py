"""
Ensemble v2 성능 시각화 차트 생성
"""
import json
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from pathlib import Path
from collections import defaultdict

# 한글 폰트 설정
matplotlib.rcParams['font.family'] = 'Malgun Gothic'  # Windows
matplotlib.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

# 결과 파일 로드
results_file = Path(__file__).parent / "results" / "ensemble_v2_results.json"
with open(results_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

output_dir = Path(__file__).parent / "charts"
output_dir.mkdir(exist_ok=True)

print("[CHART] 차트 생성 시작...")

# ============================================================================
# 차트 1: 쿼리별 Speedup 바 차트 (30개 쿼리)
# ============================================================================
print("\n[1] 쿼리별 Speedup 바 차트 생성 중...")

query_summaries = data.get("query_summaries", [])
query_names = []
speedups = []
query_types = []

for qr in query_summaries:
    query_idx = qr.get("query_idx", 0)
    query_type = qr.get("query_type", "UNKNOWN")
    mean_speedup = qr.get("mean_speedup", 1.0)
    
    query_names.append(f"Q{query_idx}")
    speedups.append(mean_speedup)
    query_types.append(query_type)

# 색상 매핑 (성능에 따라)
colors = []
for s in speedups:
    if s > 1.05:
        colors.append('#4CAF50')  # 초록 (개선)
    elif s < 0.95:
        colors.append('#F44336')  # 빨강 (저하)
    else:
        colors.append('#9E9E9E')  # 회색 (불변)

fig, ax = plt.subplots(figsize=(16, 8))
bars = ax.bar(range(len(speedups)), speedups, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)

# 기준선 (1.0x)
ax.axhline(y=1.0, color='black', linestyle='--', linewidth=1.5, label='Baseline (1.0x)')

# x축 레이블
ax.set_xticks(range(len(query_names)))
ax.set_xticklabels(query_names, rotation=90, fontsize=9)
ax.set_xlabel('쿼리 인덱스', fontsize=12, fontweight='bold')
ax.set_ylabel('Speedup (배수)', fontsize=12, fontweight='bold')
ax.set_title('Ensemble v2 - 쿼리별 성능 (Speedup)', fontsize=14, fontweight='bold', pad=20)

# 그리드
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.set_ylim(0, max(speedups) * 1.1)

# 범례
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#4CAF50', label='개선 (>1.05x)'),
    Patch(facecolor='#9E9E9E', label='불변 (0.95-1.05x)'),
    Patch(facecolor='#F44336', label='저하 (<0.95x)')
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

# 값 표시 (주요 쿼리만)
for i, (bar, speedup) in enumerate(zip(bars, speedups)):
    if speedup > 1.2 or speedup < 0.8 or speedup == 0:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{speedup:.2f}x',
                ha='center', va='bottom', fontsize=8, fontweight='bold')

plt.tight_layout()
chart1_path = output_dir / "chart1_query_speedup.png"
plt.savefig(chart1_path, dpi=300, bbox_inches='tight')
print(f"[OK] 저장됨: {chart1_path}")
plt.close()

# ============================================================================
# 차트 2: 쿼리 타입별 성능 비교 (평균 Speedup, Win Rate, Safe Rate)
# ============================================================================
print("\n[2] 쿼리 타입별 성능 비교 차트 생성 중...")

# 타입별 집계
type_stats = defaultdict(lambda: {
    "speedups": [],
    "win_rates": [],
    "safe_rates": [],
    "episodes": 0
})

for qr in query_summaries:
    query_type = qr.get("query_type", "UNKNOWN")
    mean_speedup = qr.get("mean_speedup", 1.0)
    win_rate = qr.get("win_rate", 0.0)
    safe_rate = qr.get("safe_rate", 0.0)
    n_episodes = qr.get("episodes", 10)
    
    # 타입별로 집계
    type_stats[query_type]["speedups"].append(mean_speedup)
    type_stats[query_type]["win_rates"].append(win_rate * 100)
    type_stats[query_type]["safe_rates"].append(safe_rate * 100)
    type_stats[query_type]["episodes"] += n_episodes

# 타입별 평균 계산
type_names = []
mean_speedups = []
mean_win_rates = []
mean_safe_rates = []

for qtype in sorted(type_stats.keys()):
    stats = type_stats[qtype]
    type_names.append(qtype)
    mean_speedups.append(np.mean(stats["speedups"]))
    mean_win_rates.append(np.mean(stats["win_rates"]))
    mean_safe_rates.append(np.mean(stats["safe_rates"]))

# 3개 서브플롯
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# 서브플롯 1: 평균 Speedup
colors_speedup = ['#4CAF50' if s > 1.05 else '#F44336' if s < 0.95 else '#9E9E9E' 
                  for s in mean_speedups]
axes[0].bar(type_names, mean_speedups, color=colors_speedup, alpha=0.8, edgecolor='black')
axes[0].axhline(y=1.0, color='black', linestyle='--', linewidth=1.5)
axes[0].set_ylabel('평균 Speedup (배수)', fontsize=11, fontweight='bold')
axes[0].set_title('타입별 평균 Speedup', fontsize=12, fontweight='bold')
axes[0].tick_params(axis='x', rotation=45)
axes[0].grid(axis='y', alpha=0.3)
for i, v in enumerate(mean_speedups):
    axes[0].text(i, v, f'{v:.2f}x', ha='center', va='bottom', fontsize=9, fontweight='bold')

# 서브플롯 2: Win Rate
colors_win = ['#4CAF50' if w > 30 else '#FFC107' if w > 10 else '#F44336' 
              for w in mean_win_rates]
axes[1].bar(type_names, mean_win_rates, color=colors_win, alpha=0.8, edgecolor='black')
axes[1].set_ylabel('Win Rate (%)', fontsize=11, fontweight='bold')
axes[1].set_title('타입별 Win Rate', fontsize=12, fontweight='bold')
axes[1].tick_params(axis='x', rotation=45)
axes[1].grid(axis='y', alpha=0.3)
axes[1].set_ylim(0, 100)
for i, v in enumerate(mean_win_rates):
    axes[1].text(i, v, f'{v:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

# 서브플롯 3: Safe Rate
colors_safe = ['#4CAF50' if s > 80 else '#FFC107' if s > 60 else '#F44336' 
               for s in mean_safe_rates]
axes[2].bar(type_names, mean_safe_rates, color=colors_safe, alpha=0.8, edgecolor='black')
axes[2].set_ylabel('Safe Rate (%)', fontsize=11, fontweight='bold')
axes[2].set_title('타입별 Safe Rate', fontsize=12, fontweight='bold')
axes[2].tick_params(axis='x', rotation=45)
axes[2].grid(axis='y', alpha=0.3)
axes[2].set_ylim(0, 100)
for i, v in enumerate(mean_safe_rates):
    axes[2].text(i, v, f'{v:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.suptitle('Ensemble v2 - 쿼리 타입별 성능 비교', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
chart2_path = output_dir / "chart2_type_comparison.png"
plt.savefig(chart2_path, dpi=300, bbox_inches='tight')
print(f"[OK] 저장됨: {chart2_path}")
plt.close()

# ============================================================================
# 차트 3: 전체 성능 분포 (파이 차트 + 통계 박스)
# ============================================================================
print("\n[3] 전체 성능 분포 차트 생성 중...")

# 성능 분류 카운트
improved = 0  # >1.05x
unchanged = 0  # 0.95-1.05x
degraded = 0  # <0.95x
failed = 0  # 0.0x

total_speedup = []

for qr in query_summaries:
    mean_speedup = qr.get("mean_speedup", 1.0)
    total_speedup.append(mean_speedup)
    
    if mean_speedup == 0.0:
        failed += 1
    elif mean_speedup > 1.05:
        improved += 1
    elif mean_speedup < 0.95:
        degraded += 1
    else:
        unchanged += 1

# 전체 통계
total_queries = len(query_summaries)
overall_stats = data.get("overall", {})
overall_mean = overall_stats.get("mean_speedup", 1.0)
overall_median = overall_stats.get("median_speedup", 1.0)
overall_win_rate = overall_stats.get("win_rate", 0.0) * 100
overall_safe_rate = overall_stats.get("safe_rate", 0.0) * 100

fig = plt.figure(figsize=(16, 6))

# 서브플롯 1: 파이 차트 (성능 분류)
ax1 = plt.subplot(1, 3, 1)
sizes = [improved, unchanged, degraded, failed]
labels = [
    f'개선\n({improved}개, {improved/total_queries*100:.1f}%)',
    f'불변\n({unchanged}개, {unchanged/total_queries*100:.1f}%)',
    f'저하\n({degraded}개, {degraded/total_queries*100:.1f}%)',
    f'실패\n({failed}개, {failed/total_queries*100:.1f}%)'
]
colors_pie = ['#4CAF50', '#9E9E9E', '#FF9800', '#F44336']
explode = (0.05, 0, 0.05, 0.1)  # 개선과 저하, 실패를 강조

wedges, texts, autotexts = ax1.pie(sizes, explode=explode, labels=labels, colors=colors_pie,
                                     autopct='', startangle=90, textprops={'fontsize': 10, 'fontweight': 'bold'})
ax1.set_title('성능 분포 (30개 쿼리)', fontsize=12, fontweight='bold', pad=20)

# 서브플롯 2: 통계 박스
ax2 = plt.subplot(1, 3, 2)
ax2.axis('off')

stats_text = f"""
=====================================
    [전체 성능 통계]
=====================================

평가 규모
  - 총 쿼리 수: {total_queries}개
  - 총 에피소드: {overall_stats.get('total_episodes', 0)}회
  - 쿼리당 에피소드: 10회

성능 지표
  - Mean Speedup: {overall_mean:.3f}x
  - Median Speedup: {overall_median:.3f}x
  - Win Rate: {overall_win_rate:.1f}%
  - Safe Rate: {overall_safe_rate:.1f}%

분류별 개수
  [+] 개선 (>1.05x): {improved}개
  [=] 불변 (0.95-1.05x): {unchanged}개
  [-] 저하 (<0.95x): {degraded}개
  [X] 실패 (0.0x): {failed}개

=====================================
"""

ax2.text(0.1, 0.5, stats_text, fontsize=11, verticalalignment='center',
         family='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

# 서브플롯 3: Win Rate vs Safe Rate 산점도
ax3 = plt.subplot(1, 3, 3)

win_rates_all = []
safe_rates_all = []
query_labels = []
query_colors = []

for qr in query_summaries:
    win_rate = qr.get("win_rate", 0.0) * 100
    safe_rate = qr.get("safe_rate", 0.0) * 100
    query_idx = qr.get("query_idx", 0)
    qtype = qr.get("query_type", "UNKNOWN")
    
    win_rates_all.append(win_rate)
    safe_rates_all.append(safe_rate)
    query_labels.append(f"Q{query_idx}")
    
    # 색상 (쿼리 타입별)
    type_color_map = {
        "TOP": '#2196F3',
        "JOIN_HEAVY": '#FF5722',
        "AGGREGATE": '#9C27B0',
        "CTE": '#4CAF50',
        "SIMPLE": '#FFC107',
        "SUBQUERY": '#00BCD4',
        "WINDOW": '#E91E63'
    }
    query_colors.append(type_color_map.get(qtype, '#9E9E9E'))

# 산점도
scatter = ax3.scatter(safe_rates_all, win_rates_all, c=query_colors, s=100, alpha=0.7, edgecolors='black')

# 참조선
ax3.axvline(x=50, color='gray', linestyle='--', linewidth=1, alpha=0.5)
ax3.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5)

# 이상적인 영역 표시
ax3.fill_between([80, 100], 50, 100, color='green', alpha=0.1, label='이상적 (High Safe, High Win)')

ax3.set_xlabel('Safe Rate (%)', fontsize=11, fontweight='bold')
ax3.set_ylabel('Win Rate (%)', fontsize=11, fontweight='bold')
ax3.set_title('Win Rate vs Safe Rate (쿼리별)', fontsize=12, fontweight='bold')
ax3.set_xlim(-5, 105)
ax3.set_ylim(-5, 105)
ax3.grid(True, alpha=0.3)
ax3.legend(loc='lower right', fontsize=9)

# 레이블 추가 (일부만)
for i, label in enumerate(query_labels):
    if win_rates_all[i] > 60 or safe_rates_all[i] < 20:  # 극단적인 경우만
        ax3.annotate(label, (safe_rates_all[i], win_rates_all[i]), 
                    fontsize=7, xytext=(5, 5), textcoords='offset points')

plt.suptitle('Ensemble v2 - 전체 성능 분석', fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout()
chart3_path = output_dir / "chart3_overall_analysis.png"
plt.savefig(chart3_path, dpi=300, bbox_inches='tight')
print(f"[OK] 저장됨: {chart3_path}")
plt.close()

print("\n" + "="*60)
print("[OK] 모든 차트 생성 완료!")
print("="*60)
print(f"\n[DIR] 저장 위치: {output_dir}")
print(f"  [1] chart1_query_speedup.png - 쿼리별 Speedup 바 차트")
print(f"  [2] chart2_type_comparison.png - 쿼리 타입별 성능 비교")
print(f"  [3] chart3_overall_analysis.png - 전체 성능 분석")

