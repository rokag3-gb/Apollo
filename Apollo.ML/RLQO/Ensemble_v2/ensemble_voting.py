# -*- coding: utf-8 -*-
"""
Ensemble v2: Voting Ensemble

4개 모델(DQN v4, PPO v3, DDPG v1, SAC v1)의 예측을 결합하는
개선된 Voting Ensemble 구현

v2 주요 개선사항:
1. Continuous-to-Discrete 변환 로직 개선 (DDPG/SAC 활성화)
2. Safety-First Voting
3. Query-Type Aware Routing (TOP 쿼리 최적화)
4. Action Validation & Filtering
"""

import os
import sys
import numpy as np
from typing import Dict, List, Tuple, Optional

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

from RLQO.Ensemble_v2.config.ensemble_config import (
    MODEL_PATHS, MODEL_TYPES, PERFORMANCE_WEIGHTS,
    QUERY_TYPE_WEIGHTS, CONFIDENCE_THRESHOLD,
    SAFETY_CONFIG, TOP_QUERY_CONFIG, ACTION_VALIDATOR_CONFIG
)
from RLQO.Ensemble_v2.voting_strategies import (
    majority_vote, weighted_vote, equal_weighted_vote,
    performance_based_vote, query_type_based_vote, safety_first_vote
)
from RLQO.Ensemble_v2.action_converter import ContinuousToDiscreteConverter
from RLQO.Ensemble_v2.query_type_router import QueryTypeRouter
from RLQO.Ensemble_v2.action_validator import ActionValidator


