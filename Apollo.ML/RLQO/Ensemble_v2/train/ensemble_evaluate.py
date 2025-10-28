# -*- coding: utf-8 -*-
"""
Ensemble v2: Evaluation Script

4개 모델(DQN v4, PPO v3, DDPG v1, SAC v1)을 사용하여
30개 쿼리를 평가하고 v1 대비 개선율을 측정합니다.

v2 개선사항:
- Continuous-to-Discrete 변환 개선
- Safety-First Voting
- TOP 쿼리 최적화
- Action Validation & Filtering
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
from collections import defaultdict
from typing import Dict, List

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
ensemble_dir = os.path.abspath(os.path.join(current_dir, '..'))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
project_root = os.path.abspath(os.path.join(apollo_ml_dir, '..'))

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)
sys.path.append(ensemble_dir)

from RLQO.constants2 import SAMPLE_QUERIES
from RLQO.PPO_v3.config.query_action_mapping_v3 import QUERY_TYPES
from RLQO.Ensemble_v2.config.ensemble_config import EVAL_CONFIG, OUTPUT_FILES, MODEL_PATHS
from RLQO.Ensemble_v2.ensemble_voting import VotingEnsembleV2

from stable_baselines3 import DQN, DDPG, SAC
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker


def evaluate_ensemble_v2(
    n_queries: int = 30,
    n_episodes: int = 10,
    voting_strategy: str = 'safety_first',
    output_json: str = None
):
    """
    Ensemble v2 평가 메인 함수
    
    Args:
        n_queries: 평가할 쿼리 수
        n_episodes: 각 쿼리당 에피소드 수
        voting_strategy: 투표 전략
        output_json: 결과 저장 경로
    """
    print("=" * 80)
    print("Ensemble v2 Evaluation")
    print("=" * 80)
    print(f"Queries: {n_queries}")
    print(f"Episodes per query: {n_episodes}")
    print(f"Voting strategy: {voting_strategy}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80 + "\n")
    
    # 1. Ensemble 로드
    ensemble = VotingEnsembleV2(
        voting_strategy=voting_strategy,
        use_action_validator=True,
        use_query_router=True,
        verbose=True
    )
    ensemble.load_models()
    
    if len(ensemble.loaded_models) == 0:
        print("[ERROR] No models loaded!")
        return
    
    # 2. 환경 로드 (평가용으로 DQN v4 환경 사용)
    print("\n[2/5] Loading evaluation environment...")
    from RLQO.DQN_v4.env.v4_db_env import QueryPlanDBEnvV4
    
    queries = SAMPLE_QUERIES[:n_queries]
    env = QueryPlanDBEnvV4(
        query_list=queries,
        max_steps=1,  # 1-step evaluation
        curriculum_mode=False,
        verbose=False
    )
    
    # 3. 평가 실행
    print(f"\n[3/5] Running evaluation on {n_queries} queries...")
    
    all_results = []
    query_summaries = []
    
    for query_idx in range(n_queries):
        query_type = QUERY_TYPES.get(query_idx, 'DEFAULT')
        query_results = []
        
        print(f"\n--- Query {query_idx} ({query_type}) ---")
        
        for episode in range(n_episodes):
            # Reset environment
            obs, info = env.reset(options={'query_index': query_idx})
            
            baseline_ms = info.get('baseline_ms', 0)
            action_mask = info.get('action_mask', None)
            
            # Query info for validator
            query_info = {
                'type': query_type,
                'baseline_ms': baseline_ms,
                'query_idx': query_idx
            }
            
            # Ensemble prediction
            action, pred_info = ensemble.predict(
                observation=obs,
                query_type=query_type,
                query_info=query_info,
                action_mask=action_mask
            )
            
            # Execute action
            obs, reward, terminated, truncated, step_info = env.step(action)
            
            optimized_ms = step_info.get('optimized_ms', baseline_ms)
            speedup = baseline_ms / optimized_ms if optimized_ms > 0 else 0
            
            # Record result for validator learning
            ensemble.record_action_result(query_type, action, speedup)
            
            # Save result
            result = {
                'query_idx': query_idx,
                'query_type': query_type,
                'episode': episode,
                'baseline_ms': baseline_ms,
                'optimized_ms': optimized_ms,
                'speedup': speedup,
                'action': action,
                'reward': reward,
                'predictions': pred_info['predictions'],
                'confidences': pred_info['confidences'],
                'filtered_predictions': pred_info['filtered_predictions'],
                'filtered_confidences': pred_info['filtered_confidences'],
            }
            
            query_results.append(result)
            all_results.append(result)
        
        # Query summary
        speedups = [r['speedup'] for r in query_results]
        summary = {
            'query_idx': query_idx,
            'query_type': query_type,
            'baseline_ms': query_results[0]['baseline_ms'],
            'mean_speedup': np.mean(speedups),
            'median_speedup': np.median(speedups),
            'min_speedup': np.min(speedups),
            'max_speedup': np.max(speedups),
            'episodes': n_episodes,
            'win_rate': sum(1 for s in speedups if s > 1.0) / len(speedups),
            'safe_rate': sum(1 for s in speedups if s >= 0.9) / len(speedups),
        }
        
        query_summaries.append(summary)
        
        print(f"  Mean Speedup: {summary['mean_speedup']:.3f}x")
        print(f"  Win Rate: {summary['win_rate']:.1%}")
        print(f"  Safe Rate: {summary['safe_rate']:.1%}")
    
    # 4. 전체 통계
    print("\n[4/5] Computing overall statistics...")
    
    all_speedups = [r['speedup'] for r in all_results]
    
    overall_stats = {
        'timestamp': datetime.now().isoformat(),
        'n_queries': n_queries,
        'n_episodes': n_episodes,
        'voting_strategy': voting_strategy,
        'loaded_models': ensemble.loaded_models,
        'total_episodes': len(all_results),
        'mean_speedup': float(np.mean(all_speedups)),
        'median_speedup': float(np.median(all_speedups)),
        'min_speedup': float(np.min(all_speedups)),
        'max_speedup': float(np.max(all_speedups)),
        'win_rate': sum(1 for s in all_speedups if s > 1.0) / len(all_speedups),
        'safe_rate': sum(1 for s in all_speedups if s >= 0.9) / len(all_speedups),
    }
    
    # 쿼리 타입별 통계
    type_stats = {}
    for qtype in set(r['query_type'] for r in all_results):
        type_results = [r for r in all_results if r['query_type'] == qtype]
        type_speedups = [r['speedup'] for r in type_results]
        
        type_stats[qtype] = {
            'episodes': len(type_results),
            'mean_speedup': float(np.mean(type_speedups)),
            'median_speedup': float(np.median(type_speedups)),
            'win_rate': sum(1 for s in type_speedups if s > 1.0) / len(type_speedups),
            'safe_rate': sum(1 for s in type_speedups if s >= 0.9) / len(type_speedups),
        }
    
    overall_stats['by_query_type'] = type_stats
    
    # 5. 결과 저장
    print("\n[5/5] Saving results...")
    
    output = {
        'overall': overall_stats,
        'query_summaries': query_summaries,
        'detailed_results': all_results,
        'ensemble_stats': ensemble.get_stats(),
    }
    
    output_path = output_json or OUTPUT_FILES['results_json']
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to: {output_path}")
    
    # 통계 출력
    print("\n" + "=" * 80)
    print("Ensemble v2 Evaluation Results")
    print("=" * 80)
    print(f"Mean Speedup: {overall_stats['mean_speedup']:.3f}x")
    print(f"Median Speedup: {overall_stats['median_speedup']:.3f}x")
    print(f"Max Speedup: {overall_stats['max_speedup']:.3f}x")
    print(f"Win Rate: {overall_stats['win_rate']:.1%}")
    print(f"Safe Rate: {overall_stats['safe_rate']:.1%}")
    print("=" * 80)
    
    print("\nQuery Type Statistics:")
    for qtype, stats in sorted(type_stats.items()):
        print(f"  {qtype}: {stats['mean_speedup']:.3f}x (Win Rate: {stats['win_rate']:.1%})")
    
    # Ensemble 통계 출력
    ensemble.print_stats()
    
    # 환경 정리
    env.close()
    
    print("\n[SUCCESS] Evaluation completed!")
    
    return output


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Ensemble v2 Evaluation')
    parser.add_argument('--queries', type=int, default=30, help='Number of queries to evaluate')
    parser.add_argument('--episodes', type=int, default=10, help='Episodes per query')
    parser.add_argument('--strategy', type=str, default='safety_first', 
                       choices=['majority', 'weighted', 'safety_first', 'performance', 'query_type'],
                       help='Voting strategy')
    parser.add_argument('--output', type=str, default=None, help='Output JSON file path')
    
    args = parser.parse_args()
    
    evaluate_ensemble_v2(
        n_queries=args.queries,
        n_episodes=args.episodes,
        voting_strategy=args.strategy,
        output_json=args.output
    )

