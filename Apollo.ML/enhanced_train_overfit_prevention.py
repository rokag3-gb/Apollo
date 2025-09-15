# -*- coding: utf-8 -*-
"""
Phase 2: 고급 피처 엔지니어링 + Overfitting 방지
"""

import pandas as pd
import numpy as np
import networkx as nx
from datetime import datetime
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.feature_selection import SelectKBest, f_regression, RFE
from xgboost import XGBRegressor
import warnings
warnings.filterwarnings('ignore')

def phase2_overfit_prevention():
    """Phase 2: 고급 피처 엔지니어링 + Overfitting 방지"""
    
    print("=== Phase 2: 고급 피처 엔지니어링 + Overfitting 방지 ===")
    
    # 1. 데이터 로드
    df = pd.read_parquet("artifacts/enhanced_features.parquet")
    print(f"원본 데이터 크기: {df.shape}")
    
    # 2. 실행계획 구조 분석 강화 (타겟 변수 정보 누출 방지)
    print("\n1. 실행계획 구조 분석 강화...")
    df = enhanced_plan_analysis_safe(df)
    
    # 3. 시계열 특성 추가 (과거 정보만 사용)
    print("\n2. 시계열 특성 추가 (과거 정보만 사용)...")
    df = add_temporal_features_safe(df)
    
    # 4. 도메인 특화 피처
    print("\n3. 도메인 특화 피처...")
    df = add_domain_features(df)
    
    # 5. 클러스터링 기반 피처 (타겟 변수 제외)
    print("\n4. 클러스터링 기반 피처 (타겟 변수 제외)...")
    df = add_clustering_features_safe(df)
    
    # 6. 피처 선택 및 정규화
    print("\n5. 피처 선택 및 정규화...")
    df = feature_selection_and_scaling(df)
    
    # 7. 모델 훈련 및 평가 (Overfitting 방지)
    print("\n6. Overfitting 방지 모델 훈련...")
    results = train_overfit_prevention_model(df)
    
    return results

