"""
쿼리 23번만 선택적으로 캐시 재수집
"""
import os
import sys
import pickle
import json
import re
from pathlib import Path
from statistics import median

# Apollo.ML 디렉터리를 sys.path에 추가
script_dir = Path(__file__).resolve().parent
apollo_ml_dir = script_dir.parent.parent
sys.path.insert(0, str(apollo_ml_dir))

from RLQO.constants2 import SAMPLE_QUERIES
from RLQO.DQN_v3.env.v3_db_env import apply_action_to_sql
from RLQO.DQN_v1.features.phase2_features import extract_features
from db import connect, get_execution_plan, get_query_statistics
from config import load_config
import numpy as np

def load_cache():
    """기존 캐시 로드"""
    cache_path = apollo_ml_dir / 'artifacts' / 'RLQO' / 'cache' / 'v3_plan_cache_ppo.pkl'
    if cache_path.exists():
        with open(cache_path, 'rb') as f:
            return pickle.load(f)
    return {}

def save_cache(cache):
    """캐시 저장"""
    cache_path = apollo_ml_dir / 'artifacts' / 'RLQO' / 'cache' / 'v3_plan_cache_ppo.pkl'
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, 'wb') as f:
        pickle.dump(cache, f)
    print(f"\n[OK] 캐시 저장 완료: {cache_path}")

def parse_statistics(stats_io: str, stats_time: str) -> dict:
    """통계 파싱"""
    metrics = {}
    
    logical_reads = sum(map(int, re.findall(r'logical reads (\d+)', stats_io)))
    metrics['logical_reads'] = logical_reads
    
    cpu_time_ms = 0.0
    elapsed_time_ms = 0.0
    
    execution_times_block = stats_time
    execution_times_match = re.search(r'SQL Server Execution Times:(.*)', stats_time, re.DOTALL)
    if execution_times_match:
        execution_times_block = execution_times_match.group(1)
    
    cpu_match = re.search(r'CPU time = (\d+\.?\d*)\s*(ms|s)', execution_times_block)
    if cpu_match:
        value = float(cpu_match.group(1))
        unit = cpu_match.group(2)
        if unit == 's':
            cpu_time_ms = value * 1000
        else:
            cpu_time_ms = value
    
    elapsed_match = re.search(r'elapsed time = (\d+\.?\d*)\s*(ms|s)', execution_times_block)
    if elapsed_match:
        value = float(elapsed_match.group(1))
        unit = elapsed_match.group(2)
        if unit == 's':
            elapsed_time_ms = value * 1000
        else:
            elapsed_time_ms = value
            
    metrics['cpu_time_ms'] = cpu_time_ms
    metrics['elapsed_time_ms'] = round(elapsed_time_ms, 4)
    return metrics

def collect_query_with_retries(conn, sql, num_runs=5):
    """쿼리를 여러 번 실행하고 중위값 반환"""
    all_metrics = []
    plan_xml = None
    
    for i in range(num_runs):
        try:
            # 실행 계획 수집 (첫 번째 실행에서만)
            if i == 0:
                plan_xml = get_execution_plan(conn, sql)
            
            # 통계 수집
            stats_io, stats_time = get_query_statistics(conn, sql)
            
            if stats_io and stats_time:
                metrics = parse_statistics(stats_io, stats_time)
                all_metrics.append(metrics)
                print(f"  Run {i+1}/{num_runs}: {metrics['elapsed_time_ms']:.2f}ms")
            else:
                print(f"  Run {i+1}/{num_runs}: [FAIL] 통계 수집 실패")
        except Exception as e:
            print(f"  Run {i+1}/{num_runs}: [FAIL] {str(e)[:100]}")
    
    if not all_metrics:
        return None
    
    # 중위값 계산
    elapsed_times = [m['elapsed_time_ms'] for m in all_metrics]
    median_time = median(elapsed_times)
    
    # 중위값에 가장 가까운 결과 선택
    closest_idx = min(range(len(all_metrics)), key=lambda i: abs(all_metrics[i]['elapsed_time_ms'] - median_time))
    result_metrics = all_metrics[closest_idx]
    
    print(f"  중위값: {median_time:.2f}ms (선택된 결과: {result_metrics['elapsed_time_ms']:.2f}ms)")
    
    # 안전성을 위해 0 이하 값 방지
    result_metrics['elapsed_time_ms'] = max(0.1, result_metrics['elapsed_time_ms'])
    result_metrics['logical_reads'] = max(1, result_metrics['logical_reads'])
    result_metrics['cpu_time_ms'] = max(0.1, result_metrics['cpu_time_ms'])
    
    # 실행 계획에서 특징 추출 (79차원 observation)
    if plan_xml:
        try:
            observation = extract_features(plan_xml, result_metrics)
        except Exception as e:
            print(f"  [WARN] 특징 추출 실패: {e}")
            observation = np.zeros(79, dtype=np.float32)
    else:
        observation = np.zeros(79, dtype=np.float32)
    
    # 결과 구성 (v3_sim_env.py가 기대하는 형식)
    result = {
        'observation': observation,
        'metrics': result_metrics,
        'plan_xml': plan_xml,
        'runs': len(all_metrics)
    }
    
    return result