class VotingEnsembleV2:
    """
    Voting Ensemble v2 for Query Optimization
    
    4개의 RL 모델을 결합하여 쿼리 최적화 액션을 선택합니다.
    v2에서는 DDPG/SAC도 제대로 활용하며, 안전성과 TOP 쿼리 최적화에 초점을 맞춥니다.
    """
    
    def __init__(
        self,
        model_paths: Dict[str, str] = None,
        voting_strategy: str = 'safety_first',
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        use_action_validator: bool = True,
        use_query_router: bool = True,
        verbose: bool = True
    ):
        """
        Args:
            model_paths: 모델 경로 딕셔너리
            voting_strategy: 투표 전략 ('safety_first' 권장)
            confidence_threshold: Confidence threshold
            use_action_validator: Action validator 사용 여부
            use_query_router: Query type router 사용 여부
            verbose: 로깅 여부
        """
        self.model_paths = model_paths or MODEL_PATHS
        self.voting_strategy = voting_strategy
        self.confidence_threshold = confidence_threshold
        self.use_action_validator = use_action_validator
        self.use_query_router = use_query_router
        self.verbose = verbose
        
        self.models = {}
        self.model_types = MODEL_TYPES
        self.performance_weights = PERFORMANCE_WEIGHTS
        
        # v2 신규 컴포넌트
        self.action_converter = ContinuousToDiscreteConverter(verbose=False)
        self.query_router = QueryTypeRouter(verbose=verbose) if use_query_router else None
        self.action_validator = ActionValidator(
            min_baseline_for_maxdop=ACTION_VALIDATOR_CONFIG['min_baseline_for_maxdop'],
            failure_rate_threshold=ACTION_VALIDATOR_CONFIG['failure_rate_threshold'],
            enable_failure_tracking=ACTION_VALIDATOR_CONFIG['enable_failure_tracking'],
            verbose=verbose
        ) if use_action_validator else None
        
        # 로드 성공 여부 추적
        self.loaded_models = []
        
    def load_models(self):
        """4개 모델을 로드합니다."""
        if self.verbose:
            print("=" * 80)
            print("Loading Ensemble v2 Models")
            print("=" * 80)
        
        # DQN v4
        try:
            if os.path.exists(self.model_paths['dqn_v4']):
                self.models['dqn_v4'] = DQN.load(self.model_paths['dqn_v4'])
                self.loaded_models.append('dqn_v4')
                if self.verbose:
                    print(f"[OK] DQN v4 loaded: {self.model_paths['dqn_v4']}")
            else:
                if self.verbose:
                    print(f"[X] DQN v4 not found: {self.model_paths['dqn_v4']}")
        except Exception as e:
            if self.verbose:
                print(f"[X] DQN v4 load failed: {e}")
        
        # PPO v3
        try:
            if os.path.exists(self.model_paths['ppo_v3']):
                self.models['ppo_v3'] = MaskablePPO.load(self.model_paths['ppo_v3'])
                self.loaded_models.append('ppo_v3')
                if self.verbose:
                    print(f"[OK] PPO v3 loaded: {self.model_paths['ppo_v3']}")
            else:
                if self.verbose:
                    print(f"[X] PPO v3 not found: {self.model_paths['ppo_v3']}")
        except Exception as e:
            if self.verbose:
                print(f"[X] PPO v3 load failed: {e}")
        
        # DDPG v1
        try:
            if os.path.exists(self.model_paths['ddpg_v1']):
                self.models['ddpg_v1'] = DDPG.load(self.model_paths['ddpg_v1'])
                self.loaded_models.append('ddpg_v1')
                if self.verbose:
                    print(f"[OK] DDPG v1 loaded: {self.model_paths['ddpg_v1']}")
            else:
                if self.verbose:
                    print(f"[X] DDPG v1 not found: {self.model_paths['ddpg_v1']}")
        except Exception as e:
            if self.verbose:
                print(f"[X] DDPG v1 load failed: {e}")
        
        # SAC v1
        try:
            if os.path.exists(self.model_paths['sac_v1']):
                self.models['sac_v1'] = SAC.load(self.model_paths['sac_v1'])
                self.loaded_models.append('sac_v1')
                if self.verbose:
                    print(f"[OK] SAC v1 loaded: {self.model_paths['sac_v1']}")
            else:
                if self.verbose:
                    print(f"[X] SAC v1 not found: {self.model_paths['sac_v1']}")
        except Exception as e:
            if self.verbose:
                print(f"[X] SAC v1 load failed: {e}")
        
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
        query_info: Optional[Dict] = None,
        action_mask: Optional[np.ndarray] = None
    ) -> Tuple[int, Dict]:
        """
        Ensemble 예측: 4개 모델의 예측을 결합
        
        Args:
            observation: 환경 상태 (observation)
            query_type: 쿼리 타입
            query_info: 쿼리 정보 {'baseline_ms': float, ...}
            action_mask: 액션 마스크 (PPO용)
        
        Returns:
            final_action: 최종 선택된 액션
            info: 상세 정보
        """
        predictions = {}
        confidences = {}
        
        # 1. 각 모델로부터 예측 수집
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
                    
                    # Confidence 계산
                    confidence = self._get_discrete_confidence(model, observation, action, model_name, action_mask)
                    
                    predictions[model_name] = int(action)
                    confidences[model_name] = confidence
                
                elif model_type == 'continuous':
                    # DDPG, SAC: continuous action → discrete action으로 변환 (v2 개선)
                    action, _ = model.predict(observation, deterministic=True)
                    
                    # v2: 개선된 변환 로직 사용
                    discrete_action = self.action_converter.convert(action)
                    
                    # Confidence 계산
                    confidence = self._get_continuous_confidence(model, observation, action, model_name)
                    
                    predictions[model_name] = discrete_action
                    confidences[model_name] = confidence
                    
            except Exception as e:
                if self.verbose:
                    print(f"[WARN] {model_name} prediction failed: {e}")
                continue
        
        # 2. Confidence threshold 적용
        filtered_predictions = {
            k: v for k, v in predictions.items()
            if confidences[k] >= self.confidence_threshold
        }
        filtered_confidences = {
            k: v for k, v in confidences.items()
            if v >= self.confidence_threshold
        }
        
        # 3. Action Validator 적용 (v2 신규)
        if self.use_action_validator and self.action_validator and query_info:
            filtered_predictions, filtered_confidences = self.action_validator.filter_unsafe_actions(
                filtered_predictions, filtered_confidences, query_info
            )
        
        # 4. Query Type Router 적용 (v2 신규)
        if self.use_query_router and self.query_router:
            filtered_predictions, filtered_confidences = self.query_router.filter_actions_for_query(
                query_type, filtered_predictions, filtered_confidences
            )
            
            # TOP 쿼리에 대해 NO_ACTION boost
            filtered_confidences = self.query_router.boost_no_action_for_top(
                query_type, filtered_predictions, filtered_confidences
            )
        
        # 5. 투표 전략에 따라 최종 액션 선택
        if len(filtered_predictions) == 0:
            final_action = 18  # NO_ACTION (모든 모델이 threshold 이하)
        else:
            final_action = self._apply_voting_strategy(
                filtered_predictions,
                filtered_confidences,
                query_type
            )
        
        # 6. 상세 정보 반환
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
            if model_name == 'dqn_v4':
                # DQN: Q-value 기반
                q_values = model.q_net(model.policy.obs_to_tensor(observation)[0])
                q_values = q_values.detach().cpu().numpy().flatten()
                max_q = np.max(q_values)
                selected_q = q_values[action]
                # Normalized confidence
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
        
        elif self.voting_strategy == 'safety_first':
            # v2 신규: Safety-First Voting
            return safety_first_vote(
                predictions,
                confidences,
                safety_threshold=SAFETY_CONFIG['avg_confidence_threshold'],
                disagreement_threshold=SAFETY_CONFIG['disagreement_threshold']
            )
        
        else:
            # Default: safety_first
            return safety_first_vote(
                predictions,
                confidences,
                safety_threshold=SAFETY_CONFIG['avg_confidence_threshold'],
                disagreement_threshold=SAFETY_CONFIG['disagreement_threshold']
            )
    
    def record_action_result(self, query_type: str, action_id: int, speedup: float):
        """액션 실행 결과를 기록 (Action Validator가 학습에 사용)"""
        if self.action_validator:
            self.action_validator.record_action_result(query_type, action_id, speedup)
    
    def get_stats(self) -> Dict:
        """전체 통계 반환"""
        stats = {
            'loaded_models': self.loaded_models,
            'voting_strategy': self.voting_strategy,
        }
        
        if self.action_converter:
            stats['action_converter'] = self.action_converter.get_stats()
        
        if self.query_router:
            stats['query_router'] = self.query_router.get_stats()
        
        if self.action_validator:
            stats['action_validator'] = self.action_validator.get_stats()
        
        return stats
    
    def print_stats(self):
        """전체 통계 출력"""
        print("\n" + "=" * 80)
        print("Ensemble v2 Statistics")
        print("=" * 80)
        print(f"Loaded models: {self.loaded_models}")
        print(f"Voting strategy: {self.voting_strategy}")
        
        if self.action_converter:
            print()
            self.action_converter.print_stats()
        
        if self.query_router:
            print()
            self.query_router.print_stats()
        
        if self.action_validator:
            print()
            self.action_validator.print_stats()

