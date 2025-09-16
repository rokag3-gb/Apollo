# -*- coding: utf-8 -*-
"""
데이터 수집 모듈
데이터베이스에서 실행계획 데이터를 수집합니다.
"""

import argparse
from pathlib import Path
from config import load_config
from db import connect, fetch_collected_plans

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="Apollo.ML 데이터 수집")
    parser.add_argument("--config", default="config.yaml", help="config.yaml 파일 경로 (기본값: config.yaml)")
    args = parser.parse_args()
    
    print("=== 데이터 수집 시작 ===")
    
    # 설정 로드
    cfg = load_config(args.config)
    
    # 데이터베이스 연결 및 데이터 수집
    with connect(cfg.db) as conn:
        df = fetch_collected_plans(conn)
    
    # 결과 저장
    out = Path(cfg.output_dir) / "collected_plans.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    
    print(f"수집된 데이터 크기: {df.shape}")
    print(f"저장 완료: {out}")
    print("다음 단계: python enhanced_preprocess.py")

if __name__ == "__main__":
    main()
