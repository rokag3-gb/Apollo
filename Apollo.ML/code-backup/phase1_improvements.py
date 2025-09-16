# -*- coding: utf-8 -*-
"""
Phase 1: 데이터 품질 개선 (R² 0.089 → 0.2~0.3)
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import QuantileTransformer, PowerTransformer
from sklearn.impute import KNNImputer
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from xgboost import XGBRegressor
import warnings
warnings.filterwarnings('ignore')

def phase1_data_quality_improvements():
    """Phase 1: 데이터 품질 개선 구현"""
    
    print("=== Phase 1: 데이터 품질 개선 시작 ===")
    
    # 1. 데이터 로드
    df = pd.read_parquet("artifacts/enhanced_features.parquet")
    print(f"원본 데이터 크기: {df.shape}")
    
    # 2. 이상치 처리 개선
    print("\n1. 이상치 처리 개선...")
    df_clean = improved_outlier_handling(df)
    
    # 3. 결측값 처리 개선
    print("\n2. 결측값 처리 개선...")
    df_clean = improved_missing_value_handling(df_clean)
    
    # 4. 피처 정규화 개선
    print("\n3. 피처 정규화 개선...")
    df_clean = improved_feature_scaling(df_clean)
    
    # 5. 모델 훈련 및 평가
    print("\n4. 개선된 모델 훈련...")
    results = train_improved_model(df_clean)
    
    return results

def improved_outlier_handling(df):
    """개선된 이상치 처리"""
    
    # 타겟 변수 이상치 처리
    target = df['last_ms']
    
    # 1. Isolation Forest 사용
    iso_forest = IsolationForest(contamination=0.1, random_state=42)
    outlier_mask = iso_forest.fit_predict(df[['last_ms']]) == -1
    
    print(f"  Isolation Forest 이상치: {outlier_mask.sum()}개 ({outlier_mask.sum()/len(df)*100:.1f}%)")
    
    # 2. Z-score 기반 이상치 탐지
    z_scores = np.abs((target - target.mean()) / target.std())
    z_outliers = z_scores > 3
    print(f"  Z-score 이상치: {z_outliers.sum()}개 ({z_outliers.sum()/len(df)*100:.1f}%)")
    
    # 3. 쿼리 패턴별 이상치 임계값 설정
    query_outliers = []
    for query_id in df['query_id'].unique():
        if pd.notna(query_id):
            query_data = df[df['query_id'] == query_id]['last_ms']
            if len(query_data) > 5:  # 충분한 데이터가 있는 경우만
                q1, q3 = query_data.quantile([0.25, 0.75])
                iqr = q3 - q1
                threshold = q3 + 1.5 * iqr
                query_outliers.extend(df[(df['query_id'] == query_id) & (df['last_ms'] > threshold)].index.tolist())
    
    print(f"  쿼리별 이상치: {len(query_outliers)}개")
    
    # 4. 로그 변환 적용
    df['log_last_ms'] = np.log1p(df['last_ms'])
    
    # 5. Box-Cox 변환 시도
    try:
        from scipy.stats import boxcox
        # 양수 값만 사용
        positive_values = df[df['last_ms'] > 0]['last_ms']
        if len(positive_values) > 0:
            boxcox_values, _ = boxcox(positive_values)
            df.loc[df['last_ms'] > 0, 'boxcox_last_ms'] = boxcox_values
            df['boxcox_last_ms'] = df['boxcox_last_ms'].fillna(0)
        else:
            df['boxcox_last_ms'] = 0
    except:
        df['boxcox_last_ms'] = 0
    
    return df

def improved_missing_value_handling(df):
    """개선된 결측값 처리"""
    
    print(f"  처리 전 결측값: {df.isnull().sum().sum()}개")
    
    # 1. 수치형 컬럼만 선택
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [col for col in numeric_cols if col not in ['plan_id', 'query_id']]
    
    # 2. KNN 기반 결측값 대체
    knn_imputer = KNNImputer(n_neighbors=5)
    df[numeric_cols] = knn_imputer.fit_transform(df[numeric_cols])
    
    # 3. 도메인 지식 기반 기본값 설정
    # 실행계획 관련 피처들은 0이 적절
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

def improved_feature_scaling(df):
    """개선된 피처 정규화"""
    
    # 1. QuantileTransformer 사용
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [col for col in numeric_cols if col not in ['plan_id', 'query_id', 'last_ms', 'log_last_ms', 'boxcox_last_ms']]
    
    # 2. 피처별 최적 스케일링 방법 적용
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

def train_improved_model(df):
    """개선된 모델 훈련"""
    
    # 피처 선택 (수치형 컬럼만)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [col for col in numeric_cols if col not in ['plan_id', 'query_id', 'last_ms', 'log_last_ms', 'boxcox_last_ms']]
    feature_cols = [col for col in feature_cols if not col.endswith('_qt') and not col.endswith('_pt')]  # 원본 피처만 사용
    
    X = df[feature_cols]
    y = df['last_ms']
    
    # 훈련/검증 분할
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 스케일링
    qt = QuantileTransformer(output_distribution='normal', random_state=42)
    X_train_scaled = qt.fit_transform(X_train)
    X_val_scaled = qt.transform(X_val)
    
    # 모델 훈련
    model = XGBRegressor(
        n_estimators=1000,
        max_depth=8,
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
        'scaler': qt,
        'feature_importance': feature_importance
    }

def main():
    """메인 실행 함수"""
    results = phase1_data_quality_improvements()
    
    print(f"\n=== Phase 1 결과 ===")
    print(f"R²: {results['r2']:.4f}")
    print(f"RMSE: {results['rmse']:.2f}")
    
    # 모델 저장
    import joblib
    joblib.dump(results['model'], 'artifacts/phase1_model.joblib')
    joblib.dump(results['scaler'], 'artifacts/phase1_scaler.joblib')
    results['feature_importance'].to_csv('artifacts/phase1_feature_importance.csv', index=False)
    
    print(f"\n모델 저장 완료: artifacts/phase1_model.joblib")

if __name__ == "__main__":
    main()
