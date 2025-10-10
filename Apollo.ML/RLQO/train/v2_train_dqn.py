# -*- coding: utf-8 -*-
"""
DQN v2: Sim-to-Real 하이브리드 학습 파이프라인
==============================================
Phase A: XGB 시뮬레이션 환경에서 200K 타임스텝 고속 학습
Phase B: 실제 DB 환경에서 10K 타임스텝 Fine-tuning

전략:
- 시뮬레이션으로 안전하고 빠르게 기본 정책 학습
- 실제 환경에서 시뮬레이션 오차 보정 및 실전 최적화
"""

import os
import sys
from datetime import datetime
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor

# 프로젝트 루트 경로 설정
sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML'))

from RLQO.env.v2_sim_env import QueryPlanSimEnv
from RLQO.env.v2_db_env import QueryPlanDBEnvV2
from RLQO.constants import SAMPLE_QUERIES

# ============================================================================
# Phase A: 시뮬레이션 학습 설정
# ============================================================================
SIM_TIMESTEPS = 200_000  # 시뮬레이션 학습량 (빠름: 예상 1-2시간)
SIM_LEARNING_RATE = 1e-4
SIM_BUFFER_SIZE = 50_000
SIM_BATCH_SIZE = 128
SIM_EXPLORATION_FRACTION = 0.5  # 50%까지만 탐험
SIM_EXPLORATION_FINAL_EPS = 0.05

# ============================================================================
# Phase B: 실제 DB Fine-tuning 설정
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

SIM_LOG_DIR = f"{BASE_DIR}logs/dqn_v2_sim/"
SIM_MODEL_PATH = f"{BASE_DIR}models/dqn_v2_sim.zip"
SIM_CHECKPOINT_DIR = f"{BASE_DIR}models/checkpoints/dqn_v2_sim/"

REAL_LOG_DIR = f"{BASE_DIR}logs/dqn_v2_real/"
REAL_MODEL_PATH = f"{BASE_DIR}models/dqn_v2_final.zip"
REAL_CHECKPOINT_DIR = f"{BASE_DIR}models/checkpoints/dqn_v2_real/"

TB_LOG_DIR = f"{BASE_DIR}tb/dqn_v2/"

# 디렉토리 생성
for directory in [SIM_LOG_DIR, SIM_CHECKPOINT_DIR, REAL_LOG_DIR, REAL_CHECKPOINT_DIR]:
    os.makedirs(directory, exist_ok=True)


def train_phase_a_simulation():
    """
    Phase A: 시뮬레이션 환경에서 기본 정책 학습
    - 빠른 학습 속도 (실제 DB의 100배 이상)
    - 안전한 탐험 (잘못된 쿼리도 시스템 영향 없음)
    - 200K 타임스텝: 약 18,000 에피소드 (11개 쿼리 기준)
    """
    print("=" * 80)
    print(" Phase A: 시뮬레이션 학습 시작")
    print("=" * 80)
    print(f"타임스텝: {SIM_TIMESTEPS:,}")
    print(f"예상 소요 시간: 1-2시간")
    print(f"쿼리 개수: {len(SAMPLE_QUERIES)}")
    print("-" * 80)
    
    # 1. 시뮬레이션 환경 생성
    print("\n[1/4] 시뮬레이션 환경 생성 중...")
    try:
        env = QueryPlanSimEnv(
            query_list=SAMPLE_QUERIES,
            xgb_model_path='Apollo.ML/artifacts/model.joblib',
            max_steps=10,
            verbose=False  # 학습 중에는 출력 최소화
        )
        env = Monitor(env, SIM_LOG_DIR)
        print("[OK] 환경 생성 완료")
    except Exception as e:
        print(f"[ERROR] 환경 생성 실패: {e}")
        return None
    
    # 2. 체크포인트 콜백 설정
    print("\n[2/4] 콜백 설정 중...")
    checkpoint_callback = CheckpointCallback(
        save_freq=20_000,  # 20K마다 저장
        save_path=SIM_CHECKPOINT_DIR,
        name_prefix="dqn_v2_sim"
    )
    print("[OK] 콜백 설정 완료")
    
    # 3. DQN 모델 생성
    print("\n[3/4] DQN 모델 생성 중...")
    model = DQN(
        "MlpPolicy",
        env,
        learning_rate=SIM_LEARNING_RATE,
        buffer_size=SIM_BUFFER_SIZE,
        learning_starts=1000,  # 충분한 경험 수집 후 학습 시작
        batch_size=SIM_BATCH_SIZE,
        gamma=GAMMA,
        exploration_fraction=SIM_EXPLORATION_FRACTION,
        exploration_final_eps=SIM_EXPLORATION_FINAL_EPS,
        train_freq=(1, "step"),
        gradient_steps=1,
        target_update_interval=TARGET_UPDATE_INTERVAL,
        verbose=1,
        tensorboard_log=TB_LOG_DIR
    )
    print("[OK] 모델 생성 완료")
    print(f"  Policy: {model.policy}")
    print(f"  Learning Rate: {SIM_LEARNING_RATE}")
    print(f"  Buffer Size: {SIM_BUFFER_SIZE:,}")
    
    # 4. 모델 학습
    print("\n[4/4] 학습 시작...")
    print("-" * 80)
    try:
        model.learn(
            total_timesteps=SIM_TIMESTEPS,
            callback=checkpoint_callback,
            progress_bar=True,
            log_interval=100
        )
        print("\n[OK] 학습 완료")
    except Exception as e:
        print(f"\n[ERROR] 학습 중 오류 발생: {e}")
        return None
    
    # 5. 모델 저장
    print(f"\n[5/5] 모델 저장 중: {SIM_MODEL_PATH}")
    model.save(SIM_MODEL_PATH)
    print("[OK] 모델 저장 완료")
    
    env.close()
    
    print("\n" + "=" * 80)
    print(" Phase A: 시뮬레이션 학습 완료!")
    print("=" * 80)
    
    return model


