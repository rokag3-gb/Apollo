import json
import re
import os
import sys

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..'))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))

sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)

# 결과 로드
results_path = os.path.join(current_dir, 'results', 'ensemble_v2_results.json')
with open(results_path, 'r') as f:
    data = json.load(f)

# 쿼리 이름 추출 (constants2.py에서)
query_names = {}
constants_path = os.path.join(rlqo_dir, 'constants2.py')
with open(constants_path, 'r', encoding='utf-8') as f:
    content = f.read()
    # [인덱스 N] 쿼리 이름 패턴
    pattern = r'\[인덱스 (\d+)\]\s*([^\(]+)'
    matches = re.findall(pattern, content)
    for idx, name in matches:
        query_names[int(idx)] = name.strip()

# 쿼리 타입 매핑
from RLQO.PPO_v3.config.query_action_mapping_v3 import QUERY_TYPES

# 쿼리 요약 출력
print("=" * 120)
print(f"{'Idx':<4} {'Query Name':<50} {'Type':<12} {'Baseline':<10} {'Mean':<8} {'Win%':<7} {'Safe%':<7} {'Episodes':<8}")
print("=" * 120)

for q_summary in data['query_summaries']:
    idx = q_summary['query_idx']
    name = query_names.get(idx, f"Query {idx}")
    qtype = QUERY_TYPES.get(idx, 'UNKNOWN')
    baseline = q_summary['baseline_ms']
    mean_speedup = q_summary['mean_speedup']
    win_rate = q_summary['win_rate']
    safe_rate = q_summary['safe_rate']
    episodes = q_summary['episodes']
    
    # 성능 표시
    if mean_speedup > 1.05:
        perf_icon = "✓"
    elif mean_speedup < 0.95:
        perf_icon = "✗"
    else:
        perf_icon = "="
    
    print(f"{idx:<4} {name[:48]:<50} {qtype:<12} {baseline:>8.0f}ms {mean_speedup:>7.3f}x {win_rate*100:>6.1f}% {safe_rate*100:>6.1f}% {episodes:<8} {perf_icon}")

# 타입별 요약
print("\n" + "=" * 120)
print("쿼리 타입별 요약")
print("=" * 120)
print(f"{'Type':<15} {'Episodes':<10} {'Mean Speedup':<15} {'Win Rate':<12} {'Safe Rate':<12}")
print("-" * 120)

for qtype, stats in sorted(data['overall']['by_query_type'].items()):
    episodes = stats['episodes']
    mean_speedup = stats['mean_speedup']
    win_rate = stats['win_rate']
    safe_rate = stats['safe_rate']
    
    print(f"{qtype:<15} {episodes:<10} {mean_speedup:<15.3f} {win_rate*100:<11.1f}% {safe_rate*100:<11.1f}%")

# 전체 요약
print("\n" + "=" * 120)
print("전체 요약")
print("=" * 120)
overall = data['overall']
print(f"Total Episodes: {overall['total_episodes']}")
print(f"Mean Speedup: {overall['mean_speedup']:.3f}x")
print(f"Median Speedup: {overall['median_speedup']:.3f}x")
print(f"Win Rate: {overall['win_rate']*100:.1f}%")
print(f"Safe Rate: {overall['safe_rate']*100:.1f}%")

# 성능 개선/저하 쿼리 분석
print("\n" + "=" * 120)
print("성능 분석")
print("=" * 120)

improved = [q for q in data['query_summaries'] if q['mean_speedup'] > 1.05]
degraded = [q for q in data['query_summaries'] if q['mean_speedup'] < 0.95]
unchanged = [q for q in data['query_summaries'] if 0.95 <= q['mean_speedup'] <= 1.05]

print(f"개선 (>1.05x): {len(improved)}/{len(data['query_summaries'])} queries")
print(f"저하 (<0.95x): {len(degraded)}/{len(data['query_summaries'])} queries")
print(f"불변 (0.95-1.05x): {len(unchanged)}/{len(data['query_summaries'])} queries")

if improved:
    print(f"\nTop 5 개선 쿼리:")
    for q in sorted(improved, key=lambda x: x['mean_speedup'], reverse=True)[:5]:
        idx = q['query_idx']
        name = query_names.get(idx, f"Query {idx}")
        print(f"  {idx:2d}. {name[:45]:<45} {q['mean_speedup']:.3f}x (Baseline: {q['baseline_ms']:.0f}ms)")

if degraded:
    print(f"\nTop 5 저하 쿼리:")
    for q in sorted(degraded, key=lambda x: x['mean_speedup'])[:5]:
        idx = q['query_idx']
        name = query_names.get(idx, f"Query {idx}")
        print(f"  {idx:2d}. {name[:45]:<45} {q['mean_speedup']:.3f}x (Baseline: {q['baseline_ms']:.0f}ms)")

print("\n" + "=" * 120)

