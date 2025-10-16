# -*- coding: utf-8 -*-
"""
PPO v1 RealDB 학습 스크립트 (Conservative Mode OFF)

Action 8 과도 선택 문제 해결을 위한 개선:
1. Conservative Mode OFF → Action space 확장
2. Learning Rate 증가 (5e-5 → 1e-4)
3. Entropy Coefficient 증가 (0.005 → 0.02)
4. Training Steps 증가 (50K → 100K)
5. 안전 보너스 감소 (+2.0 → +0.5)
"""

import os
import sys
import numpy as np
from datetime import datetime
import gymnasium as gym
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.monitor import Monitor

# 프로젝트 루트 경로 설정
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)

from RLQO.PPO_v1.env.v1_db_env_noconservative import QueryPlanDBEnvV1NoConservative
from RLQO.constants import SAMPLE_QUERIES

# ============================================================================
# 하이퍼파라미터 (Conservative Mode OFF 최적화)
# ============================================================================
REAL_TIMESTEPS = 100_000  # 100K steps (50K → 100K, 더 긴 학습)
REAL_LEARNING_RATE = 1e-4  # 학습률 증가 (5e-5 → 1e-4)
REAL_N_STEPS = 512  # 배치 크기 증가 (256 → 512)
REAL_BATCH_SIZE = 64  # 미니배치 증가 (32 → 64)
REAL_N_EPOCHS = 10
REAL_GAMMA = 0.99
REAL_CLIP_RANGE = 0.2
REAL_ENT_COEF = 0.02  # 탐험 증가 (0.005 → 0.02, 4배)

# 경로 설정
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_DIR = "Apollo.ML/artifacts/RLQO/"

REAL_LOG_DIR = f"{BASE_DIR}logs/ppo_v1_realdb_nocons/"
REAL_MODEL_PATH = f"{BASE_DIR}models/ppo_v1_realdb_nocons_100k.zip"
REAL_CHECKPOINT_DIR = f"{BASE_DIR}models/checkpoints/ppo_v1_realdb_nocons/"

TB_LOG_DIR = f"{BASE_DIR}tb/ppo_v1_realdb_nocons/"

# 디렉토리 생성
for directory in [REAL_LOG_DIR, REAL_CHECKPOINT_DIR]:
    os.makedirs(directory, exist_ok=True)


def mask_fn(env):
    """
    PPO용 액션 마스크 함수
    
    Args:
        env: QueryPlanDBEnvV1NoConservative 환경
    
    Returns:
        action_mask: boolean array (True = valid action)
    """
    float_mask = env.get_action_mask()
    return float_mask.astype(bool)


def make_masked_env(verbose=False):
    """
    액션 마스킹이 적용된 RealDB 환경을 생성합니다 (Conservative Mode OFF).
    
    Args:
        verbose: 진행 상황 출력 여부
    
    Returns:
        env: ActionMasker로 래핑된 RealDB 환경
    """
    # No Conservative RealDB 환경 생성
    env = QueryPlanDBEnvV1NoConservative(
        query_list=SAMPLE_QUERIES,
        max_steps=10,
        conservative_mode=False,  # ★★ Conservative Mode OFF ★★
        curriculum_mode=True,
        verbose=verbose
    )
    
    # ActionMasker wrapper 적용
    env = ActionMasker(env, mask_fn)
    
    # Monitor wrapper 적용 (로깅)
    env = Monitor(env, REAL_LOG_DIR)
    
    return env


