import os, yaml
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Union

load_dotenv()

@dataclass
class DBConfig:
    server: str
    database: str
    username: str
    password: str
    driver: str = "ODBC Driver 17 for SQL Server"
    encrypt: str = "yes"
    trust_server_certificate: str = "yes"

@dataclass
class TrainConfig:
    target: str = "last_ms"
    test_size: float = 0.2
    random_state: int = 42

@dataclass
class ModelConfig:
    n_estimators: int = 500
    max_depth: int = 6
    learning_rate: float = 0.05
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    tree_method: str = "hist"
    random_state: int = 42
    n_jobs: int = -1

@dataclass
class FeatureConfig:
    include_graph_features: bool = True
    include_cost_features: bool = True
    include_operator_features: bool = True
    include_index_features: bool = True
    encode_categorical: bool = True

@dataclass
class AppConfig:
    db: DBConfig
    train: TrainConfig
    model: ModelConfig
    features: FeatureConfig
    output_dir: str = "./artifacts"

def load_config(path: Union[str, None] = None) -> AppConfig:
    cfg = {}
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

    db = DBConfig(
        server=cfg.get("db", {}).get("server", os.getenv("DB_SERVER", "vm-apollo-db2.koreacentral.cloudapp.azure.com;11433")),
        database=cfg.get("db", {}).get("database", os.getenv("DB_NAME", "TradingDB")),
        username=cfg.get("db", {}).get("username", os.getenv("DB_USER", "apollo")),
        password=cfg.get("db", {}).get("password", os.getenv("DB_PWD", "dkvhffhelqldbwj1!")),
        driver=cfg.get("db", {}).get("driver", os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")),
    )
    
    train = TrainConfig(
        target=cfg.get("train", {}).get("target", "last_ms"),
        test_size=float(cfg.get("train", {}).get("test_size", 0.2)),
        random_state=int(cfg.get("train", {}).get("random_state", 42)),
    )
    
    model = ModelConfig(
        n_estimators=int(cfg.get("model", {}).get("n_estimators", 500)),
        max_depth=int(cfg.get("model", {}).get("max_depth", 6)),
        learning_rate=float(cfg.get("model", {}).get("learning_rate", 0.05)),
        subsample=float(cfg.get("model", {}).get("subsample", 0.8)),
        colsample_bytree=float(cfg.get("model", {}).get("colsample_bytree", 0.8)),
        tree_method=cfg.get("model", {}).get("tree_method", "hist"),
        random_state=int(cfg.get("model", {}).get("random_state", 42)),
        n_jobs=int(cfg.get("model", {}).get("n_jobs", -1)),
    )
    
    features = FeatureConfig(
        include_graph_features=cfg.get("features", {}).get("include_graph_features", True),
        include_cost_features=cfg.get("features", {}).get("include_cost_features", True),
        include_operator_features=cfg.get("features", {}).get("include_operator_features", True),
        include_index_features=cfg.get("features", {}).get("include_index_features", True),
        encode_categorical=cfg.get("features", {}).get("encode_categorical", True),
    )
    
    return AppConfig(
        db=db, 
        train=train, 
        model=model,
        features=features,
        output_dir=cfg.get("output_dir", "./artifacts")
    )