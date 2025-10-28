# -*- coding: utf-8 -*-
"""
Ensemble v1: Voting Ensemble

4개 모델(DQN v3, PPO v3, DDPG v1, SAC v1)의 예측을 결합하는
Voting Ensemble 구현
"""

import os
import sys
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import Counter

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')
rlqo_dir = os.path.join(apollo_ml_dir, 'RLQO')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)

from stable_baselines3 import DQN, DDPG, SAC
from sb3_contrib import MaskablePPO

from RLQO.Ensemble_v1.config.ensemble_config import (
    MODEL_PATHS, MODEL_TYPES, PERFORMANCE_WEIGHTS,
    QUERY_TYPE_WEIGHTS, CONFIDENCE_THRESHOLD
)
from RLQO.Ensemble_v1.voting_strategies import (
    majority_vote, weighted_vote, equal_weighted_vote,
    performance_based_vote, query_type_based_vote
)


class VotingEnsemble:
    """
    Voting Ensemble for Query Optimization
    
    4개의 RL 모델을 결합하여 쿼리 최적화 액션을 선택합니다.
    """
    
    def __init__(
        self,
        model_paths: Dict[str, str] = None,
        voting_strategy: str = 'weighted',
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        verbose: bool = True
    ):
        """
        Args:
            model_paths: 모델 경로 딕셔너리
            voting_strategy: 투표 전략 ('majority', 'weighted', 'equal', 'performance', 'query_type')
            confidence_threshold: Confidence threshold
            verbose: 로깅 여부
        """
        self.model_paths = model_paths or MODEL_PATHS
        self.voting_strategy = voting_strategy
        self.confidence_threshold = confidence_threshold
        self.verbose = verbose
        
        self.models = {}
        self.model_types = MODEL_TYPES
        self.performance_weights = PERFORMANCE_WEIGHTS
        
        # 로드 성공 여부 추적
        self.loaded_models = []
        
    def load_models(self):
        """4개 모델을 로드합니다."""
        if self.verbose:
            print("=" * 80)
            print("Loading Ensemble Models")
            print("=" * 80)
        
        # DQN v3
        try:
            if os.path.exists(self.model_paths['dqn_v3']):
                self.models['dqn_v3'] = DQN.load(self.model_paths['dqn_v3'])
                self.loaded_models.append('dqn_v3')
                if self.verbose:
                    print(f"✓ DQN v3 loaded: {self.model_paths['dqn_v3']}")
            else:
                if self.verbose:
                    print(f"✗ DQN v3 not found: {self.model_paths['dqn_v3']}")
        except Exception as e:
            if self.verbose:
                print(f"✗ DQN v3 load failed: {e}")
        
        # PPO v3
        try:
            if os.path.exists(self.model_paths['ppo_v3']):
                self.models['ppo_v3'] = MaskablePPO.load(self.model_paths['ppo_v3'])
                self.loaded_models.append('ppo_v3')
                if self.verbose:
                    print(f"✓ PPO v3 loaded: {self.model_paths['ppo_v3']}")
            else:
                if self.verbose:
                    print(f"✗ PPO v3 not found: {self.model_paths['ppo_v3']}")
        except Exception as e:
            if self.verbose:
                print(f"✗ PPO v3 load failed: {e}")
        
        # DDPG v1
        try:
            if os.path.exists(self.model_paths['ddpg_v1']):
                self.models['ddpg_v1'] = DDPG.load(self.model_paths['ddpg_v1'])
                self.loaded_models.append('ddpg_v1')
                if self.verbose:
                    print(f"✓ DDPG v1 loaded: {self.model_paths['ddpg_v1']}")
            else:
                if self.verbose:
                    print(f"✗ DDPG v1 not found: {self.model_paths['ddpg_v1']}")
        except Exception as e:
            if self.verbose:
                print(f"✗ DDPG v1 load failed: {e}")
        
        # SAC v1
        try:
            if os.path.exists(self.model_paths['sac_v1']):
                self.models['sac_v1'] = SAC.load(self.model_paths['sac_v1'])
                self.loaded_models.append('sac_v1')
                if self.verbose:
                    print(f"✓ SAC v1 loaded: {self.model_paths['sac_v1']}")
            else:
                if self.verbose:
                    print(f"✗ SAC v1 not found: {self.model_paths['sac_v1']}")
        except Exception as e:
            if self.verbose:
                print(f"✗ SAC v1 load failed: {e}")
        
        if self.verbose:
            print("=" * 80)
            print(f"Loaded {len(self.loaded_models)}/4 models: {self.loaded_models}")
            print("=" * 80 + "\n")
        
        if len(self.loaded_models) == 0:
            raise RuntimeError("No models loaded successfully!")
    
    def predict(
        self,
        observation: np.ndarray,
        query_type: str = 'DEFAULT',
        action_mask: Optional[np.ndarray] = None
    ) -> Tuple[int, Dict]:
        """
        Ensemble 예측: 4개 모델의 예측을 결합
        
        Args:
            observation: 환경 상태 (observation)
            query_type: 쿼리 타입 (투표 전략에 사용)
            action_mask: 액션 마스크 (PPO용)
        
        Returns:
            final_action: 최종 선택된 액션
            info: 상세 정보 (각 모델의 예측, confidence 등)
        """
        predictions = {}
        confidences = {}
        
        # 각 모델로부터 예측 수집
        for model_name in self.loaded_models:
            try:
                model = self.models[model_name]
                model_type = self.model_types[model_name]
                
                if model_type == 'discrete':
                    # DQN, PPO: discrete action
                    if model_name == 'ppo_v3' and action_mask is not None:
                        action, _ = model.predict(observation, action_masks=action_mask, deterministic=True)
                    else:
                        action, _ = model.predict(observation, deterministic=True)
                    
                    # Confidence: Q-value 기반 (DQN) 또는 policy 확률 (PPO)
                    confidence = self._get_discrete_confidence(model, observation, action, model_name, action_mask)
                    
                    predictions[model_name] = int(action)
                    confidences[model_name] = confidence
                
                elif model_type == 'continuous':
                    # DDPG, SAC: continuous action → discrete action으로 변환 필요
                    action, _ = model.predict(observation, deterministic=True)
                    
                    # Continuous action을 discrete action으로 매핑
                    discrete_action = self._continuous_to_discrete(action, model_name)
                    
                    # Confidence: Q-value 기반
                    confidence = self._get_continuous_confidence(model, observation, action, model_name)
                    
                    predictions[model_name] = discrete_action
                    confidences[model_name] = confidence
                    
            except Exception as e:
                if self.verbose:
                    print(f"[WARN] {model_name} prediction failed: {e}")
                continue
        
        # Confidence threshold 적용
        filtered_predictions = {
            k: v for k, v in predictions.items()
            if confidences[k] >= self.confidence_threshold
        }
        filtered_confidences = {
            k: v for k, v in confidences.items()
            if v >= self.confidence_threshold
        }
        
        if len(filtered_predictions) == 0:
            # 모든 모델이 threshold 이하면 NO_ACTION (0)
            final_action = 0
        else:
            # 투표 전략에 따라 최종 액션 선택
            final_action = self._apply_voting_strategy(
                filtered_predictions,
                filtered_confidences,
                query_type
            )
        
        # 상세 정보 반환
        info = {
            'predictions': predictions,
            'confidences': confidences,
            'filtered_predictions': filtered_predictions,
            'filtered_confidences': filtered_confidences,
            'final_action': final_action,
            'voting_strategy': self.voting_strategy,
            'query_type': query_type,
        }
        
        return final_action, info
    
    def _get_discrete_confidence(
        self,
        model,
        observation: np.ndarray,
        action: int,
        model_name: str,
        action_mask: Optional[np.ndarray] = None
    ) -> float:
        """Discrete 모델의 confidence 계산"""
        try:
            if model_name == 'dqn_v3':
                # DQN: Q-value 기반
                q_values = model.q_net(model.policy.obs_to_tensor(observation)[0])
                q_values = q_values.detach().cpu().numpy().flatten()
                max_q = np.max(q_values)
                selected_q = q_values[action]
                # Normalized confidence: selected Q / max Q
                confidence = selected_q / (max_q + 1e-8)
                return float(np.clip(confidence, 0, 1))
            
            elif model_name == 'ppo_v3':
                # PPO: Policy probability 기반
                obs_tensor = model.policy.obs_to_tensor(observation)[0]
                distribution = model.policy.get_distribution(obs_tensor)
                log_prob = distribution.distribution.logits.detach().cpu().numpy().flatten()
                
                # Apply action mask if available
                if action_mask is not None:
                    log_prob = np.where(action_mask, log_prob, -np.inf)
                
                # Softmax to get probabilities
                exp_log_prob = np.exp(log_prob - np.max(log_prob))
                probs = exp_log_prob / np.sum(exp_log_prob)
                
                confidence = probs[action]
                return float(np.clip(confidence, 0, 1))
            
            else:
                return 0.5  # Default confidence
        
        except Exception as e:
            if self.verbose:
                print(f"[WARN] Confidence calculation failed for {model_name}: {e}")
            return 0.5
    
    def _get_continuous_confidence(
        self,
        model,
        observation: np.ndarray,
        action: np.ndarray,
        model_name: str
    ) -> float:
        """Continuous 모델의 confidence 계산"""
        try:
            # DDPG, SAC: Q-value 기반 (Critic network)
            obs_tensor = model.policy.obs_to_tensor(observation)[0]
            action_tensor = model.policy.actor.action_to_tensor(action)
            
            # Q-value 계산
            if hasattr(model.policy, 'critic'):
                q_value = model.policy.critic(obs_tensor, action_tensor)
            else:
                # SAC는 여러 critic이 있을 수 있음
                q_value = model.policy.critic_target(obs_tensor, action_tensor)[0]
            
            q_value = q_value.detach().cpu().numpy().flatten()[0]
            
            # Q-value를 0~1 범위로 정규화 (시그모이드 사용)
            confidence = 1.0 / (1.0 + np.exp(-q_value / 10.0))
            return float(np.clip(confidence, 0, 1))
        
        except Exception as e:
            if self.verbose:
                print(f"[WARN] Confidence calculation failed for {model_name}: {e}")
            return 0.5
    
    def _continuous_to_discrete(self, action: np.ndarray, model_name: str) -> int:
        """
        Continuous action을 discrete action으로 변환
        
        DDPG/SAC는 연속 액션 공간을 사용하므로,
        이를 discrete action으로 매핑해야 합니다.
        """
        try:
            from RLQO.DDPG_v1.config.action_decoder import decode_continuous_action
            hints = decode_continuous_action(action)
            
            # 힌트 조합을 discrete action으로 매핑
            # 간단한 휴리스틱: 가장 강한 힌트를 선택
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
            
            # 첫 번째 힌트를 사용 (가장 강한 힌트)
            first_hint = hints[0]
            return hint_to_action.get(first_hint, 0)
        
        except Exception as e:
            if self.verbose:
                print(f"[WARN] Continuous to discrete conversion failed for {model_name}: {e}")
            return 0  # Default: NO_ACTION
    
    def _apply_voting_strategy(
        self,
        predictions: Dict[str, int],
        confidences: Dict[str, float],
        query_type: str
    ) -> int:
        """투표 전략 적용"""
        
        if self.voting_strategy == 'majority':
            return majority_vote(predictions)
        
        elif self.voting_strategy == 'weighted':
            return weighted_vote(predictions, confidences)
        
        elif self.voting_strategy == 'equal':
            return equal_weighted_vote(predictions)
        
        elif self.voting_strategy == 'performance':
            weights = {k: self.performance_weights.get(k, 1.0) for k in predictions.keys()}
            return performance_based_vote(predictions, weights)
        
        elif self.voting_strategy == 'query_type':
            type_weights = QUERY_TYPE_WEIGHTS.get(query_type, QUERY_TYPE_WEIGHTS['DEFAULT'])
            weights = {k: type_weights.get(k, 0.25) for k in predictions.keys()}
            return query_type_based_vote(predictions, weights)
        
        else:
            # Default: weighted voting
            return weighted_vote(predictions, confidences)

