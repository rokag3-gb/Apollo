# -*- coding: utf-8 -*-
"""
DDPG v1 RealDB Fine-tuning Script

Simulation에서 학습한 모델을 실제 DB에서 Fine-tuning
- 50K timesteps
- Lower learning rate (5e-5)
- Lower noise (σ=0.1)
"""

import os
import sys
from datetime import datetime
import numpy as np

# Stable-Baselines3 imports
from stable_baselines3 import DDPG
from stable_baselines3.common.noise import OrnsteinUhlenbeckActionNoise
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.monitor import Monitor

# Project root path setup
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)

from RLQO.DDPG_v1.env.ddpg_db_env import QueryPlanRealDBEnvDDPGv1

# Load 30 queries
sys.path.insert(0, os.path.join(apollo_ml_dir, 'RLQO'))
from constants2 import SAMPLE_QUERIES

# ============================================================================
# Hyperparameters (RealDB Fine-tuning - DDPG v1)
# ============================================================================
REAL_TIMESTEPS = 50_000  # 50K steps
REAL_LEARNING_RATE = 5e-5  # Much lower than simulation
REAL_BUFFER_SIZE = 50_000
REAL_BATCH_SIZE = 64  # Smaller batch
REAL_GAMMA = 0.99
REAL_TAU = 0.001
REAL_TRAIN_FREQ = 1
REAL_GRADIENT_STEPS = 1

# OU noise for fine-tuning (lower exploration)
REAL_OU_SIGMA = 0.1  # Lower noise
REAL_OU_THETA = 0.15

# Path configuration
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_DIR = os.path.join(apollo_ml_dir, "artifacts", "RLQO")

# Pre-trained model from simulation
SIM_MODEL_PATH = os.path.join(BASE_DIR, "models", "ddpg_v1_sim_100k.zip")

REAL_LOG_DIR = os.path.join(BASE_DIR, "logs", "ddpg_v1_realdb")
REAL_MODEL_PATH = os.path.join(BASE_DIR, "models", "ddpg_v1_realdb_50k.zip")
REAL_CHECKPOINT_DIR = os.path.join(BASE_DIR, "models", "checkpoints", "ddpg_v1_realdb")

TB_LOG_DIR = os.path.join(BASE_DIR, "tb", "ddpg_v1_realdb")

# Create directories
for directory in [REAL_LOG_DIR, REAL_CHECKPOINT_DIR, TB_LOG_DIR]:
    os.makedirs(directory, exist_ok=True)


def make_env(verbose=False):
    """
    Create RealDB environment
    
    Args:
        verbose: Whether to print progress
    
    Returns:
        env: RealDB environment
    """
    env = QueryPlanRealDBEnvDDPGv1(
        query_list=SAMPLE_QUERIES,
        max_steps=10,
        timeout_seconds=30,
        verbose=verbose
    )
    
    env = Monitor(env, REAL_LOG_DIR)
    
    return env


