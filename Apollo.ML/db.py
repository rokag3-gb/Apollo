import pyodbc, pandas as pd
from config import DBConfig

def connect(cfg: DBConfig) -> pyodbc.Connection:
    conn_str = (
        f"DRIVER={{{cfg.driver}}};SERVER={cfg.server};DATABASE={cfg.database};"
        f"UID={cfg.username};PWD={cfg.password};Encrypt=yes;TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

def fetch_collected_plans(conn: pyodbc.Connection) -> pd.DataFrame:
    sql = "SELECT query_id, plan_id, plan_xml, count_exec, est_total_subtree_cost, avg_ms, last_cpu_ms, last_reads, max_used_mem_kb, max_dop, last_exec_time, last_ms FROM dbo.collected_plans"
    return pd.read_sql(sql, conn)