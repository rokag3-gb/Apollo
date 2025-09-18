# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import networkx as nx
from collections import Counter
from plan_graph import planxml_to_graph

def get_tree_depth(g: nx.DiGraph) -> (int, float):
    """실행 계획 트리의 깊이와 평균 깊이를 계산합니다."""
    if g.number_of_nodes() == 0:
        return 0, 0.0
    
    # 루트 노드 찾기 (in_degree가 0인 노드)
    root_nodes = [n for n, d in g.in_degree() if d == 0]
    if not root_nodes:
        # 순환 그래프 등의 예외 케이스 처리
        # 가장 긴 경로를 찾아서 깊이로 간주
        try:
            dag_longest_path = nx.dag_longest_path(g)
            dag_longest_path_length = len(dag_longest_path) - 1 if dag_longest_path else 0
            return dag_longest_path_length, dag_longest_path_length
        except (nx.NetworkXError, nx.NetworkXUnfeasible): # 순환 감지 시
             return 0, 0.0 # 순환이 있으면 깊이를 0으로 처리
        
    all_path_lengths = []
    # 모든 리프 노드 찾기 (out_degree가 0인 노드)
    leaf_nodes = [n for n, d in g.out_degree() if d == 0]
    
    for root in root_nodes:
        for leaf in leaf_nodes:
            if nx.has_path(g, root, leaf):
                all_path_lengths.append(nx.shortest_path_length(g, root, leaf))
    
    if not all_path_lengths:
        return 0, 0.0
        
    return max(all_path_lengths), np.mean(all_path_lengths)

def enhanced_featurize(df_plans: pd.DataFrame, target_col: str = "last_ms") -> pd.DataFrame:
    """전처리된 데이터에 피처 엔지니어링을 적용합니다."""
    rows = []
    
    print(f"총 {len(df_plans)}개의 전처리된 실행계획을 처리합니다...")
    
    for idx, row in df_plans.iterrows():
        if idx % 1000 == 0:
            print(f"처리 중: {idx + 1}/{len(df_plans)} - Plan ID: {row['plan_id']}")
        
        try:
            # 기본 메타데이터 (전처리된 데이터에서 가져옴)
            feats = {
                "plan_id": row["plan_id"],
                target_col: row[target_col]
            }
            
            # 전처리된 데이터의 모든 컬럼을 유지
            for col in df_plans.columns:
                if col not in ['plan_id', target_col]:
                    feats[col] = row[col]
            
            # 1. 데이터베이스에서 가져온 추가 컬럼들 활용
            if 'query_id' in row:
                feats['query_id'] = row['query_id']
            if 'count_exec' in row:
                feats['count_exec'] = row['count_exec']
            if 'est_total_subtree_cost' in row:
                feats['est_total_subtree_cost'] = row['est_total_subtree_cost']
            if 'avg_ms' in row:
                feats['avg_ms'] = row['avg_ms']
            if 'last_cpu_ms' in row:
                feats['last_cpu_ms'] = row['last_cpu_ms']
            if 'last_reads' in row:
                feats['last_reads'] = row['last_reads']
            if 'max_used_mem_kb' in row:
                feats['max_used_mem_kb'] = row['max_used_mem_kb']
            if 'max_dop' in row:
                feats['max_dop'] = row['max_dop']
            
            # 2. 실행계획 XML에서 그래프 특성 추출
            if 'plan_xml' in row and pd.notna(row['plan_xml']):
                g = planxml_to_graph(row["plan_xml"])
            else:
                print(f"Plan ID {row['plan_id']}: plan_xml이 없거나 비어있음")
                g = nx.DiGraph()  # 빈 그래프 생성
            
            # 그래프 기본 특성
            feats.update(graph_basic_features(g))
            
            # 비용 관련 특성
            feats.update(cost_features(g))
            
            # 연산자 관련 특성
            feats.update(operator_features(g))
            
            # 인덱스 관련 특성
            feats.update(index_features(g))
            
            # 3. 새로운 파생 피처들
            feats.update(derived_features(row, g))
            
            # 4. 짧은 쿼리 예측을 위한 추가 피처
            feats.update(short_query_features(row, g))
            
            rows.append(feats)
            
        except Exception as e:
            print(f"Plan ID {row['plan_id']} 처리 중 오류: {e}")
            # 오류 발생 시 기본값으로 채움
            feats = create_default_features(row, target_col)
            rows.append(feats)
    
    return pd.DataFrame(rows)

