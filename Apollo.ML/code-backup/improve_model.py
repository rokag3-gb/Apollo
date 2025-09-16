# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
import warnings
warnings.filterwarnings('ignore')

def clean_and_engineer_features(df_features):
    """데이터 정제 및 피처 엔지니어링을 수행합니다."""
    
    print("=== 피처 정제 및 엔지니어링 시작 ===")
    
    # 1. 결측값 처리
    print("1. 결측값 처리 중...")
    
    # 상수 피처 제거
    constant_features = df_features.select_dtypes(include=[np.number]).nunique() == 1
    constant_cols = constant_features[constant_features].index.tolist()
    print(f"   상수 피처 제거: {len(constant_cols)}개")
    df_clean = df_features.drop(columns=constant_cols)
    
    # 결측값이 50% 이상인 피처 제거
    missing_threshold = 0.5
    high_missing = df_clean.isnull().sum() / len(df_clean) > missing_threshold
    high_missing_cols = high_missing[high_missing].index.tolist()
    print(f"   고결측 피처 제거: {len(high_missing_cols)}개")
    df_clean = df_clean.drop(columns=high_missing_cols)
    
    # 나머지 결측값을 0으로 채움 (실행계획 특성상 0이 적절)
    df_clean = df_clean.fillna(0)
    
    # 2. 타겟 변수 로그 변환
    print("2. 타겟 변수 로그 변환...")
    df_clean['log_last_ms'] = np.log1p(df_clean['last_ms'])
    
    # 3. 피처 엔지니어링
    print("3. 피처 엔지니어링...")
    
    # 비용 관련 피처들
    cost_features = ['total_estimated_cost', 'avg_estimated_cost', 'max_estimated_cost']
    for col in cost_features:
        if col in df_clean.columns:
            df_clean[f'log_{col}'] = np.log1p(df_clean[col])
    
    # 행 수 관련 피처들
    row_features = ['total_rows', 'avg_rows', 'max_rows']
    for col in row_features:
        if col in df_clean.columns:
            df_clean[f'log_{col}'] = np.log1p(df_clean[col])
    
    # 비용 대비 효율성 피처들
    if 'total_estimated_cost' in df_clean.columns and 'total_rows' in df_clean.columns:
        df_clean['cost_per_row'] = df_clean['total_estimated_cost'] / (df_clean['total_rows'] + 1)
        df_clean['log_cost_per_row'] = np.log1p(df_clean['cost_per_row'])
    
    # 그래프 복잡도 피처들
    if 'num_nodes' in df_clean.columns and 'num_edges' in df_clean.columns:
        df_clean['graph_density'] = df_clean['num_edges'] / (df_clean['num_nodes'] * (df_clean['num_nodes'] - 1) + 1)
        df_clean['avg_degree'] = (df_clean['avg_in_degree'] + df_clean['avg_out_degree']) / 2
    
    # 연산자 다양성 피처들
    if 'unique_physical_ops' in df_clean.columns and 'num_physical_ops' in df_clean.columns:
        df_clean['physical_op_diversity'] = df_clean['unique_physical_ops'] / (df_clean['num_physical_ops'] + 1)
    
    if 'unique_logical_ops' in df_clean.columns and 'num_logical_ops' in df_clean.columns:
        df_clean['logical_op_diversity'] = df_clean['unique_logical_ops'] / (df_clean['num_logical_ops'] + 1)
    
    # 4. 이상치 처리
    print("4. 이상치 처리...")
    
    # IQR 방법으로 이상치 탐지
    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
    numeric_cols = [col for col in numeric_cols if col not in ['plan_id', 'last_ms', 'log_last_ms']]
    
    outlier_mask = np.zeros(len(df_clean), dtype=bool)
    
    for col in numeric_cols:
        Q1 = df_clean[col].quantile(0.25)
        Q3 = df_clean[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        col_outliers = (df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)
        outlier_mask |= col_outliers
    
    print(f"   이상치 비율: {outlier_mask.sum() / len(df_clean) * 100:.1f}%")
    
    # 5. 피처 선택
    print("5. 피처 선택...")
    
    # 타겟과의 상관관계가 낮은 피처 제거
    target_corr = df_clean[numeric_cols + ['log_last_ms']].corr()['log_last_ms'].abs()
    low_corr_features = target_corr[target_corr < 0.05].index.tolist()
    low_corr_features = [col for col in low_corr_features if col != 'log_last_ms']
    print(f"   저상관 피처 제거: {len(low_corr_features)}개")
    
    # 최종 피처 선택
    feature_cols = [col for col in numeric_cols if col not in low_corr_features]
    print(f"   최종 피처 수: {len(feature_cols)}")
    
    return df_clean, feature_cols, outlier_mask

def train_improved_models(df_clean, feature_cols, outlier_mask):
    """개선된 모델들을 훈련합니다."""
    
    print("\n=== 개선된 모델 훈련 시작 ===")
    
    # 데이터 준비
    X = df_clean[feature_cols]
    y = df_clean['log_last_ms']  # 로그 변환된 타겟 사용
    
    # 이상치 제거 여부 선택
    if outlier_mask.sum() > 0:
        print(f"이상치 제거: {outlier_mask.sum()}개")
        X_clean = X[~outlier_mask]
        y_clean = y[~outlier_mask]
    else:
        X_clean = X
        y_clean = y
    
    # 훈련/검증 분할
    X_train, X_val, y_train, y_val = train_test_split(
        X_clean, y_clean, test_size=0.2, random_state=42
    )
    
    print(f"훈련 데이터: {X_train.shape[0]}개")
    print(f"검증 데이터: {X_val.shape[0]}개")
    
    # 스케일링
    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # 모델들 정의
    models = {
        'XGBoost': XGBRegressor(
            n_estimators=1000,
            max_depth=8,
            learning_rate=0.01,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        ),
        'LightGBM': LGBMRegressor(
            n_estimators=1000,
            max_depth=8,
            learning_rate=0.01,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        ),
        'RandomForest': RandomForestRegressor(
            n_estimators=500,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        ),
        'GradientBoosting': GradientBoostingRegressor(
            n_estimators=500,
            max_depth=8,
            learning_rate=0.01,
            subsample=0.8,
            random_state=42
        )
    }
    
    results = {}
    
    for name, model in models.items():
        print(f"\n{name} 훈련 중...")
        
        # 모델 훈련
        if name in ['RandomForest', 'GradientBoosting']:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_val)
        else:
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_val_scaled)
        
        # 원래 스케일로 변환
        y_val_original = np.expm1(y_val)
        y_pred_original = np.expm1(y_pred)
        
        # 메트릭 계산
        rmse = np.sqrt(mean_squared_error(y_val_original, y_pred_original))
        mae = mean_absolute_error(y_val_original, y_pred_original)
        r2 = r2_score(y_val_original, y_pred_original)
        
        # 로그 스케일에서의 R²
        r2_log = r2_score(y_val, y_pred)
        
        results[name] = {
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'r2_log': r2_log,
            'model': model,
            'scaler': scaler if name not in ['RandomForest', 'GradientBoosting'] else None
        }
        
        print(f"  RMSE: {rmse:.2f}")
        print(f"  MAE: {mae:.2f}")
        print(f"  R²: {r2:.4f}")
        print(f"  R² (log): {r2_log:.4f}")
    
    return results, X_train, X_val, y_train, y_val

