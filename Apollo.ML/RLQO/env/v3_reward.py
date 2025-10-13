# -*- coding: utf-8 -*-
"""
DQN v3: 개선된 보상 함수
v2의 보상 함수를 기반으로 다음 요소를 개선:
1. 가중치 조정: elapsed_time 0.7 + logical_reads 0.3 (CPU 제거)
2. 실패 임계값 완화: baseline_time * 10 → baseline_time * 50
3. 호환되지 않는 액션 선택 시 즉시 -15.0 페널티
4. 성공적인 개선 시 보너스 강화
"""

def calculate_reward_v3(
    metrics_before: dict,
    metrics_after: dict,
    baseline_metrics: dict,
    step_num: int = 0,
    max_steps: int = 10,
    weights: dict = None,
    action_safety_score: float = 1.0,
    invalid_action: bool = False
) -> float:
    """
    v3 보상 함수: elapsed_time 0.7 + logical_reads 0.3 가중치 적용
    
    Args:
        metrics_before: 이전 스텝의 메트릭
        metrics_after: 현재 스텝의 메트릭 (액션 적용 후)
        baseline_metrics: 베이스라인 메트릭 (힌트 없는 원본 쿼리)
        step_num: 현재 스텝 번호 (페널티 조정용)
        max_steps: 최대 스텝 수
        weights: 각 메트릭의 가중치
        action_safety_score: 액션의 안전성 점수 (0.0~1.0, 높을수록 안전)
        invalid_action: 호환되지 않는 액션 선택 여부
    
    Returns:
        계산된 보상 값
    """
    if weights is None:
        weights = {
            'time': 0.70,      # 실행 시간 (기존 0.50 → 0.70)
            'io': 0.30,        # 논리적 읽기 (기존 0.25 → 0.30)
            'cpu': 0.0,        # CPU 제거 (time과 중복성)
            'baseline': 0.0    # baseline 통합 (time에 포함)
        }
    
    # === 1. 호환되지 않는 액션 선택 시 즉시 페널티 ===
    if invalid_action:
        return -15.0
    
    # === 2. 메트릭 추출 ===
    time_before = metrics_before.get('elapsed_time_ms', 0)
    time_after = metrics_after.get('elapsed_time_ms', 0)
    time_baseline = baseline_metrics.get('elapsed_time_ms', time_before)
    
    io_before = metrics_before.get('logical_reads', 0)
    io_after = metrics_after.get('logical_reads', 0)
    io_baseline = baseline_metrics.get('logical_reads', io_before)
    
    cpu_before = metrics_before.get('cpu_time_ms', 0)
    cpu_after = metrics_after.get('cpu_time_ms', 0)
    cpu_baseline = baseline_metrics.get('cpu_time_ms', cpu_before)
    
    # === 3. 실패 처리 (임계값 완화: 10배 → 50배) ===
    if time_after == float('inf') or time_after > time_baseline * 50:
        # 점진적 페널티: 초기 스텝에서는 덜 가혹하게
        penalty_base = -10.0
        penalty_multiplier = 1 + (step_num / max_steps)
        return penalty_base * penalty_multiplier
    
    # === 4. 각 메트릭별 개선률 계산 ===
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
    
    # === 5. 기본 보상 계산 (가중 평균) ===
    base_reward = (
        weights['time'] * time_improvement +
        weights['io'] * io_improvement +
        weights['cpu'] * cpu_improvement +
        weights['baseline'] * baseline_improvement
    )
    
    # === 6. 비선형 보너스: 큰 개선에 추가 보상 (강화) ===
    bonus = 0.0
    
    # 베이스라인 대비 30% 이상 개선 시 보너스 (기존과 동일)
    if baseline_improvement > 0.3:
        bonus += 0.5 * baseline_improvement
    
    # 베이스라인 대비 50% 이상 개선 시 추가 보너스 (기존과 동일)
    if baseline_improvement > 0.5:
        bonus += 1.0 * baseline_improvement
    
    # 베이스라인 대비 80% 이상 개선 시 대형 보너스 (신규)
    if baseline_improvement > 0.8:
        bonus += 2.0 * baseline_improvement
    
    # 이전 스텝 대비 20% 이상 개선 시 작은 보너스 (연속 개선 장려)
    if time_improvement > 0.2:
        bonus += 0.2
    
    # 논리적 읽기 개선 보너스 (신규)
    if io_improvement > 0.3:
        bonus += 0.3 * io_improvement
    
    # === 7. 페널티: 성능 악화에 대한 패널티 ===
    penalty = 0.0
    
    # 베이스라인보다 50% 이상 느려진 경우 큰 페널티
    if baseline_improvement < -0.5:
        penalty = -2.0 * abs(baseline_improvement)
    # 베이스라인보다 20% 이상 느려진 경우 작은 페널티
    elif baseline_improvement < -0.2:
        penalty = -0.5 * abs(baseline_improvement)
    
    # 극심한 악화에 대한 추가 페널티 (기존과 동일)
    if baseline_improvement < -1.0:  # 100% 이상 악화 (2배 느려짐)
        penalty -= 5.0
    if baseline_improvement < -2.0:  # 200% 이상 악화 (3배 느려짐)
        penalty -= 7.0
    if baseline_improvement < -3.0:  # 300% 이상 악화 (4배 느려짐)
        penalty -= 8.0
    
    # 논리적 읽기 악화 페널티 (신규)
    if io_improvement < -0.5:
        penalty -= 1.0 * abs(io_improvement)
    
    # === 8. 안전성 페널티 (위험한 액션에 대한 페널티) ===
    # safety_score가 낮을수록 (위험할수록) 페널티 증가
    safety_penalty = (1.0 - action_safety_score) * 1.5
    penalty -= safety_penalty
    
    # === 9. 분산 페널티 (성능 불안정성) ===
    variance_penalty = 0.0
    if time_before > 0:
        # 이전 스텝 대비 급격한 변화 (10배 이상 차이)
        variance_ratio = abs(time_after - time_before) / (time_before + 1e-6)
        if variance_ratio > 10.0:
            variance_penalty = -1.0
        elif variance_ratio > 5.0:
            variance_penalty = -0.5
    
    # === 10. 점진적 개선 보너스 ===
    progress_bonus = 0.0
    if time_improvement > 0 and baseline_improvement > 0:
        # 이전 스텝보다 더 개선되었으면 보너스
        progress_bonus = 0.3
    
    # 논리적 읽기와 시간이 모두 개선된 경우 추가 보너스 (신규)
    if time_improvement > 0 and io_improvement > 0:
        progress_bonus += 0.2
    
    # === 11. 최종 보상 계산 ===
    total_reward = base_reward + bonus + penalty + variance_penalty + progress_bonus
    
    # 보상 범위 제한: [-15, +15]로 확대 (더 명확한 신호)
    total_reward = max(-15.0, min(total_reward, 15.0))
    
    return total_reward


