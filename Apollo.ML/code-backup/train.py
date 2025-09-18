import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import LabelEncoder
from config import TrainConfig, ModelConfig, FeatureConfig
from model import build_model, save_model

def preprocess_features(df_feat: pd.DataFrame, feature_cfg: FeatureConfig) -> pd.DataFrame:
    """피처 전처리를 수행합니다."""
    df_processed = df_feat.copy()
    
    # 문자열 컬럼을 원핫인코딩
    if feature_cfg.encode_categorical:
        categorical_cols = df_processed.select_dtypes(include=['object']).columns
        categorical_cols = [col for col in categorical_cols if col not in ['plan_id']]
        
        for col in categorical_cols:
            le = LabelEncoder()
            df_processed[col] = le.fit_transform(df_processed[col].astype(str))
    
    return df_processed

def train(df_feat: pd.DataFrame, train_cfg: TrainConfig, model_cfg: ModelConfig, 
          feature_cfg: FeatureConfig, out_dir: str) -> dict:
    """모델을 훈련합니다."""
    print("피처 전처리 시작...")
    df_processed = preprocess_features(df_feat, feature_cfg)
    
    # 타겟과 피처 분리
    y = df_processed[train_cfg.target]
    X = df_processed.drop(columns=[train_cfg.target, "plan_id"])
    
    print(f"총 피처 수: {X.shape[1]}")
    print(f"총 샘플 수: {X.shape[0]}")
    
    # 훈련/검증 데이터 분할
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=train_cfg.test_size, random_state=train_cfg.random_state
    )
    
    print(f"훈련 데이터: {X_train.shape[0]}개")
    print(f"검증 데이터: {X_val.shape[0]}개")
    
    # 모델 생성 및 훈련
    print("모델 훈련 시작...")
    model = build_model(model_cfg)
    model.fit(X_train, y_train)
    
    # 예측 및 평가
    print("모델 평가 중...")
    pred = model.predict(X_val)
    
    rmse = np.sqrt(mean_squared_error(y_val, pred))
    mae = mean_absolute_error(y_val, pred)
    r2 = r2_score(y_val, pred)
    
    # 모델 저장
    path = save_model(model, out_dir)
    
    # 피처 중요도 저장
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    importance_path = f"{out_dir}/feature_importance.csv"
    feature_importance.to_csv(importance_path, index=False)
    
    print(f"모델 저장됨: {path}")
    print(f"피처 중요도 저장됨: {importance_path}")
    print(f"RMSE: {rmse:.4f}")
    print(f"MAE: {mae:.4f}")
    print(f"R²: {r2:.4f}")
    
    return {
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "model_path": path,
        "feature_importance_path": importance_path,
        "n_train": len(X_train),
        "n_val": len(X_val),
        "n_features": X.shape[1]
    }