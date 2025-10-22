# -*- coding: utf-8 -*-
"""
PPO v3 Simulation 학습 스크립트

개선사항:
- 30개 쿼리
- 44개 액션 (FAST 10개, MAXDOP 10개, ISOLATION 3개, 고급 DBA 10개)
- 18차원 actionable state
- Exploration 강화: entropy_coef 0.03
- Gradient clipping: max_grad_norm 0.5
- Learning rate scheduling
"""

import os
import sys
from datetime import datetime
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

from RLQO.PPO_v3.env.v3_sim_env import QueryPlanSimEnvPPOv3
from RLQO.PPO_v3.train.callbacks import EarlyStoppingCallback, ActionDiversityCallback

# constants2.py에서 30개 쿼리 로드
sys.path.insert(0, os.path.join(apollo_ml_dir, 'RLQO'))
from constants2 import SAMPLE_QUERIES

# ============================================================================
# 하이퍼파라미터 (Simulation - PPO v3)
# ============================================================================
SIM_TIMESTEPS = 100_000  # 100K steps
SIM_LEARNING_RATE = 3e-4
SIM_N_STEPS = 2048
SIM_BATCH_SIZE = 64
SIM_N_EPOCHS = 10
SIM_GAMMA = 0.99
SIM_ENT_COEF = 0.03  # Exploration 강화
SIM_CLIP_RANGE = 0.2
SIM_MAX_GRAD_NORM = 0.5  # ★ Gradient clipping 추가

# 경로 설정
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_DIR = "Apollo.ML/artifacts/RLQO/"

SIM_LOG_DIR = f"{BASE_DIR}logs/ppo_v3_sim/"
SIM_MODEL_PATH = f"{BASE_DIR}models/ppo_v3_sim_100k.zip"
SIM_CHECKPOINT_DIR = f"{BASE_DIR}models/checkpoints/ppo_v3_sim/"

TB_LOG_DIR = f"{BASE_DIR}tb/ppo_v3_sim/"

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
    env = QueryPlanSimEnvPPOv3(
        query_list=SAMPLE_QUERIES,
        max_steps=10,
        curriculum_mode=True,  # 베이스라인 시간 기반 Curriculum Learning
        verbose=verbose
    )
    
    env = ActionMasker(env, mask_fn)
    env = Monitor(env, SIM_LOG_DIR)
    
    return env


