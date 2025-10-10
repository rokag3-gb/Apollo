# -*- coding: utf-8 -*-
"""
DQN v2: XGBoost 시뮬레이션 환경
실제 DB 실행 없이 XGB 예측 모델(R² = 0.9955)로 쿼리 성능을 시뮬레이션합니다.
빠른 학습(200K+ 타임스텝)이 가능하며, 이후 실제 DB에서 Fine-tuning합니다.
"""

import json
import os
import pickle
import gymnasium as gym
import joblib
import numpy as np
from gymnasium import spaces

from RLQO.features.phase2_features import XGB_EXPECTED_FEATURES
from RLQO.env.v2_reward import calculate_reward_v2


def simulate_query_execution(xgb_model, current_features, action_features):
    """
    XGB 모델을 사용하여 액션 적용 후 쿼리 실행 시간을 예측합니다.
    
    Args:
        xgb_model: 학습된 XGBoost 모델
        current_features: 현재 상태의 특징 벡터 (79차원)
        action_features: 액션으로 인한 특징 변화
    
    Returns:
        predicted_metrics: 예측된 실행 메트릭 (elapsed_time_ms, logical_reads, cpu_time_ms)
    """
    # 액션 적용 후 특징 벡터 생성
    modified_features = current_features.copy()
    
    # === 액션별 특징 수정 ===
    # Feature indices (phase2_features.py 기준):
    # [0] estimated_rows
    # [1] estimated_cost
    # [2] parallelism_degree
    # [3] join_type_hash
    # [4] join_type_loop
    # [5] scan_type_index
    # [6] scan_type_table
    # [7] logical_reads
    # [8] cpu_time_ms
    # [9] elapsed_time_ms
    
    # MAXDOP 액션
    if 'parallelism_degree_change' in action_features:
        modified_features[2] = action_features['parallelism_degree_change']
    
    # JOIN 타입 힌트
    if 'join_type_hash' in action_features:
        modified_features[3] = action_features['join_type_hash']
        modified_features[4] = action_features.get('join_type_loop', 0)
    
    # SCAN 타입 변경 (인덱스 힌트)
    if 'scan_type_index' in action_features:
        modified_features[5] = action_features['scan_type_index']
        modified_features[6] = action_features.get('scan_type_table', 0)
    
    # 비용 승수 (NOLOCK, REWRITE 등)
    cost_multiplier = action_features.get('estimated_cost_multiplier', 1.0)
    modified_features[1] *= cost_multiplier  # estimated_cost
    
    # XGB 모델로 실행 시간 예측
    predicted_time_ms = xgb_model.predict([modified_features])[0]
    
    # 비용 승수를 실행 시간에도 반영
    predicted_time_ms *= cost_multiplier
    
    # 논리적 읽기 추정 (시간과 상관관계, 실제로는 별도 모델 필요)
    # 간단히 선형 관계 가정: 1ms ≈ 100 logical reads
    estimated_logical_reads = int(predicted_time_ms * 100)
    
    # CPU 시간 추정 (일반적으로 전체 시간의 60-80%)
    estimated_cpu_time_ms = predicted_time_ms * 0.7
    
    predicted_metrics = {
        'elapsed_time_ms': float(max(0.1, predicted_time_ms)),  # 최소 0.1ms
        'logical_reads': max(1, estimated_logical_reads),
        'cpu_time_ms': float(max(0.1, estimated_cpu_time_ms)),
    }
    
    return predicted_metrics


