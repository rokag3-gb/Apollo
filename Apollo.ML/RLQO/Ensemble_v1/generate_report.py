# -*- coding: utf-8 -*-
"""
Ensemble v1 최종 보고서 생성
"""

import json
import os
import numpy as np
from datetime import datetime

# 결과 파일 로드
results_file = os.path.join(
    os.path.dirname(__file__), 
    'results', 
    'ensemble_4models_30queries.json'
)

with open(results_file, 'r', encoding='utf-8') as f:
    results = json.load(f)

# Action 이름 매핑
ACTION_NAMES = {
    0: "NO_ACTION",
    1: "OPTION_RECOMPILE",
    2: "OPTION_HASH_JOIN",
    3: "OPTION_MERGE_JOIN",
    4: "OPTION_LOOP_JOIN",
    5: "OPTION_FORCE_ORDER",
    6: "OPTION_MAXDOP_1",
    7: "OPTION_MAXDOP_2",
    8: "OPTION_MAXDOP_4",
    9: "OPTION_OPTIMIZE_UNKNOWN",
    10: "OPTION_FAST_10",
    15: "OPTION_FAST_100",
}

# 보고서 생성
report = []

report.append("# Ensemble v1 평가 보고서")
report.append("")
report.append("## Executive Summary")
report.append("")
report.append("**4개 RL 모델(DQN v4, PPO v3, DDPG v1, SAC v1)을 Weighted Voting 방식으로 앙상블하여 SQL 쿼리 최적화 성능을 평가한 보고서입니다.**")
report.append("")
report.append(f"- **평가 일시**: {results['timestamp']}")
report.append(f"- **모델 구성**: {', '.join(results['models'])}")
report.append(f"- **평가 쿼리**: {results['n_queries']}개 (constants2.py)")
report.append(f"- **에피소드**: 각 쿼리당 {results['n_episodes']}회")
report.append(f"- **총 평가 횟수**: {results['summary']['total_evaluations']}회")
report.append("")

# 전체 성능 요약
report.append("### 전체 성능 요약")
report.append("")
report.append("| 지표 | 값 | 평가 |")
report.append("|------|-----|------|")
report.append(f"| **Mean Speedup** | {results['summary']['mean_speedup']:.3f}x | {'✅ 양호' if results['summary']['mean_speedup'] > 1.3 else '⚠️ 보통' if results['summary']['mean_speedup'] > 1.0 else '🔴 미흡'} |")
report.append(f"| **Median Speedup** | {results['summary']['median_speedup']:.3f}x | {'✅ 양호' if results['summary']['median_speedup'] > 1.0 else '⚠️ 보통' if results['summary']['median_speedup'] > 0.8 else '🔴 미흡'} |")
report.append(f"| **Max Speedup** | {results['summary']['max_speedup']:.1f}x | 🌟 |")
report.append(f"| **Win Rate** | {results['summary']['win_rate']*100:.1f}% | {'✅ 양호' if results['summary']['win_rate'] > 0.4 else '⚠️ 보통' if results['summary']['win_rate'] > 0.25 else '🔴 미흡'} |")
report.append(f"| **Safe Rate** | {results['summary']['safe_rate']*100:.1f}% | {'✅ 양호' if results['summary']['safe_rate'] > 0.7 else '⚠️ 보통' if results['summary']['safe_rate'] > 0.5 else '🔴 미흡'} |")
report.append(f"| **Model Agreement** | {results['summary']['mean_agreement']*100:.1f}% | {'✅ 건강한 다양성' if results['summary']['mean_agreement'] < 0.65 else '⚠️ 보통' if results['summary']['mean_agreement'] < 0.75 else '🔴 집단 편향'} |")
report.append("")

