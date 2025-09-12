import networkx as nx
from lxml import etree

def planxml_to_graph(xml_text: str) -> nx.DiGraph:
    # TODO: 실제 변환 로직 연결
    root = etree.fromstring(xml_text.encode("utf-8"))
    g = nx.DiGraph()
    # 예시: 노드/엣지 파싱(스키마에 맞게 구현)
    for i, node in enumerate(root.iter()):
        g.add_node(i, tag=node.tag)
        if node.getparent() is not None:
            g.add_edge(i-1, i)
    return g