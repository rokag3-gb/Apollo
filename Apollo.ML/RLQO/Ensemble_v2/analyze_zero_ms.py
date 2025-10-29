import json

with open('results/ensemble_v2_results.json', 'r') as f:
    data = json.load(f)

results = data['detailed_results']

# optimized_ms = 0인 케이스 찾기
zero_results = [r for r in results if r['optimized_ms'] == 0]

print(f"Zero optimized_ms cases: {len(zero_results)}/{len(results)} ({100*len(zero_results)/len(results):.1f}%)")

if zero_results:
    print("\nFirst 20 zero cases:")
    for i, r in enumerate(zero_results[:20], 1):
        print(f"  {i}. Query {r['query_idx']}, Episode {r['episode']}, Action {r['action']}, Baseline {r['baseline_ms']}ms")
    
    # Action 분포
    from collections import Counter
    action_counts = Counter([r['action'] for r in zero_results])
    print(f"\nActions causing 0ms:")
    for action, count in action_counts.most_common():
        print(f"  Action {action}: {count} times ({100*count/len(zero_results):.1f}%)")
    
    # Query 분포
    query_counts = Counter([r['query_idx'] for r in zero_results])
    print(f"\nQueries with 0ms:")
    for query, count in query_counts.most_common(10):
        print(f"  Query {query}: {count} times")

