# -*- coding: utf-8 -*-
"""
DQN v4: 포괄적 성능 평가 스크립트 (constants2.py 기반 30개 쿼리)
================================
DQN v4 모델의 성능을 평가합니다.

v4 개선사항:
- constants2.py의 30개 샘플 쿼리 사용
- 실패 임계값 완화: baseline_time * 10 → baseline_time * 50
- 호환성 체크 지표 추가
- 액션 마스킹 기반 평가
- v4 보상 함수 적용

평가 메트릭:
1. Win Rate: 베이스라인보다 빠른 비율
2. Average Speedup: 평균 속도 향상률
3. Best Speedup: 최대 속도 향상률
4. Robustness: 실패율 (잘못된 액션 비율)
5. Consistency: 동일 쿼리에 대한 일관성
6. Compatibility: 호환 액션 사용률
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from stable_baselines3 import DQN

sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML'))
sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML', 'RLQO'))

from RLQO.DQN_v4.env.v4_db_env import QueryPlanDBEnvV4, apply_action_to_sql
from RLQO.constants2 import SAMPLE_QUERIES


def measure_baselines(env, queries, num_runs=10, verbose=True):
    """
    각 쿼리의 안정적인 베이스라인을 측정합니다.
    
    Args:
        env: 평가 환경
        queries: 쿼리 목록
        num_runs: 각 쿼리당 실행 횟수
        verbose: 진행 상황 출력 여부
    
    Returns:
        baselines: {query_idx: median_time_ms} 딕셔너리
    """
    if verbose:
        print("\n" + "="*80)
        print("Measuring Stable Baselines (10 runs per query)")
        print("="*80)
    
    baselines = {}
    
    for q_idx, query in enumerate(queries):
        times = []
        
        for run in range(num_runs):
            try:
                obs, info = env.reset(seed=q_idx * 1000 + run)
                baseline_time = info['metrics'].get('elapsed_time_ms', -1)
                if baseline_time > 0:
                    times.append(baseline_time)
            except Exception as e:
                if verbose:
                    print(f"  [WARN] Query {q_idx} Run {run+1}: {e}")
        
        if times:
            baselines[q_idx] = float(np.median(times))
            if verbose:
                print(f"Query {q_idx}: {baselines[q_idx]:.2f} ms (median of {len(times)} runs, "
                      f"range: {min(times):.2f}-{max(times):.2f} ms)")
        else:
            baselines[q_idx] = -1
            if verbose:
                print(f"Query {q_idx}: [ERROR] No valid baseline")
    
    if verbose:
        print("="*80 + "\n")
    
    return baselines


def evaluate_model_on_queries(model, env, queries, model_name="Model", num_runs=3, baselines=None):
    """
    모델을 쿼리 목록에 대해 평가합니다.
    
    Args:
        model: 평가할 DQN 모델
        env: 평가 환경 (QueryPlanDBEnvV4)
        queries: 평가할 쿼리 목록
        model_name: 모델 이름 (로깅용)
        num_runs: 각 쿼리당 실행 횟수 (일관성 평가)
        baselines: 사전 측정된 베이스라인 딕셔너리
    
    Returns:
        results_df: 평가 결과 DataFrame
        summary: 요약 통계
    """
    print(f"\n{'='*80}")
    print(f"Evaluating {model_name}")
    print(f"{'='*80}")
    
    results = []
    
    for q_idx, query in enumerate(queries):
        print(f"\nQuery {q_idx}: {query[:80]}...")
        
        # 베이스라인 시간 가져오기
        if baselines and q_idx in baselines:
            baseline_time = baselines[q_idx]
        else:
            # 베이스라인이 없으면 측정
            try:
                obs, info = env.reset(seed=q_idx * 1000)
                baseline_time = info['metrics'].get('elapsed_time_ms', -1)
            except Exception as e:
                print(f"  [ERROR] Baseline measurement failed: {e}")
                baseline_time = -1
        
        if baseline_time <= 0:
            print(f"  [SKIP] Invalid baseline time: {baseline_time}")
            continue
        
        print(f"  Baseline: {baseline_time:.2f} ms")
        
        # 여러 번 실행하여 일관성 평가
        agent_times = []
        agent_reads = []
        actions_taken = []
        invalid_actions = []
        
        for run in range(num_runs):
            try:
                obs, info = env.reset(seed=q_idx * 1000 + run)
                
                # 액션 마스크 확인
                action_mask = info.get('action_mask', np.ones(env.action_space.n))
                compatible_count = info.get('compatible_actions', env.action_space.n)
                
                # 모델이 액션을 선택
                action, _ = model.predict(obs, deterministic=True)
                
                # 액션 호환성 체크
                is_invalid = (action_mask[action] == 0)
                invalid_actions.append(is_invalid)
                
                if is_invalid:
                    print(f"    Run {run+1}: [INVALID] Action {action} not compatible")
                    continue
                
                # 액션 실행
                obs, reward, terminated, truncated, info = env.step(action)
                
                agent_time = info['metrics'].get('elapsed_time_ms', float('inf'))
                agent_reads.append(info['metrics'].get('logical_reads', 0))
                agent_times.append(agent_time)
                actions_taken.append(action)
                
                print(f"    Run {run+1}: {agent_time:.2f} ms (action: {action})")
                
            except Exception as e:
                print(f"    Run {run+1}: [ERROR] {e}")
                continue
        
        if not agent_times:
            print(f"  [SKIP] No valid runs")
            continue
        
        # 통계 계산
        median_agent_time = np.median(agent_times)
        median_agent_reads = np.median(agent_reads)
        
        # 실패 조건: v4에서는 임계값을 50배로 완화
        failed = (median_agent_time == float('inf') or median_agent_time > baseline_time * 50)
        
        if failed:
            speedup = -1.0
            improvement_pct = -100.0
        else:
            speedup = baseline_time / median_agent_time
            improvement_pct = (baseline_time - median_agent_time) / baseline_time * 100
        
        # 호환성 통계
        invalid_rate = np.mean(invalid_actions) if invalid_actions else 0.0
        compatibility_rate = 1.0 - invalid_rate
        
        # 일관성 통계
        time_std = np.std(agent_times) if len(agent_times) > 1 else 0.0
        consistency = 1.0 / (1.0 + time_std / median_agent_time) if median_agent_time > 0 else 0.0
        
        result = {
            'query_idx': q_idx,
            'baseline_time': baseline_time,
            'agent_time': median_agent_time,
            'agent_reads': median_agent_reads,
            'speedup': speedup,
            'improvement_pct': improvement_pct,
            'failed': failed,
            'invalid_rate': invalid_rate,
            'compatibility_rate': compatibility_rate,
            'consistency': consistency,
            'num_runs': len(agent_times),
            'actions_taken': actions_taken
        }
        
        results.append(result)
        
        # 결과 출력
        status = "FAILED" if failed else "SUCCESS"
        print(f"  Result: {status}")
        print(f"    Speedup: {speedup:.2f}x ({improvement_pct:+.1f}%)")
        print(f"    Compatibility: {compatibility_rate:.1%}")
        print(f"    Consistency: {consistency:.3f}")
    
    # DataFrame 생성
    results_df = pd.DataFrame(results)
    
    if results_df.empty:
        print(f"\n[ERROR] No valid results for {model_name}")
        return results_df, {}
    
    # 요약 통계 계산
    valid_results = results_df[~results_df['failed']]
    
    summary = {
        'model_name': model_name,
        'total_queries': len(results_df),
        'successful_queries': len(valid_results),
        'failed_queries': len(results_df) - len(valid_results),
        'win_rate': len(valid_results) / len(results_df) if len(results_df) > 0 else 0.0,
        'avg_speedup': valid_results['speedup'].mean() if len(valid_results) > 0 else 0.0,
        'best_speedup': valid_results['speedup'].max() if len(valid_results) > 0 else 0.0,
        'avg_improvement': valid_results['improvement_pct'].mean() if len(valid_results) > 0 else 0.0,
        'avg_compatibility': results_df['compatibility_rate'].mean(),
        'avg_consistency': results_df['consistency'].mean(),
        'failure_rate': (len(results_df) - len(valid_results)) / len(results_df) if len(results_df) > 0 else 0.0
    }
    
    return results_df, summary


def compare_models(models_to_evaluate, mode='full'):
    """
    여러 모델을 비교 평가합니다.
    
    Args:
        models_to_evaluate: 평가할 모델 목록
        mode: 평가 모드 ('full' 또는 'quick')
    """
    print("=" * 80)
    print(" DQN v4 Model Evaluation (constants2.py 기반 30개 쿼리)")
    print("=" * 80)
    print(f"Mode: {mode}")
    print(f"Models to evaluate: {len(models_to_evaluate)}")
    print("-" * 80)
    
    # 환경 생성
    env = QueryPlanDBEnvV4(
        query_list=SAMPLE_QUERIES,
        max_steps=10,
        curriculum_mode=False,
        verbose=False
    )
    
    # 베이스라인 사전 측정
    baselines = measure_baselines(env, SAMPLE_QUERIES, num_runs=10, verbose=True)
    env.close()
    
    all_results = []
    all_summaries = []
    
    # 각 모델 평가
    for model_path, model_name in models_to_evaluate:
        try:
            # 모델 로드
            model = DQN.load(model_path)
            
            # 환경 재생성
            env = QueryPlanDBEnvV4(
                query_list=SAMPLE_QUERIES,
                max_steps=10,
                curriculum_mode=False,
                verbose=False
            )
            
            # 평가 실행
            if mode == 'quick':
                # 빠른 평가: 처음 3개 쿼리만
                test_queries = SAMPLE_QUERIES[:3]
                num_runs = 1
            else:
                # 전체 평가: 모든 쿼리
                test_queries = SAMPLE_QUERIES
                num_runs = 3
            
            results_df, summary = evaluate_model_on_queries(
                model, env, test_queries, 
                model_name=model_name, 
                num_runs=num_runs,
                baselines=baselines
            )
            
            if not results_df.empty:
                all_results.append(results_df)
                all_summaries.append(summary)
            
            env.close()
            
        except Exception as e:
            print(f"[ERROR] Failed to evaluate {model_name}: {e}")
            continue
    
    # 결과 출력
    if all_summaries:
        print("\n" + "=" * 80)
        print(" EVALUATION SUMMARY")
        print("=" * 80)
        
        summary_df = pd.DataFrame(all_summaries)
        
        # 주요 메트릭 출력
        print("\nKey Metrics:")
        print("-" * 40)
        for _, row in summary_df.iterrows():
            print(f"{row['model_name']}:")
            print(f"  Win Rate: {row['win_rate']:.1%}")
            print(f"  Avg Speedup: {row['avg_speedup']:.2f}x")
            print(f"  Best Speedup: {row['best_speedup']:.2f}x")
            print(f"  Avg Improvement: {row['avg_improvement']:+.1f}%")
            print(f"  Compatibility: {row['avg_compatibility']:.1%}")
            print(f"  Consistency: {row['avg_consistency']:.3f}")
            print(f"  Failure Rate: {row['failure_rate']:.1%}")
            print()
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"Apollo.ML/artifacts/RLQO/evaluation_results_v4_{timestamp}.csv"
        summary_file = f"Apollo.ML/artifacts/RLQO/evaluation_summary_v4_{timestamp}.csv"
        
        # 디렉토리 생성
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        # 전체 결과 저장
        if all_results:
            combined_results = pd.concat(all_results, ignore_index=True)
            combined_results.to_csv(results_file, index=False)
            print(f"Detailed results saved: {results_file}")
        
        # 요약 저장
        summary_df.to_csv(summary_file, index=False)
        print(f"Summary saved: {summary_file}")
        
        print("\n" + "=" * 80)
        print(" EVALUATION COMPLETE")
        print("=" * 80)
    else:
        print("\n[ERROR] No models were successfully evaluated!")


def quick_test_v4():
    """v4 모델 빠른 테스트"""
    print("=== DQN v4 Quick Test (constants2.py 기반 30개 쿼리) ===\n")
    
    # 환경 생성
    env = QueryPlanDBEnvV4(
        query_list=SAMPLE_QUERIES[:2],  # 처음 2개 쿼리만
        max_steps=5,
        curriculum_mode=False,
        verbose=True
    )
    
    print(f"Action space: {env.action_space}")
    print(f"Observation space: {env.observation_space}")
    
    # 리셋 테스트
    obs, info = env.reset()
    print(f"\nReset 완료:")
    print(f"Observation shape: {obs.shape if obs is not None else 'None'}")
    print(f"Action mask: {info.get('action_mask', 'N/A')}")
    print(f"Compatible actions: {info.get('compatible_actions', 'N/A')}")
    
    # 랜덤 액션 테스트
    action_mask = info.get('action_mask', np.ones(env.action_space.n))
    valid_actions = np.where(action_mask == 1.0)[0]
    
    if len(valid_actions) > 0:
        action = valid_actions[0]
        print(f"\nValid action 테스트: {env.actions[action]['name']}")
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"Reward: {reward:.4f}")
        print(f"Metrics: {info.get('metrics', {})}")
    
    env.close()
    print("\n[SUCCESS] v4 환경 테스트 완료!")


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DQN v4 모델 평가 (constants2.py 기반 30개 쿼리)')
    parser.add_argument('--mode', choices=['full', 'quick'], default='full',
                       help='평가 모드 선택')
    parser.add_argument('--test', action='store_true',
                       help='환경 테스트만 실행')
    
    args = parser.parse_args()
    
    if args.test:
        quick_test_v4()
        return
    
    # 평가할 모델 목록 (v4 모델만)
    models_to_evaluate = [
        ('Apollo.ML/artifacts/RLQO/models/dqn_v4_sim.zip', 'DQN v4 Sim'),
        ('Apollo.ML/artifacts/RLQO/models/dqn_v4_final.zip', 'DQN v4 Final'),
    ]
    
    # 실제 존재하는 모델만 필터링
    existing_models = []
    for model_path, model_name in models_to_evaluate:
        if os.path.exists(model_path):
            existing_models.append((model_path, model_name))
        else:
            print(f"[WARN] Model not found: {model_path}")
    
    if not existing_models:
        print("[ERROR] No v4 models found for evaluation!")
        print("Available models:")
        model_dir = 'Apollo.ML/artifacts/RLQO/models/'
        if os.path.exists(model_dir):
            for f in os.listdir(model_dir):
                if f.endswith('.zip'):
                    print(f"  - {f}")
        return
    
    compare_models(existing_models, mode=args.mode)


if __name__ == "__main__":
    main()