def main():
    print("=" * 80)
    print("쿼리 23번 캐시 재수집 시작")
    print("=" * 80)
    
    # DB 연결
    config_path = os.path.join(apollo_ml_dir, 'config.yaml')
    config = load_config(config_path)
    conn = connect(config.db)
    
    try:
        # 기존 캐시 로드
        print("\n[1/4] 기존 캐시 로드 중...")
        cache = load_cache()
        print(f"기존 캐시 항목 수: {len(cache)}")
        
        # 쿼리 23번 로드
        query_idx = 23
        base_sql = SAMPLE_QUERIES[query_idx]
        
        print(f"\n[2/4] 쿼리 23번 기본 실행 계획 수집 중...")
        print(f"쿼리:\n{base_sql[:200]}...")
        
        # 기본 쿼리 수집 (5번 실행 후 중위값)
        base_result = collect_query_with_retries(conn, base_sql, num_runs=5)
        if base_result:
            cache[base_sql.strip()] = base_result
            print(f"[OK] 기본 쿼리 수집 완료")
        else:
            print(f"[FAIL] 기본 쿼리 수집 실패")
        
        # 액션 적용된 쿼리들 수집
        print(f"\n[3/4] 쿼리 23번의 액션 적용 버전 수집 중...")
        
        # 액션 및 호환성 로드
        action_space_path = apollo_ml_dir / 'artifacts' / 'RLQO' / 'configs' / 'v3_action_space_ppo.json'
        compatibility_path = apollo_ml_dir / 'artifacts' / 'RLQO' / 'configs' / 'v3_query_action_compatibility_ppo.json'
        
        with open(action_space_path, 'r', encoding='utf-8') as f:
            actions_data = json.load(f)
        
        with open(compatibility_path, 'r', encoding='utf-8') as f:
            compatibility_data = json.load(f)
            compatibility_map = compatibility_data.get('compatibility', compatibility_data)
        
        # 쿼리 23번의 호환 액션 확인
        compatible_actions = compatibility_map.get(str(query_idx), [])
        
        print(f"호환 가능한 액션 수: {len(compatible_actions)}")
        
        collected_count = 0
        failed_count = 0
        
        for action_name in compatible_actions:
            # 액션 정보 찾기 (actions_data는 리스트임)
            action_info = next((a for a in actions_data if a['name'] == action_name), None)
            if not action_info:
                continue
            
            # 액션 타입에 따라 SQL 수정
            action_type = action_info.get('type')
            action_value = action_info.get('value')
            
            if action_type == "ISOLATION":
                # ISOLATION은 쿼리 앞에 배치
                modified_sql = f"{action_value}\n{base_sql}"
            elif action_type == "HINT":
                # HINT는 쿼리 끝 (세미콜론 전)에 배치
                modified_sql = apply_action_to_sql(base_sql, action_info)
            elif action_type == "TABLE_HINT":
                # TABLE_HINT는 apply_action_to_sql 사용
                modified_sql = apply_action_to_sql(base_sql, action_info)
            elif action_type == "BASELINE":
                # NO_ACTION
                modified_sql = base_sql
            else:
                # 기본: 쿼리 앞에 배치
                modified_sql = f"{action_value}\n{base_sql}"
            
            print(f"\n  액션: {action_name} (타입: {action_type})")
            result = collect_query_with_retries(conn, modified_sql, num_runs=5)
            
            if result:
                cache[modified_sql.strip()] = result
                collected_count += 1
                print(f"  [OK] 수집 완료")
            else:
                failed_count += 1
                print(f"  [FAIL] 수집 실패")
        
        # 캐시 저장
        print(f"\n[4/4] 캐시 저장 중...")
        print(f"{'=' * 80}")
        print(f"수집 완료: 성공 {collected_count + 1}개 (기본 쿼리 + {collected_count}개 액션), 실패 {failed_count}개")
        print(f"전체 캐시 항목 수: {len(cache)}")
        print(f"캐시 데이터 구조: observation (79d) + metrics + plan_xml")
        save_cache(cache)
        
        print("=" * 80)
        print("쿼리 23번 캐시 재수집 완료!")
        print("=" * 80)
    
    finally:
        conn.close()
        print("\nDB 연결 종료")

if __name__ == "__main__":
    main()

