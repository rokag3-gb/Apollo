# -*- coding: utf-8 -*-
import argparse, json
from pathlib import Path
from config import load_config
from db import connect, fetch_collected_plans
from enhanced_features import enhanced_featurize
from train import train as train_run
from evaluate import evaluate

def cmd_fetch(args):
    cfg = load_config(args.config)
    with connect(cfg.db) as conn:
        df = fetch_collected_plans(conn)
    out = Path(cfg.output_dir) / "collected_plans.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"saved: {out}")

def cmd_featurize(args):
    cfg = load_config(args.config)
    import pandas as pd
    df = pd.read_parquet(Path(cfg.output_dir) / "collected_plans.parquet")
    df_feat = enhanced_featurize(df, cfg.train.target)
    out = Path(cfg.output_dir) / "enhanced_features.parquet"
    df_feat.to_parquet(out, index=False)
    print(f"saved: {out}")

def cmd_train(args):
    cfg = load_config(args.config)
    import pandas as pd
    df_feat = pd.read_parquet(Path(cfg.output_dir) / "enhanced_features.parquet")
    res = train_run(df_feat, cfg.train, cfg.model, cfg.features, cfg.output_dir)
    print(json.dumps(res, ensure_ascii=False, indent=2))

def cmd_eval(args):
    cfg = load_config(args.config)
    import pandas as pd
    df_feat = pd.read_parquet(Path(cfg.output_dir) / "enhanced_features.parquet")
    res = evaluate(args.model, df_feat, cfg.train.target, cfg.features)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    p = argparse.ArgumentParser("Apollo.ML Enhanced")
    p.add_argument("--config", default="config.yaml", help="config.yaml 파일 경로 (기본값: config.yaml)")
    sp = p.add_subparsers(dest="cmd", required=True)

    sp_fetch = sp.add_parser("fetch");     sp_fetch.set_defaults(func=cmd_fetch)
    sp_feat  = sp.add_parser("featurize"); sp_feat.set_defaults(func=cmd_featurize)
    sp_train = sp.add_parser("train");     sp_train.set_defaults(func=cmd_train)
    sp_eval  = sp.add_parser("eval");      sp_eval.add_argument("--model", required=True); sp_eval.set_defaults(func=cmd_eval)

    args = p.parse_args()
    args.func(args)
