def calculate_reward(baseline_cost: float, new_cost: float) -> float:
    """
    베이스라인 비용과 새로운 비용을 기반으로 보상을 계산합니다.
    보상은 '성능 향상 비율'로 정의됩니다.
    
    - 비용이 100에서 80으로 줄면, 보상은 (100 - 80) / 100 = 0.2
    - 비용이 100에서 120으로 늘면, 보상은 (100 - 120) / 100 = -0.2
    - 비용 변화가 없으면 보상은 0.0

    Args:
        baseline_cost (float): 행동을 취하기 전의 예상 비용 (e.g., last_ms).
        new_cost (float): 행동을 취한 후의 새로운 예상 비용.

    Returns:
        float: 계산된 보상 값.
    """
    if baseline_cost <= 0:
        # 베이스라인 비용이 0이거나 음수이면 보상 계산이 무의미하므로 0을 반환.
        return 0.0
    
    reward = (baseline_cost - new_cost) / baseline_cost
    return reward

if __name__ == '__main__':
    # 테스트 케이스
    cost_before = 150.5
    
    # 1. 성능이 향상된 경우
    cost_after_improved = 120.0
    reward_improved = calculate_reward(cost_before, cost_after_improved)
    print(f"Cost decreased: {cost_before:.2f} -> {cost_after_improved:.2f}. Reward: {reward_improved:.4f}")
    assert reward_improved > 0

    # 2. 성능이 저하된 경우
    cost_after_worsened = 180.0
    reward_worsened = calculate_reward(cost_before, cost_after_worsened)
    print(f"Cost increased: {cost_before:.2f} -> {cost_after_worsened:.2f}. Reward: {reward_worsened:.4f}")
    assert reward_worsened < 0

    # 3. 성능 변화가 없는 경우
    cost_after_same = 150.5
    reward_same = calculate_reward(cost_before, cost_after_same)
    print(f"Cost unchanged: {cost_before:.2f} -> {cost_after_same:.2f}. Reward: {reward_same:.4f}")
    assert reward_same == 0.0

    # 4. 베이스라인 비용이 0인 경우
    reward_zero_baseline = calculate_reward(0, 100)
    print(f"Baseline cost is 0. Reward: {reward_zero_baseline:.4f}")
    assert reward_zero_baseline == 0.0

    print("\nReward function test passed!")
