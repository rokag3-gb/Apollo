# -*- coding: utf-8 -*-
"""
PPO v1 개선 보상 함수

Query 타입별로 차별화된 보상을 제공하여 안전하고 효과적인 쿼리 최적화를 유도합니다.
"""

import sys
import os

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, apollo_ml_dir)


def calculate_reward_v1_improved(
    metrics_before: dict,
    metrics_after: dict,
    baseline_metrics: dict,
    query_type: str,
    action_id: int,
    action_name: str,
    step_num: int = 0,
    max_steps: int = 10
) -> float:
    """
    PPO v1 개선 보상 함수: Query 타입별 차별화된 보상
    
    핵심 개선:
    1. 위험한 액션 선택 시 타입별 강력한 페널티
    2. 안전한 액션 선택 시 보너스
    3. Query 타입별 가중치 조정
    
    Args:
        metrics_before: 이전 스텝의 메트릭
        metrics_after: 현재 스텝의 메트릭 (액션 적용 후)
        baseline_metrics: 베이스라인 메트릭 (힌트 없는 원본 쿼리)
        query_type: Query 타입 ('CTE', 'JOIN_HEAVY', 'TOP', 'SIMPLE')
        action_id: 선택된 액션 ID
        action_name: 선택된 액션 이름
        step_num: 현재 스텝 번호
        max_steps: 최대 스텝 수
    
    Returns:
        계산된 보상 값
    """
    from RLQO.PPO_v1.utils.query_classifier import (
        QUERY_TYPE_SAFE_ACTIONS,
        QUERY_TYPE_DANGEROUS_ACTIONS
    )
    
    # === 1. 위험한 액션 강력한 페널티 ===
    if action_id in QUERY_TYPE_DANGEROUS_ACTIONS.get(query_type, []):
        base_penalty = -20.0  # v3: -15.0 → v4: -20.0
        
        # 실제로 성능 악화된 경우 추가 페널티
        baseline_time = baseline_metrics.get('elapsed_time_ms', 1)
        after_time = metrics_after.get('elapsed_time_ms', 1)
        
        if baseline_time > 0:
            time_ratio = after_time / baseline_time
            
            # 2배 이상 느려진 경우
            if time_ratio > 2.0:
                return base_penalty - 10.0  # 최대 -30.0
            
            # 50% 이상 느려진 경우
            if time_ratio > 1.5:
                return base_penalty - 5.0  # -25.0
        
        return base_penalty
    
    # === 2. 안전한 액션 보너스 ===
    safety_bonus = 0.0
    if action_id in QUERY_TYPE_SAFE_ACTIONS.get(query_type, []):
        safety_bonus = 2.0
    
    # === 3. Query 타입별 가중치 ===
    type_weights = {
        'CTE': {
            'time': 0.8,
            'io': 0.2,
            'cpu': 0.0,
            'baseline': 0.0
        },  # CTE는 실행 시간 안정성 최우선
        'JOIN_HEAVY': {
            'time': 0.6,
            'io': 0.4,
            'cpu': 0.0,
            'baseline': 0.0
        },  # JOIN은 I/O 최적화도 중요
        'TOP': {
            'time': 0.7,
            'io': 0.3,
            'cpu': 0.0,
            'baseline': 0.0
        },  # 표준 가중치
        'SIMPLE': {
            'time': 0.7,
            'io': 0.3,
            'cpu': 0.0,
            'baseline': 0.0
        }  # 표준 가중치
    }
    weights = type_weights.get(query_type, type_weights['SIMPLE'])
    
    # === 4. 기본 보상 계산 (v3 로직 재사용) ===
    from RLQO.DQN_v3.env.v3_reward import calculate_reward_v3
    
    base_reward = calculate_reward_v3(
        metrics_before=metrics_before,
        metrics_after=metrics_after,
        baseline_metrics=baseline_metrics,
        step_num=step_num,
        max_steps=max_steps,
        weights=weights,
        action_safety_score=1.0,
        invalid_action=False
    )
    
    # === 5. 추가 안정성 보너스 ===
    # 베이스라인보다 느려지지 않았으면 보너스
    stability_bonus = 0.0
    baseline_time = baseline_metrics.get('elapsed_time_ms', 1)
    after_time = metrics_after.get('elapsed_time_ms', 1)
    
    if baseline_time > 0 and after_time <= baseline_time:
        stability_bonus = 1.0
    
    # === 6. 최종 보상 계산 ===
    total_reward = base_reward + safety_bonus + stability_bonus
    
    # 보상 범위 제한: [-30, +20]
    total_reward = max(-30.0, min(total_reward, 20.0))
    
    return total_reward


if __name__ == '__main__':
    print("=== PPO v1 개선 보상 함수 테스트 ===\n")
    
    # 테스트 데이터
    baseline = {'elapsed_time_ms': 100, 'logical_reads': 1000, 'cpu_time_ms': 70}
    before = baseline.copy()
    
    # 테스트 1: CTE 쿼리에서 위험한 액션 (MAXDOP 8)
    print("1. CTE 쿼리 + 위험한 액션 (MAXDOP 8):")
    after_bad = {'elapsed_time_ms': 400, 'logical_reads': 3000, 'cpu_time_ms': 300}
    reward = calculate_reward_v1_improved(
        before, after_bad, baseline,
        query_type='CTE',
        action_id=2,  # SET_MAXDOP_8
        action_name='SET_MAXDOP_8'
    )
    print(f"   보상: {reward:.4f} (예상: -30.0, 큰 페널티)")
    
    # 테스트 2: CTE 쿼리에서 안전한 액션
    print("\n2. CTE 쿼리 + 안전한 액션 (MAXDOP 1):")
    after_good = {'elapsed_time_ms': 80, 'logical_reads': 800, 'cpu_time_ms': 56}
    reward = calculate_reward_v1_improved(
        before, after_good, baseline,
        query_type='CTE',
        action_id=0,  # SET_MAXDOP_1
        action_name='SET_MAXDOP_1'
    )
    print(f"   보상: {reward:.4f} (예상: 양수 + 보너스)")
    
    # 테스트 3: JOIN_HEAVY에서 HASH JOIN (안전한 액션)
    print("\n3. JOIN_HEAVY + HASH JOIN (안전한 액션):")
    after_join = {'elapsed_time_ms': 70, 'logical_reads': 700, 'cpu_time_ms': 49}
    reward = calculate_reward_v1_improved(
        before, after_join, baseline,
        query_type='JOIN_HEAVY',
        action_id=3,  # USE_HASH_JOIN
        action_name='USE_HASH_JOIN'
    )
    print(f"   보상: {reward:.4f} (예상: 양수 + 보너스)")
    
    # 테스트 4: TOP 쿼리에서 FAST hint (안전한 액션)
    print("\n4. TOP 쿼리 + FAST 10 (안전한 액션):")
    after_top = {'elapsed_time_ms': 50, 'logical_reads': 500, 'cpu_time_ms': 35}
    reward = calculate_reward_v1_improved(
        before, after_top, baseline,
        query_type='TOP',
        action_id=14,  # FAST_10
        action_name='FAST_10'
    )
    print(f"   보상: {reward:.4f} (예상: 양수 + 보너스)")
    
    print("\n[SUCCESS] 개선된 보상 함수 테스트 완료!")