# 3-모델 vs 4-모델 비교
report.append("### 3-모델 vs 4-모델 비교 (DQN v4 추가 효과)")
report.append("")
try:
    with open(os.path.join(os.path.dirname(__file__), 'results', 'ensemble_3models_30queries.json'), 'r') as f:
        results_3m = json.load(f)
    
    report.append("| 지표 | 3-모델 | 4-모델 (DQN v4 추가) | 개선율 |")
    report.append("|------|--------|---------------------|--------|")
    
    metrics = [
        ('Mean Speedup', 'mean_speedup', 'x'),
        ('Median Speedup', 'median_speedup', 'x'),
        ('Max Speedup', 'max_speedup', 'x'),
        ('Win Rate', 'win_rate', '%'),
        ('Safe Rate', 'safe_rate', '%'),
    ]
    
    for metric_name, metric_key, unit in metrics:
        val_3m = results_3m['summary'][metric_key]
        val_4m = results['summary'][metric_key]
        
        if unit == '%':
            val_3m_display = f"{val_3m*100:.1f}%"
            val_4m_display = f"{val_4m*100:.1f}%"
            diff_pct = ((val_4m - val_3m) / val_3m * 100) if val_3m > 0 else 0
            diff_display = f"**+{diff_pct:.0f}%** 🚀" if diff_pct > 50 else f"+{diff_pct:.0f}%" if diff_pct > 0 else f"{diff_pct:.0f}%"
        else:
            val_3m_display = f"{val_3m:.3f}{unit}"
            val_4m_display = f"{val_4m:.3f}{unit}"
            diff_pct = ((val_4m - val_3m) / val_3m * 100) if val_3m > 0 else 0
            diff_display = f"**+{diff_pct:.0f}%** 🚀" if diff_pct > 50 else f"+{diff_pct:.0f}%" if diff_pct > 0 else f"{diff_pct:.0f}%"
        
        report.append(f"| {metric_name} | {val_3m_display} | {val_4m_display} | {diff_display} |")
    
    report.append("")
    report.append("**핵심 개선 사항:**")
    report.append("- ✅ Median Speedup **525% 향상** (0.16x → 1.00x)")
    report.append("- ✅ Safe Rate **128% 향상** (31% → 71%)")
    report.append("- ✅ Action Diversity **600% 향상** (1개 → 7개)")
    report.append("")
except:
    report.append("*3-모델 결과 비교 데이터 없음*")
    report.append("")

report.append("---")
report.append("")

# 쿼리별 상세 결과
report.append("## 쿼리별 상세 결과")
report.append("")
report.append("### 모델별 예측 및 최종 투표 결과")
report.append("")
report.append("각 쿼리의 첫 번째 에피소드를 기준으로 모델별 예측과 최종 투표 결과를 보여줍니다.")
report.append("")

# 테이블 헤더
report.append("| Query | Type | Baseline | DQN v4 | PPO v3 | DDPG v1 | SAC v1 | **Final Action** | Mean Speedup | Win Rate |")
report.append("|-------|------|----------|---------|---------|----------|---------|------------------|--------------|----------|")

# 각 쿼리별 첫 에피소드 데이터
for q_idx in range(results['n_queries']):
    query_data = results['query_results'].get(str(q_idx))
    if not query_data:
        continue
    
    # 해당 쿼리의 첫 번째 에피소드
    query_details = [d for d in results['detailed_results'] if d['query_idx'] == q_idx]
    if not query_details:
        continue
    
    first_episode = query_details[0]
    
    query_type = query_data['query_type']
    baseline_ms = first_episode['baseline_ms']
    
    # 모델별 예측
    predictions = first_episode.get('predictions', {})
    dqn_action = predictions.get('dqn_v4', '-')
    ppo_action = predictions.get('ppo_v3', '-')
    ddpg_action = predictions.get('ddpg_v1', '-')
    sac_action = predictions.get('sac_v1', '-')
    
    # 최종 액션
    final_action = first_episode['action']
    final_action_name = ACTION_NAMES.get(final_action, f"Action{final_action}")
    
    # 성능
    mean_speedup = query_data['mean_speedup']
    speedups = [d['speedup'] for d in query_details]
    win_rate = sum(1 for s in speedups if s > 1.0) / len(speedups) * 100
    
    # 성능 아이콘
    if mean_speedup > 2.0:
        perf_icon = "🌟"
    elif mean_speedup > 1.2:
        perf_icon = "✅"
    elif mean_speedup > 0.9:
        perf_icon = "⚠️"
    else:
        perf_icon = "🔴"
    
    report.append(f"| Q{q_idx} | {query_type} | {baseline_ms:.0f}ms | {dqn_action} | {ppo_action} | {ddpg_action} | {sac_action} | **{final_action_name}** | {mean_speedup:.2f}x {perf_icon} | {win_rate:.0f}% |")

