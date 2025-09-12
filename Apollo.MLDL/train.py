import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from config import TrainConfig
from model import build_model, save_model

def train(df_feat: pd.DataFrame, cfg: TrainConfig, out_dir: str) -> dict:
    y = df_feat[cfg.target]
    X = df_feat.drop(columns=[cfg.target, "plan_id"])
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=cfg.test_size, random_state=cfg.random_state
    )
    model = build_model()
    model.fit(X_train, y_train)
    pred = model.predict(X_val)
    rmse = mean_squared_error(y_val, pred, squared=False)
    path = save_model(model, out_dir)
    return {"rmse": rmse, "model_path": path, "n_train": len(X_train), "n_val": len(X_val)}