import json

# Load results
with open('results/ensemble_v2_results.json', 'r') as f:
    data = json.load(f)

results = data['detailed_results']

# Analyze slow queries
slow = [r for r in results if r['baseline_ms'] > 100]
print(f'Slow queries (>100ms): {len(slow)}/{len(results)} ({100*len(slow)/len(results):.1f}%)')

if slow:
    improvements = [r for r in slow if r['speedup'] > 1.0]
    degradations = [r for r in slow if r['speedup'] < 1.0]
    unchanged = len(slow) - len(improvements) - len(degradations)
    
    print(f'\nSlow query speedups:')
    print(f'  Improved: {len(improvements)} ({100*len(improvements)/len(slow):.1f}%)')
    print(f'  Degraded: {len(degradations)} ({100*len(degradations)/len(slow):.1f}%)')
    print(f'  Unchanged: {unchanged} ({100*unchanged/len(slow):.1f}%)')
    
    if improvements:
        print(f'\nTop 5 improvements:')
        for r in sorted(improvements, key=lambda x: x['speedup'], reverse=True)[:5]:
            print(f'  Query {r["query_idx"]}, Speedup: {r["speedup"]:.3f}x, Action: {r["action"]}, Baseline: {r["baseline_ms"]:.0f}ms → {r["optimized_ms"]:.0f}ms')
    
    if degradations:
        print(f'\nTop 5 degradations:')
        for r in sorted(degradations, key=lambda x: x['speedup'])[:5]:
            print(f'  Query {r["query_idx"]}, Speedup: {r["speedup"]:.3f}x, Action: {r["action"]}, Baseline: {r["baseline_ms"]:.0f}ms → {r["optimized_ms"]:.0f}ms')

# Analyze by action
print(f'\n' + '='*80)
print('Action effectiveness:')
print('='*80)

from collections import defaultdict

action_stats = defaultdict(lambda: {'count': 0, 'speedups': []})

for r in results:
    action = r['action']
    speedup = r['speedup']
    action_stats[action]['count'] += 1
    action_stats[action]['speedups'].append(speedup)

action_names = {
    0: 'MAXDOP_1',
    2: 'MAXDOP_8',
    3: 'HASH_JOIN',
    4: 'LOOP_JOIN',
    6: 'FORCE_ORDER',
    9: 'COMPAT_140',
    15: 'FAST_50',
    16: 'FAST_100',
    18: 'NO_ACTION'
}

for action_id in sorted(action_stats.keys()):
    stats = action_stats[action_id]
    name = action_names.get(action_id, f'Action_{action_id}')
    mean_speedup = sum(stats['speedups']) / len(stats['speedups'])
    improvements = sum(1 for s in stats['speedups'] if s > 1.0)
    
    print(f'{name:15s}: {stats["count"]:3d} times, Mean: {mean_speedup:.3f}x, Improved: {improvements}/{stats["count"]} ({100*improvements/stats["count"]:.1f}%)')

