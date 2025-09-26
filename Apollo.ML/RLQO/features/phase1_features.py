import numpy as np

# Phase 1에서 사용할 피처 목록 (예시)
# 실제로는 XML 실행 계획을 파싱하여 이 값들을 추출해야 합니다.
FEATURE_KEYS = [
    'estimated_rows',
    'estimated_cost',
    'parallelism_degree', # 0: serial, 1: parallel
    'join_type_hash',     # 1 if hash join exists, else 0
    'join_type_loop',     # 1 if loop join exists, else 0
    'scan_type_index',    # 1 if index scan exists, else 0
    'scan_type_table',    # 1 if table scan exists, else 0
]

# 미리 학습된 XGBoost 모델이 기대하는 피처의 수
XGB_EXPECTED_FEATURES = 79

def extract_features(plan_representation: dict) -> np.ndarray:
    """
    쿼리 실행 계획의 딕셔너리 표현을 받아 고정 크기의 numpy 배열 (상태 벡터)로 변환합니다.
    Phase 1에서는 정의된 7개의 피처를 추출하고 나머지는 0으로 채워 79개를 맞춥니다.

    Args:
        plan_representation (dict): 실행 계획의 주요 특징을 담은 딕셔너리.

    Returns:
        np.ndarray: 강화학습 에이전트를 위한 상태 벡터 (79개).
    """
    # 간단한 정규화를 위해 최대값 설정 (실제 데이터 분포에 맞게 조정 필요)
    max_values = {
        'estimated_rows': 1_000_000,
        'estimated_cost': 1000,
    }

    feature_vector = []
    for key in FEATURE_KEYS:
        value = plan_representation.get(key, 0)
        
        # 간단한 정규화
        if key in max_values:
            value = min(value / max_values[key], 1.0) # 1.0으로 클리핑

        feature_vector.append(value)

    # XGBoost 모델의 입력 크기에 맞게 0으로 패딩
    padding_size = XGB_EXPECTED_FEATURES - len(feature_vector)
    if padding_size > 0:
        padding = np.zeros(padding_size)
        feature_vector = np.concatenate([feature_vector, padding])
        
    return np.array(feature_vector, dtype=np.float32)

if __name__ == '__main__':
    # 테스트용 가상 실행 계획
    sample_plan = {
        'estimated_rows': 150000,
        'estimated_cost': 250,
        'parallelism_degree': 1,
        'join_type_hash': 1,
        'join_type_loop': 0,
        'scan_type_index': 1,
        'scan_type_table': 1,
    }

    features = extract_features(sample_plan)
    print(f"Sample Plan: {sample_plan}")
    print(f"Feature Vector (State): {features}")
    print(f"Feature Vector Shape: {features.shape}")

    assert features.shape == (XGB_EXPECTED_FEATURES,)
    assert features.dtype == np.float32
    assert np.all(features <= 1.0) and np.all(features >= 0.0)
    print("\nFeature extraction test passed!")
