# -*- coding: utf-8 -*-
"""
PPO v2 Simulation 학습 스크립트

핵심 개선:
- State: 18차원 actionable features
- Reward: Log scale 정규화
- Action: Query-Specific (5-7개)
- 학습 속도: 30-60분 (vs PPO v1: 6-16시간)
"""

import os
import sys
from datetime import datetime
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor

# 프로젝트 루트 경로 설정
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)

from RLQO.PPO_v2.env.v2_sim_env import QueryPlanSimEnvV2
from RLQO.constants import SAMPLE_QUERIES

# ============================================================================
# 하이퍼파라미터 (Simulation 최적화)
# ============================================================================
SIM_TIMESTEPS = 100_000
SIM_LEARNING_RATE = 3e-4  # PPO v1: 1e-4 → v2: 3e-4 (더 빠른 학습)
SIM_N_STEPS = 2048
SIM_BATCH_SIZE = 64
SIM_N_EPOCHS = 10
SIM_GAMMA = 0.99
SIM_ENT_COEF = 0.01
SIM_CLIP_RANGE = 0.2

# 경로 설정
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_DIR = "Apollo.ML/artifacts/RLQO/"

SIM_LOG_DIR = f"{BASE_DIR}logs/ppo_v2_sim/"
SIM_MODEL_PATH = f"{BASE_DIR}models/ppo_v2_sim_100k.zip"
SIM_CHECKPOINT_DIR = f"{BASE_DIR}models/checkpoints/ppo_v2_sim/"

TB_LOG_DIR = f"{BASE_DIR}tb/ppo_v2_sim/"

# 디렉토리 생성
for directory in [SIM_LOG_DIR, SIM_CHECKPOINT_DIR]:
    os.makedirs(directory, exist_ok=True)


def mask_fn(env):
    """PPO용 액션 마스크 함수"""
    float_mask = env.get_action_mask()
    return float_mask.astype(bool)


def make_masked_env(verbose=False):
    """
    액션 마스킹이 적용된 Simulation 환경 생성
    
    Args:
        verbose: 진행 상황 출력 여부
    
    Returns:
        env: ActionMasker로 래핑된 Simulation 환경
    """
    env = QueryPlanSimEnvV2(
        query_list=SAMPLE_QUERIES,
        max_steps=10,
        curriculum_mode=True,  # Curriculum Learning 사용
        verbose=verbose
    )
    
    # ActionMasker wrapper 적용
    env = ActionMasker(env, mask_fn)
    
    # Monitor wrapper 적용 (로깅)
    env = Monitor(env, SIM_LOG_DIR)
    
    return env


