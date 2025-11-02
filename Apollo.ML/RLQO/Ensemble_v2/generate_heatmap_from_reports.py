# -*- coding: utf-8 -*-
"""
평가 보고서에서 추출한 데이터로 히트맵 생성
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

script_dir = os.path.dirname(os.path.abspath(__file__))

# 데이터 로드
data_path = os.path.join(script_dir, 'results', 'model_performance_data.json')
with open(data_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 모델 이름 및 쿼리 정보
models = ['DQN v4', 'PPO v3', 'DDPG v1', 'SAC v1']
model_keys = ['dqn_v4', 'ppo_v3', 'ddpg_v1', 'sac_v1']
queries = list(range(30))

# 데이터 변환 (30 x 4 행렬)
heatmap_data = []
for query_id in queries:
    row = []
    for model_key in model_keys:
        speedup = data[model_key].get(str(query_id), 1.0)
        row.append(speedup)
    heatmap_data.append(row)

# numpy 배열로 변환
heatmap_array = np.array(heatmap_data)

# 개선율로 변환 (speedup → improvement %)
# speedup 1.0 = 0% 개선, 2.0 = 100% 개선, 0.5 = -100% 악화
improvement_array = (heatmap_array - 1.0) * 100

# X축과 Y축 피봇 (Transpose)
improvement_array = improvement_array.T

# 히트맵 생성 (가로 형태)
plt.figure(figsize=(22, 7))

# 색상 범위 설정: -100% (빨강) ~ 0% (흰색) ~ +100% (초록)
vmin = -100
vmax = 300  # DQN v4의 inf 케이스 때문에 높게 설정

# diverging colormap 사용
cmap = sns.diverging_palette(10, 130, s=80, l=55, as_cmap=True)

# 히트맵 그리기
ax = sns.heatmap(
    improvement_array,
    annot=True,  # 숫자 표시
    fmt='.0f',   # 정수로 표시
    cmap=cmap,
    center=0,    # 0을 중심으로
    vmin=vmin,
    vmax=vmax,
    xticklabels=[f'Q{i}' for i in queries],  # X축: 쿼리
    yticklabels=models,  # Y축: 모델
    cbar_kws={'label': 'Improvement (%)'},
    linewidths=0.5,
    linecolor='gray',
    annot_kws={'size': 8}  # 숫자 크기
)

# 제목 및 라벨
plt.title('4 Models × 30 Queries Performance Heatmap\n(From Evaluation Reports)', 
          fontsize=18, fontweight='bold', pad=20)
plt.xlabel('Queries', fontsize=14, fontweight='bold')
plt.ylabel('Models', fontsize=14, fontweight='bold')

# 축 레이블 크기 조정
ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=12, fontweight='bold')
ax.set_xticklabels(ax.get_xticklabels(), rotation=0, ha='center', fontsize=10)

# 레이아웃 조정
plt.tight_layout()

# 저장
output_path = os.path.join(script_dir, 'results', 'charts', 'model_performance_heatmap.png')
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"[SUCCESS] Heatmap saved: {output_path}")

plt.close()

# 통계 출력
print("\n[STATS] Model Performance Statistics:")
for i, model in enumerate(models):
    improvements = improvement_array[i, :]
    improvements_positive = improvements[improvements > 0]
    improvements_all = improvements
    
    print(f"\n{model}:")
    print(f"  Improved Queries: {len(improvements_positive)}/30")
    print(f"  Mean Improvement (all): {np.mean(improvements_all):.1f}%")
    print(f"  Mean Improvement (positive only): {np.mean(improvements_positive):.1f}%" if len(improvements_positive) > 0 else "  No improvements")
    print(f"  Median Improvement: {np.median(improvements_all):.1f}%")
    print(f"  Best Improvement: {np.max(improvements_all):.1f}%")
    print(f"  Worst Degradation: {np.min(improvements_all):.1f}%")
    print(f"  Win Rate (>0%): {len(improvements_positive) / 30 * 100:.1f}%")

