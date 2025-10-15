# -*- coding: utf-8 -*-
"""
PPO v1 개선 학습 스크립트

Query 타입별 보상 함수와 보수적 정책을 적용한 개선된 PPO 학습
- Simul 환경에서 100K steps 학습
- 안전한 액션 우선 선택
- Query 타입별 최적화
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

# 프로젝트 루트 경로 설정
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)

from RLQO.PPO_v1.env.v1_sim_env_improved import QueryPlanSimEnvV1Improved
from RLQO.constants import SAMPLE_QUERIES

# ============================================================================
# 하이퍼파라미터 (개선된 설정)
# ============================================================================
SIM_TIMESTEPS = 100_000  # 100K steps (빠른 검증)
SIM_LEARNING_RATE = 1e-4  # 보수적 학습률
SIM_N_STEPS = 1024  # 배치 크기 감소 (2048 → 1024)
SIM_BATCH_SIZE = 64
SIM_N_EPOCHS = 10
SIM_GAMMA = 0.99
SIM_CLIP_RANGE = 0.2
SIM_ENT_COEF = 0.01  # 탐험 감소 (안전성 우선)

# 경로 설정
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_DIR = "Apollo.ML/artifacts/RLQO/"

SIM_LOG_DIR = f"{BASE_DIR}logs/ppo_v1_improved/"
SIM_MODEL_PATH = f"{BASE_DIR}models/ppo_v1_sim_improved_100k.zip"
SIM_CHECKPOINT_DIR = f"{BASE_DIR}models/checkpoints/ppo_v1_improved/"

TB_LOG_DIR = f"{BASE_DIR}tb/ppo_v1_improved/"

# 디렉토리 생성
for directory in [SIM_LOG_DIR, SIM_CHECKPOINT_DIR]:
    os.makedirs(directory, exist_ok=True)


def mask_fn(env):
    """
    PPO용 액션 마스크 함수
    ActionMasker wrapper에서 사용됩니다.
    
    Args:
        env: QueryPlanSimEnvV1Improved 환경
    
    Returns:
        action_mask: boolean array (True = valid action)
    """
    # get_action_mask()는 float32 array를 반환 (1.0 = valid, 0.0 = invalid)
    # ActionMasker는 boolean array를 기대하므로 변환
    float_mask = env.get_action_mask()
    return float_mask.astype(bool)


def make_masked_env(verbose=False):
    """
    액션 마스킹이 적용된 개선된 시뮬레이션 환경을 생성합니다.
    
    Args:
        verbose: 진행 상황 출력 여부
    
    Returns:
        env: ActionMasker로 래핑된 환경
    """
    # 개선된 시뮬레이션 환경 생성
    env = QueryPlanSimEnvV1Improved(
        query_list=SAMPLE_QUERIES,
        max_steps=10,
        conservative_mode=True,  # 안전한 액션만 허용
        cache_path='Apollo.ML/artifacts/RLQO/cache/v2_plan_cache.pkl',
        curriculum_mode=True,  # 베이스라인 시간 기반 Curriculum Learning
        verbose=verbose
    )
    
    # ActionMasker wrapper 적용
    env = ActionMasker(env, mask_fn)
    
    # Monitor wrapper 적용 (로깅)
    env = Monitor(env, SIM_LOG_DIR)
    
    return env


def train_improved_simul():
    """
    Phase 1: 개선된 시뮬레이션 학습
    - Query 타입별 보상 함수
    - 보수적 정책 (안전한 액션 우선)
    - 100K 타임스텝
    """
    print("=" * 80)
    print(" PPO v1 개선 학습 시작 (Phase 1: Improved Simul)")
    print("=" * 80)
    print(f"알고리즘: MaskablePPO + Query Type-aware Rewards")
    print(f"타임스텝: {SIM_TIMESTEPS:,}")
    print(f"예상 소요 시간: 1-2시간")
    print(f"쿼리 개수: {len(SAMPLE_QUERIES)}")
    print("-" * 80)
    print(f"핵심 개선사항:")
    print(f"  1. Query 타입 자동 분류 (CTE, JOIN_HEAVY, TOP, SIMPLE)")
    print(f"  2. 타입별 안전한/위험한 액션 정의")
    print(f"  3. 위험한 액션 강력한 페널티 (-20 ~ -30)")
    print(f"  4. 안전한 액션 보너스 (+2)")
    print(f"  5. 보수적 정책 (Conservative Mode ON)")
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
    print("\n[1/4] 개선된 시뮬레이션 환경 생성 중...")
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
            save_freq=10_000,  # 10K steps마다 저장 (빠른 검증)
            save_path=SIM_CHECKPOINT_DIR,
            name_prefix="ppo_v1_improved"
        )
        
        # Eval 환경 생성 (평가용)
        eval_env = make_masked_env(verbose=False)
        
        eval_callback = EvalCallback(
            eval_env,
            best_model_save_path=SIM_CHECKPOINT_DIR,
            log_path=SIM_LOG_DIR,
            eval_freq=5_000,  # 5K steps마다 평가
            deterministic=True,
            render=False
        )
        
        callbacks = [checkpoint_callback, eval_callback]
        print("[OK] 콜백 설정 완료")
        print(f"     Checkpoint frequency: 10,000 steps")
        print(f"     Evaluation frequency: 5,000 steps")
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
            tb_log_name="ppo_v1_improved"
        )
        
        # 모델 저장
        model.save(SIM_MODEL_PATH)
        print(f"\n[OK] 학습 완료! 모델 저장: {SIM_MODEL_PATH}")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"[ERROR] 학습 실패: {e}")
        import traceback
        traceback.print_exc()
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
    print(" PPO v1 Improved Environment 테스트")
    print("=" * 80)
    
    try:
        # 환경 생성
        print("\n[1/3] 환경 생성 중...")
        env = make_masked_env(verbose=True)
        print("[OK] 환경 생성 완료")
        print(f"     Action space: {env.action_space}")
        print(f"     Observation space: {env.observation_space}")
        
        # 리셋 테스트
        print("\n[2/3] 리셋 테스트 중...")
        obs, info = env.reset()
        print("[OK] 리셋 완료")
        print(f"     Observation shape: {obs.shape}")
        print(f"     Query type: {info.get('query_type', 'N/A')}")
        
        # 액션 마스크 테스트
        print("\n[3/3] 액션 마스크 테스트 중...")
        # ActionMasker는 action_mask()를 자동으로 호출
        # 내부 환경의 get_action_mask()로 직접 접근
        base_env = env.env  # Monitor
        if hasattr(base_env, 'env'):
            base_env = base_env.env  # ActionMasker
        if hasattr(base_env, 'env'):
            base_env = base_env.env  # QueryPlanSimEnvV1Improved
        
        if hasattr(base_env, 'get_action_mask'):
            action_mask = base_env.get_action_mask()
            compatible_count = int(np.sum(action_mask))
            print(f"[OK] 액션 마스크 확인 완료")
            print(f"     Compatible actions: {compatible_count}/{len(action_mask)}")
            print(f"     Query type: {base_env.current_query_type}")
        
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
    
    parser = argparse.ArgumentParser(description='PPO v1 개선 학습 (Phase 1: Simul)')
    parser.add_argument('--test', action='store_true',
                       help='환경 테스트만 실행')
    
    args = parser.parse_args()
    
    if args.test:
        test_environment()
        return
    
    print("=" * 80)
    print(" PPO v1 개선 학습 파이프라인")
    print("=" * 80)
    print(f"타임스탬프: {TIMESTAMP}")
    print(f"전략: Improved Simul (Query Type-aware)")
    print("-" * 80)
    
    model = train_improved_simul()
    
    if model:
        print("\n" + "=" * 80)
        print(" Phase 1 학습 완료!")
        print("=" * 80)
        print(f"모델 경로: {SIM_MODEL_PATH}")
        print(f"TensorBoard 로그: {TB_LOG_DIR}")
        print(f"체크포인트: {SIM_CHECKPOINT_DIR}")
        print("-" * 80)
        print("\n다음 단계 (Phase 2: 평가 및 결정):")
        print("1. 모델 평가:")
        print(f"   python Apollo.ML/RLQO/PPO_v1/train/v1_evaluate.py \\")
        print(f"     --model {SIM_MODEL_PATH}")
        print("\n2. 성공 기준 확인:")
        print("   - Avg Speedup ≥ 1.1x")
        print("   - CTE 쿼리 악화 없음")
        print("   - 위험한 액션 선택율 < 10%")
        print("\n3. 기준 충족 시 Phase 3 (RealDB Fine-tuning) 진행")
        print("-" * 80)
    else:
        print("\n[ERROR] 학습 실패!")


if __name__ == "__main__":
    main()