def train_phase_b_finetuning():
    """
    Phase B: 실제 DB 환경에서 Fine-tuning
    - Phase A에서 학습한 모델 로드
    - 실제 DB에서 10K 타임스텝 추가 학습
    - 시뮬레이션 오차 보정 및 실전 최적화
    """
    print("\n\n")
    print("=" * 80)
    print(" Phase B: 실제 DB Fine-tuning 시작")
    print("=" * 80)
    print(f"타임스텝: {REAL_TIMESTEPS:,}")
    print(f"예상 소요 시간: 2-3시간")
    print("-" * 80)
    
    # 1. Phase A 모델 로드
    print("\n[1/5] Phase A 모델 로드 중...")
    if not os.path.exists(SIM_MODEL_PATH):
        print(f"[ERROR] Phase A 모델을 찾을 수 없습니다: {SIM_MODEL_PATH}")
        print("  먼저 Phase A를 완료하세요.")
        return None
    
    # 2. 실제 DB 환경 생성 (v2: 확장된 액션 공간, 안전성 점수)
    print("\n[2/5] 실제 DB 환경 생성 중...")
    try:
        env = QueryPlanDBEnvV2(
            query_list=SAMPLE_QUERIES,
            max_steps=10,
            curriculum_mode=True,  # Curriculum Learning 활성화 (쉬운 쿼리부터 학습)
            verbose=True
        )
        env = Monitor(env, REAL_LOG_DIR)
        print("[OK] 환경 생성 완료 (v2.1: 15개 액션)")
    except Exception as e:
        print(f"[ERROR] 환경 생성 실패: {e}")
        print("  DB 연결을 확인하세요.")
        return None
    
    # 3. Phase A 모델 로드 및 환경 연결
    print("\n[3/5] 모델 로드 및 재설정 중...")
    try:
        model = DQN.load(SIM_MODEL_PATH, env=env)
        print("[OK] 모델 로드 완료")
        
        # Fine-tuning을 위한 하이퍼파라미터 조정
        model.learning_rate = REAL_LEARNING_RATE
        model.exploration_final_eps = REAL_EXPLORATION_FINAL_EPS
        # Replay Buffer는 유지 (시뮬레이션 경험 활용)
        
        print(f"  Learning Rate: {REAL_LEARNING_RATE} (낮춤)")
        print(f"  Exploration Eps: {REAL_EXPLORATION_FINAL_EPS} (낮춤)")
        print(f"  Replay Buffer: 유지 (시뮬레이션 경험 활용)")
    except Exception as e:
        print(f"[ERROR] 모델 로드 실패: {e}")
        return None
    
    # 4. 체크포인트 콜백
    print("\n[4/5] 콜백 설정 중...")
    checkpoint_callback = CheckpointCallback(
        save_freq=2_000,  # 2K마다 저장
        save_path=REAL_CHECKPOINT_DIR,
        name_prefix="dqn_v2_real"
    )
    print("[OK] 콜백 설정 완료")
    
    # 5. Fine-tuning 학습
    print("\n[5/5] Fine-tuning 시작...")
    print("-" * 80)
    try:
        model.learn(
            total_timesteps=REAL_TIMESTEPS,
            callback=checkpoint_callback,
            progress_bar=True,
            log_interval=50,
            reset_num_timesteps=False  # 타임스텝 카운트 이어서 (200K부터 시작)
        )
        print("\n[OK] Fine-tuning 완료")
    except Exception as e:
        print(f"\n[ERROR] Fine-tuning 중 오류 발생: {e}")
        return None
    
    # 6. 최종 모델 저장
    print(f"\n[6/6] 최종 모델 저장 중: {REAL_MODEL_PATH}")
    model.save(REAL_MODEL_PATH)
    print("[OK] 최종 모델 저장 완료")
    
    env.close()
    
    print("\n" + "=" * 80)
    print(" Phase B: Fine-tuning 완료!")
    print("=" * 80)
    
    return model


