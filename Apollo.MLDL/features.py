import pandas as pd
import networkx as nx
from plan_graph import planxml_to_graph

def graph_basic_features(g: nx.DiGraph) -> dict:
    return {
        "num_nodes": g.number_of_nodes(),
        "num_edges": g.number_of_edges(),
        "avg_out_degree": (sum(dict(g.out_degree()).values()) / max(g.number_of_nodes(), 1)),
    }

def featurize(df_plans: pd.DataFrame, target_col: str = "last_ms") -> pd.DataFrame:
    rows = []
    for _, row in df_plans.iterrows():
        g = planxml_to_graph(row["plan_xml"])
        feats = graph_basic_features(g)
        feats["plan_id"] = row["plan_id"]
        feats[target_col] = row[target_col]
        rows.append(feats)
    return pd.DataFrame(rows)