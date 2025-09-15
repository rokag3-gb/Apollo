# -*- coding: utf-8 -*-
"""
Phase 3: 앙상블 모델링 (R² 0.4~0.5 → 0.6~0.7)
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor
import warnings
warnings.filterwarnings('ignore')

def phase3_ensemble_modeling():
    """Phase 3: 앙상블 모델링"""
    
    print("=== Phase 3: 앙상블 모델링 시작 ===")
    
    # 1. 데이터 로드
    df = pd.read_parquet("artifacts/enhanced_features.parquet")
    print(f"원본 데이터 크기: {df.shape}")
    
    # 2. 피처 선택 및 전처리
    print("\n1. 피처 선택 및 전처리...")
    X, y = prepare_features(df)
    
    # 3. 개별 모델 훈련
    print("\n2. 개별 모델 훈련...")
    individual_models = train_individual_models(X, y)
    
    # 4. 앙상블 모델 훈련
    print("\n3. 앙상블 모델 훈련...")
    ensemble_results = train_ensemble_models(X, y, individual_models)
    
    # 5. 최적 앙상블 선택
    print("\n4. 최적 앙상블 선택...")
    best_ensemble = select_best_ensemble(ensemble_results)
    
    return best_ensemble

def prepare_features(df):
    """피처 준비"""
    
    # 수치형 컬럼만 선택
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [col for col in numeric_cols if col not in ['plan_id', 'query_id', 'last_ms']]
    
    X = df[feature_cols].fillna(0)
    y = df['last_ms']
    
    print(f"  피처 수: {X.shape[1]}")
    print(f"  샘플 수: {X.shape[0]}")
    
    return X, y

def train_individual_models(X, y):
    """개별 모델 훈련"""
    
    # 훈련/검증 분할
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 스케일링
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    models = {}
    
    # 1. XGBoost
    print("  XGBoost 훈련 중...")
    xgb = XGBRegressor(
        n_estimators=1000,
        max_depth=8,
        learning_rate=0.01,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1
    )
    xgb.fit(X_train_scaled, y_train)
    xgb_pred = xgb.predict(X_val_scaled)
    xgb_r2 = r2_score(y_val, xgb_pred)
    print(f"    XGBoost R²: {xgb_r2:.4f}")
    models['XGBoost'] = {'model': xgb, 'r2': xgb_r2, 'predictions': xgb_pred}
    
    # 2. LightGBM
    print("  LightGBM 훈련 중...")
    lgb = LGBMRegressor(
        n_estimators=1000,
        max_depth=8,
        learning_rate=0.01,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbose=-1
    )
    lgb.fit(X_train_scaled, y_train)
    lgb_pred = lgb.predict(X_val_scaled)
    lgb_r2 = r2_score(y_val, lgb_pred)
    print(f"    LightGBM R²: {lgb_r2:.4f}")
    models['LightGBM'] = {'model': lgb, 'r2': lgb_r2, 'predictions': lgb_pred}
    
    # 3. CatBoost
    print("  CatBoost 훈련 중...")
    cat = CatBoostRegressor(
        iterations=1000,
        depth=8,
        learning_rate=0.01,
        subsample=0.8,
        colsample_bylevel=0.8,
        random_seed=42,
        verbose=False
    )
    cat.fit(X_train_scaled, y_train)
    cat_pred = cat.predict(X_val_scaled)
    cat_r2 = r2_score(y_val, cat_pred)
    print(f"    CatBoost R²: {cat_r2:.4f}")
    models['CatBoost'] = {'model': cat, 'r2': cat_r2, 'predictions': cat_pred}
    
    # 4. Random Forest
    print("  Random Forest 훈련 중...")
    rf = RandomForestRegressor(
        n_estimators=500,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)  # 스케일링 없이
    rf_pred = rf.predict(X_val)
    rf_r2 = r2_score(y_val, rf_pred)
    print(f"    Random Forest R²: {rf_r2:.4f}")
    models['RandomForest'] = {'model': rf, 'r2': rf_r2, 'predictions': rf_pred}
    
    # 5. Gradient Boosting
    print("  Gradient Boosting 훈련 중...")
    gb = GradientBoostingRegressor(
        n_estimators=500,
        max_depth=8,
        learning_rate=0.01,
        subsample=0.8,
        random_state=42
    )
    gb.fit(X_train, y_train)  # 스케일링 없이
    gb_pred = gb.predict(X_val)
    gb_r2 = r2_score(y_val, gb_pred)
    print(f"    Gradient Boosting R²: {gb_r2:.4f}")
    models['GradientBoosting'] = {'model': gb, 'r2': gb_r2, 'predictions': gb_pred}
    
    # 6. Neural Network
    print("  Neural Network 훈련 중...")
    nn = MLPRegressor(
        hidden_layer_sizes=(100, 50, 25),
        activation='relu',
        solver='adam',
        alpha=0.001,
        learning_rate='adaptive',
        max_iter=1000,
        random_state=42
    )
    nn.fit(X_train_scaled, y_train)
    nn_pred = nn.predict(X_val_scaled)
    nn_r2 = r2_score(y_val, nn_pred)
    print(f"    Neural Network R²: {nn_r2:.4f}")
    models['NeuralNetwork'] = {'model': nn, 'r2': nn_r2, 'predictions': nn_pred}
    
    return models

def train_ensemble_models(X, y, individual_models):
    """앙상블 모델 훈련"""
    
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    ensemble_results = {}
    
    # 1. Voting Regressor (평균)
    print("  Voting Regressor (평균) 훈련 중...")
    voting_avg = VotingRegressor([
        ('xgb', individual_models['XGBoost']['model']),
        ('lgb', individual_models['LightGBM']['model']),
        ('cat', individual_models['CatBoost']['model']),
        ('rf', individual_models['RandomForest']['model']),
        ('gb', individual_models['GradientBoosting']['model'])
    ])
    voting_avg.fit(X_train_scaled, y_train)
    voting_avg_pred = voting_avg.predict(X_val_scaled)
    voting_avg_r2 = r2_score(y_val, voting_avg_pred)
    print(f"    Voting (평균) R²: {voting_avg_r2:.4f}")
    ensemble_results['Voting_Avg'] = {'model': voting_avg, 'r2': voting_avg_r2, 'predictions': voting_avg_pred}
    
    # 2. 가중 평균 앙상블
    print("  가중 평균 앙상블 훈련 중...")
    weights = [individual_models[model]['r2'] for model in ['XGBoost', 'LightGBM', 'CatBoost', 'RandomForest', 'GradientBoosting']]
    weights = np.array(weights) / sum(weights)
    
    weighted_pred = (
        weights[0] * individual_models['XGBoost']['predictions'] +
        weights[1] * individual_models['LightGBM']['predictions'] +
        weights[2] * individual_models['CatBoost']['predictions'] +
        weights[3] * individual_models['RandomForest']['predictions'] +
        weights[4] * individual_models['GradientBoosting']['predictions']
    )
    weighted_r2 = r2_score(y_val, weighted_pred)
    print(f"    가중 평균 R²: {weighted_r2:.4f}")
    ensemble_results['Weighted_Avg'] = {'r2': weighted_r2, 'predictions': weighted_pred, 'weights': weights}
    
    # 3. Stacking 앙상블 (간단한 버전)
    print("  Stacking 앙상블 훈련 중...")
    # 메타 피처 생성
    meta_features = np.column_stack([
        individual_models['XGBoost']['predictions'],
        individual_models['LightGBM']['predictions'],
        individual_models['CatBoost']['predictions'],
        individual_models['RandomForest']['predictions'],
        individual_models['GradientBoosting']['predictions']
    ])
    
    # 메타 모델 (XGBoost)
    meta_model = XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
        n_jobs=-1
    )
    meta_model.fit(meta_features, y_val)
    stacking_pred = meta_model.predict(meta_features)
    stacking_r2 = r2_score(y_val, stacking_pred)
    print(f"    Stacking R²: {stacking_r2:.4f}")
    ensemble_results['Stacking'] = {'model': meta_model, 'r2': stacking_r2, 'predictions': stacking_pred}
    
    return ensemble_results

def select_best_ensemble(ensemble_results):
    """최적 앙상블 선택"""
    
    print("\n=== 앙상블 모델 성능 비교 ===")
    for name, result in ensemble_results.items():
        print(f"{name}: R² = {result['r2']:.4f}")
    
    # 최고 성능 모델 선택
    best_name = max(ensemble_results.keys(), key=lambda x: ensemble_results[x]['r2'])
    best_result = ensemble_results[best_name]
    
    print(f"\n최고 성능 앙상블: {best_name} (R² = {best_result['r2']:.4f})")
    
    return {
        'best_model': best_result,
        'best_name': best_name,
        'all_results': ensemble_results
    }

def main():
    """메인 실행 함수"""
    results = phase3_ensemble_modeling()
    
    print(f"\n=== Phase 3 결과 ===")
    print(f"최고 R²: {results['best_model']['r2']:.4f}")
    print(f"최고 모델: {results['best_name']}")
    
    # 모델 저장
    import joblib
    if 'model' in results['best_model']:
        joblib.dump(results['best_model']['model'], f'artifacts/phase3_{results["best_name"].lower()}_model.joblib')
        print(f"\n모델 저장 완료: artifacts/phase3_{results['best_name'].lower()}_model.joblib")

if __name__ == "__main__":
    main()
