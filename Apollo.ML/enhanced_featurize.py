# -*- coding: utf-8 -*-
"""
피처 엔지니어링 모듈
전처리된 데이터에 피처 엔지니어링을 적용합니다.
"""

import argparse
import pandas as pd
from pathlib import Path
from config import load_config
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
        try:
            dag_longest_path = nx.dag_longest_path(g)
            return len(dag_longest_path) - 1 if dag_longest_path else 0, 0.0
        except nx.NetworkXUnfeasible: # 순환 감지 시
             return 0, 0.0 # 순환이 있으면 깊이를 0으로 처리
        
    all_path_lengths = []
    leaf_nodes = [n for n, d in g.out_degree() if d == 0]
    
    for root in root_nodes:
        for leaf in leaf_nodes:
            if nx.has_path(g, root, leaf):
                all_path_lengths.append(nx.shortest_path_length(g, root, leaf))
    
    return max(all_path_lengths) if all_path_lengths else 0, np.mean(all_path_lengths) if all_path_lengths else 0.0

def _get_node_attributes(g, attribute_name, default_value=0):
    return [attrs.get(attribute_name, default_value) for _, attrs in g.nodes(data=True)]

def graph_basic_features(g: nx.DiGraph) -> dict:
    """기본 그래프 통계 특성들을 추출합니다."""
    num_nodes = g.number_of_nodes()
    if num_nodes == 0:
        return {
            "num_nodes": 0, "num_edges": 0, "avg_out_degree": 0.0, "max_out_degree": 0,
            "avg_in_degree": 0.0, "max_in_degree": 0, "density": 0.0, "is_connected": False,
            "num_components": 0, "diameter": 0, "avg_clustering": 0.0, "tree_depth": 0, "avg_tree_depth": 0.0
        }
    
    out_degrees = list(dict(g.out_degree()).values())
    in_degrees = list(dict(g.in_degree()).values())
    max_depth, avg_depth = get_tree_depth(g)
    
    return {
        "num_nodes": num_nodes,
        "num_edges": g.number_of_edges(),
        "avg_out_degree": np.mean(out_degrees),
        "max_out_degree": max(out_degrees) if out_degrees else 0,
        "avg_in_degree": np.mean(in_degrees),
        "max_in_degree": max(in_degrees) if in_degrees else 0,
        "density": nx.density(g),
        "is_connected": nx.is_weakly_connected(g),
        "num_components": nx.number_weakly_connected_components(g),
        "diameter": nx.diameter(g) if nx.is_strongly_connected(g) else 0,
        "avg_clustering": nx.average_clustering(g.to_undirected()),
        "tree_depth": max_depth,
        "avg_tree_depth": avg_depth
    }

def cost_features(g: nx.DiGraph) -> dict:
    """비용 관련 특성들을 추출합니다."""
    if g.number_of_nodes() == 0: return { "total_estimated_cost": 0.0, "avg_estimated_cost": 0.0, "max_estimated_cost": 0.0, "total_io_cost": 0.0, "total_cpu_cost": 0.0, "total_rows": 0.0, "avg_rows": 0.0, "max_rows": 0.0, "cost_per_row": 0.0 }

    costs = _get_node_attributes(g, 'EstimatedTotalSubtreeCost')
    rows = _get_node_attributes(g, 'EstimateRows')
    total_cost = sum(costs)
    total_rows = sum(rows)

    return {
        "total_estimated_cost": total_cost,
        "avg_estimated_cost": np.mean(costs),
        "max_estimated_cost": max(costs),
        "total_io_cost": sum(_get_node_attributes(g, 'EstimateIO')),
        "total_cpu_cost": sum(_get_node_attributes(g, 'EstimateCPU')),
        "total_rows": total_rows,
        "avg_rows": np.mean(rows),
        "max_rows": max(rows),
        "cost_per_row": total_cost / total_rows if total_rows > 0 else 0.0
    }

def operator_features(g: nx.DiGraph) -> dict:
    """연산자 관련 특성들을 추출합니다."""
    if g.number_of_nodes() == 0: return { "num_physical_ops": 0, "num_logical_ops": 0, "unique_physical_ops": 0, "unique_logical_ops": 0, "scan_ops_count": 0, "join_ops_count": 0, "sort_ops_count": 0, "aggregate_ops_count": 0, "parallel_ops_ratio": 0.0, "join_to_scan_ratio": 0.0 }

    physical_ops = _get_node_attributes(g, 'PhysicalOp', '')
    logical_ops = _get_node_attributes(g, 'LogicalOp', '')
    
    scan_ops = sum(1 for op in physical_ops if 'scan' in op.lower() or 'seek' in op.lower())
    join_ops = sum(1 for op in physical_ops if any(k in op.lower() for k in ['join', 'merge', 'hash']))

    return {
        "num_physical_ops": len(physical_ops),
        "num_logical_ops": len(logical_ops),
        "unique_physical_ops": len(set(physical_ops)),
        "unique_logical_ops": len(set(logical_ops)),
        "scan_ops_count": scan_ops,
        "join_ops_count": join_ops,
        "sort_ops_count": sum(1 for op in physical_ops if 'sort' in op.lower()),
        "aggregate_ops_count": sum(1 for op in physical_ops if any(k in op.lower() for k in ['aggregate', 'stream'])),
        "parallel_ops_ratio": sum(_get_node_attributes(g, 'Parallel', 0)) / g.number_of_nodes(),
        "join_to_scan_ratio": join_ops / scan_ops if scan_ops > 0 else 0.0
    }

