# -*- coding: utf-8 -*-
"""
PPO v3 평가 스크립트

30개 쿼리에 대한 성능 평가 및 분석:
- 쿼리별 성능 추적
- Query 타입별 평균 성능
- Action 선택 분포
- Speedup 분포 (히스토그램)
"""

import os
import sys
import numpy as np
import json
from datetime import datetime
from collections import defaultdict
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

# 프로젝트 루트 경로 설정
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)

from RLQO.PPO_v3.env.v3_db_env import QueryPlanDBEnvPPOv3

# constants2.py에서 30개 쿼리 로드
sys.path.insert(0, os.path.join(apollo_ml_dir, 'RLQO'))
from constants2 import SAMPLE_QUERIES
from RLQO.PPO_v3.config.query_action_mapping_v3 import QUERY_TYPES


def mask_fn(env):
    """PPO용 액션 마스크 함수"""
    float_mask = env.get_action_mask()
    return float_mask.astype(bool)


def evaluate_model(model_path: str, num_episodes: int = 3, max_steps: int = 10):
    """
    모델 평가 및 성능 분석
    
    Args:
        model_path: 평가할 모델 경로
        num_episodes: 에피소드 수 (각 쿼리별)
        max_steps: 쿼리당 최대 스텝 수
    
    Returns:
        results: 평가 결과 딕셔너리
    """
    print("=" * 80)
    print(" PPO v3 모델 평가")
    print("=" * 80)
    print(f"모델: {model_path}")
    print(f"쿼리 개수: {len(SAMPLE_QUERIES)}")
    print(f"에피소드 수: {num_episodes}")
    print(f"최대 스텝: {max_steps}")
    print("=" * 80)
    
    # 환경 생성
    env = QueryPlanDBEnvPPOv3(
        query_list=SAMPLE_QUERIES,
        max_steps=max_steps,
        curriculum_mode=False,  # 평가 시에는 curriculum 비활성화
        verbose=False
    )
    env = ActionMasker(env, mask_fn)
    
    # 모델 로드
    print(f"\n[1/4] 모델 로드 중...")
    model = MaskablePPO.load(model_path, env=env)
    print("[OK] 모델 로드 완료")
    
    # 평가 결과 저장
    results = {
        'query_results': {},  # 쿼리별 결과
        'type_results': defaultdict(list),  # 타입별 결과
        'action_counts': defaultdict(int),  # 액션 선택 빈도
        'speedups': [],  # 모든 speedup 값
        'total_queries': len(SAMPLE_QUERIES),
        'num_episodes': num_episodes
    }
    
    # 각 쿼리별 평가
    print(f"\n[2/4] 쿼리별 평가 중...")
    total_evaluations = len(SAMPLE_QUERIES) * num_episodes
    eval_count = 0
    
    for query_idx in range(len(SAMPLE_QUERIES)):
        query_type = QUERY_TYPES.get(query_idx, 'UNKNOWN')
        query_speedups = []
        query_actions = []
        
        for episode in range(num_episodes):
            eval_count += 1
            if eval_count % 10 == 0:
                print(f"   진행: {eval_count}/{total_evaluations} ({eval_count*100//total_evaluations}%)")
            
            obs, info = env.reset()
            
            # 현재 쿼리 인덱스가 맞는지 확인
            if env.unwrapped.current_query_ix % len(SAMPLE_QUERIES) != query_idx:
                # 강제로 특정 쿼리로 이동
                env.unwrapped.current_query_ix = query_idx
                obs, info = env.reset()
            
            baseline_time = info['baseline_metrics']['elapsed_time_ms']
            
            done = False
            step_count = 0
            best_time = baseline_time
            best_action = None
            
            while not done and step_count < max_steps:
                action_masks = env.action_masks()
                action, _states = model.predict(obs, action_masks=action_masks, deterministic=True)
                
                obs, reward, terminated, truncated, info = env.step(action)
                done = terminated or truncated
                step_count += 1
                
                current_time = info['metrics']['elapsed_time_ms']
                if current_time < best_time:
                    best_time = current_time
                    best_action = action
                
                query_actions.append(int(action))
                results['action_counts'][int(action)] += 1
            
            # Speedup 계산
            speedup = baseline_time / max(best_time, 0.1)
            query_speedups.append(speedup)
            results['speedups'].append(speedup)
        
        # 쿼리별 평균 speedup 계산
        avg_speedup = np.mean(query_speedups)
        std_speedup = np.std(query_speedups)
        
        results['query_results'][query_idx] = {
            'query_type': query_type,
            'avg_speedup': avg_speedup,
            'std_speedup': std_speedup,
            'speedups': query_speedups,
            'actions': query_actions
        }
        
        # 타입별 결과 집계
        results['type_results'][query_type].append(avg_speedup)
    
    print(f"   완료: {total_evaluations}/{total_evaluations} (100%)")
    
    # 통계 계산
    print(f"\n[3/4] 통계 계산 중...")
    results['overall_avg_speedup'] = np.mean(results['speedups'])
    results['overall_std_speedup'] = np.std(results['speedups'])
    results['overall_median_speedup'] = np.median(results['speedups'])
    
    # 타입별 평균 계산
    results['type_avg_speedups'] = {}
    for query_type, speedups in results['type_results'].items():
        results['type_avg_speedups'][query_type] = {
            'mean': np.mean(speedups),
            'std': np.std(speedups),
            'count': len(speedups)
        }
    
    print("[OK] 통계 계산 완료")
    
    # 결과 출력
    print(f"\n[4/4] 결과 요약:")
    print("-" * 80)
    print(f"전체 평균 Speedup: {results['overall_avg_speedup']:.3f}x ± {results['overall_std_speedup']:.3f}")
    print(f"중앙값 Speedup: {results['overall_median_speedup']:.3f}x")
    print(f"최대 Speedup: {max(results['speedups']):.3f}x")
    print(f"최소 Speedup: {min(results['speedups']):.3f}x")
    
    print(f"\n타입별 평균 Speedup:")
    for query_type in sorted(results['type_avg_speedups'].keys()):
        stats = results['type_avg_speedups'][query_type]
        print(f"  {query_type:15s}: {stats['mean']:.3f}x ± {stats['std']:.3f} ({stats['count']}개 쿼리)")
    
    print(f"\n상위 10개 액션:")
    top_actions = sorted(results['action_counts'].items(), key=lambda x: x[1], reverse=True)[:10]
    for action_id, count in top_actions:
        action_name = env.unwrapped.actions[action_id]['name']
        print(f"  Action {action_id:2d} ({action_name:30s}): {count:4d}회")
    
    print(f"\n쿼리별 성능 (상위 10개):")
    query_results_sorted = sorted(
        results['query_results'].items(),
        key=lambda x: x[1]['avg_speedup'],
        reverse=True
    )[:10]
    for query_idx, result in query_results_sorted:
        print(f"  Query {query_idx:2d} ({result['query_type']:15s}): {result['avg_speedup']:.3f}x ± {result['std_speedup']:.3f}")
    
    print("=" * 80)
    
    env.close()
    
    return results


