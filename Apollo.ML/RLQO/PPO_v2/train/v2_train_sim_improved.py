# -*- coding: utf-8 -*-
"""
PPO v2 Improved Simulation 학습 스크립트

개선사항:
- Exploration 강화: entropy_coef 0.01 → 0.03
- Early Stopping: Best 성능 도달 후 10 episodes 동안 개선 없으면 종료
- Action Diversity 모니터링: 같은 액션 5번 연속 선택 시 경고
"""

import os
import sys
from datetime import datetime
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import CheckpointCallback, CallbackList
from stable_baselines3.common.monitor import Monitor

# 프로젝트 루트 경로 설정
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)

from RLQO.PPO_v2.env.v2_sim_env import QueryPlanSimEnvV2
from RLQO.PPO_v2.train.callbacks import EarlyStoppingCallback, ActionDiversityCallback
from RLQO.constants import SAMPLE_QUERIES

# ============================================================================
# 하이퍼파라미터 (Improved 버전)
# ============================================================================
SIM_TIMESTEPS = 100_000
SIM_LEARNING_RATE = 3e-4
SIM_N_STEPS = 2048
SIM_BATCH_SIZE = 64
SIM_N_EPOCHS = 10
SIM_GAMMA = 0.99
SIM_ENT_COEF = 0.03  # ★ 0.01 → 0.03 (Exploration 강화)
SIM_CLIP_RANGE = 0.2

# 경로 설정
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_DIR = "Apollo.ML/artifacts/RLQO/"

SIM_LOG_DIR = f"{BASE_DIR}logs/ppo_v2_sim_improved/"
SIM_MODEL_PATH = f"{BASE_DIR}models/ppo_v2_sim_improved_100k.zip"
SIM_CHECKPOINT_DIR = f"{BASE_DIR}models/checkpoints/ppo_v2_sim_improved/"

TB_LOG_DIR = f"{BASE_DIR}tb/ppo_v2_sim_improved/"

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
        curriculum_mode=True,
        verbose=verbose
    )
    
    env = ActionMasker(env, mask_fn)
    env = Monitor(env, SIM_LOG_DIR)
    
    return env


def train_simulation_improved():
    """
    Improved Simulation 환경에서 PPO v2 학습
    
    개선사항:
    - Exploration 강화 (entropy_coef 3배 증가)
    - Early Stopping (10 episodes patience)
    - Action Diversity 모니터링
    """
    print("=" * 80)
    print(" PPO v2 Improved Simulation 학습 시작")
    print("=" * 80)
    print(f"타임스탬프: {TIMESTAMP}")
    print(f"목적: Exploration 강화 (Entropy Coef x3)로 성능 개선")
    print("-" * 80)
    print(" 핵심 개선사항")
    print("=" * 80)
    print(f"1. Exploration 강화: entropy_coef 0.01 → 0.03 (3배 증가)")
    print(f"2. 100K steps 완전 학습 (Early Stopping 비활성화)")
    print(f"3. Action Diversity: 같은 액션 5번 연속 선택 시 경고")
    print("-" * 80)
    print(f"알고리즘: MaskablePPO")
    print(f"환경: XGBoost Simulation (18차원 State)")
    print(f"타임스텝: {SIM_TIMESTEPS:,}")
    print(f"예상 소요 시간: 10-15분")
    print(f"쿼리 개수: {len(SAMPLE_QUERIES)}")
    print("-" * 80)
    print(f"하이퍼파라미터:")
    print(f"  Learning Rate: {SIM_LEARNING_RATE}")
    print(f"  N Steps: {SIM_N_STEPS}")
    print(f"  Batch Size: {SIM_BATCH_SIZE}")
    print(f"  N Epochs: {SIM_N_EPOCHS}")
    print(f"  Gamma: {SIM_GAMMA}")
    print(f"  Clip Range: {SIM_CLIP_RANGE}")
    print(f"  Entropy Coef: {SIM_ENT_COEF} (기존: 0.01)")
    print("-" * 80)
    print(f"목표:")
    print(f"  - Avg Speedup: 2.0x+ (기존 v2: 1.95x)")
    print(f"  - 악화 케이스: 1-2건 (기존 v2: 3건)")
    print(f"  - Action 다양성: 70%+ (기존 v2: 62.5%)")
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
            ent_coef=SIM_ENT_COEF,  # ★ Exploration 강화
            policy_kwargs={
                'net_arch': [128, 128]
            },
            tensorboard_log=TB_LOG_DIR,
            verbose=1,
            seed=42
        )
        print("[OK] 모델 생성 완료")
        print(f"     Policy: MlpPolicy [128, 128]")
        print(f"     Algorithm: MaskablePPO (Entropy Coef: {SIM_ENT_COEF})")
    except Exception as e:
        print(f"[ERROR] 모델 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 3. Callbacks 설정
    print("\n[3/4] Callbacks 설정 중...")
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path=SIM_CHECKPOINT_DIR,
        name_prefix="ppo_v2_sim_improved",
        verbose=1
    )
    
    # Early Stopping 비활성화: Simulation 환경에서 episode reward가 제대로 작동하지 않음
    # entropy_coef=0.03로 exploration 강화만 적용
    action_diversity_callback = ActionDiversityCallback(
        max_consecutive=5,  # 5번 연속 동일 액션 선택 시 경고
        verbose=False  # 출력 최소화
    )
    
    callback_list = CallbackList([
        checkpoint_callback,
        action_diversity_callback
    ])
    
    print("[OK] Callbacks 설정 완료")
    print(f"     1. Checkpoint: 10,000 steps마다 저장")
    print(f"     2. Action Diversity: 연속 5회 경고 (자동)")
    
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
            callback=callback_list,
            tb_log_name="ppo_v2_sim_improved",
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
    print(" PPO v2 Improved: Exploration 강화 (Entropy x3)")
    print("=" * 80)
    print("개선사항:")
    print("  1. Entropy Coef: 0.01 → 0.03 (3배, 더 많은 탐색)")
    print("  2. 100K steps 완전 학습 (Early Stopping 비활성화)")
    print("  3. Action Diversity 모니터링")
    print("=" * 80)
    print("예상 성과:")
    print("  - Avg Speedup: 2.0x+ (기존: 1.95x)")
    print("  - 악화 케이스: 1-2건 (기존: 3건)")
    print("  - Action 다양성: 70%+ (기존: 62.5%)")
    print("=" * 80)
    
    model = train_simulation_improved()
    
    if model is not None:
        print("\n" + "=" * 80)
        print(" Improved Simulation 학습 완료!")
        print("=" * 80)
        print(f"모델 저장: {SIM_MODEL_PATH}")
        print(f"TensorBoard 로그: {TB_LOG_DIR}")
        print(f"체크포인트: {SIM_CHECKPOINT_DIR}")
        print("-" * 80)
        print(f"다음 단계:")
        print(f"1. 모델 평가:")
        print(f"   python Apollo.ML/RLQO/PPO_v2/train/v2_evaluate.py \\")
        print(f"     --model {SIM_MODEL_PATH}")
        print(f"2. 성공 시 (Speedup ≥ 2.0x):")
        print(f"   → RealDB Fine-tuning 진행")
        print(f"3. 실패 시:")
        print(f"   → 하이퍼파라미터 추가 조정 또는 Ensemble 시도")
        print("-" * 80)
    else:
        print("\n[ERROR] 학습 실패!")


if __name__ == "__main__":
    main()

