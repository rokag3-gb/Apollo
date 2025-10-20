# -*- coding: utf-8 -*-
"""
PPO v2 RealDB Fine-tuning 스크립트

Simulation 모델을 실제 DB 환경에서 Fine-tuning합니다.
- 낮은 learning rate (5e-5)
- 낮은 entropy (0.005)
- 50K timesteps (예상 30-60분)
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

from RLQO.PPO_v2.env.v2_db_env import QueryPlanDBEnvV2
from RLQO.PPO_v2.train.callbacks import ActionDiversityCallback
from RLQO.constants import SAMPLE_QUERIES

# ============================================================================
# 하이퍼파라미터 (RealDB Fine-tuning)
# ============================================================================
REAL_TIMESTEPS = 50_000  # 50K steps (예상 30-60분)
REAL_LEARNING_RATE = 5e-5  # 매우 낮은 학습률 (미세 조정)
REAL_N_STEPS = 256  # 작은 배치 (DB 부하 최소화)
REAL_BATCH_SIZE = 32  # 작은 미니배치
REAL_N_EPOCHS = 10
REAL_GAMMA = 0.99
REAL_CLIP_RANGE = 0.2
REAL_ENT_COEF = 0.005  # 매우 낮은 탐험 (안정성 최우선)

# 경로 설정
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_DIR = "Apollo.ML/artifacts/RLQO/"

# Simulation 모델 경로 (Pre-trained)
PRETRAINED_MODEL_PATH = f"{BASE_DIR}models/ppo_v2_sim_improved_100k.zip"

REAL_LOG_DIR = f"{BASE_DIR}logs/ppo_v2_realdb/"
REAL_MODEL_PATH = f"{BASE_DIR}models/ppo_v2_realdb_50k.zip"
REAL_CHECKPOINT_DIR = f"{BASE_DIR}models/checkpoints/ppo_v2_realdb/"

TB_LOG_DIR = f"{BASE_DIR}tb/ppo_v2_realdb/"

# 디렉토리 생성
for directory in [REAL_LOG_DIR, REAL_CHECKPOINT_DIR]:
    os.makedirs(directory, exist_ok=True)


def mask_fn(env):
    """
    PPO용 액션 마스크 함수
    
    Args:
        env: QueryPlanDBEnvV2 환경
    
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
    # PPO v2 RealDB 환경 생성
    env = QueryPlanDBEnvV2(
        query_list=SAMPLE_QUERIES,
        max_steps=10,
        curriculum_mode=True,  # 베이스라인 시간 기반 Curriculum Learning
        verbose=verbose
    )
    
    # ActionMasker wrapper 적용
    env = ActionMasker(env, mask_fn)
    
    # Monitor wrapper 적용 (로깅)
    env = Monitor(env, REAL_LOG_DIR)
    
    return env


