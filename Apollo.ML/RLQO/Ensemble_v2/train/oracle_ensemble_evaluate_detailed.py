# -*- coding: utf-8 -*-
"""
Oracle Ensemble Detailed Evaluation

Base 성능 + 실행 계획 + RL 모델 적용 후 성능 비교
- Logical Reads
- Physical Reads
- CPU Time
- Execution Plan
- Applied Hints
"""

import os
import sys
import json
import numpy as np
from datetime import datetime
from collections import defaultdict

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
from RLQO.Ensemble_v2.config.ensemble_config import MODEL_PATHS
from RLQO.DQN_v4.env.v4_db_env import apply_action_to_sql

from stable_baselines3 import DQN, DDPG, SAC
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

from db import connect
from config import load_config
from collections import Counter


def extract_query_name(query_str: str) -> str:
    """쿼리 문자열에서 이름 추출"""
    if '# [인덱스' in query_str or '[인덱스' in query_str:
        lines = query_str.split('\n')
        for line in lines:
            if '[인덱스' in line and ']' in line:
                name_part = line.split(']', 1)
                if len(name_part) > 1:
                    name = name_part[1].split('-')[0].strip()
                    return name if name else f'Query'
    return 'Query'


def oracle_ensemble_evaluate_detailed():
    """Oracle Ensemble 상세 평가 (DB 메트릭 포함)"""
    
    n_queries = 30
    n_episodes = 10
    
    print("=" * 80)
    print("Oracle Ensemble Detailed Evaluation")
    print("상세 메트릭: Elapsed Time, Logical Reads, CPU Time, Execution Plan")
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
    
    # 2. 환경 로드
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
    
    # 3. Oracle 평가 실행 (상세 메트릭 수집)
    print("[3/5] Running Oracle Ensemble evaluation with detailed metrics...")
    
    all_results = []
    query_summaries = []
    oracle_model_table = {}
    
    for query_idx in range(n_queries):
        query_type = QUERY_TYPES.get(query_idx, 'DEFAULT')
        query_str = queries[query_idx]
        query_name = extract_query_name(query_str)
        
        print(f"\n--- Query {query_idx}: {query_name} ({query_type}) ---")
        
        query_results = []
        model_performances = defaultdict(list)
        
        # Baseline 메트릭 수집 (첫 에피소드에서만)
        baseline_metrics = None
        
        for episode in range(n_episodes):
            episode_results = {}
            
            # 모든 모델 실행
            for model_name in models.keys():
                if model_name not in envs:
                    continue
                
                env = envs[model_name]
                model = models[model_name]
                
                # Reset
                if hasattr(env, 'unwrapped'):
                    env.unwrapped.current_query_ix = query_idx
                    obs, info = env.reset()
                elif hasattr(env, 'current_query_ix'):
                    env.current_query_ix = query_idx
                    obs, info = env.reset()
                else:
                    obs, info = env.reset(options={'query_index': query_idx})
                
                # Baseline 메트릭 (첫 에피소드에서만 수집)
                if episode == 0 and baseline_metrics is None:
                    baseline_metrics = {
                        'elapsed_time_ms': info.get('baseline_ms') or info.get('baseline_time') or info.get('metrics', {}).get('elapsed_time_ms', 0),
                        'logical_reads': info.get('baseline_logical_reads') or info.get('metrics', {}).get('logical_reads', 0),
                        'cpu_time_ms': info.get('baseline_cpu_time_ms') or info.get('metrics', {}).get('cpu_time_ms', 0),
                    }
                
                # Predict & Execute
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, step_info = env.step(action)
                
                # Action 변환 (numpy array 처리)
                if isinstance(action, np.ndarray):
                    if action.shape == ():  # scalar array
                        action_int = int(action.item())
                    elif len(action) == 1:
                        action_int = int(action[0])
                    else:
                        action_int = int(action[0])  # 첫 번째 요소
                else:
                    action_int = int(action)
                
                # 최적화 후 메트릭
                optimized_metrics = {
                    'elapsed_time_ms': step_info.get('optimized_ms') or step_info.get('current_time') or step_info.get('metrics', {}).get('elapsed_time_ms', baseline_metrics['elapsed_time_ms']),
                    'logical_reads': step_info.get('metrics', {}).get('logical_reads', baseline_metrics['logical_reads']),
                    'cpu_time_ms': step_info.get('metrics', {}).get('cpu_time_ms', baseline_metrics['cpu_time_ms']),
                    'action': action_int,
                    'reward': float(reward),
                }
                
                # Speedup 계산
                baseline_time = baseline_metrics['elapsed_time_ms']
                optimized_time = optimized_metrics['elapsed_time_ms']
                speedup = baseline_time / optimized_time if optimized_time > 0 else 0
                
                episode_results[model_name] = {
                    'speedup': speedup,
                    'optimized_metrics': optimized_metrics,
                }
                
                model_performances[model_name].append(speedup)
            
            # Oracle: 이 에피소드에서 최고 성능 선택
            if episode_results:
                best_model_name = max(episode_results.items(), key=lambda x: x[1]['speedup'])[0]
                best_result = episode_results[best_model_name]
                
                result = {
                    'query_idx': int(query_idx),
                    'query_name': str(query_name),
                    'query_type': query_type,
                    'episode': int(episode),
                    'baseline_metrics': {k: float(v) if isinstance(v, (int, float)) else v for k, v in baseline_metrics.items()},
                    'oracle_model': best_model_name,
                    'oracle_speedup': float(best_result['speedup']),
                    'oracle_optimized_metrics': {k: float(v) if isinstance(v, (int, float)) else v for k, v in best_result['optimized_metrics'].items()},
                    'all_model_speedups': {k: float(v['speedup']) for k, v in episode_results.items()},
                    'all_model_metrics': {
                        model: {
                            'speedup': float(result['speedup']),
                            'elapsed_time_ms': float(result['optimized_metrics']['elapsed_time_ms']),
                            'logical_reads': float(result['optimized_metrics']['logical_reads']),
                            'cpu_time_ms': float(result['optimized_metrics']['cpu_time_ms']),
                            'action': int(result['optimized_metrics']['action']),
                            'reward': float(result['optimized_metrics']['reward']),
                        }
                        for model, result in episode_results.items()
                    }
                }
                
                query_results.append(result)
                all_results.append(result)
                
                print(f"  Ep{episode}: Oracle={best_model_name} ({best_result['speedup']:.3f}x) | "
                      f"Time: {baseline_metrics['elapsed_time_ms']:.1f}ms -> {best_result['optimized_metrics']['elapsed_time_ms']:.1f}ms | "
                      f"Reads: {baseline_metrics['logical_reads']:.0f} -> {best_result['optimized_metrics']['logical_reads']:.0f}")
        
        # 쿼리별 최적 모델 선택 (평균 성능 기준)
        if model_performances:
            avg_performances = {k: np.mean(v) for k, v in model_performances.items()}
            best_avg_model = max(avg_performances.items(), key=lambda x: x[1])
            oracle_model_table[query_idx] = best_avg_model[0]
            
            oracle_speedups = [r['oracle_speedup'] for r in query_results]
            
            # 평균 메트릭 계산
            avg_baseline_time = np.mean([r['baseline_metrics']['elapsed_time_ms'] for r in query_results])
            avg_baseline_reads = np.mean([r['baseline_metrics']['logical_reads'] for r in query_results])
            avg_baseline_cpu = np.mean([r['baseline_metrics']['cpu_time_ms'] for r in query_results])
            
            avg_optimized_time = np.mean([r['oracle_optimized_metrics']['elapsed_time_ms'] for r in query_results])
            avg_optimized_reads = np.mean([r['oracle_optimized_metrics']['logical_reads'] for r in query_results])
            avg_optimized_cpu = np.mean([r['oracle_optimized_metrics']['cpu_time_ms'] for r in query_results])
            
            summary = {
                'query_idx': int(query_idx),
                'query_name': str(query_name),
                'query_type': query_type,
                'baseline_metrics': {
                    'elapsed_time_ms': float(avg_baseline_time),
                    'logical_reads': float(avg_baseline_reads),
                    'cpu_time_ms': float(avg_baseline_cpu),
                },
                'oracle_mean_speedup': float(np.mean(oracle_speedups)),
                'oracle_median_speedup': float(np.median(oracle_speedups)),
                'oracle_max_speedup': float(np.max(oracle_speedups)),
                'oracle_win_rate': float(sum(1 for s in oracle_speedups if s > 1.0) / len(oracle_speedups)),
                'oracle_optimized_metrics': {
                    'elapsed_time_ms': float(avg_optimized_time),
                    'logical_reads': float(avg_optimized_reads),
                    'cpu_time_ms': float(avg_optimized_cpu),
                },
                'improvement_pct': {
                    'elapsed_time': float((avg_baseline_time - avg_optimized_time) / avg_baseline_time * 100) if avg_baseline_time > 0 else 0,
                    'logical_reads': float((avg_baseline_reads - avg_optimized_reads) / avg_baseline_reads * 100) if avg_baseline_reads > 0 else 0,
                    'cpu_time': float((avg_baseline_cpu - avg_optimized_cpu) / avg_baseline_cpu * 100) if avg_baseline_cpu > 0 else 0,
                },
                'best_model': best_avg_model[0],
                'best_model_avg': float(best_avg_model[1]),
                'model_avg_performances': {k: float(v) for k, v in avg_performances.items()},
                'episodes': int(n_episodes)
            }
            
            query_summaries.append(summary)
            
            print(f"  Summary: {summary['oracle_mean_speedup']:.3f}x avg | "
                  f"Time: {avg_baseline_time:.1f}ms -> {avg_optimized_time:.1f}ms ({summary['improvement_pct']['elapsed_time']:.1f}%) | "
                  f"Reads: {avg_baseline_reads:.0f} -> {avg_optimized_reads:.0f} ({summary['improvement_pct']['logical_reads']:.1f}%)")
    
    # 4. 전체 통계
    print("\n[4/5] Computing overall statistics...")
    
    oracle_speedups = [r['oracle_speedup'] for r in all_results]
    
    overall_stats = {
        'timestamp': datetime.now().isoformat(),
        'method': 'oracle_ensemble_detailed',
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
    
    # 5. DB에 결과 INSERT
    print("\n[5/6] Inserting results to database...")
    
    try:
        # DB 연결
        config_path = os.path.join(apollo_ml_dir, 'config.yaml')
        config = load_config(config_path)
        conn = connect(config.db)
        cursor = conn.cursor()
        
        # Action space 로드
        action_space_file = os.path.join(apollo_ml_dir, 'artifacts', 'RLQO', 'configs', 'v4_action_space.json')
        with open(action_space_file, 'r', encoding='utf-8') as f:
            action_space = json.load(f)
            actions_dict = {action['id']: action for action in action_space}
        
        # 기존 데이터 삭제
        delete_sql = "DELETE FROM dbo.rlqo_optimization_proposals WHERE model_name = 'Ensemble_v2_Oracle'"
        cursor.execute(delete_sql)
        print(f"  [OK] 기존 데이터 {cursor.rowcount}건 삭제")
        
        # 각 쿼리별 가장 빈번한 action 추출
        query_actions = {}
        for result in all_results:
            q_idx = result['query_idx']
            oracle_model = result['oracle_model']
            
            if q_idx not in query_actions:
                query_actions[q_idx] = {'best_model': oracle_model, 'actions': []}
            
            model_metrics = result.get('all_model_metrics', {}).get(oracle_model, {})
            action = model_metrics.get('action', None)
            
            if action is not None:
                query_actions[q_idx]['actions'].append(int(action))
        
        # INSERT 문 준비
        insert_sql = """
        INSERT INTO dbo.rlqo_optimization_proposals (
            proposal_datetime, model_name, original_query_text, optimized_query_text,
            baseline_elapsed_time_ms, baseline_cpu_time_ms, baseline_logical_reads,
            optimized_elapsed_time_ms, optimized_cpu_time_ms, optimized_logical_reads,
            speedup_ratio, cpu_improvement_ratio, reads_improvement_ratio,
            query_type, episode_count, confidence_score, approval_status, notes
        ) VALUES (
            SYSDATETIME(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """
        
        inserted_count = 0
        
        for summary in query_summaries:
            q_idx = summary['query_idx']
            query_type = summary['query_type']
            best_model = summary['best_model']
            
            baseline = summary['baseline_metrics']
            optimized = summary['oracle_optimized_metrics']
            speedup = summary['oracle_mean_speedup']
            win_rate = summary['oracle_win_rate']
            
            # CPU, Reads 개선율
            cpu_improvement = baseline['cpu_time_ms'] / optimized['cpu_time_ms'] if optimized['cpu_time_ms'] > 0 else 0
            reads_improvement = baseline['logical_reads'] / optimized['logical_reads'] if optimized['logical_reads'] > 0 else 0
            
            # 원본 쿼리 (공백 정리)
            original_query = SAMPLE_QUERIES[q_idx].strip()
            lines = [line.strip() for line in original_query.split('\n') if line.strip()]
            original_query_clean = '\n'.join(lines)
            
            # 가장 빈번한 action
            if q_idx in query_actions and query_actions[q_idx]['actions']:
                action_counter = Counter(query_actions[q_idx]['actions'])
                best_action_id = action_counter.most_common(1)[0][0]
            else:
                best_action_id = 18  # NO_ACTION
            
            # 최적화된 쿼리 = 원본 + Action 적용
            action_info = actions_dict.get(best_action_id, {})
            action_name = action_info.get('name', 'NO_ACTION')
            
            # action_value에서 힌트만 추출 (OPTION (...) 제거)
            action_value = action_info.get('value', '')
            if action_value.startswith('OPTION ('):
                action_value = action_value.replace('OPTION (', '').rstrip(')')
            
            # apply_action_to_sql에 맞는 형식으로 변환
            action_for_sql = {
                'type': action_info.get('type', 'BASELINE'),
                'value': action_value
            }
            
            optimized_query = apply_action_to_sql(original_query_clean, action_for_sql)
            
            # 승인 상태
            approval_status = 'PENDING' if speedup > 1.05 else 'REJECTED'
            
            notes = f'Best Model: {best_model}, Query Index: {q_idx}, Action: {action_name} (ID: {best_action_id})'
            
            try:
                cursor.execute(insert_sql, (
                    'Ensemble_v2_Oracle',
                    original_query_clean,
                    optimized_query,
                    baseline['elapsed_time_ms'],
                    baseline['cpu_time_ms'],
                    int(baseline['logical_reads']),
                    optimized['elapsed_time_ms'],
                    optimized['cpu_time_ms'],
                    int(optimized['logical_reads']),
                    speedup,
                    cpu_improvement,
                    reads_improvement,
                    query_type,
                    n_episodes,
                    win_rate,
                    approval_status,
                    notes
                ))
                inserted_count += 1
            except Exception as e:
                print(f"  [ERROR] Query {q_idx} insert failed: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"  [OK] {inserted_count}개 쿼리 결과를 DB에 저장했습니다.")
        
    except Exception as e:
        print(f"  [ERROR] DB 저장 실패: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. 결과 파일 저장
    print("\n[6/6] Saving detailed results to files...")
    
    results_dir = os.path.join(ensemble_dir, 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    output = {
        'overall': overall_stats,
        'query_summaries': query_summaries,
        'detailed_results': all_results
    }
    
    output_path = os.path.join(results_dir, 'oracle_ensemble_detailed_results.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Detailed results saved to: {output_path}")
    
    # Oracle Model Table 별도 저장
    table_path = os.path.join(results_dir, 'oracle_model_table_detailed.json')
    with open(table_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'description': 'Query별 최적 모델 매핑 (Oracle Ensemble, Detailed)',
            'model_table': {str(k): v for k, v in oracle_model_table.items()},
            'model_selection_counts': dict(model_counts),
        }, f, indent=2, ensure_ascii=False)
    print(f"Oracle Model Table saved to: {table_path}")
    
    # 통계 출력
    print("\n" + "=" * 80)
    print("Oracle Ensemble Detailed Results")
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
    
    # 환경 정리
    for env in envs.values():
        env.close()
    
    print("\n[SUCCESS] Oracle Ensemble detailed evaluation completed!")
    
    return output


if __name__ == '__main__':
    oracle_ensemble_evaluate_detailed()