def graph_basic_features(g: nx.DiGraph) -> dict:
    """기본 그래프 통계 특성들을 추출합니다."""
    if g.number_of_nodes() == 0:
        return {
            "num_nodes": 0,
            "num_edges": 0,
            "avg_out_degree": 0.0,
            "max_out_degree": 0,
            "avg_in_degree": 0.0,
            "max_in_degree": 0,
            "density": 0.0,
            "is_connected": False,
            "num_components": 0,
            "diameter": 0,
            "avg_clustering": 0.0
        }
    
    out_degrees = dict(g.out_degree())
    in_degrees = dict(g.in_degree())
    max_depth, avg_depth = get_tree_depth(g)
    
    return {
        "num_nodes": g.number_of_nodes(),
        "num_edges": g.number_of_edges(),
        "avg_out_degree": np.mean(list(out_degrees.values())),
        "max_out_degree": max(out_degrees.values()) if out_degrees else 0,
        "avg_in_degree": np.mean(list(in_degrees.values())),
        "max_in_degree": max(in_degrees.values()) if in_degrees else 0,
        "max_children_per_node": max(out_degrees.values()) if out_degrees else 0,
        "tree_depth": max_depth,
        "avg_tree_depth": avg_depth,
        "density": nx.density(g),
        "is_connected": nx.is_weakly_connected(g),
        "num_components": nx.number_weakly_connected_components(g),
        "diameter": nx.diameter(g) if nx.is_strongly_connected(g) and g.number_of_nodes() > 0 else 0,
        "avg_clustering": nx.average_clustering(g.to_undirected())
    }

def cost_features(g: nx.DiGraph) -> dict:
    """비용 관련 특성들을 추출합니다."""
    if g.number_of_nodes() == 0:
        return {
            "total_estimated_cost": 0.0,
            "avg_estimated_cost": 0.0,
            "max_estimated_cost": 0.0,
            "total_io_cost": 0.0,
            "total_cpu_cost": 0.0,
            "total_rows": 0.0,
            "avg_rows": 0.0,
            "max_rows": 0.0,
            "total_avg_row_size": 0.0,
            "cost_per_row": 0.0
        }
    
    costs = []
    io_costs = []
    cpu_costs = []
    rows = []
    avg_row_sizes = []
    
    for node_id, attrs in g.nodes(data=True):
        if 'EstimatedTotalSubtreeCost' in attrs:
            costs.append(attrs['EstimatedTotalSubtreeCost'])
        if 'EstimateIO' in attrs:
            io_costs.append(attrs['EstimateIO'])
        if 'EstimateCPU' in attrs:
            cpu_costs.append(attrs['EstimateCPU'])
        if 'EstimateRows' in attrs:
            rows.append(attrs['EstimateRows'])
        if 'AvgRowSize' in attrs:
            avg_row_sizes.append(attrs['AvgRowSize'])
    
    total_cost = sum(costs) if costs else 0.0
    total_rows = sum(rows) if rows else 0.0
    
    return {
        "total_estimated_cost": total_cost,
        "avg_estimated_cost": np.mean(costs) if costs else 0.0,
        "max_estimated_cost": max(costs) if costs else 0.0,
        "total_io_cost": sum(io_costs) if io_costs else 0.0,
        "total_cpu_cost": sum(cpu_costs) if cpu_costs else 0.0,
        "total_rows": total_rows,
        "avg_rows": np.mean(rows) if rows else 0.0,
        "max_rows": max(rows) if rows else 0.0,
        "total_avg_row_size": sum(avg_row_sizes) if avg_row_sizes else 0.0,
        "cost_per_row": total_cost / total_rows if total_rows > 0 else 0.0
    }

