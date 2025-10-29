import json

# Load results
with open('results/ensemble_v2_results.json', 'r') as f:
    data = json.load(f)

# Check first 10 results
print("First 10 results:")
print("="*80)
for i, result in enumerate(data['detailed_results'][:10]):
    print(f"\nResult {i}:")
    print(f"  Query {result['query_idx']}, Episode {result['episode']}")
    print(f"  Baseline: {result['baseline_ms']}ms")
    print(f"  Optimized: {result['optimized_ms']}ms")
    print(f"  Speedup: {result['speedup']:.3f}x")
    print(f"  Action: {result['action']}")
    
# Check if optimized_ms is always 1.0 for certain queries
print("\n" + "="*80)
print("Checking optimized_ms values:")
print("="*80)

optimized_values = {}
for result in data['detailed_results'][:50]:
    opt = result['optimized_ms']
    if opt not in optimized_values:
        optimized_values[opt] = 0
    optimized_values[opt] += 1

print(f"Unique optimized_ms values (first 50 results):")
for value in sorted(optimized_values.keys())[:20]:
    print(f"  {value}ms: {optimized_values[value]} times")

# Check specific problematic queries
print("\n" + "="*80)
print("Query 0 all episodes:")
print("="*80)
query_0_results = [r for r in data['detailed_results'] if r['query_idx'] == 0]
for r in query_0_results[:5]:
    print(f"  Episode {r['episode']}: Baseline {r['baseline_ms']}ms → Optimized {r['optimized_ms']}ms (Speedup: {r['speedup']:.3f}x)")