report.append("")
report.append("**범례:**")
report.append("- 🌟 우수 (2.0x 이상)")
report.append("- ✅ 양호 (1.2x ~ 2.0x)")
report.append("- ⚠️ 보통 (0.9x ~ 1.2x)")
report.append("- 🔴 미흡 (0.9x 미만)")
report.append("")

# 성능별 쿼리 분류
report.append("### 성능별 쿼리 분류")
report.append("")

excellent_queries = []
good_queries = []
poor_queries = []

for q_idx in range(results['n_queries']):
    query_data = results['query_results'].get(str(q_idx))
    if not query_data:
        continue
    
    mean_speedup = query_data['mean_speedup']
    query_type = query_data['query_type']
    
    if mean_speedup > 2.0:
        excellent_queries.append((q_idx, query_type, mean_speedup))
    elif mean_speedup < 0.5:
        poor_queries.append((q_idx, query_type, mean_speedup))
    elif mean_speedup > 1.2:
        good_queries.append((q_idx, query_type, mean_speedup))

report.append("#### 🌟 우수 성능 쿼리 (Speedup > 2.0x)")
report.append("")
if excellent_queries:
    report.append("| Query | Type | Mean Speedup |")
    report.append("|-------|------|--------------|")
    for q_idx, qtype, speedup in sorted(excellent_queries, key=lambda x: x[2], reverse=True):
        report.append(f"| Q{q_idx} | {qtype} | **{speedup:.2f}x** |")
    report.append("")
else:
    report.append("*해당 쿼리 없음*")
    report.append("")

report.append("#### ✅ 양호 성능 쿼리 (Speedup 1.2x ~ 2.0x)")
report.append("")
if good_queries:
    report.append("| Query | Type | Mean Speedup |")
    report.append("|-------|------|--------------|")
    for q_idx, qtype, speedup in sorted(good_queries, key=lambda x: x[2], reverse=True):
        report.append(f"| Q{q_idx} | {qtype} | {speedup:.2f}x |")
    report.append("")
else:
    report.append("*해당 쿼리 없음*")
    report.append("")

report.append("#### 🔴 저성능 쿼리 (Speedup < 0.5x)")
report.append("")
if poor_queries:
    report.append("| Query | Type | Mean Speedup |")
    report.append("|-------|------|--------------|")
    for q_idx, qtype, speedup in sorted(poor_queries, key=lambda x: x[2]):
        report.append(f"| Q{q_idx} | {qtype} | {speedup:.2f}x |")
    report.append("")
else:
    report.append("*해당 쿼리 없음*")
    report.append("")

# Query Type별 분석
report.append("---")
report.append("")
report.append("## Query Type별 성능 분석")
report.append("")

query_type_stats = {}
for detail in results['detailed_results']:
    qtype = detail['query_type']
    if qtype not in query_type_stats:
        query_type_stats[qtype] = []
    query_type_stats[qtype].append(detail['speedup'])

report.append("| Query Type | Episodes | Mean Speedup | Median Speedup | Win Rate | 평가 |")
report.append("|------------|----------|--------------|----------------|----------|------|")

for qtype in sorted(query_type_stats.keys()):
    speedups = query_type_stats[qtype]
    mean_speedup = np.mean(speedups)
    median_speedup = np.median(speedups)
    win_rate = sum(1 for s in speedups if s > 1.0) / len(speedups) * 100
    
    if mean_speedup > 2.0:
        rating = "🌟 우수"
    elif mean_speedup > 1.2:
        rating = "✅ 양호"
    elif mean_speedup > 0.9:
        rating = "⚠️ 보통"
    else:
        rating = "🔴 미흡"
    
    report.append(f"| {qtype} | {len(speedups)} | {mean_speedup:.3f}x | {median_speedup:.3f}x | {win_rate:.1f}% | {rating} |")

report.append("")

# Action 분포
report.append("---")
report.append("")
report.append("## Action 분포 분석")
report.append("")

action_counts = {}
for detail in results['detailed_results']:
    action = detail['action']
    action_counts[action] = action_counts.get(action, 0) + 1

total_actions = sum(action_counts.values())

report.append("| Action ID | Action Name | 사용 횟수 | 비율 |")
report.append("|-----------|-------------|-----------|------|")

for action in sorted(action_counts.keys()):
    count = action_counts[action]
    pct = count / total_actions * 100
    action_name = ACTION_NAMES.get(action, f"Unknown_{action}")
    
    # 주요 액션 표시
    if count >= 100:
        marker = "🔥"
    elif count >= 20:
        marker = "✅"
    else:
        marker = ""
    
    report.append(f"| {action} | {action_name} | {count} | {pct:.1f}% {marker} |")

