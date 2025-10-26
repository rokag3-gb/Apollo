# -*- coding: utf-8 -*-
"""
DDPG v1 Evaluation Script

학습된 DDPG 모델을 평가하고 DQN v3, PPO v3와 비교합니다.
"""

import os
import sys
import argparse
import json
from datetime import datetime
import numpy as np
import pandas as pd

from stable_baselines3 import DDPG

# Project root path setup
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..', '..', '..'))
apollo_ml_dir = os.path.join(project_root, 'Apollo.ML')

sys.path.insert(0, project_root)
sys.path.insert(0, apollo_ml_dir)

from RLQO.DDPG_v1.env.ddpg_db_env import QueryPlanRealDBEnvDDPGv1

# Load 30 queries
sys.path.insert(0, os.path.join(apollo_ml_dir, 'RLQO'))
from constants2 import SAMPLE_QUERIES

# Query names mapping
QUERY_NAMES = {
    0: '계좌별 일별 거래 통계',
    1: '거래소별 종목별 평균 체결가격과 거래량',
    2: '대용량 테이블 전체 스캔',
    3: '2-way JOIN (대용량)',
    4: '3-way JOIN + ORDER BY',
    5: 'NOT EXISTS (서브쿼리)',
    6: 'RAND() 함수',
    7: '주문 체결률과 평균 슬리피지 분석',
    8: '포지션 수익률 분석',
    9: '당일 거래량 상위 종목',
    10: '당일 거래대금 상위 종목',
    11: '전일 종가 대비 등락률 상위 종목',
    12: '계좌별 포지션 평가',
    13: '미체결 주문 목록',
    14: '최근 대량 주문 검색',
    15: '최근 거래 모니터링',
    16: '주문과 체결 내역 함께 조회',
    17: '체결 내역이 있는 주문만 조회 (EXISTS)',
    18: '체결 내역이 있는 주문만 조회 (IN)',
    19: '계좌별 현금 잔액 조회',
    20: '거래소별 종목 수 및 통계',
    21: '종목별 최근 가격 이력',
    22: '고객별 계좌 및 잔액 요약',
    23: '리스크 노출도 스냅샷 조회',
    24: '계좌별 주문 소스 분포',
    25: '종목 타입별 거래 통계',
    26: '마진 계좌 상태 조회',
    27: '컴플라이언스 경고 현황',
    28: '거래 원장 집계 vs 포지션 검증',
    29: '종목별 시세 변동성 분석'
}


