# -*- coding: utf-8 -*-
"""
DQN v4: Sim-to-Real 하이브리드 학습 파이프라인 (constants2.py 기반 30개 쿼리)
==============================================
Phase SimulXGB: XGB 시뮬레이션 환경에서 200K 타임스텝 고속 학습
Phase RealDB: 실제 DB 환경에서 10K 타임스텝 Fine-tuning

v4 개선사항:
- constants2.py의 30개 샘플 쿼리 사용
- 액션 호환성 체크 및 마스킹
- Invalid Action Masking Wrapper (DQN 유지)
- 베이스라인 시간 기반 Curriculum Learning
- v4 보상 함수 적용
"""

import os
import sys
import numpy as np
from datetime import datetime
import gymnasium as gym
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

# 프로젝트 루트 경로 설정
sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML'))
sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML', 'RLQO'))

from RLQO.DQN_v4.env.v4_sim_env import QueryPlanSimEnvV4
from RLQO.DQN_v4.env.v4_db_env import QueryPlanDBEnvV4
from RLQO.constants2 import SAMPLE_QUERIES

# ============================================================================
# Phase SimulXGB: 시뮬레이션 학습 설정
# ============================================================================
SIM_TIMESTEPS = 200_000  # 시뮬레이션 학습량 (빠름: 예상 1-2시간)
SIM_LEARNING_RATE = 1e-4
SIM_BUFFER_SIZE = 50_000
SIM_BATCH_SIZE = 128
SIM_EXPLORATION_FRACTION = 0.5  # 50%까지만 탐험
SIM_EXPLORATION_FINAL_EPS = 0.05

# ============================================================================
# Phase RealDB: 실제 DB Fine-tuning 설정
# ============================================================================
REAL_TIMESTEPS = 10_000  # 실제 DB 학습량 (느림: 예상 12-14시간)
REAL_LEARNING_RATE = 5e-5  # 낮은 학습률로 미세 조정
REAL_BUFFER_SIZE = 20_000
REAL_BATCH_SIZE = 64
REAL_EXPLORATION_FINAL_EPS = 0.02  # 더 적은 탐험

# ============================================================================
# 공통 설정
# ============================================================================
GAMMA = 0.99
TARGET_UPDATE_INTERVAL = 1000

# 경로 설정
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_DIR = "Apollo.ML/artifacts/RLQO/"

SIM_LOG_DIR = f"{BASE_DIR}logs/dqn_v4_sim/"
SIM_MODEL_PATH = f"{BASE_DIR}models/dqn_v4_sim.zip"
SIM_CHECKPOINT_DIR = f"{BASE_DIR}models/checkpoints/dqn_v4_sim/"

REAL_LOG_DIR = f"{BASE_DIR}logs/dqn_v4_real/"
REAL_MODEL_PATH = f"{BASE_DIR}models/dqn_v4_final.zip"
REAL_CHECKPOINT_DIR = f"{BASE_DIR}models/checkpoints/dqn_v4_real/"

TB_LOG_DIR = f"{BASE_DIR}tb/dqn_v4/"

# 디렉토리 생성
for directory in [SIM_LOG_DIR, SIM_CHECKPOINT_DIR, REAL_LOG_DIR, REAL_CHECKPOINT_DIR]:
    os.makedirs(directory, exist_ok=True)


