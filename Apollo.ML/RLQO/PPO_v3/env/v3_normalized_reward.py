# -*- coding: utf-8 -*-
"""
PPO v3: Normalized Reward 함수

PPO v2의 Log scale 변환 + Baseline 개선률 + Clipping [-1, +1] 유지
새로운 위험 액션 반영
"""

import numpy as np
import sys
import os

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, apollo_ml_dir)

from RLQO.PPO_v3.config.query_action_mapping_v3 import is_dangerous_action


def calculate_reward_v3_normalized(
    metrics_before: dict,
    metrics_after: dict,
    baseline_metrics: dict,
    query_type: str,
    action_id: int
) -> float:
    """
    PPO v3 정규화된 보상 함수
    
    PPO v2 로직 유지:
    - Log scale 변환으로 variance 감소
    - Baseline 개선률 기반
    - Reward clipping [-1, +1]
    
    Args:
        metrics_before: 이전 스텝 메트릭
        metrics_after: 현재 스텝 메트릭
        baseline_metrics: 베이스라인 메트릭
        query_type: Query 타입
        action_id: 선택된 액션 ID (0-43)
    
    Returns:
        reward: [-1.0, +1.0] 범위의 정규화된 보상
    """
    
    # === 1. 위험 액션 강한 페널티 ===
    if is_dangerous_action(query_type, action_id):
        return -1.0  # 최대 페널티
    
    # === 2. Log scale 변환 ===
    baseline_time_log = np.log1p(baseline_metrics.get('elapsed_time_ms', 1.0))
    after_time_log = np.log1p(metrics_after.get('elapsed_time_ms', 1.0))
    
    baseline_io_log = np.log1p(baseline_metrics.get('logical_reads', 1))
    after_io_log = np.log1p(metrics_after.get('logical_reads', 1))
    
    # === 3. Baseline 대비 개선률 (log scale) ===
    time_improvement = (baseline_time_log - after_time_log) / max(baseline_time_log, 0.1)
    io_improvement = (baseline_io_log - after_io_log) / max(baseline_io_log, 0.1)
    
    # === 4. Query 타입별 가중치 (PPO v3 확장) ===
    type_weights = {
        'CTE': {'time': 0.8, 'io': 0.2},         # CTE는 시간 안정성 우선
        'JOIN_HEAVY': {'time': 0.5, 'io': 0.5},  # JOIN은 I/O 최적화 중요
        'TOP': {'time': 0.9, 'io': 0.1},         # TOP은 빠른 첫 행 반환
        'SIMPLE': {'time': 0.7, 'io': 0.3},      # 균형
        'AGGREGATE': {'time': 0.6, 'io': 0.4},   # 집계는 I/O도 중요
        'WINDOW': {'time': 0.8, 'io': 0.2},      # 윈도우 함수는 시간 우선
        'SUBQUERY': {'time': 0.7, 'io': 0.3}     # 서브쿼리는 균형
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
    print("=" * 80)
    print(" PPO v3: Normalized Reward 함수 테스트")
    print("=" * 80)
    
    baseline = {'elapsed_time_ms': 100.0, 'logical_reads': 1000, 'cpu_time_ms': 70.0}
    
    # 테스트 1: 위험 액션 (CTE + MAXDOP 9)
    print("\n1. 위험 액션 (CTE + MAXDOP 9):")
    after_dangerous = {'elapsed_time_ms': 400.0, 'logical_reads': 3000, 'cpu_time_ms': 300.0}
    reward = calculate_reward_v3_normalized(
        baseline, after_dangerous, baseline,
        query_type='CTE',
        action_id=18  # MAXDOP 9
    )
    print(f"   Reward: {reward:.4f} (예상: -1.0000)")
    
    # 테스트 2: 20% 개선
    print("\n2. 20% 개선 (100ms → 80ms):")
    after_good = {'elapsed_time_ms': 80.0, 'logical_reads': 800, 'cpu_time_ms': 56.0}
    reward = calculate_reward_v3_normalized(
        baseline, after_good, baseline,
        query_type='TOP',
        action_id=4  # FAST 50
    )
    print(f"   Reward: {reward:.4f} (예상: ~+0.4)")
    
    # 테스트 3: 20% 악화
    print("\n3. 20% 악화 (100ms → 120ms):")
    after_bad = {'elapsed_time_ms': 120.0, 'logical_reads': 1200, 'cpu_time_ms': 84.0}
    reward = calculate_reward_v3_normalized(
        baseline, after_bad, baseline,
        query_type='SIMPLE',
        action_id=13  # MAXDOP 4
    )
    print(f"   Reward: {reward:.4f} (예상: ~-0.4)")
    
    # 테스트 4: 안정성 유지
    print("\n4. 안정성 유지 (변화 없음):")
    after_same = baseline.copy()
    reward = calculate_reward_v3_normalized(
        baseline, after_same, baseline,
        query_type='AGGREGATE',
        action_id=43  # NO_ACTION
    )
    print(f"   Reward: {reward:.4f} (예상: ~+0.2, 안정성 보너스)")
    
    # 테스트 5: JOIN_HEAVY 쿼리 (시간/IO 균형 가중치)
    print("\n5. JOIN_HEAVY 쿼리 I/O 개선:")
    after_io_improved = {'elapsed_time_ms': 95.0, 'logical_reads': 600, 'cpu_time_ms': 65.0}
    reward = calculate_reward_v3_normalized(
        baseline, after_io_improved, baseline,
        query_type='JOIN_HEAVY',
        action_id=23  # HASH JOIN
    )
    print(f"   Reward: {reward:.4f} (I/O 개선 효과 반영)")
    
    # 테스트 6: 새로운 고급 액션 (FORCESEEK)
    print("\n6. 고급 액션 (FORCESEEK) 적용:")
    after_forceseek = {'elapsed_time_ms': 75.0, 'logical_reads': 700, 'cpu_time_ms': 50.0}
    reward = calculate_reward_v3_normalized(
        baseline, after_forceseek, baseline,
        query_type='TOP',
        action_id=33  # FORCESEEK
    )
    print(f"   Reward: {reward:.4f} (개선 시 보상)")
    
    print("\n" + "=" * 80)
    print(" [SUCCESS] Normalized Reward 함수 테스트 완료!")
    print("=" * 80)
    print("\n특징:")
    print("- Log scale: 비례 관계 유지")
    print("- Baseline 개선률 기반")
    print("- 범위: [-1.0, +1.0]")
    print("- 안정성 보너스: +0.2")
    print("- Query 타입별 시간/IO 가중치")
    print("=" * 80)

