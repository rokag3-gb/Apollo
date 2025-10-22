# -*- coding: utf-8 -*-
"""
PPO v3 Simulation Environment Evaluation Script

Quick evaluation on Simulation environment (no DB connection needed)
"""

import os
import sys
import numpy as np
import json
from datetime import datetime
from collections import defaultdict
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

# Project root path setup
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)

from RLQO.PPO_v3.env.v3_sim_env import QueryPlanSimEnvPPOv3

# Load 30 queries from constants2.py
sys.path.insert(0, os.path.join(apollo_ml_dir, 'RLQO'))
from constants2 import SAMPLE_QUERIES


def mask_fn(env):
    """Action mask function for PPO"""
    float_mask = env.get_action_mask()
    return float_mask.astype(bool)


def evaluate_model_sim(model_path: str, num_episodes: int = 30, max_steps: int = 10):
    """
    Evaluate model on Simulation environment
    
    Args:
        model_path: Path to model file
        num_episodes: Number of episodes per query
        max_steps: Maximum steps per query
    
    Returns:
        results: Evaluation results dictionary
    """
    print("=" * 80)
    print(" PPO v3 Simulation Evaluation")
    print("=" * 80)
    print(f"Model: {model_path}")
    print(f"Query Count: {len(SAMPLE_QUERIES)}")
    print(f"Episodes: {num_episodes}")
    print(f"Max Steps: {max_steps}")
    print("=" * 80)
    
    # Create environment
    print(f"\n[1/4] Creating Simulation environment...")
    env = QueryPlanSimEnvPPOv3(
        query_list=SAMPLE_QUERIES,
        max_steps=max_steps,
        curriculum_mode=False,  # Disable curriculum for evaluation
        verbose=False
    )
    env = ActionMasker(env, mask_fn)
    print("[OK] Environment created")
    
    # Load model
    print(f"\n[2/4] Loading model...")
    model = MaskablePPO.load(model_path, env=env)
    print("[OK] Model loaded")
    
    # Evaluation results storage
    results = {
        'query_results': {},  # Per-query results
        'action_counts': defaultdict(int),  # Action selection frequency
        'rewards': [],  # All reward values
        'total_queries': len(SAMPLE_QUERIES),
        'num_episodes': num_episodes
    }
    
    # Evaluate each query
    print(f"\n[3/4] Evaluating per query...")
    total_evaluations = len(SAMPLE_QUERIES) * num_episodes
    eval_count = 0
    
    for query_idx in range(len(SAMPLE_QUERIES)):
        query_rewards = []
        query_actions = []
        
        for episode in range(num_episodes):
            eval_count += 1
            if eval_count % 10 == 0:
                print(f"  Progress: {eval_count}/{total_evaluations} ({eval_count/total_evaluations*100:.1f}%)")
            
            obs, info = env.reset()
            episode_reward = 0
            episode_actions = []
            
            for step in range(max_steps):
                # Get action mask (from the underlying environment)
                action_masks = mask_fn(env.env)
                
                # Predict action
                action, _states = model.predict(obs, action_masks=action_masks, deterministic=True)
                
                # Step
                obs, reward, done, truncated, info = env.step(action)
                
                episode_reward += reward
                episode_actions.append(int(action))
                
                if done or truncated:
                    break
            
            query_rewards.append(episode_reward)
            query_actions.extend(episode_actions)
        
        # Store query results
        results['query_results'][query_idx] = {
            'mean_reward': float(np.mean(query_rewards)),
            'std_reward': float(np.std(query_rewards)),
            'min_reward': float(np.min(query_rewards)),
            'max_reward': float(np.max(query_rewards)),
            'actions': query_actions
        }
        
        # Count actions
        for action in query_actions:
            results['action_counts'][str(action)] += 1
        
        # Store all rewards
        results['rewards'].extend(query_rewards)
    
    print(f"  Progress: {total_evaluations}/{total_evaluations} (100.0%)")
    
    # Calculate statistics
    print(f"\n[4/4] Calculating statistics...")
    all_rewards = results['rewards']
    
    results['summary'] = {
        'mean_reward': float(np.mean(all_rewards)),
        'std_reward': float(np.std(all_rewards)),
        'min_reward': float(np.min(all_rewards)),
        'max_reward': float(np.max(all_rewards)),
        'median_reward': float(np.median(all_rewards)),
        'total_actions': sum(results['action_counts'].values()),
        'unique_actions': len(results['action_counts'])
    }
    
    # Print summary
    print("\n" + "=" * 80)
    print(" Evaluation Summary")
    print("=" * 80)
    print(f"Total Episodes: {total_evaluations}")
    print(f"Mean Reward: {results['summary']['mean_reward']:.4f}")
    print(f"Std Reward: {results['summary']['std_reward']:.4f}")
    print(f"Min Reward: {results['summary']['min_reward']:.4f}")
    print(f"Max Reward: {results['summary']['max_reward']:.4f}")
    print(f"Median Reward: {results['summary']['median_reward']:.4f}")
    print(f"Total Actions: {results['summary']['total_actions']}")
    print(f"Unique Actions: {results['summary']['unique_actions']} / 44")
    
    # Top 10 actions
    print("\nTop 10 Most Used Actions:")
    sorted_actions = sorted(results['action_counts'].items(), key=lambda x: x[1], reverse=True)
    for i, (action, count) in enumerate(sorted_actions[:10], 1):
        percentage = count / results['summary']['total_actions'] * 100
        print(f"  {i}. Action {action}: {count} times ({percentage:.1f}%)")
    
    print("=" * 80)
    
    env.close()
    return results


def save_results(results, output_path):
    """Save evaluation results to JSON file"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Convert defaultdict to regular dict for JSON serialization
    results_json = {
        'query_results': results['query_results'],
        'action_counts': dict(results['action_counts']),
        'summary': results['summary'],
        'total_queries': results['total_queries'],
        'num_episodes': results['num_episodes'],
        'evaluation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results_json, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Results saved: {output_path}")


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PPO v3 Simulation Evaluation')
    parser.add_argument('--model', type=str, required=True,
                       help='Path to model file')
    parser.add_argument('--episodes', type=int, default=30,
                       help='Number of episodes per query')
    parser.add_argument('--max-steps', type=int, default=10,
                       help='Maximum steps per query')
    parser.add_argument('--output', type=str, default=None,
                       help='Output path for results (JSON)')
    
    args = parser.parse_args()
    
    # Check model exists
    if not os.path.exists(args.model):
        print(f"[ERROR] Model file not found: {args.model}")
        return
    
    # Run evaluation
    start_time = datetime.now()
    print(f"Evaluation start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        results = evaluate_model_sim(
            model_path=args.model,
            num_episodes=args.episodes,
            max_steps=args.max_steps
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\nEvaluation complete!")
        print(f"Duration: {duration:.1f} seconds")
        
        # Save results
        if args.output:
            output_path = args.output
        else:
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            output_path = f"Apollo.ML/artifacts/RLQO/evaluation/ppo_v3_sim_eval_{timestamp}.json"
        
        save_results(results, output_path)
        
    except Exception as e:
        print(f"\n[ERROR] Evaluation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

