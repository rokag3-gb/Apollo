# -*- coding: utf-8 -*-
"""
데이터 전처리 모듈
타겟 변수 정보 누출을 방지한 안전한 전처리를 수행합니다.
"""

import pandas as pd
import numpy as np
import networkx as nx
from datetime import datetime
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, QuantileTransformer, PowerTransformer
from sklearn.impute import KNNImputer
from sklearn.ensemble import IsolationForest
from sklearn.feature_selection import SelectKBest, f_regression, RFE
from xgboost import XGBRegressor
from scipy.stats import boxcox
import warnings
warnings.filterwarnings('ignore')

def preprocess_data():
    """메인 전처리 함수"""
    
    print("=== 데이터 전처리 시작 ===")
    
    # 1. 원본 데이터 로드
    df = pd.read_parquet("artifacts/collected_plans.parquet")
    print(f"원본 데이터 크기: {df.shape}")
    
    # 2. 타겟 변수 분리 (가장 먼저!)
    print("\n1. 타겟 변수 분리...")
    y = df['last_ms'].copy()
    # plan_xml 컬럼은 피처 엔지니어링에서 필요하므로 보존
    df_features = df.drop(['last_ms'], axis=1)
    
    # 3. 이상치 처리 (타겟 변수 정보 누출 방지)
    print("\n2. 이상치 처리 (타겟 변수 정보 누출 방지)...")
    df_clean, y = improved_outlier_handling_safe(df_features, y)
    
    # 4. 결측값 처리 (타겟 변수 제외)
    print("\n3. 결측값 처리 (타겟 변수 제외)...")
    df_clean = improved_missing_value_handling_safe(df_clean)
    
    # 5. 안전한 피처 엔지니어링 (타겟 변수 제외)
    print("\n4. 안전한 피처 엔지니어링...")
    df_clean = add_safe_domain_features(df_clean)
    
    # 6. 안전한 클러스터링 (타겟 변수 제외)
    print("\n5. 안전한 클러스터링...")
    df_clean = add_safe_clustering_features(df_clean)
    
    # 7. 피처 정규화
    print("\n6. 피처 정규화...")
    df_clean = improved_feature_scaling(df_clean)
    
    # 8. 피처 선택
    print("\n7. 피처 선택...")
    df_clean = safe_feature_selection(df_clean, y)
    
    # 9. 최종 데이터 저장
    print("\n8. 전처리된 데이터 저장...")
    df_clean['last_ms'] = y  # 타겟 변수 다시 추가
    df_clean.to_parquet('artifacts/preprocessed_data.parquet', index=False)
    
    print(f"전처리 완료! 최종 데이터 크기: {df_clean.shape}")
    print(f"저장 위치: artifacts/preprocessed_data.parquet")
    
    return df_clean

