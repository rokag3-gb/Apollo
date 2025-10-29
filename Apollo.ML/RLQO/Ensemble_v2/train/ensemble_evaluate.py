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
    
    # 2. 각 모델의 환경 로드 (Ensemble v1 방식)
    print("\n[2/5] Loading environments for each model...")
    queries = SAMPLE_QUERIES[:n_queries]
    envs = {}
    
    # DQN v4 환경
    if 'dqn_v4' in ensemble.loaded_models:
        from RLQO.DQN_v4.env.v4_db_env import QueryPlanDBEnvV4
        envs['dqn_v4'] = QueryPlanDBEnvV4(
            query_list=queries,
            max_steps=1,
            curriculum_mode=False,
            verbose=False
        )
        print("  [OK] DQN v4 environment loaded")
    
    # PPO v3 환경
    if 'ppo_v3' in ensemble.loaded_models:
        from RLQO.PPO_v3.env.v3_db_env import QueryPlanDBEnvPPOv3
        ppo_env = QueryPlanDBEnvPPOv3(
            query_list=queries,
            max_steps=1,
            curriculum_mode=False,
            verbose=False
        )
        
        def mask_fn(env_instance):
            float_mask = env_instance.get_action_mask()
            return float_mask.astype(bool)
        
        envs['ppo_v3'] = ActionMasker(ppo_env, mask_fn)
        print("  [OK] PPO v3 environment loaded")
    
    # DDPG v1 환경
    if 'ddpg_v1' in ensemble.loaded_models:
        from RLQO.DDPG_v1.env.ddpg_db_env import QueryPlanRealDBEnvDDPGv1
        envs['ddpg_v1'] = QueryPlanRealDBEnvDDPGv1(
            query_list=queries,
            max_steps=1,
            verbose=False
        )
        print("  [OK] DDPG v1 environment loaded")
    
    # SAC v1 환경
    if 'sac_v1' in ensemble.loaded_models:
        from RLQO.SAC_v1.env.sac_db_env import make_sac_db_env
        envs['sac_v1'] = make_sac_db_env(
            query_list=queries,
            max_steps=1,
            verbose=False
        )
        print("  [OK] SAC v1 environment loaded")
    
    # Baseline 측정용 환경 (DQN v4 우선, 없으면 첫 번째 환경)
    baseline_env = envs.get('dqn_v4') or list(envs.values())[0]
    
    # 3. 평가 실행
    print(f"\n[3/5] Running evaluation on {n_queries} queries...")
    
    all_results = []
    query_summaries = []
    
    for query_idx in range(n_queries):
        query_type = QUERY_TYPES.get(query_idx, 'DEFAULT')
        query_results = []
        
        print(f"\n--- Query {query_idx} ({query_type}) ---")
        
        for episode in range(n_episodes):
            # 각 환경 reset (query_idx 설정)
            observations = {}
            action_masks = {}
            baseline_ms = 0
            
            for model_name, env in envs.items():
                # Query index 설정
                if hasattr(env, 'unwrapped'):
                    env.unwrapped.current_query_ix = query_idx
                    obs, info = env.reset()
                    # Action mask는 discrete action space만 사용
                    if hasattr(env.unwrapped, 'get_action_mask'):
                        action_masks[model_name] = env.unwrapped.get_action_mask()
                    else:
                        action_masks[model_name] = None
                elif hasattr(env, 'current_query_ix'):
                    env.current_query_ix = query_idx
                    obs, info = env.reset()
                    # Action mask는 discrete action space만 사용
                    action_masks[model_name] = getattr(env, 'get_action_mask', lambda: None)()
                else:
                    obs, info = env.reset(options={'query_index': query_idx})
                    action_masks[model_name] = info.get('action_mask', None)
                
                observations[model_name] = obs
                
                # Baseline은 첫 환경에서만 가져옴 (환경마다 키 이름이 다름)
                if baseline_ms == 0:
                    # DQN v4: info['metrics']['elapsed_time_ms']
                    # PPO v3 등: info['baseline_ms'] or info['baseline_time']
                    baseline_ms = (info.get('baseline_ms') or 
                                  info.get('baseline_time') or 
                                  info.get('metrics', {}).get('elapsed_time_ms', 0))
            
            # Query info for validator
            query_info = {
                'type': query_type,
                'baseline_ms': baseline_ms,
                'query_idx': query_idx
            }
            
            # Ensemble prediction (각 모델에게 자신의 observation 전달)
            action, pred_info = ensemble.predict_with_multi_env(
                observations=observations,
                action_masks=action_masks,
                query_type=query_type,
                query_info=query_info
            )
            
            # 하나의 환경에서만 action 실행 (baseline 환경)
            obs, reward, terminated, truncated, step_info = baseline_env.step(action)
            
            # 환경마다 키 이름이 다름 (optimized_ms, current_time 등)
            # DQN v4: step_info['metrics']['elapsed_time_ms']
            # PPO v3 등: step_info['optimized_ms'] or step_info['current_time']
            optimized_ms = (step_info.get('optimized_ms') or 
                           step_info.get('current_time') or 
                           step_info.get('metrics', {}).get('elapsed_time_ms', baseline_ms))
            speedup = baseline_ms / optimized_ms if optimized_ms > 0 else 0
            
            # Record result for validator learning
            ensemble.record_action_result(query_type, action, speedup)
            
            # Save result (numpy 타입을 Python 기본 타입으로 변환)
            result = {
                'query_idx': int(query_idx),
                'query_type': query_type,
                'episode': int(episode),
                'baseline_ms': float(baseline_ms),
                'optimized_ms': float(optimized_ms),
                'speedup': float(speedup),
                'action': int(action),
                'reward': float(reward),
                'predictions': {k: int(v) for k, v in pred_info['predictions'].items()},
                'confidences': {k: float(v) for k, v in pred_info['confidences'].items()},
                'filtered_predictions': {k: int(v) for k, v in pred_info['filtered_predictions'].items()},
                'filtered_confidences': {k: float(v) for k, v in pred_info['filtered_confidences'].items()},
            }
            
            query_results.append(result)
            all_results.append(result)
        
        # Query summary (numpy 타입 변환)
        speedups = [r['speedup'] for r in query_results]
        summary = {
            'query_idx': int(query_idx),
            'query_type': query_type,
            'baseline_ms': float(query_results[0]['baseline_ms']),
            'mean_speedup': float(np.mean(speedups)),
            'median_speedup': float(np.median(speedups)),
            'min_speedup': float(np.min(speedups)),
            'max_speedup': float(np.max(speedups)),
            'episodes': int(n_episodes),
            'win_rate': float(sum(1 for s in speedups if s > 1.0) / len(speedups)),
            'safe_rate': float(sum(1 for s in speedups if s >= 0.9) / len(speedups)),
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
        'n_queries': int(n_queries),
        'n_episodes': int(n_episodes),
        'voting_strategy': voting_strategy,
        'loaded_models': ensemble.loaded_models,
        'total_episodes': int(len(all_results)),
        'mean_speedup': float(np.mean(all_speedups)),
        'median_speedup': float(np.median(all_speedups)),
        'min_speedup': float(np.min(all_speedups)),
        'max_speedup': float(np.max(all_speedups)),
        'win_rate': float(sum(1 for s in all_speedups if s > 1.0) / len(all_speedups)),
        'safe_rate': float(sum(1 for s in all_speedups if s >= 0.9) / len(all_speedups)),
    }
    
    # 쿼리 타입별 통계 (numpy 타입 변환)
    type_stats = {}
    for qtype in set(r['query_type'] for r in all_results):
        type_results = [r for r in all_results if r['query_type'] == qtype]
        type_speedups = [r['speedup'] for r in type_results]
        
        type_stats[qtype] = {
            'episodes': int(len(type_results)),
            'mean_speedup': float(np.mean(type_speedups)),
            'median_speedup': float(np.median(type_speedups)),
            'win_rate': float(sum(1 for s in type_speedups if s > 1.0) / len(type_speedups)),
            'safe_rate': float(sum(1 for s in type_speedups if s >= 0.9) / len(type_speedups)),
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
    for env in envs.values():
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

