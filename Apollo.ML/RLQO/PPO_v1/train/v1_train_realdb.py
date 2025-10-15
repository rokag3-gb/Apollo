# -*- coding: utf-8 -*-
"""
PPO v1 RealDB 직접 학습 스크립트

시뮬레이션 없이 처음부터 실제 DB 환경에서 학습합니다.
- Query 타입별 보상 함수
- 보수적 정책 (안전한 액션 우선)
- 50K steps
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

from RLQO.PPO_v1.env.v1_db_env_improved import QueryPlanDBEnvV1Improved
from RLQO.constants import SAMPLE_QUERIES

# ============================================================================
# 하이퍼파라미터 (RealDB 최적화)
# ============================================================================
REAL_TIMESTEPS = 50_000  # 50K steps (예상 8-16시간)
REAL_LEARNING_RATE = 5e-5  # 매우 낮은 학습률 (안정성 우선)
REAL_N_STEPS = 256  # 작은 배치 (DB 부하 최소화)
REAL_BATCH_SIZE = 32  # 작은 미니배치
REAL_N_EPOCHS = 10
REAL_GAMMA = 0.99
REAL_CLIP_RANGE = 0.2
REAL_ENT_COEF = 0.005  # 매우 낮은 탐험 (안전성 최우선)

# 경로 설정
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_DIR = "Apollo.ML/artifacts/RLQO/"

REAL_LOG_DIR = f"{BASE_DIR}logs/ppo_v1_realdb/"
REAL_MODEL_PATH = f"{BASE_DIR}models/ppo_v1_realdb_50k.zip"
REAL_CHECKPOINT_DIR = f"{BASE_DIR}models/checkpoints/ppo_v1_realdb/"

TB_LOG_DIR = f"{BASE_DIR}tb/ppo_v1_realdb/"

# 디렉토리 생성
for directory in [REAL_LOG_DIR, REAL_CHECKPOINT_DIR]:
    os.makedirs(directory, exist_ok=True)


def mask_fn(env):
    """
    PPO용 액션 마스크 함수
    
    Args:
        env: QueryPlanDBEnvV1Improved 환경
    
    Returns:
        action_mask: boolean array (True = valid action)
    """
    float_mask = env.get_action_mask()
    return float_mask.astype(bool)


def make_masked_env(verbose=False):
    """
    액션 마스킹이 적용된 RealDB 환경을 생성합니다.
    
    Args:
        verbose: 진행 상황 출력 여부
    
    Returns:
        env: ActionMasker로 래핑된 RealDB 환경
    """
    # 개선된 RealDB 환경 생성
    env = QueryPlanDBEnvV1Improved(
        query_list=SAMPLE_QUERIES,
        max_steps=10,
        conservative_mode=True,  # 안전한 액션만 허용
        curriculum_mode=True,  # 베이스라인 시간 기반 Curriculum Learning
        verbose=verbose
    )
    
    # ActionMasker wrapper 적용
    env = ActionMasker(env, mask_fn)
    
    # Monitor wrapper 적용 (로깅)
    env = Monitor(env, REAL_LOG_DIR)
    
    return env


def train_realdb():
    """
    RealDB 직접 학습
    - 시뮬레이션 없이 처음부터 실제 DB에서 학습
    - Query 타입별 보상 함수
    - 보수적 정책 (안전한 액션만)
    - 50K 타임스텝
    """
    print("=" * 80)
    print(" PPO v1 RealDB 직접 학습 시작")
    print("=" * 80)
    print(f"알고리즘: MaskablePPO + Query Type-aware Rewards")
    print(f"환경: Real SQL Server DB (시뮬레이션 없음)")
    print(f"타임스텝: {REAL_TIMESTEPS:,}")
    print(f"예상 소요 시간: 8-16시간")
    print(f"쿼리 개수: {len(SAMPLE_QUERIES)}")
    print("-" * 80)
    print(f"핵심 개선사항:")
    print(f"  1. Query 타입 자동 분류 (CTE, JOIN_HEAVY, TOP, SIMPLE)")
    print(f"  2. 타입별 안전한/위험한 액션 정의")
    print(f"  3. 위험한 액션 강력한 페널티 (-20 ~ -30)")
    print(f"  4. 안전한 액션 보너스 (+2)")
    print(f"  5. 보수적 정책 (Conservative Mode ON)")
    print(f"  6. 실제 DB에서 직접 학습 (시뮬레이션 스킵)")
    print("-" * 80)
    print(f"하이퍼파라미터 (RealDB 최적화):")
    print(f"  Learning Rate: {REAL_LEARNING_RATE} (매우 낮음)")
    print(f"  N Steps: {REAL_N_STEPS} (DB 부하 최소화)")
    print(f"  Batch Size: {REAL_BATCH_SIZE}")
    print(f"  N Epochs: {REAL_N_EPOCHS}")
    print(f"  Gamma: {REAL_GAMMA}")
    print(f"  Clip Range: {REAL_CLIP_RANGE}")
    print(f"  Entropy Coef: {REAL_ENT_COEF} (매우 낮음)")
    print("-" * 80)
    print("[주의] 실제 DB 학습은 매우 느립니다!")
    print("    - DB 부하를 주의 깊게 모니터링하세요")
    print("    - 중간에 중단 가능 (체크포인트 자동 저장)")
    print("-" * 80)
    
    # 1. RealDB 환경 생성
    print("\n[1/4] RealDB 환경 생성 중...")
    try:
        env = make_masked_env(verbose=True)
        print("[OK] 환경 생성 완료")
        print(f"     Action space: {env.action_space}")
        print(f"     Observation space: {env.observation_space}")
    except Exception as e:
        print(f"[ERROR] 환경 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 2. MaskablePPO 모델 생성
    print("\n[2/4] MaskablePPO 모델 생성 중...")
    try:
        model = MaskablePPO(
            "MlpPolicy",
            env,
            learning_rate=REAL_LEARNING_RATE,
            n_steps=REAL_N_STEPS,
            batch_size=REAL_BATCH_SIZE,
            n_epochs=REAL_N_EPOCHS,
            gamma=REAL_GAMMA,
            clip_range=REAL_CLIP_RANGE,
            ent_coef=REAL_ENT_COEF,
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
            save_freq=2_500,  # 2.5K steps마다 저장 (자주 저장)
            save_path=REAL_CHECKPOINT_DIR,
            name_prefix="ppo_v1_realdb"
        )
        
        callbacks = [checkpoint_callback]
        print("[OK] 콜백 설정 완료")
        print(f"     Checkpoint frequency: 2,500 steps")
        print(f"     (Eval callback 제거: DB 부하 최소화)")
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
    print("[중단] Ctrl+C로 중단 가능 (마지막 체크포인트부터 재개 가능)")
    print("-" * 80)
    
    try:
        model.learn(
            total_timesteps=REAL_TIMESTEPS,
            callback=callbacks,
            tb_log_name="ppo_v1_realdb"
        )
        
        # 모델 저장
        model.save(REAL_MODEL_PATH)
        print(f"\n[OK] 학습 완료! 모델 저장: {REAL_MODEL_PATH}")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n[INFO] 사용자에 의해 학습 중단됨")
        print(f"[INFO] 마지막 체크포인트: {REAL_CHECKPOINT_DIR}")
        
        # 현재까지 학습된 모델 저장
        partial_model_path = f"{BASE_DIR}models/ppo_v1_realdb_partial.zip"
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


def resume_training(checkpoint_path: str, remaining_steps: int):
    """
    체크포인트에서 학습 재개
    
    Args:
        checkpoint_path: 재개할 체크포인트 경로
        remaining_steps: 남은 학습 스텝 수
    """
    print("=" * 80)
    print(" PPO v1 RealDB 학습 재개")
    print("=" * 80)
    print(f"체크포인트: {checkpoint_path}")
    print(f"남은 스텝: {remaining_steps:,}")
    print("-" * 80)
    
    # 환경 생성
    env = make_masked_env(verbose=True)
    
    # 모델 로드
    model = MaskablePPO.load(checkpoint_path, env=env)
    print(f"[OK] 모델 로드 완료 (현재 timesteps: {model.num_timesteps:,})")
    
    # 콜백 설정
    checkpoint_callback = CheckpointCallback(
        save_freq=2_500,
        save_path=REAL_CHECKPOINT_DIR,
        name_prefix="ppo_v1_realdb"
    )
    
    # 학습 재개
    print(f"\n학습 재개 중...")
    try:
        model.learn(
            total_timesteps=remaining_steps,
            callback=[checkpoint_callback],
            tb_log_name="ppo_v1_realdb",
            reset_num_timesteps=False  # 기존 timesteps 유지
        )
        
        model.save(REAL_MODEL_PATH)
        print(f"[OK] 학습 완료!")
        
    except Exception as e:
        print(f"[ERROR] 학습 재개 실패: {e}")
        import traceback
        traceback.print_exc()
    
    env.close()


def test_environment():
    """환경 테스트 함수"""
    print("=" * 80)
    print(" PPO v1 RealDB Environment 테스트")
    print("=" * 80)
    
    try:
        # 환경 생성
        print("\n[1/2] 환경 생성 중...")
        env = make_masked_env(verbose=True)
        print("[OK] 환경 생성 완료")
        
        # 리셋 및 스텝 테스트
        print("\n[2/2] 리셋 및 스텝 테스트 중...")
        obs, info = env.reset()
        print(f"[OK] 리셋 완료")
        print(f"     Query type: {info.get('query_type', 'N/A')}")
        
        # 액션 마스크 확인
        base_env = env.env
        if hasattr(base_env, 'env'):
            base_env = base_env.env
        if hasattr(base_env, 'env'):
            base_env = base_env.env
        
        if hasattr(base_env, 'get_action_mask'):
            action_mask = base_env.get_action_mask()
            compatible_count = int(np.sum(action_mask))
            print(f"     Compatible actions: {compatible_count}/{len(action_mask)}")
        
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
    
    parser = argparse.ArgumentParser(description='PPO v1 RealDB 직접 학습')
    parser.add_argument('--test', action='store_true',
                       help='환경 테스트만 실행')
    parser.add_argument('--resume', type=str, default=None,
                       help='체크포인트에서 재개 (경로 지정)')
    parser.add_argument('--steps', type=int, default=REAL_TIMESTEPS,
                       help='학습 스텝 수')
    
    args = parser.parse_args()
    
    if args.test:
        test_environment()
        return
    
    if args.resume:
        resume_training(args.resume, args.steps)
        return
    
    print("=" * 80)
    print(" PPO v1 RealDB 직접 학습 파이프라인")
    print("=" * 80)
    print(f"타임스탬프: {TIMESTAMP}")
    print(f"전략: RealDB Direct (시뮬레이션 없음)")
    print("-" * 80)
    
    model = train_realdb()
    
    if model:
        print("\n" + "=" * 80)
        print(" RealDB 학습 완료!")
        print("=" * 80)
        print(f"모델 경로: {REAL_MODEL_PATH}")
        print(f"TensorBoard 로그: {TB_LOG_DIR}")
        print(f"체크포인트: {REAL_CHECKPOINT_DIR}")
        print("-" * 80)
        print("\n다음 단계:")
        print("1. 모델 평가:")
        print(f"   python Apollo.ML/RLQO/PPO_v1/train/v1_evaluate.py \\")
        print(f"     --model {REAL_MODEL_PATH}")
        print("\n2. DQN v3, PPO v1 Simul과 비교")
        print("-" * 80)
    else:
        print("\n[ERROR] 학습 실패!")


if __name__ == "__main__":
    main()