def index_features(g: nx.DiGraph) -> dict:
    """인덱스 관련 특성들을 추출합니다."""
    if g.number_of_nodes() == 0: return { "index_ops_count": 0, "unique_index_kinds": 0, "clustered_index_ops": 0, "nonclustered_index_ops": 0, "index_scan_ops": 0, "index_seek_ops": 0 }
    
    index_kinds = _get_node_attributes(g, 'IndexKind', '')
    scan_types = _get_node_attributes(g, 'IndexScanType', '')
    
    return {
        "index_ops_count": len(index_kinds),
        "unique_index_kinds": len(set(index_kinds)),
        "clustered_index_ops": index_kinds.count('Clustered'),
        "nonclustered_index_ops": index_kinds.count('NonClustered'),
        "index_scan_ops": sum(1 for st in scan_types if 'scan' in st.lower()),
        "index_seek_ops": sum(1 for st in scan_types if 'seek' in st.lower())
    }

def derived_features(row: pd.Series, g: nx.DiGraph, costs: dict) -> dict:
    """데이터 누수를 방지한 안전한 파생 피처들을 생성합니다."""
    count_exec = row.get('count_exec', 0)
    avg_ms = row.get('avg_ms', 0)
    last_cpu_ms = row.get('last_cpu_ms', 0)
    last_reads = row.get('last_reads', 0)
    plan_xml_len = len(str(row.get('plan_xml', '')))
    
    complexity = (g.number_of_nodes() * 0.4 + g.number_of_edges() * 0.4 + costs['num_physical_ops'] * 0.2)

    return {
        'is_frequent_query': 1 if count_exec > 10 else 0,
        'estimated_cpu_per_cost': costs['total_cpu_cost'] / costs['total_estimated_cost'] if costs['total_estimated_cost'] > 0 else 0,
        'cpu_per_avg_ms': last_cpu_ms / avg_ms if avg_ms > 0 else 0,
        'reads_per_avg_ms': last_reads / avg_ms if avg_ms > 0 else 0,
        'memory_intensive': 1 if row.get('max_used_mem_kb', 0) > 10000 else 0,
        'is_parallel': 1 if row.get('max_dop', 0) > 1 else 0,
        'complexity_score': complexity,
        'cost_x_complexity': costs['total_estimated_cost'] * complexity,
        'reads_x_cpu': last_reads * last_cpu_ms,
        'is_large_plan': 1 if plan_xml_len > 50000 else 0
    }

def enhanced_featurize(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    """피처 엔지니어링 파이프라인"""
    print(f"총 {len(df)}개의 실행계획에 대한 피처 엔지니어링 시작...")
    
    features_list = []
    for _, row in df.iterrows():
        try:
            g = planxml_to_graph(row["plan_xml"]) if pd.notna(row.get('plan_xml')) else nx.DiGraph()
            
            base_feats = row.to_dict()
            graph_feats = graph_basic_features(g)
            cost_feats = cost_features(g)
            op_feats = operator_features(g)
            idx_feats = index_features(g)
            derived_feats = derived_features(row, g, {**cost_feats, **op_feats})
            
            features_list.append({
                **base_feats, **graph_feats, **cost_feats,
                **op_feats, **idx_feats, **derived_feats
            })
        except Exception as e:
            print(f"Plan ID {row.get('plan_id', 'N/A')} 처리 오류: {e}")
            features_list.append(row.to_dict()) # 오류 시 원본 데이터만 추가
            
    return pd.DataFrame(features_list)

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="Apollo.ML 피처 엔지니어링")
    parser.add_argument("--config", default="config.yaml", help="config.yaml 파일 경로")
    args = parser.parse_args()
    
    print("=== 피처 엔지니어링 시작 ===")
    cfg = load_config(args.config)
    
    input_path = Path(cfg.output_dir) / "preprocessed_data.parquet"
    df = pd.read_parquet(input_path)
    print(f"데이터 로드 완료: {input_path} (크기: {df.shape})")
    
    df_feat = enhanced_featurize(df, cfg.train.target)
    
    out_path = Path(cfg.output_dir) / "enhanced_features.parquet"
    df_feat.to_parquet(out_path, index=False)
    
    print(f"피처 엔지니어링 완료. 최종 데이터 크기: {df_feat.shape}")
    print(f"저장 완료: {out_path}")
    print("다음 단계: python enhanced_train.py")

if __name__ == "__main__":
    main()
