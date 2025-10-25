# -*- coding: utf-8 -*-
"""
DDPG v1 Simulation Training Script

Stable-Baselines3 DDPG를 사용한 시뮬레이션 학습
- 100K timesteps
- Ornstein-Uhlenbeck noise for exploration
- Experience replay buffer
"""

import os
import sys
from datetime import datetime
import numpy as np

# Stable-Baselines3 imports
from stable_baselines3 import DDPG
from stable_baselines3.common.noise import OrnsteinUhlenbeckActionNoise
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor

# Project root path setup
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)

from RLQO.DDPG_v1.env.ddpg_sim_env import QueryPlanSimEnvDDPGv1

# Load 30 queries
sys.path.insert(0, os.path.join(apollo_ml_dir, 'RLQO'))
from constants2 import SAMPLE_QUERIES

# ============================================================================
# Hyperparameters (Simulation - DDPG v1)
# ============================================================================
SIM_TIMESTEPS = 100_000  # 100K steps
SIM_LEARNING_RATE = 1e-4  # Actor learning rate
SIM_BUFFER_SIZE = 100_000  # Replay buffer size
SIM_BATCH_SIZE = 128
SIM_GAMMA = 0.99
SIM_TAU = 0.001  # Soft update coefficient
SIM_TRAIN_FREQ = 1  # Train every step
SIM_GRADIENT_STEPS = 1

# Ornstein-Uhlenbeck noise parameters
OU_SIGMA = 0.2  # Noise standard deviation
OU_THETA = 0.15  # Noise mean reversion rate

# Path configuration
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_DIR = os.path.join(apollo_ml_dir, "artifacts", "RLQO")

SIM_LOG_DIR = os.path.join(BASE_DIR, "logs", "ddpg_v1_sim")
SIM_MODEL_PATH = os.path.join(BASE_DIR, "models", "ddpg_v1_sim_100k.zip")
SIM_CHECKPOINT_DIR = os.path.join(BASE_DIR, "models", "checkpoints", "ddpg_v1_sim")

TB_LOG_DIR = os.path.join(BASE_DIR, "tb", "ddpg_v1_sim")

# Create directories
for directory in [SIM_LOG_DIR, SIM_CHECKPOINT_DIR, TB_LOG_DIR]:
    os.makedirs(directory, exist_ok=True)


def make_env(verbose=False):
    """
    Create Simulation environment
    
    Args:
        verbose: Whether to print progress
    
    Returns:
        env: Simulation environment
    """
    env = QueryPlanSimEnvDDPGv1(
        query_list=SAMPLE_QUERIES,
        max_steps=10,
        verbose=verbose
    )
    
    env = Monitor(env, SIM_LOG_DIR)
    
    return env


