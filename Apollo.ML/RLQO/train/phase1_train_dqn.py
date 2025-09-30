import os
import sys
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.monitor import Monitor

# 프로젝트 루트 경로 설정
# 스크립트가 C:\source\Apollo 와 같은 프로젝트 루트에서 실행된다고 가정하고,
# 'Apollo.ML' 폴더를 파이썬 경로에 추가하여 모듈 임포트 문제를 해결합니다.
sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML'))

from RLQO.env.phase2_db_env import QueryPlanDBEnv # [MOD] phase2_db_env로 변경
from RLQO.constants import SAMPLE_QUERIES # [MOD] constants에서 쿼리 목록 가져오기

# --- 설정 ---
# 학습 파라미터
TOTAL_TIMESTEPS = 5_000 # 총 학습 스텝 수 (300,000 -> 5,000, DB 연동으로 인한 속도 저하 감안)
LEARNING_RATE = 1e-4
BUFFER_SIZE = 5_000 # 버퍼 사이즈도 타임스텝에 맞춰 조정
BATCH_SIZE = 64 # 배치 사이즈 조정 (옵션)
GAMMA = 0.99
EXPLORATION_FRACTION = 0.8 # 탐험 비율을 늘려 다양한 경험을 쌓도록 조정
EXPLORATION_FINAL_EPS = 0.1

# 경로 설정 (프로젝트 루트 기준) - Phase 1.5
LOG_DIR = "Apollo.ML/artifacts/RLQO/logs/dqn_v1_5/"
MODEL_PATH = "Apollo.ML/artifacts/RLQO/models/dqn_v1_5.zip"
CHECKPOINT_DIR = "Apollo.ML/artifacts/RLQO/models/checkpoints/dqn_v1_5/"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)


def train_agent():
    """DQN 에이전트 학습을 위한 메인 함수"""
    print("--- Phase 1.5: DQN Agent Re-Training Start ---")

    # 1. 환경 생성 및 Monitor 래핑
    print("Creating DB environment...")
    try:
        # [MOD] QueryPlanDBEnv를 사용하도록 수정
        env = QueryPlanDBEnv(query_list=SAMPLE_QUERIES)
        env = Monitor(env, LOG_DIR)
        print("Environment created successfully.")
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
        learning_starts=100, # 학습 시작 시점 앞당기기
        batch_size=BATCH_SIZE,
        gamma=GAMMA,
        exploration_fraction=EXPLORATION_FRACTION,
        exploration_final_eps=EXPLORATION_FINAL_EPS,
        train_freq=(1, "step"),
        gradient_steps=1,
        target_update_interval=500, # 타겟 네트워크 업데이트 주기 조정
        verbose=1,
        tensorboard_log="Apollo.ML/artifacts/RLQO/tb/dqn_v1_5/"
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
    print("\n--- Phase 1.5: DQN Agent Re-Training Complete ---")


if __name__ == '__main__':
    train_agent()
