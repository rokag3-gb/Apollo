import pandas as pd
from sklearn.metrics import mean_squared_error
from model import load_model

def evaluate(model_path: str, df_feat: pd.DataFrame, target_col: str = "last_ms") -> dict:
    model = load_model(model_path)
    y = df_feat[target_col]
    X = df_feat.drop(columns=[target_col, "plan_id"])
    pred = model.predict(X)
    rmse = mean_squared_error(y, pred, squared=False)
    return {"rmse": rmse, "n": len(df_feat)}