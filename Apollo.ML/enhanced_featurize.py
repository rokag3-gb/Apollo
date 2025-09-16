# -*- coding: utf-8 -*-
"""
피처 엔지니어링 모듈
전처리된 데이터에 피처 엔지니어링을 적용합니다.
"""

import argparse
import pandas as pd
from pathlib import Path
from config import load_config
from enhanced_features import enhanced_featurize

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="Apollo.ML 피처 엔지니어링")
    parser.add_argument("--config", default="config.yaml", help="config.yaml 파일 경로 (기본값: config.yaml)")
    args = parser.parse_args()
    
    print("=== 피처 엔지니어링 시작 ===")
    
    # 설정 로드
    cfg = load_config(args.config)
    
    # 전처리된 데이터 로드
    df = pd.read_parquet(Path(cfg.output_dir) / "preprocessed_data.parquet")
    print(f"전처리된 데이터 크기: {df.shape}")
    
    # 피처 엔지니어링 적용
    df_feat = enhanced_featurize(df, cfg.train.target)
    
    # 결과 저장
    out = Path(cfg.output_dir) / "enhanced_features.parquet"
    df_feat.to_parquet(out, index=False)
    
    print(f"피처 엔지니어링된 데이터 크기: {df_feat.shape}")
    print(f"저장 완료: {out}")
    print("다음 단계: python enhanced_train.py")

if __name__ == "__main__":
    main()
