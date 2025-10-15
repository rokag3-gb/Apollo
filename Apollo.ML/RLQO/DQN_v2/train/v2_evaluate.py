# -*- coding: utf-8 -*-
"""
DQN v2: 포괄적 성능 평가 스크립트
================================
DQN v1, v1.5, v2 모델의 성능을 비교 평가합니다.

평가 메트릭:
1. Win Rate: 베이스라인보다 빠른 비율
2. Average Speedup: 평균 속도 향상률
3. Best Speedup: 최대 속도 향상률
4. Robustness: 실패율 (잘못된 액션 비율)
5. Consistency: 동일 쿼리에 대한 일관성
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from stable_baselines3 import DQN

sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML'))

from RLQO.DQN_v1.env.phase2_db_env import QueryPlanDBEnv, apply_action_to_sql as apply_action_v1
from RLQO.DQN_v2.env.v2_db_env import QueryPlanDBEnvV2, apply_action_to_sql as apply_action_v2
from RLQO.constants import SAMPLE_QUERIES


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


def evaluate_model_on_queries(model, env, queries, model_name="Model", num_runs=3, 
                              apply_action_func=None, baselines=None):
    """
    모델을 쿼리 목록에 대해 평가합니다.
    
    Args:
        model: 평가할 DQN 모델
        env: 평가 환경 (QueryPlanDBEnv or QueryPlanDBEnvV2)
        queries: 평가할 쿼리 목록
        model_name: 모델 이름 (로깅용)
        num_runs: 각 쿼리당 실행 횟수 (일관성 평가)
        apply_action_func: 액션을 SQL에 적용하는 함수 (None이면 자동 선택)
        baselines: 사전 측정된 베이스라인 딕셔너리 (None이면 매번 측정)
    
    Returns:
        results_df: 평가 결과 DataFrame
        summary: 요약 통계
    """
    # apply_action 함수 자동 선택
    if apply_action_func is None:
        if isinstance(env, QueryPlanDBEnvV2):
            apply_action_func = apply_action_v2
        else:
            apply_action_func = apply_action_v1
    print(f"\n{'='*80}")
    print(f"Evaluating: {model_name}")
    print(f"{'='*80}")
    
    results = []
    
    for q_idx, query in enumerate(queries):
        print(f"\n[Query {q_idx}] Evaluating...")
        
        # 사전 측정된 베이스라인 사용 (있으면)
        if baselines and q_idx in baselines:
            baseline_time = baselines[q_idx]
            if baseline_time <= 0:
                print(f"  [WARN] Baseline invalid: {baseline_time}")
                continue
            print(f"  Baseline: {baseline_time:.2f} ms (pre-measured)")
        else:
            # 베이스라인이 없으면 1회 측정
            obs, info = env.reset(seed=q_idx * 100)
            baseline_time = info['metrics'].get('elapsed_time_ms', -1)
            if baseline_time <= 0:
                print(f"  [WARN] Baseline execution failed")
                continue
            print(f"  Baseline: {baseline_time:.2f} ms (single run)")
        
        # 여러 번 실행하여 일관성 측정
        run_results = []
        
        for run in range(num_runs):
            # 환경 리셋 (관찰만 얻기 위해)
            obs, info = env.reset(seed=q_idx * 100 + run)
            
            # 에이전트의 액션 예측
            action_id, _ = model.predict(obs, deterministic=True)
            action = env.actions[action_id]
            
            # 수정된 SQL 생성
            modified_sql = apply_action_func(query, action)
            
            # 수정된 쿼리 실행
            _, agent_metrics = env._get_obs_from_db(modified_sql)
            agent_time = agent_metrics.get('elapsed_time_ms', float('inf'))
            
            # 실패 여부
            failed = (agent_time == float('inf') or agent_time > baseline_time * 10)
            
            # 개선률 계산
            if not failed:
                improvement_pct = (baseline_time - agent_time) / baseline_time * 100
            else:
                improvement_pct = -100.0  # 실패는 -100%
            
            run_results.append({
                'run': run + 1,
                'baseline_ms': baseline_time,
                'agent_ms': agent_time if not failed else None,
                'improvement_pct': improvement_pct,
                'action': action['name'],
                'failed': failed
            })
        
        # 여러 실행 결과 집계
        if run_results:
            valid_runs = [r for r in run_results if not r['failed']]
            
            if valid_runs:
                avg_improvement = np.mean([r['improvement_pct'] for r in valid_runs])
                std_improvement = np.std([r['improvement_pct'] for r in valid_runs])
                best_improvement = max([r['improvement_pct'] for r in valid_runs])
                action_consistency = len(set([r['action'] for r in run_results])) == 1
            else:
                avg_improvement = -100.0
                std_improvement = 0.0
                best_improvement = -100.0
                action_consistency = False
            
            failure_rate = sum([r['failed'] for r in run_results]) / len(run_results)
            
            results.append({
                'query_id': q_idx + 1,
                'model': model_name,
                'baseline_avg_ms': np.mean([r['baseline_ms'] for r in run_results]),
                'agent_avg_ms': np.mean([r['agent_ms'] for r in valid_runs]) if valid_runs else None,
                'avg_improvement_pct': avg_improvement,
                'std_improvement_pct': std_improvement,
                'best_improvement_pct': best_improvement,
                'failure_rate': failure_rate,
                'action_consistency': action_consistency,
                'primary_action': run_results[0]['action']
            })
            
            # 진행 상황 출력
            if failure_rate < 1.0:
                print(f"  [OK] 평균 개선: {avg_improvement:+.1f}% (±{std_improvement:.1f}%), "
                      f"실패율: {failure_rate*100:.0f}%")
            else:
                print(f"  [ERROR] 모든 실행 실패")
    
    # DataFrame 생성
    results_df = pd.DataFrame(results)
    
    # 요약 통계 계산
    valid_results = results_df[results_df['failure_rate'] < 1.0]
    
    if len(valid_results) > 0:
        summary = {
            'model': model_name,
            'total_queries': len(results_df),
            'successful_queries': len(valid_results),
            'win_rate': (valid_results['avg_improvement_pct'] > 0).sum() / len(valid_results) * 100,
            'avg_speedup': valid_results['avg_improvement_pct'].mean(),
            'best_speedup': valid_results['best_improvement_pct'].max(),
            'avg_failure_rate': results_df['failure_rate'].mean() * 100,
            'action_consistency_rate': results_df['action_consistency'].sum() / len(results_df) * 100
        }
    else:
        summary = {
            'model': model_name,
            'total_queries': len(results_df),
            'successful_queries': 0,
            'win_rate': 0.0,
            'avg_speedup': -100.0,
            'best_speedup': -100.0,
            'avg_failure_rate': 100.0,
            'action_consistency_rate': 0.0
        }
    
    return results_df, summary


def compare_models():
    """
    DQN v1, v1.5, v2 모델을 비교 평가합니다.
    """
    print("\n")
    print("=" * 80)
    print(" " * 20 + "DQN 모델 성능 비교 평가")
    print("=" * 80)
    print(f"\n시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"평가 쿼리 수: {len(SAMPLE_QUERIES)}")
    print(f"각 쿼리당 실행 횟수: 3회 (일관성 측정)")
    
    # 모델 경로 정의 (v2 모델만 평가)
    models_to_evaluate = [
        {
            'name': 'DQN v2 (Sim)',
            'path': 'Apollo.ML/artifacts/RLQO/models/dqn_v2_sim.zip',
            'use_v2_env': True
        },
        {
            'name': 'DQN v2 (Final)',
            'path': 'Apollo.ML/artifacts/RLQO/models/dqn_v2_final.zip',
            'use_v2_env': True
        }
    ]
    
    # 베이스라인 사전 측정 (v2 환경 사용)
    print("\n[Step 1] Measuring stable baselines...")
    try:
        baseline_env = QueryPlanDBEnvV2(
            query_list=SAMPLE_QUERIES,
            max_steps=10,
            curriculum_mode=False,
            verbose=False
        )
        baselines = measure_baselines(baseline_env, SAMPLE_QUERIES, num_runs=10, verbose=True)
        baseline_env.close()
        print("[OK] Baseline measurement complete\n")
    except Exception as e:
        print(f"[ERROR] Baseline measurement failed: {e}")
        print("  Falling back to per-run baseline measurement")
        baselines = None
    
    # 각 모델 평가
    all_results = []
    all_summaries = []
    
    for model_info in models_to_evaluate:
        model_name = model_info['name']
        model_path = model_info['path']
        use_v2_env = model_info.get('use_v2_env', False)
        
        if not os.path.exists(model_path):
            print(f"\n[WARN] {model_name} 모델을 찾을 수 없습니다: {model_path}")
            print("  이 모델은 건너뜁니다.")
            continue
        
        # 환경 생성 (모델 버전에 맞는 환경)
        print(f"\n{model_name} 환경 생성 중...")
        try:
            if use_v2_env:
                env = QueryPlanDBEnvV2(
                    query_list=SAMPLE_QUERIES,
                    max_steps=10,
                    curriculum_mode=False,
                    verbose=False
                )
                print("[OK] V2 환경 생성 완료 (19 actions)")
            else:
                env = QueryPlanDBEnv(query_list=SAMPLE_QUERIES, max_steps=10)
                print("[OK] V1 환경 생성 완료 (9 actions)")
        except Exception as e:
            print(f"[ERROR] 환경 생성 실패: {e}")
            continue
        
        try:
            # 모델 로드
            print(f"{model_name} 로드 중...")
            model = DQN.load(model_path, env=env)
            print(f"[OK] {model_name} 로드 완료")
            
            # 평가 실행 (사전 측정된 베이스라인 사용)
            results_df, summary = evaluate_model_on_queries(
                model, env, SAMPLE_QUERIES, model_name=model_name, num_runs=3, baselines=baselines
            )
            
            all_results.append(results_df)
            all_summaries.append(summary)
            
        except Exception as e:
            print(f"[ERROR] {model_name} 평가 중 오류: {e}")
        finally:
            env.close()
    
    if not all_summaries:
        print("\n[ERROR] 평가할 수 있는 모델이 없습니다.")
        return
    
    # 결과 출력
    print("\n\n")
    print("=" * 80)
    print(" " * 28 + "평가 결과 요약")
    print("=" * 80)
    
    summary_df = pd.DataFrame(all_summaries)
    
    print("\n[결과] 전체 비교:")
    print("-" * 80)
    print(summary_df.to_string(index=False))
    
    # 베스트 모델 선정
    print("\n\n[BEST] 베스트 모델:")
    print("-" * 80)
    
    best_by_speedup = summary_df.loc[summary_df['avg_speedup'].idxmax()]
    print(f"최고 평균 속도 향상: {best_by_speedup['model']} ({best_by_speedup['avg_speedup']:+.1f}%)")
    
    best_by_winrate = summary_df.loc[summary_df['win_rate'].idxmax()]
    print(f"최고 승률: {best_by_winrate['model']} ({best_by_winrate['win_rate']:.1f}%)")
    
    best_by_robustness = summary_df.loc[summary_df['avg_failure_rate'].idxmin()]
    print(f"최고 안정성: {best_by_robustness['model']} (실패율 {best_by_robustness['avg_failure_rate']:.1f}%)")
    
    # 상세 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "Apollo.ML/artifacts/RLQO/evaluation/"
    os.makedirs(output_dir, exist_ok=True)
    
    # 전체 결과 저장
    all_results_df = pd.concat(all_results, ignore_index=True)
    detail_path = f"{output_dir}detail_{timestamp}.csv"
    all_results_df.to_csv(detail_path, index=False, encoding='utf-8-sig')
    
    # 요약 결과 저장
    summary_path = f"{output_dir}summary_{timestamp}.csv"
    summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')
    
    print(f"\n\n[저장] 결과 저장:")
    print(f"  - 상세 결과: {detail_path}")
    print(f"  - 요약 결과: {summary_path}")
    
    print(f"\n종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n[SUCCESS] 평가 완료!")


def quick_test_v2():
    """
    v2 모델만 빠르게 테스트합니다.
    """
    print("\n=== DQN v2 Quick Test ===\n")
    
    model_path = 'Apollo.ML/artifacts/RLQO/models/dqn_v2_final.zip'
    
    if not os.path.exists(model_path):
        print(f"[ERROR] v2 model not found: {model_path}")
        print("  Please run v2_train_dqn.py first.")
        return
    
    # Create V2 environment (19 actions)
    env = QueryPlanDBEnvV2(
        query_list=SAMPLE_QUERIES[:3],
        max_steps=10,
        curriculum_mode=False,
        verbose=False
    )
    print("[OK] V2 environment created (19 actions, first 3 queries)")
    
    # Load model
    model = DQN.load(model_path, env=env)
    print("[OK] Model loaded")
    
    # Evaluate
    results_df, summary = evaluate_model_on_queries(
        model, env, SAMPLE_QUERIES[:3], model_name="DQN v2", num_runs=1
    )
    
    print("\n[RESULTS]:")
    print(results_df.to_string(index=False))
    print("\nSummary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    env.close()
    print("\n[SUCCESS] Test complete!")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='DQN 모델 성능 평가')
    parser.add_argument('--mode', type=str, choices=['full', 'quick'], default='full',
                        help='평가 모드: full(전체 비교), quick(v2만 빠른 테스트)')
    args = parser.parse_args()
    
    if args.mode == 'quick':
        quick_test_v2()
    else:
        compare_models()

