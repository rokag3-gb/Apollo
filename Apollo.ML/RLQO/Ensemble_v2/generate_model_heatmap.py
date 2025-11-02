# -*- coding: utf-8 -*-
"""
4개 모델의 30개 쿼리별 성능 히트맵 생성
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# 스크립트 위치 기준 경로 설정
script_dir = os.path.dirname(os.path.abspath(__file__))

# 데이터 로드
data_path = os.path.join(script_dir, 'results', 'oracle_ensemble_detailed_results.json')
with open(data_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 모델 이름 및 쿼리 정보
models = ['DQN v4', 'PPO v3', 'DDPG v1', 'SAC v1']
model_keys = ['dqn_v4', 'ppo_v3', 'ddpg_v1', 'sac_v1']
queries = list(range(30))

# 데이터 추출 (30 x 4 행렬)
heatmap_data = []
for query_summary in data['query_summaries']:
    query_idx = query_summary['query_idx']
    if query_idx < 30:  # 30개 쿼리만
        perfs = query_summary['model_avg_performances']
        row = [perfs.get(key, 0.0) for key in model_keys]
        heatmap_data.append(row)

# numpy 배열로 변환
heatmap_array = np.array(heatmap_data)

# 개선율로 변환 (speedup → improvement %)
# speedup 1.0 = 0% 개선, 2.0 = 100% 개선, 0.5 = -100% 악화
improvement_array = (heatmap_array - 1.0) * 100

# X축과 Y축 피봇 (Transpose)
improvement_array = improvement_array.T

# 히트맵 생성 (가로 형태)
plt.figure(figsize=(20, 6))

# 색상 범위 설정: -100% (빨강) ~ 0% (흰색) ~ +100% (초록)
vmin = -100
vmax = 200  # 더 큰 개선도 표시 가능하도록

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
    linecolor='gray'
)

# 제목 및 라벨
plt.title('Query Optimization Performance Heatmap\n(4 Models × 30 Queries)', 
          fontsize=16, fontweight='bold', pad=20)
plt.xlabel('Queries', fontsize=12, fontweight='bold')
plt.ylabel('Models', fontsize=12, fontweight='bold')

# 축 레이블 크기 조정
ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=11)
ax.set_xticklabels(ax.get_xticklabels(), rotation=0, ha='center', fontsize=9)

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
    improvements = improvement_array[:, i]
    improvements_valid = improvements[improvements != -100]  # speedup=0 제외
    
    print(f"\n{model}:")
    print(f"  Mean Improvement: {np.mean(improvements_valid):.1f}%")
    print(f"  Median Improvement: {np.median(improvements_valid):.1f}%")
    print(f"  Best Improvement: {np.max(improvements_valid):.1f}%")
    print(f"  Worst Improvement: {np.min(improvements_valid):.1f}%")
    print(f"  Win Rate (>0%): {np.sum(improvements_valid > 0) / len(improvements_valid) * 100:.1f}%")

