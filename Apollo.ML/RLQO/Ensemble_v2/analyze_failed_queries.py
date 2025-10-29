import json

with open('results/ensemble_v2_results.json', 'r') as f:
    data = json.load(f)

results = data['detailed_results']

# 0ms 결과만 필터링
zero_results = [r for r in results if r['optimized_ms'] == 0]

# 쿼리별 분석
print("="*80)
print("쿼리별 실패 분석 (optimized_ms = 0)")
print("="*80)

# 10번 모두 실패한 쿼리들
problem_queries = [11, 12, 15, 23, 26, 29]

for q in problem_queries:
    q_results = [r for r in results if r['query_idx'] == q]
    q_zeros = [r for r in zero_results if r['query_idx'] == q]
    
    print(f"\n[Query {q}]")
    print(f"  Total episodes: {len(q_results)}")
    print(f"  Failed (0ms): {len(q_zeros)} ({100*len(q_zeros)/len(q_results):.0f}%)")
    
    if q_zeros:
        # 액션 분포
        from collections import Counter
        actions = Counter([r['action'] for r in q_zeros])
        print(f"  Failed actions: {dict(actions)}")
        
        # 샘플 출력
        print(f"  Sample cases:")
        for r in q_zeros[:3]:
            print(f"    Episode {r['episode']}: Action {r['action']}, Baseline {r['baseline_ms']:.0f}ms → 0ms")

# Query 8 특별 분석
print("\n" + "="*80)
print("[Query 8] - 데이터 없는 쿼리")
print("="*80)
q8_results = [r for r in results if r['query_idx'] == 8]
q8_zeros = [r for r in zero_results if r['query_idx'] == 8]

print(f"Total episodes: {len(q8_results)}")
print(f"Failed (0ms): {len(q8_zeros)} ({100*len(q8_zeros)/len(q8_results):.0f}%)")

# 성공한 케이스 확인
q8_success = [r for r in q8_results if r['optimized_ms'] > 0]
print(f"Success cases: {len(q8_success)}")
if q8_success:
    print("Success details:")
    for r in q8_success:
        print(f"  Episode {r['episode']}: Action {r['action']}, Baseline {r['baseline_ms']:.0f}ms → {r['optimized_ms']:.0f}ms")

# Baseline이 0인 경우도 확인
print("\n" + "="*80)
print("Baseline = 0인 케이스")
print("="*80)
baseline_zeros = [r for r in results if r['baseline_ms'] == 0]
print(f"Total: {len(baseline_zeros)}")
if baseline_zeros:
    for r in baseline_zeros[:5]:
        print(f"  Query {r['query_idx']}, Episode {r['episode']}: Baseline 0ms → {r['optimized_ms']:.0f}ms")

