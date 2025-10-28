# -*- coding: utf-8 -*-
"""
Ensemble v1: Multi-Environment Evaluation

각 모델이 자신의 환경을 사용하도록 수정된 평가 스크립트
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
from collections import defaultdict
from typing import Dict, List

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
ensemble_dir = os.path.abspath(os.path.join(current_dir, '..'))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
project_root = os.path.abspath(os.path.join(apollo_ml_dir, '..'))

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)
sys.path.insert(0, ensemble_dir)

from RLQO.constants2 import SAMPLE_QUERIES
from RLQO.PPO_v3.config.query_action_mapping_v3 import QUERY_TYPES
from RLQO.Ensemble_v1.config.ensemble_config import EVAL_CONFIG, OUTPUT_FILES, MODEL_PATHS, MODEL_ENV_TYPES

from stable_baselines3 import DQN, DDPG, SAC
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker


class MultiEnvironmentEnsemble:
    """
    각 모델이 독립적인 환경을 사용하는 Ensemble
    """
    
    def __init__(self, voting_strategy: str = 'weighted', verbose: bool = True):
        self.voting_strategy = voting_strategy
        self.verbose = verbose
        
        self.models = {}
        self.envs = {}
        self.loaded_models = []
        
    def load_models_and_envs(self, queries: List[str], max_steps: int = 1):
        """
        모델과 각 모델의 환경을 로드합니다.
        """
        if self.verbose:
            print("=" * 80)
            print("Loading Models and Environments")
            print("=" * 80)
        
        # DQN v3
        try:
            from RLQO.DQN_v3.env.v3_db_env import QueryPlanDBEnvV3
            
            if os.path.exists(MODEL_PATHS['dqn_v3']):
                self.models['dqn_v3'] = DQN.load(MODEL_PATHS['dqn_v3'])
                self.envs['dqn_v3'] = QueryPlanDBEnvV3(
                    query_list=queries,
                    max_steps=max_steps,
                    verbose=False
                )
                self.loaded_models.append('dqn_v3')
                if self.verbose:
                    print(f"✓ DQN v3 loaded with QueryPlanDBEnvV3")
            else:
                if self.verbose:
                    print(f"✗ DQN v3 not found")
        except Exception as e:
            if self.verbose:
                print(f"✗ DQN v3 load failed: {e}")
        
        # PPO v3
        try:
            from RLQO.PPO_v3.env.v3_db_env import QueryPlanDBEnvPPOv3
            
            if os.path.exists(MODEL_PATHS['ppo_v3']):
                self.models['ppo_v3'] = MaskablePPO.load(MODEL_PATHS['ppo_v3'])
                ppo_env = QueryPlanDBEnvPPOv3(
                    query_list=queries,
                    max_steps=max_steps,
                    curriculum_mode=False,
                    verbose=False
                )
                
                # ActionMasker 적용
                def mask_fn(env):
                    float_mask = env.get_action_mask()
                    return float_mask.astype(bool)
                
                self.envs['ppo_v3'] = ActionMasker(ppo_env, mask_fn)
                self.loaded_models.append('ppo_v3')
                if self.verbose:
                    print(f"✓ PPO v3 loaded with QueryPlanDBEnvPPOv3")
            else:
                if self.verbose:
                    print(f"✗ PPO v3 not found")
        except Exception as e:
            if self.verbose:
                print(f"✗ PPO v3 load failed: {e}")
        
        # DDPG v1
        try:
            from RLQO.DDPG_v1.env.ddpg_db_env import QueryPlanRealDBEnvDDPGv1
            
            if os.path.exists(MODEL_PATHS['ddpg_v1']):
                self.models['ddpg_v1'] = DDPG.load(MODEL_PATHS['ddpg_v1'])
                self.envs['ddpg_v1'] = QueryPlanRealDBEnvDDPGv1(
                    query_list=queries,
                    max_steps=max_steps,
                    verbose=False
                )
                self.loaded_models.append('ddpg_v1')
                if self.verbose:
                    print(f"✓ DDPG v1 loaded with QueryPlanRealDBEnvDDPGv1")
            else:
                if self.verbose:
                    print(f"✗ DDPG v1 not found")
        except Exception as e:
            if self.verbose:
                print(f"✗ DDPG v1 load failed: {e}")
        
        # SAC v1
        try:
            from RLQO.SAC_v1.env.sac_db_env import make_sac_db_env
            
            if os.path.exists(MODEL_PATHS['sac_v1']):
                self.models['sac_v1'] = SAC.load(MODEL_PATHS['sac_v1'])
                self.envs['sac_v1'] = make_sac_db_env(
                    query_list=queries,
                    max_steps=max_steps,
                    verbose=False
                )
                self.loaded_models.append('sac_v1')
                if self.verbose:
                    print(f"✓ SAC v1 loaded with make_sac_db_env")
            else:
                if self.verbose:
                    print(f"✗ SAC v1 not found")
        except Exception as e:
            if self.verbose:
                print(f"✗ SAC v1 load failed: {e}")
        
        if self.verbose:
            print("=" * 80)
            print(f"Loaded {len(self.loaded_models)}/4 models: {self.loaded_models}")
            print("=" * 80 + "\n")
        
        if len(self.loaded_models) == 0:
            raise RuntimeError("No models loaded successfully!")
    
    def predict(self, query_idx: int, episode: int):
        """
        각 모델의 환경에서 observation을 얻고 예측 수행
        
        Returns:
            final_action: 투표로 결정된 최종 액션
            predictions: 각 모델의 예측
            confidences: 각 모델의 confidence
            observations: 각 모델의 observation (디버깅용)
        """
        predictions = {}
        confidences = {}
        observations = {}
        
        # 각 모델의 환경에서 observation 얻기
        for model_name in self.loaded_models:
            try:
                env = self.envs[model_name]
                model = self.models[model_name]
                
                # Reset environment to specific query
                env.current_query_ix = query_idx
                obs, info = env.reset(seed=query_idx * 10000 + episode)
                observations[model_name] = obs
                
                # Predict
                if model_name == 'ppo_v3':
                    # PPO with action mask
                    action_mask = env.get_action_mask() if hasattr(env, 'get_action_mask') else None
                    action, _ = model.predict(obs, action_masks=action_mask, deterministic=True)
                    # Confidence: policy probability
                    confidence = self._get_ppo_confidence(model, obs, action, action_mask)
                
                elif model_name == 'dqn_v3':
                    # DQN
                    action, _ = model.predict(obs, deterministic=True)
                    # Confidence: Q-value
                    confidence = self._get_dqn_confidence(model, obs, action)
                
                elif model_name in ['ddpg_v1', 'sac_v1']:
                    # DDPG, SAC
                    continuous_action, _ = model.predict(obs, deterministic=True)
                    # Convert to discrete
                    action = self._continuous_to_discrete(continuous_action, model_name)
                    # Confidence: Q-value
                    confidence = self._get_continuous_confidence(model, obs, continuous_action, model_name)
                
                predictions[model_name] = int(action)
                confidences[model_name] = confidence
                
            except Exception as e:
                if self.verbose:
                    print(f"[WARN] {model_name} prediction failed: {e}")
                continue
        
        # Voting
        final_action = self._apply_voting_strategy(predictions, confidences)
        
        return final_action, predictions, confidences, observations
    
    def _get_dqn_confidence(self, model, obs, action):
        """DQN confidence"""
        try:
            q_values = model.q_net(model.policy.obs_to_tensor(obs)[0])
            q_values = q_values.detach().cpu().numpy().flatten()
            max_q = np.max(q_values)
            selected_q = q_values[action]
            confidence = selected_q / (max_q + 1e-8)
            return float(np.clip(confidence, 0, 1))
        except:
            return 0.5
    
    def _get_ppo_confidence(self, model, obs, action, action_mask):
        """PPO confidence"""
        try:
            obs_tensor = model.policy.obs_to_tensor(obs)[0]
            distribution = model.policy.get_distribution(obs_tensor)
            log_prob = distribution.distribution.logits.detach().cpu().numpy().flatten()
            
            if action_mask is not None:
                log_prob = np.where(action_mask, log_prob, -np.inf)
            
            exp_log_prob = np.exp(log_prob - np.max(log_prob))
            probs = exp_log_prob / np.sum(exp_log_prob)
            
            confidence = probs[action]
            return float(np.clip(confidence, 0, 1))
        except:
            return 0.5
    
    def _get_continuous_confidence(self, model, obs, action, model_name):
        """Continuous model confidence"""
        try:
            obs_tensor = model.policy.obs_to_tensor(obs)[0]
            action_tensor = model.policy.actor.action_to_tensor(action)
            
            if hasattr(model.policy, 'critic'):
                q_value = model.policy.critic(obs_tensor, action_tensor)
            else:
                q_value = model.policy.critic_target(obs_tensor, action_tensor)[0]
            
            q_value = q_value.detach().cpu().numpy().flatten()[0]
            confidence = 1.0 / (1.0 + np.exp(-q_value / 10.0))
            return float(np.clip(confidence, 0, 1))
        except:
            return 0.5
    
    def _continuous_to_discrete(self, action: np.ndarray, model_name: str) -> int:
        """Continuous action을 discrete로 변환"""
        try:
            from RLQO.DDPG_v1.config.action_decoder import decode_continuous_action
            hints = decode_continuous_action(action)
            
            hint_to_action = {
                'NO_ACTION': 0,
                'OPTION_RECOMPILE': 1,
                'OPTION_HASH_JOIN': 2,
                'OPTION_MERGE_JOIN': 3,
                'OPTION_LOOP_JOIN': 4,
                'OPTION_FORCE_ORDER': 5,
                'OPTION_MAXDOP_1': 6,
                'OPTION_MAXDOP_2': 7,
                'OPTION_MAXDOP_4': 8,
                'OPTION_OPTIMIZE_UNKNOWN': 9,
                'OPTION_FAST_10': 10,
            }
            
            if len(hints) == 0 or hints == ['NO_ACTION']:
                return 0
            
            first_hint = hints[0]
            return hint_to_action.get(first_hint, 0)
        except:
            return 0
    
    def _apply_voting_strategy(self, predictions: Dict[str, int], confidences: Dict[str, float]) -> int:
        """투표 전략 적용"""
        if len(predictions) == 0:
            return 0
        
        from RLQO.Ensemble_v1.voting_strategies import (
            majority_vote, weighted_vote, equal_weighted_vote,
            performance_based_vote, query_type_based_vote
        )
        from RLQO.Ensemble_v1.config.ensemble_config import PERFORMANCE_WEIGHTS, QUERY_TYPE_WEIGHTS
        
        if self.voting_strategy == 'majority':
            return majority_vote(predictions)
        elif self.voting_strategy == 'weighted':
            return weighted_vote(predictions, confidences)
        elif self.voting_strategy == 'equal':
            return equal_weighted_vote(predictions)
        elif self.voting_strategy == 'performance':
            weights = {k: PERFORMANCE_WEIGHTS.get(k, 1.0) for k in predictions.keys()}
            return performance_based_vote(predictions, weights)
        else:
            return weighted_vote(predictions, confidences)
    
    def execute_action(self, query_idx: int, action: int):
        """
        모든 환경에 동일한 액션을 적용하고 baseline 대비 성능 측정
        
        DQN 환경을 대표로 사용 (실제 DB 실행)
        """
        env = self.envs[self.loaded_models[0]]  # 첫 번째 모델의 환경 사용
        
        # Step
        obs, reward, done, truncated, info = env.step(action)
        
        return info
    
    def close_all(self):
        """모든 환경 종료"""
        for env in self.envs.values():
            try:
                env.close()
            except:
                pass


def evaluate_ensemble_multienv(
    voting_strategy: str = 'weighted',
    n_queries: int = 30,
    n_episodes: int = 10,
    verbose: bool = True
):
    """
    Multi-Environment Ensemble 평가
    """
    
    if verbose:
        print("=" * 80)
        print(f"Multi-Environment Ensemble: {voting_strategy.upper()}")
        print("=" * 80)
        print(f"Queries: {n_queries}")
        print(f"Episodes: {n_episodes}")
        print("=" * 80 + "\n")
    
    # Create ensemble
    ensemble = MultiEnvironmentEnsemble(voting_strategy=voting_strategy, verbose=verbose)
    ensemble.load_models_and_envs(SAMPLE_QUERIES[:n_queries], max_steps=1)
    
    # Results
    results = {
        'timestamp': datetime.now().isoformat(),
        'voting_strategy': voting_strategy,
        'n_queries': n_queries,
        'n_episodes': n_episodes,
        'loaded_models': ensemble.loaded_models,
        'query_results': {},
        'detailed_results': [],
        'action_counts': defaultdict(int),
        'model_agreement': [],
    }
    
    total_speedups = []
    
    if verbose:
        print(f"\n[Starting Evaluation]")
        print(f"{'Query':<8} {'Episode':<10} {'Type':<15} {'Baseline(ms)':<15} {'Optimized(ms)':<15} {'Speedup':<10} {'Action':<8}")
        print("-" * 100)
    
    # Measure baselines first
    baselines = {}
    for q_idx in range(n_queries):
        # Use first model's env for baseline
        first_env = ensemble.envs[ensemble.loaded_models[0]]
        first_env.current_query_ix = q_idx
        obs, info = first_env.reset(seed=q_idx * 1000)
        baselines[q_idx] = info['metrics'].get('elapsed_time_ms', -1)
    
    # Evaluate
    for q_idx in range(n_queries):
        query_type = QUERY_TYPES.get(q_idx, 'UNKNOWN')
        query_speedups = []
        query_actions = []
        
        baseline_time = baselines[q_idx]
        
        if baseline_time <= 0:
            if verbose:
                print(f"Q{q_idx} [SKIP] No valid baseline")
            continue
        
        for episode in range(n_episodes):
            try:
                # Predict with ensemble (each model uses its own env)
                action, predictions, confidences, observations = ensemble.predict(q_idx, episode)
                
                # Execute action
                info = ensemble.execute_action(q_idx, action)
                optimized_time = info['metrics'].get('elapsed_time_ms', -1)
                
                if optimized_time > 0:
                    speedup = baseline_time / optimized_time
                else:
                    speedup = 0.0
                
                # Record
                query_speedups.append(speedup)
                query_actions.append(action)
                total_speedups.append(speedup)
                results['action_counts'][action] += 1
                
                # Model agreement
                unique_predictions = len(set(predictions.values()))
                total_models = len(predictions)
                agreement_ratio = 1.0 - (unique_predictions - 1) / max(total_models, 1)
                results['model_agreement'].append(agreement_ratio)
                
                # Detailed result
                detail = {
                    'query_idx': q_idx,
                    'query_type': query_type,
                    'episode': episode,
                    'baseline_ms': baseline_time,
                    'optimized_ms': optimized_time,
                    'speedup': speedup,
                    'action': action,
                    'predictions': predictions,
                    'confidences': confidences,
                }
                results['detailed_results'].append(detail)
                
                if verbose:
                    print(f"Q{q_idx:<6} Ep{episode+1:<8} {query_type:<15} {baseline_time:>12.2f}   {optimized_time:>12.2f}   {speedup:>8.3f}x  {action:<8}")
            
            except Exception as e:
                if verbose:
                    print(f"Q{q_idx:<6} Ep{episode+1:<8} [ERROR] {str(e)[:50]}")
                continue
        
        # Query summary
        if query_speedups:
            results['query_results'][q_idx] = {
                'query_type': query_type,
                'mean_speedup': float(np.mean(query_speedups)),
                'median_speedup': float(np.median(query_speedups)),
                'episodes': len(query_speedups),
                'most_common_action': int(max(set(query_actions), key=query_actions.count)),
            }
    
    ensemble.close_all()
    
    # Overall summary
    if total_speedups:
        results['summary'] = {
            'mean_speedup': float(np.mean(total_speedups)),
            'median_speedup': float(np.median(total_speedups)),
            'max_speedup': float(np.max(total_speedups)),
            'win_rate': float(np.mean([s > 1.0 for s in total_speedups])),
            'safe_rate': float(np.mean([s >= 0.9 for s in total_speedups])),
            'mean_agreement': float(np.mean(results['model_agreement'])),
        }
        
        if verbose:
            print("\n" + "=" * 80)
            print("Evaluation Summary")
            print("=" * 80)
            print(f"Mean Speedup:   {results['summary']['mean_speedup']:.3f}x")
            print(f"Median Speedup: {results['summary']['median_speedup']:.3f}x")
            print(f"Max Speedup:    {results['summary']['max_speedup']:.3f}x")
            print(f"Win Rate:       {results['summary']['win_rate']*100:.1f}%")
            print(f"Safe Rate:      {results['summary']['safe_rate']*100:.1f}%")
            print(f"Model Agreement: {results['summary']['mean_agreement']*100:.1f}%")
            print("=" * 80 + "\n")
    
    return results


def main():
    """Main evaluation"""
    
    # Test with single strategy
    results = evaluate_ensemble_multienv(
        voting_strategy='weighted',
        n_queries=10,  # Start with 10 queries for testing
        n_episodes=3,   # 3 episodes for testing
        verbose=True
    )
    
    # Save results
    output_file = os.path.join(os.path.dirname(__file__), '..', 'results', 'multienv_test_results.json')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n[Results saved to: {output_file}]")


if __name__ == '__main__':
    main()

