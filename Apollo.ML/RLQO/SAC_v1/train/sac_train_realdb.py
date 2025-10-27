# -*- coding: utf-8 -*-
"""
SAC v1: Real DB Fine-tuning

Simulation 모델을 Real DB에서 50k steps fine-tuning
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
apollo_core_dir = os.path.abspath(os.path.join(apollo_ml_dir, '..', 'Apollo.Core'))
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, apollo_core_dir)
sys.path.insert(0, rlqo_dir)
sys.path.insert(0, sac_v1_dir)

# Imports
from RLQO.constants2 import SAMPLE_QUERIES
from RLQO.SAC_v1.env.sac_db_env import make_sac_db_env
from RLQO.SAC_v1.config.sac_config import SAC_REALDB_CONFIG, MODEL_PATHS


def train_sac_realdb():
    """
    SAC v1 Real DB Fine-tuning
    
    Steps:
    1. Simulation 모델 로드
    2. Real DB 환경 생성
    3. 50k steps fine-tuning
    4. 모델 저장
    """
    
    print("=" * 80)
    print("SAC v1 Real DB Fine-tuning")
    print("=" * 80)
    
    # 0. Check simulation model exists
    sim_model_path = MODEL_PATHS['sim']
    if not os.path.exists(sim_model_path):
        print(f"\n❌ Error: Simulation model not found at {sim_model_path}")
        print("Please run sac_train_sim.py first!")
        return
    
    # 1. Create environments (DB connection handled inside environment)
    print("\n[1/4] Creating Real DB environments...")
    train_env = make_sac_db_env(SAMPLE_QUERIES, max_steps=10, verbose=False)
    eval_env = make_sac_db_env(SAMPLE_QUERIES, max_steps=10, verbose=False)
    
    print(f"Action space: {train_env.action_space}")
    print(f"Observation space: {train_env.observation_space}")
    
    # 2. Load simulation model OR latest checkpoint (resume capability)
    print("\n[2/4] Loading pre-trained model...")
    
    checkpoint_dir = MODEL_PATHS['checkpoint_dir'] + "realdb/"
    
    # Check for existing checkpoints
    checkpoint_files = []
    if os.path.exists(checkpoint_dir):
        checkpoint_files = [f for f in os.listdir(checkpoint_dir) 
                           if f.startswith('sac_v1_realdb_') and f.endswith('_steps.zip')]
    
    if checkpoint_files:
        # Sort by timesteps and get the latest
        checkpoint_files.sort(key=lambda x: int(x.split('_')[3]))  # Extract timesteps number
        latest_checkpoint = os.path.join(checkpoint_dir, checkpoint_files[-1])
        model = SAC.load(latest_checkpoint, env=train_env)
        timesteps_completed = int(checkpoint_files[-1].split('_')[3])
        print(f"✅ Resuming from checkpoint: {latest_checkpoint}")
        print(f"   Already completed: {timesteps_completed:,} timesteps")
        print(f"   (Sim 100k + RealDB {timesteps_completed - 100000:,})")
    else:
        # No checkpoint found, load simulation model
        model = SAC.load(sim_model_path, env=train_env)
        print(f"✅ Starting from simulation model: {sim_model_path}")
        print(f"   Starting Real DB fine-tuning from scratch")
    
    # Update config for fine-tuning
    model.learning_rate = SAC_REALDB_CONFIG['learning_rate']
    model.learning_starts = SAC_REALDB_CONFIG['learning_starts']
    
    print("Fine-tuning Configuration:")
    print(f"  - Learning Rate: {SAC_REALDB_CONFIG['learning_rate']}")
    print(f"  - Learning Starts: {SAC_REALDB_CONFIG['learning_starts']}")
    print(f"  - Total Steps: {SAC_REALDB_CONFIG['total_timesteps']:,}")
    print(f"  - Entropy Coef: auto (adaptive)")
    
    # 3. Setup callbacks
    print("\n[3/4] Setting up callbacks...")
    
    checkpoint_dir = MODEL_PATHS['checkpoint_dir'] + "realdb/"
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    checkpoint_callback = CheckpointCallback(
        save_freq=SAC_REALDB_CONFIG['save_freq'],
        save_path=checkpoint_dir,
        name_prefix='sac_v1_realdb'
    )
    
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=checkpoint_dir + "best/",
        log_path=checkpoint_dir + "logs/",
        eval_freq=SAC_REALDB_CONFIG['eval_freq'],
        n_eval_episodes=SAC_REALDB_CONFIG['n_eval_episodes'],
        deterministic=False,  # SAC uses stochastic policy
        render=False
    )
    
    # 4. Fine-tune
    print("\n" + "=" * 80)
    print("Starting Fine-tuning on Real DB...")
    print("=" * 80)
    print(f"Total timesteps: {SAC_REALDB_CONFIG['total_timesteps']:,}")
    print(f"Expected duration: ~2-4 hours (depends on DB performance)")
    print("⚠️  Warning: This will execute many queries on your database!")
    print("=" * 80)
    
    try:
        model.learn(
            total_timesteps=SAC_REALDB_CONFIG['total_timesteps'],
            callback=[checkpoint_callback, eval_callback],
            log_interval=SAC_REALDB_CONFIG['log_interval'],
            reset_num_timesteps=False  # Continue from simulation training
        )
        
        # 6. Save final model
        print("\n" + "=" * 80)
        print("Fine-tuning completed!")
        print("=" * 80)
        
        model_path = MODEL_PATHS['realdb']
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        model.save(model_path)
        print(f"Model saved: {model_path}")
        
    except Exception as e:
        print(f"\n❌ Training error: {e}")
        print("Saving current model...")
        model.save(MODEL_PATHS['realdb'] + ".interrupted")
    
    finally:
        # 7. Close environments
        train_env.close()
        eval_env.close()
        db_helper.close()
    
    print("\nNext step: Evaluate model")
    print("Run: python train/sac_evaluate.py")


if __name__ == '__main__':
    train_sac_realdb()