def analyze_feature_importance(results, feature_cols):
    """피처 중요도를 분석합니다."""
    
    print("\n=== 피처 중요도 분석 ===")
    
    for name, result in results.items():
        if hasattr(result['model'], 'feature_importances_'):
            print(f"\n{name} 피처 중요도 (상위 10개):")
            importance_df = pd.DataFrame({
                'feature': feature_cols,
                'importance': result['model'].feature_importances_
            }).sort_values('importance', ascending=False)
            
            print(importance_df.head(10))
            
            # 중요도 시각화
            plt.figure(figsize=(10, 6))
            top_features = importance_df.head(15)
            plt.barh(range(len(top_features)), top_features['importance'])
            plt.yticks(range(len(top_features)), top_features['feature'])
            plt.xlabel('Importance')
            plt.title(f'{name} Feature Importance')
            plt.gca().invert_yaxis()
            plt.tight_layout()
            plt.savefig(f'artifacts/{name.lower()}_importance.png', dpi=300, bbox_inches='tight')
            plt.show()

def main():
    """메인 실행 함수"""
    
    # 데이터 로드
    df_features = pd.read_parquet("artifacts/features.parquet")
    
    # 피처 정제 및 엔지니어링
    df_clean, feature_cols, outlier_mask = clean_and_engineer_features(df_features)
    
    # 개선된 모델 훈련
    results, X_train, X_val, y_train, y_val = train_improved_models(df_clean, feature_cols, outlier_mask)
    
    # 피처 중요도 분석
    analyze_feature_importance(results, feature_cols)
    
    # 최고 성능 모델 선택
    best_model_name = max(results.keys(), key=lambda x: results[x]['r2'])
    best_result = results[best_model_name]
    
    print(f"\n=== 최고 성능 모델: {best_model_name} ===")
    print(f"R²: {best_result['r2']:.4f}")
    print(f"RMSE: {best_result['rmse']:.2f}")
    print(f"MAE: {best_result['mae']:.2f}")
    
    # 모델 저장
    import joblib
    joblib.dump(best_result['model'], f'artifacts/best_model_{best_model_name.lower()}.joblib')
    if best_result['scaler']:
        joblib.dump(best_result['scaler'], f'artifacts/scaler_{best_model_name.lower()}.joblib')
    
    print(f"\n모델 저장 완료: artifacts/best_model_{best_model_name.lower()}.joblib")
    
    return results

if __name__ == "__main__":
    results = main()
