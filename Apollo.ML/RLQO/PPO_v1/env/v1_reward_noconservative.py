# -*- coding: utf-8 -*-
"""
PPO v1 보상 함수 (No Conservative Mode)

Action 8 과도 선택 문제 해결을 위해 안전 보너스를 감소시킨 버전:
- 안전 보너스: +2.0 → +0.5
- 위험 페널티는 유지 (-20.0 ~ -30.0)
- 다양한 액션 선택을 유도
"""

import sys
import os

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, apollo_ml_dir)


def calculate_reward_v1_noconservative(
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
    PPO v1 보상 함수 (No Conservative Mode)
    
    v1_improved와의 차이:
    - 안전 보너스 감소: +2.0 → +0.5
    - 더 공정한 보상으로 다양한 액션 선택 유도
    
    Args:
        metrics_before: 이전 스텝의 메트릭
        metrics_after: 현재 스텝의 메트릭 (액션 적용 후)
        baseline_metrics: 베이스라인 메트릭
        query_type: Query 타입
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
    
    # === 1. 위험한 액션 강력한 페널티 (유지) ===
    if action_id in QUERY_TYPE_DANGEROUS_ACTIONS.get(query_type, []):
        base_penalty = -20.0
        
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
    
    # === 2. 안전한 액션 보너스 (감소) ===
    safety_bonus = 0.0
    if action_id in QUERY_TYPE_SAFE_ACTIONS.get(query_type, []):
        safety_bonus = 0.5  # ★★ 2.0 → 0.5 감소 ★★
    
    # === 3. Query 타입별 가중치 ===
    type_weights = {
        'CTE': {
            'time': 0.8,
            'io': 0.2,
            'cpu': 0.0,
            'baseline': 0.0
        },
        'JOIN_HEAVY': {
            'time': 0.6,
            'io': 0.4,
            'cpu': 0.0,
            'baseline': 0.0
        },
        'TOP': {
            'time': 0.7,
            'io': 0.3,
            'cpu': 0.0,
            'baseline': 0.0
        },
        'SIMPLE': {
            'time': 0.7,
            'io': 0.3,
            'cpu': 0.0,
            'baseline': 0.0
        }
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
    
    # === 5. 안정성 보너스 (유지) ===
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
    print("=== PPO v1 보상 함수 테스트 (No Conservative) ===\n")
    
    # 테스트 데이터
    baseline = {'elapsed_time_ms': 100, 'logical_reads': 1000, 'cpu_time_ms': 70}
    before = baseline.copy()
    
    # 테스트 1: 위험한 액션
    print("1. CTE 쿼리 + 위험한 액션 (MAXDOP 8):")
    after_bad = {'elapsed_time_ms': 400, 'logical_reads': 3000, 'cpu_time_ms': 300}
    reward = calculate_reward_v1_noconservative(
        before, after_bad, baseline,
        query_type='CTE',
        action_id=2,
        action_name='SET_MAXDOP_8'
    )
    print(f"   보상: {reward:.4f} (페널티 -30.0)")
    
    # 테스트 2: 안전한 액션
    print("\n2. CTE 쿼리 + 안전한 액션 (MAXDOP 1):")
    after_good = {'elapsed_time_ms': 80, 'logical_reads': 800, 'cpu_time_ms': 56}
    reward = calculate_reward_v1_noconservative(
        before, after_good, baseline,
        query_type='CTE',
        action_id=0,
        action_name='SET_MAXDOP_1'
    )
    print(f"   보상: {reward:.4f} (base + 0.5 안전 보너스)")
    
    # 테스트 3: 일반 액션 (안전/위험 목록 외)
    print("\n3. 일반 액션 (DISABLE_PARAMETER_SNIFFING):")
    after_normal = {'elapsed_time_ms': 90, 'logical_reads': 900, 'cpu_time_ms': 63}
    reward = calculate_reward_v1_noconservative(
        before, after_normal, baseline,
        query_type='CTE',
        action_id=8,
        action_name='DISABLE_PARAMETER_SNIFFING'
    )
    print(f"   보상: {reward:.4f} (base reward만)")
    
    print("\n[SUCCESS] 보상 함수 테스트 완료!")
    print("\n주요 변경사항:")
    print("- 안전 보너스: +2.0 → +0.5 감소")
    print("- 다양한 액션 선택을 유도")

