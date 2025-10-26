# -*- coding: utf-8 -*-
"""
SAC v1: Simulation Training

100k steps 학습:
- Maximum Entropy RL로 다양한 액션 조합 탐색
- Automatic temperature tuning
- Stochastic policy
"""

import os
import sys
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
sac_v1_dir = os.path.abspath(os.path.join(current_dir, '..'))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)
sys.path.insert(0, sac_v1_dir)

# Imports
from RLQO.constants2 import SAMPLE_QUERIES
from RLQO.SAC_v1.env.sac_sim_env import make_sac_sim_env
from RLQO.SAC_v1.config.sac_config import (
    SAC_SIM_CONFIG,
    MODEL_PATHS
)


def train_sac_simulation():
    """
    SAC v1 Simulation 학습
    
    Steps:
    1. 환경 생성 (Simulation)
    2. SAC 모델 생성
    3. 100k steps 학습
    4. 모델 저장
    """
    
    print("=" * 80)
    print("SAC v1 Simulation Training")
    print("=" * 80)
    
    # 1. Create environments
    print("\n[1/4] Creating environments...")
    train_env = make_sac_sim_env(SAMPLE_QUERIES, max_steps=10, verbose=False)
    eval_env = make_sac_sim_env(SAMPLE_QUERIES, max_steps=10, verbose=False)
    
    print(f"Action space: {train_env.action_space}")
    print(f"Observation space: {train_env.observation_space}")
    
    # 2. Create SAC model
    print("\n[2/4] Creating SAC model...")
    model = SAC(
        policy=SAC_SIM_CONFIG['policy'],
        env=train_env,
        learning_rate=SAC_SIM_CONFIG['learning_rate'],
        buffer_size=SAC_SIM_CONFIG['buffer_size'],
        learning_starts=SAC_SIM_CONFIG['learning_starts'],
        batch_size=SAC_SIM_CONFIG['batch_size'],
        tau=SAC_SIM_CONFIG['tau'],
        gamma=SAC_SIM_CONFIG['gamma'],
        ent_coef=SAC_SIM_CONFIG['ent_coef'],  # "auto" - automatic tuning
        target_entropy=SAC_SIM_CONFIG['target_entropy'],  # "auto"
        use_sde=SAC_SIM_CONFIG['use_sde'],
        sde_sample_freq=SAC_SIM_CONFIG['sde_sample_freq'],
        train_freq=SAC_SIM_CONFIG['train_freq'],
        gradient_steps=SAC_SIM_CONFIG['gradient_steps'],
        policy_kwargs=SAC_SIM_CONFIG['policy_kwargs'],
        tensorboard_log=SAC_SIM_CONFIG['tensorboard_log'],
        verbose=SAC_SIM_CONFIG['verbose']
    )
    
    print("SAC Model Configuration:")
    print(f"  - Maximum Entropy RL: Enabled")
    print(f"  - Automatic Temperature Tuning: {SAC_SIM_CONFIG['ent_coef']}")
    print(f"  - Stochastic Policy: Yes")
    print(f"  - Learning Rate: {SAC_SIM_CONFIG['learning_rate']}")
    print(f"  - Buffer Size: {SAC_SIM_CONFIG['buffer_size']:,}")
    
    # 3. Setup callbacks
    print("\n[3/4] Setting up callbacks...")
    
    # Checkpoint callback
    checkpoint_dir = MODEL_PATHS['checkpoint_dir'] + "sim/"
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_callback = CheckpointCallback(
        save_freq=SAC_SIM_CONFIG['save_freq'],
        save_path=checkpoint_dir,
        name_prefix='sac_v1_sim'
    )
    
    # Evaluation callback
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=checkpoint_dir + "best/",
        log_path=checkpoint_dir + "logs/",
        eval_freq=SAC_SIM_CONFIG['eval_freq'],
        n_eval_episodes=SAC_SIM_CONFIG['n_eval_episodes'],
        deterministic=False,  # SAC uses stochastic policy
        render=False
    )
    
    # 4. Train
    print("\n" + "=" * 80)
    print("Starting Training...")
    print("=" * 80)
    print(f"Total timesteps: {SAC_SIM_CONFIG['total_timesteps']:,}")
    print(f"Expected duration: ~30-60 minutes")
    print("=" * 80)
    
    model.learn(
        total_timesteps=SAC_SIM_CONFIG['total_timesteps'],
        callback=[checkpoint_callback, eval_callback],
        log_interval=SAC_SIM_CONFIG['log_interval']
    )
    
    # 5. Save final model
    print("\n" + "=" * 80)
    print("Training completed!")
    print("=" * 80)
    
    model_path = MODEL_PATHS['sim']
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    model.save(model_path)
    print(f"Model saved: {model_path}")
    
    # 6. Close environments
    train_env.close()
    eval_env.close()
    
    print("\nNext step: Fine-tune on Real DB")
    print("Run: python train/sac_train_realdb.py")


if __name__ == '__main__':
    train_sac_simulation()

