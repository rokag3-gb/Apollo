# -*- coding: utf-8 -*-
"""
Ensemble v1: Evaluation Script

Voting Ensemble을 평가하고 단일 모델들과 비교합니다.
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
sys.path.insert(0, ensemble_dir)

from RLQO.constants2 import SAMPLE_QUERIES
from RLQO.PPO_v3.config.query_action_mapping_v3 import QUERY_TYPES
from RLQO.Ensemble_v1.ensemble_voting import VotingEnsemble
from RLQO.Ensemble_v1.env.ensemble_env import create_dqn_env
from RLQO.Ensemble_v1.config.ensemble_config import EVAL_CONFIG, OUTPUT_FILES


def _save_checkpoint(results: Dict, checkpoint_file: str, verbose: bool = True):
    """
    체크포인트 저장
    
    Args:
        results: 현재까지의 평가 결과
        checkpoint_file: 저장 경로
        verbose: 로깅 여부
    """
    try:
        # Convert defaultdict to dict for JSON serialization
        results_copy = results.copy()
        if 'action_counts' in results_copy and isinstance(results_copy['action_counts'], defaultdict):
            results_copy['action_counts'] = dict(results_copy['action_counts'])
        
        # Save
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(results_copy, f, indent=2, ensure_ascii=False)
        
        if verbose:
            completed = len(results.get('query_results', {}))
            print(f"  [Checkpoint saved: {completed} queries completed]")
    except Exception as e:
        if verbose:
            print(f"  [WARN] Failed to save checkpoint: {e}")


def measure_baseline_times(queries: List[str], num_runs: int = 10, verbose: bool = True):
    """
    각 쿼리의 베이스라인 실행 시간을 측정합니다.
    
    Args:
        queries: 쿼리 목록
        num_runs: 각 쿼리당 실행 횟수
        verbose: 진행 상황 출력 여부
    
    Returns:
        baselines: {query_idx: median_time_ms}
    """
    if verbose:
        print("\n" + "="*80)
        print("Measuring Baseline Times (10 runs per query)")
        print("="*80)
    
    env = create_dqn_env(queries, max_steps=1, verbose=False)
    baselines = {}
    
    for q_idx in range(len(queries)):
        times = []
        
        for run in range(num_runs):
            try:
                obs, info = env.reset(seed=q_idx * 1000 + run)
                env.current_query_ix = q_idx
                baseline_time = info['metrics'].get('elapsed_time_ms', -1)
                
                if baseline_time > 0:
                    times.append(baseline_time)
            except Exception as e:
                if verbose:
                    print(f"  [WARN] Query {q_idx} Run {run+1}: {e}")
        
        if times:
            baselines[q_idx] = float(np.median(times))
            if verbose:
                print(f"Query {q_idx:2d}: {baselines[q_idx]:8.2f} ms (median of {len(times)} runs, "
                      f"range: {min(times):8.2f}-{max(times):8.2f} ms)")
        else:
            baselines[q_idx] = -1
            if verbose:
                print(f"Query {q_idx:2d}: [ERROR] No valid baseline")
    
    env.close()
    
    if verbose:
        print("="*80 + "\n")
    
    return baselines


def evaluate_ensemble(
    voting_strategy: str = 'weighted',
    n_queries: int = 30,
    n_episodes: int = 10,
    baselines: Dict[int, float] = None,
    verbose: bool = True,
    resume: bool = True,
    checkpoint_file: str = None
):
    """
    Ensemble 모델을 평가합니다.
    
    Args:
        voting_strategy: 투표 전략
        n_queries: 평가할 쿼리 개수
        n_episodes: 각 쿼리당 에피소드 수
        baselines: 사전 측정된 베이스라인 시간
        verbose: 진행 상황 출력 여부
        resume: 체크포인트에서 재개 여부
        checkpoint_file: 체크포인트 파일 경로 (None이면 자동 생성)
    
    Returns:
        results: 평가 결과 딕셔너리
    """
    
    # Checkpoint file path
    if checkpoint_file is None:
        checkpoint_dir = os.path.join(os.path.dirname(__file__), '..', 'results', 'checkpoints')
        os.makedirs(checkpoint_dir, exist_ok=True)
        checkpoint_file = os.path.join(checkpoint_dir, f'checkpoint_{voting_strategy}.json')
    
    # Try to load checkpoint
    if resume and os.path.exists(checkpoint_file):
        if verbose:
            print("=" * 80)
            print(f"Resuming from checkpoint: {checkpoint_file}")
            print("=" * 80)
        
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        # Convert string keys back to int for query_results
        if 'query_results' in results:
            results['query_results'] = {int(k): v for k, v in results['query_results'].items()}
        
        completed_queries = set(results.get('query_results', {}).keys())
        if verbose:
            print(f"Found {len(completed_queries)} completed queries: {sorted(completed_queries)}")
            print(f"Remaining: {n_queries - len(completed_queries)} queries")
            print("=" * 80 + "\n")
    else:
        # Start fresh
        results = {
            'timestamp': datetime.now().isoformat(),
            'voting_strategy': voting_strategy,
            'n_queries': n_queries,
            'n_episodes': n_episodes,
            'baselines': {},
            'query_results': {},
            'detailed_results': [],
            'action_counts': defaultdict(int),
            'model_agreement': [],
        }
        completed_queries = set()
    
    if verbose:
        print("=" * 80)
        print(f"Ensemble Evaluation: {voting_strategy.upper()} Strategy")
        print("=" * 80)
        print(f"Queries: {n_queries}")
        print(f"Episodes: {n_episodes}")
        print(f"Total evaluations: {n_queries * n_episodes}")
        print(f"Checkpoint: {checkpoint_file}")
        print(f"Resume mode: {'ON' if resume else 'OFF'}")
        print("=" * 80 + "\n")
    
    # 1. Load ensemble
    ensemble = VotingEnsemble(voting_strategy=voting_strategy, verbose=verbose)
    ensemble.load_models()
    
    # 2. Create environment
    env = create_dqn_env(SAMPLE_QUERIES[:n_queries], max_steps=1, verbose=False)
    
    # 3. Measure baselines if not provided
    if baselines is None:
        baselines = results.get('baselines', {})
        if not baselines:
            baselines = measure_baseline_times(SAMPLE_QUERIES[:n_queries], num_runs=10, verbose=verbose)
            results['baselines'] = baselines
    else:
        results['baselines'] = baselines
    
    # 4. Prepare for evaluation
    total_speedups = []
    
    # Restore action_counts and model_agreement if resuming
    if resume and os.path.exists(checkpoint_file):
        # Rebuild total_speedups from detailed_results
        for detail in results.get('detailed_results', []):
            total_speedups.append(detail['speedup'])
    
    if verbose:
        print(f"\n[Starting Evaluation]")
        print(f"{'Query':<8} {'Episode':<10} {'Type':<15} {'Baseline(ms)':<15} {'Optimized(ms)':<15} {'Speedup':<10} {'Action':<8}")
        print("-" * 100)
    
    for q_idx in range(n_queries):
        # Skip if already completed
        if q_idx in completed_queries:
            if verbose:
                print(f"Q{q_idx} [SKIP] Already completed")
            
            # Still need to collect data for summary
            if q_idx in results['query_results']:
                q_result = results['query_results'][q_idx]
                # Estimate total_speedups (mean * episodes)
                for _ in range(q_result['episodes']):
                    total_speedups.append(q_result['mean_speedup'])
            continue
        
        query_type = QUERY_TYPES.get(q_idx, 'UNKNOWN')
        query_speedups = []
        query_actions = []
        
        for episode in range(n_episodes):
            try:
                # Reset environment to specific query
                env.current_query_ix = q_idx
                obs, info = env.reset(seed=q_idx * 10000 + episode)
                
                baseline_time = baselines.get(q_idx, -1)
                
                if baseline_time <= 0:
                    if verbose:
                        print(f"Q{q_idx:<6} Ep{episode+1:<8} {'SKIP':<15} {'N/A':<15} {'N/A':<15} {'N/A':<10} {'N/A':<8}")
                    continue
                
                # Get action mask (for PPO)
                action_mask = env.get_action_mask() if hasattr(env, 'get_action_mask') else None
                
                # Ensemble prediction
                action, pred_info = ensemble.predict(obs, query_type=query_type, action_mask=action_mask)
                
                # Apply action and measure time
                obs, reward, done, truncated, info = env.step(action)
                optimized_time = info['metrics'].get('elapsed_time_ms', -1)
                
                if optimized_time > 0:
                    speedup = baseline_time / optimized_time
                else:
                    speedup = 0.0
                
                # Record results
                query_speedups.append(speedup)
                query_actions.append(action)
                total_speedups.append(speedup)
                results['action_counts'][action] += 1
                
                # Detailed result
                detail = {
                    'query_idx': q_idx,
                    'query_type': query_type,
                    'episode': episode,
                    'baseline_ms': baseline_time,
                    'optimized_ms': optimized_time,
                    'speedup': speedup,
                    'action': action,
                    'predictions': pred_info['predictions'],
                    'confidences': pred_info['confidences'],
                }
                results['detailed_results'].append(detail)
                
                # Model agreement (얼마나 모델들이 일치하는지)
                unique_predictions = len(set(pred_info['predictions'].values()))
                total_models = len(pred_info['predictions'])
                agreement_ratio = 1.0 - (unique_predictions - 1) / max(total_models, 1)
                results['model_agreement'].append(agreement_ratio)
                
                if verbose:
                    print(f"Q{q_idx:<6} Ep{episode+1:<8} {query_type:<15} {baseline_time:>12.2f}   {optimized_time:>12.2f}   {speedup:>8.3f}x  {action:<8}")
            
            except Exception as e:
                if verbose:
                    print(f"Q{q_idx:<6} Ep{episode+1:<8} [ERROR] {str(e)[:50]}")
                continue
            
            # Save checkpoint after each episode
            if (episode + 1) % 5 == 0 or episode == n_episodes - 1:
                _save_checkpoint(results, checkpoint_file, verbose=False)
        
        # Query summary
        if query_speedups:
            results['query_results'][q_idx] = {
                'query_type': query_type,
                'mean_speedup': float(np.mean(query_speedups)),
                'median_speedup': float(np.median(query_speedups)),
                'std_speedup': float(np.std(query_speedups)),
                'min_speedup': float(np.min(query_speedups)),
                'max_speedup': float(np.max(query_speedups)),
                'episodes': len(query_speedups),
                'most_common_action': int(max(set(query_actions), key=query_actions.count)),
            }
            
            # Save checkpoint after each query
            _save_checkpoint(results, checkpoint_file, verbose=verbose)
    
    env.close()
    
    # Overall summary
    if total_speedups:
        results['summary'] = {
            'mean_speedup': float(np.mean(total_speedups)),
            'median_speedup': float(np.median(total_speedups)),
            'std_speedup': float(np.std(total_speedups)),
            'min_speedup': float(np.min(total_speedups)),
            'max_speedup': float(np.max(total_speedups)),
            'win_rate': float(np.mean([s > 1.0 for s in total_speedups])),
            'safe_rate': float(np.mean([s >= 0.9 for s in total_speedups])),  # 10% 이내 저하
            'total_evaluations': len(total_speedups),
            'mean_agreement': float(np.mean(results['model_agreement'])),
        }
        
        if verbose:
            print("\n" + "=" * 80)
            print("Evaluation Summary")
            print("=" * 80)
            print(f"Mean Speedup:   {results['summary']['mean_speedup']:.3f}x")
            print(f"Median Speedup: {results['summary']['median_speedup']:.3f}x")
            print(f"Max Speedup:    {results['summary']['max_speedup']:.3f}x")
            print(f"Win Rate:       {results['summary']['win_rate']*100:.1f}%")
            print(f"Safe Rate:      {results['summary']['safe_rate']*100:.1f}%")
            print(f"Model Agreement: {results['summary']['mean_agreement']*100:.1f}%")
            print("=" * 80 + "\n")
    
    return results


def compare_strategies(
    strategies: List[str] = ['majority', 'weighted', 'equal', 'performance', 'query_type'],
    n_queries: int = 30,
    n_episodes: int = 10,
    baselines: Dict[int, float] = None,
    resume: bool = True
):
    """
    여러 투표 전략을 비교합니다.
    
    Args:
        strategies: 비교할 전략 목록
        n_queries: 쿼리 개수
        n_episodes: 에피소드 수
        baselines: 베이스라인 시간
        resume: 체크포인트에서 재개 여부
    
    Returns:
        comparison_results: 비교 결과
    """
    print("=" * 80)
    print("Comparing Voting Strategies")
    print("=" * 80)
    print(f"Strategies: {', '.join(strategies)}")
    print(f"Resume mode: {'ON' if resume else 'OFF'}")
    print("=" * 80 + "\n")
    
    # Measure baselines once
    if baselines is None:
        baselines = measure_baseline_times(SAMPLE_QUERIES[:n_queries], num_runs=10, verbose=True)
    
    comparison_results = {}
    
    for idx, strategy in enumerate(strategies, 1):
        print(f"\n{'='*80}")
        print(f"[{idx}/{len(strategies)}] Evaluating: {strategy.upper()}")
        print(f"{'='*80}\n")
        
        results = evaluate_ensemble(
            voting_strategy=strategy,
            n_queries=n_queries,
            n_episodes=n_episodes,
            baselines=baselines,
            verbose=True,
            resume=resume
        )
        
        comparison_results[strategy] = results
        
        # Show progress
        print(f"\n{'='*80}")
        print(f"[{idx}/{len(strategies)}] {strategy.upper()} completed!")
        if 'summary' in results:
            print(f"Mean Speedup: {results['summary']['mean_speedup']:.3f}x")
            print(f"Win Rate: {results['summary']['win_rate']*100:.1f}%")
        print(f"{'='*80}\n")
    
    # Summary comparison
    print("\n" + "=" * 80)
    print("Strategy Comparison Summary")
    print("=" * 80)
    print(f"{'Strategy':<20} {'Mean Speedup':<15} {'Median Speedup':<18} {'Win Rate':<12} {'Agreement':<12}")
    print("-" * 80)
    
    for strategy, results in comparison_results.items():
        if 'summary' in results:
            summary = results['summary']
            print(f"{strategy:<20} {summary['mean_speedup']:<14.3f}x {summary['median_speedup']:<17.3f}x "
                  f"{summary['win_rate']*100:<11.1f}% {summary['mean_agreement']*100:<11.1f}%")
    
    print("=" * 80 + "\n")
    
    return comparison_results


def main():
    """Main evaluation function"""
    
    # Configuration
    n_queries = EVAL_CONFIG['n_queries']
    n_episodes = EVAL_CONFIG['n_episodes']
    
    print("\n" + "=" * 80)
    print("Ensemble v1: Evaluation with Checkpoint Support")
    print("=" * 80)
    print(f"Configuration:")
    print(f"  Queries: {n_queries}")
    print(f"  Episodes per query: {n_episodes}")
    print(f"  Total evaluations per strategy: {n_queries * n_episodes}")
    print(f"\nCheckpoint features:")
    print(f"  ✓ Auto-save after each query")
    print(f"  ✓ Auto-save every 5 episodes")
    print(f"  ✓ Resume from last checkpoint on restart")
    print(f"  ✓ Location: results/checkpoints/checkpoint_<strategy>.json")
    print("=" * 80 + "\n")
    
    # Option 1: Single strategy evaluation
    # results = evaluate_ensemble(
    #     voting_strategy='weighted',
    #     n_queries=n_queries,
    #     n_episodes=n_episodes,
    #     verbose=True,
    #     resume=True  # Enable checkpoint resume
    # )
    
    # Option 2: Compare multiple strategies (recommended)
    strategies = ['majority', 'weighted', 'equal', 'performance', 'query_type']
    comparison_results = compare_strategies(
        strategies=strategies,
        n_queries=n_queries,
        n_episodes=n_episodes,
        resume=True  # Enable checkpoint resume
    )
    
    # Save results
    output_file = OUTPUT_FILES['results_json']
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n[Results saved to: {output_file}]")
    
    # Save comparison CSV
    comparison_csv = OUTPUT_FILES['comparison_csv']
    comparison_df = pd.DataFrame([
        {
            'strategy': strategy,
            'mean_speedup': results['summary']['mean_speedup'],
            'median_speedup': results['summary']['median_speedup'],
            'max_speedup': results['summary']['max_speedup'],
            'win_rate': results['summary']['win_rate'],
            'safe_rate': results['summary']['safe_rate'],
            'mean_agreement': results['summary']['mean_agreement'],
        }
        for strategy, results in comparison_results.items()
        if 'summary' in results
    ])
    
    comparison_df.to_csv(comparison_csv, index=False)
    print(f"[Comparison saved to: {comparison_csv}]\n")


if __name__ == '__main__':
    main()