def train_simulation():
    """
    Simulation 환경에서 PPO v2 학습
    
    목표:
    - 30-60분 내 100K steps 완료
    - Avg Speedup ≥ 1.15x
    - CTE 안정성 (악화 0-1건)
    """
    print("=" * 80)
    print(" PPO v2 Simulation 학습 시작")
    print("=" * 80)
    print(f"타임스탬프: {TIMESTAMP}")
    print(f"목적: Domain-Aware MDP로 성능 개선")
    print("-" * 80)
    print(" 핵심 개선사항")
    print("=" * 80)
    print(f"알고리즘: MaskablePPO")
    print(f"환경: XGBoost Simulation")
    print(f"타임스텝: {SIM_TIMESTEPS:,}")
    print(f"예상 소요 시간: 30-60분")
    print(f"쿼리 개수: {len(SAMPLE_QUERIES)}")
    print("-" * 80)
    print("개선사항:")
    print(f"  1. State: 79차원 → 18차원 actionable features (77% 축소)")
    print(f"  2. Reward: Log scale 정규화 [-1, +1]")
    print(f"  3. Action: Query-Specific 5-7개 (68% 축소)")
    print(f"  4. Learning Rate: 3e-4 (PPO v1: 1e-4)")
    print("-" * 80)
    print(f"하이퍼파라미터:")
    print(f"  Learning Rate: {SIM_LEARNING_RATE}")
    print(f"  N Steps: {SIM_N_STEPS}")
    print(f"  Batch Size: {SIM_BATCH_SIZE}")
    print(f"  N Epochs: {SIM_N_EPOCHS}")
    print(f"  Gamma: {SIM_GAMMA}")
    print(f"  Clip Range: {SIM_CLIP_RANGE}")
    print(f"  Entropy Coef: {SIM_ENT_COEF}")
    print("-" * 80)
    
    # 1. 환경 생성
    print("\n[1/4] Simulation 환경 생성 중...")
    try:
        env = make_masked_env(verbose=False)
        print("[OK] 환경 생성 완료")
        print(f"     Action space: {env.action_space}")
        print(f"     Observation space: {env.observation_space} (18차원)")
    except Exception as e:
        print(f"[ERROR] 환경 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 2. PPO 모델 생성
    print("\n[2/4] MaskablePPO 모델 생성 중...")
    try:
        model = MaskablePPO(
            policy="MlpPolicy",
            env=env,
            learning_rate=SIM_LEARNING_RATE,
            n_steps=SIM_N_STEPS,
            batch_size=SIM_BATCH_SIZE,
            n_epochs=SIM_N_EPOCHS,
            gamma=SIM_GAMMA,
            clip_range=SIM_CLIP_RANGE,
            ent_coef=SIM_ENT_COEF,
            policy_kwargs={
                'net_arch': [128, 128]  # 작은 네트워크 (18차원 input)
            },
            tensorboard_log=TB_LOG_DIR,
            verbose=1,
            seed=42
        )
        print("[OK] 모델 생성 완료")
        print(f"     Policy: MlpPolicy [128, 128]")
        print(f"     Algorithm: MaskablePPO")
    except Exception as e:
        print(f"[ERROR] 모델 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 3. Callbacks 설정
    print("\n[3/4] Callbacks 설정 중...")
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,  # 10K steps마다 저장
        save_path=SIM_CHECKPOINT_DIR,
        name_prefix="ppo_v2_sim",
        verbose=1
    )
    print("[OK] Callbacks 설정 완료")
    print(f"     Checkpoint 주기: 10,000 steps")
    print(f"     저장 경로: {SIM_CHECKPOINT_DIR}")
    
    # 4. 학습 시작
    print("\n[4/4] 학습 시작...")
    print("=" * 80)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    print("TIP: TensorBoard로 실시간 모니터링:")
    print(f"     tensorboard --logdir {TB_LOG_DIR}")
    print("-" * 80)
    print("중단: Ctrl+C (마지막 체크포인트부터 재개 가능)")
    print("-" * 80)
    
    try:
        model.learn(
            total_timesteps=SIM_TIMESTEPS,
            callback=checkpoint_callback,
            tb_log_name="ppo_v2_sim",
            progress_bar=True
        )
        
        # 학습 완료 후 최종 모델 저장
        model.save(SIM_MODEL_PATH)
        print(f"\n[OK] 학습 완료! 모델 저장: {SIM_MODEL_PATH}")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n[중단] 사용자에 의해 학습이 중단되었습니다.")
        print(f"[INFO] 마지막 체크포인트: {SIM_CHECKPOINT_DIR}")
        return None
    except Exception as e:
        print(f"\n[ERROR] 학습 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        env.close()
    
    return model


def main():
    """메인 실행 함수"""
    print("\n" + "=" * 80)
    print(" PPO v2: Domain-Aware MDP 재설계")
    print("=" * 80)
    print("State: 79차원 → 18차원 (77% 축소)")
    print("Reward: Log scale 정규화 [-1, +1]")
    print("Action: Query-Specific 5-7개 (68% 축소)")
    print("=" * 80)
    
    model = train_simulation()
    
    if model is not None:
        print("\n" + "=" * 80)
        print(" Simulation 학습 완료!")
        print("=" * 80)
        print(f"모델 저장: {SIM_MODEL_PATH}")
        print(f"TensorBoard 로그: {TB_LOG_DIR}")
        print(f"체크포인트: {SIM_CHECKPOINT_DIR}")
        print("-" * 80)
        print(f"다음 단계:")
        print(f"1. 모델 평가:")
        print(f"   python Apollo.ML/RLQO/PPO_v2/train/v2_evaluate.py \\")
        print(f"     --model {SIM_MODEL_PATH}")
        print(f"2. 성공 기준 (3개 중 2개 이상):")
        print(f"   - Avg Speedup ≥ 1.15x")
        print(f"   - CTE 안정성: 악화 0-1건")
        print(f"   - Action 다양성 > 40%")
        print("-" * 80)
    else:
        print("\n[ERROR] 학습 실패!")


if __name__ == "__main__":
    main()

