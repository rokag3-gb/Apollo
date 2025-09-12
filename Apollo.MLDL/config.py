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
    driver: str = "ODBC Driver 18 for SQL Server"
    encrypt: str = "yes"
    trust_server_certificate: str = "yes"

@dataclass
class TrainConfig:
    target: str = "last_ms"
    test_size: float = 0.2
    random_state: int = 42

@dataclass
class AppConfig:
    db: DBConfig
    train: TrainConfig
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
    return AppConfig(db=db, train=train, output_dir=cfg.get("output_dir", "./artifacts"))