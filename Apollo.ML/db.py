import pyodbc, pandas as pd
from config import DBConfig
import subprocess
import time

def connect(cfg: DBConfig, max_retries: int = 3, retry_delay: int = 5) -> pyodbc.Connection:
    """데이터베이스에 연결합니다. 재시도 로직 포함."""
    conn_str = (
        f"DRIVER={{{cfg.driver}}};SERVER={cfg.server};DATABASE={cfg.database};"
        f"UID={cfg.username};PWD={cfg.password};Encrypt=yes;TrustServerCertificate=yes;"
    )
    
    for attempt in range(max_retries):
        try:
            conn = pyodbc.connect(conn_str)
            print(f"[DB] 연결 성공 (시도 {attempt + 1}/{max_retries})")
            return conn
        except pyodbc.Error as e:
            print(f"[DB] 연결 실패 (시도 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"[DB] {retry_delay}초 후 재시도...")
                time.sleep(retry_delay)
            else:
                print(f"[DB] 최대 재시도 횟수 초과. 연결 실패.")
                raise e

def fetch_collected_plans(conn: pyodbc.Connection) -> pd.DataFrame:
    sql = "SELECT query_id, plan_id, plan_xml, count_exec, est_total_subtree_cost, avg_ms, last_cpu_ms, last_reads, max_used_mem_kb, max_dop, last_exec_time, last_ms FROM dbo.collected_plans"
    return pd.read_sql(sql, conn)

def get_execution_plan(conn: pyodbc.Connection, sql: str) -> str:
    """SET SHOWPLAN_XML을 사용하여 쿼리의 실행 계획(XML)만 반환합니다."""
    cursor = conn.cursor()
    plan_xml = None
    try:
        # SHOWPLAN은 배치 내에서 단독으로 실행되어야 합니다.
        cursor.execute("SET NOCOUNT ON;")
        cursor.execute("SET SHOWPLAN_XML ON;")
        # CTE 쿼리를 위해 SQL 앞에 세미콜론 추가 (이전 문장 종료)
        safe_sql = f"; {sql}" if sql.strip().upper().startswith('WITH') else sql
        cursor.execute(safe_sql)
        row = cursor.fetchone()
        if row and row[0] and isinstance(row[0], str):
            plan_xml = row[0]
        cursor.execute("SET SHOWPLAN_XML OFF;")
        cursor.execute("SET NOCOUNT OFF;")
    except pyodbc.Error as e:
        print(f"Error getting execution plan: {e}")
        print(f"SQL that caused error: {sql[:500]}...")  # 처음 500자 출력
        conn.rollback()
    finally:
        cursor.close()
    return plan_xml

def get_query_statistics(conn: pyodbc.Connection, sql: str) -> tuple[str, str]:
    """[MOD] sqlcmd를 사용하여 쿼리를 실행하고 통계 정보를 캡처합니다."""
    
    # pyodbc 연결 정보에서 설정 값을 가져옵니다.
    # conn.getinfo()는 pyodbc의 숨겨진 기능일 수 있으므로, 더 명시적인 방법이 필요할 수 있습니다.
    # 여기서는 config를 다시 로드하는 대신, 연결 문자열에서 파싱하는 방식을 가정합니다.
    # 하지만 가장 간단한 방법은 connect 함수가 사용한 config 객체를 어딘가에 저장해두는 것입니다.
    # 이 테스트에서는 config 값을 하드코딩하거나, 다시 로드하는 방식을 사용해야 합니다.
    # 임시방편으로 config를 다시 로드하겠습니다.
    from config import load_config
    config = load_config('Apollo.ML/config.yaml').db

    # sqlcmd 명령어 구성
    # 중요: 실제 환경에서는 비밀번호를 명령어에 직접 노출하지 않도록 주의해야 합니다.
    # CTE 쿼리를 위해 SQL 앞에 세미콜론 추가 (이전 문장 종료)
    safe_sql = f"; {sql}" if sql.strip().upper().startswith('WITH') else sql
    command = [
        'sqlcmd',
        '-S', config.server,
        '-d', config.database,
        '-U', config.username,
        '-P', config.password,
        '-Q', f"SET STATISTICS IO ON; SET STATISTICS TIME ON; {safe_sql}",
        '-s', '|', # 구분자 변경 (옵션)
        '-W' # 너비 제한 제거
    ]

    stats_io_list = []
    stats_time_list = []
    
    try:
        # [MOD] 한국어 Windows 환경을 고려하여 encoding을 'cp949'로 지정하고, 오류 발생 시에도 None이 아닌 stderr를 반환하도록 수정
        # 타임아웃 단축 (15초) - 빠른 실패로 재시도 로직 활용
        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='cp949', errors='ignore', timeout=15)

        if result.returncode != 0:
            print(f"sqlcmd execution failed with return code {result.returncode}:")
            print(f"Stderr: {result.stderr}")
            return "", ""

        output = result.stdout
        output_lines = output.splitlines()

        for i, line in enumerate(output_lines):
            line = line.strip()
            if "Table '" in line:
                stats_io_list.append(line)
            elif "SQL Server Execution Times:" in line:
                # 'Execution Times:' 라인과 그 다음 라인(시간 정보)을 함께 추가
                if i + 1 < len(output_lines):
                    full_time_info = line + " " + output_lines[i+1].strip()
                    stats_time_list.append(full_time_info)
                
    except subprocess.CalledProcessError as e:
        print(f"sqlcmd execution failed: {e}")
        print(f"Stderr: {e.stderr}")
        return "", ""
    except subprocess.TimeoutExpired:
        print("sqlcmd execution timed out after 15 seconds")
        return "", ""
    except FileNotFoundError:
        print("Error: 'sqlcmd' is not in your PATH. Please install SQL Server Command Line Utilities.")
        return "", ""
        
    stats_io_str = "\n".join(stats_io_list)
    # 마지막 Execution Times 블록만 사용
    stats_time_str = "\n".join(stats_time_list)

    return stats_io_str, stats_time_str