def train_realdb_noconservative():
    """
    RealDB 직접 학습 (Conservative Mode OFF)
    - Action space 확장
    - 더 높은 Learning Rate & Entropy
    - 더 긴 학습 (100K steps)
    """
    print("=" * 80)
    print(" PPO v1 RealDB 학습 (Conservative Mode OFF)")
    print("=" * 80)
    print(f"타임스탬프: {TIMESTAMP}")
    print(f"목적: Action 8 과도 선택 문제 해결")
    print("-" * 80)
    print("=" * 80)
    print(" PPO v1 RealDB 직접 학습 시작")
    print("=" * 80)
    print(f"알고리즘: MaskablePPO + Query Type-aware Rewards")
    print(f"환경: Real SQL Server DB")
    print(f"타임스텝: {REAL_TIMESTEPS:,}")
    print(f"예상 소요 시간: 16-24시간")
    print(f"쿼리 개수: {len(SAMPLE_QUERIES)}")
    print("-" * 80)
    print(f"핵심 개선사항 (vs 이전 버전):")
    print(f"  1. Conservative Mode: ON → OFF (Action space 확장)")
    print(f"  2. Learning Rate: 5e-5 → 1e-4 (2배 증가)")
    print(f"  3. Entropy Coef: 0.005 → 0.02 (4배 증가, 더 많은 탐험)")
    print(f"  4. N Steps: 256 → 512 (배치 크기 2배)")
    print(f"  5. Training Steps: 50K → 100K (2배 증가)")
    print(f"  6. 안전 보너스 감소: +2.0 → +0.5 (과도한 보수성 완화)")
    print("-" * 80)
    print(f"하이퍼파라미터:")
    print(f"  Learning Rate: {REAL_LEARNING_RATE}")
    print(f"  N Steps: {REAL_N_STEPS}")
    print(f"  Batch Size: {REAL_BATCH_SIZE}")
    print(f"  N Epochs: {REAL_N_EPOCHS}")
    print(f"  Gamma: {REAL_GAMMA}")
    print(f"  Clip Range: {REAL_CLIP_RANGE}")
    print(f"  Entropy Coef: {REAL_ENT_COEF}")
    print("-" * 80)
    print("[주의] 실제 DB 학습은 매우 느립니다!")
    print("    - DB 부하를 주의 깊게 모니터링하세요")
    print("    - 중간에 중단 가능 (체크포인트 자동 저장)")
    print("-" * 80)
    
    # 1. RealDB 환경 생성
    print("\n[1/4] RealDB 환경 생성 중 (Conservative Mode OFF)...")
    try:
        env = make_masked_env(verbose=True)
        print("[OK] 환경 생성 완료")
        print(f"     Action space: {env.action_space}")
        print(f"     Observation space: {env.observation_space}")
        
        # Action space 크기 확인
        base_env = env
        while hasattr(base_env, 'env'):
            base_env = base_env.env
        initial_mask = base_env.get_action_mask()
        available_actions = int(np.sum(initial_mask))
        print(f"     Available actions (초기): {available_actions}/{len(initial_mask)}")
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
            learning_rate=REAL_LEARNING_RATE,
            n_steps=REAL_N_STEPS,
            batch_size=REAL_BATCH_SIZE,
            n_epochs=REAL_N_EPOCHS,
            gamma=REAL_GAMMA,
            clip_range=REAL_CLIP_RANGE,
            ent_coef=REAL_ENT_COEF,
            tensorboard_log=TB_LOG_DIR,
            verbose=1,
            seed=42
        )
        print("[OK] 모델 생성 완료")
        print(f"     Policy: MlpPolicy")
        print(f"     Algorithm: MaskablePPO")
    except Exception as e:
        print(f"[ERROR] 모델 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 3. Callbacks 설정
    print("\n[3/4] Callbacks 설정 중...")
    checkpoint_callback = CheckpointCallback(
        save_freq=5000,  # 5K steps마다 저장
        save_path=REAL_CHECKPOINT_DIR,
        name_prefix="ppo_v1_realdb_nocons",
        verbose=1
    )
    print("[OK] Callbacks 설정 완료")
    print(f"     Checkpoint 주기: 5,000 steps")
    print(f"     저장 경로: {REAL_CHECKPOINT_DIR}")
    
    # 4. 학습 시작
    print("\n[4/4] 학습 시작...")
    print("=" * 80)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    print("TIP: TensorBoard로 실시간 모니터링:")
    print(f"     tensorboard --logdir {TB_LOG_DIR}")
    print("-" * 80)
    print("[중단] Ctrl+C로 중단 가능 (마지막 체크포인트부터 재개 가능)")
    print("-" * 80)
    
    try:
        model.learn(
            total_timesteps=REAL_TIMESTEPS,
            callback=checkpoint_callback,
            tb_log_name="ppo_v1_realdb_nocons",
            progress_bar=True
        )
        
        # 학습 완료 후 최종 모델 저장
        model.save(REAL_MODEL_PATH)
        print(f"\n[OK] 학습 완료! 모델 저장: {REAL_MODEL_PATH}")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n[중단] 사용자에 의해 학습이 중단되었습니다.")
        print(f"[INFO] 마지막 체크포인트: {REAL_CHECKPOINT_DIR}")
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
    print(" PPO v1 RealDB Training (No Conservative Mode)")
    print("=" * 80)
    
    model = train_realdb_noconservative()
    
    if model is not None:
        print("\n" + "=" * 80)
        print(" RealDB 학습 완료!")
        print("=" * 80)
        print(f"모델 저장: {REAL_MODEL_PATH}")
        print(f"TensorBoard 로그: {TB_LOG_DIR}")
        print(f"체크포인트: {REAL_CHECKPOINT_DIR}")
        print("-" * 80)
        print(f"다음 단계:")
        print(f"1. 모델 평가:")
        print(f"   python Apollo.ML/RLQO/PPO_v1/train/v1_evaluate.py \\")
        print(f"     --model {REAL_MODEL_PATH}")
        print(f"2. 이전 버전 (Conservative ON)과 비교")
        print("-" * 80)
    else:
        print("\n[ERROR] 학습 실패!")


if __name__ == "__main__":
    main()

