import numpy as np
from lxml import etree

# 미리 학습된 XGBoost 모델이 기대하는 피처의 수
XGB_EXPECTED_FEATURES = 79

# XML 네임스페이스
PLAN_NS = "{http://schemas.microsoft.com/sqlserver/2004/07/showplan}"

def parse_plan_features(plan_xml: str) -> dict:
    """실행 계획 XML을 파싱하여 주요 특징을 딕셔너리로 추출합니다."""
    features = {
        'estimated_rows': 0,
        'estimated_cost': 0,
        'parallelism_degree': 0,
        'join_type_hash': 0,
        'join_type_loop': 0,
        'scan_type_index': 0,
        'scan_type_table': 0,
    }
    if not plan_xml:
        return features

    try:
        root = etree.fromstring(plan_xml.encode('utf-8'))
        # [FIX] .xpath()를 사용하기 위한 네임스페이스 맵 정의
        ns = {'sh': PLAN_NS.strip('{}')}
        
        # 전체 서브트리 비용
        stmt = root.find(f".//{PLAN_NS}StmtSimple") # find()는 predicate가 없으므로 그대로 사용 가능
        if stmt is not None:
            features['estimated_cost'] = float(stmt.get('StatementSubTreeCost', 0))

        # [FIX] .xpath()를 사용하여 고급 조건 검색
        parallel_node = root.xpath(".//*[@DegreeOfParallelism > 0]", namespaces=ns)
        if parallel_node: # xpath()는 리스트를 반환하므로, 비어있는지 여부로 확인
            features['parallelism_degree'] = 1

        # [FIX] .xpath()와 'and'를 사용하여 조인 타입 카운트
        hash_joins = root.xpath(".//sh:RelOp[contains(@LogicalOp, 'Join') and contains(@PhysicalOp, 'Hash')]", namespaces=ns)
        loop_joins = root.xpath(".//sh:RelOp[contains(@LogicalOp, 'Join') and contains(@PhysicalOp, 'Nested Loops')]", namespaces=ns)
        features['join_type_hash'] = 1 if len(hash_joins) > 0 else 0
        features['join_type_loop'] = 1 if len(loop_joins) > 0 else 0

        # 스캔 타입 카운트 및 총 예상 Rows
        total_rows = 0
        index_scans = 0
        table_scans = 0
        rel_ops = root.xpath(f".//sh:RelOp", namespaces=ns)
        for op in rel_ops:
            total_rows += float(op.get('EstimateRows', 0))
            physical_op = op.get('PhysicalOp', '')
            if 'Index Scan' in physical_op or 'Index Seek' in physical_op:
                index_scans += 1
            elif 'Table Scan' in physical_op:
                table_scans += 1
        
        features['estimated_rows'] = total_rows
        features['scan_type_index'] = 1 if index_scans > 0 else 0
        features['scan_type_table'] = 1 if table_scans > 0 else 0

    except etree.XMLSyntaxError:
        print("Warning: Could not parse execution plan XML.")

    return features

def extract_features(plan_xml: str, metrics: dict) -> np.ndarray:
    """
    실행 계획 XML과 실행 통계(metrics)를 입력받아 최종 상태 벡터를 생성합니다.
    """
    plan_features = parse_plan_features(plan_xml)
    
    # Phase 1에서 사용한 피처들을 순서대로 벡터화
    feature_vector = [
        plan_features.get('estimated_rows', 0),
        plan_features.get('estimated_cost', 0),
        plan_features.get('parallelism_degree', 0),
        plan_features.get('join_type_hash', 0),
        plan_features.get('join_type_loop', 0),
        plan_features.get('scan_type_index', 0),
        plan_features.get('scan_type_table', 0),
    ]

    # Phase 2에서 추가된 실행 통계 피처
    feature_vector.append(metrics.get('logical_reads', 0))
    feature_vector.append(metrics.get('cpu_time_ms', 0))
    feature_vector.append(metrics.get('elapsed_time_ms', 0))

    # TODO: 여기에 더 많은 피처들을 추가하여 79개를 맞춰야 함.
    # (예: Cardinality 오차, 연산자별 비용, 메모리 사용량 등)

    # XGBoost 모델의 입력 크기에 맞게 0으로 패딩
    padding_size = XGB_EXPECTED_FEATURES - len(feature_vector)
    if padding_size > 0:
        padding = np.zeros(padding_size)
        feature_vector = np.concatenate([feature_vector, padding])
    
    # 정규화 (필요 시)
    # 예: feature_vector[0] = np.log1p(feature_vector[0])
    
    return np.array(feature_vector, dtype=np.float32)
