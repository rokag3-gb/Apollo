# -*- coding: utf-8 -*-
"""
DQN v2: 개선된 보상 함수
v1의 단순 선형 보상을 개선하여 다음 요소를 추가:
1. 비선형 보상: 큰 개선에 보너스
2. 다차원 메트릭: CPU, 메모리 등 추가
3. 점진적 페널티: 실패 시 가혹한 -100 대신 상황별 페널티
4. 베이스라인 대비 절대 개선도 반영
"""

def calculate_reward_v2(
    metrics_before: dict,
    metrics_after: dict,
    baseline_metrics: dict,
    step_num: int = 0,
    max_steps: int = 10,
    weights: dict = None
) -> float:
    """
    v2 보상 함수: 다차원 메트릭과 비선형 보상을 지원합니다.
    
    Args:
        metrics_before: 이전 스텝의 메트릭
        metrics_after: 현재 스텝의 메트릭 (액션 적용 후)
        baseline_metrics: 베이스라인 메트릭 (힌트 없는 원본 쿼리)
        step_num: 현재 스텝 번호 (페널티 조정용)
        max_steps: 최대 스텝 수
        weights: 각 메트릭의 가중치
    
    Returns:
        계산된 보상 값
    """
    if weights is None:
        weights = {
            'time': 0.50,      # 실행 시간 (가장 중요)
            'io': 0.25,        # 논리적 읽기
            'cpu': 0.15,       # CPU 시간
            'baseline': 0.10   # 베이스라인 대비 개선도
        }
    
    # === 1. 메트릭 추출 ===
    time_before = metrics_before.get('elapsed_time_ms', 0)
    time_after = metrics_after.get('elapsed_time_ms', 0)
    time_baseline = baseline_metrics.get('elapsed_time_ms', time_before)
    
    io_before = metrics_before.get('logical_reads', 0)
    io_after = metrics_after.get('logical_reads', 0)
    io_baseline = baseline_metrics.get('logical_reads', io_before)
    
    cpu_before = metrics_before.get('cpu_time_ms', 0)
    cpu_after = metrics_after.get('cpu_time_ms', 0)
    cpu_baseline = baseline_metrics.get('cpu_time_ms', cpu_before)
    
    # === 2. 실패 처리 (elapsed_time이 inf 또는 매우 큰 값) ===
    if time_after == float('inf') or time_after > time_baseline * 10:
        # 점진적 페널티: 초기 스텝에서는 덜 가혹하게
        penalty_base = -10.0
        penalty_multiplier = 1 + (step_num / max_steps)
        return penalty_base * penalty_multiplier
    
    # === 3. 각 메트릭별 개선률 계산 ===
    # 이전 스텝 대비 개선률
    if time_before > 0:
        time_improvement = (time_before - time_after) / time_before
    else:
        time_improvement = 0.0
    
    if io_before > 0:
        io_improvement = (io_before - io_after) / io_before
    else:
        io_improvement = 0.0
    
    if cpu_before > 0:
        cpu_improvement = (cpu_before - cpu_after) / cpu_before
    else:
        cpu_improvement = 0.0
    
    # 베이스라인 대비 개선률
    if time_baseline > 0:
        baseline_improvement = (time_baseline - time_after) / time_baseline
    else:
        baseline_improvement = 0.0
    
    # === 4. 기본 보상 계산 (가중 평균) ===
    base_reward = (
        weights['time'] * time_improvement +
        weights['io'] * io_improvement +
        weights['cpu'] * cpu_improvement +
        weights['baseline'] * baseline_improvement
    )
    
    # === 5. 비선형 보너스: 큰 개선에 추가 보상 ===
    bonus = 0.0
    
    # 베이스라인 대비 30% 이상 개선 시 보너스
    if baseline_improvement > 0.3:
        bonus += 0.5 * baseline_improvement
    
    # 베이스라인 대비 50% 이상 개선 시 추가 보너스
    if baseline_improvement > 0.5:
        bonus += 1.0 * baseline_improvement
    
    # 이전 스텝 대비 20% 이상 개선 시 작은 보너스 (연속 개선 장려)
    if time_improvement > 0.2:
        bonus += 0.2
    
    # === 6. 페널티: 성능 악화에 대한 패널티 ===
    penalty = 0.0
    
    # 베이스라인보다 50% 이상 느려진 경우 큰 페널티
    if baseline_improvement < -0.5:
        penalty = -2.0 * abs(baseline_improvement)
    # 베이스라인보다 20% 이상 느려진 경우 작은 페널티
    elif baseline_improvement < -0.2:
        penalty = -0.5 * abs(baseline_improvement)
    
    # === 7. 최종 보상 계산 ===
    total_reward = base_reward + bonus + penalty
    
    # 보상 범위 제한: [-5, 5]
    total_reward = max(-5.0, min(total_reward, 5.0))
    
    return total_reward