def map_action_to_features(action: dict, current_features: np.ndarray) -> dict:
    """
    액션 딕셔너리를 특징 벡터 변화로 매핑합니다.
    
    Args:
        action: 적용할 액션 (phase2_action_space.json)
        current_features: 현재 상태의 특징 벡터
    
    Returns:
        action_features: 액션으로 인한 특징 변화 딕셔너리
    """
    action_features = {}
    action_type = action.get('type')
    action_value = action.get('value', '')
    
    if action_type == "HINT":
        # MAXDOP 힌트
        if "MAXDOP 1" in action_value:
            action_features['parallelism_degree_change'] = 1
            action_features['estimated_cost_multiplier'] = 1.05  # 단일 스레드는 약간 느림
        elif "MAXDOP 4" in action_value:
            action_features['parallelism_degree_change'] = 4
            action_features['estimated_cost_multiplier'] = 0.85  # 병렬 처리 개선
        elif "MAXDOP 8" in action_value:
            action_features['parallelism_degree_change'] = 8
            action_features['estimated_cost_multiplier'] = 0.75  # 더 큰 병렬 개선
        
        # JOIN 타입 힌트
        elif "HASH JOIN" in action_value:
            action_features['join_type_hash'] = 1
            action_features['join_type_loop'] = 0
            # Hash Join은 대용량 데이터에 유리
            if current_features[0] > 1000:  # estimated_rows > 1000
                action_features['estimated_cost_multiplier'] = 0.90
            else:
                action_features['estimated_cost_multiplier'] = 1.10  # 소량 데이터에는 비효율
        
        elif "LOOP JOIN" in action_value:
            action_features['join_type_hash'] = 0
            action_features['join_type_loop'] = 1
            # Nested Loop는 소량 데이터에 유리
            if current_features[0] < 1000:
                action_features['estimated_cost_multiplier'] = 0.85
            else:
                action_features['estimated_cost_multiplier'] = 1.20  # 대용량에는 비효율
        
        elif "MERGE JOIN" in action_value:
            # Merge Join은 정렬된/인덱싱된 데이터에 유리
            action_features['estimated_cost_multiplier'] = 0.95
        
        # 조인 순서 강제
        elif "FORCE ORDER" in action_value:
            # 최적화기의 선택을 무시하므로 위험할 수 있음
            action_features['estimated_cost_multiplier'] = 1.15
        
        # 파라미터 스니핑 관련
        elif "OPTIMIZE FOR UNKNOWN" in action_value:
            # 평균 통계 기반, 안정적
            action_features['estimated_cost_multiplier'] = 1.0
        
        elif "DISABLE_PARAMETER_SNIFFING" in action_value:
            # 파라미터 스니핑 비활성화
            action_features['estimated_cost_multiplier'] = 1.05
        
        # 호환성 레벨 변경
        elif "COMPATIBILITY_LEVEL_140" in action_value:
            # SQL 2017 최적화기 (안정적)
            action_features['estimated_cost_multiplier'] = 1.0
        
        elif "COMPATIBILITY_LEVEL_150" in action_value:
            # SQL 2019 최적화기 (균형)
            action_features['estimated_cost_multiplier'] = 0.98
        
        elif "COMPATIBILITY_LEVEL_160" in action_value:
            # SQL 2022 최적화기 (최신, 다소 불안정 가능)
            action_features['estimated_cost_multiplier'] = 0.95
        
        # RECOMPILE
        elif "RECOMPILE" in action_value:
            # 매번 재컴파일, 통계 변화가 심한 경우 유용
            action_features['estimated_cost_multiplier'] = 1.1
        
        # FAST n (TOP 쿼리 최적화)
        elif "FAST" in action_value:
            # TOP이 있는 쿼리에 매우 유용
            # 첫 n개 행을 빠르게 반환하도록 최적화
            action_features['estimated_cost_multiplier'] = 0.8  # 약 20% 개선
    
    elif action_type == "TABLE_HINT":
        # NOLOCK 힌트
        if "NOLOCK" in action_value:
            # 락 대기 없음, 약간의 성능 향상
            action_features['estimated_cost_multiplier'] = 0.95
        
        # 인덱스 힌트
        elif "INDEX" in action_value:
            action_features['scan_type_index'] = 1
            action_features['scan_type_table'] = 0
            # 적절한 인덱스 사용은 성능 대폭 향상
            action_features['estimated_cost_multiplier'] = 0.70
    
    elif action_type == "REWRITE":
        # SELECT * 제거 등
        # 불필요한 컬럼 제거로 IO 감소
        action_features['estimated_cost_multiplier'] = 0.85
    
    return action_features


