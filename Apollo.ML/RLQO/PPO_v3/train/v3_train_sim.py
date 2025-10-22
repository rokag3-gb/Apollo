# -*- coding: utf-8 -*-
"""
PPO v3 Simulation Training Script

Improvements:
- 30 queries
- 44 actions (FAST 10, MAXDOP 10, ISOLATION 3, Advanced DBA 10)
- 18-dim actionable state
- Enhanced exploration: entropy_coef 0.03
- Gradient clipping: max_grad_norm 0.5
- Learning rate scheduling
"""

import os
import sys
from datetime import datetime
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.monitor import Monitor

# Project root path setup
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)

from RLQO.PPO_v3.env.v3_sim_env import QueryPlanSimEnvPPOv3
from RLQO.PPO_v3.train.callbacks import EarlyStoppingCallback, ActionDiversityCallback

# Load 30 queries from constants2.py
sys.path.insert(0, os.path.join(apollo_ml_dir, 'RLQO'))
from constants2 import SAMPLE_QUERIES

# ============================================================================
# Hyperparameters (Simulation - PPO v3)
# ============================================================================
SIM_TIMESTEPS = 100_000  # 100K steps
SIM_LEARNING_RATE = 3e-4
SIM_N_STEPS = 2048
SIM_BATCH_SIZE = 64
SIM_N_EPOCHS = 10
SIM_GAMMA = 0.99
SIM_ENT_COEF = 0.03  # Enhanced exploration
SIM_CLIP_RANGE = 0.2
SIM_MAX_GRAD_NORM = 0.5  # ★ Gradient clipping

# Path configuration (absolute paths from project root)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_DIR = os.path.join(apollo_ml_dir, "artifacts", "RLQO")

SIM_LOG_DIR = os.path.join(BASE_DIR, "logs", "ppo_v3_sim")
SIM_MODEL_PATH = os.path.join(BASE_DIR, "models", "ppo_v3_sim_100k.zip")
SIM_CHECKPOINT_DIR = os.path.join(BASE_DIR, "models", "checkpoints", "ppo_v3_sim")

TB_LOG_DIR = os.path.join(BASE_DIR, "tb", "ppo_v3_sim")

# Create directories
for directory in [SIM_LOG_DIR, SIM_CHECKPOINT_DIR]:
    os.makedirs(directory, exist_ok=True)


def mask_fn(env):
    """Action mask function for PPO"""
    float_mask = env.get_action_mask()
    return float_mask.astype(bool)


def make_masked_env(verbose=False):
    """
    Create Simulation environment with action masking
    
    Args:
        verbose: Whether to print progress
    
    Returns:
        env: Simulation environment wrapped with ActionMasker
    """
    env = QueryPlanSimEnvPPOv3(
        query_list=SAMPLE_QUERIES,
        max_steps=10,
        curriculum_mode=True,  # Curriculum Learning based on baseline time
        verbose=verbose
    )
    
    env = ActionMasker(env, mask_fn)
    env = Monitor(env, SIM_LOG_DIR)
    
    return env


