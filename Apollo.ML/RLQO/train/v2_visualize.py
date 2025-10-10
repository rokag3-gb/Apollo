# -*- coding: utf-8 -*-
"""
DQN v2: 평가 결과 시각화 스크립트
=================================
evaluation/ 폴더의 CSV 결과를 읽어 차트 생성

생성되는 차트:
1. 쿼리별 성능 개선률 막대 그래프
2. 액션별 평균 개선률 히트맵
3. 모델별 비교 차트 (Sim vs Final)
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import glob

# 한글 폰트 설정 (Windows 환경)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML'))


def find_latest_results():
    """
    가장 최근의 평가 결과 CSV 파일 찾기
    """
    eval_dir = 'Apollo.ML/artifacts/RLQO/evaluation/'
    detail_files = glob.glob(f"{eval_dir}detail_*.csv")
    summary_files = glob.glob(f"{eval_dir}summary_*.csv")
    
    if not detail_files or not summary_files:
        return None, None
    
    detail_files.sort(reverse=True)
    summary_files.sort(reverse=True)
    
    return detail_files[0], summary_files[0]


def plot_query_performance(df, output_path):
    """
    쿼리별 성능 개선률 막대 그래프
    
    Args:
        df: detail CSV의 DataFrame
        output_path: 저장할 경로
    """
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # 쿼리별로 모델별 개선률 비교
    query_ids = sorted(df['query_id'].unique())
    models = df['model'].unique()
    
    x = np.arange(len(query_ids))
    width = 0.35
    
    for i, model in enumerate(models):
        model_data = df[df['model'] == model]
        improvements = []
        
        for qid in query_ids:
            q_data = model_data[model_data['query_id'] == qid]
            if not q_data.empty:
                improvements.append(q_data['avg_improvement_pct'].values[0])
            else:
                improvements.append(0)
        
        offset = width * (i - len(models)/2 + 0.5)
        bars = ax.bar(x + offset, improvements, width, label=model, alpha=0.8)
        
        # 값 라벨 추가
        for bar in bars:
            height = bar.get_height()
            if abs(height) > 5:  # 너무 작은 값은 라벨 생략
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%',
                       ha='center', va='bottom' if height > 0 else 'top',
                       fontsize=8)
    
    # 0% 기준선
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
    
    ax.set_xlabel('Query Index', fontsize=12, fontweight='bold')
    ax.set_ylabel('Performance Improvement (%)', fontsize=12, fontweight='bold')
    ax.set_title('Query Performance Improvement by Model', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'Q{qid}' for qid in query_ids])
    ax.legend(loc='best')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"[OK] Query performance chart saved: {output_path}")


def plot_action_effectiveness(df, output_path):
    """
    액션별 평균 개선률 히트맵
    
    Args:
        df: detail CSV의 DataFrame
        output_path: 저장할 경로
    """
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # 액션별 쿼리별 개선률 집계
    pivot_data = df.pivot_table(
        values='avg_improvement_pct',
        index='primary_action',
        columns='query_id',
        aggfunc='mean'
    )
    
    # 히트맵 생성
    sns.heatmap(pivot_data, annot=True, fmt='.1f', cmap='RdYlGn', center=0,
                cbar_kws={'label': 'Avg Improvement (%)'}, ax=ax,
                linewidths=0.5, linecolor='gray')
    
    ax.set_xlabel('Query Index', fontsize=12, fontweight='bold')
    ax.set_ylabel('Action', fontsize=12, fontweight='bold')
    ax.set_title('Action Effectiveness Heatmap (Avg Improvement %)', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"[OK] Action effectiveness heatmap saved: {output_path}")


def plot_model_comparison(summary_df, output_path):
    """
    모델별 비교 차트 (Sim vs Final)
    
    Args:
        summary_df: summary CSV의 DataFrame
        output_path: 저장할 경로
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    models = summary_df['model'].values
    
    # 1. Win Rate
    ax = axes[0, 0]
    ax.bar(models, summary_df['win_rate'], color=['#1f77b4', '#ff7f0e'], alpha=0.7)
    ax.set_ylabel('Win Rate (%)', fontweight='bold')
    ax.set_title('Win Rate Comparison', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    for i, v in enumerate(summary_df['win_rate']):
        ax.text(i, v + 1, f'{v:.1f}%', ha='center', fontweight='bold')
    
    # 2. Average Speedup
    ax = axes[0, 1]
    colors = ['green' if x > 0 else 'red' for x in summary_df['avg_speedup']]
    ax.bar(models, summary_df['avg_speedup'], color=colors, alpha=0.7)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.set_ylabel('Avg Speedup (%)', fontweight='bold')
    ax.set_title('Average Speedup Comparison', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    for i, v in enumerate(summary_df['avg_speedup']):
        ax.text(i, v + (5 if v > 0 else -5), f'{v:.1f}%', ha='center', fontweight='bold')
    
    # 3. Failure Rate
    ax = axes[1, 0]
    ax.bar(models, summary_df['avg_failure_rate'], color=['#d62728', '#9467bd'], alpha=0.7)
    ax.set_ylabel('Avg Failure Rate (%)', fontweight='bold')
    ax.set_title('Failure Rate Comparison', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    for i, v in enumerate(summary_df['avg_failure_rate']):
        ax.text(i, v + 1, f'{v:.1f}%', ha='center', fontweight='bold')
    
    # 4. Successful Queries
    ax = axes[1, 1]
    ax.bar(models, summary_df['successful_queries'], color=['#2ca02c', '#8c564b'], alpha=0.7)
    ax.set_ylabel('Successful Queries', fontweight='bold')
    ax.set_title('Successful Queries Count', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    for i, v in enumerate(summary_df['successful_queries']):
        ax.text(i, v + 0.1, f'{int(v)}', ha='center', fontweight='bold')
    
    plt.suptitle('DQN v2 Model Comparison (Sim vs Final)', fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"[OK] Model comparison chart saved: {output_path}")


def plot_baseline_consistency(df, output_path):
    """
    베이스라인 일관성 차트 (표준편차 시각화)
    
    Args:
        df: detail CSV의 DataFrame
        output_path: 저장할 경로
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    query_ids = sorted(df['query_id'].unique())
    models = df['model'].unique()
    
    x = np.arange(len(query_ids))
    width = 0.35
    
    for i, model in enumerate(models):
        model_data = df[df['model'] == model]
        std_devs = []
        
        for qid in query_ids:
            q_data = model_data[model_data['query_id'] == qid]
            if not q_data.empty:
                std_devs.append(q_data['std_improvement_pct'].values[0])
            else:
                std_devs.append(0)
        
        offset = width * (i - len(models)/2 + 0.5)
        ax.bar(x + offset, std_devs, width, label=model, alpha=0.8)
    
    ax.set_xlabel('Query Index', fontsize=12, fontweight='bold')
    ax.set_ylabel('Std Dev of Improvement (%)', fontsize=12, fontweight='bold')
    ax.set_title('Performance Consistency (Lower is Better)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'Q{qid}' for qid in query_ids])
    ax.legend(loc='best')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"[OK] Baseline consistency chart saved: {output_path}")


def generate_all_charts(detail_path=None, summary_path=None):
    """
    모든 차트 생성
    
    Args:
        detail_path: detail CSV 경로 (None이면 최신 파일 자동 탐색)
        summary_path: summary CSV 경로 (None이면 최신 파일 자동 탐색)
    """
    print("\n" + "="*80)
    print(" " * 25 + "DQN v2 Result Visualization")
    print("="*80)
    
    # 파일 찾기
    if detail_path is None or summary_path is None:
        print("\n[1/5] Finding latest evaluation results...")
        detail_path, summary_path = find_latest_results()
        
        if detail_path is None or summary_path is None:
            print("[ERROR] No evaluation results found in Apollo.ML/artifacts/RLQO/evaluation/")
            print("  Please run v2_evaluate.py first.")
            return
        
        print(f"  Detail: {os.path.basename(detail_path)}")
        print(f"  Summary: {os.path.basename(summary_path)}")
    
    # CSV 읽기
    print("\n[2/5] Loading CSV files...")
    try:
        detail_df = pd.read_csv(detail_path, encoding='utf-8-sig')
        summary_df = pd.read_csv(summary_path, encoding='utf-8-sig')
        print(f"  Detail: {len(detail_df)} rows")
        print(f"  Summary: {len(summary_df)} rows")
    except Exception as e:
        print(f"[ERROR] Failed to load CSV: {e}")
        return
    
    # 출력 디렉토리 생성
    output_dir = 'Apollo.ML/artifacts/RLQO/evaluation/charts/'
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 차트 생성
    print("\n[3/5] Generating query performance chart...")
    plot_query_performance(detail_df, f"{output_dir}query_performance_{timestamp}.png")
    
    print("\n[4/5] Generating action effectiveness heatmap...")
    plot_action_effectiveness(detail_df, f"{output_dir}action_effectiveness_{timestamp}.png")
    
    print("\n[5/5] Generating model comparison chart...")
    plot_model_comparison(summary_df, f"{output_dir}model_comparison_{timestamp}.png")
    
    print("\n[BONUS] Generating baseline consistency chart...")
    plot_baseline_consistency(detail_df, f"{output_dir}baseline_consistency_{timestamp}.png")
    
    print("\n" + "="*80)
    print("[SUCCESS] All charts generated successfully!")
    print(f"Output directory: {output_dir}")
    print("="*80 + "\n")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='DQN v2 Evaluation Result Visualization')
    parser.add_argument('--detail', type=str, help='Path to detail CSV file')
    parser.add_argument('--summary', type=str, help='Path to summary CSV file')
    args = parser.parse_args()
    
    generate_all_charts(args.detail, args.summary)

