# -*- coding: utf-8 -*-
"""
Phase 1: 데이터 품질 개선 + Overfitting 방지
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import QuantileTransformer, PowerTransformer
from sklearn.impute import KNNImputer
from sklearn.model_selection import train_test_split, cross_val_score, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.feature_selection import SelectKBest, f_regression
from xgboost import XGBRegressor
import warnings
warnings.filterwarnings('ignore')

def phase1_overfit_prevention():
    """Phase 1: 데이터 품질 개선 + Overfitting 방지"""
    
    print("=== Phase 1: 데이터 품질 개선 + Overfitting 방지 ===")
    
    # 1. 데이터 로드
    df = pd.read_parquet("artifacts/enhanced_features.parquet")
    print(f"원본 데이터 크기: {df.shape}")
    
    # 2. 이상치 처리 개선 (타겟 변수 정보 누출 방지)
    print("\n1. 이상치 처리 개선 (타겟 변수 정보 누출 방지)...")
    df_clean = improved_outlier_handling_safe(df)
    
    # 3. 결측값 처리 개선 (타겟 변수 제외)
    print("\n2. 결측값 처리 개선 (타겟 변수 제외)...")
    df_clean = improved_missing_value_handling_safe(df_clean)
    
    # 4. 피처 정규화 개선
    print("\n3. 피처 정규화 개선...")
    df_clean = improved_feature_scaling(df_clean)
    
    # 5. 피처 선택 (복잡도 감소)
    print("\n4. 피처 선택 (복잡도 감소)...")
    df_clean = feature_selection(df_clean)
    
    # 6. 모델 훈련 및 평가 (Overfitting 방지)
    print("\n5. Overfitting 방지 모델 훈련...")
    results = train_overfit_prevention_model(df_clean)
    
    return results

def improved_outlier_handling_safe(df):
    """타겟 변수 정보 누출을 방지한 이상치 처리"""
    
    # 타겟 변수를 제외한 피처만으로 이상치 탐지
    feature_cols = [col for col in df.columns if col not in ['plan_id', 'query_id', 'last_ms']]
    numeric_cols = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
    
    # 1. 피처 기반 Isolation Forest
    if len(numeric_cols) > 0:
        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        outlier_mask = iso_forest.fit_predict(df[numeric_cols]) == -1
        print(f"  피처 기반 Isolation Forest 이상치: {outlier_mask.sum()}개")
    
    # 2. 로그 변환 적용 (타겟 변수)
    df['log_last_ms'] = np.log1p(df['last_ms'])
    
    # 3. Box-Cox 변환 시도 (양수 값만)
    try:
        from scipy.stats import boxcox
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

def improved_missing_value_handling_safe(df):
    """타겟 변수 제외한 결측값 처리"""
    
    print(f"  처리 전 결측값: {df.isnull().sum().sum()}개")
    
    # 1. 수치형 컬럼만 선택 (타겟 변수 제외)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [col for col in numeric_cols if col not in ['plan_id', 'query_id', 'last_ms', 'log_last_ms', 'boxcox_last_ms']]
    
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

def improved_feature_scaling(df):
    """개선된 피처 정규화"""
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [col for col in numeric_cols if col not in ['plan_id', 'query_id', 'last_ms', 'log_last_ms', 'boxcox_last_ms']]
    
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

def feature_selection(df):
    """피처 선택으로 복잡도 감소"""
    
    # 수치형 컬럼만 선택
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [col for col in numeric_cols if col not in ['plan_id', 'query_id', 'last_ms', 'log_last_ms', 'boxcox_last_ms']]
    feature_cols = [col for col in feature_cols if not col.endswith('_qt') and not col.endswith('_pt')]  # 원본 피처만 사용
    
    X = df[feature_cols].fillna(0)
    y = df['last_ms']
    
    # 상관관계가 높은 피처들 제거
    corr_matrix = X.corr().abs()
    upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    high_corr_features = [column for column in upper_tri.columns if any(upper_tri[column] > 0.95)]
    
    print(f"  고상관관계 피처 제거: {len(high_corr_features)}개")
    feature_cols = [col for col in feature_cols if col not in high_corr_features]
    
    # SelectKBest로 상위 피처 선택
    if len(feature_cols) > 20:  # 피처가 많을 때만 선택
        selector = SelectKBest(f_regression, k=20)
        X_selected = selector.fit_transform(X[feature_cols], y)
        selected_features = [feature_cols[i] for i in selector.get_support(indices=True)]
        print(f"  SelectKBest 선택된 피처: {len(selected_features)}개")
    else:
        selected_features = feature_cols
    
    # 선택된 피처만 유지
    df_selected = df[selected_features + ['plan_id', 'query_id', 'last_ms']].copy()
    
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
    qt = QuantileTransformer(output_distribution='normal', random_state=42)
    X_train_scaled = qt.fit_transform(X_train)
    X_val_scaled = qt.transform(X_val)
    
    # Overfitting 방지 모델 설정
    model = XGBRegressor(
        n_estimators=500,  # 감소
        max_depth=6,       # 감소
        learning_rate=0.05,  # 감소
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,     # L1 정규화
        reg_lambda=0.1,    # L2 정규화
        min_child_weight=5,  # 최소 샘플 수 제한
        random_state=42,
        n_jobs=-1
    )
    
    # 조기 종료를 위한 훈련
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_val_scaled, y_val)],
        verbose=False
    )
    
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
        'scaler': qt,
        'feature_importance': feature_importance
    }

def main():
    """메인 실행 함수"""
    results = phase1_overfit_prevention()
    
    print(f"\n=== Phase 1 Overfitting 방지 결과 ===")
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
    joblib.dump(results['model'], 'artifacts/phase1_overfit_prevention_model.joblib')
    joblib.dump(results['scaler'], 'artifacts/phase1_overfit_prevention_scaler.joblib')
    results['feature_importance'].to_csv('artifacts/phase1_overfit_prevention_importance.csv', index=False)
    
    print(f"\n모델 저장 완료: artifacts/phase1_overfit_prevention_model.joblib")

if __name__ == "__main__":
    main()
