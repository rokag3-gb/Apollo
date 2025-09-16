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
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.feature_selection import SelectKBest, f_regression, RFE
from xgboost import XGBRegressor
import warnings
warnings.filterwarnings('ignore')

def phase2_overfit_prevention():
    """Phase 2: 전처리된 데이터로 모델 훈련"""
    
    print("=== Phase 2: 모델 훈련 ===")
    
    # 1. 피처 엔지니어링된 데이터 로드
    try:
        df = pd.read_parquet("artifacts/enhanced_features.parquet")
        print(f"피처 엔지니어링된 데이터 크기: {df.shape}")
    except FileNotFoundError:
        print("❌ 피처 엔지니어링된 데이터가 없습니다. 먼저 enhanced_main.py featurize를 실행하세요.")
        return None
    
    # 2. 모델 훈련
    print("\n1. 모델 훈련...")
    results = train_overfit_prevention_model(df)
    
    return results

# 전처리된 데이터를 사용하므로 추가 전처리 함수들은 제거됨

def train_overfit_prevention_model(df):
    """Overfitting 방지 모델 훈련"""
    
    # 피처 선택 (수치형 컬럼만)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [col for col in numeric_cols if col not in ['plan_id', 'query_id', 'last_ms']]
    
    # 문자열 컬럼 제외 (스케일링할 수 없음)
    string_cols = df.select_dtypes(include=['object']).columns.tolist()
    feature_cols = [col for col in feature_cols if col not in string_cols]
    
    X = df[feature_cols]
    y = df['last_ms']
    
    # 훈련/검증 분할
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 스케일링
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # 안정성 우선 모델 설정 (이전 설정으로 복원)
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
    print("  모델 훈련 중...")
    model.fit(X_train_scaled, y_train)
    
    # 전체 데이터 스케일링 (저장용)
    X_scaled = scaler.transform(X)
    
    # 피처 중요도 분석
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(f"  훈련 완료! 사용된 피처 수: {len(feature_cols)}")
    print(f"  상위 5개 피처: {feature_importance.head()['feature'].tolist()}")
    
    return {
        'model': model,
        'scaler': scaler,
        'feature_importance': feature_importance,
        'feature_cols': feature_cols,
        'X_processed': pd.DataFrame(X_scaled, columns=feature_cols),
        'y_processed': pd.Series(y, name='last_ms'),
        'X_train': X_train,
        'X_val': X_val,
        'y_train': y_train,
        'y_val': y_val
    }

def main():
    """메인 실행 함수"""
    results = phase2_overfit_prevention()
    
    print(f"\n=== Phase 2 모델 훈련 완료 ===")
    print(f"사용된 피처 수: {len(results['feature_cols'])}")
    print(f"훈련 데이터 크기: {results['X_train'].shape}")
    print(f"검증 데이터 크기: {results['X_val'].shape}")
    
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
    print(f"평가를 실행하려면: python enhanced_evaluate.py")

if __name__ == "__main__":
    main()
