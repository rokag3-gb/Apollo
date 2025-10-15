# -*- coding: utf-8 -*-
"""
PPO v1: XGBoost 시뮬레이션 환경에서 PPO 학습
==============================================
Phase Simul: XGB 시뮬레이션 환경에서 200K 타임스텝 학습

PPO 특징:
- On-policy 알고리즘
- Policy Gradient 기반
- Clipped Surrogate Objective로 안정적 학습
- Action Masking을 통한 호환성 보장

v1 개선사항:
- DQN v3의 검증된 환경과 보상 함수 재사용
- sb3-contrib의 MaskablePPO 사용
- 액션 호환성 체크 및 마스킹
- v3 보상 함수 적용
"""

import os
import sys
import numpy as np
from datetime import datetime
import gymnasium as gym
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

# 프로젝트 루트 경로 설정
sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML'))
sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML', 'RLQO'))

from RLQO.DQN_v3.env.v3_sim_env import QueryPlanSimEnvV3
from RLQO.constants import SAMPLE_QUERIES

# ============================================================================
# Phase Simul: 시뮬레이션 학습 설정
# ============================================================================
SIM_TIMESTEPS = 200_000  # 시뮬레이션 학습량 (빠름: 예상 1-2시간)
SIM_LEARNING_RATE = 3e-4  # PPO 표준 학습률
SIM_N_STEPS = 2048  # 각 업데이트 전에 수집할 스텝 수
SIM_BATCH_SIZE = 64  # 미니배치 크기
SIM_N_EPOCHS = 10  # 각 업데이트당 에폭 수
SIM_GAMMA = 0.99  # 할인율
SIM_CLIP_RANGE = 0.2  # PPO 클리핑 범위
SIM_ENT_COEF = 0.01  # 엔트로피 계수 (탐험 장려)

# 경로 설정
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_DIR = "Apollo.ML/artifacts/RLQO/"

SIM_LOG_DIR = f"{BASE_DIR}logs/ppo_v1_sim/"
SIM_MODEL_PATH = f"{BASE_DIR}models/ppo_v1_sim.zip"
SIM_CHECKPOINT_DIR = f"{BASE_DIR}models/checkpoints/ppo_v1_sim/"

TB_LOG_DIR = f"{BASE_DIR}tb/ppo_v1/"

# 디렉토리 생성
for directory in [SIM_LOG_DIR, SIM_CHECKPOINT_DIR]:
    os.makedirs(directory, exist_ok=True)


def mask_fn(env):
    """
    PPO용 액션 마스크 함수
    ActionMasker wrapper에서 사용됩니다.
    
    Args:
        env: QueryPlanSimEnvV3 환경
    
    Returns:
        action_mask: boolean array (True = valid action)
    """
    # get_action_mask()는 float32 array를 반환 (1.0 = valid, 0.0 = invalid)
    # ActionMasker는 boolean array를 기대하므로 변환
    float_mask = env.get_action_mask()
    return float_mask.astype(bool)


def make_masked_env():
    """
    액션 마스킹이 적용된 시뮬레이션 환경을 생성합니다.
    
    Returns:
        env: ActionMasker로 래핑된 환경
    """
    # 기본 시뮬레이션 환경 생성
    env = QueryPlanSimEnvV3(
        query_list=SAMPLE_QUERIES,
        max_steps=10,
        cache_path='Apollo.ML/artifacts/RLQO/cache/v2_plan_cache.pkl',
        curriculum_mode=True,  # 베이스라인 시간 기반 Curriculum Learning
        verbose=False  # 학습 중에는 출력 최소화
    )
    
    # ActionMasker wrapper 적용
    env = ActionMasker(env, mask_fn)
    
    # Monitor wrapper 적용 (로깅)
    env = Monitor(env, SIM_LOG_DIR)
    
    return env


