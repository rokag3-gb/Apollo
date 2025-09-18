from xgboost import XGBRegressor
from joblib import dump, load
from pathlib import Path
from config import ModelConfig

def build_model(cfg: ModelConfig = None) -> XGBRegressor:
    if cfg is None:
        cfg = ModelConfig()
    
    return XGBRegressor(
        n_estimators=cfg.n_estimators,
        max_depth=cfg.max_depth,
        learning_rate=cfg.learning_rate,
        subsample=cfg.subsample,
        colsample_bytree=cfg.colsample_bytree,
        tree_method=cfg.tree_method,
        random_state=cfg.random_state,
        n_jobs=cfg.n_jobs,
    )

def save_model(model, out_dir: str, name: str = "xgb_reg.joblib") -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    path = str(Path(out_dir) / name)
    dump(model, path)
    return path

def load_model(path: str):
    return load(path)