def train_simulation():
    """
    PPO v3 Training in Simulation Environment
    
    Improvements:
    - 30 queries
    - 44 actions
    - Gradient clipping
    - Learning rate scheduling
    """
    print("=" * 80)
    print(" PPO v3 Simulation Training Start")
    print("=" * 80)
    print(f"Timestamp: {TIMESTAMP}")
    print(f"Goal: Improve performance with 30 queries + 44 actions")
    print(f"Algorithm: MaskablePPO + 18-dim Actionable State")
    print(f"Environment: XGBoost Simulation")
    print(f"Timesteps: {SIM_TIMESTEPS:,}")
    print(f"Query Count: {len(SAMPLE_QUERIES)}")
    print(f"Estimated Time: 30-45 minutes")
    print("-" * 80)
    print(f"PPO v3 Key Improvements:")
    print(f"  1. Queries: 9 -> 30")
    print(f"  2. Actions: 19 -> 44 (FAST 10, MAXDOP 10, ISOLATION 3, Advanced DBA 10)")
    print(f"  3. State: 18-dim actionable features (maintained)")
    print(f"  4. Reward: Log scale normalized [-1, +1] (maintained)")
    print(f"  5. Gradient clipping: {SIM_MAX_GRAD_NORM}")
    print("-" * 80)
    print(f"Hyperparameters:")
    print(f"  Learning Rate: {SIM_LEARNING_RATE}")
    print(f"  N Steps: {SIM_N_STEPS}")
    print(f"  Batch Size: {SIM_BATCH_SIZE}")
    print(f"  N Epochs: {SIM_N_EPOCHS}")
    print(f"  Gamma: {SIM_GAMMA}")
    print(f"  Entropy Coef: {SIM_ENT_COEF}")
    print(f"  Clip Range: {SIM_CLIP_RANGE}")
    print(f"  Max Grad Norm: {SIM_MAX_GRAD_NORM}")
    print("=" * 80)
    
    # 1. Environment setup
    print("\n[1/4] Creating Simulation environment...")
    try:
        env = make_masked_env(verbose=False)
        print("[OK] Environment created")
        print(f"     Action space: {env.action_space}")
        print(f"     Observation space: {env.observation_space}")
    except Exception as e:
        print(f"[ERROR] Environment creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 2. Model setup
    print("\n[2/4] Creating MaskablePPO model...")
    try:
        model = MaskablePPO(
            'MlpPolicy',
            env,
            learning_rate=SIM_LEARNING_RATE,
            n_steps=SIM_N_STEPS,
            batch_size=SIM_BATCH_SIZE,
            n_epochs=SIM_N_EPOCHS,
            gamma=SIM_GAMMA,
            ent_coef=SIM_ENT_COEF,
            clip_range=SIM_CLIP_RANGE,
            max_grad_norm=SIM_MAX_GRAD_NORM,  # ★ Gradient clipping
            tensorboard_log=TB_LOG_DIR,
            verbose=1
        )
        print("[OK] Model created")
        print(f"     Total parameters: {sum(p.numel() for p in model.policy.parameters()):,}")
    except Exception as e:
        print(f"[ERROR] Model creation failed: {e}")
        import traceback
        traceback.print_exc()
        env.close()
        return None
    
    # 3. Callback setup
    print("\n[3/4] Setting up callbacks...")
    try:
        checkpoint_callback = CheckpointCallback(
            save_freq=3_000,  # Save every 3K steps (5K -> 3K)
            save_path=SIM_CHECKPOINT_DIR,
            name_prefix="ppo_v3_sim"
        )
        
        # Early stopping disabled for Simulation (limited effect without cache)
        # early_stopping_callback = EarlyStoppingCallback(
        #     patience=10,
        #     min_delta=0.01,
        #     verbose=True
        # )
        
        action_diversity_callback = ActionDiversityCallback(
            max_consecutive=10,
            verbose=False
        )
        
        callbacks = [checkpoint_callback, action_diversity_callback]
        print("[OK] Callbacks configured")
        print(f"     Checkpoint frequency: 3,000 steps")
        print(f"     Early stopping: Disabled (Full training for Simulation)")
        print(f"     Action diversity monitoring: ON")
    except Exception as e:
        print(f"[ERROR] Callback setup failed: {e}")
        env.close()
        return None
    
    # 4. Start training
    print("\n[4/4] Starting training...")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    print("TIP: Monitor in real-time with TensorBoard:")
    print(f"     tensorboard --logdir {TB_LOG_DIR}")
    print("-" * 80)
    
    try:
        model.learn(
            total_timesteps=SIM_TIMESTEPS,
            callback=callbacks,
            tb_log_name="ppo_v3_sim"
        )
        
        # Save model
        model.save(SIM_MODEL_PATH)
        print(f"\n[OK] Training complete! Model saved: {SIM_MODEL_PATH}")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n[INFO] Training interrupted by user")
        print(f"[INFO] Last checkpoint: {SIM_CHECKPOINT_DIR}")
        
        partial_model_path = f"{BASE_DIR}models/ppo_v3_sim_partial.zip"
        model.save(partial_model_path)
        print(f"[INFO] Partial model saved: {partial_model_path}")
        
    except Exception as e:
        print(f"[ERROR] Training failed: {e}")
        import traceback
        traceback.print_exc()
        env.close()
        return None
    
    env.close()
    
    return model


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PPO v3 Simulation Training')
    parser.add_argument('--test', action='store_true',
                       help='Run environment test only')
    
    args = parser.parse_args()
    
    if args.test:
        print("=" * 80)
        print(" PPO v3 Simulation Environment Test")
        print("=" * 80)
        
        try:
            env = make_masked_env(verbose=True)
            print("[OK] Environment created")
            
            obs, info = env.reset()
            print(f"[OK] Reset complete: obs shape={obs.shape}")
            
            action_mask = env.get_action_mask()
            valid_actions = np.where(action_mask)[0]
            print(f"[OK] Action mask: {len(valid_actions)} valid actions")
            
            env.close()
            print("\n[SUCCESS] Environment test complete!")
            
        except Exception as e:
            print(f"\n[ERROR] Environment test failed: {e}")
            import traceback
            traceback.print_exc()
        
        return
    
    model = train_simulation()
    
    if model:
        print("\n" + "=" * 80)
        print(" Simulation Training Complete!")
        print("=" * 80)
        print(f"Model path: {SIM_MODEL_PATH}")
        print(f"TensorBoard logs: {TB_LOG_DIR}")
        print(f"Checkpoints: {SIM_CHECKPOINT_DIR}")
        print("-" * 80)
        print("\nNext step: RealDB Fine-tuning")
        print(f"   python Apollo.ML/RLQO/PPO_v3/train/v3_train_realdb.py")
        print("=" * 80)
    else:
        print("\n[ERROR] Training failed!")


if __name__ == "__main__":
    import numpy as np
    main()
