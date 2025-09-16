import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

def enhanced_evaluate(model_path: str, scaler_path: str, features_path: str, target_path: str) -> dict:
    """고급 모델을 평가합니다."""
    
    print("피처 전처리 시작...")
    
    # 1. 피처 데이터와 타겟 데이터 로드
    X = pd.read_parquet(features_path)
    y_df = pd.read_parquet(target_path)
    y = y_df['last_ms'] if 'last_ms' in y_df.columns else y_df.iloc[:, 0]
    
    print(f"총 피처 수: {X.shape[1]}")
    print(f"총 샘플 수: {len(X)}")
    
    # 2. 스케일러 로드 및 적용
    print("스케일러 로딩 중...")
    scaler = joblib.load(scaler_path)
    X_scaled = scaler.transform(X)
    
    # 3. 모델 로드
    print("모델 로딩 중...")
    model = joblib.load(model_path)
    
    # 4. 예측 수행
    print("예측 수행 중...")
    pred = model.predict(X_scaled)
    
    # 5. 메트릭 계산
    rmse = np.sqrt(mean_squared_error(y, pred))
    mae = mean_absolute_error(y, pred)
    r2 = r2_score(y, pred)
    
    # MAPE 계산 (0으로 나누기 방지)
    mape = np.mean(np.abs((y - pred) / np.maximum(y, 1e-8))) * 100
    
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
        "n": len(X),
        "n_features": X_scaled.shape[1]
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 5:
        print("사용법: python enhanced_evaluate.py <model_path> <scaler_path> <features_path> <target_path>")
        sys.exit(1)
    
    model_path = sys.argv[1]
    scaler_path = sys.argv[2]
    features_path = sys.argv[3]
    target_path = sys.argv[4]
    
    # 평가 수행
    results = enhanced_evaluate(model_path, scaler_path, features_path, target_path)
    
    # 결과 출력
    import json
    print(json.dumps(results, ensure_ascii=False, indent=2))
