# -*- coding: utf-8 -*-
"""
DDPG v1 Evaluation Script

학습된 DDPG 모델을 평가하고 DQN v3, PPO v3와 비교합니다.
"""

import os
import sys
import argparse
import json
from datetime import datetime
import numpy as np
import pandas as pd

from stable_baselines3 import DDPG

# Project root path setup
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)

from RLQO.DDPG_v1.env.ddpg_db_env import QueryPlanRealDBEnvDDPGv1

# Load 30 queries
sys.path.insert(0, os.path.join(apollo_ml_dir, 'RLQO'))
from constants2 import SAMPLE_QUERIES


def evaluate_ddpg(model_path: str, episodes: int = 3, output_file: str = None):
    """
    DDPG 모델 평가
    
    Args:
        model_path: 학습된 모델 경로
        episodes: 평가 에피소드 수
        output_file: 결과 저장 경로 (JSON)
    """
    print("=" * 80)
    print(" DDPG v1 Model Evaluation")
    print("=" * 80)
    print(f"Model: {model_path}")
    print(f"Episodes: {episodes}")
    print(f"Queries: {len(SAMPLE_QUERIES)}")
    print("=" * 80)
    
    # Check model exists
    if not os.path.exists(model_path):
        print(f"[ERROR] Model not found: {model_path}")
        return
    
    # Load model
    print("\n[1/3] Loading model...")
    try:
        model = DDPG.load(model_path)
        print(f"✓ Model loaded successfully")
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        return
    
    # Create environment
    print("\n[2/3] Creating evaluation environment...")
    env = QueryPlanRealDBEnvDDPGv1(
        query_list=SAMPLE_QUERIES,
        max_steps=10,
        timeout_seconds=30,
        verbose=False  # Reduce verbosity during evaluation
    )
    print(f"✓ Environment created")
    
    # Evaluation
    print("\n[3/3] Starting evaluation...")
    print("-" * 80)
    
    results = []
    query_results = {i: [] for i in range(len(SAMPLE_QUERIES))}
    
    for episode in range(episodes):
        print(f"\nEpisode {episode + 1}/{episodes}")
        print("-" * 80)
        
        for query_idx in range(len(SAMPLE_QUERIES)):
            # Reset to specific query
            env.current_query_ix = query_idx
            obs, info = env.reset()
            
            baseline_time = info['baseline_time']
            best_time = baseline_time
            best_action = None
            total_reward = 0.0
            
            # Run episode
            for step in range(10):
                # Use deterministic action (no noise)
                action, _ = model.predict(obs, deterministic=True)
                
                obs, reward, terminated, truncated, info = env.step(action)
                total_reward += reward
                
                if info['current_time'] < best_time:
                    best_time = info['current_time']
                    best_action = info['action_description']
                
                if terminated or truncated:
                    break
            
            speedup = baseline_time / best_time if best_time > 0 else 1.0
            
            result = {
                'episode': episode + 1,
                'query_idx': query_idx,
                'baseline_time_ms': baseline_time,
                'best_time_ms': best_time,
                'speedup': speedup,
                'improvement_pct': (speedup - 1.0) * 100,
                'total_reward': total_reward,
                'best_action': best_action
            }
            
            results.append(result)
            query_results[query_idx].append(speedup)
            
            print(f"  Query {query_idx:2d}: {baseline_time:6.1f}ms → {best_time:6.1f}ms "
                  f"(Speedup: {speedup:.3f}x, +{(speedup-1)*100:+.1f}%)")
    
    env.close()
    
    # Analysis
    print("\n" + "=" * 80)
    print(" Evaluation Results Summary")
    print("=" * 80)
    
    df = pd.DataFrame(results)
    
    # Overall statistics
    print(f"\n전체 통계 ({episodes} episodes × {len(SAMPLE_QUERIES)} queries):")
    print(f"  - 평균 Speedup: {df['speedup'].mean():.3f}x")
    print(f"  - 중앙값 Speedup: {df['speedup'].median():.3f}x")
    print(f"  - 최대 Speedup: {df['speedup'].max():.3f}x")
    print(f"  - 최소 Speedup: {df['speedup'].min():.3f}x")
    print(f"  - 표준편차: {df['speedup'].std():.3f}")
    print(f"  - 평균 개선: {df['improvement_pct'].mean():+.2f}%")
    print(f"  - 평균 Reward: {df['total_reward'].mean():.4f}")
    
    # Performance categories
    excellent = df[df['speedup'] >= 1.5]
    good = df[(df['speedup'] >= 1.2) & (df['speedup'] < 1.5)]
    neutral = df[(df['speedup'] >= 0.9) & (df['speedup'] < 1.2)]
    degraded = df[df['speedup'] < 0.9]
    
    print(f"\n성능 분포:")
    print(f"  - 탁월 (≥1.5x): {len(excellent)} ({len(excellent)/len(df)*100:.1f}%)")
    print(f"  - 양호 (1.2~1.5x): {len(good)} ({len(good)/len(df)*100:.1f}%)")
    print(f"  - 중립 (0.9~1.2x): {len(neutral)} ({len(neutral)/len(df)*100:.1f}%)")
    print(f"  - 저하 (<0.9x): {len(degraded)} ({len(degraded)/len(df)*100:.1f}%)")
    
    # Query-wise statistics
    print(f"\n쿼리별 평균 성능:")
    query_summary = []
    for query_idx in range(len(SAMPLE_QUERIES)):
        query_speedups = query_results[query_idx]
        avg_speedup = np.mean(query_speedups)
        std_speedup = np.std(query_speedups)
        query_summary.append({
            'query_idx': query_idx,
            'avg_speedup': avg_speedup,
            'std_speedup': std_speedup
        })
        print(f"  Query {query_idx:2d}: {avg_speedup:.3f}x ± {std_speedup:.3f}")
    
    # Top 5 best queries
    print(f"\n상위 5개 쿼리 (평균 Speedup):")
    top_queries = sorted(query_summary, key=lambda x: x['avg_speedup'], reverse=True)[:5]
    for i, q in enumerate(top_queries, 1):
        print(f"  {i}. Query {q['query_idx']:2d}: {q['avg_speedup']:.3f}x")
    
    # Top 5 worst queries
    print(f"\n하위 5개 쿼리 (평균 Speedup):")
    worst_queries = sorted(query_summary, key=lambda x: x['avg_speedup'])[:5]
    for i, q in enumerate(worst_queries, 1):
        print(f"  {i}. Query {q['query_idx']:2d}: {q['avg_speedup']:.3f}x")
    
    # Save results
    if output_file:
        # 절대 경로로 변환 (상대 경로 입력 시 현재 디렉토리 기준)
        output_file = os.path.abspath(output_file)
        
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'model_path': model_path,
            'episodes': episodes,
            'overall': {
                'mean_speedup': float(df['speedup'].mean()),
                'median_speedup': float(df['speedup'].median()),
                'max_speedup': float(df['speedup'].max()),
                'min_speedup': float(df['speedup'].min()),
                'std_speedup': float(df['speedup'].std()),
                'mean_improvement_pct': float(df['improvement_pct'].mean())
            },
            'distribution': {
                'excellent': len(excellent),
                'good': len(good),
                'neutral': len(neutral),
                'degraded': len(degraded)
            },
            'query_summary': query_summary,
            'detailed_results': results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Results saved to: {output_file}")
    
    print("\n" + "=" * 80)
    print(" Evaluation Complete")
    print("=" * 80)
    
    return df


def main():
    parser = argparse.ArgumentParser(description='DDPG v1 Model Evaluation')
    parser.add_argument(
        '--model',
        type=str,
        default='Apollo.ML/artifacts/RLQO/models/ddpg_v1_realdb_50k.zip',
        help='Path to trained model'
    )
    parser.add_argument(
        '--episodes',
        type=int,
        default=3,
        help='Number of evaluation episodes'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file path (JSON)'
    )
    
    args = parser.parse_args()
    
    # Default output file
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"ddpg_v1_eval_{timestamp}.json"
    
    evaluate_ddpg(args.model, args.episodes, args.output)


if __name__ == '__main__':
    main()

