import numpy as np
from lxml import etree

# 미리 학습된 XGBoost 모델이 기대하는 피처의 수
XGB_EXPECTED_FEATURES = 79

# XML 네임스페이스
PLAN_NS = "{http://schemas.microsoft.com/sqlserver/2004/07/showplan}"

def parse_plan_features(plan_xml: str) -> dict:
    """실행 계획 XML을 파싱하여 주요 특징을 딕셔너리로 추출합니다."""
    features = {
        # 기존 특징
        'estimated_rows': 0,
        'estimated_cost': 0,
        'parallelism_degree': 0,
        'join_type_hash': 0,
        'join_type_loop': 0,
        'scan_type_index': 0,
        'scan_type_table': 0,
        # [NEW] Step 1: 컨텍스트 특징 추가
        'join_count': 0,
        'subquery_count': 0,
        'table_count': 0,
        'cardinality_error': 0.0, # (실제 row / 예상 row)
        'actual_rows': 0,
        'missing_index_count': 0, # [NEW] 누락된 인덱스 제안 개수
        # [NEW] 가장 비싼 연산자 정보
        'most_expensive_op_cost': 0.0,
        'most_expensive_op_is_join': 0,
        'most_expensive_op_is_scan': 0,
        'plan_warning_count': 0, # [NEW] 계획 경고 개수
    }
    if not plan_xml:
        return features

    try:
        root = etree.fromstring(plan_xml.encode('utf-8'))
        # .xpath()를 사용하기 위한 네임스페이스 맵 정의
        ns = {'sh': PLAN_NS.strip('{}')}
        
        # 전체 서브트리 비용 및 실제/예상 Rows
        stmt = root.find(f".//{PLAN_NS}StmtSimple")
        if stmt is not None:
            features['estimated_cost'] = float(stmt.get('StatementSubTreeCost', 0))
            
        rel_op_root = root.find(f".//{PLAN_NS}RelOp")
        if rel_op_root is not None:
            features['estimated_rows'] = float(rel_op_root.get('EstimateRows', 0))
            features['actual_rows'] = float(rel_op_root.get('ActualRows', 0))

        # Cardinality 오차 계산
        if features['estimated_rows'] > 0:
            features['cardinality_error'] = features['actual_rows'] / features['estimated_rows']
        else:
            features['cardinality_error'] = 1.0 if features['actual_rows'] > 0 else 0.0

        # 병렬 실행 여부 (DegreeOfParallelism > 0)
        parallel_node = root.xpath(".//*[@DegreeOfParallelism > 0]", namespaces=ns)
        if parallel_node:
            features['parallelism_degree'] = 1

        # 조인 타입 및 개수
        joins = root.xpath(".//sh:RelOp[contains(@LogicalOp, 'Join')]", namespaces=ns)
        features['join_count'] = len(joins)
        hash_joins = root.xpath(".//sh:RelOp[contains(@LogicalOp, 'Join') and contains(@PhysicalOp, 'Hash')]", namespaces=ns)
        loop_joins = root.xpath(".//sh:RelOp[contains(@LogicalOp, 'Join') and contains(@PhysicalOp, 'Nested Loops')]", namespaces=ns)
        features['join_type_hash'] = 1 if len(hash_joins) > 0 else 0
        features['join_type_loop'] = 1 if len(loop_joins) > 0 else 0

        # 서브쿼리 개수 (Apply 연산자 기준)
        subqueries = root.xpath(".//sh:RelOp[contains(@LogicalOp, 'Apply')]", namespaces=ns)
        features['subquery_count'] = len(subqueries)

        # 테이블 개수 (Table Scan, Index Scan/Seek 등 물리적 테이블 접근 연산자 기준)
        table_access_ops = root.xpath(".//*[starts-with(name(), 'TableScan') or starts-with(name(), 'Index')]", namespaces=ns)
        features['table_count'] = len(table_access_ops)
        
        # 스캔 타입
        index_scans = root.xpath(".//sh:RelOp[contains(@PhysicalOp, 'Index Scan') or contains(@PhysicalOp, 'Index Seek')]", namespaces=ns)
        table_scans = root.xpath(".//sh:RelOp[contains(@PhysicalOp, 'Table Scan')]", namespaces=ns)
        features['scan_type_index'] = 1 if len(index_scans) > 0 else 0
        features['scan_type_table'] = 1 if len(table_scans) > 0 else 0

        # 누락된 인덱스 제안 개수
        missing_indexes = root.xpath(".//sh:MissingIndexes/sh:MissingIndexGroup", namespaces=ns)
        features['missing_index_count'] = len(missing_indexes)

        # 가장 비용이 높은 연산자 찾기
        all_ops = root.xpath(".//sh:RelOp", namespaces=ns)
        most_expensive_op = None
        max_cost = -1.0
        for op in all_ops:
            cost_str = op.get('EstimatedTotalSubtreeCost')
            if cost_str:
                cost = float(cost_str)
                if cost > max_cost:
                    max_cost = cost
                    most_expensive_op = op
        
        if most_expensive_op is not None:
            features['most_expensive_op_cost'] = max_cost
            logical_op = most_expensive_op.get('LogicalOp', '').lower()
            if 'join' in logical_op:
                features['most_expensive_op_is_join'] = 1
            elif 'scan' in logical_op or 'seek' in logical_op:
                features['most_expensive_op_is_scan'] = 1

        # 계획 경고 개수
        warnings = root.xpath(".//sh:Warnings", namespaces=ns)
        features['plan_warning_count'] = len(warnings)

    except etree.XMLSyntaxError:
        print("Warning: Could not parse execution plan XML.")

    return features

