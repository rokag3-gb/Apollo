# -*- coding: utf-8 -*-
"""
Phase 1 vs Phase 2 Overfitting 방지 모델 비교 분석
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import joblib

def compare_overfit_prevention_models():
    """Overfitting 방지 모델들 비교 분석"""
    
    print("=" * 80)
    print("🔍 Phase 1 vs Phase 2 Overfitting 방지 모델 비교 분석")
    print("=" * 80)
    
    # 1. 모델 성능 비교
    print("\n📊 모델 성능 비교")
    print("-" * 60)
    
    performance_comparison = {
        "Phase 1 (데이터 품질 개선)": {
            "검증 R²": 0.1151,
            "교차 검증 R²": 0.0914,
            "교차 검증 표준편차": 0.0422,
            "훈련 R²": 0.0857,
            "검증 R²": 0.1151,
            "Overfitting Gap": 0.0294,
            "피처 수": 20,
            "주요 피처": ["avg_ms", "reads_per_ms", "last_cpu_ms", "cpu_ratio", "max_dop"]
        },
        "Phase 2 (고급 피처 엔지니어링)": {
            "검증 R²": 0.9297,
            "교차 검증 R²": 0.9343,
            "교차 검증 표준편차": 0.0043,
            "훈련 R²": 0.9350,
            "검증 R²": 0.9297,
            "Overfitting Gap": 0.0052,
            "피처 수": 15,
            "주요 피처": ["performance_trend", "avg_ms", "parallel_efficiency", "cpu_ratio", "last_reads"]
        }
    }
    
    for model_name, metrics in performance_comparison.items():
        print(f"\n{model_name}:")
        for metric, value in metrics.items():
            if metric == "주요 피처":
                print(f"  {metric}: {', '.join(value)}")
            else:
                print(f"  {metric}: {value}")
    
    # 2. Overfitting 분석
    print(f"\n⚠️  Overfitting 분석")
    print("-" * 60)
    
    print("Phase 1:")
    print(f"  - Overfitting Gap: {performance_comparison['Phase 1 (데이터 품질 개선)']['Overfitting Gap']:.4f}")
    print(f"  - 교차 검증 표준편차: {performance_comparison['Phase 1 (데이터 품질 개선)']['교차 검증 표준편차']:.4f}")
    print(f"  - 판정: {'✅ Overfitting 없음' if performance_comparison['Phase 1 (데이터 품질 개선)']['Overfitting Gap'] < 0.05 else '❌ Overfitting 의심'}")
    
    print("\nPhase 2:")
    print(f"  - Overfitting Gap: {performance_comparison['Phase 2 (고급 피처 엔지니어링)']['Overfitting Gap']:.4f}")
    print(f"  - 교차 검증 표준편차: {performance_comparison['Phase 2 (고급 피처 엔지니어링)']['교차 검증 표준편차']:.4f}")
    print(f"  - 판정: {'✅ Overfitting 없음' if performance_comparison['Phase 2 (고급 피처 엔지니어링)']['Overfitting Gap'] < 0.05 else '❌ Overfitting 의심'}")
    
    # 3. 성능 안정성 분석
    print(f"\n📈 성능 안정성 분석")
    print("-" * 60)
    
    print("교차 검증 표준편차 (낮을수록 안정적):")
    print(f"  Phase 1: {performance_comparison['Phase 1 (데이터 품질 개선)']['교차 검증 표준편차']:.4f}")
    print(f"  Phase 2: {performance_comparison['Phase 2 (고급 피처 엔지니어링)']['교차 검증 표준편차']:.4f}")
    
    if performance_comparison['Phase 2 (고급 피처 엔지니어링)']['교차 검증 표준편차'] < performance_comparison['Phase 1 (데이터 품질 개선)']['교차 검증 표준편차']:
        print("  → Phase 2가 더 안정적")
    else:
        print("  → Phase 1이 더 안정적")
    
    # 4. 피처 효율성 분석
    print(f"\n🎯 피처 효율성 분석")
    print("-" * 60)
    
    phase1_efficiency = performance_comparison['Phase 1 (데이터 품질 개선)']['검증 R²'] / performance_comparison['Phase 1 (데이터 품질 개선)']['피처 수']
    phase2_efficiency = performance_comparison['Phase 2 (고급 피처 엔지니어링)']['검증 R²'] / performance_comparison['Phase 2 (고급 피처 엔지니어링)']['피처 수']
    
    print(f"피처당 R² (높을수록 효율적):")
    print(f"  Phase 1: {phase1_efficiency:.4f}")
    print(f"  Phase 2: {phase2_efficiency:.4f}")
    
    if phase2_efficiency > phase1_efficiency:
        print("  → Phase 2가 더 효율적")
    else:
        print("  → Phase 1이 더 효율적")
    
    # 5. 권장사항
    print(f"\n💡 권장사항")
    print("-" * 60)
    
    recommendations = []
    
    if performance_comparison['Phase 2 (고급 피처 엔지니어링)']['검증 R²'] > performance_comparison['Phase 1 (데이터 품질 개선)']['검증 R²']:
        recommendations.append("Phase 2 모델을 프로덕션에 사용 권장 (R² 0.9297)")
    else:
        recommendations.append("Phase 1 모델을 프로덕션에 사용 권장 (R² 0.1151)")
    
    if performance_comparison['Phase 2 (고급 피처 엔지니어링)']['Overfitting Gap'] < performance_comparison['Phase 1 (데이터 품질 개선)']['Overfitting Gap']:
        recommendations.append("Phase 2가 더 안정적 (Overfitting Gap 0.0052)")
    else:
        recommendations.append("Phase 1이 더 안정적 (Overfitting Gap 0.0294)")
    
    if performance_comparison['Phase 2 (고급 피처 엔지니어링)']['교차 검증 표준편차'] < performance_comparison['Phase 1 (데이터 품질 개선)']['교차 검증 표준편차']:
        recommendations.append("Phase 2가 더 일관된 성능 (낮은 표준편차)")
    else:
        recommendations.append("Phase 1이 더 일관된 성능 (낮은 표준편차)")
    
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")
    
    # 6. 최종 결론
    print(f"\n🏆 최종 결론")
    print("-" * 60)
    
    if performance_comparison['Phase 2 (고급 피처 엔지니어링)']['검증 R²'] > 0.9:
        print("✅ Phase 2 모델이 R² 0.9 이상 달성!")
        print("   - 고급 피처 엔지니어링이 매우 효과적")
        print("   - Overfitting 없이 안정적인 성능")
        print("   - 프로덕션 적용 권장")
    elif performance_comparison['Phase 1 (데이터 품질 개선)']['검증 R²'] > 0.1:
        print("⚠️  Phase 1 모델은 기본적인 성능 달성")
        print("   - 데이터 품질 개선이 중요")
        print("   - 추가 피처 엔지니어링 필요")
    else:
        print("❌ 두 모델 모두 개선 필요")
        print("   - 더 많은 데이터 수집 필요")
        print("   - 피처 엔지니어링 전략 재검토 필요")
    
    return performance_comparison

def create_performance_visualization():
    """성능 비교 시각화"""
    
    # 데이터 준비
    models = ['Phase 1\n(데이터 품질)', 'Phase 2\n(고급 피처)']
    r2_scores = [0.1151, 0.9297]
    cv_scores = [0.0914, 0.9343]
    cv_stds = [0.0422, 0.0043]
    overfitting_gaps = [0.0294, 0.0052]
    
    # 그래프 생성
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. R² 점수 비교
    x = np.arange(len(models))
    width = 0.35
    
    ax1.bar(x - width/2, r2_scores, width, label='검증 R²', alpha=0.8, color='skyblue')
    ax1.bar(x + width/2, cv_scores, width, label='교차 검증 R²', alpha=0.8, color='lightcoral')
    ax1.set_xlabel('모델')
    ax1.set_ylabel('R² 점수')
    ax1.set_title('R² 점수 비교')
    ax1.set_xticks(x)
    ax1.set_xticklabels(models)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 교차 검증 표준편차
    ax2.bar(models, cv_stds, alpha=0.8, color='orange')
    ax2.set_xlabel('모델')
    ax2.set_ylabel('표준편차')
    ax2.set_title('교차 검증 표준편차 (낮을수록 안정적)')
    ax2.grid(True, alpha=0.3)
    
    # 3. Overfitting Gap
    ax3.bar(models, overfitting_gaps, alpha=0.8, color='green')
    ax3.axhline(y=0.05, color='red', linestyle='--', label='Overfitting 임계값 (0.05)')
    ax3.set_xlabel('모델')
    ax3.set_ylabel('Overfitting Gap')
    ax3.set_title('Overfitting Gap (낮을수록 좋음)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 종합 성능 지표
    # 정규화된 점수 (0-1 스케일)
    normalized_r2 = [score for score in r2_scores]
    normalized_stability = [1 - std for std in cv_stds]  # 표준편차가 낮을수록 높은 점수
    normalized_overfitting = [1 - gap for gap in overfitting_gaps]  # Gap이 낮을수록 높은 점수
    
    categories = ['R² 점수', '안정성', 'Overfitting 방지']
    phase1_scores = [normalized_r2[0], normalized_stability[0], normalized_overfitting[0]]
    phase2_scores = [normalized_r2[1], normalized_stability[1], normalized_overfitting[1]]
    
    x = np.arange(len(categories))
    width = 0.35
    
    ax4.bar(x - width/2, phase1_scores, width, label='Phase 1', alpha=0.8, color='skyblue')
    ax4.bar(x + width/2, phase2_scores, width, label='Phase 2', alpha=0.8, color='lightcoral')
    ax4.set_xlabel('성능 지표')
    ax4.set_ylabel('정규화된 점수')
    ax4.set_title('종합 성능 비교')
    ax4.set_xticks(x)
    ax4.set_xticklabels(categories)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('artifacts/overfit_prevention_comparison.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("\n📊 시각화 완료: artifacts/overfit_prevention_comparison.png")

def main():
    """메인 실행 함수"""
    performance_comparison = compare_overfit_prevention_models()
    create_performance_visualization()
    
    print(f"\n" + "=" * 80)
    print("🎯 요약")
    print("=" * 80)
    print("Phase 1: R² 0.1151, Overfitting Gap 0.0294 (안정적)")
    print("Phase 2: R² 0.9297, Overfitting Gap 0.0052 (매우 안정적)")
    print("→ Phase 2 모델이 R² 0.9 이상 달성하며 Overfitting 없이 안정적!")

if __name__ == "__main__":
    main()