def train_phase_simul():
    """
    Phase Simul: 시뮬레이션 환경에서 PPO 학습
    - 빠른 학습 속도 (실제 DB의 100배 이상)
    - 액션 호환성 체크 및 마스킹
    - 200K 타임스텝: 약 18,000 에피소드 (9개 쿼리 기준)
    """
    print("=" * 80)
    print(" Phase Simul: PPO 시뮬레이션 학습 시작")
    print("=" * 80)
    print(f"알고리즘: MaskablePPO (sb3-contrib)")
    print(f"타임스텝: {SIM_TIMESTEPS:,}")
    print(f"예상 소요 시간: 1-2시간")
    print(f"쿼리 개수: {len(SAMPLE_QUERIES)}")
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
    
    # 1. 시뮬레이션 환경 생성
    print("\n[1/4] 시뮬레이션 환경 생성 중...")
    try:
        env = make_masked_env()
        print("[OK] 환경 생성 완료")
        print(f"     Action space: {env.action_space}")
        print(f"     Observation space: {env.observation_space}")
    except Exception as e:
        print(f"[ERROR] 환경 생성 실패: {e}")
        return None
    
    # 2. MaskablePPO 모델 생성
    print("\n[2/4] MaskablePPO 모델 생성 중...")
    try:
        model = MaskablePPO(
            "MlpPolicy",
            env,
            learning_rate=SIM_LEARNING_RATE,
            n_steps=SIM_N_STEPS,
            batch_size=SIM_BATCH_SIZE,
            n_epochs=SIM_N_EPOCHS,
            gamma=SIM_GAMMA,
            clip_range=SIM_CLIP_RANGE,
            ent_coef=SIM_ENT_COEF,
            verbose=1,
            tensorboard_log=TB_LOG_DIR
        )
        print("[OK] 모델 생성 완료")
        print(f"     Policy: MlpPolicy")
        print(f"     Total parameters: {sum(p.numel() for p in model.policy.parameters()):,}")
    except Exception as e:
        print(f"[ERROR] 모델 생성 실패: {e}")
        env.close()
        return None
    
    # 3. 콜백 설정
    print("\n[3/4] 콜백 설정 중...")
    try:
        checkpoint_callback = CheckpointCallback(
            save_freq=20_000,
            save_path=SIM_CHECKPOINT_DIR,
            name_prefix="ppo_v1_sim"
        )
        
        # Eval 환경 생성 (평가용)
        eval_env = make_masked_env()
        
        eval_callback = EvalCallback(
            eval_env,
            best_model_save_path=SIM_CHECKPOINT_DIR,
            log_path=SIM_LOG_DIR,
            eval_freq=10_000,
            deterministic=True,
            render=False
        )
        
        callbacks = [checkpoint_callback, eval_callback]
        print("[OK] 콜백 설정 완료")
        print(f"     Checkpoint frequency: 20,000 steps")
        print(f"     Evaluation frequency: 10,000 steps")
    except Exception as e:
        print(f"[ERROR] 콜백 설정 실패: {e}")
        env.close()
        return None
    
    # 4. 학습 시작
    print("\n[4/4] 학습 시작...")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    
    try:
        model.learn(
            total_timesteps=SIM_TIMESTEPS,
            callback=callbacks,
            tb_log_name="ppo_v1_sim"
        )
        
        # 모델 저장
        model.save(SIM_MODEL_PATH)
        print(f"\n[OK] 학습 완료! 모델 저장: {SIM_MODEL_PATH}")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"[ERROR] 학습 실패: {e}")
        env.close()
        if 'eval_env' in locals():
            eval_env.close()
        return None
    
    env.close()
    if 'eval_env' in locals():
        eval_env.close()
    
    return model


def test_environment():
    """환경 테스트 함수"""
    print("=" * 80)
    print(" PPO v1 환경 테스트")
    print("=" * 80)
    
    try:
        # 환경 생성
        print("\n[1/3] 환경 생성 중...")
        env = make_masked_env()
        print("[OK] 환경 생성 완료")
        print(f"     Action space: {env.action_space}")
        print(f"     Observation space: {env.observation_space}")
        
        # 리셋 테스트
        print("\n[2/3] 리셋 테스트 중...")
        obs, info = env.reset()
        print("[OK] 리셋 완료")
        print(f"     Observation shape: {obs.shape}")
        
        # 액션 마스크 테스트
        print("\n[3/3] 액션 마스크 테스트 중...")
        # ActionMasker는 action_mask()를 자동으로 호출
        # 내부 환경의 get_action_mask()로 직접 접근
        if hasattr(env, 'env'):
            # Monitor -> ActionMasker -> QueryPlanSimEnvV3
            base_env = env.env
            if hasattr(base_env, 'env'):
                base_env = base_env.env
            
            if hasattr(base_env, 'get_action_mask'):
                action_mask = base_env.get_action_mask()
                compatible_count = int(np.sum(action_mask))
                print(f"[OK] 액션 마스크 확인 완료")
                print(f"     Compatible actions: {compatible_count}/{len(action_mask)}")
        
        # 랜덤 액션 테스트
        action = env.action_space.sample()
        print(f"\n랜덤 액션 테스트: {action}")
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"[OK] 스텝 완료")
        print(f"     Reward: {reward:.4f}")
        print(f"     Terminated: {terminated}")
        print(f"     Truncated: {truncated}")
        
        env.close()
        
        print("\n" + "=" * 80)
        print(" 환경 테스트 완료!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] 환경 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PPO v1 시뮬레이션 학습')
    parser.add_argument('--test', action='store_true',
                       help='환경 테스트만 실행')
    
    args = parser.parse_args()
    
    if args.test:
        test_environment()
        return
    
    print("=" * 80)
    print(" PPO v1 시뮬레이션 학습 파이프라인")
    print("=" * 80)
    print(f"타임스탬프: {TIMESTAMP}")
    print("-" * 80)
    
    model = train_phase_simul()
    
    if model:
        print("\n" + "=" * 80)
        print(" 학습 완료!")
        print("=" * 80)
        print(f"모델 경로: {SIM_MODEL_PATH}")
        print(f"TensorBoard 로그: {TB_LOG_DIR}")
        print(f"체크포인트: {SIM_CHECKPOINT_DIR}")
        print("-" * 80)
        print("\n다음 단계:")
        print("1. TensorBoard로 학습 진행 확인:")
        print(f"   tensorboard --logdir {TB_LOG_DIR}")
        print("\n2. 모델 평가:")
        print(f"   python Apollo.ML/RLQO/PPO_v1/train/v1_evaluate.py --model {SIM_MODEL_PATH}")
        print("-" * 80)
    else:
        print("\n[ERROR] 학습 실패!")


if __name__ == "__main__":
    main()

