import pandas as pd
import networkx as nx
import numpy as np
from collections import Counter
from plan_graph import planxml_to_graph

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
    
    return {
        "num_nodes": g.number_of_nodes(),
        "num_edges": g.number_of_edges(),
        "avg_out_degree": np.mean(list(out_degrees.values())),
        "max_out_degree": max(out_degrees.values()) if out_degrees else 0,
        "avg_in_degree": np.mean(list(in_degrees.values())),
        "max_in_degree": max(in_degrees.values()) if in_degrees else 0,
        "density": nx.density(g),
        "is_connected": nx.is_weakly_connected(g),
        "num_components": nx.number_weakly_connected_components(g),
        "diameter": nx.diameter(g) if nx.is_weakly_connected(g) and g.number_of_nodes() > 0 else 0,
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
        "aggregate_ops_count": aggregate_ops
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

def featurize(df_plans: pd.DataFrame, target_col: str = "last_ms") -> pd.DataFrame:
    """실행계획 데이터를 피처로 변환합니다."""
    rows = []
    
    for idx, row in df_plans.iterrows():
        print(f"처리 중: {idx + 1}/{len(df_plans)} - Plan ID: {row['plan_id']}")
        
        try:
            g = planxml_to_graph(row["plan_xml"])
            
            # 모든 특성 추출
            feats = {}
            feats.update(graph_basic_features(g))
            feats.update(cost_features(g))
            feats.update(operator_features(g))
            feats.update(index_features(g))
            
            # 메타데이터 추가
            feats["plan_id"] = row["plan_id"]
            feats[target_col] = row[target_col]
            
            rows.append(feats)
            
        except Exception as e:
            print(f"Plan ID {row['plan_id']} 처리 중 오류: {e}")
            # 오류 발생 시 기본값으로 채움
            feats = {
                "plan_id": row["plan_id"],
                target_col: row[target_col],
                "num_nodes": 0,
                "num_edges": 0,
                "total_estimated_cost": 0.0,
                "num_physical_ops": 0,
                "index_ops_count": 0
            }
            rows.append(feats)
    
    return pd.DataFrame(rows)