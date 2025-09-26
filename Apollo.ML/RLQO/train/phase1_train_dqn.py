import os
import sys
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.monitor import Monitor

# 프로젝트 루트 경로 설정
# 스크립트가 C:\source\Apollo 와 같은 프로젝트 루트에서 실행된다고 가정하고,
# 'Apollo.ML' 폴더를 파이썬 경로에 추가하여 모듈 임포트 문제를 해결합니다.
sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML'))

from RLQO.env.phase1_query_plan_env import QueryPlanEnv

# --- 설정 ---
# 학습 파라미터
TOTAL_TIMESTEPS = 200_000 # 총 학습 스텝 수
LEARNING_RATE = 1e-4
BUFFER_SIZE = 100_000
BATCH_SIZE = 128
GAMMA = 0.99
EXPLORATION_FRACTION = 0.5
EXPLORATION_FINAL_EPS = 0.05

# 경로 설정 (프로젝트 루트 기준)
LOG_DIR = "Apollo.ML/RLQO/logs/dqn_v1/"
MODEL_PATH = "Apollo.ML/RLQO/models/dqn_v1.zip"
CHECKPOINT_DIR = "Apollo.ML/RLQO/models/checkpoints/dqn_v1/"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)


def train_agent():
    """DQN 에이전트 학습을 위한 메인 함수"""
    print("--- Phase 1: DQN Agent Training Start ---")

    # 1. 환경 생성 및 Monitor 래핑
    print("Creating environment...")
    try:
        # 프로젝트 루트를 기준으로 상대 경로를 사용하도록 수정
        xgb_model_path_from_root = 'Apollo.ML/artifacts/model.joblib'
        action_space_path_from_root = 'Apollo.ML/RLQO/configs/phase1_action_space.json'
        
        env = QueryPlanEnv(
            xgb_model_path=xgb_model_path_from_root,
            action_space_path=action_space_path_from_root
        )
        env = Monitor(env, LOG_DIR)
        print("Environment created successfully.")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please check if 'Apollo.ML/artifacts/model.joblib' and 'Apollo.ML/RLQO/configs/phase1_action_space.json' exist from the project root.")
        return
    except Exception as e:
        print(f"An unexpected error occurred while creating the environment: {e}")
        return

    # 2. 체크포인트 콜백 설정 (일정 스텝마다 모델 저장)
    checkpoint_callback = CheckpointCallback(
        save_freq=10_000,
        save_path=CHECKPOINT_DIR,
        name_prefix="dqn_model"
    )

    # 3. DQN 모델 생성
    print("Creating DQN model...")
    model = DQN(
        "MlpPolicy",
        env,
        learning_rate=LEARNING_RATE,
        buffer_size=BUFFER_SIZE,
        learning_starts=1000,
        batch_size=BATCH_SIZE,
        gamma=GAMMA,
        exploration_fraction=EXPLORATION_FRACTION,
        exploration_final_eps=EXPLORATION_FINAL_EPS,
        train_freq=(1, "step"),
        gradient_steps=1,
        target_update_interval=1000,
        verbose=1,
        tensorboard_log="Apollo.ML/RLQO/tb/dqn_v1/"
    )
    print("Model created.")
    print("Policy Architecture:", model.policy)


    # 4. 모델 학습 시작
    print(f"\nStarting training for {TOTAL_TIMESTEPS} timesteps...")
    try:
        model.learn(
            total_timesteps=TOTAL_TIMESTEPS,
            callback=checkpoint_callback,
            progress_bar=True
        )
        print("\nTraining finished.")
    except Exception as e:
        print(f"\nAn error occurred during training: {e}")
        return

    # 5. 최종 모델 저장
    print(f"Saving final model to {MODEL_PATH}")
    model.save(MODEL_PATH)
    print("Model saved successfully.")
    print("\n--- Phase 1: DQN Agent Training Complete ---")


if __name__ == '__main__':
    train_agent()
