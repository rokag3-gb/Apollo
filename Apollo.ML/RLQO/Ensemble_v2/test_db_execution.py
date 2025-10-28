# -*- coding: utf-8 -*-
"""
Ensemble v2: DB 실행 테스트

각 환경이 DB에 제대로 연결되고 쿼리를 실행하는지 확인합니다.
"""

import os
import sys

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..'))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
project_root = os.path.abspath(os.path.join(apollo_ml_dir, '..'))

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)

from RLQO.constants2 import SAMPLE_QUERIES
from sb3_contrib.common.wrappers import ActionMasker


def test_environment(env_name, env, query_idx=0):
    """
    환경 테스트
    
    Args:
        env_name: 환경 이름
        env: 환경 인스턴스
        query_idx: 테스트할 쿼리 인덱스
    """
    print(f"\n{'='*80}")
    print(f"Testing {env_name}")
    print(f"{'='*80}")
    
    try:
        # Query index 설정
        if hasattr(env, 'unwrapped'):
            env.unwrapped.current_query_ix = query_idx
            obs, info = env.reset()
        elif hasattr(env, 'current_query_ix'):
            env.current_query_ix = query_idx
            obs, info = env.reset()
        else:
            obs, info = env.reset(options={'query_index': query_idx})
        
        print(f"[OK] Environment reset successful")
        print(f"  Query index: {query_idx}")
        print(f"  Observation shape: {obs.shape}")
        print(f"  Info keys: {list(info.keys())}")
        
        # Baseline 확인
        baseline_ms = info.get('baseline_ms', None)
        if baseline_ms is not None:
            print(f"  Baseline: {baseline_ms:.2f} ms")
            if baseline_ms > 0:
                print(f"  [SUCCESS] Baseline > 0!")
            else:
                print(f"  [WARNING] Baseline = 0!")
        else:
            print(f"  [ERROR] No baseline_ms in info!")
        
        # Action 실행 테스트 (NO_ACTION)
        print(f"\n[Test] Executing NO_ACTION (baseline measurement)...")
        
        # 환경에 따라 NO_ACTION 다름
        if env_name in ['DQN v4', 'PPO v3']:
            # Discrete: NO_ACTION = 마지막 액션 (18 or 43)
            action = info.get('action_space_size', 19) - 1
        else:
            # Continuous: [0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            import numpy as np
            action = np.array([0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        
        obs, reward, terminated, truncated, step_info = env.step(action)
        
        print(f"[OK] Step executed")
        print(f"  Reward: {reward:.4f}")
        print(f"  Terminated: {terminated}")
        print(f"  Step info keys: {list(step_info.keys())}")
        
        # Optimized time 확인
        optimized_ms = step_info.get('optimized_ms', None)
        if optimized_ms is not None:
            print(f"  Optimized time: {optimized_ms:.2f} ms")
            
            if baseline_ms and baseline_ms > 0:
                speedup = baseline_ms / optimized_ms if optimized_ms > 0 else 0
                print(f"  Speedup: {speedup:.3f}x")
                
                if speedup > 0:
                    print(f"  [SUCCESS] Speedup calculated!")
                else:
                    print(f"  [WARNING] Speedup = 0!")
        else:
            print(f"  [ERROR] No optimized_ms in step_info!")
        
        return True, baseline_ms, optimized_ms
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None


def main():
    """메인 테스트"""
    print("="*80)
    print("Ensemble v2 DB Execution Test")
    print("="*80)
    print("Testing first 3 queries with each environment...")
    print()
    
    queries = SAMPLE_QUERIES[:3]
    
    results = {}
    
    # 1. DQN v4 환경 테스트
    print("\n" + "="*80)
    print("1. DQN v4 Environment")
    print("="*80)
    try:
        from RLQO.DQN_v4.env.v4_db_env import QueryPlanDBEnvV4
        
        env = QueryPlanDBEnvV4(
            query_list=queries,
            max_steps=1,
            curriculum_mode=False,
            verbose=True  # 디버깅용 verbose
        )
        
        results['dqn_v4'] = []
        for query_idx in range(len(queries)):
            success, baseline, optimized = test_environment('DQN v4', env, query_idx)
            results['dqn_v4'].append({
                'success': success,
                'baseline_ms': baseline,
                'optimized_ms': optimized
            })
        
        env.close()
        
    except Exception as e:
        print(f"[ERROR] DQN v4 environment failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 2. PPO v3 환경 테스트
    print("\n" + "="*80)
    print("2. PPO v3 Environment")
    print("="*80)
    try:
        from RLQO.PPO_v3.env.v3_db_env import QueryPlanDBEnvPPOv3
        
        ppo_env = QueryPlanDBEnvPPOv3(
            query_list=queries,
            max_steps=1,
            curriculum_mode=False,
            verbose=True  # 디버깅용 verbose
        )
        
        def mask_fn(env_instance):
            float_mask = env_instance.get_action_mask()
            return float_mask.astype(bool)
        
        env = ActionMasker(ppo_env, mask_fn)
        
        results['ppo_v3'] = []
        for query_idx in range(len(queries)):
            success, baseline, optimized = test_environment('PPO v3', env, query_idx)
            results['ppo_v3'].append({
                'success': success,
                'baseline_ms': baseline,
                'optimized_ms': optimized
            })
        
        env.close()
        
    except Exception as e:
        print(f"[ERROR] PPO v3 environment failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. DDPG v1 환경 테스트
    print("\n" + "="*80)
    print("3. DDPG v1 Environment")
    print("="*80)
    try:
        from RLQO.DDPG_v1.env.ddpg_db_env import QueryPlanRealDBEnvDDPGv1
        
        env = QueryPlanRealDBEnvDDPGv1(
            query_list=queries,
            max_steps=1,
            verbose=True  # 디버깅용 verbose
        )
        
        results['ddpg_v1'] = []
        for query_idx in range(len(queries)):
            success, baseline, optimized = test_environment('DDPG v1', env, query_idx)
            results['ddpg_v1'].append({
                'success': success,
                'baseline_ms': baseline,
                'optimized_ms': optimized
            })
        
        env.close()
        
    except Exception as e:
        print(f"[ERROR] DDPG v1 environment failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. SAC v1 환경 테스트
    print("\n" + "="*80)
    print("4. SAC v1 Environment")
    print("="*80)
    try:
        from RLQO.SAC_v1.env.sac_db_env import make_sac_db_env
        
        env = make_sac_db_env(
            query_list=queries,
            max_steps=1,
            verbose=True  # 디버깅용 verbose
        )
        
        results['sac_v1'] = []
        for query_idx in range(len(queries)):
            success, baseline, optimized = test_environment('SAC v1', env, query_idx)
            results['sac_v1'].append({
                'success': success,
                'baseline_ms': baseline,
                'optimized_ms': optimized
            })
        
        env.close()
        
    except Exception as e:
        print(f"[ERROR] SAC v1 environment failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 결과 요약
    print("\n" + "="*80)
    print("Test Results Summary")
    print("="*80)
    
    for env_name, query_results in results.items():
        print(f"\n{env_name.upper()}:")
        for i, result in enumerate(query_results):
            if result['success']:
                baseline = result['baseline_ms'] or 0
                optimized = result['optimized_ms'] or 0
                speedup = baseline / optimized if optimized > 0 else 0
                
                status = "✓" if baseline > 0 and optimized > 0 else "✗"
                print(f"  Query {i}: {status} Baseline={baseline:.2f}ms, Optimized={optimized:.2f}ms, Speedup={speedup:.3f}x")
            else:
                print(f"  Query {i}: ✗ FAILED")
    
    # 전체 요약
    print("\n" + "="*80)
    print("Overall Summary")
    print("="*80)
    
    total_tests = sum(len(r) for r in results.values())
    successful_tests = sum(1 for r in results.values() for result in r if result['success'])
    valid_baselines = sum(1 for r in results.values() for result in r 
                          if result['baseline_ms'] and result['baseline_ms'] > 0)
    
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful_tests}/{total_tests}")
    print(f"Valid baselines (> 0): {valid_baselines}/{total_tests}")
    
    if valid_baselines > 0:
        print("\n[SUCCESS] At least some environments are working correctly!")
    else:
        print("\n[ERROR] No valid baselines found - DB connection or query execution issue!")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()

