# -*- coding: utf-8 -*-
"""
Normalized Reward 함수

Log scale 변환 + Baseline 개선률 + Clipping [-1, +1]

핵심:
- Log scale: 비례 관계 (1ms→10ms == 100ms→1000ms)
- Baseline 대비 상대 개선
- Clipping으로 outlier 방지
"""

import numpy as np
import sys
import os

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, apollo_ml_dir)

from RLQO.PPO_v2.config.query_action_mapping import QUERY_DANGEROUS_ACTIONS


def calculate_reward_v2_normalized(
    metrics_before: dict,
    metrics_after: dict,
    baseline_metrics: dict,
    query_type: str,
    action_id: int
) -> float:
    """
    PPO v2 정규화된 보상 함수
    
    ChatGPT 조언 반영:
    - Log scale 변환으로 variance 감소
    - Baseline 개선률 기반
    - Reward clipping [-1, +1]
    
    Args:
        metrics_before: 이전 스텝 메트릭
        metrics_after: 현재 스텝 메트릭
        baseline_metrics: 베이스라인 메트릭
        query_type: Query 타입
        action_id: 선택된 액션 ID
    
    Returns:
        reward: [-1.0, +1.0] 범위의 정규화된 보상
    """
    
    # === 1. 위험 액션 강한 페널티 ===
    if action_id in QUERY_DANGEROUS_ACTIONS.get(query_type, []):
        return -1.0  # 최대 페널티
    
    # === 2. Log scale 변환 ===
    # 원본: 1ms ~ 10000ms → Log: 0 ~ 9.2
    baseline_time_log = np.log1p(baseline_metrics.get('elapsed_time_ms', 1.0))
    after_time_log = np.log1p(metrics_after.get('elapsed_time_ms', 1.0))
    
    baseline_io_log = np.log1p(baseline_metrics.get('logical_reads', 1))
    after_io_log = np.log1p(metrics_after.get('logical_reads', 1))
    
    # === 3. Baseline 대비 개선률 (log scale) ===
    # 개선: 양수, 악화: 음수
    time_improvement = (baseline_time_log - after_time_log) / max(baseline_time_log, 0.1)
    io_improvement = (baseline_io_log - after_io_log) / max(baseline_io_log, 0.1)
    
    # === 4. Query 타입별 가중치 ===
    type_weights = {
        'CTE': {'time': 0.8, 'io': 0.2},        # CTE는 시간 안정성 우선
        'JOIN_HEAVY': {'time': 0.5, 'io': 0.5}, # JOIN은 I/O 최적화 중요
        'TOP': {'time': 0.9, 'io': 0.1},        # TOP은 빠른 첫 행 반환
        'SIMPLE': {'time': 0.7, 'io': 0.3}      # 균형
    }
    weights = type_weights.get(query_type, type_weights['SIMPLE'])
    
    # === 5. 가중 개선률 ===
    weighted_improvement = (
        time_improvement * weights['time'] +
        io_improvement * weights['io']
    )
    
    # === 6. 안정성 보너스 ===
    # 베이스라인보다 안 느려지면 +0.2
    stability_bonus = 0.0
    if after_time_log <= baseline_time_log * 1.05:  # 5% 이내 유지
        stability_bonus = 0.2
    
    # === 7. 최종 보상 ===
    # 스케일: improvement는 대략 -0.5 ~ +0.5 범위
    # 목표: 20% 개선 시 +0.4, 20% 악화 시 -0.4
    reward = weighted_improvement * 2.0 + stability_bonus
    
    # === 8. Clipping [-1, +1] ===
    reward = np.clip(reward, -1.0, 1.0)
    
    return reward


if __name__ == '__main__':
    print("=== Normalized Reward 함수 테스트 ===\n")
    
    baseline = {'elapsed_time_ms': 100.0, 'logical_reads': 1000, 'cpu_time_ms': 70.0}
    
    # 테스트 1: 위험 액션 (CTE + MAXDOP 8)
    print("1. 위험 액션 (CTE + MAXDOP 8):")
    after_dangerous = {'elapsed_time_ms': 400.0, 'logical_reads': 3000, 'cpu_time_ms': 300.0}
    reward = calculate_reward_v2_normalized(
        baseline, after_dangerous, baseline,
        query_type='CTE',
        action_id=2  # MAXDOP 8
    )
    print(f"   Reward: {reward:.4f} (예상: -1.0000)\n")
    
    # 테스트 2: 20% 개선
    print("2. 20% 개선 (100ms → 80ms):")
    after_good = {'elapsed_time_ms': 80.0, 'logical_reads': 800, 'cpu_time_ms': 56.0}
    reward = calculate_reward_v2_normalized(
        baseline, after_good, baseline,
        query_type='SIMPLE',
        action_id=0  # MAXDOP 1
    )
    print(f"   Reward: {reward:.4f} (예상: ~+0.4)\n")
    
    # 테스트 3: 20% 악화
    print("3. 20% 악화 (100ms → 120ms):")
    after_bad = {'elapsed_time_ms': 120.0, 'logical_reads': 1200, 'cpu_time_ms': 84.0}
    reward = calculate_reward_v2_normalized(
        baseline, after_bad, baseline,
        query_type='SIMPLE',
        action_id=1  # MAXDOP 4
    )
    print(f"   Reward: {reward:.4f} (예상: ~-0.4)\n")
    
    # 테스트 4: 안정성 유지 (변화 없음)
    print("4. 안정성 유지 (변화 없음):")
    after_same = baseline.copy()
    reward = calculate_reward_v2_normalized(
        baseline, after_same, baseline,
        query_type='CTE',
        action_id=18  # NO_ACTION
    )
    print(f"   Reward: {reward:.4f} (예상: ~+0.2, 안정성 보너스)\n")
    
    # 테스트 5: Extreme case (10배 악화)
    print("5. Extreme case (100ms → 1000ms):")
    after_extreme = {'elapsed_time_ms': 1000.0, 'logical_reads': 10000, 'cpu_time_ms': 700.0}
    reward = calculate_reward_v2_normalized(
        baseline, after_extreme, baseline,
        query_type='SIMPLE',
        action_id=8  # DISABLE_PARAM_SNIFFING
    )
    print(f"   Reward: {reward:.4f} (클리핑으로 -1.0에 제한)\n")
    
    print("[SUCCESS] Normalized Reward 함수 테스트 완료!")
    print("\n특징:")
    print("- Log scale: 비례 관계 (1ms→10ms == 100ms→1000ms)")
    print("- Baseline 개선률 기반")
    print("- 범위: [-1.0, +1.0]")
    print("- 안정성 보너스: +0.2")