def calculate_reward_simple(metrics_before: dict, metrics_after: dict) -> float:
    """
    간단한 보상 함수 (v1 호환성 유지용)
    단순히 시간과 IO 개선률만 반영합니다.
    """
    time_before = metrics_before.get('elapsed_time_ms', 0)
    time_after = metrics_after.get('elapsed_time_ms', 0)
    io_before = metrics_before.get('logical_reads', 0)
    io_after = metrics_after.get('logical_reads', 0)
    
    if time_before <= 0:
        reward_time = 0.0
    else:
        reward_time = (time_before - time_after) / time_before
    
    if io_before <= 0:
        reward_io = 0.0
    else:
        reward_io = (io_before - io_after) / io_before
    
    return 0.7 * reward_time + 0.3 * reward_io


if __name__ == '__main__':
    print("=== DQN v2 보상 함수 테스트 ===\n")
    
    baseline = {'elapsed_time_ms': 100, 'logical_reads': 1000, 'cpu_time_ms': 70}
    before = baseline.copy()
    
    # 테스트 케이스 1: 큰 개선 (50% 감소)
    print("1. 큰 개선 (50% 시간 감소):")
    after_improved = {'elapsed_time_ms': 50, 'logical_reads': 500, 'cpu_time_ms': 35}
    reward = calculate_reward_v2(before, after_improved, baseline, step_num=0, max_steps=10)
    print(f"   보상: {reward:.4f} (예상: 양수 + 보너스)")
    
    # 테스트 케이스 2: 작은 개선 (10% 감소)
    print("\n2. 작은 개선 (10% 시간 감소):")
    after_small = {'elapsed_time_ms': 90, 'logical_reads': 900, 'cpu_time_ms': 63}
    reward = calculate_reward_v2(before, after_small, baseline, step_num=1, max_steps=10)
    print(f"   보상: {reward:.4f} (예상: 작은 양수)")
    
    # 테스트 케이스 3: 성능 악화 (50% 증가)
    print("\n3. 성능 악화 (50% 시간 증가):")
    after_worse = {'elapsed_time_ms': 150, 'logical_reads': 1500, 'cpu_time_ms': 105}
    reward = calculate_reward_v2(before, after_worse, baseline, step_num=2, max_steps=10)
    print(f"   보상: {reward:.4f} (예상: 음수 + 페널티)")
    
    # 테스트 케이스 4: 쿼리 실행 실패
    print("\n4. 쿼리 실행 실패:")
    after_failed = {'elapsed_time_ms': float('inf'), 'logical_reads': 0, 'cpu_time_ms': 0}
    reward = calculate_reward_v2(before, after_failed, baseline, step_num=0, max_steps=10)
    print(f"   보상: {reward:.4f} (예상: 초기 스텝 페널티 ~-10)")
    
    # 테스트 케이스 5: 후반 스텝 실패 (더 큰 페널티)
    print("\n5. 후반 스텝 실패:")
    reward = calculate_reward_v2(before, after_failed, baseline, step_num=8, max_steps=10)
    print(f"   보상: {reward:.4f} (예상: 후반 스텝 페널티 ~-18)")
    
    # 테스트 케이스 6: 연속 개선
    print("\n6. 연속 개선 시나리오:")
    step1 = {'elapsed_time_ms': 80, 'logical_reads': 800, 'cpu_time_ms': 56}
    step2 = {'elapsed_time_ms': 60, 'logical_reads': 600, 'cpu_time_ms': 42}
    
    reward1 = calculate_reward_v2(before, step1, baseline, step_num=0, max_steps=10)
    print(f"   Step 1 보상: {reward1:.4f}")
    
    reward2 = calculate_reward_v2(step1, step2, baseline, step_num=1, max_steps=10)
    print(f"   Step 2 보상: {reward2:.4f} (연속 개선 보너스 포함)")
    
    print("\n[SUCCESS] 테스트 완료!")