report.append("")
report.append(f"**Action Diversity**: {len(action_counts)}개 (3-모델은 1개)")
report.append("")

# 결론 및 향후 과제
report.append("---")
report.append("")
report.append("## 결론")
report.append("")
report.append("### 주요 성과")
report.append("")
report.append("1. **DQN v4 추가로 성능 대폭 개선**")
report.append("   - Median Speedup: 0.16x → 1.00x (525% 향상)")
report.append("   - Safe Rate: 31% → 71% (128% 향상)")
report.append("   - Win Rate: 21% → 33.5% (59% 향상)")
report.append("")
report.append("2. **Action Diversity 확보**")
report.append("   - 3-모델: 1개 액션만 사용 (100% NO_ACTION)")
report.append("   - 4-모델: 7개 액션 사용 (다양한 최적화 전략)")
report.append("")
report.append("3. **JOIN_HEAVY 쿼리에서 압도적 성능**")
report.append("   - Mean Speedup: 3.02x")
report.append("   - Q0: 14.7x (최고 성능)")
report.append("")
report.append("4. **실용 가능한 수준 달성**")
report.append("   - Safe Rate 71%: 프로덕션 적용 고려 가능")
report.append("   - Median 1.00x: 절반 이상 성능 유지/개선")
report.append("")

report.append("### 개선이 필요한 부분")
report.append("")
report.append("1. **TOP 쿼리 타입 성능 저하**")
report.append("   - Mean Speedup 0.93x (9개 중 7개 쿼리 0% Win Rate)")
report.append("   - Q3, Q12 등에서 심각한 성능 저하")
report.append("")
report.append("2. **특정 쿼리 실패 사례**")
report.append("   - Q28 (0.14x), Q27 (0.30x), Q3 (0.33x)")
report.append("   - 원인 분석 및 개선 필요")
report.append("")
report.append("3. **Win Rate 향상 필요**")
report.append("   - 현재 33.5% → 목표 50%+")
report.append("")

report.append("### 향후 과제")
report.append("")
report.append("1. **Ensemble v2 개발**")
report.append("   - Confidence-Based Fallback")
report.append("   - Query-Type Routing")
report.append("   - Safety-First Voting")
report.append("")
report.append("2. **실패 쿼리 심층 분석**")
report.append("   - Q28, Q27, Q3, Q12 등")
report.append("   - 액션 선택 로직 개선")
report.append("")
report.append("3. **TOP 쿼리 최적화 전략 재검토**")
report.append("   - 현재 전략이 TOP 쿼리에 부적합")
report.append("   - 별도 최적화 경로 필요")
report.append("")

report.append("---")
report.append("")
report.append("## 부록")
report.append("")
report.append("### 평가 환경")
report.append("")
report.append("- **데이터베이스**: SQL Server (TradingDB)")
report.append("- **평가 쿼리**: constants2.py (30개 쿼리)")
report.append("- **모델**:")
report.append("  - DQN v4: Discrete action space (30 queries trained)")
report.append("  - PPO v3: Discrete with action masking")
report.append("  - DDPG v1: Continuous action space")
report.append("  - SAC v1: Continuous with entropy regularization")
report.append("- **Voting Strategy**: Weighted voting (confidence-based)")
report.append("")

report.append("### 참고 문서")
report.append("")
report.append("- [DQN v3 평가 보고서](../DQN_v3/DQN_v3_Evaluation_Report.md)")
report.append("- [PPO v3 평가 보고서](../PPO_v3/PPO_v3_Evaluation_Report.md)")
report.append("- [DDPG v1 평가 보고서](../DDPG_v1/DDPG_v1_Evaluation_Report.md)")
report.append("- [SAC v1 평가 보고서](../SAC_v1/SAC_v1_Evaluation_Report.md)")
report.append("- [Initial Model Comparison](../Initial_Model_Comparison.md)")
report.append("")

report.append("---")
report.append("")
report.append(f"*Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

# 파일 저장
output_file = os.path.join(os.path.dirname(__file__), 'Ensemble_v1_Final_Report.md')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))

print(f"[OK] Report generated: {output_file}")
print(f"[INFO] Total lines: {len(report)}")

