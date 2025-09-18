import networkx as nx
from lxml import etree
import re
from typing import Dict, Any, List, Optional

def extract_numeric_value(text: str) -> float:
    """텍스트에서 숫자 값을 추출합니다."""
    if not text:
        return 0.0
    # 숫자와 소수점만 추출
    numbers = re.findall(r'[\d.]+', str(text))
    return float(numbers[0]) if numbers else 0.0

def extract_operator_info(node) -> Dict[str, Any]:
    """실행계획 노드에서 연산자 정보를 추출합니다."""
    info = {
        'PhysicalOp': node.get('PhysicalOp', ''),
        'LogicalOp': node.get('LogicalOp', ''),
        'EstimateRows': extract_numeric_value(node.get('EstimateRows', '0')),
        'EstimateIO': extract_numeric_value(node.get('EstimateIO', '0')),
        'EstimateCPU': extract_numeric_value(node.get('EstimateCPU', '0')),
        'AvgRowSize': extract_numeric_value(node.get('AvgRowSize', '0')),
        'EstimatedTotalSubtreeCost': extract_numeric_value(node.get('EstimatedTotalSubtreeCost', '0')),
        'TableCardinality': extract_numeric_value(node.get('TableCardinality', '0')),
        'IndexKind': node.get('IndexKind', ''),
        'IndexScanType': node.get('IndexScanType', ''),
        'Storage': node.get('Storage', ''),
        'MemoryFractions': node.get('MemoryFractions', ''),
        'Parallel': node.get('Parallel', 'false').lower() == 'true',
        'NodeId': extract_numeric_value(node.get('NodeId', '0'))
    }
    return info

def extract_relop_info(node) -> Dict[str, Any]:
    """RelOp 노드에서 관계 연산자 정보를 추출합니다."""
    info = {
        'EstimateRows': extract_numeric_value(node.get('EstimateRows', '0')),
        'EstimateIO': extract_numeric_value(node.get('EstimateIO', '0')),
        'EstimateCPU': extract_numeric_value(node.get('EstimateCPU', '0')),
        'AvgRowSize': extract_numeric_value(node.get('AvgRowSize', '0')),
        'EstimatedTotalSubtreeCost': extract_numeric_value(node.get('EstimatedTotalSubtreeCost', '0')),
        'TableCardinality': extract_numeric_value(node.get('TableCardinality', '0')),
        'Parallel': node.get('Parallel', 'false').lower() == 'true',
        'NodeId': extract_numeric_value(node.get('NodeId', '0'))
    }
    return info

def planxml_to_graph(xml_text: str) -> nx.DiGraph:
    """SQL Server 실행계획 XML을 NetworkX 그래프로 변환합니다."""
    try:
        root = etree.fromstring(xml_text.encode("utf-8"))
        g = nx.DiGraph()
        
        # RelOp 노드들을 찾아서 그래프에 추가 (네임스페이스 고려)
        relops = root.xpath('.//*[local-name()="RelOp"]')
        node_id_map = {}
        
        for relop in relops:
            node_id = int(extract_numeric_value(relop.get('NodeId', '0')))
            if node_id == 0:
                continue
                
            # 연산자 정보 추출
            op_info = extract_relop_info(relop)
            
            # PhysicalOp 정보가 있으면 추가
            physical_op = relop.get('PhysicalOp', '')
            if physical_op:
                op_info['PhysicalOp'] = physical_op
                
            # LogicalOp 정보가 있으면 추가
            logical_op = relop.get('LogicalOp', '')
            if logical_op:
                op_info['LogicalOp'] = logical_op
            
            # 노드 추가
            g.add_node(node_id, **op_info)
            node_id_map[node_id] = relop
        
        # 부모-자식 관계 설정
        for node_id, relop in node_id_map.items():
            # 부모 노드 찾기 (네임스페이스 고려)
            parent = relop.getparent()
            while parent is not None:
                if parent.tag.endswith('}RelOp') and parent.get('NodeId'):
                    parent_id = int(extract_numeric_value(parent.get('NodeId')))
                    if parent_id in node_id_map:
                        g.add_edge(parent_id, node_id)
                        break
                parent = parent.getparent()
        
        return g
        
    except Exception as e:
        print(f"XML 파싱 오류: {e}")
        # 오류 발생 시 빈 그래프 반환
        return nx.DiGraph()