def evaluate_ddpg(model_path: str, episodes: int = 3, output_file: str = None):
    """
    DDPG 모델 평가
    
    Args:
        model_path: 학습된 모델 경로
        episodes: 평가 에피소드 수
        output_file: 결과 저장 경로 (JSON)
    """
    print("=" * 80)
    print(" DDPG v1 Model Evaluation")
    print("=" * 80)
    print(f"Model: {model_path}")
    print(f"Episodes: {episodes}")
    print(f"Queries: {len(SAMPLE_QUERIES)}")
    print("=" * 80)
    
    # Check model exists
    if not os.path.exists(model_path):
        print(f"[ERROR] Model not found: {model_path}")
        return
    
    # Load model
    print("\n[1/3] Loading model...")
    try:
        model = DDPG.load(model_path)
        print(f"✓ Model loaded successfully")
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        return
    
    # Create environment
    print("\n[2/3] Creating evaluation environment...")
    env = QueryPlanRealDBEnvDDPGv1(
        query_list=SAMPLE_QUERIES,
        max_steps=10,
        timeout_seconds=30,
        verbose=False  # Reduce verbosity during evaluation
    )
    print(f"✓ Environment created")
    
    # Evaluation
    print("\n[3/3] Starting evaluation...")
    print("-" * 80)
    
    results = []
    query_results = {i: [] for i in range(len(SAMPLE_QUERIES))}
    
    for episode in range(episodes):
        print(f"\nEpisode {episode + 1}/{episodes}")
        print("-" * 80)
        
        for query_idx in range(len(SAMPLE_QUERIES)):
            # Reset to specific query
            env.current_query_ix = query_idx
            obs, info = env.reset()
            
            baseline_time = info['baseline_time']
            best_time = baseline_time
            best_action = None
            total_reward = 0.0
            
            # Run episode
            for step in range(10):
                # Use deterministic action (no noise)
                action, _ = model.predict(obs, deterministic=True)
                
                obs, reward, terminated, truncated, info = env.step(action)
                total_reward += reward
                
                if info['current_time'] < best_time:
                    best_time = info['current_time']
                    best_action = info['action_description']
                
                if terminated or truncated:
                    break
            
            speedup = baseline_time / best_time if best_time > 0 else 1.0
            
            result = {
                'episode': episode + 1,
                'query_idx': query_idx,
                'query_name': QUERY_NAMES.get(query_idx, f'Query {query_idx}'),
                'baseline_time_ms': baseline_time,
                'best_time_ms': best_time,
                'speedup': speedup,
                'improvement_pct': (speedup - 1.0) * 100,
                'total_reward': total_reward,
                'best_action': best_action
            }
            
            results.append(result)
            query_results[query_idx].append(speedup)
            
            # 출력 형식 개선
            query_name = QUERY_NAMES.get(query_idx, f'Query {query_idx}')
            action_str = best_action if best_action else 'NO_ACTION'
            print(f"  Query {query_idx:2d} [{query_name[:30]:30s}]: "
                  f"{baseline_time:6.1f}ms → {best_time:6.1f}ms "
                  f"(Speedup: {speedup:.3f}x, {(speedup-1)*100:+.1f}%)")
            if best_action:
                print(f"           Action: {action_str}")
    
    env.close()
    
    # Analysis
    print("\n" + "=" * 80)
    print(" Evaluation Results Summary")
    print("=" * 80)
    
    df = pd.DataFrame(results)
    
    # Overall statistics
    print(f"\n전체 통계 ({episodes} episodes × {len(SAMPLE_QUERIES)} queries):")
    print(f"  - 평균 Speedup: {df['speedup'].mean():.3f}x")
    print(f"  - 중앙값 Speedup: {df['speedup'].median():.3f}x")
    print(f"  - 최대 Speedup: {df['speedup'].max():.3f}x")
    print(f"  - 최소 Speedup: {df['speedup'].min():.3f}x")
    print(f"  - 표준편차: {df['speedup'].std():.3f}")
    print(f"  - 평균 개선: {df['improvement_pct'].mean():+.2f}%")
    print(f"  - 평균 Reward: {df['total_reward'].mean():.4f}")
    
    # Performance categories
    excellent = df[df['speedup'] >= 1.5]
    good = df[(df['speedup'] >= 1.2) & (df['speedup'] < 1.5)]
    neutral = df[(df['speedup'] >= 0.9) & (df['speedup'] < 1.2)]
    degraded = df[df['speedup'] < 0.9]
    
    print(f"\n성능 분포:")
    print(f"  - 탁월 (≥1.5x): {len(excellent)} ({len(excellent)/len(df)*100:.1f}%)")
    print(f"  - 양호 (1.2~1.5x): {len(good)} ({len(good)/len(df)*100:.1f}%)")
    print(f"  - 중립 (0.9~1.2x): {len(neutral)} ({len(neutral)/len(df)*100:.1f}%)")
    print(f"  - 저하 (<0.9x): {len(degraded)} ({len(degraded)/len(df)*100:.1f}%)")
    
    # Query-wise statistics
    print(f"\n쿼리별 평균 성능 (쿼리 이름 및 액션 포함):")
    print(f"{'='*120}")
    query_summary = []
    
    # 각 쿼리의 대표 액션 찾기 (첫 번째 에피소드에서)
    query_actions = {}
    for result in results:
        if result['episode'] == 1:
            query_actions[result['query_idx']] = result['best_action']
    
    for query_idx in range(len(SAMPLE_QUERIES)):
        query_speedups = query_results[query_idx]
        avg_speedup = np.mean(query_speedups)
        std_speedup = np.std(query_speedups)
        improvement_pct = (avg_speedup - 1.0) * 100
        
        query_summary.append({
            'query_idx': query_idx,
            'query_name': QUERY_NAMES.get(query_idx, f'Query {query_idx}'),
            'avg_speedup': avg_speedup,
            'std_speedup': std_speedup,
            'improvement_pct': improvement_pct,
            'action': query_actions.get(query_idx, 'NO_ACTION')
        })
        
        query_name = QUERY_NAMES.get(query_idx, f'Query {query_idx}')
        action_str = query_actions.get(query_idx, None)
        
        # 성능 아이콘
        if avg_speedup >= 2.0:
            icon = '🚀'
        elif avg_speedup >= 1.2:
            icon = '✅'
        elif avg_speedup >= 0.9:
            icon = '  '
        else:
            icon = '⚠️'
        
        print(f"{icon} Query {query_idx:2d} [{query_name[:35]:35s}]: "
              f"{avg_speedup:6.3f}x ± {std_speedup:.3f} ({improvement_pct:+6.1f}%)")
        
        if action_str and action_str != 'NO_ACTION':
            # 액션 문자열 줄바꿈 처리
            if len(action_str) > 100:
                print(f"           Action: {action_str[:100]}...")
                print(f"                   {action_str[100:]}")
            else:
                print(f"           Action: {action_str}")
    
    print(f"{'='*120}")
    
    # Top 5 best queries
    print(f"\n상위 5개 쿼리 (평균 Speedup):")
    top_queries = sorted(query_summary, key=lambda x: x['avg_speedup'], reverse=True)[:5]
    for i, q in enumerate(top_queries, 1):
        query_name = q['query_name']
        action_str = q['action'] if q['action'] and q['action'] != 'NO_ACTION' else 'NO_ACTION'
        print(f"  {i}. Query {q['query_idx']:2d} [{query_name[:30]:30s}]: {q['avg_speedup']:.3f}x ({q['improvement_pct']:+.1f}%)")
        if action_str != 'NO_ACTION':
            print(f"      → {action_str}")
    
    # Top 5 worst queries
    print(f"\n하위 5개 쿼리 (평균 Speedup):")
    worst_queries = sorted(query_summary, key=lambda x: x['avg_speedup'])[:5]
    for i, q in enumerate(worst_queries, 1):
        query_name = q['query_name']
        action_str = q['action'] if q['action'] and q['action'] != 'NO_ACTION' else 'NO_ACTION'
        print(f"  {i}. Query {q['query_idx']:2d} [{query_name[:30]:30s}]: {q['avg_speedup']:.3f}x ({q['improvement_pct']:+.1f}%)")
    
    # 액션이 적용된 쿼리 요약
    print(f"\n액션이 적용된 쿼리 요약:")
    action_applied = [q for q in query_summary if q['action'] and q['action'] != 'NO_ACTION']
    if action_applied:
        print(f"총 {len(action_applied)}개 쿼리에 최적화 적용:")
        for q in sorted(action_applied, key=lambda x: x['avg_speedup'], reverse=True):
            print(f"  • Query {q['query_idx']:2d} [{q['query_name'][:30]:30s}]: {q['avg_speedup']:.3f}x")
            print(f"    → {q['action']}")
    else:
        print(f"  (액션이 적용된 쿼리 없음)")
    
    # Save results
    if output_file:
        # 절대 경로로 변환 (상대 경로 입력 시 현재 디렉토리 기준)
        output_file = os.path.abspath(output_file)
        
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'model_path': model_path,
            'episodes': episodes,
            'overall': {
                'mean_speedup': float(df['speedup'].mean()),
                'median_speedup': float(df['speedup'].median()),
                'max_speedup': float(df['speedup'].max()),
                'min_speedup': float(df['speedup'].min()),
                'std_speedup': float(df['speedup'].std()),
                'mean_improvement_pct': float(df['improvement_pct'].mean())
            },
            'distribution': {
                'excellent': len(excellent),
                'good': len(good),
                'neutral': len(neutral),
                'degraded': len(degraded)
            },
            'query_summary': query_summary,
            'detailed_results': results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Results saved to: {output_file}")
    
    print("\n" + "=" * 80)
    print(" Evaluation Complete")
    print("=" * 80)
    
    return df


def main():
    parser = argparse.ArgumentParser(description='DDPG v1 Model Evaluation')
    parser.add_argument(
        '--model',
        type=str,
        default='Apollo.ML/artifacts/RLQO/models/ddpg_v1_realdb_50k.zip',
        help='Path to trained model'
    )
    parser.add_argument(
        '--episodes',
        type=int,
        default=3,
        help='Number of evaluation episodes'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file path (JSON)'
    )
    
    args = parser.parse_args()
    
    # Default output file
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"ddpg_v1_eval_{timestamp}.json"
    
    evaluate_ddpg(args.model, args.episodes, args.output)


if __name__ == '__main__':
    main()

