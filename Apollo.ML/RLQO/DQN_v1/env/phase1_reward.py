def calculate_reward(metrics_before: dict, metrics_after: dict, weights: dict = None) -> float:
    """
    이전과 이후의 실행 통계(metrics)를 기반으로 보상을 계산합니다.
    실행 시간과 논리적 읽기 감소를 모두 고려합니다.

    Args:
        metrics_before (dict): 행동 전 실행 통계. {'elapsed_time_ms': ..., 'logical_reads': ...}
        metrics_after (dict): 행동 후 실행 통계.
        weights (dict, optional): 각 지표의 가중치. Defaults to {'time': 0.7, 'io': 0.3}.

    Returns:
        float: 계산된 보상 값.
    """
    if weights is None:
        weights = {'time': 0.7, 'io': 0.3}

    # 이전 메트릭 값 가져오기
    time_before = metrics_before.get('elapsed_time_ms', 0)
    io_before = metrics_before.get('logical_reads', 0)

    # 이후 메트릭 값 가져오기
    time_after = metrics_after.get('elapsed_time_ms', 0)
    io_after = metrics_after.get('logical_reads', 0)

    # 시간 기반 보상 계산
    if time_before <= 0:
        reward_time = 0.0
    else:
        reward_time = (time_before - time_after) / time_before

    # IO 기반 보상 계산
    if io_before <= 0:
        reward_io = 0.0
    else:
        reward_io = (io_before - io_after) / io_before
        
    # 가중 합산
    total_reward = (weights['time'] * reward_time) + (weights['io'] * reward_io)
    
    # 보상의 범위를 [-1, 1] 정도로 유지하기 위해 클리핑 (선택적)
    return max(-1.0, min(total_reward, 1.0))


if __name__ == '__main__':
    # 테스트 케이스
    metrics_before = {'elapsed_time_ms': 100, 'logical_reads': 1000}

    # 1. 성능이 향상된 경우 (시간 20% 감소, IO 30% 감소)
    metrics_after_improved = {'elapsed_time_ms': 80, 'logical_reads': 700}
    reward_improved = calculate_reward(metrics_before, metrics_after_improved)
    # 예상 보상: (0.7 * 0.2) + (0.3 * 0.3) = 0.14 + 0.09 = 0.23
    print(f"Metrics improved. Reward: {reward_improved:.4f}")
    assert abs(reward_improved - 0.23) < 1e-5

    # 2. 성능이 저하된 경우 (시간 50% 증가, IO 20% 증가)
    metrics_after_worsened = {'elapsed_time_ms': 150, 'logical_reads': 1200}
    reward_worsened = calculate_reward(metrics_before, metrics_after_worsened)
    # 예상 보상: (0.7 * -0.5) + (0.3 * -0.2) = -0.35 - 0.06 = -0.41
    print(f"Metrics worsened. Reward: {reward_worsened:.4f}")
    assert abs(reward_worsened - (-0.41)) < 1e-5

    # 3. 일부는 개선, 일부는 저하된 경우 (시간 10% 감소, IO 20% 증가)
    metrics_after_mixed = {'elapsed_time_ms': 90, 'logical_reads': 1200}
    reward_mixed = calculate_reward(metrics_before, metrics_after_mixed)
    # 예상 보상: (0.7 * 0.1) + (0.3 * -0.2) = 0.07 - 0.06 = 0.01
    print(f"Metrics mixed. Reward: {reward_mixed:.4f}")
    assert abs(reward_mixed - 0.01) < 1e-5
    
    # 4. 베이스라인 값이 0인 경우
    metrics_before_zero = {'elapsed_time_ms': 0, 'logical_reads': 0}
    reward_zero = calculate_reward(metrics_before_zero, metrics_after_improved)
    print(f"Baseline is zero. Reward: {reward_zero:.4f}")
    assert reward_zero == 0.0

    print("\nNew reward function test passed!")
