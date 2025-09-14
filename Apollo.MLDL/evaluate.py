import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import LabelEncoder
from model import load_model
from config import FeatureConfig

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

def evaluate(model_path: str, df_feat: pd.DataFrame, target_col: str = "last_ms", 
             feature_cfg: FeatureConfig = None) -> dict:
    """모델을 평가합니다."""
    if feature_cfg is None:
        feature_cfg = FeatureConfig()
    
    print("피처 전처리 시작...")
    df_processed = preprocess_features(df_feat, feature_cfg)
    
    print("모델 로딩 중...")
    model = load_model(model_path)
    
    y = df_processed[target_col]
    X = df_processed.drop(columns=[target_col, "plan_id"])
    
    print("예측 수행 중...")
    pred = model.predict(X)
    
    # 다양한 메트릭 계산
    rmse = np.sqrt(mean_squared_error(y, pred))
    mae = mean_absolute_error(y, pred)
    r2 = r2_score(y, pred)
    
    # 추가 통계
    mape = np.mean(np.abs((y - pred) / y)) * 100 if (y != 0).any() else 0
    
    print(f"평가 완료:")
    print(f"RMSE: {rmse:.4f}")
    print(f"MAE: {mae:.4f}")
    print(f"R²: {r2:.4f}")
    print(f"MAPE: {mape:.2f}%")
    
    return {
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "mape": mape,
        "n": len(df_feat),
        "n_features": X.shape[1]
    }