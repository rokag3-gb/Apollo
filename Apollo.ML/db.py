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

def execute_query(conn: pyodbc.Connection, sql: str) -> tuple[str, str, str]:
    """
    주어진 SQL 쿼리를 실행하고 실행 계획과 통계 정보를 반환합니다.

    Args:
        conn (pyodbc.Connection): 데이터베이스 커넥션 객체.
        sql (str): 실행할 SQL 쿼리.

    Returns:
        tuple[str, str, str]: (plan_xml, stats_io, stats_time)
    """
    cursor = conn.cursor()
    plan_xml = None
    stats_io = []
    stats_time = []

    try:
        # 실행 계획과 통계 수집을 위한 세션 설정
        cursor.execute("SET STATISTICS XML ON;")
        cursor.execute("SET STATISTICS IO ON;")
        cursor.execute("SET STATISTICS TIME ON;")

        # 쿼리 실행
        cursor.execute(sql)

        # 실행 계획 XML 가져오기
        cursor.nextset()
        plan_xml = cursor.fetchone()[0]

        # 통계 정보 가져오기 (메시지 파싱)
        for info in conn.getinfo(pyodbc.SQL_INFO_DRIVER_MESSAGES):
            info_str = info.strip()
            if info_str.startswith("Table"):
                stats_io.append(info_str)
            elif info_str.startswith("SQL Server Execution Times"):
                stats_time.append(info_str)

    except pyodbc.Error as e:
        print(f"Error executing query: {e}")
        # 에러 발생 시 롤백
        conn.rollback()
    finally:
        # 세션 설정 초기화
        cursor.execute("SET STATISTICS XML OFF;")
        cursor.execute("SET STATISTICS IO OFF;")
        cursor.execute("SET STATISTICS TIME OFF;")
        cursor.close()

    return plan_xml, "\n".join(stats_io), "\n".join(stats_time)