# -*- coding: utf-8 -*-
"""
TD3 v1: Simulation Training

100k steps 학습:
- Twin Critic Networks로 Q-value overestimation 방지
- Delayed Policy Updates로 안정성 향상
- Target Policy Smoothing으로 과적합 방지
"""

import os
import sys
from stable_baselines3 import TD3
from stable_baselines3.common.noise import OrnsteinUhlenbeckActionNoise
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
import numpy as np

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
td3_v1_dir = os.path.abspath(os.path.join(current_dir, '..'))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)
sys.path.insert(0, td3_v1_dir)

# Imports
from RLQO.constants2 import QUERY_LIST
from RLQO.TD3_v1.env.td3_sim_env import make_td3_sim_env
from RLQO.TD3_v1.config.td3_config import (
    TD3_SIM_CONFIG,
    ACTION_NOISE_CONFIG,
    MODEL_PATHS
)


def train_td3_simulation():
    """
    TD3 v1 Simulation 학습
    
    Steps:
    1. 환경 생성 (Simulation)
    2. TD3 모델 생성 (Twin Critic)
    3. 100k steps 학습
    4. 모델 저장
    """
    
    print("=" * 80)
    print("TD3 v1 Simulation Training")
    print("=" * 80)
    
    # 1. Create environments
    print("\n[1/4] Creating environments...")
    train_env = make_td3_sim_env(QUERY_LIST, max_steps=10, verbose=False)
    eval_env = make_td3_sim_env(QUERY_LIST, max_steps=10, verbose=False)
    
    print(f"Action space: {train_env.action_space}")
    print(f"Observation space: {train_env.observation_space}")
    
    # 2. Create action noise (Ornstein-Uhlenbeck)
    print("\n[2/4] Setting up action noise...")
    n_actions = train_env.action_space.shape[0]
    action_noise = OrnsteinUhlenbeckActionNoise(
        mean=np.zeros(n_actions) + ACTION_NOISE_CONFIG['mean'],
        sigma=np.ones(n_actions) * ACTION_NOISE_CONFIG['sigma'],
        theta=ACTION_NOISE_CONFIG['theta'],
        dt=ACTION_NOISE_CONFIG['dt']
    )
    
    # 3. Create TD3 model
    print("\n[3/4] Creating TD3 model...")
    model = TD3(
        policy=TD3_SIM_CONFIG['policy'],
        env=train_env,
        learning_rate=TD3_SIM_CONFIG['learning_rate'],
        buffer_size=TD3_SIM_CONFIG['buffer_size'],
        learning_starts=TD3_SIM_CONFIG['learning_starts'],
        batch_size=TD3_SIM_CONFIG['batch_size'],
        tau=TD3_SIM_CONFIG['tau'],
        gamma=TD3_SIM_CONFIG['gamma'],
        policy_delay=TD3_SIM_CONFIG['policy_delay'],  # TD3 specific
        target_policy_noise=TD3_SIM_CONFIG['target_policy_noise'],  # TD3 specific
        target_noise_clip=TD3_SIM_CONFIG['target_noise_clip'],  # TD3 specific
        action_noise=action_noise,
        train_freq=TD3_SIM_CONFIG['train_freq'],
        gradient_steps=TD3_SIM_CONFIG['gradient_steps'],
        policy_kwargs=TD3_SIM_CONFIG['policy_kwargs'],
        tensorboard_log=TD3_SIM_CONFIG['tensorboard_log'],
        verbose=TD3_SIM_CONFIG['verbose']
    )
    
    print("TD3 Model Configuration:")
    print(f"  - Twin Critic Networks: Q1, Q2")
    print(f"  - Policy Delay: {TD3_SIM_CONFIG['policy_delay']}")
    print(f"  - Target Policy Noise: {TD3_SIM_CONFIG['target_policy_noise']}")
    print(f"  - Learning Rate: {TD3_SIM_CONFIG['learning_rate']}")
    print(f"  - Buffer Size: {TD3_SIM_CONFIG['buffer_size']:,}")
    
    # 4. Setup callbacks
    print("\n[4/4] Setting up callbacks...")
    
    # Checkpoint callback
    checkpoint_dir = MODEL_PATHS['checkpoint_dir'] + "sim/"
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_callback = CheckpointCallback(
        save_freq=TD3_SIM_CONFIG['save_freq'],
        save_path=checkpoint_dir,
        name_prefix='td3_v1_sim'
    )
    
    # Evaluation callback
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=checkpoint_dir + "best/",
        log_path=checkpoint_dir + "logs/",
        eval_freq=TD3_SIM_CONFIG['eval_freq'],
        n_eval_episodes=TD3_SIM_CONFIG['n_eval_episodes'],
        deterministic=True,
        render=False
    )
    
    # 5. Train
    print("\n" + "=" * 80)
    print("Starting Training...")
    print("=" * 80)
    print(f"Total timesteps: {TD3_SIM_CONFIG['total_timesteps']:,}")
    print(f"Expected duration: ~30-60 minutes")
    print("=" * 80)
    
    model.learn(
        total_timesteps=TD3_SIM_CONFIG['total_timesteps'],
        callback=[checkpoint_callback, eval_callback],
        log_interval=TD3_SIM_CONFIG['log_interval']
    )
    
    # 6. Save final model
    print("\n" + "=" * 80)
    print("Training completed!")
    print("=" * 80)
    
    model_path = MODEL_PATHS['sim']
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    model.save(model_path)
    print(f"Model saved: {model_path}")
    
    # 7. Close environments
    train_env.close()
    eval_env.close()
    
    print("\nNext step: Fine-tune on Real DB")
    print("Run: python train/td3_train_realdb.py")


if __name__ == '__main__':
    train_td3_simulation()

