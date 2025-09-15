# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'

def analyze_original_dataset():
    """원본 데이터셋(9천건 미만)을 분석합니다."""
    
    # 데이터 로드
    print("=== 원본 데이터셋 분석 시작 ===")
    df_plans = pd.read_parquet("artifacts/collected_plans.parquet")
    
    # 9천건 미만으로 제한 (원본 상태 시뮬레이션)
    df_plans_original = df_plans.head(8500)  # 8,500건으로 제한
    print(f"원본 데이터 크기 (제한): {df_plans_original.shape}")
    print(f"전체 데이터 크기: {df_plans.shape}")
    
    # 피처 데이터도 동일하게 제한
    df_features = pd.read_parquet("artifacts/features.parquet")
    df_features_original = df_features.head(8500)
    
    # 1. 타겟 변수 분석
    print("\n=== 타겟 변수 (last_ms) 분석 ===")
    target = df_plans_original['last_ms']
    print(f"기본 통계:")
    print(f"  평균: {target.mean():.2f}")
    print(f"  중앙값: {target.median():.2f}")
    print(f"  표준편차: {target.std():.2f}")
    print(f"  최솟값: {target.min():.2f}")
    print(f"  최댓값: {target.max():.2f}")
    print(f"  사분위수:")
    print(f"    Q1: {target.quantile(0.25):.2f}")
    print(f"    Q3: {target.quantile(0.75):.2f}")
    print(f"  IQR: {target.quantile(0.75) - target.quantile(0.25):.2f}")
    
    # 이상치 분석
    Q1 = target.quantile(0.25)
    Q3 = target.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    outliers = target[(target < lower_bound) | (target > upper_bound)]
    print(f"  이상치 개수: {len(outliers)} ({len(outliers)/len(target)*100:.1f}%)")
    
    # 2. 타겟 변수 분포 시각화
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # 히스토그램
    axes[0,0].hist(target, bins=50, alpha=0.7, edgecolor='black')
    axes[0,0].set_title('Target Distribution (last_ms) - Original Dataset')
    axes[0,0].set_xlabel('last_ms')
    axes[0,0].set_ylabel('Frequency')
    
    # 로그 스케일 히스토그램
    log_target = np.log1p(target)
    axes[0,1].hist(log_target, bins=50, alpha=0.7, edgecolor='black')
    axes[0,1].set_title('Target Distribution (log scale) - Original Dataset')
    axes[0,1].set_xlabel('log(last_ms + 1)')
    axes[0,1].set_ylabel('Frequency')
    
    # 박스플롯
    axes[1,0].boxplot(target)
    axes[1,0].set_title('Target Box Plot - Original Dataset')
    axes[1,0].set_ylabel('last_ms')
    
    # Q-Q 플롯
    from scipy import stats
    stats.probplot(target, dist="norm", plot=axes[1,1])
    axes[1,1].set_title('Q-Q Plot (Normal Distribution) - Original Dataset')
    
    plt.tight_layout()
    plt.savefig('artifacts/target_analysis_original.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 3. 피처 분석
    print("\n=== 피처 분석 ===")
    feature_cols = [col for col in df_features_original.columns if col not in ['plan_id', 'last_ms']]
    print(f"총 피처 수: {len(feature_cols)}")
    
    # 피처별 기본 통계
    feature_stats = df_features_original[feature_cols].describe()
    print("\n피처별 기본 통계:")
    print(feature_stats)
    
    # 4. 타겟과 피처 간 상관관계 분석
    print("\n=== 타겟과 피처 간 상관관계 ===")
    # 수치형 컬럼만 선택
    numeric_cols = df_features_original[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
    correlations = df_features_original[numeric_cols + ['last_ms']].corr()['last_ms'].sort_values(key=abs, ascending=False)
    print("상위 10개 상관관계:")
    print(correlations.head(11)[1:])  # last_ms 자기 자신 제외
    
    # 5. 상관관계 히트맵
    plt.figure(figsize=(12, 10))
    corr_matrix = df_features_original[numeric_cols + ['last_ms']].corr()
    sns.heatmap(corr_matrix, annot=False, cmap='coolwarm', center=0, 
                square=True, cbar_kws={'shrink': 0.8})
    plt.title('Feature Correlation Matrix - Original Dataset')
    plt.tight_layout()
    plt.savefig('artifacts/correlation_heatmap_original.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 6. 피처별 분포 확인
    print("\n=== 피처별 분포 확인 ===")
    numeric_features = df_features_original[feature_cols].select_dtypes(include=[np.number]).columns
    print(f"수치형 피처 수: {len(numeric_features)}")
    
    # 피처별 분산 분석
    feature_vars = df_features_original[numeric_features].var().sort_values(ascending=False)
    print("\n피처별 분산 (상위 10개):")
    print(feature_vars.head(10))
    
    # 7. 결측값 확인
    print("\n=== 결측값 확인 ===")
    missing_values = df_features_original.isnull().sum()
    missing_percent = (missing_values / len(df_features_original)) * 100
    missing_df = pd.DataFrame({
        'Missing Count': missing_values,
        'Missing %': missing_percent
    }).sort_values('Missing %', ascending=False)
    
    print("결측값이 있는 컬럼:")
    print(missing_df[missing_df['Missing Count'] > 0])
    
    # 8. 데이터 품질 이슈 확인
    print("\n=== 데이터 품질 이슈 ===")
    
    # 0값이 많은 피처들
    zero_counts = (df_features_original[numeric_features] == 0).sum()
    high_zero_features = zero_counts[zero_counts > len(df_features_original) * 0.8]
    print(f"80% 이상이 0인 피처들: {len(high_zero_features)}개")
    if len(high_zero_features) > 0:
        print(high_zero_features)
    
    # 상수 피처들
    constant_features = df_features_original[numeric_features].nunique() == 1
    print(f"상수 피처들: {constant_features.sum()}개")
    if constant_features.any():
        print(constant_features[constant_features].index.tolist())
    
    # 9. 원본 vs 확장 데이터 비교
    print("\n=== 원본 vs 확장 데이터 비교 ===")
    print(f"원본 데이터 크기: {df_plans_original.shape[0]:,}건")
    print(f"확장 데이터 크기: {df_plans.shape[0]:,}건")
    print(f"증가율: {(df_plans.shape[0] / df_plans_original.shape[0] - 1) * 100:.1f}%")
    
    # 타겟 변수 비교
    target_original = df_plans_original['last_ms']
    target_expanded = df_plans['last_ms']
    
    print(f"\n타겟 변수 비교:")
    print(f"원본 - 평균: {target_original.mean():.2f}ms, 중앙값: {target_original.median():.2f}ms")
    print(f"확장 - 평균: {target_expanded.mean():.2f}ms, 중앙값: {target_expanded.median():.2f}ms")
    
    return df_plans_original, df_features_original, correlations

if __name__ == "__main__":
    df_plans, df_features, correlations = analyze_original_dataset()
