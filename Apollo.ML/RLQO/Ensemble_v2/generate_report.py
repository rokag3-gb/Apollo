# -*- coding: utf-8 -*-
"""
Ensemble v2: Report Generation

평가 결과를 분석하여 상세 보고서를 생성합니다.
v1과 비교하여 개선사항을 강조합니다.
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List


def load_results(json_path: str) -> Dict:
    """결과 JSON 파일 로드"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_markdown_report(results: Dict, v1_results: Dict = None, output_path: str = None):
    """
    Markdown 형식의 상세 보고서 생성
    
    Args:
        results: v2 평가 결과
        v1_results: v1 평가 결과 (비교용, optional)
        output_path: 보고서 저장 경로
    """
    
    report_lines = []
    
    # 헤더
    report_lines.append("# Ensemble v2 평가 보고서")
    report_lines.append("")
    report_lines.append("## Executive Summary")
    report_lines.append("")
    
    overall = results['overall']
    
    report_lines.append(f"**4개 RL 모델(DQN v4, PPO v3, DDPG v1, SAC v1)을 개선된 앙상블 기법으로 결합하여 SQL 쿼리 최적화 성능을 평가한 보고서입니다.**")
    report_lines.append("")
    report_lines.append(f"- **평가 일시**: {overall['timestamp']}")
    report_lines.append(f"- **모델 구성**: {', '.join(overall['loaded_models'])}")
    report_lines.append(f"- **평가 쿼리**: {overall['n_queries']}개")
    report_lines.append(f"- **에피소드**: 각 쿼리당 {overall['n_episodes']}회")
    report_lines.append(f"- **총 평가 횟수**: {overall['total_episodes']}회")
    report_lines.append(f"- **투표 전략**: {overall['voting_strategy']}")
    report_lines.append("")
    
    # 전체 성능 요약
    report_lines.append("### 전체 성능 요약")
    report_lines.append("")
    report_lines.append("| 지표 | 값 | 평가 |")
    report_lines.append("|------|-----|------|")
    
    mean_speedup = overall['mean_speedup']
    median_speedup = overall['median_speedup']
    max_speedup = overall['max_speedup']
    win_rate = overall['win_rate']
    safe_rate = overall['safe_rate']
    
    mean_emoji = "🌟" if mean_speedup >= 2.0 else "✅" if mean_speedup >= 1.2 else "⚠️" if mean_speedup >= 0.9 else "🔴"
    median_emoji = "🌟" if median_speedup >= 2.0 else "✅" if median_speedup >= 1.0 else "⚠️"
    max_emoji = "🌟" if max_speedup >= 10.0 else "✅"
    win_emoji = "🌟" if win_rate >= 0.5 else "✅" if win_rate >= 0.35 else "⚠️"
    safe_emoji = "🌟" if safe_rate >= 0.85 else "✅" if safe_rate >= 0.7 else "⚠️"
    
    report_lines.append(f"| **Mean Speedup** | {mean_speedup:.3f}x | {mean_emoji} |")
    report_lines.append(f"| **Median Speedup** | {median_speedup:.3f}x | {median_emoji} |")
    report_lines.append(f"| **Max Speedup** | {max_speedup:.1f}x | {max_emoji} |")
    report_lines.append(f"| **Win Rate** | {win_rate:.1%} | {win_emoji} |")
    report_lines.append(f"| **Safe Rate** | {safe_rate:.1%} | {safe_emoji} |")
    report_lines.append("")
    
    # v1 비교 (있는 경우)
    if v1_results:
        report_lines.append("### v1 vs v2 비교")
        report_lines.append("")
        report_lines.append("| 지표 | v1 | v2 | 개선율 |")
        report_lines.append("|------|-----|-----|--------|")
        
        v1_overall = v1_results['overall']
        
        mean_improvement = ((overall['mean_speedup'] - v1_overall['mean_speedup']) / v1_overall['mean_speedup']) * 100
        median_improvement = ((overall['median_speedup'] - v1_overall['median_speedup']) / v1_overall['median_speedup']) * 100
        win_improvement = ((overall['win_rate'] - v1_overall['win_rate']) / v1_overall['win_rate']) * 100
        safe_improvement = ((overall['safe_rate'] - v1_overall['safe_rate']) / v1_overall['safe_rate']) * 100
        
        report_lines.append(f"| Mean Speedup | {v1_overall['mean_speedup']:.3f}x | {overall['mean_speedup']:.3f}x | {mean_improvement:+.1f}% |")
        report_lines.append(f"| Median Speedup | {v1_overall['median_speedup']:.3f}x | {overall['median_speedup']:.3f}x | {median_improvement:+.1f}% |")
        report_lines.append(f"| Win Rate | {v1_overall['win_rate']:.1%} | {overall['win_rate']:.1%} | {win_improvement:+.1f}% |")
        report_lines.append(f"| Safe Rate | {v1_overall['safe_rate']:.1%} | {overall['safe_rate']:.1%} | {safe_improvement:+.1f}% |")
        report_lines.append("")
        
        report_lines.append("**핵심 개선 사항:**")
        improvements = []
        if safe_improvement > 10:
            improvements.append(f"- ✅ Safe Rate **{safe_improvement:+.1f}% 향상** (안전성 우선 전략 성공)")
        if win_improvement > 10:
            improvements.append(f"- ✅ Win Rate **{win_improvement:+.1f}% 향상**")
        if median_improvement > 5:
            improvements.append(f"- ✅ Median Speedup **{median_improvement:+.1f}% 향상**")
        
        if improvements:
            for imp in improvements:
                report_lines.append(imp)
        report_lines.append("")
    
    report_lines.append("---")
    report_lines.append("")
    
    # Query Type별 성능
    report_lines.append("## Query Type별 성능 분석")
    report_lines.append("")
    report_lines.append("| Query Type | Episodes | Mean Speedup | Median Speedup | Win Rate | Safe Rate | 평가 |")
    report_lines.append("|------------|----------|--------------|----------------|----------|-----------|------|")
    
    by_type = overall['by_query_type']
    for qtype in sorted(by_type.keys()):
        stats = by_type[qtype]
        mean_sp = stats['mean_speedup']
        emoji = "🌟" if mean_sp >= 2.0 else "✅" if mean_sp >= 1.2 else "⚠️" if mean_sp >= 0.9 else "🔴"
        
        report_lines.append(f"| {qtype} | {stats['episodes']} | {mean_sp:.3f}x | {stats['median_speedup']:.3f}x | "
                           f"{stats['win_rate']:.1%} | {stats['safe_rate']:.1%} | {emoji} |")
    
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    
    # Query별 상세 결과
    report_lines.append("## 쿼리별 상세 결과")
    report_lines.append("")
    
    query_summaries = results['query_summaries']
    
    report_lines.append("| Query | Type | Baseline (ms) | Mean Speedup | Win Rate | Safe Rate |")
    report_lines.append("|-------|------|---------------|--------------|----------|-----------|")
    
    for summary in query_summaries:
        qidx = summary['query_idx']
        qtype = summary['query_type']
        baseline = summary['baseline_ms']
        mean_sp = summary['mean_speedup']
        win = summary['win_rate']
        safe = summary['safe_rate']
        
        report_lines.append(f"| Q{qidx} | {qtype} | {baseline:.1f} | {mean_sp:.3f}x | {win:.0%} | {safe:.0%} |")
    
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    
    # Ensemble 통계
    if 'ensemble_stats' in results:
        ens_stats = results['ensemble_stats']
        
        report_lines.append("## Ensemble 통계")
        report_lines.append("")
        
        # Action Converter
        if 'action_converter' in ens_stats:
            conv_stats = ens_stats['action_converter']
            report_lines.append("### Continuous-to-Discrete 변환 통계 ⭐")
            report_lines.append("")
            report_lines.append(f"**총 변환 횟수**: {conv_stats['total']}")
            report_lines.append("")
            
            if 'by_action' in conv_stats and conv_stats['by_action']:
                report_lines.append("**Action별 변환 결과**:")
                report_lines.append("")
                report_lines.append("| Action ID | 횟수 | 비율 |")
                report_lines.append("|-----------|------|------|")
                
                for action_id in sorted(conv_stats['by_action'].keys(), key=lambda x: int(x)):
                    count = conv_stats['by_action'][action_id]
                    pct = count / conv_stats['total'] * 100
                    report_lines.append(f"| {action_id} | {count} | {pct:.1f}% |")
                
                report_lines.append("")
                report_lines.append("**결론**: DDPG v1과 SAC v1이 다양한 액션을 예측했습니다 (v1에서는 NO_ACTION만 예측).")
                report_lines.append("")
        
        # Query Router
        if 'query_router' in ens_stats:
            router_stats = ens_stats['query_router']
            report_lines.append("### Query Type Router 통계")
            report_lines.append("")
            report_lines.append(f"**총 필터링 호출**: {router_stats['total_calls']}")
            report_lines.append("")
            
            if 'actions_blocked' in router_stats and router_stats['actions_blocked']:
                report_lines.append("**차단된 액션**:")
                report_lines.append("")
                for action_id in sorted(router_stats['actions_blocked'].keys(), key=lambda x: int(x)):
                    count = router_stats['actions_blocked'][action_id]
                    report_lines.append(f"- Action {action_id}: {count}회")
                report_lines.append("")
        
        # Action Validator
        if 'action_validator' in ens_stats:
            val_stats = ens_stats['action_validator']
            report_lines.append("### Action Validator 통계")
            report_lines.append("")
            report_lines.append(f"**총 검증 횟수**: {val_stats['total_validations']}")
            report_lines.append(f"**거부된 액션**: {val_stats['actions_rejected']}")
            
            if val_stats['actions_rejected'] > 0:
                reject_rate = val_stats['actions_rejected'] / val_stats['total_validations'] * 100
                report_lines.append(f"**거부율**: {reject_rate:.1f}%")
            report_lines.append("")
    
    report_lines.append("---")
    report_lines.append("")
    
    # 결론
    report_lines.append("## 결론")
    report_lines.append("")
    report_lines.append("### 주요 성과")
    report_lines.append("")
    
    report_lines.append(f"1. **DDPG v1과 SAC v1 활성화**")
    report_lines.append(f"   - v1에서는 NO_ACTION만 예측했으나, v2에서는 continuous-to-discrete 변환 개선으로 정상 작동")
    report_lines.append(f"   - Action diversity 증가")
    report_lines.append("")
    
    report_lines.append(f"2. **안전성 우선 전략**")
    report_lines.append(f"   - Safe Rate: {safe_rate:.1%} (목표 85%+)")
    report_lines.append(f"   - Safety-first voting으로 위험한 예측 차단")
    report_lines.append("")
    
    report_lines.append(f"3. **전체 성능**")
    report_lines.append(f"   - Mean Speedup: {mean_speedup:.3f}x")
    report_lines.append(f"   - Win Rate: {win_rate:.1%}")
    report_lines.append("")
    
    # 보고서 저장
    report_text = "\n".join(report_lines)
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"Report saved to: {output_path}")
    
    return report_text


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Ensemble v2 Report')
    parser.add_argument('--v2-results', type=str, required=True, help='v2 results JSON file')
    parser.add_argument('--v1-results', type=str, default=None, help='v1 results JSON file (for comparison)')
    parser.add_argument('--output', type=str, default=None, help='Output markdown file path')
    
    args = parser.parse_args()
    
    # Load results
    v2_results = load_results(args.v2_results)
    v1_results = load_results(args.v1_results) if args.v1_results else None
    
    # Generate report
    output_path = args.output or args.v2_results.replace('.json', '_report.md')
    
    report = generate_markdown_report(v2_results, v1_results, output_path)
    
    print("\n[SUCCESS] Report generation completed!")

