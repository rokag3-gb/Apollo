import sys
import os
import pandas as pd
from stable_baselines3 import DQN

# 경로 설정
sys.path.append(os.path.join(os.getcwd(), 'Apollo.ML'))

from RLQO.env.phase2_db_env import QueryPlanDBEnv, apply_action_to_sql
from db import execute_query, connect
from config import AppConfig

# --- 설정 ---
MODEL_PATH = "Apollo.ML/artifacts/RLQO/models/dqn_v1.zip"
ACTION_SPACE_PATH = "Apollo.ML/artifacts/RLQO/configs/phase2_action_space.json"

# 평가에 사용할 샘플 쿼리 목록
# (실제로는 대표적인 성능 문제를 가진 쿼리들을 선택해야 합니다)
SAMPLE_QUERIES = [
    #"SELECT * FROM Users WHERE Email LIKE '%.com';",
    #"SELECT TOP 100 * FROM Orders o JOIN Users u ON o.UserId = u.UserId ORDER BY o.OrderDate DESC;",
    "SELECT execution_id FROM dbo.exe_execution e;"
    , "SELECT AccountID=o.account_id, SecID=o.security_id, Side=o.side, Qty=e.exec_qty, Price=e.exec_price, Fee=e.fee, Tax=e.tax FROM dbo.exe_execution e JOIN dbo.ord_order o ON e.order_id=o.order_id;"
    , "SELECT TOP 100 * FROM dbo.risk_exposure_snapshot WHERE CAST(ts AS DATE) = cast(getdate() as date);"
    , "SELECT e.execution_id, o.account_id, s.symbol, o.side, e.exec_qty, e.exec_price, e.exec_time FROM dbo.exe_execution e JOIN dbo.ord_order o ON e.order_id=o.order_id JOIN dbo.ref_security s ON o.security_id=s.security_id ORDER BY e.exec_time DESC;"
    , "SELECT e.* FROM dbo.exe_execution e WHERE NOT EXISTS (SELECT 1 FROM dbo.ord_order o WHERE o.order_id = e.order_id);"
    , "SELECT OBJECT_NAME(ips.object_id) AS TableName, si.name AS IndexName, ips.index_type_desc, ips.avg_fragmentation_in_percent FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'SAMPLED') AS ips JOIN sys.indexes AS si ON ips.object_id = si.object_id AND ips.index_id = si.index_id WHERE ips.avg_fragmentation_in_percent > 30.0 ORDER BY ips.avg_fragmentation_in_percent DESC;"
    , "SELECT account_id, GETDATE(), RAND()*100000, RAND()*50000, 0, 0 FROM dbo.cust_account WHERE closed_at IS NULL;"
]

def evaluate_agent():
    """
    학습된 DQN 에이전트의 성능을 샌드박스 DB에서 평가합니다.
    """
    print("--- Phase 2: Agent Evaluation Start ---")

    # 1. 모델 및 환경 로드
    print(f"Loading model from {MODEL_PATH}...")
    try:
        model = DQN.load(MODEL_PATH)
    except FileNotFoundError:
        print(f"Error: Model not found at {MODEL_PATH}. Did you run Phase 1 training?")
        return
        
    print("Initializing DB environment...")
    env = QueryPlanDBEnv(query_list=SAMPLE_QUERIES)
    
    results = []

    # 2. 각 쿼리에 대해 평가 진행
    for i, query in enumerate(SAMPLE_QUERIES):
        print(f"\n--- Evaluating Query {i+1}/{len(SAMPLE_QUERIES)} ---")
        print(f"Original Query: {query}")

        # --- Baseline (힌트 없음) ---
        print("Running Baseline...")
        obs, info = env.reset(seed=i) # 재현성을 위해 seed 설정
        baseline_metrics = info.get('metrics', {})
        print(f"  - Baseline Metrics: {baseline_metrics}")

        # --- Agent's Turn ---
        print("Agent is predicting an action...")
        action_id, _ = model.predict(obs, deterministic=True)
        action = env.actions[action_id]
        print(f"  - Agent's chosen action: {action['name']}")
        
        modified_sql = apply_action_to_sql(query, action)
        print(f"  - Modified SQL: {modified_sql}")
        
        # 에이전트가 제안한 쿼리 실행
        print("Running Agent's suggested query...")
        _, stats_io, agent_stats_time = execute_query(env.db_connection, modified_sql)
        
        # [FIX] 에이전트의 행동으로 쿼리 실행이 실패하여 통계가 없는 경우 방어
        agent_elapsed_time = float('inf') # 실패 시 무한대로 초기화
        if agent_stats_time and 'elapsed time' in agent_stats_time:
            try:
                agent_elapsed_time = int(re.findall(r'elapsed time = (\d+) ms', agent_stats_time)[0])
            except (IndexError, ValueError):
                 print("  - Warning: Could not parse agent's execution time.")
        else:
            print("  - Warning: Agent's action may have resulted in an invalid query (no execution time stats).")

        print(f"  - Agent Metrics: {{'elapsed_time_ms': {agent_elapsed_time}}}")

        results.append({
            "query": query,
            "baseline_elapsed_ms": baseline_metrics.get('elapsed_time_ms', -1),
            "agent_action": action['name'],
            "agent_elapsed_ms": agent_elapsed_time
        })

    env.close()

    # 3. 결과 요약 출력
    print("\n--- Evaluation Summary ---")
    df = pd.DataFrame(results)
    df['improvement_%'] = 100 * (df['baseline_elapsed_ms'] - df['agent_elapsed_ms']) / df['baseline_elapsed_ms']
    print(df.to_string())
    print("\n--- Phase 2: Agent Evaluation Complete ---")


if __name__ == '__main__':
    # phase2_features.py에 lxml이 필요하므로 import re 추가
    import re
    evaluate_agent()