def train_simulation():
    """
    DDPG v1 Training in Simulation Environment
    
    핵심 특징:
    - Continuous action space (7차원)
    - Off-policy learning with replay buffer
    - Ornstein-Uhlenbeck noise for exploration
    - Target networks with soft updates
    """
    print("=" * 80)
    print(" DDPG v1 Simulation Training Start")
    print("=" * 80)
    print(f"Timestamp: {TIMESTAMP}")
    print(f"Goal: Query optimization with continuous action space")
    print(f"Algorithm: DDPG (Deep Deterministic Policy Gradient)")
    print(f"Environment: XGBoost Simulation")
    print(f"Timesteps: {SIM_TIMESTEPS:,}")
    print(f"Query Count: {len(SAMPLE_QUERIES)}")
    print(f"Estimated Time: 30-45 minutes")
    print("-" * 80)
    print(f"DDPG v1 Key Features:")
    print(f"  1. Action Space: Continuous (7 dimensions)")
    print(f"  2. State Space: 18 dimensions (actionable features)")
    print(f"  3. Learning Rate: {SIM_LEARNING_RATE}")
    print(f"  4. Replay Buffer: {SIM_BUFFER_SIZE:,}")
    print(f"  5. OU Noise: σ={OU_SIGMA}, θ={OU_THETA}")
    print(f"  6. Soft Update: τ={SIM_TAU}")
    print("=" * 80)
    
    # Create environment
    print("\n[1/4] Creating environment...")
    env = make_env(verbose=True)
    
    print(f"Action space: {env.action_space}")
    print(f"Observation space: {env.observation_space}")
    
    # Create Ornstein-Uhlenbeck noise
    print("\n[2/4] Creating Ornstein-Uhlenbeck noise...")
    n_actions = env.action_space.shape[0]
    action_noise = OrnsteinUhlenbeckActionNoise(
        mean=np.zeros(n_actions),
        sigma=OU_SIGMA * np.ones(n_actions),
        theta=OU_THETA
    )
    print(f"OU Noise: mean={np.zeros(n_actions)}, sigma={OU_SIGMA}, theta={OU_THETA}")
    
    # Create DDPG model
    print("\n[3/4] Creating DDPG model...")
    model = DDPG(
        policy="MlpPolicy",
        env=env,
        learning_rate=SIM_LEARNING_RATE,
        buffer_size=SIM_BUFFER_SIZE,
        batch_size=SIM_BATCH_SIZE,
        gamma=SIM_GAMMA,
        tau=SIM_TAU,
        train_freq=SIM_TRAIN_FREQ,
        gradient_steps=SIM_GRADIENT_STEPS,
        action_noise=action_noise,
        tensorboard_log=TB_LOG_DIR,
        verbose=1,
        device="auto"
    )
    
    print(f"Model created:")
    print(f"  - Policy: MlpPolicy")
    print(f"  - Learning rate: {SIM_LEARNING_RATE}")
    print(f"  - Replay buffer: {SIM_BUFFER_SIZE:,}")
    print(f"  - Batch size: {SIM_BATCH_SIZE}")
    print(f"  - Device: {model.device}")
    
    # Callbacks
    print("\n[4/4] Setting up callbacks...")
    checkpoint_callback = CheckpointCallback(
        save_freq=10_000,  # Every 10K steps
        save_path=SIM_CHECKPOINT_DIR,
        name_prefix="ddpg_v1_sim"
    )
    
    callbacks = [checkpoint_callback]
    
    # Start training
    print("\n" + "=" * 80)
    print(" Training Start")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target timesteps: {SIM_TIMESTEPS:,}")
    print(f"Checkpoint frequency: 10,000 steps")
    print(f"TensorBoard log: {TB_LOG_DIR}")
    print("-" * 80)
    
    try:
        model.learn(
            total_timesteps=SIM_TIMESTEPS,
            callback=callbacks,
            log_interval=10,
            progress_bar=True
        )
    except KeyboardInterrupt:
        print("\n[WARN] Training interrupted by user!")
    
    # Save final model
    print("\n" + "=" * 80)
    print(" Training Complete")
    print("=" * 80)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    model.save(SIM_MODEL_PATH)
    print(f"Model saved to: {SIM_MODEL_PATH}")
    
    # Cleanup
    env.close()
    
    print("\n" + "=" * 80)
    print(" Next Steps")
    print("=" * 80)
    print(f"1. Check TensorBoard:")
    print(f"   tensorboard --logdir {TB_LOG_DIR}")
    print(f"")
    print(f"2. Fine-tune on RealDB:")
    print(f"   python Apollo.ML/RLQO/DDPG_v1/train/ddpg_train_realdb.py")
    print(f"")
    print(f"3. Evaluate model:")
    print(f"   python Apollo.ML/RLQO/DDPG_v1/train/ddpg_evaluate.py")
    print("=" * 80)


if __name__ == '__main__':
    # Test environment first
    print("Testing environment...")
    test_env = make_env(verbose=False)
    obs, info = test_env.reset()
    print(f"✓ Environment test passed")
    print(f"  - Observation shape: {obs.shape}")
    print(f"  - Action space: {test_env.action_space}")
    test_env.close()
    
    # Start training
    print("\n" + "=" * 80)
    input("Press Enter to start training (or Ctrl+C to cancel)...")
    print("=" * 80 + "\n")
    
    train_simulation()

