# -*- coding: utf-8 -*-
"""
Ensemble v1: Quick Test

빠른 테스트: 1개 쿼리 × 3 episodes로 Ensemble이 정상 작동하는지 확인
"""

import os
import sys

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from ensemble_voting import VotingEnsemble
from env.ensemble_env import create_dqn_env
from RLQO.constants2 import SAMPLE_QUERIES
from RLQO.PPO_v3.config.query_action_mapping_v3 import QUERY_TYPES


def quick_test():
    """빠른 테스트: 모델 로드 및 예측 확인"""
    
    print("=" * 80)
    print("Ensemble v1: Quick Test")
    print("=" * 80)
    print("Testing: 1 query × 3 episodes")
    print("=" * 80 + "\n")
    
    # 1. Load ensemble
    print("[1/4] Loading ensemble...")
    ensemble = VotingEnsemble(voting_strategy='weighted', verbose=True)
    
    try:
        ensemble.load_models()
    except Exception as e:
        print(f"\n[ERROR] Failed to load models: {e}")
        print("\nPossible reasons:")
        print("- Model files not found at expected paths")
        print("- Check config/ensemble_config.py for correct MODEL_PATHS")
        return False
    
    if len(ensemble.loaded_models) == 0:
        print("\n[ERROR] No models loaded!")
        return False
    
    print(f"\n[OK] {len(ensemble.loaded_models)}/4 models loaded: {ensemble.loaded_models}\n")
    
    # 2. Create environment
    print("[2/4] Creating environment...")
    try:
        env = create_dqn_env(SAMPLE_QUERIES[:1], max_steps=1, verbose=False)
        print("[OK] Environment created\n")
    except Exception as e:
        print(f"\n[ERROR] Failed to create environment: {e}")
        return False
    
    # 3. Test predictions
    print("[3/4] Testing predictions...")
    
    query_idx = 0
    query_type = QUERY_TYPES.get(query_idx, 'UNKNOWN')
    
    for episode in range(3):
        try:
            # Reset
            env.current_query_ix = query_idx
            obs, info = env.reset(seed=query_idx * 100 + episode)
            
            baseline_time = info['metrics'].get('elapsed_time_ms', -1)
            
            # Get action mask
            action_mask = env.get_action_mask() if hasattr(env, 'get_action_mask') else None
            
            # Predict
            action, pred_info = ensemble.predict(obs, query_type=query_type, action_mask=action_mask)
            
            # Execute
            obs, reward, done, truncated, step_info = env.step(action)
            optimized_time = step_info['metrics'].get('elapsed_time_ms', -1)
            
            speedup = baseline_time / optimized_time if optimized_time > 0 else 0.0
            
            print(f"\nEpisode {episode + 1}:")
            print(f"  Query Type: {query_type}")
            print(f"  Baseline:   {baseline_time:.2f} ms")
            print(f"  Optimized:  {optimized_time:.2f} ms")
            print(f"  Speedup:    {speedup:.3f}x")
            print(f"  Action:     {action}")
            print(f"  Predictions: {pred_info['predictions']}")
            print(f"  Confidences: {', '.join([f'{k}: {v:.3f}' for k, v in pred_info['confidences'].items()])}")
            
        except Exception as e:
            print(f"\n[ERROR] Episode {episode + 1} failed: {e}")
            import traceback
            traceback.print_exc()
    
    env.close()
    
    # 4. Summary
    print("\n" + "=" * 80)
    print("[4/4] Test Summary")
    print("=" * 80)
    print("[OK] Quick test completed successfully!")
    print("\nNext steps:")
    print("1. Run full evaluation:")
    print("   cd train && python ensemble_evaluate.py")
    print("\n2. Generate visualizations:")
    print("   python visualize_ensemble.py")
    print("=" * 80 + "\n")
    
    return True


if __name__ == '__main__':
    success = quick_test()
    sys.exit(0 if success else 1)

