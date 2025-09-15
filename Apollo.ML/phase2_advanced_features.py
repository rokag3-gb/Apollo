# -*- coding: utf-8 -*-
"""
Phase 2: 고급 피처 엔지니어링 (R² 0.2~0.3 → 0.4~0.5)
"""

import pandas as pd
import numpy as np
import networkx as nx
from datetime import datetime
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from xgboost import XGBRegressor
import warnings
warnings.filterwarnings('ignore')

def phase2_advanced_feature_engineering():
    """Phase 2: 고급 피처 엔지니어링"""
    
    print("=== Phase 2: 고급 피처 엔지니어링 시작 ===")
    
    # 1. 데이터 로드
    df = pd.read_parquet("artifacts/enhanced_features.parquet")
    print(f"원본 데이터 크기: {df.shape}")
    
    # 2. 실행계획 구조 분석 강화
    print("\n1. 실행계획 구조 분석 강화...")
    df = enhanced_plan_analysis(df)
    
    # 3. 시계열 특성 추가
    print("\n2. 시계열 특성 추가...")
    df = add_temporal_features(df)
    
    # 4. 도메인 특화 피처
    print("\n3. 도메인 특화 피처...")
    df = add_domain_features(df)
    
    # 5. 클러스터링 기반 피처
    print("\n4. 클러스터링 기반 피처...")
    df = add_clustering_features(df)
    
    # 6. 모델 훈련 및 평가
    print("\n5. 고급 모델 훈련...")
    results = train_advanced_model(df)
    
    return results

def enhanced_plan_analysis(df):
    """실행계획 구조 분석 강화"""
    
    # 실행계획 XML에서 추가 특성 추출
    plan_features = []
    
    for idx, row in df.iterrows():
        if idx % 1000 == 0:
            print(f"  실행계획 분석 중: {idx + 1}/{len(df)}")
        
        try:
            from plan_graph import planxml_to_graph
            g = planxml_to_graph(row["plan_xml"])
            
            # 1. 실행계획 트리 깊이
            if g.number_of_nodes() > 0:
                # 최장 경로 길이 계산
                longest_path = 0
                for node in g.nodes():
                    if g.in_degree(node) == 0:  # 루트 노드
                        path_length = nx.single_source_shortest_path_length(g, node)
                        longest_path = max(longest_path, max(path_length.values()) if path_length else 0)
                
                plan_features.append({
                    'plan_id': row['plan_id'],
                    'tree_depth': longest_path,
                    'max_parallel_levels': calculate_max_parallel_levels(g),
                    'join_complexity': calculate_join_complexity(g),
                    'index_usage_score': calculate_index_usage_score(g),
                    'memory_intensity': calculate_memory_intensity(g)
                })
            else:
                plan_features.append({
                    'plan_id': row['plan_id'],
                    'tree_depth': 0,
                    'max_parallel_levels': 0,
                    'join_complexity': 0,
                    'index_usage_score': 0,
                    'memory_intensity': 0
                })
                
        except Exception as e:
            plan_features.append({
                'plan_id': row['plan_id'],
                'tree_depth': 0,
                'max_parallel_levels': 0,
                'join_complexity': 0,
                'index_usage_score': 0,
                'memory_intensity': 0
            })
    
    # 피처를 DataFrame으로 변환
    plan_df = pd.DataFrame(plan_features)
    
    # 원본 데이터와 병합
    df = df.merge(plan_df, on='plan_id', how='left')
    
    return df

def calculate_max_parallel_levels(g):
    """최대 병렬 처리 레벨 계산"""
    parallel_levels = 0
    for node, attrs in g.nodes(data=True):
        if attrs.get('Parallel', False):
            parallel_levels += 1
    return parallel_levels

def calculate_join_complexity(g):
    """조인 복잡도 계산"""
    join_ops = 0
    for node, attrs in g.nodes(data=True):
        if 'PhysicalOp' in attrs:
            op = attrs['PhysicalOp'].lower()
            if 'join' in op or 'merge' in op or 'hash' in op:
                join_ops += 1
    return join_ops

def calculate_index_usage_score(g):
    """인덱스 사용 점수 계산"""
    index_ops = 0
    total_ops = g.number_of_nodes()
    
    for node, attrs in g.nodes(data=True):
        if 'PhysicalOp' in attrs:
            op = attrs['PhysicalOp'].lower()
            if 'scan' in op or 'seek' in op:
                index_ops += 1
    
    return index_ops / total_ops if total_ops > 0 else 0

def calculate_memory_intensity(g):
    """메모리 집약도 계산"""
    memory_ops = 0
    for node, attrs in g.nodes(data=True):
        if 'PhysicalOp' in attrs:
            op = attrs['PhysicalOp'].lower()
            if 'sort' in op or 'hash' in op or 'spool' in op:
                memory_ops += 1
    return memory_ops

def add_temporal_features(df):
    """시계열 특성 추가"""
    
    # 1. 시간대별 특성
    if 'last_exec_time' in df.columns:
        df['last_exec_time'] = pd.to_datetime(df['last_exec_time'])
        df['hour_of_day'] = df['last_exec_time'].dt.hour
        df['day_of_week'] = df['last_exec_time'].dt.dayofweek
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        df['is_business_hours'] = ((df['hour_of_day'] >= 9) & (df['hour_of_day'] <= 18)).astype(int)
    
    # 2. 쿼리 실행 빈도 특성
    if 'query_id' in df.columns:
        query_counts = df['query_id'].value_counts()
        df['query_frequency'] = df['query_id'].map(query_counts)
        df['is_high_frequency'] = (df['query_frequency'] > query_counts.quantile(0.8)).astype(int)
    
    # 3. 성능 트렌드 특성
    if 'avg_ms' in df.columns and 'last_ms' in df.columns:
        df['performance_trend'] = df['last_ms'] / (df['avg_ms'] + 1e-6)
        df['is_performance_degrading'] = (df['performance_trend'] > 1.5).astype(int)
    
    return df