def improved_outlier_handling_safe(df_features, y):
    """타겟 변수 정보 누출을 방지한 이상치 처리 (IQR 기반 제거 추가)"""
    
    # 임시로 피처와 타겟을 합쳐서 이상치 제거 (행 일관성 유지)
    df_combined = df_features.copy()
    df_combined['last_ms'] = y
    
    initial_rows = len(df_combined)
    print(f"  IQR 처리 전 데이터 크기: {initial_rows}개 행")

    # IQR 기반 이상치 제거 (타겟 변수 포함 모든 수치형 컬럼)
    numeric_cols = df_combined.select_dtypes(include=np.number).columns.tolist()
    numeric_cols = [col for col in numeric_cols if col not in ['plan_id', 'query_id']]

    df_clean = df_combined.copy()
    # 이상치로 인해 제거될 인덱스를 추적
    outlier_indices = pd.Series(False, index=df_clean.index)

    for col in numeric_cols:
        # 0을 포함하는 데이터가 많으므로, 0을 제외하고 IQR 계산
        col_data = df_clean[col][df_clean[col] > 0]
        if col_data.empty:
            continue

        Q1 = col_data.quantile(0.25)
        Q3 = col_data.quantile(0.75)
        IQR = Q3 - Q1
        
        # IQR이 0인 경우 (데이터가 거의 동일한 경우) 이상치 탐지 스킵
        if IQR == 0:
            continue

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        is_outlier = (df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)
        num_outliers = is_outlier.sum()
        
        if num_outliers > 0:
            print(f"  - '{col}' 컬럼에서 IQR 이상치 {num_outliers}개 발견")
            outlier_indices = outlier_indices | is_outlier

    # 한 번에 이상치 행 제거
    df_clean = df_clean[~outlier_indices]
    
    final_rows = len(df_clean)
    removed_rows = initial_rows - final_rows
    print(f"  IQR 처리로 총 {removed_rows}개의 이상치 행 제거됨. 최종 크기: {final_rows}개 행")

    if df_clean.empty:
        raise ValueError("이상치 제거 후 남은 데이터가 없습니다. contamination을 조정하거나 데이터 품질을 확인하세요.")

    # 다시 타겟 변수와 피처 분리
    y_clean = df_clean['last_ms'].copy()
    df_features_clean = df_clean.drop('last_ms', axis=1)
    
    # 타겟 변수를 제외한 피처만으로 이상치 탐지
    feature_cols = [col for col in df_features_clean.columns if col not in ['plan_id', 'query_id']]
    numeric_cols_iso = df_features_clean[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
    
    # 1. 피처 기반 Isolation Forest
    if len(numeric_cols_iso) > 0:
        iso_forest = IsolationForest(contamination='auto', random_state=42)
        outlier_mask = iso_forest.fit_predict(df_features_clean[numeric_cols_iso]) == -1
        print(f"  피처 기반 Isolation Forest 이상치: {outlier_mask.sum()}개")
        
        # 이상치를 중앙값으로 대체
        for col in numeric_cols_iso:
            if outlier_mask.sum() > 0:
                median_val = df_features_clean[col].median()
                df_features_clean.loc[outlier_mask, col] = median_val
    
    # 2. 타겟 변수 변환 (별도 처리)
    y_log = np.log1p(y_clean)
    y_boxcox = np.zeros_like(y_clean, dtype=float)
    
    try:
        positive_mask = y_clean > 0
        if positive_mask.sum() > 0:
            # Box-Cox 변환은 양수 값만 처리 가능. 0을 포함하는 경우, 1을 더해 안정성 확보
            transformed_data, _ = boxcox(y_clean[positive_mask].astype(float) + 1)
            y_boxcox[positive_mask] = transformed_data
    except Exception as e:
        print(f"  Box-Cox 변환 실패: {e}. 로그 변환으로 대체합니다.")
        y_boxcox = y_log
    
    # 변환된 타겟 변수 저장 (나중에 사용)
    df_features_clean['target_log'] = y_log
    df_features_clean['target_boxcox'] = y_boxcox
    
    return df_features_clean, y_clean

def improved_missing_value_handling_safe(df):
    """타겟 변수 제외한 결측값 처리"""
    
    print(f"  처리 전 결측값: {df.isnull().sum().sum()}개")
    
    # 1. 수치형 컬럼만 선택 (타겟 변수 제외)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [col for col in numeric_cols if col not in ['plan_id', 'query_id', 'target_log', 'target_boxcox']]
    
    # 2. KNN 기반 결측값 대체 (타겟 변수 제외)
    if len(numeric_cols) > 0:
        knn_imputer = KNNImputer(n_neighbors=5)
        df[numeric_cols] = knn_imputer.fit_transform(df[numeric_cols])
    
    # 3. 도메인 지식 기반 기본값 설정
    plan_features = ['num_nodes', 'num_edges', 'total_estimated_cost', 'num_physical_ops']
    for col in plan_features:
        if col in df.columns:
            df[col] = df[col].fillna(0)
    
    # 4. 문자열 컬럼 처리
    string_cols = df.select_dtypes(include=['object']).columns
    for col in string_cols:
        if col not in ['plan_id', 'query_id']:
            df[col] = df[col].fillna('unknown')
    
    print(f"  처리 후 결측값: {df.isnull().sum().sum()}개")
    
    return df

def add_safe_domain_features(df):
    """타겟 변수 제외한 안전한 도메인 피처 추가"""
    
    # 1. 리소스 효율성 피처 (타겟 변수 제외)
    if 'last_cpu_ms' in df.columns and 'avg_ms' in df.columns:
        df['cpu_efficiency'] = df['last_cpu_ms'] / (df['avg_ms'] + 1e-6)
    
    if 'last_reads' in df.columns and 'avg_ms' in df.columns:
        df['io_efficiency'] = df['last_reads'] / (df['avg_ms'] + 1e-6)
    
    # 2. 복잡도 점수 (타겟 변수 제외)
    complexity_features = ['num_nodes', 'num_edges', 'num_logical_ops', 'num_physical_ops']
    available_complexity = [col for col in complexity_features if col in df.columns]
    
    if available_complexity:
        df['complexity_score'] = df[available_complexity].sum(axis=1)
        df['normalized_complexity'] = df['complexity_score'] / (df['complexity_score'].max() + 1e-6)
    
    # 3. 리소스 집약도 (타겟 변수 제외)
    resource_features = ['max_used_mem_kb', 'last_cpu_ms', 'last_reads']
    available_resources = [col for col in resource_features if col in df.columns]
    
    if available_resources:
        df['resource_intensity'] = df[available_resources].sum(axis=1)
        df['is_resource_intensive'] = (df['resource_intensity'] > df['resource_intensity'].quantile(0.8)).astype(int)
    
    # 4. 병렬 처리 효율성 (타겟 변수 제외)
    if 'max_dop' in df.columns and 'avg_ms' in df.columns:
        df['parallel_efficiency'] = df['max_dop'] / (df['avg_ms'] + 1e-6)
        df['is_parallel_efficient'] = (df['parallel_efficiency'] > df['parallel_efficiency'].quantile(0.7)).astype(int)
    
    return df

def add_safe_clustering_features(df):
    """타겟 변수 제외한 안전한 클러스터링 피처 추가"""
    
    # 클러스터링에 사용할 피처 선택 (타겟 변수 완전 제외)
    clustering_features = [
        'num_nodes', 'num_edges', 'num_logical_ops', 'num_physical_ops',
        'total_estimated_cost', 'avg_ms', 'last_cpu_ms', 'last_reads',
        'max_used_mem_kb', 'max_dop', 'tree_depth', 'join_complexity',
        'index_usage_score', 'memory_intensity', 'operator_diversity',
        'cpu_efficiency', 'io_efficiency', 'complexity_score', 'resource_intensity'
    ]
    
    # 타겟 변수 관련 피처 완전 제외
    excluded_features = ['last_ms', 'target_log', 'target_boxcox', 'cluster_avg_ms_mean', 'cluster_avg_ms_std']
    available_features = [col for col in clustering_features if col in df.columns and col not in excluded_features]
    
    if len(available_features) >= 3:
        # 데이터 정규화
        scaler = StandardScaler()
        X_cluster = scaler.fit_transform(df[available_features].fillna(0))
        
        # K-means 클러스터링
        kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
        df['query_cluster'] = kmeans.fit_predict(X_cluster)
        
        # 클러스터별 통계 (타겟 변수 완전 제외)
        cluster_stats = df.groupby('query_cluster')[available_features].agg(['mean', 'std']).reset_index()
        
        # 클러스터 특성 추가 (타겟 변수 관련 피처 제외)
        for feature in available_features:
            if feature not in excluded_features:
                df[f'cluster_{feature}_mean'] = df['query_cluster'].map(cluster_stats.set_index('query_cluster')[feature]['mean'])
                df[f'cluster_{feature}_std'] = df['query_cluster'].map(cluster_stats.set_index('query_cluster')[feature]['std'])
    
    return df

def improved_feature_scaling(df):
    """개선된 피처 정규화"""
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [col for col in numeric_cols if col not in ['plan_id', 'query_id', 'target_log', 'target_boxcox']]
    
    # 피처별 최적 스케일링 방법 적용
    for col in numeric_cols:
        if df[col].nunique() > 1:  # 상수가 아닌 경우만
            # QuantileTransformer 적용
            qt = QuantileTransformer(output_distribution='normal', random_state=42)
            df[f'{col}_qt'] = qt.fit_transform(df[[col]])
            
            # PowerTransformer 적용 (Yeo-Johnson)
            try:
                pt = PowerTransformer(method='yeo-johnson', standardize=True)
                df[f'{col}_pt'] = pt.fit_transform(df[[col]])
            except:
                df[f'{col}_pt'] = df[col]
    
    return df

def safe_feature_selection(df, y):
    """안전한 피처 선택"""
    
    # 수치형 컬럼만 선택 (타겟 변수 완전 제외)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    excluded_cols = ['plan_id', 'query_id', 'last_ms', 'target_log', 'target_boxcox']
    feature_cols = [col for col in numeric_cols if col not in excluded_cols]
    
    # 원본 피처만 사용 (변환된 피처 제외)
    original_features = [col for col in feature_cols if not col.endswith('_qt') and not col.endswith('_pt')]
    
    # plan_xml과 같은 문자열 컬럼도 보존
    string_cols = df.select_dtypes(include=['object']).columns.tolist()
    string_cols = [col for col in string_cols if col not in ['plan_id', 'query_id']]
    
    # 모든 컬럼을 보존 (피처 선택을 하지 않음)
    keep_cols = original_features + string_cols + ['plan_id', 'query_id', 'target_log', 'target_boxcox']
    df_selected = df[keep_cols].copy()
    
    print(f"  피처 선택 완료: {len(keep_cols)}개 컬럼 보존")
    
    return df_selected

def main():
    """메인 실행 함수"""
    try:
        preprocessed_df = preprocess_data()
        print(f"\n✅ 전처리 완료!")
        print(f"다음 단계: python enhanced_train.py")
    except Exception as e:
        print(f"❌ 전처리 실패: {e}")
        raise

if __name__ == "__main__":
    main()