def train_realdb_finetune():
    """
    RealDB Fine-tuning
    - Simulation 모델 로드
    - 실제 DB에서 미세 조정
    - 50K 타임스텝
    """
    print("=" * 80)
    print(" PPO v2 RealDB Fine-tuning 시작")
    print("=" * 80)
    print(f"알고리즘: MaskablePPO + Actionable State + Normalized Reward")
    print(f"환경: Real SQL Server DB")
    print(f"타임스텝: {REAL_TIMESTEPS:,}")
    print(f"예상 소요 시간: 30-60분")
    print(f"쿼리 개수: {len(SAMPLE_QUERIES)}")
    print("-" * 80)
    print(f"PPO v2 핵심 개선사항:")
    print(f"  1. State: 79차원 → 18차원 actionable features")
    print(f"  2. Reward: Log scale 정규화 [-1, +1]")
    print(f"  3. Action: Query 타입별 5개 (Dynamic Action Space)")
    print(f"  4. Pre-training: Simulation 100K steps 완료")
    print("-" * 80)
    print(f"하이퍼파라미터 (Fine-tuning):")
    print(f"  Learning Rate: {REAL_LEARNING_RATE} (매우 낮음)")
    print(f"  N Steps: {REAL_N_STEPS}")
    print(f"  Batch Size: {REAL_BATCH_SIZE}")
    print(f"  N Epochs: {REAL_N_EPOCHS}")
    print(f"  Gamma: {REAL_GAMMA}")
    print(f"  Clip Range: {REAL_CLIP_RANGE}")
    print(f"  Entropy Coef: {REAL_ENT_COEF} (매우 낮음)")
    print("-" * 80)
    print(f"Pre-trained 모델: {PRETRAINED_MODEL_PATH}")
    print("-" * 80)
    
    # 1. RealDB 환경 생성
    print("\n[1/4] RealDB 환경 생성 중...")
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
    
    # 2. Pre-trained 모델 로드
    print("\n[2/4] Pre-trained 모델 로드 중...")
    try:
        if not os.path.exists(PRETRAINED_MODEL_PATH):
            print(f"[ERROR] Pre-trained 모델이 없습니다: {PRETRAINED_MODEL_PATH}")
            print("[INFO] Simulation 모델을 먼저 학습해주세요:")
            print(f"       python Apollo.ML/RLQO/PPO_v2/train/v2_train_sim_improved.py")
            env.close()
            return None
        
        model = MaskablePPO.load(
            PRETRAINED_MODEL_PATH,
            env=env,
            tensorboard_log=TB_LOG_DIR
        )
        
        # Fine-tuning을 위한 하이퍼파라미터 조정
        model.learning_rate = REAL_LEARNING_RATE
        model.ent_coef = REAL_ENT_COEF
        
        print("[OK] 모델 로드 완료")
        print(f"     Learning rate: {REAL_LEARNING_RATE}")
        print(f"     Entropy coef: {REAL_ENT_COEF}")
        print(f"     Total parameters: {sum(p.numel() for p in model.policy.parameters()):,}")
    except Exception as e:
        print(f"[ERROR] 모델 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        env.close()
        return None
    
    # 3. 콜백 설정
    print("\n[3/4] 콜백 설정 중...")
    try:
        checkpoint_callback = CheckpointCallback(
            save_freq=5_000,  # 5K steps마다 저장
            save_path=REAL_CHECKPOINT_DIR,
            name_prefix="ppo_v2_realdb"
        )
        
        action_diversity_callback = ActionDiversityCallback(
            max_consecutive=10,  # 10번 연속 동일 액션 선택 시 경고
            verbose=False  # 실시간 출력 비활성화
        )
        
        callbacks = [checkpoint_callback, action_diversity_callback]
        print("[OK] 콜백 설정 완료")
        print(f"     Checkpoint frequency: 5,000 steps")
        print(f"     Action diversity monitoring: ON")
    except Exception as e:
        print(f"[ERROR] 콜백 설정 실패: {e}")
        env.close()
        return None
    
    # 4. Fine-tuning 시작
    print("\n[4/4] Fine-tuning 시작...")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    print("TIP: TensorBoard로 실시간 모니터링:")
    print(f"     tensorboard --logdir {TB_LOG_DIR}")
    print("-" * 80)
    
    try:
        model.learn(
            total_timesteps=REAL_TIMESTEPS,
            callback=callbacks,
            tb_log_name="ppo_v2_realdb",
            reset_num_timesteps=False  # 기존 timesteps 유지
        )
        
        # 모델 저장
        model.save(REAL_MODEL_PATH)
        print(f"\n[OK] Fine-tuning 완료! 모델 저장: {REAL_MODEL_PATH}")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n[INFO] 사용자에 의해 학습 중단됨")
        print(f"[INFO] 마지막 체크포인트: {REAL_CHECKPOINT_DIR}")
        
        # 현재까지 학습된 모델 저장
        partial_model_path = f"{BASE_DIR}models/ppo_v2_realdb_partial.zip"
        model.save(partial_model_path)
        print(f"[INFO] 부분 학습 모델 저장: {partial_model_path}")
        
    except RuntimeError as e:
        if "DB 연결 불가" in str(e):
            print("\n[INFO] DB 연결 문제로 학습 자동 중단")
            print(f"[INFO] 연속 실패 횟수가 임계값을 초과했습니다")
            print(f"[INFO] 마지막 체크포인트: {REAL_CHECKPOINT_DIR}")
            print(f"[INFO] DB를 다시 시작한 후 체크포인트에서 재개하세요")
            
            # 현재까지 학습된 모델 저장
            partial_model_path = f"{BASE_DIR}models/ppo_v2_realdb_partial.zip"
            model.save(partial_model_path)
            print(f"[INFO] 부분 학습 모델 저장: {partial_model_path}")
        else:
            raise
        
    except Exception as e:
        print(f"[ERROR] Fine-tuning 실패: {e}")
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
    print(" PPO v2 RealDB Fine-tuning 재개")
    print("=" * 80)
    print(f"체크포인트: {checkpoint_path}")
    print(f"남은 스텝: {remaining_steps:,}")
    print("-" * 80)
    
    # 환경 생성
    env = make_masked_env(verbose=False)
    
    # 모델 로드
    model = MaskablePPO.load(checkpoint_path, env=env)
    print(f"[OK] 모델 로드 완료 (현재 timesteps: {model.num_timesteps:,})")
    
    # 콜백 설정
    checkpoint_callback = CheckpointCallback(
        save_freq=5_000,
        save_path=REAL_CHECKPOINT_DIR,
        name_prefix="ppo_v2_realdb"
    )
    
    action_diversity_callback = ActionDiversityCallback(
        max_consecutive=10,
        verbose=False
    )
    
    # 학습 재개
    print(f"\n학습 재개 중...")
    try:
        model.learn(
            total_timesteps=remaining_steps,
            callback=[checkpoint_callback, action_diversity_callback],
            tb_log_name="ppo_v2_realdb",
            reset_num_timesteps=False  # 기존 timesteps 유지
        )
        
        model.save(REAL_MODEL_PATH)
        print(f"[OK] Fine-tuning 완료!")
        
    except KeyboardInterrupt:
        print("\n[INFO] 사용자에 의해 학습 중단됨")
        partial_model_path = f"{BASE_DIR}models/ppo_v2_realdb_partial.zip"
        model.save(partial_model_path)
        print(f"[INFO] 부분 학습 모델 저장: {partial_model_path}")
        
    except RuntimeError as e:
        if "DB 연결 불가" in str(e):
            print("\n[INFO] DB 연결 문제로 학습 자동 중단")
            print(f"[INFO] 연속 실패 횟수가 임계값을 초과했습니다")
            print(f"[INFO] 마지막 체크포인트: {REAL_CHECKPOINT_DIR}")
            partial_model_path = f"{BASE_DIR}models/ppo_v2_realdb_partial.zip"
            model.save(partial_model_path)
            print(f"[INFO] 부분 학습 모델 저장: {partial_model_path}")
        else:
            raise
        
    except Exception as e:
        print(f"[ERROR] 학습 재개 실패: {e}")
        import traceback
        traceback.print_exc()
    
    env.close()


def test_environment():
    """환경 테스트 함수"""
    print("=" * 80)
    print(" PPO v2 RealDB Environment 테스트")
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
        print(f"     Observation shape: {obs.shape}")
        print(f"     Observation range: [{obs.min():.3f}, {obs.max():.3f}]")
        
        # 액션 마스크 확인
        base_env = env.env
        if hasattr(base_env, 'env'):
            base_env = base_env.env
        if hasattr(base_env, 'env'):
            base_env = base_env.env
        
        if hasattr(base_env, 'get_action_mask'):
            action_mask = base_env.get_action_mask()
            compatible_count = int(np.sum(action_mask))
            valid_actions = np.where(action_mask == 1.0)[0]
            print(f"     Compatible actions: {compatible_count}/{len(action_mask)}")
            print(f"     Valid action IDs: {valid_actions}")
        
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
    
    parser = argparse.ArgumentParser(description='PPO v2 RealDB Fine-tuning')
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
    print(" PPO v2 RealDB Fine-tuning 파이프라인")
    print("=" * 80)
    print(f"타임스탬프: {TIMESTAMP}")
    print(f"전략: Simulation (100K) → RealDB Fine-tuning (50K)")
    print("-" * 80)
    
    model = train_realdb_finetune()
    
    if model:
        print("\n" + "=" * 80)
        print(" RealDB Fine-tuning 완료!")
        print("=" * 80)
        print(f"모델 경로: {REAL_MODEL_PATH}")
        print(f"TensorBoard 로그: {TB_LOG_DIR}")
        print(f"체크포인트: {REAL_CHECKPOINT_DIR}")
        print("-" * 80)
        print("\n다음 단계:")
        print("1. 모델 평가:")
        print(f"   python Apollo.ML/RLQO/PPO_v2/train/v2_evaluate.py \\")
        print(f"     --model {REAL_MODEL_PATH}")
        print("\n2. PPO v2 Simulation vs RealDB 비교")
        print("-" * 80)
    else:
        print("\n[ERROR] Fine-tuning 실패!")


if __name__ == "__main__":
    main()

