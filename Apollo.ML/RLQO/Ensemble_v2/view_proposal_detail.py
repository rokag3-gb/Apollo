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

# colorama 사용 (Windows 호환)
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLOR_SUPPORT = True
except ImportError:
    # colorama가 없으면 색상 없이 출력
    COLOR_SUPPORT = False
    class Fore:
        RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = WHITE = RESET = ''
    class Back:
        BLACK = RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ''
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ''

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
    
    # 승인 상태만 색상
    status_color = Fore.GREEN if status == 'PENDING' else Fore.RED if status == 'REJECTED' else Fore.YELLOW
    print(f"  승인 상태:      {status_color + Style.BRIGHT + status + Style.RESET_ALL}")
    
    print(f"  신뢰도:         {confidence:.4f}")
    print(f"  비고:           {notes}")
    print()
    
    print("[ 성능 비교 상세 ]")
    print()
    print("=" * 100)
    print(f"{'메트릭':<25s} | {'Before (Baseline)':>20s} | {'After (Optimized)':>20s} | {'개선':>15s} | {'개선율':>10s}")
    print("=" * 100)
    
    # Elapsed Time
    elapsed_saved = baseline_elapsed - optimized_elapsed
    elapsed_pct = (elapsed_saved / baseline_elapsed * 100) if baseline_elapsed > 0 else 0
    if speedup > 1.05:
        elapsed_status = Fore.GREEN + Style.BRIGHT + "[OK] 개선" + Style.RESET_ALL
        status_color = Fore.GREEN
    elif speedup < 0.95:
        elapsed_status = Fore.RED + Style.BRIGHT + "[!!] 악화" + Style.RESET_ALL
        status_color = Fore.RED
    else:
        elapsed_status = "[--] 유지"
        status_color = ""
    
    print(f"{'Elapsed Time':<25s} | {baseline_elapsed:>17.2f} ms | {optimized_elapsed:>17.2f} ms | {elapsed_saved:>12.2f} ms | {elapsed_pct:>9.1f}%  {elapsed_status}")
    
    # CPU Time
    cpu_saved = baseline_cpu - optimized_cpu
    cpu_pct = (cpu_saved / baseline_cpu * 100) if baseline_cpu > 0 else 0
    if cpu_improvement > 1.05:
        cpu_status = Fore.GREEN + Style.BRIGHT + "[OK] 개선" + Style.RESET_ALL
    elif cpu_improvement < 0.95:
        cpu_status = Fore.RED + Style.BRIGHT + "[!!] 악화" + Style.RESET_ALL
    else:
        cpu_status = "[--] 유지"
        
    print(f"{'CPU Time':<25s} | {baseline_cpu:>17.2f} ms | {optimized_cpu:>17.2f} ms | {cpu_saved:>12.2f} ms | {cpu_pct:>9.1f}%  {cpu_status}")
    
    # Logical Reads
    reads_saved = baseline_reads - optimized_reads
    reads_pct = (reads_saved / baseline_reads * 100) if baseline_reads > 0 else 0
    if reads_improvement > 1.05:
        reads_status = Fore.GREEN + Style.BRIGHT + "[OK] 개선" + Style.RESET_ALL
    elif reads_improvement < 0.95:
        reads_status = Fore.RED + Style.BRIGHT + "[!!] 악화" + Style.RESET_ALL
    else:
        reads_status = "[--] 유지"
        
    print(f"{'Logical Reads':<25s} | {baseline_reads:>20,} | {optimized_reads:>20,} | {reads_saved:>15,} | {reads_pct:>9.1f}%  {reads_status}")
    
    print("=" * 100)
    print()
    
    # 요약
    print("[ 성능 개선 요약 ]")
    print(f"  실행 시간:     {baseline_elapsed:.2f}ms -> {optimized_elapsed:.2f}ms  (절약: {elapsed_saved:.2f}ms, {elapsed_pct:.1f}%)")
    print(f"  CPU 시간:      {baseline_cpu:.2f}ms -> {optimized_cpu:.2f}ms  (절약: {cpu_saved:.2f}ms, {cpu_pct:.1f}%)")
    print(f"  Logical Reads: {baseline_reads:,} -> {optimized_reads:,}  (절약: {reads_saved:,}, {reads_pct:.1f}%)")
    print(f"  전체 Speedup:  {status_color + Style.BRIGHT}{speedup:.4f}x{Style.RESET_ALL}")
    
    if speedup > 1.05:
        overall_status = Fore.GREEN + Style.BRIGHT + "[OK] 권장 (승인 검토)" + Style.RESET_ALL
    elif speedup < 0.95:
        overall_status = Fore.RED + Style.BRIGHT + "[!!] 권장하지 않음" + Style.RESET_ALL
    else:
        overall_status = "[--] 성능 차이 미미"
    print(f"  평가:          {overall_status}")
    print()
    
    print("=" * 100)
    print(Fore.CYAN + Style.BRIGHT + "[ 기존 쿼리 (Original Query) ]" + Style.RESET_ALL)
    print("=" * 100)
    print(original_query)
    print()
    
    print("=" * 100)
    print(Fore.MAGENTA + Style.BRIGHT + "[ 제안된 쿼리 (Optimized Query) ]" + Style.RESET_ALL)
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

