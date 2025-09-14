#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XML 파싱 디버깅 스크립트
"""

import pandas as pd
from lxml import etree
from plan_graph import planxml_to_graph

def debug_xml_parsing():
    # 데이터 로드
    df = pd.read_parquet('artifacts/collected_plans.parquet')
    print(f"총 {len(df)}개의 실행계획 로드됨")
    
    # 첫 번째 XML 분석
    xml_text = df['plan_xml'].iloc[0]
    print(f"\n첫 번째 XML 길이: {len(xml_text)} 문자")
    print(f"XML 시작 부분:\n{xml_text[:200]}...")
    
    # XML 파싱
    try:
        root = etree.fromstring(xml_text.encode('utf-8'))
        print(f"\nRoot tag: {root.tag}")
        print(f"Root namespace: {root.nsmap}")
        
        # 자식 요소들
        children = [child.tag for child in root]
        print(f"Root children: {children}")
        
        # RelOp 찾기
        relops = root.xpath('.//RelOp')
        print(f"RelOp 개수: {len(relops)}")
        
        if relops:
            print(f"첫 번째 RelOp: {relops[0].tag}")
            print(f"첫 번째 RelOp 속성: {relops[0].attrib}")
            
            # NodeId 확인
            node_id = relops[0].get('NodeId')
            print(f"NodeId: {node_id}")
        
        # 다른 연산자들도 찾아보기
        all_ops = root.xpath('.//*[@NodeId]')
        print(f"NodeId가 있는 모든 요소: {len(all_ops)}개")
        
        if all_ops:
            print("첫 5개 요소:")
            for i, op in enumerate(all_ops[:5]):
                print(f"  {i+1}. {op.tag}: {op.attrib}")
        
    except Exception as e:
        print(f"XML 파싱 오류: {e}")
    
    # 그래프 변환 테스트
    print(f"\n그래프 변환 테스트:")
    g = planxml_to_graph(xml_text)
    print(f"그래프 노드 수: {g.number_of_nodes()}")
    print(f"그래프 엣지 수: {g.number_of_edges()}")

if __name__ == "__main__":
    debug_xml_parsing()