def train_dqn_v2_full():
    """
    DQN v2 전체 학습 파이프라인 실행
    Phase A (Sim) + Phase B (Real)
    """
    print("\n")
    print("=" * 80)
    print(" " * 20 + "DQN v2 하이브리드 학습 시작")
    print("=" * 80)
    print(f"\n시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 예상 시간: 3-5시간")
    print(f"총 타임스텝: {SIM_TIMESTEPS + REAL_TIMESTEPS:,}")
    print("\n")
    
    start_time = datetime.now()
    
    # Phase A: 시뮬레이션 학습
    phase_a_start = datetime.now()
    model_sim = train_phase_a_simulation()
    phase_a_duration = (datetime.now() - phase_a_start).total_seconds() / 60
    
    if model_sim is None:
        print("\n[FAILED] Phase A 실패. 학습을 중단합니다.")
        return
    
    print(f"\n[SUCCESS] Phase A 완료 (소요 시간: {phase_a_duration:.1f}분)")
    
    # Phase B: 실제 DB Fine-tuning
    phase_b_start = datetime.now()
    model_final = train_phase_b_finetuning()
    phase_b_duration = (datetime.now() - phase_b_start).total_seconds() / 60
    
    if model_final is None:
        print("\n[FAILED] Phase B 실패. 하지만 Phase A 모델은 사용 가능합니다.")
        return
    
    print(f"\n[SUCCESS] Phase B 완료 (소요 시간: {phase_b_duration:.1f}분)")
    
    # 전체 완료
    total_duration = (datetime.now() - start_time).total_seconds() / 60
    
    print("\n\n")
    print("=" * 80)
    print(" " * 22 + "DQN v2 학습 완료!")
    print("=" * 80)
    print(f"\n종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 소요 시간: {total_duration:.1f}분 ({total_duration/60:.1f}시간)")
    print("\n📊 학습 결과:")
    print(f"  - Phase A (Sim): {phase_a_duration:.1f}분, {SIM_TIMESTEPS:,} 타임스텝")
    print(f"  - Phase B (Real): {phase_b_duration:.1f}분, {REAL_TIMESTEPS:,} 타임스텝")
    print(f"\n💾 저장된 모델:")
    print(f"  - 시뮬레이션 모델: {SIM_MODEL_PATH}")
    print(f"  - 최종 모델: {REAL_MODEL_PATH}")
    print(f"\n📈 TensorBoard 로그: {TB_LOG_DIR}")
    print(f"   실행: tensorboard --logdir={TB_LOG_DIR}")
    print("\n[NEXT] 다음 단계: v2_evaluate.py로 성능 평가를 진행하세요.")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='DQN v2 하이브리드 학습')
    parser.add_argument('--phase', type=str, choices=['SimulXGB', 'RealDB', 'full'], default='full',
                        help='학습 단계: SimulXGB(시뮬레이션만), RealDB(Fine-tuning만), full(전체)')
    args = parser.parse_args()
    
    if args.phase == 'SimulXGB':
        train_phase_a_simulation()
    elif args.phase == 'RealDB':
        train_phase_b_finetuning()
    else:
        train_dqn_v2_full()