class QueryPlanSimEnv(gym.Env):
    """
    XGBoost 모델 기반 시뮬레이션 환경.
    실제 DB 실행 없이 빠르게 강화학습 에이전트를 훈련합니다.
    
    특징:
    - 실행 속도: 실제 DB의 100배 이상 빠름
    - 정확도: R² = 0.9955 수준의 높은 예측 정확도
    - 안전성: 잘못된 쿼리도 시스템에 영향 없음
    """
    
    def __init__(self, query_list: list[str], xgb_model_path: str, max_steps=10, verbose=True, 
                 plan_cache_path='Apollo.ML/artifacts/RLQO/cache/plan_cache.pkl'):
        super().__init__()
        
        # 1. XGB 모델 로드
        self.xgb_model = joblib.load(xgb_model_path)
        if verbose:
            print(f"[SimEnv] XGB 모델 로드 완료: {xgb_model_path}")
        
        # 2. 실행 계획 캐시 로드
        if os.path.exists(plan_cache_path):
            with open(plan_cache_path, 'rb') as f:
                self.plan_cache = pickle.load(f)
            if verbose:
                print(f"[SimEnv] 실행 계획 캐시 로드 완료: {len(self.plan_cache)}개")
        else:
            if verbose:
                print(f"[SimEnv] 경고: 캐시 파일 없음. v2_collect_plans.py를 먼저 실행하세요!")
                print(f"[SimEnv] 휴리스틱 모드로 폴백합니다.")
            self.plan_cache = None
        
        # 3. 액션 스페이스 로드 (v2: 15개 액션)
        action_space_path = 'Apollo.ML/artifacts/RLQO/configs/v2_action_space.json'
        with open(action_space_path, 'r', encoding='utf-8') as f:
            self.actions = json.load(f)
        if verbose:
            print(f"[SimEnv] 액션 스페이스 로드 완료: {len(self.actions)}개 액션")
        
        # 3. 쿼리 목록 및 에피소드 변수
        self.query_list = query_list
        self.current_query_ix = 0
        self.current_sql = ""
        self.max_steps = max_steps
        self.current_step = 0
        self.verbose = verbose
        
        # 4. Gym 인터페이스 정의
        self.action_space = spaces.Discrete(len(self.actions))
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(XGB_EXPECTED_FEATURES,), dtype=np.float32
        )
        
        # 5. 메트릭 저장
        self.baseline_metrics = {}
        self.current_metrics = {}
        self.current_obs = None
        
        # 6. 시뮬레이션 노이즈 (현실성 증가)
        self.add_noise = True
        self.noise_std = 0.03  # 예측값의 3% 표준편차 (R²=0.9955 반영)
    
    def _generate_baseline_features(self, sql: str) -> np.ndarray:
        """
        쿼리 텍스트에서 베이스라인 특징 벡터를 생성합니다.
        실제 DB 실행 없이 쿼리 구조 분석을 통해 근사적으로 생성합니다.
        """
        features = np.zeros(XGB_EXPECTED_FEATURES, dtype=np.float32)
        sql_upper = sql.upper()
        
        # === 쿼리 구조 분석 ===
        join_count = sql_upper.count('JOIN')
        subquery_count = max(0, sql_upper.count('SELECT') - 1)
        table_count = sql_upper.count('FROM') + join_count
        
        # Feature vector indices (phase2_features.py 기준)
        features[10] = join_count           # join_count
        features[11] = subquery_count       # subquery_count
        features[12] = table_count          # table_count
        
        # 추정 rows (JOIN 개수 기반 휴리스틱)
        features[0] = 1000 * (2 ** join_count)  # exponential growth
        
        # 추정 cost (복잡도 기반)
        base_cost = 5.0
        base_cost *= (join_count + 1) * (table_count + 1)
        
        # 집계 함수
        if any(agg in sql_upper for agg in ['SUM', 'AVG', 'COUNT', 'MAX', 'MIN']):
            base_cost *= 1.5
        
        # 윈도우 함수
        if 'OVER' in sql_upper and 'PARTITION BY' in sql_upper:
            base_cost *= 2.0
        
        # GROUP BY
        if 'GROUP BY' in sql_upper:
            base_cost *= 1.3
        
        # ORDER BY
        if 'ORDER BY' in sql_upper:
            base_cost *= 1.2
        
        # CTE (WITH)
        if 'WITH' in sql_upper and 'AS (' in sql_upper:
            features[11] += 1  # CTE도 서브쿼리로 간주
            base_cost *= 1.4
        
        features[1] = base_cost  # estimated_cost
        
        # 기본값: Index Scan 가정
        features[5] = 1  # scan_type_index
        
        return features
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # 다음 쿼리 선택
        self.current_sql = self.query_list[self.current_query_ix]
        query_id = self.current_query_ix
        self.current_query_ix = (self.current_query_ix + 1) % len(self.query_list)
        self.current_step = 0
        
        # 캐시에서 베이스라인 로드 (가능한 경우)
        if self.plan_cache:
            cache_key = f"query_{query_id}_baseline"
            if cache_key in self.plan_cache:
                cached = self.plan_cache[cache_key]
                self.current_obs = cached['features']
                self.baseline_metrics = cached['metrics'].copy()
                
                # 0으로 나누기 방지 (최소값 보장)
                self.baseline_metrics['elapsed_time_ms'] = max(0.1, self.baseline_metrics.get('elapsed_time_ms', 0.1))
                self.baseline_metrics['logical_reads'] = max(1, self.baseline_metrics.get('logical_reads', 1))
                self.baseline_metrics['cpu_time_ms'] = max(0.1, self.baseline_metrics.get('cpu_time_ms', 0.1))
                
                self.current_metrics = self.baseline_metrics.copy()
                
                if self.verbose:
                    print(f"\n[SimEnv] Episode: Query {query_id}/{len(self.query_list)} (캐시 사용)")
                    print(f"  Baseline: {self.baseline_metrics['elapsed_time_ms']:.2f} ms")
                
                return self.current_obs, {"metrics": self.baseline_metrics}
        
        # 캐시 미스: 휴리스틱 폴백
        self.current_obs = self._generate_baseline_features(self.current_sql)
        predicted_time = self.xgb_model.predict([self.current_obs])[0]
        
        # 예측값이 0이 되는 것을 방지 (최소 0.1ms)
        predicted_time = max(0.1, predicted_time)
        
        if self.add_noise:
            noise = np.random.normal(0, predicted_time * self.noise_std)
            predicted_time = max(0.1, predicted_time + noise)
        
        self.baseline_metrics = {
            'elapsed_time_ms': float(max(0.1, predicted_time)),
            'logical_reads': max(1, int(predicted_time * 100)),
            'cpu_time_ms': max(0.1, predicted_time * 0.7)
        }
        
        self.current_metrics = self.baseline_metrics.copy()
        
        if self.verbose:
            print(f"\n[SimEnv] Episode: Query {query_id}/{len(self.query_list)} (휴리스틱)")
            print(f"  Baseline: {predicted_time:.2f} ms")
        
        return self.current_obs, {"metrics": self.baseline_metrics}
    
    def step(self, action_id):
        self.current_step += 1
        action = self.actions[action_id]
        
        # 캐시에서 로드 시도
        if self.plan_cache:
            # 현재 쿼리의 원본 인덱스 계산
            query_id = (self.current_query_ix - 1) % len(self.query_list)
            cache_key = f"query_{query_id}_action_{action_id}"
            
            if cache_key in self.plan_cache:
                # 캐시 히트!
                cached = self.plan_cache[cache_key]
                next_obs = cached['features']
                predicted_metrics = cached['metrics'].copy()
                
                # 노이즈 추가
                if self.add_noise:
                    noise = np.random.normal(0, predicted_metrics['elapsed_time_ms'] * self.noise_std)
                    predicted_metrics['elapsed_time_ms'] = max(0.1, predicted_metrics['elapsed_time_ms'] + noise)
            else:
                # 캐시 미스: 시뮬레이션으로 폴백
                action_features = map_action_to_features(action, self.current_obs)
                predicted_metrics = simulate_query_execution(
                    self.xgb_model, self.current_obs, action_features
                )
                
                if self.add_noise:
                    noise = np.random.normal(0, predicted_metrics['elapsed_time_ms'] * self.noise_std)
                    predicted_metrics['elapsed_time_ms'] = max(0.1, predicted_metrics['elapsed_time_ms'] + noise)
                
                # 다음 상태 생성
                next_obs = self.current_obs.copy()
                if 'parallelism_degree_change' in action_features:
                    next_obs[2] = action_features['parallelism_degree_change']
                if 'join_type_hash' in action_features:
                    next_obs[3] = action_features['join_type_hash']
                    next_obs[4] = action_features.get('join_type_loop', 0)
                if 'scan_type_index' in action_features:
                    next_obs[5] = action_features['scan_type_index']
                    next_obs[6] = action_features.get('scan_type_table', 0)
        else:
            # 캐시 없음: 시뮬레이션만 사용
            action_features = map_action_to_features(action, self.current_obs)
            predicted_metrics = simulate_query_execution(
                self.xgb_model, self.current_obs, action_features
            )
            
            if self.add_noise:
                noise = np.random.normal(0, predicted_metrics['elapsed_time_ms'] * self.noise_std)
                predicted_metrics['elapsed_time_ms'] = max(0.1, predicted_metrics['elapsed_time_ms'] + noise)
            
            # 다음 상태 생성
            next_obs = self.current_obs.copy()
            if 'parallelism_degree_change' in action_features:
                next_obs[2] = action_features['parallelism_degree_change']
            if 'join_type_hash' in action_features:
                next_obs[3] = action_features['join_type_hash']
                next_obs[4] = action_features.get('join_type_loop', 0)
            if 'scan_type_index' in action_features:
                next_obs[5] = action_features['scan_type_index']
                next_obs[6] = action_features.get('scan_type_table', 0)
        
        # 4. 보상 계산 (v2.1 보상 함수 사용 - 안전성 점수 포함)
        safety_score = action.get('safety_score', 1.0)
        reward = calculate_reward_v2(
            self.current_metrics, 
            predicted_metrics,
            self.baseline_metrics,
            step_num=self.current_step,
            max_steps=self.max_steps,
            action_safety_score=safety_score
        )
        
        # 5. 상태 업데이트
        self.current_obs = next_obs
        self.current_metrics = predicted_metrics
        
        # 6. 종료 조건
        terminated = False
        truncated = self.current_step >= self.max_steps
        
        improvement_pct = (
            (self.baseline_metrics['elapsed_time_ms'] - predicted_metrics['elapsed_time_ms']) 
            / self.baseline_metrics['elapsed_time_ms'] * 100
        )
        
        info = {
            "metrics": predicted_metrics, 
            "action_name": action['name'],
            "improvement_pct": improvement_pct
        }
        
        if self.verbose and self.current_step == 1:
            print(f"  Action: {action['name']}, Time: {predicted_metrics['elapsed_time_ms']:.2f} ms, "
                  f"Reward: {reward:.3f}, Improvement: {improvement_pct:.1f}%")
        
        return self.current_obs, reward, terminated, truncated, info
    
    def close(self):
        pass


if __name__ == '__main__':
    # 단위 테스트
    from RLQO.constants import SAMPLE_QUERIES
    
    print("=== QueryPlanSimEnv 단위 테스트 ===\n")
    
    env = QueryPlanSimEnv(
        query_list=SAMPLE_QUERIES[:3],
        xgb_model_path='Apollo.ML/artifacts/model.joblib',
        verbose=True
    )
    
    for episode in range(2):
        print(f"\n{'='*60}")
        print(f"Episode {episode + 1}")
        print(f"{'='*60}")
        
        obs, info = env.reset(seed=episode)
        print(f"초기 상태 shape: {obs.shape}")
        print(f"베이스라인: {info['metrics']}")
        
        total_reward = 0
        for step in range(3):
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            
            print(f"  Step {step + 1}: "
                  f"Action={env.actions[action]['name']}, "
                  f"Reward={reward:.3f}, "
                  f"Improvement={info['improvement_pct']:.1f}%")
            
            if terminated or truncated:
                break
        
        print(f"Episode 총 보상: {total_reward:.3f}")
    
    env.close()
    print("\n[SUCCESS] 시뮬레이션 환경 테스트 완료!")