def operator_features(g: nx.DiGraph) -> dict:
    """연산자 관련 특성들을 추출합니다."""
    if g.number_of_nodes() == 0:
        return {
            "num_physical_ops": 0,
            "num_logical_ops": 0,
            "unique_physical_ops": 0,
            "unique_logical_ops": 0,
            "most_common_physical_op": "",
            "most_common_logical_op": "",
            "parallel_ops_ratio": 0.0,
            "scan_ops_count": 0,
            "join_ops_count": 0,
            "sort_ops_count": 0,
            "aggregate_ops_count": 0
        }
    
    physical_ops = []
    logical_ops = []
    parallel_count = 0
    scan_ops = 0
    join_ops = 0
    sort_ops = 0
    aggregate_ops = 0
    
    for node_id, attrs in g.nodes(data=True):
        if 'PhysicalOp' in attrs and attrs['PhysicalOp']:
            physical_ops.append(attrs['PhysicalOp'])
            
            # 특정 연산자 타입 카운트
            op = attrs['PhysicalOp'].lower()
            if 'scan' in op or 'seek' in op:
                scan_ops += 1
            if 'join' in op or 'merge' in op or 'hash' in op:
                join_ops += 1
            if 'sort' in op:
                sort_ops += 1
            if 'aggregate' in op or 'stream' in op:
                aggregate_ops += 1
                
        if 'LogicalOp' in attrs and attrs['LogicalOp']:
            logical_ops.append(attrs['LogicalOp'])
            
        if attrs.get('Parallel', False):
            parallel_count += 1
    
    physical_op_counts = Counter(physical_ops)
    logical_op_counts = Counter(logical_ops)
    
    return {
        "num_physical_ops": len(physical_ops),
        "num_logical_ops": len(logical_ops),
        "unique_physical_ops": len(physical_op_counts),
        "unique_logical_ops": len(logical_op_counts),
        "most_common_physical_op": physical_op_counts.most_common(1)[0][0] if physical_op_counts else "",
        "most_common_logical_op": logical_op_counts.most_common(1)[0][0] if logical_op_counts else "",
        "parallel_ops_ratio": parallel_count / g.number_of_nodes() if g.number_of_nodes() > 0 else 0.0,
        "scan_ops_count": scan_ops,
        "join_ops_count": join_ops,
        "sort_ops_count": sort_ops,
        "aggregate_ops_count": aggregate_ops,
        "join_to_scan_ratio": join_ops / scan_ops if scan_ops > 0 else 0.0
    }

def index_features(g: nx.DiGraph) -> dict:
    """인덱스 관련 특성들을 추출합니다."""
    if g.number_of_nodes() == 0:
        return {
            "index_ops_count": 0,
            "unique_index_kinds": 0,
            "clustered_index_ops": 0,
            "nonclustered_index_ops": 0,
            "index_scan_ops": 0,
            "index_seek_ops": 0
        }
    
    index_kinds = []
    index_scan_count = 0
    index_seek_count = 0
    
    for node_id, attrs in g.nodes(data=True):
        if 'IndexKind' in attrs and attrs['IndexKind']:
            index_kinds.append(attrs['IndexKind'])
            
        if 'IndexScanType' in attrs and attrs['IndexScanType']:
            scan_type = attrs['IndexScanType'].lower()
            if 'scan' in scan_type:
                index_scan_count += 1
            if 'seek' in scan_type:
                index_seek_count += 1
    
    index_kind_counts = Counter(index_kinds)
    
    return {
        "index_ops_count": len(index_kinds),
        "unique_index_kinds": len(index_kind_counts),
        "clustered_index_ops": index_kind_counts.get('Clustered', 0),
        "nonclustered_index_ops": index_kind_counts.get('NonClustered', 0),
        "index_scan_ops": index_scan_count,
        "index_seek_ops": index_seek_count
    }

