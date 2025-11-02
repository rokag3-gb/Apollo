# -*- coding: utf-8 -*-
"""
rlqo_optimization_proposals 테이블에서 특정 제안의 상세 정보 조회
기존 쿼리와 제안된 쿼리를 CRLF 포함하여 출력
"""

import os
import sys

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))

sys.path.insert(0, apollo_ml_dir)

from db import connect
from config import load_config

def view_proposal(proposal_id=None):
    """특정 proposal_id의 상세 정보 조회"""
    
    # DB 연결
    config_path = os.path.join(apollo_ml_dir, 'config.yaml')
    config = load_config(config_path)
    
    print("DB에 연결 중...")
    try:
        conn = connect(config.db)
        print("[OK] DB 연결 성공\n")
    except Exception as e:
        print(f"[ERROR] DB 연결 실패: {e}")
        sys.exit(1)
    
    cursor = conn.cursor()
    
    # proposal_id가 없으면 최고 성능 개선 쿼리 선택
    if proposal_id is None:
        cursor.execute("""
            SELECT TOP 1 proposal_id
            FROM dbo.rlqo_optimization_proposals
            WHERE model_name = 'Ensemble_v2_Oracle'
              AND approval_status = 'PENDING'
            ORDER BY speedup_ratio DESC
        """)
        row = cursor.fetchone()
        if row:
            proposal_id = row[0]
        else:
            print("[ERROR] 조회할 제안이 없습니다.")
            cursor.close()
            conn.close()
            return
    
    # 기본 정보 조회
    cursor.execute("""
        SELECT 
            proposal_id,
            model_name,
            query_type,
            speedup_ratio,
            baseline_elapsed_time_ms,
            baseline_cpu_time_ms,
            baseline_logical_reads,
            optimized_elapsed_time_ms,
            optimized_cpu_time_ms,
            optimized_logical_reads,
            cpu_improvement_ratio,
            reads_improvement_ratio,
            confidence_score,
            approval_status,
            notes,
            proposal_datetime,
            original_query_text,
            optimized_query_text
        FROM dbo.rlqo_optimization_proposals
        WHERE proposal_id = ?
    """, proposal_id)
    
    row = cursor.fetchone()
    if not row:
        print(f"[ERROR] proposal_id={proposal_id}를 찾을 수 없습니다.")
        cursor.close()
        conn.close()
        return
    
    # 결과 파싱
    (pid, model_name, query_type, speedup, 
     baseline_elapsed, baseline_cpu, baseline_reads,
     optimized_elapsed, optimized_cpu, optimized_reads,
     cpu_improvement, reads_improvement, confidence, status, notes, proposal_dt,
     original_query, optimized_query) = row
    
    # 출력
    print("=" * 100)
    print(f"제안 ID: {pid}")
    print("=" * 100)
    print()
    
    print("[ 기본 정보 ]")
    print(f"  모델명:         {model_name}")
    print(f"  쿼리 타입:      {query_type}")
    print(f"  제안 일시:      {proposal_dt}")
    print(f"  승인 상태:      {status}")
    print(f"  신뢰도:         {confidence:.4f}")
    print(f"  비고:           {notes}")
    print()
    
    print("[ 성능 비교 ]")
    print(f"  {'메트릭':<20s} | {'Baseline':>15s} | {'Optimized':>15s} | {'개선율':>10s}")
    print("-" * 70)
    print(f"  {'Elapsed Time (ms)':<20s} | {baseline_elapsed:>15.2f} | {optimized_elapsed:>15.2f} | {speedup:>9.4f}x")
    print(f"  {'CPU Time (ms)':<20s} | {baseline_cpu:>15.2f} | {optimized_cpu:>15.2f} | {cpu_improvement:>9.4f}x")
    print(f"  {'Logical Reads':<20s} | {baseline_reads:>15,} | {optimized_reads:>15,} | {reads_improvement:>9.4f}x")
    print()
    
    saved_time = baseline_elapsed - optimized_elapsed
    saved_pct = (saved_time / baseline_elapsed * 100) if baseline_elapsed > 0 else 0
    print(f"  ▶ 시간 절약: {saved_time:.2f}ms ({saved_pct:.1f}% 개선)")
    print()
    
    print("=" * 100)
    print("[ 기존 쿼리 (Original Query) ]")
    print("=" * 100)
    print(original_query)
    print()
    
    print("=" * 100)
    print("[ 제안된 쿼리 (Optimized Query) ]")
    print("=" * 100)
    print(optimized_query)
    print()
    
    print("=" * 100)
    
    cursor.close()
    conn.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='RLQO 최적화 제안 상세 조회')
    parser.add_argument('--id', type=int, help='조회할 proposal_id (생략 시 최고 성능 개선 쿼리 조회)')
    
    args = parser.parse_args()
    
    view_proposal(args.id)