def train_simulation():
    """
    Simulation 환경에서 PPO v3 학습
    
    개선사항:
    - 30개 쿼리
    - 44개 액션
    - Gradient clipping
    - Learning rate scheduling
    """
    print("=" * 80)
    print(" PPO v3 Simulation 학습 시작")
    print("=" * 80)
    print(f"타임스탬프: {TIMESTAMP}")
    print(f"목적: 30개 쿼리 + 44개 액션으로 성능 개선")
    print(f"알고리즘: MaskablePPO + 18차원 Actionable State")
    print(f"환경: XGBoost Simulation")
    print(f"타임스텝: {SIM_TIMESTEPS:,}")
    print(f"쿼리 개수: {len(SAMPLE_QUERIES)}")
    print(f"예상 소요 시간: 30-45분")
    print("-" * 80)
    print(f"PPO v3 핵심 개선사항:")
    print(f"  1. 쿼리: 9개 → 30개")
    print(f"  2. 액션: 19개 → 44개 (FAST 10개, MAXDOP 10개, ISOLATION 3개, 고급 DBA 10개)")
    print(f"  3. State: 18차원 actionable features (유지)")
    print(f"  4. Reward: Log scale normalized [-1, +1] (유지)")
    print(f"  5. Gradient clipping: {SIM_MAX_GRAD_NORM}")
    print("-" * 80)
    print(f"하이퍼파라미터:")
    print(f"  Learning Rate: {SIM_LEARNING_RATE}")
    print(f"  N Steps: {SIM_N_STEPS}")
    print(f"  Batch Size: {SIM_BATCH_SIZE}")
    print(f"  N Epochs: {SIM_N_EPOCHS}")
    print(f"  Gamma: {SIM_GAMMA}")
    print(f"  Entropy Coef: {SIM_ENT_COEF}")
    print(f"  Clip Range: {SIM_CLIP_RANGE}")
    print(f"  Max Grad Norm: {SIM_MAX_GRAD_NORM}")
    print("=" * 80)
    
    # 1. 환경 생성
    print("\n[1/4] Simulation 환경 생성 중...")
    try:
        env = make_masked_env(verbose=False)
        print("[OK] 환경 생성 완료")
        print(f"     Action space: {env.action_space}")
        print(f"     Observation space: {env.observation_space}")
    except Exception as e:
        print(f"[ERROR] 환경 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 2. 모델 생성
    print("\n[2/4] MaskablePPO 모델 생성 중...")
    try:
        model = MaskablePPO(
            'MlpPolicy',
            env,
            learning_rate=SIM_LEARNING_RATE,
            n_steps=SIM_N_STEPS,
            batch_size=SIM_BATCH_SIZE,
            n_epochs=SIM_N_EPOCHS,
            gamma=SIM_GAMMA,
            ent_coef=SIM_ENT_COEF,
            clip_range=SIM_CLIP_RANGE,
            max_grad_norm=SIM_MAX_GRAD_NORM,  # ★ Gradient clipping
            tensorboard_log=TB_LOG_DIR,
            verbose=1
        )
        print("[OK] 모델 생성 완료")
        print(f"     Total parameters: {sum(p.numel() for p in model.policy.parameters()):,}")
    except Exception as e:
        print(f"[ERROR] 모델 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        env.close()
        return None
    
    # 3. 콜백 설정
    print("\n[3/4] 콜백 설정 중...")
    try:
        checkpoint_callback = CheckpointCallback(
            save_freq=3_000,  # 3K steps마다 저장 (5K → 3K)
            save_path=SIM_CHECKPOINT_DIR,
            name_prefix="ppo_v3_sim"
        )
        
        # Early stopping은 Simulation에서는 비활성화 (캐시 없으면 효과 제한적)
        # early_stopping_callback = EarlyStoppingCallback(
        #     patience=10,
        #     min_delta=0.01,
        #     verbose=True
        # )
        
        action_diversity_callback = ActionDiversityCallback(
            max_consecutive=10,
            verbose=False
        )
        
        callbacks = [checkpoint_callback, action_diversity_callback]
        print("[OK] 콜백 설정 완료")
        print(f"     Checkpoint frequency: 3,000 steps")
        print(f"     Early stopping: 비활성화 (Simulation은 전체 학습)")
        print(f"     Action diversity monitoring: ON")
    except Exception as e:
        print(f"[ERROR] 콜백 설정 실패: {e}")
        env.close()
        return None
    
    # 4. 학습 시작
    print("\n[4/4] 학습 시작...")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    print("TIP: TensorBoard로 실시간 모니터링:")
    print(f"     tensorboard --logdir {TB_LOG_DIR}")
    print("-" * 80)
    
    try:
        model.learn(
            total_timesteps=SIM_TIMESTEPS,
            callback=callbacks,
            tb_log_name="ppo_v3_sim"
        )
        
        # 모델 저장
        model.save(SIM_MODEL_PATH)
        print(f"\n[OK] 학습 완료! 모델 저장: {SIM_MODEL_PATH}")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n[INFO] 사용자에 의해 학습 중단됨")
        print(f"[INFO] 마지막 체크포인트: {SIM_CHECKPOINT_DIR}")
        
        partial_model_path = f"{BASE_DIR}models/ppo_v3_sim_partial.zip"
        model.save(partial_model_path)
        print(f"[INFO] 부분 학습 모델 저장: {partial_model_path}")
        
    except Exception as e:
        print(f"[ERROR] 학습 실패: {e}")
        import traceback
        traceback.print_exc()
        env.close()
        return None
    
    env.close()
    
    return model


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PPO v3 Simulation 학습')
    parser.add_argument('--test', action='store_true',
                       help='환경 테스트만 실행')
    
    args = parser.parse_args()
    
    if args.test:
        print("=" * 80)
        print(" PPO v3 Simulation Environment 테스트")
        print("=" * 80)
        
        try:
            env = make_masked_env(verbose=True)
            print("[OK] 환경 생성 완료")
            
            obs, info = env.reset()
            print(f"[OK] 리셋 완료: obs shape={obs.shape}")
            
            action_mask = env.get_action_mask()
            valid_actions = np.where(action_mask)[0]
            print(f"[OK] Action mask: {len(valid_actions)} valid actions")
            
            env.close()
            print("\n[SUCCESS] 환경 테스트 완료!")
            
        except Exception as e:
            print(f"\n[ERROR] 환경 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
        
        return
    
    model = train_simulation()
    
    if model:
        print("\n" + "=" * 80)
        print(" Simulation 학습 완료!")
        print("=" * 80)
        print(f"모델 경로: {SIM_MODEL_PATH}")
        print(f"TensorBoard 로그: {TB_LOG_DIR}")
        print(f"체크포인트: {SIM_CHECKPOINT_DIR}")
        print("-" * 80)
        print("\n다음 단계: RealDB Fine-tuning")
        print(f"   python Apollo.ML/RLQO/PPO_v3/train/v3_train_realdb.py")
        print("=" * 80)
    else:
        print("\n[ERROR] 학습 실패!")


if __name__ == "__main__":
    import numpy as np
    main()

