# -*- coding: utf-8 -*-
"""
PPO v1 학습 로그 분석 스크립트
Action 선택 패턴, 보상 분포, 학습 진행 상황 분석
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from tensorboard.backend.event_processing import event_accumulator

# 프로젝트 루트 설정
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)

# Load ACTION_SPACE from JSON
action_space_path = os.path.join(apollo_ml_dir, 'artifacts', 'RLQO', 'configs', 'v3_action_space.json')
with open(action_space_path, 'r', encoding='utf-8') as f:
    ACTION_SPACE = json.load(f)


def analyze_tensorboard_logs(log_dir: str):
    """TensorBoard 로그 파일 분석"""
    print(f"\n{'='*80}")
    print(f"분석 중: {log_dir}")
    print(f"{'='*80}")
    
    # EventAccumulator 초기화
    ea = event_accumulator.EventAccumulator(log_dir)
    ea.Reload()
    
    # 사용 가능한 태그 확인
    print("\n[사용 가능한 스칼라 태그]")
    scalar_tags = ea.Tags()['scalars']
    for tag in scalar_tags:
        print(f"  - {tag}")
    
    # 주요 학습 메트릭 추출
    results = {}
    
    # 1. Entropy Loss (다양성 지표)
    if 'train/entropy_loss' in scalar_tags:
        entropy_events = ea.Scalars('train/entropy_loss')
        entropy_values = [e.value for e in entropy_events]
        results['entropy_loss'] = {
            'first': entropy_values[0] if entropy_values else None,
            'last': entropy_values[-1] if entropy_values else None,
            'mean': np.mean(entropy_values) if entropy_values else None,
            'trend': 'decreasing' if entropy_values and entropy_values[-1] < entropy_values[0] else 'increasing'
        }
        print(f"\n[Entropy Loss 분석]")
        print(f"  초기: {results['entropy_loss']['first']:.4f}")
        print(f"  최종: {results['entropy_loss']['last']:.4f}")
        print(f"  평균: {results['entropy_loss']['mean']:.4f}")
        print(f"  추세: {results['entropy_loss']['trend']}")
        print(f"  → Entropy가 매우 낮으면 정책이 특정 액션에 고정됨")
    
    # 2. Policy Gradient Loss
    if 'train/policy_gradient_loss' in scalar_tags:
        pg_events = ea.Scalars('train/policy_gradient_loss')
        pg_values = [e.value for e in pg_events]
        results['policy_gradient_loss'] = {
            'last': pg_values[-1] if pg_values else None,
            'mean': np.mean(pg_values) if pg_values else None
        }
        print(f"\n[Policy Gradient Loss]")
        print(f"  최종: {results['policy_gradient_loss']['last']:.6f}")
        print(f"  평균: {results['policy_gradient_loss']['mean']:.6f}")
    
    # 3. Clip Fraction (정책 변화 정도)
    if 'train/clip_fraction' in scalar_tags:
        clip_events = ea.Scalars('train/clip_fraction')
        clip_values = [e.value for e in clip_events]
        results['clip_fraction'] = {
            'last': clip_values[-1] if clip_values else None,
            'mean': np.mean(clip_values) if clip_values else None
        }
        print(f"\n[Clip Fraction]")
        print(f"  최종: {results['clip_fraction']['last']:.4f}")
        print(f"  평균: {results['clip_fraction']['mean']:.4f}")
        print(f"  → 0에 가까우면 정책이 거의 변하지 않음 (조기 수렴)")
    
    # 4. Approx KL
    if 'train/approx_kl' in scalar_tags:
        kl_events = ea.Scalars('train/approx_kl')
        kl_values = [e.value for e in kl_events]
        results['approx_kl'] = {
            'last': kl_values[-1] if kl_values else None,
            'mean': np.mean(kl_values) if kl_values else None
        }
        print(f"\n[Approx KL]")
        print(f"  최종: {results['approx_kl']['last']:.6f}")
        print(f"  평균: {results['approx_kl']['mean']:.6f}")
        print(f"  → 매우 낮으면 새 정책과 이전 정책이 거의 동일 (학습 정체)")
    
    # 5. Value Loss
    if 'train/value_loss' in scalar_tags:
        value_events = ea.Scalars('train/value_loss')
        value_values = [e.value for e in value_events]
        results['value_loss'] = {
            'last': value_values[-1] if value_values else None,
            'mean': np.mean(value_values) if value_values else None
        }
        print(f"\n[Value Loss]")
        print(f"  최종: {results['value_loss']['last']:.2f}")
        print(f"  평균: {results['value_loss']['mean']:.2f}")
    
    # 6. Learning Rate
    if 'train/learning_rate' in scalar_tags:
        lr_events = ea.Scalars('train/learning_rate')
        lr_values = [e.value for e in lr_events]
        print(f"\n[Learning Rate]")
        print(f"  {lr_values[-1]:.2e}")
    
    return results


def diagnose_action8_problem(log_results: dict):
    """Action 8 과도 선택 원인 진단"""
    print(f"\n{'='*80}")
    print("Action 8 과도 선택 원인 진단")
    print(f"{'='*80}")
    
    issues = []
    
    # 1. Entropy Loss 체크
    if log_results.get('entropy_loss'):
        entropy = log_results['entropy_loss']
        if entropy['last'] and entropy['last'] > -0.5:  # Entropy loss가 -0.5보다 크면 (덜 음수)
            issues.append({
                'issue': '매우 낮은 Entropy',
                'value': f"{entropy['last']:.4f}",
                'diagnosis': '정책이 특정 액션(Action 8)에 고착화됨',
                'cause': 'Conservative mode가 너무 제한적 + 낮은 entropy coefficient'
            })
    
    # 2. Clip Fraction 체크
    if log_results.get('clip_fraction'):
        clip = log_results['clip_fraction']
        if clip['last'] is not None and clip['last'] < 0.01:
            issues.append({
                'issue': 'Clip Fraction 거의 0',
                'value': f"{clip['last']:.4f}",
                'diagnosis': '정책이 거의 변하지 않음 (조기 수렴)',
                'cause': '너무 낮은 learning rate (5e-5) + 제한적인 action space'
            })
    
    # 3. Approx KL 체크
    if log_results.get('approx_kl'):
        kl = log_results['approx_kl']
        if kl['last'] is not None and kl['last'] < 0.01:
            issues.append({
                'issue': 'KL Divergence 매우 낮음',
                'value': f"{kl['last']:.6f}",
                'diagnosis': '새 정책이 이전 정책과 거의 동일 (학습 정체)',
                'cause': '보수적인 학습 설정 + 제한적인 탐색'
            })
    
    # 진단 결과 출력
    print(f"\n발견된 문제: {len(issues)}개\n")
    for i, issue in enumerate(issues, 1):
        print(f"{i}. {issue['issue']}")
        print(f"   값: {issue['value']}")
        print(f"   진단: {issue['diagnosis']}")
        print(f"   원인: {issue['cause']}\n")
    
    # 종합 진단
    print(f"{'='*80}")
    print("종합 진단")
    print(f"{'='*80}")
    print("""