def add_domain_features(df):
    """도메인 특화 피처 추가"""
    
    # 1. 리소스 효율성 피처
    if 'last_cpu_ms' in df.columns and 'last_ms' in df.columns:
        df['cpu_efficiency'] = df['last_cpu_ms'] / (df['last_ms'] + 1e-6)
    
    if 'last_reads' in df.columns and 'last_ms' in df.columns:
        df['io_efficiency'] = df['last_reads'] / (df['last_ms'] + 1e-6)
    
    # 2. 복잡도 점수
    complexity_features = ['num_nodes', 'num_edges', 'num_logical_ops', 'num_physical_ops']
    available_complexity = [col for col in complexity_features if col in df.columns]
    
    if available_complexity:
        df['complexity_score'] = df[available_complexity].sum(axis=1)
        df['normalized_complexity'] = df['complexity_score'] / df['complexity_score'].max()
    
    # 3. 리소스 집약도
    resource_features = ['max_used_mem_kb', 'last_cpu_ms', 'last_reads']
    available_resources = [col for col in resource_features if col in df.columns]
    
    if available_resources:
        df['resource_intensity'] = df[available_resources].sum(axis=1)
        df['is_resource_intensive'] = (df['resource_intensity'] > df['resource_intensity'].quantile(0.8)).astype(int)
    
    # 4. 병렬 처리 효율성
    if 'max_dop' in df.columns and 'last_ms' in df.columns:
        df['parallel_efficiency'] = df['max_dop'] / (df['last_ms'] + 1e-6)
        df['is_parallel_efficient'] = (df['parallel_efficiency'] > df['parallel_efficiency'].quantile(0.7)).astype(int)
    
    return df

def add_clustering_features(df):
    """클러스터링 기반 피처 추가"""
    
    # 클러스터링에 사용할 피처 선택
    clustering_features = [
        'num_nodes', 'num_edges', 'num_logical_ops', 'num_physical_ops',
        'total_estimated_cost', 'avg_ms', 'last_cpu_ms', 'last_reads',
        'max_used_mem_kb', 'max_dop'
    ]
    
    available_features = [col for col in clustering_features if col in df.columns]
    
    if len(available_features) >= 3:
        # 데이터 정규화
        scaler = StandardScaler()
        X_cluster = scaler.fit_transform(df[available_features].fillna(0))
        
        # K-means 클러스터링
        kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
        df['query_cluster'] = kmeans.fit_predict(X_cluster)
        
        # 클러스터별 통계
        cluster_stats = df.groupby('query_cluster')['last_ms'].agg(['mean', 'std', 'count']).reset_index()
        cluster_stats.columns = ['query_cluster', 'cluster_avg_ms', 'cluster_std_ms', 'cluster_count']
        
        df = df.merge(cluster_stats, on='query_cluster', how='left')
        
        # 클러스터 내 상대적 성능
        df['cluster_performance_rank'] = df.groupby('query_cluster')['last_ms'].rank(pct=True)
        df['is_cluster_outlier'] = (df['cluster_performance_rank'] > 0.9).astype(int)
    
    return df

def train_advanced_model(df):
    """고급 모델 훈련"""
    
    # 피처 선택 (수치형 컬럼만)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [col for col in numeric_cols if col not in ['plan_id', 'query_id', 'last_ms']]
    
    X = df[feature_cols]
    y = df['last_ms']
    
    # 훈련/검증 분할
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 스케일링
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # 모델 훈련
    model = XGBRegressor(
        n_estimators=1000,
        max_depth=10,
        learning_rate=0.01,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train_scaled, y_train)
    
    # 예측 및 평가
    y_pred = model.predict(X_val_scaled)
    
    rmse = np.sqrt(mean_squared_error(y_val, y_pred))
    r2 = r2_score(y_val, y_pred)
    
    print(f"  RMSE: {rmse:.2f}")
    print(f"  R²: {r2:.4f}")
    
    # 피처 중요도 분석
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(f"\n  상위 10개 피처 중요도:")
    print(feature_importance.head(10))
    
    return {
        'rmse': rmse,
        'r2': r2,
        'model': model,
        'scaler': scaler,
        'feature_importance': feature_importance
    }

def main():
    """메인 실행 함수"""
    results = phase2_advanced_feature_engineering()
    
    print(f"\n=== Phase 2 결과 ===")
    print(f"R²: {results['r2']:.4f}")
    print(f"RMSE: {results['rmse']:.2f}")
    
    # 모델 저장
    import joblib
    joblib.dump(results['model'], 'artifacts/phase2_model.joblib')
    joblib.dump(results['scaler'], 'artifacts/phase2_scaler.joblib')
    results['feature_importance'].to_csv('artifacts/phase2_feature_importance.csv', index=False)
    
    print(f"\n모델 저장 완료: artifacts/phase2_model.joblib")

if __name__ == "__main__":
    main()
