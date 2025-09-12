import networkx as nx
from lxml import etree

def planxml_to_graph(xml_text: str) -> nx.DiGraph:
    # TODO: ���� ��ȯ ���� ����
    root = etree.fromstring(xml_text.encode("utf-8"))
    g = nx.DiGraph()
    # ����: ���/���� �Ľ�(��Ű���� �°� ����)
    for i, node in enumerate(root.iter()):
        g.add_node(i, tag=node.tag)
        if node.getparent() is not None:
            g.add_edge(i-1, i)
    return g