# -*- coding: utf-8 -*-
"""
PPO v2 평가 스크립트

실제 DB 환경에서 모델 평가
성공 기준:
1. Avg Speedup ≥ 1.15x
2. CTE 안정성: 악화 0-1건
3. Action 다양성 > 40%
"""

import os
import sys
import argparse
import json
import numpy as np
import pandas as pd
from datetime import datetime
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

# 프로젝트 루트 경로 설정
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)

from RLQO.constants import SAMPLE_QUERIES
from RLQO.DQN_v3.env.v3_db_env import QueryPlanDBEnvV3


# DB 환경용 ActionableState Encoder Wrapper
class DBEnvV2Wrapper(QueryPlanDBEnvV3):
    """
    실제 DB 환경을 PPO v2 State로 변환
    
    v3_db_env를 사용하면서 state만 18차원으로 변환
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # State encoder import (circular import 방지)
        from RLQO.PPO_v2.env.v2_actionable_state import ActionableStateEncoder
        from RLQO.PPO_v1.utils.query_classifier import classify_query
        
        self.state_encoder = ActionableStateEncoder()
        self.query_types = [classify_query(q) for q in self.query_list]
        
        # Observation space 18차원으로 재정의
        from gymnasium import spaces
        self.observation_space = spaces.Box(
            low=0.0, high=1.0,
            shape=(18,), dtype=np.float32
        )
        
        # 이력 추적
        self.prev_action_id = -1
        self.prev_reward = 0.0
        self.current_query_type = None
    
    def reset(self, seed=None, options=None):
        """리셋 + 18차원 state 반환"""
        obs_79d, info = super().reset(seed, options)
        
        # Query 타입 설정
        query_idx = (self.current_query_ix - 1) % len(self.query_list)
        self.current_query_type = self.query_types[query_idx]
        
        # 이력 초기화
        self.prev_action_id = -1
        self.prev_reward = 0.0
        
        # 현재 힌트 (초기: 없음)
        current_hints = {
            'maxdop': 0,
            'join_hint': 'none',
            'isolation_hint': False,
            'recompile': False,
            'optimize_for_unknown': False
        }
        
        # 18차원 state 생성
        obs_18d = self.state_encoder.encode_from_query_and_metrics(
            sql=self.current_sql,
            current_metrics=self.baseline_metrics,
            current_hints=current_hints,
            prev_action_id=self.prev_action_id,
            prev_reward=self.prev_reward
        )
        
        info['query_type'] = self.current_query_type
        info['baseline_metrics'] = self.baseline_metrics  # baseline_metrics 추가
        return obs_18d, info
    
    def step(self, action_id):
        """스텝 실행 + 18차원 state 반환"""
        # 이전 보상 계산을 위한 메트릭 저장
        prev_metrics = self.current_metrics.copy() if hasattr(self, 'current_metrics') else self.baseline_metrics.copy()
        
        # 부모 step 실행 (실제 DB 쿼리 실행)
        obs_79d, reward, terminated, truncated, info = super().step(action_id)
        
        # 보상 재계산 (PPO v2 정규화)
        from RLQO.PPO_v2.env.v2_normalized_reward import calculate_reward_v2_normalized
        reward = calculate_reward_v2_normalized(
            metrics_before=prev_metrics,
            metrics_after=info['metrics'],
            baseline_metrics=self.baseline_metrics,
            query_type=self.current_query_type,
            action_id=action_id
        )
        
        # 이력 업데이트
        self.prev_action_id = action_id
        self.prev_reward = reward
        
        # 현재 힌트 추출
        current_hints = self.state_encoder.extract_hints_from_sql(self.current_sql)
        
        # 18차원 state 생성
        obs_18d = self.state_encoder.encode_from_query_and_metrics(
            sql=self.current_sql,
            current_metrics=info['metrics'],
            current_hints=current_hints,
            prev_action_id=self.prev_action_id,
            prev_reward=self.prev_reward
        )
        
        return obs_18d, reward, terminated, truncated, info


def mask_fn(env):
    """PPO용 액션 마스크 함수"""
    float_mask = env.get_action_mask()
    return float_mask.astype(bool)


def evaluate_model(model_path: str, n_episodes: int = 9, verbose: bool = True):
    """
    PPO v2 모델 평가
    
    Args:
        model_path: 평가할 모델 경로
        n_episodes: 평가 에피소드 수 (쿼리 수)
        verbose: 진행 상황 출력
    
    Returns:
        results: 평가 결과 딕셔너리
    """
    print("=" * 80)
    print(" PPO v2 모델 평가 (실제 DB 환경)")
    print("=" * 80)
    print(f"모델 경로: {model_path}")
    print(f"평가 쿼리 수: {n_episodes}")
    print(f"환경: 실제 SQL Server DB")
    print("-" * 80)
    
    # 1. 모델 로드
    print("\n[1/3] 모델 로드 중...")
    try:
        model = MaskablePPO.load(model_path)
        print("[OK] 모델 로드 완료")
    except Exception as e:
        print(f"[ERROR] 모델 로드 실패: {e}")
        return None
    
    # 2. DB 환경 생성
    print("\n[2/3] 실제 DB 환경 생성 중...")
    try:
        base_env = DBEnvV2Wrapper(
            query_list=SAMPLE_QUERIES,
            max_steps=10,
            curriculum_mode=False,
            verbose=verbose
        )
        env = ActionMasker(base_env, mask_fn)
        print("[OK] DB 환경 생성 완료")
        print(f"     Observation space: {env.observation_space}")
    except Exception as e:
        print(f"[ERROR] 환경 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 3. 평가 실행
    print("\n[3/3] 평가 실행 중...")
    print("-" * 80)
    
    results = []
    action_counts = {}
    cte_degradations = []
    
    for episode in range(n_episodes):
        obs, info = env.reset()
        query_type = info.get('query_type', 'UNKNOWN')
        baseline_time = info.get('baseline_metrics', {}).get('elapsed_time_ms', 0)
        
        episode_reward = 0
        episode_actions = []
        best_time = baseline_time
        
        if verbose:
            print(f"\n[Query {episode + 1}/{n_episodes}] Type: {query_type}, Baseline: {baseline_time:.1f}ms")
        
        done = False
        step_count = 0
        
        while not done and step_count < 10:
            # 모델로 액션 선택 (ActionMasker가 자동으로 마스킹 처리)
            action, _states = model.predict(obs, deterministic=True)
            
            # 스텝 실행
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            
            episode_reward += reward
            episode_actions.append(action)
            
            # 액션 카운팅
            action_name = base_env.actions[action]['name']
            action_counts[action_name] = action_counts.get(action_name, 0) + 1
            
            # 최고 성능 추적
            current_time = info['metrics']['elapsed_time_ms']
            if current_time < best_time:
                best_time = current_time
            
            if verbose:
                print(f"  Step {step_count + 1}: Action={action_name}, Time={current_time:.1f}ms, Reward={reward:.3f}")
            
            step_count += 1
        
        # 최종 speedup 계산
        final_time = info['metrics']['elapsed_time_ms']
        
        # baseline_time이 0인 경우 처리
        if baseline_time <= 0:
            baseline_time = final_time if final_time > 0 else 1.0
        
        speedup = baseline_time / max(final_time, 0.1)
        improvement_pct = ((baseline_time - final_time) / baseline_time) * 100
        
        # CTE 악화 추적
        if query_type == 'CTE' and speedup < 1.0:
            cte_degradations.append(episode + 1)
        
        results.append({
            'query_id': episode + 1,
            'query_type': query_type,
            'baseline_ms': baseline_time,
            'final_ms': final_time,
            'best_ms': best_time,
            'speedup': speedup,
            'improvement_pct': improvement_pct,
            'total_reward': episode_reward,
            'steps': step_count,
            'actions': [base_env.actions[a]['name'] for a in episode_actions]
        })
        
        if verbose:
            print(f"  [결과] Speedup: {speedup:.2f}x, Improvement: {improvement_pct:+.1f}%, Reward: {episode_reward:.2f}")
    
    env.close()
    
    # 4. 결과 요약
    print("\n" + "=" * 80)
    print(" 평가 결과 요약")
    print("=" * 80)
    
    df = pd.DataFrame(results)
    
    avg_speedup = df['speedup'].mean()
    avg_improvement = df['improvement_pct'].mean()
    total_actions = sum(action_counts.values())
    
    print(f"평균 Speedup: {avg_speedup:.2f}x")
    print(f"평균 개선률: {avg_improvement:+.1f}%")
    print(f"총 액션 수: {total_actions}")
    print(f"CTE 악화 건수: {len(cte_degradations)}/3 (Query IDs: {cte_degradations})")
    print("-" * 80)
    
    # 액션 다양성
    print("\n액션 분포:")
    sorted_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)
    for action_name, count in sorted_actions[:10]:
        percentage = (count / total_actions) * 100
        print(f"  {action_name}: {count}회 ({percentage:.1f}%)")
    
    # 가장 많이 선택된 액션의 비율
    max_action_count = max(action_counts.values()) if action_counts else 0
    max_action_pct = (max_action_count / total_actions) * 100 if total_actions > 0 else 0
    action_diversity = 100 - max_action_pct
    
    print(f"\n액션 다양성: {action_diversity:.1f}% (가장 많은 액션 외 비율)")
    print("-" * 80)
    
    # 성공 기준 평가
    print("\n성공 기준 (3개 중 2개 이상):")
    criterion_1 = avg_speedup >= 1.15
    criterion_2 = len(cte_degradations) <= 1
    criterion_3 = action_diversity > 40.0
    
    print(f"1. Avg Speedup ≥ 1.15x: {'[OK]' if criterion_1 else '[FAIL]'} ({avg_speedup:.2f}x)")
    print(f"2. CTE 안정성 (악화 0-1건): {'[OK]' if criterion_2 else '[FAIL]'} ({len(cte_degradations)}건)")
    print(f"3. Action 다양성 > 40%: {'[OK]' if criterion_3 else '[FAIL]'} ({action_diversity:.1f}%)")
    
    success_count = sum([criterion_1, criterion_2, criterion_3])
    overall_success = success_count >= 2
    
    print(f"\n전체 결과: {'[SUCCESS]' if overall_success else '[FAIL]'} ({success_count}/3 충족)")
    print("=" * 80)
    
    # CSV 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = f"Apollo.ML/artifacts/RLQO/results/ppo_v2_evaluation_{timestamp}.csv"
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n결과 CSV 저장: {csv_path}")
    
    return {
        'results': results,
        'avg_speedup': avg_speedup,
        'avg_improvement': avg_improvement,
        'action_counts': action_counts,
        'action_diversity': action_diversity,
        'cte_degradations': cte_degradations,
        'success': overall_success,
        'csv_path': csv_path
    }


def main():
    parser = argparse.ArgumentParser(description='PPO v2 모델 평가')
    parser.add_argument('--model', type=str, 
                        default='Apollo.ML/artifacts/RLQO/models/ppo_v2_realdb_50k.zip',
                        help='평가할 모델 경로')
    parser.add_argument('--n_episodes', type=int, default=9,
                        help='평가 에피소드 수 (쿼리 수)')
    parser.add_argument('--verbose', action='store_true', default=True,
                        help='상세 출력')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.model):
        print(f"[ERROR] 모델 파일이 존재하지 않습니다: {args.model}")
        return
    
    results = evaluate_model(
        model_path=args.model,
        n_episodes=args.n_episodes,
        verbose=args.verbose
    )
    
    if results and results['success']:
        print("\n[다음 단계] RealDB Fine-tuning 고려")
        print("성공 기준을 충족했습니다. 실제 DB에서 fine-tuning을 진행할 수 있습니다.")
    elif results:
        print("\n[다음 단계] Ensemble 시도")
        print("성공 기준 미달. DQN v3와 PPO v2의 Ensemble을 고려하세요.")


if __name__ == "__main__":
    main()

