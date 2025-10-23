# -*- coding: utf-8 -*-
"""
PPO v3 RealDB Fine-tuning 재개 스크립트

최신 체크포인트에서 이어서 학습합니다.
"""

import os
import sys
from datetime import datetime
from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import CheckpointCallback

# 프로젝트 루트 경로 설정
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)

from RLQO.PPO_v3.train.v3_train_realdb import make_masked_env
from RLQO.PPO_v3.train.callbacks import ActionDiversityCallback

# 경로 설정
BASE_DIR = os.path.join(apollo_ml_dir, "artifacts", "RLQO")
CHECKPOINT_DIR = os.path.join(BASE_DIR, "models", "checkpoints", "ppo_v3_realdb")
FINAL_MODEL_PATH = os.path.join(BASE_DIR, "models", "ppo_v3_realdb_50k.zip")
TB_LOG_DIR = os.path.join(BASE_DIR, "tb", "ppo_v3_realdb")

# 최신 체크포인트 찾기
def find_latest_checkpoint():
    """최신 체크포인트 파일을 찾습니다."""
    checkpoints = [f for f in os.listdir(CHECKPOINT_DIR) if f.endswith('.zip')]
    if not checkpoints:
        return None
    
    # 파일명에서 timesteps 추출하여 정렬
    checkpoint_steps = []
    for cp in checkpoints:
        try:
            steps = int(cp.split('_')[3].replace('steps.zip', ''))
            checkpoint_steps.append((steps, cp))
        except:
            continue
    
    if not checkpoint_steps:
        return None
    
    checkpoint_steps.sort(reverse=True)
    latest_steps, latest_file = checkpoint_steps[0]
    
    return os.path.join(CHECKPOINT_DIR, latest_file), latest_steps


def resume_training():
    """체크포인트에서 학습을 재개합니다."""
    
    print("=" * 80)
    print(" PPO v3 RealDB Fine-tuning 재개")
    print("=" * 80)
    print(f"타임스탬프: {datetime.now().strftime('%Y%m%d_%H%M%S')}")
    print("-" * 80)
    
    # 1. 최신 체크포인트 찾기
    checkpoint_info = find_latest_checkpoint()
    if checkpoint_info is None:
        print("[ERROR] 체크포인트를 찾을 수 없습니다!")
        return
    
    checkpoint_path, current_steps = checkpoint_info
    print(f"[OK] 최신 체크포인트 발견: {os.path.basename(checkpoint_path)}")
    print(f"     현재 진행: {current_steps:,} steps")
    
    # 목표 계산
    target_total = 150_000  # Simulation 100K + RealDB 50K
    remaining_steps = target_total - current_steps
    
    print(f"     목표: {target_total:,} steps")
    print(f"     남은 학습량: {remaining_steps:,} steps")
    
    if remaining_steps <= 0:
        print("\n[INFO] 이미 목표를 달성했습니다!")
        return
    
    # 2. 환경 생성
    print("\n[1/3] RealDB 환경 생성 중...")
    try:
        env = make_masked_env(verbose=False)
        print("[OK] 환경 생성 완료")
    except Exception as e:
        print(f"[ERROR] 환경 생성 실패: {e}")
        return
    
    # 3. 체크포인트 로드
    print("\n[2/3] 체크포인트 로드 중...")
    try:
        model = MaskablePPO.load(
            checkpoint_path,
            env=env,
            tensorboard_log=TB_LOG_DIR
        )
        print("[OK] 모델 로드 완료")
        print(f"     Learning rate: {model.learning_rate}")
        print(f"     Entropy coef: {model.ent_coef}")
    except Exception as e:
        print(f"[ERROR] 모델 로드 실패: {e}")
        env.close()
        return
    
    # 4. 콜백 설정
    print("\n[3/3] 학습 재개 중...")
    checkpoint_callback = CheckpointCallback(
        save_freq=1_000,  # 자주 저장 (1K steps마다)
        save_path=CHECKPOINT_DIR,
        name_prefix="ppo_v3_realdb"
    )
    
    action_diversity_callback = ActionDiversityCallback(
        max_consecutive=10,
        verbose=False
    )
    
    callbacks = [checkpoint_callback, action_diversity_callback]
    
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"예상 소요 시간: 약 {int(remaining_steps / 2 / 60)} 분 (FPS 2 기준)")
    print("-" * 80)
    
    try:
        model.learn(
            total_timesteps=remaining_steps,
            callback=callbacks,
            tb_log_name="ppo_v3_realdb_resumed",
            reset_num_timesteps=False  # 기존 timesteps 유지
        )
        
        # 최종 모델 저장
        model.save(FINAL_MODEL_PATH)
        print(f"\n[OK] 학습 완료! 모델 저장: {FINAL_MODEL_PATH}")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"최종 timesteps: {current_steps + remaining_steps:,}")
        
    except KeyboardInterrupt:
        print("\n[INFO] 사용자에 의해 학습 중단됨")
        partial_model_path = os.path.join(BASE_DIR, "models", "ppo_v3_realdb_partial.zip")
        model.save(partial_model_path)
        print(f"[INFO] 부분 학습 모델 저장: {partial_model_path}")
    
    except Exception as e:
        print(f"\n[ERROR] 학습 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        env.close()
        print("\n[INFO] 환경 종료")
    
    print("\n" + "=" * 80)
    print(" 학습 완료!")
    print("=" * 80)
    print(f"모델 경로: {FINAL_MODEL_PATH}")
    print(f"체크포인트: {CHECKPOINT_DIR}")
    print("-" * 80)
    print("다음 단계: 모델 평가")
    print(f"   python Apollo.ML/RLQO/PPO_v3/train/v3_evaluate.py \\")
    print(f"     --model {FINAL_MODEL_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    resume_training()