def train_realdb():
    """
    DDPG v1 Fine-tuning in RealDB Environment
    
    핵심 특징:
    - Pre-trained model from simulation
    - Lower learning rate for stability
    - Lower exploration noise
    - Actual SQL Server execution
    """
    print("=" * 80)
    print(" DDPG v1 RealDB Fine-tuning Start")
    print("=" * 80)
    print(f"Timestamp: {TIMESTAMP}")
    print(f"Goal: Fine-tune simulation model on real database")
    print(f"Algorithm: DDPG (Deep Deterministic Policy Gradient)")
    print(f"Environment: SQL Server RealDB")
    print(f"Timesteps: {REAL_TIMESTEPS:,}")
    print(f"Query Count: {len(SAMPLE_QUERIES)}")
    print(f"Estimated Time: 40-60 minutes")
    print("-" * 80)
    print(f"Fine-tuning Settings:")
    print(f"  1. Pre-trained model: {SIM_MODEL_PATH}")
    print(f"  2. Learning Rate: {REAL_LEARNING_RATE} (lower)")
    print(f"  3. OU Noise: σ={REAL_OU_SIGMA} (lower exploration)")
    print(f"  4. Replay Buffer: {REAL_BUFFER_SIZE:,}")
    print(f"  5. Batch Size: {REAL_BATCH_SIZE}")
    print("=" * 80)
    
    # Check pre-trained model
    if not os.path.exists(SIM_MODEL_PATH):
        print(f"\n[ERROR] Pre-trained model not found: {SIM_MODEL_PATH}")
        print(f"Please run simulation training first:")
        print(f"  python Apollo.ML/RLQO/DDPG_v1/train/ddpg_train_sim.py")
        return
    
    print(f"\n✓ Pre-trained model found: {SIM_MODEL_PATH}")
    
    # Create environment
    print("\n[1/3] Creating RealDB environment...")
    env = make_env(verbose=True)
    
    print(f"Action space: {env.action_space}")
    print(f"Observation space: {env.observation_space}")
    
    # Load pre-trained model
    print("\n[2/3] Loading pre-trained model...")
    try:
        model = DDPG.load(
            SIM_MODEL_PATH,
            env=env,
            device="auto"
        )
        print(f"✓ Model loaded successfully")
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        return
    
    # Update hyperparameters for fine-tuning
    print("\n[3/3] Updating hyperparameters for fine-tuning...")
    
    # Update learning rate
    model.learning_rate = REAL_LEARNING_RATE
    if hasattr(model, 'actor') and hasattr(model.actor, 'optimizer'):
        for param_group in model.actor.optimizer.param_groups:
            param_group['lr'] = REAL_LEARNING_RATE
    if hasattr(model, 'critic') and hasattr(model.critic, 'optimizer'):
        for param_group in model.critic.optimizer.param_groups:
            param_group['lr'] = REAL_LEARNING_RATE
    
    # Update action noise (lower exploration)
    n_actions = env.action_space.shape[0]
    model.action_noise = OrnsteinUhlenbeckActionNoise(
        mean=np.zeros(n_actions),
        sigma=REAL_OU_SIGMA * np.ones(n_actions),
        theta=REAL_OU_THETA
    )
    
    print(f"Updated settings:")
    print(f"  - Learning rate: {REAL_LEARNING_RATE}")
    print(f"  - OU Noise: σ={REAL_OU_SIGMA}")
    print(f"  - Device: {model.device}")
    
    # Callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=5_000,  # Every 5K steps
        save_path=REAL_CHECKPOINT_DIR,
        name_prefix="ddpg_v1_realdb"
    )
    
    callbacks = [checkpoint_callback]
    
    # Start fine-tuning
    print("\n" + "=" * 80)
    print(" Fine-tuning Start")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target timesteps: {REAL_TIMESTEPS:,}")
    print(f"Checkpoint frequency: 5,000 steps")
    print(f"TensorBoard log: {TB_LOG_DIR}")
    print("-" * 80)
    print("[IMPORTANT] This will execute queries on real database!")
    print("[IMPORTANT] Each step takes longer than simulation")
    print("-" * 80)
    
    try:
        model.learn(
            total_timesteps=REAL_TIMESTEPS,
            callback=callbacks,
            log_interval=10,
            progress_bar=True,
            reset_num_timesteps=False  # Continue from simulation timesteps
        )
    except KeyboardInterrupt:
        print("\n[WARN] Fine-tuning interrupted by user!")
    except Exception as e:
        print(f"\n[ERROR] Fine-tuning failed: {e}")
        raise
    
    # Save final model
    print("\n" + "=" * 80)
    print(" Fine-tuning Complete")
    print("=" * 80)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    model.save(REAL_MODEL_PATH)
    print(f"Model saved to: {REAL_MODEL_PATH}")
    
    # Cleanup
    env.close()
    
    print("\n" + "=" * 80)
    print(" Next Steps")
    print("=" * 80)
    print(f"1. Check TensorBoard:")
    print(f"   tensorboard --logdir {TB_LOG_DIR}")
    print(f"")
    print(f"2. Evaluate fine-tuned model:")
    print(f"   python Apollo.ML/RLQO/DDPG_v1/train/ddpg_evaluate.py --model {REAL_MODEL_PATH}")
    print(f"")
    print(f"3. Compare with DQN v3 and PPO v3 results")
    print("=" * 80)


if __name__ == '__main__':
    # Test environment first
    print("Testing RealDB environment...")
    try:
        test_env = make_env(verbose=False)
        obs, info = test_env.reset()
        print(f"✓ Environment test passed")
        print(f"  - Observation shape: {obs.shape}")
        print(f"  - Action space: {test_env.action_space}")
        print(f"  - Baseline time: {info['baseline_time']:.2f} ms")
        test_env.close()
    except Exception as e:
        print(f"[ERROR] Environment test failed: {e}")
        print(f"Please check:")
        print(f"  1. SQL Server is running")
        print(f"  2. Database connection settings in config.yaml")
        print(f"  3. Credentials in Secret.py")
        sys.exit(1)
    
    # Start fine-tuning
    print("\n" + "=" * 80)
    print("[WARNING] This will execute queries on real database!")
    print("[WARNING] Make sure you have proper permissions and backups!")
    print("=" * 80)
    response = input("\nPress Enter to continue, or Ctrl+C to cancel...")
    print("=" * 80 + "\n")
    
    train_realdb()