class InvalidActionMaskingWrapper(gym.Env):
    """
    DQN용 Invalid Action Masking Wrapper
    호환되지 않는 액션 선택 시 즉시 페널티를 반환합니다.
    """
    
    def __init__(self, env):
        super().__init__()
        self.env = env
        self.action_space = env.action_space
        self.observation_space = env.observation_space
    
    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        return obs, info
    
    def step(self, action):
        # 액션 호환성 체크
        action_mask = self.env.get_action_mask()
        
        if action_mask[action] == 0:
            # 호환되지 않는 액션 선택 시 즉시 페널티 반환
            reward = -15.0
            terminated = True
            truncated = False
            
            info = {
                "action": self.env.actions[action]['name'],
                "metrics": self.env.current_metrics,
                "baseline_metrics": self.env.baseline_metrics,
                "safety_score": self.env.actions[action].get('safety_score', 1.0),
                "invalid_action": True
            }
            
            return self.env.current_obs, reward, terminated, truncated, info
        else:
            # 호환되는 액션은 정상 처리
            return self.env.step(action)
    
    def close(self):
        self.env.close()
    
    def get_action_mask(self):
        return self.env.get_action_mask()


def train_phase_simulxgb():
    """
    Phase SimulXGB: 시뮬레이션 환경에서 기본 정책 학습
    - 빠른 학습 속도 (실제 DB의 100배 이상)
    - 액션 호환성 체크 및 마스킹
    - 200K 타임스텝: 약 6,000 에피소드 (30개 쿼리 기준)
    """
    print("=" * 80)
    print(" Phase SimulXGB: 시뮬레이션 학습 시작")
    print("=" * 80)
    print(f"타임스텝: {SIM_TIMESTEPS:,}")
    print(f"예상 소요 시간: 1-2시간")
    print(f"쿼리 개수: {len(SAMPLE_QUERIES)} (constants2.py 기반)")
    print("-" * 80)
    
    # 1. 시뮬레이션 환경 생성
    print("\n[1/4] 시뮬레이션 환경 생성 중...")
    try:
        env = QueryPlanSimEnvV4(
            query_list=SAMPLE_QUERIES,
            max_steps=10,
            cache_path='Apollo.ML/artifacts/RLQO/cache/v4_plan_cache.pkl',  # v4 캐시 사용
            curriculum_mode=True,  # 베이스라인 시간 기반 Curriculum Learning
            verbose=False  # 학습 중에는 출력 최소화
        )
        
        # Invalid Action Masking Wrapper 적용
        env = InvalidActionMaskingWrapper(env)
        env = Monitor(env, SIM_LOG_DIR)
        print("[OK] 환경 생성 완료")
    except Exception as e:
        print(f"[ERROR] 환경 생성 실패: {e}")
        return None
    
    # 2. DQN 모델 생성
    print("\n[2/4] DQN 모델 생성 중...")
    try:
        model = DQN(
            "MlpPolicy",
            env,
            learning_rate=SIM_LEARNING_RATE,
            buffer_size=SIM_BUFFER_SIZE,
            batch_size=SIM_BATCH_SIZE,
            gamma=GAMMA,
            target_update_interval=TARGET_UPDATE_INTERVAL,
            exploration_fraction=SIM_EXPLORATION_FRACTION,
            exploration_final_eps=SIM_EXPLORATION_FINAL_EPS,
            verbose=1,
            tensorboard_log=TB_LOG_DIR
        )
        print("[OK] 모델 생성 완료")
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
            name_prefix="dqn_v4_sim"
        )
        
        eval_callback = EvalCallback(
            env,
            best_model_save_path=SIM_CHECKPOINT_DIR,
            log_path=SIM_LOG_DIR,
            eval_freq=10_000,
            deterministic=True,
            render=False
        )
        
        callbacks = [checkpoint_callback, eval_callback]
        print("[OK] 콜백 설정 완료")
    except Exception as e:
        print(f"[ERROR] 콜백 설정 실패: {e}")
        env.close()
        return None
    
    # 4. 학습 시작
    print("\n[4/4] 학습 시작...")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        model.learn(
            total_timesteps=SIM_TIMESTEPS,
            callback=callbacks,
            tb_log_name="dqn_v4_sim"
        )
        
        # 모델 저장
        model.save(SIM_MODEL_PATH)
        print(f"[OK] 학습 완료! 모델 저장: {SIM_MODEL_PATH}")
        
    except Exception as e:
        print(f"[ERROR] 학습 실패: {e}")
        env.close()
        return None
    
    env.close()
    return model