def save_results(results: dict, output_path: str):
    """
    결과를 JSON 파일로 저장
    
    Args:
        results: 평가 결과
        output_path: 출력 파일 경로
    """
    # NumPy 타입을 Python 기본 타입으로 변환
    def convert_numpy(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, defaultdict):
            return dict(obj)
        elif isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(item) for item in obj]
        return obj
    
    results_serializable = convert_numpy(results)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results_serializable, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] 결과 저장: {output_path}")


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PPO v3 모델 평가')
    parser.add_argument('--model', type=str, required=True,
                       help='평가할 모델 경로')
    parser.add_argument('--episodes', type=int, default=3,
                       help='쿼리당 에피소드 수')
    parser.add_argument('--max-steps', type=int, default=10,
                       help='쿼리당 최대 스텝 수')
    parser.add_argument('--output', type=str, default=None,
                       help='결과 저장 경로 (JSON)')
    
    args = parser.parse_args()
    
    # 모델 존재 확인
    if not os.path.exists(args.model):
        print(f"[ERROR] 모델 파일을 찾을 수 없습니다: {args.model}")
        return
    
    # 평가 실행
    start_time = datetime.now()
    print(f"평가 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        results = evaluate_model(
            model_path=args.model,
            num_episodes=args.episodes,
            max_steps=args.max_steps
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n평가 완료!")
        print(f"소요 시간: {duration:.1f}초")
        
        # 결과 저장
        if args.output:
            output_path = args.output
        else:
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            output_path = f"Apollo.ML/artifacts/RLQO/evaluation/ppo_v3_eval_{timestamp}.json"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        save_results(results, output_path)
        
    except Exception as e:
        print(f"\n[ERROR] 평가 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

