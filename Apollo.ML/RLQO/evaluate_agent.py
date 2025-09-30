print("--- [DEBUG] Starting evaluate_agent.py script ---")
import sys
import os
import pandas as pd
from stable_baselines3 import DQN

# --- [MOD] 견고한 경로 설정 ---
# 현재 파일의 절대 경로를 찾습니다.
current_file_path = os.path.abspath(__file__)
# RLQO 폴더 경로
rlqo_dir = os.path.dirname(current_file_path)
# Apollo.ML 폴더 경로
apollo_ml_dir = os.path.dirname(rlqo_dir)
# 프로젝트 루트 경로 (C:\source\Apollo)
project_root = os.path.dirname(apollo_ml_dir)

# 파이썬 경로에 프로젝트 루트와 Apollo.ML을 추가하여 모듈 임포트 문제를 해결합니다.
sys.path.append(project_root)
sys.path.append(apollo_ml_dir)


from RLQO.env.phase2_db_env import QueryPlanDBEnv, apply_action_to_sql
from db import execute_query, connect
from config import AppConfig
from RLQO.constants import SAMPLE_QUERIES # [NEW]

# --- 설정 ---
MODEL_PATH = "Apollo.ML/artifacts/RLQO/models/dqn_v1_5.zip" # [MOD] v1.5 모델 사용
ACTION_SPACE_PATH = "Apollo.ML/artifacts/RLQO/configs/phase2_action_space.json"

# [MOD] SAMPLE_QUERIES는 constants.py로 이동

def evaluate_agent():
    """
    학습된 DQN 에이전트의 성능을 샌드박스 DB에서 평가합니다.
    """
    try:
        print("--- Phase 2: Agent Evaluation Start ---")

        # 1. 모델 및 환경 로드
        print(f"Loading model from {MODEL_PATH}...")
        model = DQN.load(MODEL_PATH)
            
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
            # [MOD] env의 메소드를 사용하여 안전하게 쿼리 실행
            _, agent_metrics = env._get_obs_from_db(modified_sql)
            agent_elapsed_time = agent_metrics.get('elapsed_time_ms', float('inf'))

            if agent_elapsed_time == float('inf'):
                print("  - Warning: Agent's action may have resulted in an invalid query (no execution time stats).")
            
            print(f"  - Agent Metrics: {agent_metrics}")

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
        # [MOD] 0으로 나누기 오류 방지
        df['improvement_%'] = 100 * (df['baseline_elapsed_ms'] - df['agent_elapsed_ms']) / (df['baseline_elapsed_ms'] + 1e-9)
        print(df.to_string())
        print("\n--- Phase 2: Agent Evaluation Complete ---")

    except Exception as e:
        import traceback
        print(f"\nAn unexpected error occurred during evaluation: {e}")
        print(traceback.format_exc())

if __name__ == '__main__':
    evaluate_agent()