def train_phase_realdb_finetuning(pretrained_model=None, checkpoint_path=None):
    """
    Phase RealDB: 실제 DB 환경에서 Fine-tuning
    - 시뮬레이션 모델을 기반으로 실제 환경에 적응
    - 액션 호환성 체크 및 마스킹
    - 10K 타임스텝: 약 330 에피소드 (30개 쿼리 기준)
    
    Args:
        pretrained_model: 사전 훈련된 모델 (옵션)
        checkpoint_path: 이어서 훈련할 체크포인트 경로 (옵션)
    """
    print("=" * 80)
    print(" Phase RealDB: 실제 DB Fine-tuning 시작")
    print("=" * 80)
    print(f"타임스텝: {REAL_TIMESTEPS:,}")
    print(f"예상 소요 시간: 12-14시간")
    print(f"쿼리 개수: {len(SAMPLE_QUERIES)} (constants2.py 기반)")
    print("-" * 80)
    
    # 1. 실제 DB 환경 생성
    print("\n[1/4] 실제 DB 환경 생성 중...")
    try:
        env = QueryPlanDBEnvV4(
            query_list=SAMPLE_QUERIES,
            max_steps=10,
            curriculum_mode=True,  # 베이스라인 시간 기반 Curriculum Learning
            verbose=True  # 실시간 진행 상황 확인을 위해 verbose=True로 변경
        )
        
        # Invalid Action Masking Wrapper 적용
        env = InvalidActionMaskingWrapper(env)
        env = Monitor(env, REAL_LOG_DIR)
        print("[OK] 환경 생성 완료")
    except Exception as e:
        print(f"[ERROR] 환경 생성 실패: {e}")
        return None
    
    # 2. 모델 생성 또는 로드
    print("\n[2/4] 모델 생성/로드 중...")
    try:
        if checkpoint_path:
            # 체크포인트에서 이어서 훈련
            if os.path.exists(checkpoint_path):
                model = DQN.load(checkpoint_path, env=env)
                print(f"[OK] 체크포인트 로드 완료: {checkpoint_path}")
                print(f"[INFO] 현재 타임스텝: {model.num_timesteps}")
            else:
                print(f"[ERROR] 체크포인트 파일을 찾을 수 없습니다: {checkpoint_path}")
                env.close()
                return None
        elif pretrained_model:
            # 사전 훈련된 모델 사용
            model = pretrained_model
            model.set_env(env)
            print("[OK] 사전 훈련된 모델 로드 완료")
        else:
            # 시뮬레이션 모델 로드
            if os.path.exists(SIM_MODEL_PATH):
                model = DQN.load(SIM_MODEL_PATH, env=env)
                print("[OK] 시뮬레이션 모델 로드 완료")
            else:
                print("[WARN] 시뮬레이션 모델이 없습니다. 새로 생성합니다.")
                model = DQN(
                    "MlpPolicy",
                    env,
                    learning_rate=REAL_LEARNING_RATE,
                    buffer_size=REAL_BUFFER_SIZE,
                    batch_size=REAL_BATCH_SIZE,
                    gamma=GAMMA,
                    target_update_interval=TARGET_UPDATE_INTERVAL,
                    exploration_final_eps=REAL_EXPLORATION_FINAL_EPS,
                    verbose=1,
                    tensorboard_log=TB_LOG_DIR
                )
        
        # Fine-tuning을 위한 낮은 학습률 설정
        model.learning_rate = REAL_LEARNING_RATE
        print(f"[OK] 학습률 설정: {REAL_LEARNING_RATE}")
        
        # 체크포인트에서 로드한 경우가 아니면 타임스텝 카운터 리셋
        if not checkpoint_path:
            model.num_timesteps = 0
        
    except Exception as e:
        print(f"[ERROR] 모델 생성/로드 실패: {e}")
        env.close()
        return None
    
    # 3. 콜백 설정
    print("\n[3/4] 콜백 설정 중...")
    try:
        checkpoint_callback = CheckpointCallback(
            save_freq=500,  # 더 자주 저장하여 안정성 향상
            save_path=REAL_CHECKPOINT_DIR,
            name_prefix="dqn_v4_real"
        )
        
        # EvalCallback 제거 - 평가 과정에서 긴 지연 발생으로 인한 훈련 중단 방지
        # eval_callback = EvalCallback(
        #     env,
        #     best_model_save_path=REAL_CHECKPOINT_DIR,
        #     log_path=REAL_LOG_DIR,
        #     eval_freq=500,
        #     deterministic=True,
        #     render=False
        # )
        
        callbacks = [checkpoint_callback]  # EvalCallback 제거, CheckpointCallback만 사용
        print("[OK] 콜백 설정 완료 (EvalCallback 제거됨)")
    except Exception as e:
        print(f"[ERROR] 콜백 설정 실패: {e}")
        env.close()
        return None
    
    # 4. Fine-tuning 시작
    print("\n[4/4] Fine-tuning 시작...")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        model.learn(
            total_timesteps=REAL_TIMESTEPS,
            callback=callbacks,
            tb_log_name="dqn_v4_real",
            reset_num_timesteps=False  # 기존 타임스텝 유지
        )
        
        # 최종 모델 저장
        model.save(REAL_MODEL_PATH)
        print(f"[OK] Fine-tuning 완료! 모델 저장: {REAL_MODEL_PATH}")
        
    except Exception as e:
        print(f"[ERROR] Fine-tuning 실패: {e}")
        env.close()
        return None
    
    env.close()
    return model


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DQN v4 하이브리드 학습 파이프라인 (constants2.py 기반 30개 쿼리)')
    parser.add_argument('--phase', choices=['Simul', 'RealDB'], required=True,
                       help='학습 단계 선택')
    parser.add_argument('--skip-sim', action='store_true',
                       help='시뮬레이션 단계 건너뛰기 (RealDB만 실행)')
    parser.add_argument('--checkpoint', type=str, default=None,
                       help='이어서 훈련할 체크포인트 경로 (예: Apollo.ML/artifacts/RLQO/models/checkpoints/dqn_v4_real/dqn_v4_real_500_steps.zip)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" DQN v4 하이브리드 학습 파이프라인 (constants2.py 기반 30개 쿼리)")
    print("=" * 80)
    print(f"선택된 단계: {args.phase}")
    print(f"시뮬레이션 건너뛰기: {args.skip_sim}")
    if args.checkpoint:
        print(f"체크포인트: {args.checkpoint}")
    print("-" * 80)
    
    if args.phase == 'Simul':
        if args.skip_sim:
            print("[INFO] 시뮬레이션 단계를 건너뛰고 RealDB로 진행합니다.")
            model = train_phase_realdb_finetuning(checkpoint_path=args.checkpoint)
        else:
            model = train_phase_simulxgb()
            if model:
                print("\n[INFO] 시뮬레이션 학습 완료!")
                print("[INFO] RealDB 단계를 실행하려면 다음 명령어를 사용하세요:")
                print("python Apollo.ML/RLQO/DQN_v4/train/v4_train_dqn.py --phase RealDB")
    
    elif args.phase == 'RealDB':
        model = train_phase_realdb_finetuning(checkpoint_path=args.checkpoint)
    
    if model:
        print("\n" + "=" * 80)
        print(" 모든 학습 단계 완료!")
        print("=" * 80)
        print(f"최종 모델: {REAL_MODEL_PATH}")
        print(f"TensorBoard 로그: {TB_LOG_DIR}")
        print("-" * 80)
    else:
        print("\n[ERROR] 학습 실패!")


if __name__ == "__main__":
    main()
