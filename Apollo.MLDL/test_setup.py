#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apollo.MLDL 설정 테스트 스크립트
"""

import sys
import os
from pathlib import Path

def test_imports():
    """필수 패키지 import 테스트"""
    print("=== 패키지 Import 테스트 ===")
    
    try:
        import pandas as pd
        print("✅ pandas")
    except ImportError as e:
        print(f"❌ pandas: {e}")
        return False
    
    try:
        import numpy as np
        print("✅ numpy")
    except ImportError as e:
        print(f"❌ numpy: {e}")
        return False
    
    try:
        import networkx as nx
        print("✅ networkx")
    except ImportError as e:
        print(f"❌ networkx: {e}")
        return False
    
    try:
        import lxml
        print("✅ lxml")
    except ImportError as e:
        print(f"❌ lxml: {e}")
        return False
    
    try:
        import xgboost
        print("✅ xgboost")
    except ImportError as e:
        print(f"❌ xgboost: {e}")
        return False
    
    try:
        import sklearn
        print("✅ scikit-learn")
    except ImportError as e:
        print(f"❌ scikit-learn: {e}")
        return False
    
    try:
        import yaml
        print("✅ pyyaml")
    except ImportError as e:
        print(f"❌ pyyaml: {e}")
        return False
    
    try:
        import pyodbc
        print("✅ pyodbc")
    except ImportError as e:
        print(f"❌ pyodbc: {e}")
        return False
    
    return True

def test_config():
    """설정 파일 테스트"""
    print("\n=== 설정 파일 테스트 ===")
    
    try:
        from config import load_config
        cfg = load_config("config.yaml")
        print("✅ config.yaml 로딩 성공")
        print(f"  - DB 서버: {cfg.db.server}")
        print(f"  - DB 이름: {cfg.db.database}")
        print(f"  - 타겟 컬럼: {cfg.train.target}")
        print(f"  - 출력 디렉토리: {cfg.output_dir}")
        return True
    except Exception as e:
        print(f"❌ 설정 파일 오류: {e}")
        return False

def test_modules():
    """모듈 import 테스트"""
    print("\n=== 모듈 Import 테스트 ===")
    
    try:
        from plan_graph import planxml_to_graph
        print("✅ plan_graph 모듈")
    except Exception as e:
        print(f"❌ plan_graph 모듈: {e}")
        return False
    
    try:
        from features import featurize
        print("✅ features 모듈")
    except Exception as e:
        print(f"❌ features 모듈: {e}")
        return False
    
    try:
        from model import build_model
        print("✅ model 모듈")
    except Exception as e:
        print(f"❌ model 모듈: {e}")
        return False
    
    try:
        from train import train
        print("✅ train 모듈")
    except Exception as e:
        print(f"❌ train 모듈: {e}")
        return False
    
    try:
        from evaluate import evaluate
        print("✅ evaluate 모듈")
    except Exception as e:
        print(f"❌ evaluate 모듈: {e}")
        return False
    
    return True

def test_xml_parsing():
    """XML 파싱 테스트"""
    print("\n=== XML 파싱 테스트 ===")
    
    try:
        from plan_graph import planxml_to_graph
        
        # 간단한 테스트 XML
        test_xml = '''<?xml version="1.0" encoding="utf-8"?>
<ShowPlanXML xmlns="http://schemas.microsoft.com/sqlserver/2004/07/showplan">
  <BatchSequence>
    <Batch>
      <Statements>
        <StmtSimple>
          <QueryPlan>
            <RelOp NodeId="0" PhysicalOp="Table Scan" LogicalOp="Table Scan">
              <OutputList />
              <TableScan>
                <Object />
              </TableScan>
            </RelOp>
          </QueryPlan>
        </StmtSimple>
      </Statements>
    </Batch>
  </BatchSequence>
</ShowPlanXML>'''
        
        g = planxml_to_graph(test_xml)
        print(f"✅ XML 파싱 성공 - 노드 수: {g.number_of_nodes()}, 엣지 수: {g.number_of_edges()}")
        return True
    except Exception as e:
        print(f"❌ XML 파싱 오류: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("Apollo.MLDL 설정 테스트 시작\n")
    
    tests = [
        test_imports,
        test_config,
        test_modules,
        test_xml_parsing
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"=== 테스트 결과 ===")
    print(f"통과: {passed}/{total}")
    
    if passed == total:
        print("🎉 모든 테스트 통과! 프로젝트가 정상적으로 설정되었습니다.")
        print("\n사용법:")
        print("1. 데이터 가져오기: python main.py fetch --config config.yaml")
        print("2. 피처 생성: python main.py featurize --config config.yaml")
        print("3. 모델 훈련: python main.py train --config config.yaml")
        print("4. 모델 평가: python main.py eval --model artifacts/xgb_reg.joblib --config config.yaml")
    else:
        print("❌ 일부 테스트 실패. 패키지 설치를 확인해주세요.")
        print("설치 명령어: pip install -r requirements.txt")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