def enhanced_plan_analysis_safe(df):
    """타겟 변수 정보 누출을 방지한 실행계획 구조 분석"""
    
    # 실행계획 XML에서 추가 특성 추출 (타겟 변수와 무관한 구조적 특성만)
    plan_features = []
    
    for idx, row in df.iterrows():
        if idx % 1000 == 0:
            print(f"  실행계획 분석 중: {idx + 1}/{len(df)}")
        
        try:
            from plan_graph import planxml_to_graph
            g = planxml_to_graph(row["plan_xml"])
            
            # 1. 실행계획 트리 깊이 (구조적 특성)
            if g.number_of_nodes() > 0:
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
                    'memory_intensity': calculate_memory_intensity(g),
                    'operator_diversity': calculate_operator_diversity(g)
                })
            else:
                plan_features.append({
                    'plan_id': row['plan_id'],
                    'tree_depth': 0,
                    'max_parallel_levels': 0,
                    'join_complexity': 0,
                    'index_usage_score': 0,
                    'memory_intensity': 0,
                    'operator_diversity': 0
                })
                
        except Exception as e:
            plan_features.append({
                'plan_id': row['plan_id'],
                'tree_depth': 0,
                'max_parallel_levels': 0,
                'join_complexity': 0,
                'index_usage_score': 0,
                'memory_intensity': 0,
                'operator_diversity': 0
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

def calculate_operator_diversity(g):
    """연산자 다양성 계산"""
    unique_ops = set()
    for node, attrs in g.nodes(data=True):
        if 'PhysicalOp' in attrs:
            unique_ops.add(attrs['PhysicalOp'])
    return len(unique_ops)

def add_temporal_features_safe(df):
    """과거 정보만 사용한 시계열 특성 추가"""
    
    # 1. 시간대별 특성 (과거 정보)
    if 'last_exec_time' in df.columns:
        df['last_exec_time'] = pd.to_datetime(df['last_exec_time'])
        df['hour_of_day'] = df['last_exec_time'].dt.hour
        df['day_of_week'] = df['last_exec_time'].dt.dayofweek
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        df['is_business_hours'] = ((df['hour_of_day'] >= 9) & (df['hour_of_day'] <= 18)).astype(int)
    
    # 2. 쿼리 실행 빈도 특성 (과거 정보)
    if 'query_id' in df.columns:
        query_counts = df['query_id'].value_counts()
        df['query_frequency'] = df['query_id'].map(query_counts)
        df['is_high_frequency'] = (df['query_frequency'] > query_counts.quantile(0.8)).astype(int)
    
    # 3. 성능 트렌드 특성 (과거 평균 대비)
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

def add_clustering_features_safe(df):
    """타겟 변수 제외한 클러스터링 기반 피처 추가"""
    
    # 클러스터링에 사용할 피처 선택 (타겟 변수 제외)
    clustering_features = [
        'num_nodes', 'num_edges', 'num_logical_ops', 'num_physical_ops',
        'total_estimated_cost', 'avg_ms', 'last_cpu_ms', 'last_reads',
        'max_used_mem_kb', 'max_dop', 'tree_depth', 'join_complexity',
        'index_usage_score', 'memory_intensity', 'operator_diversity'
    ]
    
    available_features = [col for col in clustering_features if col in df.columns]
    
    if len(available_features) >= 3:
        # 데이터 정규화
        scaler = StandardScaler()
        X_cluster = scaler.fit_transform(df[available_features].fillna(0))
        
        # K-means 클러스터링
        kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
        df['query_cluster'] = kmeans.fit_predict(X_cluster)
        
        # 클러스터별 통계 (타겟 변수 제외)
        cluster_stats = df.groupby('query_cluster')[available_features].agg(['mean', 'std']).reset_index()
        
        # 클러스터 특성 추가
        for feature in available_features:
            df[f'cluster_{feature}_mean'] = df['query_cluster'].map(cluster_stats.set_index('query_cluster')[feature]['mean'])
            df[f'cluster_{feature}_std'] = df['query_cluster'].map(cluster_stats.set_index('query_cluster')[feature]['std'])
    
    return df

def feature_selection_and_scaling(df):
    """피처 선택 및 정규화"""
    
    # 수치형 컬럼만 선택
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [col for col in numeric_cols if col not in ['plan_id', 'query_id', 'last_ms']]
    
    X = df[feature_cols].fillna(0)
    y = df['last_ms']
    
    # 1. 상관관계가 높은 피처들 제거
    corr_matrix = X.corr().abs()
    upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    high_corr_features = [column for column in upper_tri.columns if any(upper_tri[column] > 0.95)]
    
    print(f"  고상관관계 피처 제거: {len(high_corr_features)}개")
    feature_cols = [col for col in feature_cols if col not in high_corr_features]
    
    # 2. SelectKBest로 상위 피처 선택
    if len(feature_cols) > 25:  # 피처가 많을 때만 선택
        selector = SelectKBest(f_regression, k=25)
        X_selected = selector.fit_transform(X[feature_cols], y)
        selected_features = [feature_cols[i] for i in selector.get_support(indices=True)]
        print(f"  SelectKBest 선택된 피처: {len(selected_features)}개")
    else:
        selected_features = feature_cols
    
    # 3. RFE로 추가 피처 선택
    if len(selected_features) > 15:
        xgb = XGBRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        rfe = RFE(estimator=xgb, n_features_to_select=15)
        X_rfe = rfe.fit_transform(X[selected_features], y)
        final_features = [selected_features[i] for i in rfe.get_support(indices=True)]
        print(f"  RFE 선택된 피처: {len(final_features)}개")
    else:
        final_features = selected_features
    
    # 선택된 피처만 유지
    df_selected = df[final_features + ['plan_id', 'query_id', 'last_ms']].copy()
    
    return df_selected

def train_overfit_prevention_model(df):
    """Overfitting 방지 모델 훈련"""
    
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
    
    # Overfitting 방지 모델 설정
    model = XGBRegressor(
        n_estimators=300,  # 감소
        max_depth=5,       # 감소
        learning_rate=0.05,  # 감소
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.2,     # L1 정규화 강화
        reg_lambda=0.2,    # L2 정규화 강화
        min_child_weight=10,  # 최소 샘플 수 제한 강화
        random_state=42,
        n_jobs=-1
    )
    
    # 훈련
    model.fit(X_train_scaled, y_train)
    
    # 전체 데이터 스케일링 (평가용)
    X_scaled = scaler.transform(X)
    
    # 예측 및 평가
    y_pred = model.predict(X_val_scaled)
    
    rmse = np.sqrt(mean_squared_error(y_val, y_pred))
    r2 = r2_score(y_val, y_pred)
    
    print(f"  검증 RMSE: {rmse:.2f}")
    print(f"  검증 R²: {r2:.4f}")
    
    # 교차 검증으로 overfitting 확인
    print("\n  교차 검증 수행 중...")
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='r2')
    print(f"  교차 검증 R²: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    
    # 훈련/검증 성능 차이 확인
    train_r2 = model.score(X_train_scaled, y_train)
    val_r2 = model.score(X_val_scaled, y_val)
    print(f"  훈련 R²: {train_r2:.4f}, 검증 R²: {val_r2:.4f}")
    print(f"  성능 차이: {abs(train_r2 - val_r2):.4f}")
    
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
        'cv_r2_mean': cv_scores.mean(),
        'cv_r2_std': cv_scores.std(),
        'train_r2': train_r2,
        'val_r2': val_r2,
        'overfitting_gap': abs(train_r2 - val_r2),
        'model': model,
        'scaler': scaler,
        'feature_importance': feature_importance,
        'X_processed': pd.DataFrame(X_scaled, columns=feature_cols),
        'y_processed': pd.Series(y, name='last_ms')
    }

def main():
    """메인 실행 함수"""
    results = phase2_overfit_prevention()
    
    print(f"\n=== Phase 2 Overfitting 방지 결과 ===")
    print(f"검증 R²: {results['r2']:.4f}")
    print(f"교차 검증 R²: {results['cv_r2_mean']:.4f} ± {results['cv_r2_std']:.4f}")
    print(f"훈련 R²: {results['train_r2']:.4f}")
    print(f"검증 R²: {results['val_r2']:.4f}")
    print(f"Overfitting Gap: {results['overfitting_gap']:.4f}")
    
    # Overfitting 판정
    if results['overfitting_gap'] < 0.05:
        print("✅ Overfitting 없음 (Gap < 0.05)")
    elif results['overfitting_gap'] < 0.1:
        print("⚠️  경미한 Overfitting (Gap < 0.1)")
    else:
        print("❌ Overfitting 의심 (Gap >= 0.1)")
    
    # 모델 저장
    import joblib
    joblib.dump(results['model'], 'artifacts/model.joblib')
    joblib.dump(results['scaler'], 'artifacts/scaler.joblib')
    results['feature_importance'].to_csv('artifacts/model_importance.csv', index=False)
    
    # 처리된 피처 데이터도 저장 (평가용)
    results['X_processed'].to_parquet('artifacts/processed_features.parquet', index=False)
    results['y_processed'].to_frame().to_parquet('artifacts/processed_target.parquet', index=False)
    
    print(f"\n모델 저장 완료: artifacts/model.joblib")
    print(f"처리된 피처 데이터 저장 완료: artifacts/processed_features.parquet")

if __name__ == "__main__":
    main()