def extract_features(plan_xml: str, metrics: dict) -> np.ndarray:
    """
    실행 계획 XML과 실행 통계(metrics)를 입력받아 최종 상태 벡터를 생성합니다.
    """
    plan_features = parse_plan_features(plan_xml)
    
    # 특징 벡터 생성 순서를 일관성 있게 유지
    feature_vector = [
        # 기존 특징
        plan_features.get('estimated_rows', 0),
        plan_features.get('estimated_cost', 0),
        plan_features.get('parallelism_degree', 0),
        plan_features.get('join_type_hash', 0),
        plan_features.get('join_type_loop', 0),
        plan_features.get('scan_type_index', 0),
        plan_features.get('scan_type_table', 0),
        
        # 실행 통계 특징
        metrics.get('logical_reads', 0),
        metrics.get('cpu_time_ms', 0),
        metrics.get('elapsed_time_ms', 0),

        # [NEW] Step 1: 컨텍스트 특징 추가
        plan_features.get('join_count', 0),
        plan_features.get('subquery_count', 0),
        plan_features.get('table_count', 0),
        plan_features.get('cardinality_error', 0.0),
        plan_features.get('actual_rows', 0),
        plan_features.get('missing_index_count', 0), # [NEW]
        # [NEW] 가장 비싼 연산자 정보
        plan_features.get('most_expensive_op_cost', 0.0),
        plan_features.get('most_expensive_op_is_join', 0),
        plan_features.get('most_expensive_op_is_scan', 0),
        plan_features.get('plan_warning_count', 0), # [NEW]
    ]

    # TODO: is_readonly 특징 추가 필요 (SQL 파서 필요)

    # XGBoost 모델의 입력 크기에 맞게 0으로 패딩
    padding_size = XGB_EXPECTED_FEATURES - len(feature_vector)
    if padding_size > 0:
        padding = np.zeros(padding_size)
        feature_vector = np.concatenate([feature_vector, padding])
    
    # 정규화 (필요 시)
    # 예: feature_vector[0] = np.log1p(feature_vector[0])
    
    return np.array(feature_vector, dtype=np.float32)