def calculate_reward_simple_v3(metrics_before: dict, metrics_after: dict) -> float:
    """
    간단한 보상 함수 (v3 버전)
    elapsed_time 0.7 + logical_reads 0.3 가중치 적용
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
    print("=== DQN v3 보상 함수 테스트 ===\n")
    
    baseline = {'elapsed_time_ms': 100, 'logical_reads': 1000, 'cpu_time_ms': 70}
    before = baseline.copy()
    
    # 테스트 케이스 1: 큰 개선 (50% 감소)
    print("1. 큰 개선 (50% 시간 감소):")
    after_improved = {'elapsed_time_ms': 50, 'logical_reads': 500, 'cpu_time_ms': 35}
    reward = calculate_reward_v3(before, after_improved, baseline, step_num=0, max_steps=10)
    print(f"   보상: {reward:.4f} (예상: 양수 + 보너스)")
    
    # 테스트 케이스 2: 작은 개선 (10% 감소)
    print("\n2. 작은 개선 (10% 시간 감소):")
    after_small = {'elapsed_time_ms': 90, 'logical_reads': 900, 'cpu_time_ms': 63}
    reward = calculate_reward_v3(before, after_small, baseline, step_num=1, max_steps=10)
    print(f"   보상: {reward:.4f} (예상: 작은 양수)")
    
    # 테스트 케이스 3: 성능 악화 (50% 증가)
    print("\n3. 성능 악화 (50% 시간 증가):")
    after_worse = {'elapsed_time_ms': 150, 'logical_reads': 1500, 'cpu_time_ms': 105}
    reward = calculate_reward_v3(before, after_worse, baseline, step_num=2, max_steps=10)
    print(f"   보상: {reward:.4f} (예상: 음수 + 페널티)")
    
    # 테스트 케이스 4: 호환되지 않는 액션 선택
    print("\n4. 호환되지 않는 액션 선택:")
    reward = calculate_reward_v3(before, after_improved, baseline, invalid_action=True)
    print(f"   보상: {reward:.4f} (예상: -15.0)")
    
    # 테스트 케이스 5: 논리적 읽기 개선
    print("\n5. 논리적 읽기 개선 (시간은 동일):")
    after_io_improved = {'elapsed_time_ms': 100, 'logical_reads': 500, 'cpu_time_ms': 70}
    reward = calculate_reward_v3(before, after_io_improved, baseline, step_num=0, max_steps=10)
    print(f"   보상: {reward:.4f} (예상: 논리적 읽기 개선 보너스)")
    
    # 테스트 케이스 6: 대형 개선 (80% 감소)
    print("\n6. 대형 개선 (80% 시간 감소):")
    after_huge = {'elapsed_time_ms': 20, 'logical_reads': 200, 'cpu_time_ms': 14}
    reward = calculate_reward_v3(before, after_huge, baseline, step_num=0, max_steps=10)
    print(f"   보상: {reward:.4f} (예상: 대형 보너스)")
    
    print("\n[SUCCESS] v3 보상 함수 테스트 완료!")
