# -*- coding: utf-8 -*-
"""
4개 모델의 평가 보고서에서 30개 쿼리별 성능 추출
"""

import re
import numpy as np
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
rlqo_dir = os.path.abspath(os.path.join(script_dir, '..'))

# 30개 쿼리 초기화 (모두 1.0x = 개선 없음)
def init_speedups():
    return {i: 1.0 for i in range(30)}

# DQN v4 데이터 추출
def extract_dqn_v4():
    file_path = os.path.join(rlqo_dir, 'DQN_v4', 'DQN_v4_Evaluation_Report.md')
    speedups = init_speedups()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 상세 테이블 찾기 (라인 300 근처)
    for line in lines[290:340]:
        # | 0 | 26.0 | 865.0 | 0.03x | -3227% | ...
        match = re.match(r'\|\s*(\d+)\s*\|.*\|\s*([\d.]+)x\s*\|', line)
        if match:
            query_id = int(match.group(1))
            speedup = float(match.group(2))
            if 'inf' in line or '∞' in line:
                speedup = 100.0  # 0ms 쿼리는 100x로 처리
            speedups[query_id] = speedup
    
    return speedups

# PPO v3 데이터 추출
def extract_ppo_v3():
    file_path = os.path.join(rlqo_dir, 'PPO_v3', 'PPO_v3_Evaluation_Report.md')
    speedups = init_speedups()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Top 10 쿼리 찾기
    # | 1 | **Query 1** | 거래소별... | CTE | **4.102x** | ±13.399 |
    pattern = r'\|\s*\d+\s*\|\s*\*?\*?Query (\d+)\*?\*?\s*\|[^|]*\|[^|]*\|\s*\*?\*?([\d.]+)x\*?\*?'
    matches = re.findall(pattern, content)
    
    for match in matches:
        query_id = int(match[0])
        speedup = float(match[1])
        speedups[query_id] = speedup
    
    return speedups

# DDPG v1 데이터 추출
def extract_ddpg_v1():
    file_path = os.path.join(rlqo_dir, 'DDPG_v1', 'DDPG_v1_Evaluation_Report.md')
    speedups = init_speedups()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Top 5 RealDB 쿼리 찾기
    # | 🥇 1 | **Query 2** | 대용량 테이블 전체 스캔 | **17.823x** | **+1682%** |
    pattern = r'\|\s*[🥇🥈🥉\d\s]+\|\s*\*?\*?Query (\d+)\*?\*?\s*\|[^|]*\|\s*\*?\*?([\d.]+)x\*?\*?'
    matches = re.findall(pattern, content)
    
    for match in matches:
        query_id = int(match[0])
        speedup = float(match[1])
        speedups[query_id] = speedup
    
    return speedups

# SAC v1 데이터 추출
def extract_sac_v1():
    file_path = os.path.join(rlqo_dir, 'SAC_v1', 'SAC_v1_Evaluation_Report.md')
    speedups = init_speedups()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Top 5 쿼리 찾기
    # | 🥇 1 | **Query 2** | 대용량 테이블 전체 스캔 | **22.140x** | **28.45x** | **+2114%** |
    pattern = r'\|\s*[🥇🥈🥉\d\s]+\|\s*\*?\*?Query (\d+)\*?\*?\s*\|[^|]*\|\s*\*?\*?([\d.]+)x\*?\*?'
    matches = re.findall(pattern, content)
    
    for match in matches:
        query_id = int(match[0])
        speedup = float(match[1])
        speedups[query_id] = speedup
    
    # 테이블에서 추가 데이터 찾기
    # | 6 | | RAND() 함수 | 1.015x | 1.46x | 0.083 | 3% | (희귀 적용) |
    pattern2 = r'\|\s*(\d+)\s*\|[^|]*\|\s*([\d.]+)x\s*\|'
    matches2 = re.findall(pattern2, content)
    
    for match in matches2:
        query_id = int(match[0])
        speedup = float(match[1])
        if speedup > 1.0:
            speedups[query_id] = speedup
    
    return speedups

# 데이터 추출
print("[INFO] Extracting performance data from evaluation reports...")
print("")

dqn_v4 = extract_dqn_v4()
ppo_v3 = extract_ppo_v3()
ddpg_v1 = extract_ddpg_v1()
sac_v1 = extract_sac_v1()

# 통계 출력
for model_name, speedups in [('DQN v4', dqn_v4), ('PPO v3', ppo_v3), 
                               ('DDPG v1', ddpg_v1), ('SAC v1', sac_v1)]:
    improvements = [(s - 1.0) * 100 for s in speedups.values()]
    positive = sum(1 for s in speedups.values() if s > 1.0)
    
    print(f"{model_name}:")
    print(f"  Improved Queries: {positive}/30")
    print(f"  Mean Speedup: {np.mean(list(speedups.values())):.3f}x")
    print(f"  Max Speedup: {max(speedups.values()):.1f}x")
    print(f"  Win Rate: {positive/30*100:.1f}%")
    print("")

# 데이터 저장
import json
output = {
    'dqn_v4': dqn_v4,
    'ppo_v3': ppo_v3,
    'ddpg_v1': ddpg_v1,
    'sac_v1': sac_v1
}

output_path = os.path.join(script_dir, 'results', 'model_performance_data.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2)

print(f"[SUCCESS] Data saved: {output_path}")

