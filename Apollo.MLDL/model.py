from xgboost import XGBRegressor
from joblib import dump, load
from pathlib import Path

def build_model() -> XGBRegressor:
    return XGBRegressor(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        tree_method="hist",
        random_state=42,
        n_jobs=-1,
    )

def save_model(model, out_dir: str, name: str = "xgb_reg.joblib") -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    path = str(Path(out_dir) / name)
    dump(model, path)
    return path

def load_model(path: str):
    return load(path)