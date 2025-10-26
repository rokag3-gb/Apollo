# -*- coding: utf-8 -*-
"""
TD3 v1: Hyperparameter Configuration

TD3-specific improvements over DDPG:
- Twin Critics for reduced overestimation
- Delayed policy updates
- Target policy smoothing
"""

# TD3 Hyperparameters
TD3_CONFIG = {
    # Model Architecture
    "policy": "MlpPolicy",
    "policy_kwargs": {
        "net_arch": [256, 256],  # Actor & Critic network sizes
    },
    
    # Learning Parameters
    "learning_rate": 3e-4,
    "buffer_size": 1_000_000,
    "learning_starts": 100,
    "batch_size": 256,
    "tau": 0.005,  # Soft update coefficient
    "gamma": 0.99,  # Discount factor
    
    # TD3-Specific Parameters
    "policy_delay": 2,  # Delayed policy updates (TD3 특징)
    "target_policy_noise": 0.2,  # Target policy smoothing noise (TD3 특징)
    "target_noise_clip": 0.5,  # Noise clipping range (TD3 특징)
    
    # Exploration
    "action_noise": None,  # Will be set during training (OrnsteinUhlenbeckActionNoise)
    
    # Training
    "train_freq": 1,  # Update frequency
    "gradient_steps": 1,  # Gradient steps per update
    
    # Logging
    "verbose": 1,
    "tensorboard_log": "./artifacts/RLQO/tb/td3_v1/",
}

# Simulation Training Config
TD3_SIM_CONFIG = {
    **TD3_CONFIG,
    "total_timesteps": 100_000,  # 100k steps
    "eval_freq": 5_000,
    "n_eval_episodes": 10,
    "save_freq": 10_000,
    "log_interval": 100,
}

# Real DB Fine-tuning Config
TD3_REALDB_CONFIG = {
    **TD3_CONFIG,
    "total_timesteps": 50_000,  # 50k steps (fine-tuning)
    "eval_freq": 2_500,
    "n_eval_episodes": 5,
    "save_freq": 5_000,
    "log_interval": 50,
    "learning_starts": 50,  # Reduced for fine-tuning
}

# Evaluation Config
TD3_EVAL_CONFIG = {
    "n_episodes": 30,  # 30 episodes
    "n_queries": 30,  # 30 queries
    "deterministic": True,  # Use deterministic policy
    "render": False,
}

# Action Noise Config (Ornstein-Uhlenbeck Process)
ACTION_NOISE_CONFIG = {
    "mean": 0.0,
    "sigma": 0.2,  # Exploration noise
    "theta": 0.15,  # Mean reversion rate
    "dt": 1e-2,
}

# Model Save Paths
MODEL_PATHS = {
    "sim": "artifacts/RLQO/models/td3_v1_sim_100k.zip",
    "realdb": "artifacts/RLQO/models/td3_v1_realdb_50k.zip",
    "checkpoint_dir": "artifacts/RLQO/models/checkpoints/td3_v1/",
}

# Environment Config
ENV_CONFIG = {
    "max_steps": 10,  # Max steps per episode
    "reward_scale": 1.0,  # Reward scaling
    "use_simulation": True,  # Start with simulation
}

