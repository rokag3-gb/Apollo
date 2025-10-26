# -*- coding: utf-8 -*-
"""
SAC v1: Hyperparameter Configuration

Soft Actor-Critic (Maximum Entropy RL):
- Entropy-regularized objective
- Automatic temperature tuning
- Stochastic policy
"""

# SAC Hyperparameters
SAC_CONFIG = {
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
    
    # SAC-Specific Parameters
    "ent_coef": "auto",  # Automatic entropy tuning (핵심 특징)
    "target_entropy": "auto",  # -dim(A) by default
    "use_sde": False,  # State-dependent exploration (optional)
    "sde_sample_freq": -1,
    
    # Training
    "train_freq": 1,  # Update frequency
    "gradient_steps": 1,  # Gradient steps per update
    
    # Logging
    "verbose": 1,
    "tensorboard_log": "./artifacts/RLQO/tb/sac_v1/",
}

# Simulation Training Config
SAC_SIM_CONFIG = {
    **SAC_CONFIG,
    "total_timesteps": 100_000,  # 100k steps
    "eval_freq": 5_000,
    "n_eval_episodes": 10,
    "save_freq": 10_000,
    "log_interval": 100,
}

# Real DB Fine-tuning Config
SAC_REALDB_CONFIG = {
    **SAC_CONFIG,
    "total_timesteps": 50_000,  # 50k steps (fine-tuning)
    "eval_freq": 2_500,
    "n_eval_episodes": 5,
    "save_freq": 5_000,
    "log_interval": 50,
    "learning_starts": 50,  # Reduced for fine-tuning
}

# Evaluation Config
SAC_EVAL_CONFIG = {
    "n_episodes": 30,  # 30 episodes
    "n_queries": 30,  # 30 queries
    "deterministic": False,  # SAC uses stochastic policy
    "render": False,
}

# Model Save Paths
MODEL_PATHS = {
    "sim": "artifacts/RLQO/models/sac_v1_sim_100k.zip",
    "realdb": "artifacts/RLQO/models/sac_v1_realdb_50k.zip",
    "checkpoint_dir": "artifacts/RLQO/models/checkpoints/sac_v1/",
}

# Environment Config
ENV_CONFIG = {
    "max_steps": 10,  # Max steps per episode
    "reward_scale": 1.0,  # Reward scaling
    "use_simulation": True,  # Start with simulation
}

