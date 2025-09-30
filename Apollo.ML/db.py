import pyodbc, pandas as pd
from config import DBConfig

# [NEW] 메시지 핸들러를 통해 통계 정보를 저장할 전역 변수
_STATS_IO = []
_STATS_TIME = []

def _message_handler(conn):
    """
    pyodbc 연결에 대한 메시지 핸들러.
    SET STATISTICS 출력을 캡처하여 전역 변수에 저장합니다.
    """
    def on_message(msg_type, message):
        global _STATS_IO, _STATS_TIME
        message_str = message.decode('utf-8', errors='ignore')
        
        for line in message_str.splitlines():
            line = line.strip()
            if line.startswith("Table"):
                _STATS_IO.append(line)
            elif line.startswith("SQL Server Execution Times"):
                _STATS_TIME.append(line)
    
    conn.add_output_converter(-1, on_message)

def connect(cfg: DBConfig) -> pyodbc.Connection:
    conn_str = (
        f"DRIVER={{{cfg.driver}}};SERVER={cfg.server};DATABASE={cfg.database};"
        f"UID={cfg.username};PWD={cfg.password};Encrypt=yes;TrustServerCertificate=yes;"
    )
    conn = pyodbc.connect(conn_str)
    # [NEW] 메시지 핸들러 등록
    _message_handler(conn)
    return conn

def fetch_collected_plans(conn: pyodbc.Connection) -> pd.DataFrame:
    sql = "SELECT query_id, plan_id, plan_xml, count_exec, est_total_subtree_cost, avg_ms, last_cpu_ms, last_reads, max_used_mem_kb, max_dop, last_exec_time, last_ms FROM dbo.collected_plans"
    return pd.read_sql(sql, conn)

def execute_query(conn: pyodbc.Connection, sql: str) -> tuple[str, str, str]:
    """
    주어진 SQL 쿼리를 실행하고 실행 계획과 통계 정보를 반환합니다.
    """
    global _STATS_IO, _STATS_TIME
    _STATS_IO.clear()
    _STATS_TIME.clear()
    
    cursor = conn.cursor()
    plan_xml = None
    
    sql_batch = f"""
    SET STATISTICS IO ON;
    SET STATISTICS TIME ON;
    SET STATISTICS XML ON;
    {sql}
    SET STATISTICS XML OFF;
    SET STATISTICS IO OFF;
    SET STATISTICS TIME OFF;
    """

    try:
        cursor.execute(sql_batch)
        while True:
            try:
                row = cursor.fetchone()
                if row and row[0] and isinstance(row[0], str) and row[0].strip().startswith('<'):
                    plan_xml = row[0]
            except pyodbc.ProgrammingError:
                pass
            if not cursor.nextset():
                break
    except pyodbc.Error as e:
        print(f"Error executing query: {e}")
        conn.rollback()
    finally:
        cursor.close()

    stats_io_str = "\\n".join(_STATS_IO)
    stats_time_str = "\\n".join(_STATS_TIME)
    
    if not isinstance(plan_xml, str):
        print(f"Warning: Invalid execution plan received (type: {type(plan_xml)}). Treating as no plan found.")
        plan_xml = None

    return plan_xml, stats_io_str, stats_time_str