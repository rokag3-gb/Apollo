# -*- coding: utf-8 -*-
"""
Oracle Ensemble Evaluation (기존 ensemble_evaluate.py 기반)

각 쿼리별로 모든 모델을 실제 실행한 후 최고 성능 선택

실행: python oracle_ensemble_evaluate.py
"""

import os
import sys
import json
import numpy as np
from datetime import datetime
from collections import defaultdict

# Path setup (기존과 동일)
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
from RLQO.Ensemble_v2.config.ensemble_config import MODEL_PATHS

from stable_baselines3 import DQN, DDPG, SAC
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker


def oracle_ensemble_evaluate():
    """Oracle Ensemble 평가 (기존 코드 기반)"""
    
    n_queries = 30
    n_episodes = 10
    
    print("=" * 80)
    print("Oracle Ensemble Evaluation")
    print("=" * 80)
    print(f"Queries: {n_queries}")
    print(f"Episodes per query: {n_episodes}")
    print(f"Total executions: {n_queries * n_episodes * 4} (모든 모델 실행)")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80 + "\n")
    
    # 1. 모델 로드
    print("[1/5] Loading models...")
    models = {}
    
    try:
        models['dqn_v4'] = DQN.load(MODEL_PATHS['dqn_v4'])
        print("  [OK] DQN v4 loaded")
    except Exception as e:
        print(f"  [X] DQN v4 failed: {e}")
    
    try:
        models['ppo_v3'] = MaskablePPO.load(MODEL_PATHS['ppo_v3'])
        print("  [OK] PPO v3 loaded")
    except Exception as e:
        print(f"  [X] PPO v3 failed: {e}")
    
    try:
        models['ddpg_v1'] = DDPG.load(MODEL_PATHS['ddpg_v1'])
        print("  [OK] DDPG v1 loaded")
    except Exception as e:
        print(f"  [X] DDPG v1 failed: {e}")
    
    try:
        models['sac_v1'] = SAC.load(MODEL_PATHS['sac_v1'])
        print("  [OK] SAC v1 loaded")
    except Exception as e:
        print(f"  [X] SAC v1 failed: {e}")
    
    print(f"\nTotal loaded: {len(models)} models\n")
    
    if len(models) == 0:
        print("[ERROR] No models loaded!")
        return
    
    # 2. 환경 로드 (기존 코드 그대로)
    print("[2/5] Loading environments...")
    queries = SAMPLE_QUERIES[:n_queries]
    envs = {}
    
    # DQN v4
    try:
        from RLQO.DQN_v4.env.v4_db_env import QueryPlanDBEnvV4
        envs['dqn_v4'] = QueryPlanDBEnvV4(
            query_list=queries,
            max_steps=1,
            curriculum_mode=False,
            verbose=False
        )
        print("  [OK] DQN v4 environment")
    except Exception as e:
        print(f"  [X] DQN v4 env failed: {e}")
    
    # PPO v3
    try:
        from RLQO.PPO_v3.env.v3_db_env import QueryPlanDBEnvPPOv3
        ppo_env = QueryPlanDBEnvPPOv3(
            query_list=queries,
            max_steps=1,
            curriculum_mode=False,
            verbose=False
        )
        def mask_fn(env_instance):
            return env_instance.get_action_mask().astype(bool)
        envs['ppo_v3'] = ActionMasker(ppo_env, mask_fn)
        print("  [OK] PPO v3 environment")
    except Exception as e:
        print(f"  [X] PPO v3 env failed: {e}")
    
    # DDPG v1
    try:
        from RLQO.DDPG_v1.env.ddpg_db_env import QueryPlanRealDBEnvDDPGv1
        envs['ddpg_v1'] = QueryPlanRealDBEnvDDPGv1(
            query_list=queries,
            max_steps=1,
            verbose=False
        )
        print("  [OK] DDPG v1 environment")
    except Exception as e:
        print(f"  [X] DDPG v1 env failed: {e}")
    
    # SAC v1
    try:
        from RLQO.SAC_v1.env.sac_db_env import make_sac_db_env
        envs['sac_v1'] = make_sac_db_env(
            query_list=queries,
            max_steps=1,
            verbose=False
        )
        print("  [OK] SAC v1 environment")
    except Exception as e:
        print(f"  [X] SAC v1 env failed: {e}")
    
    print(f"\nTotal loaded: {len(envs)} environments\n")
    
    # 3. Oracle 평가 실행
    print("[3/5] Running Oracle Ensemble evaluation...")
    
    all_results = []
    query_summaries = []
    oracle_model_table = {}  # {query_idx: best_model_name}
    
    for query_idx in range(n_queries):
        query_type = QUERY_TYPES.get(query_idx, 'DEFAULT')
        
        print(f"\n--- Query {query_idx} ({query_type}) ---")
        
        query_results = []
        model_performances = defaultdict(list)  # {model_name: [speedups]}
        
        for episode in range(n_episodes):
            episode_speedups = {}  # {model_name: speedup}
            baseline_ms = 0
            
            # 모든 모델 실행
            for model_name in models.keys():
                if model_name not in envs:
                    continue
                
                env = envs[model_name]
                model = models[model_name]
                
                # Reset (기존 코드 그대로)
                if hasattr(env, 'unwrapped'):
                    env.unwrapped.current_query_ix = query_idx
                    obs, info = env.reset()
                elif hasattr(env, 'current_query_ix'):
                    env.current_query_ix = query_idx
                    obs, info = env.reset()
                else:
                    obs, info = env.reset(options={'query_index': query_idx})
                
                # Baseline (첫 번째 모델에서만)
                if baseline_ms == 0:
                    baseline_ms = (info.get('baseline_ms') or 
                                  info.get('baseline_time') or 
                                  info.get('metrics', {}).get('elapsed_time_ms', 0))
                
                # Predict & Execute
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, step_info = env.step(action)
                
                # Optimized time
                optimized_ms = (step_info.get('optimized_ms') or 
                               step_info.get('current_time') or 
                               step_info.get('metrics', {}).get('elapsed_time_ms', baseline_ms))
                
                speedup = baseline_ms / optimized_ms if optimized_ms > 0 else 0
                
                episode_speedups[model_name] = speedup
                model_performances[model_name].append(speedup)
            
            # Oracle: 이 에피소드에서 최고 성능 선택
            if episode_speedups:
                best_model = max(episode_speedups.items(), key=lambda x: x[1])
                oracle_model = best_model[0]
                oracle_speedup = best_model[1]
                
                result = {
                    'query_idx': int(query_idx),
                    'query_type': query_type,
                    'episode': int(episode),
                    'baseline_ms': float(baseline_ms),
                    'oracle_speedup': float(oracle_speedup),
                    'oracle_model': oracle_model,
                    'all_model_speedups': {k: float(v) for k, v in episode_speedups.items()}
                }
                
                query_results.append(result)
                all_results.append(result)
                
                print(f"  Ep{episode}: Oracle={oracle_model} ({oracle_speedup:.3f}x)")
        
        # 쿼리별 최적 모델 선택 (평균 성능 기준)
        if model_performances:
            avg_performances = {k: np.mean(v) for k, v in model_performances.items()}
            best_avg_model = max(avg_performances.items(), key=lambda x: x[1])
            oracle_model_table[query_idx] = best_avg_model[0]
            
            oracle_speedups = [r['oracle_speedup'] for r in query_results]
            
            summary = {
                'query_idx': int(query_idx),
                'query_type': query_type,
                'baseline_ms': float(query_results[0]['baseline_ms']),
                'oracle_mean_speedup': float(np.mean(oracle_speedups)),
                'oracle_median_speedup': float(np.median(oracle_speedups)),
                'oracle_max_speedup': float(np.max(oracle_speedups)),
                'oracle_win_rate': float(sum(1 for s in oracle_speedups if s > 1.0) / len(oracle_speedups)),
                'best_model': best_avg_model[0],
                'best_model_avg': float(best_avg_model[1]),
                'model_avg_performances': {k: float(v) for k, v in avg_performances.items()},
                'episodes': int(n_episodes)
            }
            
            query_summaries.append(summary)
            
            print(f"  Oracle Avg: {summary['oracle_mean_speedup']:.3f}x, "
                  f"Best Model: {best_avg_model[0]} ({best_avg_model[1]:.3f}x)")
    
    # 4. 전체 통계
    print("\n[4/5] Computing overall statistics...")
    
    oracle_speedups = [r['oracle_speedup'] for r in all_results]
    
    overall_stats = {
        'timestamp': datetime.now().isoformat(),
        'method': 'oracle_ensemble',
        'n_queries': int(n_queries),
        'n_episodes': int(n_episodes),
        'loaded_models': list(models.keys()),
        'total_episodes': int(len(all_results)),
        'oracle_mean_speedup': float(np.mean(oracle_speedups)),
        'oracle_median_speedup': float(np.median(oracle_speedups)),
        'oracle_max_speedup': float(np.max(oracle_speedups)),
        'oracle_win_rate': float(sum(1 for s in oracle_speedups if s > 1.0) / len(oracle_speedups)),
        'oracle_safe_rate': float(sum(1 for s in oracle_speedups if s >= 0.9) / len(oracle_speedups)),
    }
    
    # 쿼리 타입별 통계
    type_stats = {}
    for qtype in set(r['query_type'] for r in all_results):
        type_results = [r for r in all_results if r['query_type'] == qtype]
        type_speedups = [r['oracle_speedup'] for r in type_results]
        
        type_stats[qtype] = {
            'episodes': int(len(type_results)),
            'mean_speedup': float(np.mean(type_speedups)),
            'median_speedup': float(np.median(type_speedups)),
            'win_rate': float(sum(1 for s in type_speedups if s > 1.0) / len(type_speedups)),
        }
    
    overall_stats['by_query_type'] = type_stats
    
    # 모델 선택 횟수
    model_counts = defaultdict(int)
    for model_name in oracle_model_table.values():
        model_counts[model_name] += 1
    
    overall_stats['model_selection_counts'] = dict(model_counts)
    overall_stats['model_selection_rates'] = {k: float(v / n_queries) for k, v in model_counts.items()}
    
    # 5. 결과 저장
    print("\n[5/5] Saving results...")
    
    output = {
        'overall': overall_stats,
        'query_summaries': query_summaries,
        'detailed_results': all_results,
        'oracle_model_table': {str(k): v for k, v in oracle_model_table.items()}
    }
    
    results_dir = os.path.join(ensemble_dir, 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    output_path = os.path.join(results_dir, 'oracle_ensemble_results.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Results saved to: {output_path}")
    
    # Oracle Model Table 별도 저장
    table_path = os.path.join(results_dir, 'oracle_model_table.json')
    with open(table_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'description': 'Query별 최적 모델 매핑 (Oracle Ensemble)',
            'model_table': {str(k): v for k, v in oracle_model_table.items()},
            'model_selection_counts': dict(model_counts),
        }, f, indent=2, ensure_ascii=False)
    print(f"Oracle Model Table saved to: {table_path}")
    
    # 통계 출력
    print("\n" + "=" * 80)
    print("Oracle Ensemble Results")
    print("=" * 80)
    print(f"Oracle Mean Speedup: {overall_stats['oracle_mean_speedup']:.3f}x")
    print(f"Oracle Median Speedup: {overall_stats['oracle_median_speedup']:.3f}x")
    print(f"Oracle Max Speedup: {overall_stats['oracle_max_speedup']:.3f}x")
    print(f"Oracle Win Rate: {overall_stats['oracle_win_rate']:.1%}")
    print(f"Oracle Safe Rate: {overall_stats['oracle_safe_rate']:.1%}")
    print("=" * 80)
    
    print("\nModel Selection Distribution:")
    for model_name, count in sorted(model_counts.items(), key=lambda x: x[1], reverse=True):
        rate = overall_stats['model_selection_rates'][model_name]
        print(f"  {model_name}: {count}개 쿼리 ({rate:.1%})")
    
    print("\nQuery Type Statistics:")
    for qtype, stats in sorted(type_stats.items()):
        print(f"  {qtype}: {stats['mean_speedup']:.3f}x (Win: {stats['win_rate']:.1%})")
    
    print("\n" + "=" * 80)
    print("Oracle Model Table:")
    print("=" * 80)
    for query_idx in sorted(oracle_model_table.keys()):
        model_name = oracle_model_table[query_idx]
        summary = next(s for s in query_summaries if s['query_idx'] == query_idx)
        print(f"  Query {query_idx:2d}: {model_name:8s} ({summary['best_model_avg']:.3f}x)")
    
    # 환경 정리
    for env in envs.values():
        env.close()
    
    print("\n[SUCCESS] Oracle Ensemble evaluation completed!")
    
    return output


if __name__ == '__main__':
    oracle_ensemble_evaluate()