def derived_features(row: pd.Series, g: nx.DiGraph) -> dict:
    """데이터 누수를 방지한 안전한 파생 피처들을 생성합니다."""
    feats = {}
    
    # 1. 실행 빈도 관련 피처
    count_exec = row.get('count_exec', 0)
    feats['count_exec'] = count_exec
    feats['is_frequent_query'] = 1 if count_exec > 10 else 0
    
    # 2. 비용 효율성 피처 (Data Leakage 제거)
    # est_total_subtree_cost는 전처리 단계에서 다른 피처들로부터 생성될 수 있으므로,
    # featurize 단계에서 row에 포함되어 있을 수 있습니다. 없으면 기본값 0 사용.
    total_estimated_cost = row.get('total_estimated_cost', 0)
    total_cpu_cost = row.get('total_cpu_cost', 0)
    total_io_cost = row.get('total_io_cost', 0)
    
    feats['estimated_cpu_per_cost'] = total_cpu_cost / total_estimated_cost if total_estimated_cost > 0 else 0
    feats['estimated_io_per_cost'] = total_io_cost / total_estimated_cost if total_estimated_cost > 0 else 0
    
    # 3. 평균 실행시간 기반 비율 피처 (Data Leakage 제거)
    avg_ms = row.get('avg_ms', 0)
    last_cpu_ms = row.get('last_cpu_ms', 0)
    last_reads = row.get('last_reads', 0)
    
    if avg_ms > 0:
        feats['cpu_per_avg_ms'] = last_cpu_ms / avg_ms
        feats['reads_per_avg_ms'] = last_reads / avg_ms
    else:
        feats['cpu_per_avg_ms'] = 0
        feats['reads_per_avg_ms'] = 0

    # 4. 메모리 사용량 관련
    max_used_mem_kb = row.get('max_used_mem_kb', 0)
    feats['max_used_mem_kb'] = max_used_mem_kb
    feats['memory_intensive'] = 1 if max_used_mem_kb > 10000 else 0  # 10MB 이상

    # 5. 병렬 처리 관련
    max_dop = row.get('max_dop', 0)
    feats['max_dop'] = max_dop
    feats['is_parallel'] = 1 if max_dop > 1 else 0
    
    # 6. 그래프 복잡도 점수
    complexity = (
        g.number_of_nodes() * 0.3 +
        g.number_of_edges() * 0.3 +
        len([n for n, d in g.nodes(data=True) if 'PhysicalOp' in d]) * 0.2 +
        len([n for n, d in g.nodes(data=True) if 'LogicalOp' in d]) * 0.2
    )
    feats['complexity_score'] = complexity
    
    # 7. 상호작용 피처
    feats['cost_x_complexity'] = total_estimated_cost * complexity
    feats['reads_x_cpu'] = last_reads * last_cpu_ms
    
    # 8. 실행계획 크기 (XML 길이)
    plan_xml_str = str(row.get('plan_xml', ''))
    feats['plan_xml_length'] = len(plan_xml_str)
    feats['is_large_plan'] = 1 if len(plan_xml_str) > 50000 else 0
    
    return feats

