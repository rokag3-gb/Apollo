# -*- coding: utf-8 -*-
"""
Ensemble v2: Voting Strategies

다양한 투표 전략을 구현합니다.
v2에서는 safety_first_vote를 추가하여 안전성을 우선합니다.
"""

import numpy as np
from typing import Dict
from collections import Counter


def majority_vote(predictions: Dict[str, int]) -> int:
    """
    Majority Voting: 가장 많이 선택된 액션 반환
    
    Args:
        predictions: {model_name: action}
    
    Returns:
        most_common_action: 최다 득표 액션
    """
    if len(predictions) == 0:
        return 18  # NO_ACTION
    
    # Count votes
    vote_counts = Counter(predictions.values())
    most_common = vote_counts.most_common(1)[0]
    
    return most_common[0]


def weighted_vote(predictions: Dict[str, int], confidences: Dict[str, float]) -> int:
    """
    Weighted Voting: Confidence로 가중치를 준 투표
    
    Args:
        predictions: {model_name: action}
        confidences: {model_name: confidence}
    
    Returns:
        weighted_action: 가중 투표 결과
    """
    if len(predictions) == 0:
        return 18  # NO_ACTION
    
    # 액션별 가중치 합산
    action_weights = {}
    
    for model_name, action in predictions.items():
        confidence = confidences.get(model_name, 1.0)
        
        if action not in action_weights:
            action_weights[action] = 0.0
        
        action_weights[action] += confidence
    
    # 최고 가중치 액션 선택
    best_action = max(action_weights.items(), key=lambda x: x[1])[0]
    
    return best_action


def equal_weighted_vote(predictions: Dict[str, int]) -> int:
    """
    Equal Weighted Voting: 모든 모델에 동일한 가중치
    
    Args:
        predictions: {model_name: action}
    
    Returns:
        action: 균등 가중 투표 결과
    """
    if len(predictions) == 0:
        return 18  # NO_ACTION
    
    # 모든 confidence를 1.0으로 설정
    confidences = {model: 1.0 for model in predictions.keys()}
    
    return weighted_vote(predictions, confidences)


def performance_based_vote(predictions: Dict[str, int], performance_weights: Dict[str, float]) -> int:
    """
    Performance-Based Voting: 모델의 평균 성능으로 가중치
    
    Args:
        predictions: {model_name: action}
        performance_weights: {model_name: performance_score}
    
    Returns:
        action: 성능 기반 가중 투표 결과
    """
    if len(predictions) == 0:
        return 18  # NO_ACTION
    
    # 성능 가중치를 confidence로 사용
    confidences = {model: performance_weights.get(model, 1.0) for model in predictions.keys()}
    
    return weighted_vote(predictions, confidences)


def query_type_based_vote(predictions: Dict[str, int], type_weights: Dict[str, float]) -> int:
    """
    Query Type-Based Voting: 쿼리 타입에 따른 모델 가중치
    
    Args:
        predictions: {model_name: action}
        type_weights: {model_name: weight} (쿼리 타입별)
    
    Returns:
        action: 쿼리 타입 기반 가중 투표 결과
    """
    if len(predictions) == 0:
        return 18  # NO_ACTION
    
    # 쿼리 타입별 가중치를 confidence로 사용
    confidences = {model: type_weights.get(model, 0.25) for model in predictions.keys()}
    
    return weighted_vote(predictions, confidences)


def safety_first_vote(
    predictions: Dict[str, int],
    confidences: Dict[str, float],
    safety_threshold: float = 0.2,
    disagreement_threshold: float = 0.1
) -> int:
    """
    Safety-First Voting: 안전성 우선 투표 (v2 신규)
    
    규칙:
    1. 모든 모델의 평균 confidence < safety_threshold → NO_ACTION
    2. 모델 간 disagreement > disagreement_threshold → NO_ACTION
    3. 위 조건을 통과하면 Confidence 가중 투표
    
    Args:
        predictions: {model_name: action}
        confidences: {model_name: confidence}
        safety_threshold: 평균 confidence 임계값 (default: 0.2, v2 완화)
        disagreement_threshold: 동의율 임계값 (default: 0.1, v2 추가 완화)
    
    Returns:
        action: 안전성 우선 투표 결과
    """
    if len(predictions) == 0:
        return 18  # NO_ACTION
    
    # 1. 평균 confidence 체크
    avg_conf = np.mean(list(confidences.values()))
    if avg_conf < safety_threshold:
        # Confidence가 너무 낮으면 NO_ACTION
        return 18
    
    # 2. Disagreement 체크 (모델 간 의견 일치도)
    action_counts = Counter(predictions.values())
    max_count = max(action_counts.values())
    agreement_rate = max_count / len(predictions)
    
    if agreement_rate < disagreement_threshold:
        # 의견이 너무 분산되면 NO_ACTION (안전)
        return 18
    
    # 3. 안전성 조건을 통과하면 Weighted vote
    return weighted_vote(predictions, confidences)


def adaptive_vote(
    predictions: Dict[str, int],
    confidences: Dict[str, float],
    recent_performance: Dict[str, float]
) -> int:
    """
    Adaptive Voting: 최근 성능에 따라 동적으로 가중치 조정
    
    Args:
        predictions: {model_name: action}
        confidences: {model_name: confidence}
        recent_performance: {model_name: recent_speedup}
    
    Returns:
        action: 적응적 투표 결과
    """
    if len(predictions) == 0:
        return 18  # NO_ACTION
    
    # Confidence와 최근 성능을 결합
    combined_weights = {}
    for model_name in predictions.keys():
        conf = confidences.get(model_name, 0.5)
        perf = recent_performance.get(model_name, 1.0)
        
        # Combine: confidence * performance
        combined_weights[model_name] = conf * perf
    
    return weighted_vote(predictions, combined_weights)


def consensus_vote(predictions: Dict[str, int], threshold: float = 0.75) -> int:
    """
    Consensus Voting: 일정 비율 이상 동의하는 액션만 선택
    
    Args:
        predictions: {model_name: action}
        threshold: 합의 임계값 (0.75 = 75% 이상 동의)
    
    Returns:
        action: 합의된 액션 (합의 실패 시 NO_ACTION)
    """
    if len(predictions) == 0:
        return 18  # NO_ACTION
    
    # Count votes
    vote_counts = Counter(predictions.values())
    total_votes = len(predictions)
    
    # Check consensus
    for action, count in vote_counts.most_common():
        if count / total_votes >= threshold:
            return action
    
    # No consensus: return NO_ACTION
    return 18


def rank_based_vote(predictions: Dict[str, int], model_ranks: Dict[str, int]) -> int:
    """
    Rank-Based Voting: 모델의 순위에 따라 가중치 부여
    
    Args:
        predictions: {model_name: action}
        model_ranks: {model_name: rank} (1=best, 2=second, ...)
    
    Returns:
        action: 순위 기반 투표 결과
    """
    if len(predictions) == 0:
        return 18  # NO_ACTION
    
    # Rank를 가중치로 변환 (rank 1 = highest weight)
    max_rank = max(model_ranks.values())
    confidences = {
        model: (max_rank - model_ranks.get(model, max_rank) + 1) / max_rank
        for model in predictions.keys()
    }
    
    return weighted_vote(predictions, confidences)

