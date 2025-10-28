# -*- coding: utf-8 -*-
"""
Ensemble v1: Visualization

평가 결과를 시각화합니다.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from config.ensemble_config import OUTPUT_FILES, CHARTS_DIR

# Set plot style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10


def load_results(results_file: str = None) -> Dict:
    """평가 결과 로드"""
    if results_file is None:
        results_file = OUTPUT_FILES['results_json']
    
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    return results


def plot_speedup_distribution(results: Dict, output_dir: str = None):
    """
    Speedup 분포 박스플롯
    
    Ensemble vs 단일 모델 (만약 데이터가 있다면) 비교
    """
    if output_dir is None:
        output_dir = CHARTS_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract speedups by strategy
    data = []
    for strategy, strategy_results in results.items():
        if 'detailed_results' in strategy_results:
            for detail in strategy_results['detailed_results']:
                data.append({
                    'Strategy': strategy,
                    'Speedup': detail['speedup']
                })
    
    df = pd.DataFrame(data)
    
    # Plot
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x='Strategy', y='Speedup')
    plt.axhline(y=1.0, color='r', linestyle='--', label='Baseline')
    plt.title('Speedup Distribution by Voting Strategy', fontsize=14, fontweight='bold')
    plt.ylabel('Speedup (x)', fontsize=12)
    plt.xlabel('Voting Strategy', fontsize=12)
    plt.legend()
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'speedup_distribution.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_query_performance(results: Dict, strategy: str = 'weighted', output_dir: str = None):
    """
    쿼리별 성능 비교 바 차트
    """
    if output_dir is None:
        output_dir = CHARTS_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    strategy_results = results.get(strategy, {})
    query_results = strategy_results.get('query_results', {})
    
    if not query_results:
        print(f"[WARN] No query results for strategy: {strategy}")
        return
    
    # Prepare data
    query_ids = sorted(query_results.keys(), key=lambda x: int(x))
    mean_speedups = [query_results[str(q)]['mean_speedup'] for q in query_ids]
    query_types = [query_results[str(q)]['query_type'] for q in query_ids]
    
    # Plot
    plt.figure(figsize=(16, 6))
    colors = ['green' if s > 1.0 else 'red' for s in mean_speedups]
    bars = plt.bar(range(len(query_ids)), mean_speedups, color=colors, alpha=0.7)
    
    # Add baseline
    plt.axhline(y=1.0, color='black', linestyle='--', linewidth=2, label='Baseline (1.0x)')
    
    # Labels
    plt.xlabel('Query Index', fontsize=12)
    plt.ylabel('Mean Speedup (x)', fontsize=12)
    plt.title(f'Query Performance: {strategy.upper()} Strategy', fontsize=14, fontweight='bold')
    plt.xticks(range(len(query_ids)), query_ids, rotation=45)
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, f'query_performance_{strategy}.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_action_distribution(results: Dict, strategy: str = 'weighted', output_dir: str = None):
    """
    액션 사용 빈도 히스토그램
    """
    if output_dir is None:
        output_dir = CHARTS_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    strategy_results = results.get(strategy, {})
    action_counts = strategy_results.get('action_counts', {})
    
    if not action_counts:
        print(f"[WARN] No action counts for strategy: {strategy}")
        return
    
    # Prepare data
    actions = sorted(action_counts.keys(), key=lambda x: int(x) if isinstance(x, (int, str)) and str(x).isdigit() else 0)
    counts = [action_counts[str(a)] for a in actions]
    
    # Plot
    plt.figure(figsize=(14, 6))
    plt.bar(range(len(actions)), counts, alpha=0.7, color='steelblue')
    plt.xlabel('Action ID', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.title(f'Action Distribution: {strategy.upper()} Strategy', fontsize=14, fontweight='bold')
    plt.xticks(range(len(actions)), actions, rotation=45)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, f'action_distribution_{strategy}.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_model_agreement(results: Dict, output_dir: str = None):
    """
    Voting 합의도 분석
    
    4개 모델이 얼마나 일치하는지 보여줍니다.
    """
    if output_dir is None:
        output_dir = CHARTS_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract agreement data
    data = []
    for strategy, strategy_results in results.items():
        if 'model_agreement' in strategy_results:
            agreements = strategy_results['model_agreement']
            for agreement in agreements:
                data.append({
                    'Strategy': strategy,
                    'Agreement': agreement
                })
    
    df = pd.DataFrame(data)
    
    # Plot
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x='Strategy', y='Agreement')
    plt.title('Model Agreement by Voting Strategy', fontsize=14, fontweight='bold')
    plt.ylabel('Agreement Ratio', fontsize=12)
    plt.xlabel('Voting Strategy', fontsize=12)
    plt.ylim(0, 1.05)
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'model_agreement.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_query_type_performance(results: Dict, strategy: str = 'weighted', output_dir: str = None):
    """
    쿼리 타입별 성능 비교
    """
    if output_dir is None:
        output_dir = CHARTS_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    strategy_results = results.get(strategy, {})
    query_results = strategy_results.get('query_results', {})
    
    if not query_results:
        print(f"[WARN] No query results for strategy: {strategy}")
        return
    
    # Group by query type
    type_speedups = {}
    for q_id, q_result in query_results.items():
        q_type = q_result['query_type']
        speedup = q_result['mean_speedup']
        
        if q_type not in type_speedups:
            type_speedups[q_type] = []
        
        type_speedups[q_type].append(speedup)
    
    # Calculate mean speedup per type
    type_means = {k: np.mean(v) for k, v in type_speedups.items()}
    
    # Plot
    plt.figure(figsize=(12, 6))
    types = sorted(type_means.keys())
    means = [type_means[t] for t in types]
    colors = ['green' if m > 1.0 else 'red' for m in means]
    
    plt.bar(range(len(types)), means, color=colors, alpha=0.7)
    plt.axhline(y=1.0, color='black', linestyle='--', linewidth=2, label='Baseline (1.0x)')
    plt.xlabel('Query Type', fontsize=12)
    plt.ylabel('Mean Speedup (x)', fontsize=12)
    plt.title(f'Performance by Query Type: {strategy.upper()} Strategy', fontsize=14, fontweight='bold')
    plt.xticks(range(len(types)), types, rotation=45, ha='right')
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, f'query_type_performance_{strategy}.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_strategy_comparison(results: Dict, output_dir: str = None):
    """
    전략별 성능 비교 요약
    """
    if output_dir is None:
        output_dir = CHARTS_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract summary data
    strategies = []
    mean_speedups = []
    median_speedups = []
    win_rates = []
    
    for strategy, strategy_results in results.items():
        if 'summary' in strategy_results:
            summary = strategy_results['summary']
            strategies.append(strategy)
            mean_speedups.append(summary['mean_speedup'])
            median_speedups.append(summary['median_speedup'])
            win_rates.append(summary['win_rate'] * 100)
    
    # Plot 1: Speedup comparison
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Mean & Median Speedup
    x = np.arange(len(strategies))
    width = 0.35
    
    axes[0].bar(x - width/2, mean_speedups, width, label='Mean Speedup', alpha=0.8)
    axes[0].bar(x + width/2, median_speedups, width, label='Median Speedup', alpha=0.8)
    axes[0].axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='Baseline')
    axes[0].set_xlabel('Voting Strategy', fontsize=12)
    axes[0].set_ylabel('Speedup (x)', fontsize=12)
    axes[0].set_title('Speedup Comparison', fontsize=14, fontweight='bold')
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(strategies, rotation=45, ha='right')
    axes[0].legend()
    axes[0].grid(axis='y', alpha=0.3)
    
    # Win Rate
    axes[1].bar(strategies, win_rates, alpha=0.8, color='green')
    axes[1].axhline(y=50, color='red', linestyle='--', linewidth=2, label='50% Win Rate')
    axes[1].set_xlabel('Voting Strategy', fontsize=12)
    axes[1].set_ylabel('Win Rate (%)', fontsize=12)
    axes[1].set_title('Win Rate Comparison', fontsize=14, fontweight='bold')
    axes[1].set_xticklabels(strategies, rotation=45, ha='right')
    axes[1].legend()
    axes[1].grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'strategy_comparison.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def generate_all_visualizations(results_file: str = None, output_dir: str = None):
    """모든 시각화 생성"""
    
    print("=" * 80)
    print("Generating Visualizations")
    print("=" * 80)
    
    # Load results
    results = load_results(results_file)
    
    if output_dir is None:
        output_dir = CHARTS_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate all plots
    print("\n[1/6] Speedup Distribution...")
    plot_speedup_distribution(results, output_dir)
    
    print("\n[2/6] Query Performance...")
    for strategy in results.keys():
        plot_query_performance(results, strategy, output_dir)
    
    print("\n[3/6] Action Distribution...")
    for strategy in results.keys():
        plot_action_distribution(results, strategy, output_dir)
    
    print("\n[4/6] Model Agreement...")
    plot_model_agreement(results, output_dir)
    
    print("\n[5/6] Query Type Performance...")
    for strategy in results.keys():
        plot_query_type_performance(results, strategy, output_dir)
    
    print("\n[6/6] Strategy Comparison...")
    plot_strategy_comparison(results, output_dir)
    
    print("\n" + "=" * 80)
    print(f"All visualizations saved to: {output_dir}")
    print("=" * 80 + "\n")


def main():
    """Main visualization function"""
    generate_all_visualizations()


if __name__ == '__main__':
    main()

