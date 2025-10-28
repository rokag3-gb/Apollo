# -*- coding: utf-8 -*-
"""
SAC v1: Evaluation

30 queries × 30 episodes = 900 evaluations
"""

import os
import sys
import json
from datetime import datetime
from stable_baselines3 import SAC
import numpy as np

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
sac_v1_dir = os.path.abspath(os.path.join(current_dir, '..'))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
apollo_core_dir = os.path.abspath(os.path.join(apollo_ml_dir, '..', 'Apollo.Core'))
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, apollo_core_dir)
sys.path.insert(0, rlqo_dir)
sys.path.insert(0, sac_v1_dir)

# Imports
from RLQO.constants2 import SAMPLE_QUERIES
from RLQO.SAC_v1.env.sac_db_env import make_sac_db_env
from RLQO.SAC_v1.config.sac_config import SAC_EVAL_CONFIG, MODEL_PATHS


def evaluate_sac(model_path: str = None, output_path: str = None):
    """
    SAC v1 모델 평가
    
    Args:
        model_path: 평가할 모델 경로 (None이면 realdb 모델)
        output_path: 결과 저장 경로
    """
    
    print("=" * 80)
    print("SAC v1 Model Evaluation")
    print("=" * 80)
    
    # 1. Setup paths
    if model_path is None:
        model_path = MODEL_PATHS['realdb']
    
    if output_path is None:
        output_path = "sac_v1_realdb_eval.json"
    
    if not os.path.exists(model_path):
        print(f"\n[ERROR] Model not found at {model_path}")
        return
    
    # 2. Create environment (DB connection handled inside)
    print("\n[1/4] Creating Real DB environment...")
    try:
        env = make_sac_db_env(SAMPLE_QUERIES, max_steps=10, verbose=True)
        print("[OK] Environment created successfully")
    except Exception as e:
        print(f"[ERROR] Environment creation failed: {e}")
        return
    
    # 3. Load model
    print("\n[2/4] Loading model...")
    model = SAC.load(model_path)
    print(f"[OK] Model loaded from: {model_path}")
    print(f"Policy type: Stochastic (SAC)")
    
    # 4. Evaluate
    print("\n[3/4] Starting evaluation...")
    print(f"Queries: {SAC_EVAL_CONFIG['n_queries']}")
    print(f"Episodes per query: {SAC_EVAL_CONFIG['n_episodes']}")
    print(f"Total evaluations: {SAC_EVAL_CONFIG['n_queries'] * SAC_EVAL_CONFIG['n_episodes']}")
    print(f"Deterministic: {SAC_EVAL_CONFIG['deterministic']} (stochastic policy)")
    print(f"Expected duration: ~2-3 hours")
    print("=" * 80)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'model_path': model_path,
        'episodes': SAC_EVAL_CONFIG['n_episodes'],
        'queries': SAC_EVAL_CONFIG['n_queries'],
        'policy_type': 'stochastic',
        'detailed_results': [],
        'query_summary': []
    }
    
    try:
        for episode in range(SAC_EVAL_CONFIG['n_episodes']):
            print(f"\n{'='*80}")
            print(f"Episode {episode + 1}/{SAC_EVAL_CONFIG['n_episodes']}")
            print(f"{'='*80}")
            
            for query_idx in range(SAC_EVAL_CONFIG['n_queries']):
                # Reset to specific query
                env.current_query_ix = query_idx
                obs, info = env.reset()
                
                baseline_time = info['baseline_time']
                best_time = baseline_time
                best_action = None
                total_reward = 0.0
                
                # Run episode (max 10 steps)
                for step in range(10):
                    # SAC uses stochastic policy
                    action, _ = model.predict(obs, deterministic=SAC_EVAL_CONFIG['deterministic'])
                    
                    obs, reward, terminated, truncated, info = env.step(action)
                    total_reward += reward
                    
                    if info['current_time'] < best_time:
                        best_time = info['current_time']
                        best_action = info['action_description']
                    
                    if terminated or truncated:
                        break
                
                # Record results
                speedup = baseline_time / best_time if best_time > 0 else 1.0
                result = {
                    'episode': episode + 1,
                    'query_idx': query_idx,
                    'baseline_time_ms': baseline_time,
                    'optimized_time_ms': best_time,
                    'speedup': speedup,
                    'reward': total_reward,
                    'action': best_action
                }
                
                results['detailed_results'].append(result)
                
                print(f"Query {query_idx}: {baseline_time:.0f}ms → {best_time:.0f}ms "
                      f"(Speedup: {speedup:.2f}x, Reward: {total_reward:.2f})")
        
        # 5. Calculate summary statistics
        print("\n[4/4] Calculating summary statistics...")
        
        # Per-query statistics
        for query_idx in range(SAC_EVAL_CONFIG['n_queries']):
            query_results = [r for r in results['detailed_results'] if r['query_idx'] == query_idx]
            speedups = [r['speedup'] for r in query_results]
            
            query_summary = {
                'query_idx': query_idx,
                'avg_speedup': np.mean(speedups),
                'std_speedup': np.std(speedups),
                'min_speedup': np.min(speedups),
                'max_speedup': np.max(speedups)
            }
            results['query_summary'].append(query_summary)
        
        # Overall statistics
        all_speedups = [r['speedup'] for r in results['detailed_results']]
        results['overall'] = {
            'mean_speedup': np.mean(all_speedups),
            'median_speedup': np.median(all_speedups),
            'std_speedup': np.std(all_speedups),
            'min_speedup': np.min(all_speedups),
            'max_speedup': np.max(all_speedups)
        }
        
        # Win rate
        improved_count = sum(1 for s in all_speedups if s > 1.05)  # >5% improvement
        results['overall']['win_rate'] = improved_count / len(all_speedups)
        
        # 6. Save results
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 80)
        print("Evaluation completed!")
        print("=" * 80)
        print(f"Results saved: {output_path}")
        print(f"\nOverall Performance:")
        print(f"  Mean Speedup: {results['overall']['mean_speedup']:.3f}x")
        print(f"  Median Speedup: {results['overall']['median_speedup']:.3f}x")
        print(f"  Max Speedup: {results['overall']['max_speedup']:.3f}x")
        print(f"  Win Rate: {results['overall']['win_rate']*100:.1f}%")
        print(f"  Policy: Stochastic (Maximum Entropy)")
        
    except Exception as e:
        print(f"\n[ERROR] Evaluation error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        env.close()


if __name__ == '__main__':
    evaluate_sac()