def short_query_features(row: pd.Series, g: nx.DiGraph) -> dict:
    """짧은 쿼리 예측을 위한 추가 피처들을 생성합니다."""
    feats = {}
    
    # 1. 쿼리 복잡도 기반 분류
    if g.number_of_nodes() == 0:
        feats['is_simple_query'] = 1
        feats['is_medium_query'] = 0
        feats['is_complex_query'] = 0
    elif g.number_of_nodes() <= 5:
        feats['is_simple_query'] = 1
        feats['is_medium_query'] = 0
        feats['is_complex_query'] = 0
    elif g.number_of_nodes() <= 15:
        feats['is_simple_query'] = 0
        feats['is_medium_query'] = 1
        feats['is_complex_query'] = 0
    else:
        feats['is_simple_query'] = 0
        feats['is_medium_query'] = 0
        feats['is_complex_query'] = 1
    
    # 2. 실행 시간 기반 분류 (Data Leakage 제거하고 avg_ms 사용)
    if 'avg_ms' in row and pd.notna(row['avg_ms']):
        avg_ms = row['avg_ms']
        if avg_ms < 1:
            feats['avg_execution_speed'] = 0  # 매우 빠름
        elif avg_ms < 10:
            feats['avg_execution_speed'] = 1  # 빠름
        elif avg_ms < 100:
            feats['avg_execution_speed'] = 2  # 보통
        elif avg_ms < 1000:
            feats['avg_execution_speed'] = 3  # 느림
        else:
            feats['avg_execution_speed'] = 4  # 매우 느림
    else:
        feats['avg_execution_speed'] = 2  # 기본값
    
    # 3. 리소스 사용 패턴 (Data Leakage 제거하고 avg_ms 사용)
    if 'last_cpu_ms' in row and 'avg_ms' in row and pd.notna(row['last_cpu_ms']) and pd.notna(row['avg_ms']):
        cpu_ratio = row['last_cpu_ms'] / (row['avg_ms'] + 1e-8)
        if cpu_ratio > 0.8:
            feats['resource_type'] = 0  # CPU 집약적
        elif cpu_ratio > 0.3:
            feats['resource_type'] = 1  # 균형
        else:
            feats['resource_type'] = 2  # I/O 집약적
    else:
        feats['resource_type'] = 1  # 기본값
    
    # 4. 실행 빈도 기반 분류
    if 'count_exec' in row and pd.notna(row['count_exec']):
        count_exec = row['count_exec']
        if count_exec == 1:
            feats['frequency_type'] = 0  # 일회성
        elif count_exec <= 10:
            feats['frequency_type'] = 1  # 가끔
        elif count_exec <= 100:
            feats['frequency_type'] = 2  # 자주
        else:
            feats['frequency_type'] = 3  # 매우 자주
    else:
        feats['frequency_type'] = 1  # 기본값
    
    return feats

def create_default_features(row: pd.Series, target_col: str) -> dict:
    """오류 발생 시 기본 피처를 생성합니다."""
    feats = {
        "plan_id": row["plan_id"],
        target_col: row[target_col],
        "num_nodes": 0,
        "num_edges": 0,
        "avg_out_degree": 0.0,
        "max_out_degree": 0,
        "avg_in_degree": 0.0,
        "max_in_degree": 0,
        "max_children_per_node": 0,
        "tree_depth": 0,
        "avg_tree_depth": 0.0,
        "density": 0.0,
        "is_connected": False,
        "num_components": 0,
        "diameter": 0,
        "avg_clustering": 0.0,
        "total_estimated_cost": 0.0,
        "avg_estimated_cost": 0.0,
        "max_estimated_cost": 0.0,
        "total_io_cost": 0.0,
        "total_cpu_cost": 0.0,
        "total_rows": 0.0,
        "avg_rows": 0.0,
        "max_rows": 0.0,
        "total_avg_row_size": 0.0,
        "cost_per_row": 0.0,
        "num_physical_ops": 0,
        "num_logical_ops": 0,
        "unique_physical_ops": 0,
        "unique_logical_ops": 0,
        "most_common_physical_op": "",
        "most_common_logical_op": "",
        "parallel_ops_ratio": 0.0,
        "scan_ops_count": 0,
        "join_ops_count": 0,
        "sort_ops_count": 0,
        "aggregate_ops_count": 0,
        "join_to_scan_ratio": 0.0,
        "index_ops_count": 0,
        "unique_index_kinds": 0,
        "clustered_index_ops": 0,
        "nonclustered_index_ops": 0,
        "index_scan_ops": 0,
        "index_seek_ops": 0,
        "count_exec": 0,
        "is_frequent_query": 0,
        "estimated_cpu_per_cost": 0.0,
        "estimated_io_per_cost": 0.0,
        "cpu_per_avg_ms": 0.0,
        "reads_per_avg_ms": 0.0,
        "max_used_mem_kb": 0,
        "memory_intensive": 0,
        "max_dop": 0,
        "is_parallel": 0,
        "complexity_score": 0.0,
        "cost_x_complexity": 0.0,
        "reads_x_cpu": 0.0,
        "plan_xml_length": 0,
        "is_large_plan": 0,
        "is_simple_query": 1,
        "is_medium_query": 0,
        "is_complex_query": 0,
        "avg_execution_speed": 2,
        "resource_type": 1,
        "frequency_type": 1
    }
    return feats