RealDB 학습이 Action 8에 고착된 주요 원인:

1. **Conservative Mode의 과도한 제약**
   - Query 타입별로 안전한 액션만 허용
   - Action space가 너무 좁아져 다양성 상실
   
2. **매우 낮은 Learning Rate (5e-5)**
   - 정책 변화가 너무 느림
   - 초기 선택된 Action 8에서 벗어나지 못함
   
3. **낮은 Entropy Coefficient (0.005)**
   - 탐험(exploration)이 거의 없음
   - 익숙한 액션만 계속 선택
   
4. **보수적인 보상 함수**
   - 안전한 액션(Action 8)에 보너스 (+2.0)
   - 위험한 액션에 강한 페널티 (-20.0 ~ -30.0)
   - 결과: 에이전트가 안전한 Action 8만 선택
""")
    
    return issues


def main():
    """메인 실행"""
    print(f"\n{'='*80}")
    print("PPO v1 학습 로그 분석")
    print(f"{'='*80}")
    
    # Action Space 확인
    print(f"\n[Action 8 정보]")
    action_8 = next((a for a in ACTION_SPACE if a['id'] == 8), None)
    if action_8:
        print(f"  ID: {action_8['id']}")
        print(f"  Name: {action_8['name']}")
        print(f"  Description: {action_8['description']}")
        print(f"  Type: {action_8['type']}")
    
    # 1. RealDB 학습 로그 분석
    realdb_log = "Apollo.ML/artifacts/RLQO/tb/ppo_v1_realdb/ppo_v1_realdb_1"
    if os.path.exists(realdb_log):
        realdb_results = analyze_tensorboard_logs(realdb_log)
        diagnose_action8_problem(realdb_results)
    else:
        print(f"\n[ERROR] RealDB 로그 찾을 수 없음: {realdb_log}")
    
    # 2. Improved Simul 로그 분석 (비교)
    print(f"\n\n{'='*80}")
    print("비교: Improved Simul 학습 로그")
    print(f"{'='*80}")
    
    improved_log = "Apollo.ML/artifacts/RLQO/tb/ppo_v1_improved/ppo_v1_improved_1"
    if os.path.exists(improved_log):
        improved_results = analyze_tensorboard_logs(improved_log)
    else:
        print(f"\n[INFO] Improved Simul 로그 찾을 수 없음: {improved_log}")
    
    print(f"\n{'='*80}")
    print("분석 완료!")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()

