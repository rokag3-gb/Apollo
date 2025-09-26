import json
import os
import gymnasium as gym
import joblib
import numpy as np
from gymnasium import spaces

from RLQO.features.phase1_features import XGB_EXPECTED_FEATURES, extract_features
from RLQO.env.phase1_reward import calculate_reward


class QueryPlanEnv(gym.Env):
    """
    쿼리 계획 최적화를 위한 OpenAI Gym 스타일의 강화학습 환경.
    실제 DB를 호출하는 대신 XGBoost 모델을 사용하여 비용을 예측하는 오프라인 시뮬레이터.
    """
    metadata = {'render.modes': ['human']}

    def __init__(self, xgb_model_path='Apollo.ML/artifacts/model.joblib',
                 action_space_path='Apollo.ML/RLQO/configs/phase1_action_space.json',
                 max_steps=10):
        super(QueryPlanEnv, self).__init__()

        # 1. XGBoost 비용 예측 모델 로드
        if not os.path.exists(xgb_model_path):
            raise FileNotFoundError(f"XGBoost model not found at {xgb_model_path}. "
                                    "Please ensure the model file exists.")
        self.xgb_model = joblib.load(xgb_model_path)

        # 2. 행동 공간(Action Space) 정의
        if not os.path.exists(action_space_path):
            raise FileNotFoundError(f"Action space config not found at {action_space_path}.")
        with open(action_space_path, 'r') as f:
            self.actions = json.load(f)
        self.action_space = spaces.Discrete(len(self.actions))

        # 3. 상태 공간(Observation Space) 정의
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(XGB_EXPECTED_FEATURES,), dtype=np.float32
        )

        # 4. 에피소드 관련 변수 초기화
        self.max_steps = max_steps
        self.current_step = 0
        self.baseline_cost = 0.0
        self.current_plan = {}

    def _get_initial_plan(self) -> dict:
        """
        에피소드 시작 시 초기 실행 계획을 샘플링합니다.
        Phase 1에서는 무작위로 생성된 가상의 계획을 사용합니다.
        """
        plan = {
            'estimated_rows': self.np_random.integers(1000, 500000),
            'estimated_cost': self.np_random.integers(50, 800),
            'parallelism_degree': self.np_random.choice([0, 1]),
            'join_type_hash': self.np_random.choice([0, 1]),
            'join_type_loop': self.np_random.choice([0, 1]),
            'scan_type_index': self.np_random.choice([0, 1]),
            'scan_type_table': self.np_random.choice([0, 1]),
        }
        # 상호 배타적인 조건 처리 (예: 해시 조인과 루프 조인이 동시에 1일 수 없음)
        if plan['join_type_hash'] == 1:
            plan['join_type_loop'] = 0
            
        return plan

    def _predict_cost(self, plan_representation: dict) -> float:
        """
        주어진 실행 계획 표현에 대해 XGBoost 모델로 비용(last_ms)을 예측합니다.
        """
        features = extract_features(plan_representation)
        # XGBoost 모델은 2D 배열을 입력으로 기대하므로 reshape 합니다.
        predicted_cost = self.xgb_model.predict(features.reshape(1, -1))
        return float(predicted_cost[0])

    def _apply_action(self, action_id: int) -> dict:
        """
        현재 실행 계획에 선택된 행동을 적용하여 새로운 계획을 반환합니다.
        Phase 1에서는 계획의 특징을 직접 수정하는 방식으로 시뮬레이션합니다.
        """
        new_plan = self.current_plan.copy()
        action_name = self.actions[action_id]['name']

        if 'SET_MAXDOP' in action_name:
            dop = int(action_name.split('_')[-1])
            new_plan['parallelism_degree'] = 1 if dop > 1 else 0
        elif 'USE_HASH_JOIN' in action_name:
            new_plan['join_type_hash'] = 1
            new_plan['join_type_loop'] = 0
        elif 'USE_LOOP_JOIN' in action_name:
            new_plan['join_type_hash'] = 0
            new_plan['join_type_loop'] = 1
        
        return new_plan
        
    def reset(self, seed=None, options=None):
        """환경을 초기 상태로 리셋하고 초기 관측값을 반환합니다."""
        super().reset(seed=seed)  # Gymnasium API에 따라 seed 설정

        self.current_step = 0
        self.current_plan = self._get_initial_plan()
        self.baseline_cost = self._predict_cost(self.current_plan)
        
        initial_observation = extract_features(self.current_plan)
        info = {}  # Gymnasium API는 reset 시 info 딕셔너리 반환을 요구
        return initial_observation, info

    def step(self, action):
        """환경에서 한 스텝을 진행합니다."""
        if not self.action_space.contains(action):
            raise ValueError(f"Invalid action {action}")

        # 1. 행동 적용 및 새로운 계획 생성
        new_plan = self._apply_action(action)
        
        # 2. 새로운 계획의 비용 예측 및 보상 계산
        # 행동을 취하기 전의 비용은 현재 비용입니다.
        cost_before_action = self._predict_cost(self.current_plan)
        new_cost = self._predict_cost(new_plan)
        reward = calculate_reward(cost_before_action, new_cost)
        
        # 3. 상태 업데이트
        self.current_plan = new_plan
        next_observation = extract_features(self.current_plan)
        
        # 4. 에피소드 종료 조건 확인 (Gymnasium API 변경사항 적용)
        self.current_step += 1
        terminated = False  # 시간 초과 외의 종료 조건은 없으므로 False
        truncated = self.current_step >= self.max_steps
        
        # 추가 정보 (디버깅용)
        info = {
            'baseline_cost': self.baseline_cost,
            'cost_before_action': cost_before_action,
            'new_cost': new_cost,
            'action_name': self.actions[action]['name']
        }
        
        return next_observation, reward, terminated, truncated, info

    def render(self, mode='human'):
        """환경의 현재 상태를 시각화합니다 (간단한 텍스트 출력)."""
        print(f"Step: {self.current_step}")
        print(f"Current Plan Features: {extract_features(self.current_plan)}")
        print(f"Predicted Cost: {self._predict_cost(self.current_plan):.4f}")

if __name__ == '__main__':
    # 환경 테스트
    print("Initializing environment...")
    env = QueryPlanEnv()
    print("Environment initialized.")
    
    # reset 테스트
    obs, info = env.reset(seed=42)
    print(f"\nInitial observation received, shape: {obs.shape}")
    assert env.observation_space.contains(obs)
    assert isinstance(info, dict)
    
    # step 테스트
    random_action = env.action_space.sample()
    print(f"\nTaking a random action: {random_action} ({env.actions[random_action]['name']})")
    
    next_obs, reward, terminated, truncated, info = env.step(random_action)
    
    print(f"Next Observation Shape: {next_obs.shape}")
    print(f"Reward: {reward:.4f}")
    print(f"Terminated: {terminated}")
    print(f"Truncated: {truncated}")
    print(f"Info: {info}")
    
    assert env.observation_space.contains(next_obs)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)
    
    print("\nEnvironment step test passed!")

    # 전체 에피소드 실행 테스트
    print("\nRunning a full dummy episode...")
    obs, info = env.reset()
    total_reward = 0
    for i in range(env.max_steps + 2): # max_steps보다 길게 실행하여 done 확인
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        total_reward += reward
        print(f"Step {i+1}: action={info['action_name']}, reward={reward:.3f}, done={done}")
        if done:
            print("Episode finished.")
            break
    print(f"Total reward for the episode: {total_reward:.4f}")
    print("\nDummy episode run test passed!")
