# -*- coding: utf-8 -*-
"""
DQN v2: 빠른 테스트 스크립트
============================
학습 전에 모든 컴포넌트가 정상 작동하는지 확인합니다.
"""

import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML'))

def test_reward_function():
    """v2 보상 함수 테스트"""
    print("\n" + "="*60)
    print("1. v2_reward.py 테스트")
    print("="*60)
    
    try:
        from RLQO.env.v2_reward import calculate_reward_v2
        
        baseline = {'elapsed_time_ms': 100, 'logical_reads': 1000, 'cpu_time_ms': 70}
        before = baseline.copy()
        
        # 개선 케이스
        after_good = {'elapsed_time_ms': 50, 'logical_reads': 500, 'cpu_time_ms': 35}
        reward = calculate_reward_v2(before, after_good, baseline, 0, 10)
        
        print(f"[OK] 보상 함수 작동 확인")
        print(f"  50% 개선 시 보상: {reward:.3f} (예상: 양수)")
        
        # 악화 케이스
        after_bad = {'elapsed_time_ms': 150, 'logical_reads': 1500, 'cpu_time_ms': 105}
        reward = calculate_reward_v2(before, after_bad, baseline, 0, 10)
        print(f"  50% 악화 시 보상: {reward:.3f} (예상: 음수)")
        
        return True
    except Exception as e:
        print(f"✗ 오류: {e}")
        return False


def test_sim_env():
    """시뮬레이션 환경 테스트"""
    print("\n" + "="*60)
    print("2. v2_sim_env.py 테스트")
    print("="*60)
    
    try:
        from RLQO.env.v2_sim_env import QueryPlanSimEnv
        from RLQO.constants import SAMPLE_QUERIES
        
        env = QueryPlanSimEnv(
            query_list=SAMPLE_QUERIES[:2],  # 2개만 테스트
            xgb_model_path='Apollo.ML/artifacts/model.joblib',
            verbose=False
        )
        
        # 1 에피소드 테스트
        obs, info = env.reset(seed=42)
        print(f"[OK] 환경 초기화 성공")
        print(f"  상태 벡터 shape: {obs.shape}")
        print(f"  베이스라인 시간: {info['metrics']['elapsed_time_ms']:.2f} ms")
        
        # 1 스텝 테스트
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"[OK] 스텝 실행 성공")
        print(f"  보상: {reward:.3f}")
        print(f"  개선도: {info['improvement_pct']:.1f}%")
        
        env.close()
        return True
    except FileNotFoundError as e:
        print(f"[ERROR] XGB 모델을 찾을 수 없습니다: {e}")
        print("  해결: enhanced_train.py를 먼저 실행하여 XGB 모델을 학습하세요.")
        return False
    except Exception as e:
        print(f"[ERROR] 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_imports():
    """필수 모듈 import 테스트"""
    print("\n" + "="*60)
    print("0. 필수 모듈 확인")
    print("="*60)
    
    modules = {
        'stable_baselines3': 'Stable Baselines3 (강화학습)',
        'gymnasium': 'Gymnasium (RL 환경)',
        'joblib': 'Joblib (모델 직렬화)',
        'xgboost': 'XGBoost (예측 모델)',
        'pandas': 'Pandas (데이터 처리)',
        'numpy': 'NumPy (수치 연산)'
    }
    
    all_ok = True
    for module, desc in modules.items():
        try:
            __import__(module)
            print(f"[OK] {module:20s} - {desc}")
        except ImportError:
            print(f"[X]  {module:20s} - 설치 필요: pip install {module}")
            all_ok = False
    
    return all_ok


def test_file_structure():
    """파일 구조 확인"""
    print("\n" + "="*60)
    print("3. 파일 구조 확인")
    print("="*60)
    
    required_files = [
        'Apollo.ML/RLQO/env/v2_reward.py',
        'Apollo.ML/RLQO/env/v2_sim_env.py',
        'Apollo.ML/RLQO/train/v2_train_dqn.py',
        'Apollo.ML/RLQO/train/v2_evaluate.py',
        'Apollo.ML/RLQO/DQN_v2_README.md',
    ]
    
    all_ok = True
    for filepath in required_files:
        if os.path.exists(filepath):
            print(f"[OK] {filepath}")
        else:
            print(f"[X]  {filepath} - 파일 없음")
            all_ok = False
    
    # XGB 모델 확인 (선택적)
    xgb_path = 'Apollo.ML/artifacts/model.joblib'
    if os.path.exists(xgb_path):
        print(f"[OK] {xgb_path} (필수)")
    else:
        print(f"[!]  {xgb_path} - 필수! enhanced_train.py를 먼저 실행하세요.")
        all_ok = False
    
    return all_ok


def main():
    """전체 테스트 실행"""
    print("\n")
    print("=" * 60)
    print(" " * 15 + "DQN v2 빠른 테스트")
    print("=" * 60)
    
    tests = [
        ("필수 모듈 확인", test_imports),
        ("파일 구조 확인", test_file_structure),
        ("보상 함수", test_reward_function),
        ("시뮬레이션 환경", test_sim_env),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n[ERROR] {test_name} 테스트 중 예외 발생: {e}")
            results[test_name] = False
    
    # 결과 요약
    print("\n\n" + "="*60)
    print("테스트 결과 요약")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{test_name:20s}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("[SUCCESS] 모든 테스트 통과!")
        print("\n다음 단계:")
        print("1. 학습 시작: python Apollo.ML/RLQO/train/v2_train_dqn.py")
        print("2. 예상 소요 시간: 3-5시간")
    else:
        print("[WARNING] 일부 테스트 실패")
        print("\n해결 방법:")
        if not results.get("필수 모듈 확인", False):
            print("- 누락된 패키지 설치: pip install [패키지명]")
        if not results.get("시뮬레이션 환경", False):
            print("- XGB 모델 학습: python Apollo.ML/enhanced_train.py")
    
    print("="*60 + "\n")


if __name__ == '__main__':
    main()

