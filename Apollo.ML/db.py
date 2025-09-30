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

    # 모든 SET 구문과 실제 쿼리를 하나의 배치로 묶어 실행
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

        # 모든 결과 셋(Result Set)을 순회하며 실행 계획을 찾음
        while True:
            try:
                # 현재 결과 셋이 실행 계획 XML인지 확인
                row = cursor.fetchone()
                if row and row[0] and isinstance(row[0], str) and row[0].strip().startswith('<'):
                    plan_xml = row[0]
                
                # 현재 결과 셋의 나머지 데이터가 있다면 소모
                # fetchall()을 호출하면 일부 드라이버에서 문제가 생길 수 있으므로,
                # 한 번에 하나의 row만 처리하는 지금의 방식이 더 안정적일 수 있음
                
            except pyodbc.ProgrammingError:
                # 현재 결과 셋에 row가 없는 경우 (예: SET 구문 결과, 데이터가 없는 쿼리 결과)
                pass

            # 다음 결과 셋으로 이동, 없으면 루프 종료
            if not cursor.nextset():
                break

        # [NEW] cursor.messages를 사용하여 안정적으로 통계 정보 수집
        for _, message in cursor.messages:
            for line in message.split('\\n'):
                line = line.strip()
                if line.startswith("Table"):
                    stats_io.append(line)
                elif line.startswith("SQL Server Execution Times"):
                    stats_time.append(line)

    except pyodbc.Error as e:
        print(f"Error executing query: {e}")
        # 에러 발생 시 롤백
        conn.rollback()
    finally:
        cursor.close()

    # [NEW] 방어 코드: 반환된 실행 계획이 유효한지 최종 검사
    if not isinstance(plan_xml, str):
        print(f"Warning: Invalid execution plan received (type: {type(plan_xml)}). Treating as no plan found.")
        plan_xml = None

    return plan_xml, "\\n".join(stats_io), "\\n".join(stats_time)