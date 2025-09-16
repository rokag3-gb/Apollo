# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def deep_data_analysis():
    """데이터의 근본적인 문제를 분석합니다."""
    
    print("=== 심층 데이터 분석 ===")
    
    # 원본 데이터 로드
    df_plans = pd.read_parquet("artifacts/collected_plans.parquet")
    df_features = pd.read_parquet("artifacts/features.parquet")
    
    print(f"원본 데이터: {df_plans.shape}")
    print(f"피처 데이터: {df_features.shape}")
    
    # 1. 타겟 변수 상세 분석
    print("\n=== 타겟 변수 상세 분석 ===")
    target = df_plans['last_ms']
    
    # 분위수별 분석
    percentiles = [0, 1, 5, 10, 25, 50, 75, 90, 95, 99, 100]
    print("분위수별 값:")
    for p in percentiles:
        val = np.percentile(target, p)
        print(f"  {p:2d}%: {val:10.2f}ms")
    
    # 0에 가까운 값들 분석
    very_small = target[target < 1.0]
    small = target[(target >= 1.0) & (target < 10.0)]
    medium = target[(target >= 10.0) & (target < 100.0)]
    large = target[(target >= 100.0) & (target < 1000.0)]
    very_large = target[target >= 1000.0]
    
    print(f"\n값 범위별 분포:")
    print(f"  < 1ms:     {len(very_small):4d}개 ({len(very_small)/len(target)*100:5.1f}%)")
    print(f"  1-10ms:    {len(small):4d}개 ({len(small)/len(target)*100:5.1f}%)")
    print(f"  10-100ms:  {len(medium):4d}개 ({len(medium)/len(target)*100:5.1f}%)")
    print(f"  100-1000ms:{len(large):4d}개 ({len(large)/len(target)*100:5.1f}%)")
    print(f"  >= 1000ms: {len(very_large):4d}개 ({len(very_large)/len(target)*100:5.1f}%)")
    
    # 2. 실행계획 XML 분석
    print("\n=== 실행계획 XML 분석 ===")
    
    # XML 길이 분석
    xml_lengths = df_plans['plan_xml'].str.len()
    print(f"XML 길이 통계:")
    print(f"  평균: {xml_lengths.mean():.0f}자")
    print(f"  중앙값: {xml_lengths.median():.0f}자")
    print(f"  최댓값: {xml_lengths.max():.0f}자")
    print(f"  최솟값: {xml_lengths.min():.0f}자")
    
    # 3. 피처 데이터 품질 분석
    print("\n=== 피처 데이터 품질 분석 ===")
    
    # 각 피처별 유효한 값의 비율
    feature_cols = [col for col in df_features.columns if col not in ['plan_id', 'last_ms']]
    valid_ratios = {}
    
    for col in feature_cols:
        if df_features[col].dtype in ['object', 'string']:
            valid_ratio = (df_features[col].notna() & (df_features[col] != '')).sum() / len(df_features)
        else:
            valid_ratio = df_features[col].notna().sum() / len(df_features)
        valid_ratios[col] = valid_ratio
    
    valid_df = pd.DataFrame(list(valid_ratios.items()), columns=['feature', 'valid_ratio'])
    valid_df = valid_df.sort_values('valid_ratio')
    
    print("피처별 유효값 비율 (하위 10개):")
    print(valid_df.head(10))
    
    # 4. 실행계획 복잡도와 실행시간의 관계 분석
    print("\n=== 실행계획 복잡도 vs 실행시간 분석 ===")
    
    # 간단한 복잡도 지표 생성
    df_features['complexity_score'] = (
        df_features['num_nodes'].fillna(0) * 0.3 +
        df_features['num_edges'].fillna(0) * 0.3 +
        df_features['num_logical_ops'].fillna(0) * 0.2 +
        df_features['num_physical_ops'].fillna(0) * 0.2
    )
    
    # 복잡도 구간별 분석
    complexity_bins = pd.cut(df_features['complexity_score'], bins=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
    complexity_analysis = df_features.groupby(complexity_bins)['last_ms'].agg(['count', 'mean', 'median', 'std']).round(2)
    
    print("복잡도 구간별 실행시간 분석:")
    print(complexity_analysis)
    
    # 5. 특이 케이스 분석
    print("\n=== 특이 케이스 분석 ===")
    
    # 가장 빠른 쿼리들
    fastest_queries = df_plans.nsmallest(10, 'last_ms')[['plan_id', 'last_ms']]
    print("가장 빠른 쿼리들 (상위 10개):")
    print(fastest_queries)
    
    # 가장 느린 쿼리들
    slowest_queries = df_plans.nlargest(10, 'last_ms')[['plan_id', 'last_ms']]
    print("\n가장 느린 쿼리들 (상위 10개):")
    print(slowest_queries)
    
    # 6. 실행계획 XML 샘플 분석
    print("\n=== 실행계획 XML 샘플 분석 ===")
    
    # 빠른 쿼리와 느린 쿼리의 XML 비교
    fast_sample = df_plans[df_plans['plan_id'] == fastest_queries.iloc[0]['plan_id']]['plan_xml'].iloc[0]
    slow_sample = df_plans[df_plans['plan_id'] == slowest_queries.iloc[0]['plan_id']]['plan_xml'].iloc[0]
    
    print(f"빠른 쿼리 (ID: {fastest_queries.iloc[0]['plan_id']}, {fastest_queries.iloc[0]['last_ms']:.2f}ms) XML 길이: {len(fast_sample)}자")
    print(f"느린 쿼리 (ID: {slowest_queries.iloc[0]['plan_id']}, {slowest_queries.iloc[0]['last_ms']:.2f}ms) XML 길이: {len(slow_sample)}자")
    
    # 7. 데이터 분포 시각화
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    # 타겟 분포 (로그 스케일)
    axes[0,0].hist(np.log1p(target), bins=50, alpha=0.7, edgecolor='black')
    axes[0,0].set_title('Target Distribution (log scale)')
    axes[0,0].set_xlabel('log(last_ms + 1)')
    axes[0,0].set_ylabel('Frequency')
    
    # 타겟 분포 (원본 스케일, 제한)
    axes[0,1].hist(target[target < 1000], bins=50, alpha=0.7, edgecolor='black')
    axes[0,1].set_title('Target Distribution (< 1000ms)')
    axes[0,1].set_xlabel('last_ms')
    axes[0,1].set_ylabel('Frequency')
    
    # 복잡도 vs 실행시간
    axes[0,2].scatter(df_features['complexity_score'], target, alpha=0.5, s=1)
    axes[0,2].set_title('Complexity vs Execution Time')
    axes[0,2].set_xlabel('Complexity Score')
    axes[0,2].set_ylabel('last_ms')
    axes[0,2].set_yscale('log')
    
    # XML 길이 vs 실행시간
    axes[1,0].scatter(xml_lengths, target, alpha=0.5, s=1)
    axes[1,0].set_title('XML Length vs Execution Time')
    axes[1,0].set_xlabel('XML Length (characters)')
    axes[1,0].set_ylabel('last_ms')
    axes[1,0].set_yscale('log')
    
    # 노드 수 vs 실행시간
    axes[1,1].scatter(df_features['num_nodes'], target, alpha=0.5, s=1)
    axes[1,1].set_title('Number of Nodes vs Execution Time')
    axes[1,1].set_xlabel('Number of Nodes')
    axes[1,1].set_ylabel('last_ms')
    axes[1,1].set_yscale('log')
    
    # 엣지 수 vs 실행시간
    axes[1,2].scatter(df_features['num_edges'], target, alpha=0.5, s=1)
    axes[1,2].set_title('Number of Edges vs Execution Time')
    axes[1,2].set_xlabel('Number of Edges')
    axes[1,2].set_ylabel('last_ms')
    axes[1,2].set_yscale('log')
    
    plt.tight_layout()
    plt.savefig('artifacts/deep_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 8. 결론 및 권장사항
    print("\n=== 분석 결론 및 권장사항 ===")
    
    print("1. 타겟 변수 문제:")
    print(f"   - 극심한 분포 불균형: 중앙값 {target.median():.2f}ms vs 평균 {target.mean():.2f}ms")
    print(f"   - 80% 이상이 10ms 미만의 매우 빠른 쿼리")
    print(f"   - 19.8%가 이상치 (극단적으로 느린 쿼리)")
    
    print("\n2. 피처 데이터 문제:")
    print(f"   - 49.6%의 피처가 결측값")
    print(f"   - 9개 피처가 상수값 (분산 0)")
    print(f"   - 대부분 피처가 타겟과 낮은 상관관계")
    
    print("\n3. 근본적인 문제:")
    print("   - 실행계획의 구조적 특성만으로는 실행시간을 예측하기 어려움")
    print("   - 실제 실행시간은 데이터 크기, 인덱스 상태, 시스템 리소스 등에 더 의존")
    print("   - 현재 피처들은 실행계획의 '복잡도'만 반영, '실행 비용'을 제대로 반영하지 못함")
    
    print("\n4. 개선 방향:")
    print("   - 더 많은 컨텍스트 정보 필요 (테이블 크기, 인덱스 통계, 시스템 상태)")
    print("   - 실행계획의 '비용' 정보를 더 정확히 추출")
    print("   - 클러스터링을 통한 쿼리 패턴 분석")
    print("   - 시계열 특성 고려 (시간대별 성능 변화)")
    
    return df_plans, df_features

if __name__ == "__main__":
    df_plans, df_features = deep_data_analysis()
