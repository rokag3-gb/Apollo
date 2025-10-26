# -*- coding: utf-8 -*-
"""
데이터 수집 모듈
데이터베이스에서 실행계획 데이터를 수집합니다.
"""

import argparse
from pathlib import Path
from datetime import datetime  # datetime 임포트
from config import load_config
from db import connect, fetch_collected_plans

def log_message(message):
    """메시지에 타임스탬프를 추가하여 출력"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"{timestamp} {message}")

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="Apollo.ML 데이터 수집")
    parser.add_argument("--config", default="config.yaml", help="config.yaml 파일 경로 (기본값: config.yaml)")
    args = parser.parse_args()
    
    log_message("=== 데이터 수집 시작 ===")
    
    # 설정 로드
    cfg = load_config(args.config)
    
    # 데이터베이스 연결 및 데이터 수집
    with connect(cfg.db) as conn:
        df = fetch_collected_plans(conn)
    
    # 결과 저장
    out = Path(cfg.output_dir) / "collected_plans.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    
    log_message(f"수집된 데이터 크기: {df.shape}")
    log_message(f"저장 완료: {out}")
    log_message("다음 단계: python enhanced_preprocess.py")

if __name__ == "__main__":
    main()
