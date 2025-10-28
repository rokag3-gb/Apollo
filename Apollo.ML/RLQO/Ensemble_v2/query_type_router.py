# -*- coding: utf-8 -*-
"""
Ensemble v2: Query Type Router

쿼리 타입별로 적합한 액션을 필터링하고 전략을 선택합니다.
특히 TOP 쿼리 성능 개선에 초점을 맞춥니다.
"""

from typing import Dict, List, Optional
from collections import Counter


class QueryTypeRouter:
    """
    쿼리 타입별 액션 필터링 및 전략 선택
    
    v2의 핵심 개선사항:
    - TOP 쿼리에서 LOOP_JOIN 억제, FAST 힌트 선호
    - JOIN_HEAVY 쿼리에서 JOIN 힌트만 허용
    - SIMPLE 쿼리에서 액션 자제 (NO_ACTION 선호)
    """
    
    def __init__(self, verbose: bool = False):
        """
        Args:
            verbose: 필터링 과정 로깅 여부
        """
        self.verbose = verbose
        
        # 쿼리 타입별 허용 액션 정의
        self.allowed_actions = {
            'TOP': [14, 15, 16, 17, 18],      # FAST_10/50/100/200, NO_ACTION
            'JOIN_HEAVY': [3, 4, 5, 6, 18],   # HASH/LOOP/MERGE/FORCE, NO_ACTION
            'CTE': [3, 4, 5, 6, 7, 13, 18],   # JOIN 힌트 + OPTIMIZE + RECOMPILE
            'AGGREGATE': [0, 1, 2, 7, 18],    # MAXDOP + OPTIMIZE_FOR_UNKNOWN
            'SIMPLE': [18],                    # NO_ACTION만 (최소 개입)
            'SUBQUERY': [3, 4, 5, 7, 13, 18], # JOIN 힌트 + OPTIMIZE + RECOMPILE
            'WINDOW': [0, 1, 2, 7, 18],       # MAXDOP + OPTIMIZE_FOR_UNKNOWN
            'DEFAULT': list(range(19)),        # 모든 액션 허용
        }
        
        # TOP 쿼리 특별 규칙
        self.top_query_rules = {
            'prefer_fast_hints': True,      # FAST 힌트 선호
            'penalize_loop_join': True,     # LOOP_JOIN 억제 (v1에서 과다 사용)
            'boost_no_action': True,        # NO_ACTION 선호도 증가
        }
        
        # 통계
        self.filter_stats = {
            'total_calls': 0,
            'filtered_by_type': {},   # query_type -> count
            'actions_blocked': {},    # action_id -> count
        }
    
    def filter_actions_for_query(
        self,
        query_type: str,
        predictions: Dict[str, int],
        confidences: Optional[Dict[str, float]] = None
    ) -> tuple[Dict[str, int], Dict[str, float]]:
        """
        쿼리 타입에 맞는 액션만 필터링
        
        Args:
            query_type: 쿼리 타입 (TOP, JOIN_HEAVY, CTE, AGGREGATE, SIMPLE, SUBQUERY, WINDOW)
            predictions: {model_name: action_id}
            confidences: {model_name: confidence} (optional)
        
        Returns:
            filtered_predictions: 필터링된 예측
            filtered_confidences: 필터링된 confidence
        """
        self.filter_stats['total_calls'] += 1
        
        if query_type not in self.filter_stats['filtered_by_type']:
            self.filter_stats['filtered_by_type'][query_type] = 0
        self.filter_stats['filtered_by_type'][query_type] += 1
        
        # 허용 액션 목록 가져오기
        allowed = self.allowed_actions.get(query_type, self.allowed_actions['DEFAULT'])
        
        # 특별 규칙 적용
        if query_type == 'TOP':
            allowed = self._apply_top_query_rules(predictions, allowed)
        
        # 필터링
        filtered_predictions = {}
        filtered_confidences = {} if confidences else None
        
        for model_name, action_id in predictions.items():
            if action_id in allowed:
                filtered_predictions[model_name] = action_id
                if confidences and model_name in confidences:
                    filtered_confidences[model_name] = confidences[model_name]
            else:
                # 허용되지 않은 액션 → NO_ACTION으로 대체
                filtered_predictions[model_name] = 18  # NO_ACTION
                if confidences and model_name in confidences:
                    # Confidence 감소 (강제 변경이므로)
                    filtered_confidences[model_name] = confidences[model_name] * 0.5
                
                # 통계
                if action_id not in self.filter_stats['actions_blocked']:
                    self.filter_stats['actions_blocked'][action_id] = 0
                self.filter_stats['actions_blocked'][action_id] += 1
                
                if self.verbose:
                    print(f"[Router] {model_name}: Action {action_id} blocked for {query_type}, replaced with NO_ACTION")
        
        return filtered_predictions, filtered_confidences if confidences else {}
    
    def _apply_top_query_rules(
        self,
        predictions: Dict[str, int],
        allowed: List[int]
    ) -> List[int]:
        """
        TOP 쿼리 특별 규칙 적용
        
        v1에서 TOP 쿼리 성능이 가장 낮았으므로 (Mean Speedup 0.93x),
        v2에서는 특별 처리합니다.
        """
        # LOOP_JOIN (action 4) 억제
        if self.top_query_rules['penalize_loop_join']:
            if 4 in allowed:
                allowed = [a for a in allowed if a != 4]
                if self.verbose:
                    print("[Router] TOP query: LOOP_JOIN blocked")
        
        # FAST 힌트 (14-17) 선호는 이미 allowed에 반영됨
        # NO_ACTION 선호는 voting 단계에서 처리
        
        return allowed
    
    def boost_no_action_for_top(
        self,
        query_type: str,
        predictions: Dict[str, int],
        confidences: Dict[str, float]
    ) -> Dict[str, float]:
        """
        TOP 쿼리에 대해 NO_ACTION confidence를 증폭
        
        Args:
            query_type: 쿼리 타입
            predictions: {model_name: action_id}
            confidences: {model_name: confidence}
        
        Returns:
            boosted_confidences: NO_ACTION이 증폭된 confidence
        """
        if query_type != 'TOP':
            return confidences
        
        if not self.top_query_rules['boost_no_action']:
            return confidences
        
        boosted = confidences.copy()
        
        for model_name, action_id in predictions.items():
            if action_id == 18:  # NO_ACTION
                # NO_ACTION의 confidence를 1.5배 증폭
                boosted[model_name] = min(confidences[model_name] * 1.5, 1.0)
                if self.verbose:
                    print(f"[Router] {model_name}: NO_ACTION confidence boosted for TOP query "
                          f"({confidences[model_name]:.3f} → {boosted[model_name]:.3f})")
        
        return boosted
    
    def get_query_type_from_sql(self, sql: str) -> str:
        """
        SQL 쿼리로부터 쿼리 타입 추론
        
        Args:
            sql: SQL 쿼리 문자열
        
        Returns:
            query_type: 추론된 쿼리 타입
        """
        sql_upper = sql.upper()
        
        # TOP 쿼리
        if 'TOP ' in sql_upper or 'LIMIT ' in sql_upper:
            return 'TOP'
        
        # CTE (Common Table Expression)
        if 'WITH ' in sql_upper and ' AS (' in sql_upper:
            return 'CTE'
        
        # JOIN_HEAVY (3개 이상 JOIN)
        join_count = sql_upper.count(' JOIN ')
        if join_count >= 3:
            return 'JOIN_HEAVY'
        
        # WINDOW 함수
        if any(func in sql_upper for func in ['ROW_NUMBER()', 'RANK()', 'DENSE_RANK()', 'OVER (']):
            return 'WINDOW'
        
        # AGGREGATE (GROUP BY)
        if 'GROUP BY' in sql_upper:
            return 'AGGREGATE'
        
        # SUBQUERY (서브쿼리)
        if sql_upper.count('SELECT') > 1 or 'EXISTS' in sql_upper:
            return 'SUBQUERY'
        
        # SIMPLE (단순 쿼리)
        if join_count == 0 and 'WHERE' not in sql_upper:
            return 'SIMPLE'
        
        # 기본값
        return 'DEFAULT'
    
    def get_stats(self) -> Dict:
        """필터링 통계 반환"""
        return self.filter_stats.copy()
    
    def reset_stats(self):
        """통계 초기화"""
        self.filter_stats = {
            'total_calls': 0,
            'filtered_by_type': {},
            'actions_blocked': {},
        }
    
    def print_stats(self):
        """필터링 통계 출력"""
        print("=" * 80)
        print("Query Type Router Statistics")
        print("=" * 80)
        print(f"Total filter calls: {self.filter_stats['total_calls']}")
        
        print("\nFiltering by Query Type:")
        for qtype, count in sorted(self.filter_stats['filtered_by_type'].items()):
            pct = count / self.filter_stats['total_calls'] * 100
            print(f"  {qtype}: {count} ({pct:.1f}%)")
        
        print("\nActions Blocked:")
        for action_id, count in sorted(self.filter_stats['actions_blocked'].items()):
            print(f"  Action {action_id}: {count} times")
        print("=" * 80)


# Test code
if __name__ == '__main__':
    print("=" * 80)
    print("Testing Query Type Router")
    print("=" * 80)
    
    router = QueryTypeRouter(verbose=True)
    
    # Test 1: TOP 쿼리 (LOOP_JOIN 차단)
    print("\n[Test 1] TOP Query - LOOP_JOIN should be blocked")
    predictions = {
        'dqn_v4': 4,   # LOOP_JOIN (should be blocked)
        'ppo_v3': 14,  # FAST_10 (should be allowed)
        'ddpg_v1': 3,  # HASH_JOIN (should be blocked for TOP)
        'sac_v1': 18,  # NO_ACTION (should be allowed)
    }
    confidences = {
        'dqn_v4': 0.8,
        'ppo_v3': 0.7,
        'ddpg_v1': 0.6,
        'sac_v1': 0.5,
    }
    
    filtered_pred, filtered_conf = router.filter_actions_for_query('TOP', predictions, confidences)
    print(f"Original: {predictions}")
    print(f"Filtered: {filtered_pred}")
    
    # Boost NO_ACTION for TOP
    boosted_conf = router.boost_no_action_for_top('TOP', filtered_pred, filtered_conf)
    print(f"Original confidences: {filtered_conf}")
    print(f"Boosted confidences: {boosted_conf}")
    
    # Test 2: JOIN_HEAVY 쿼리
    print("\n[Test 2] JOIN_HEAVY Query - Only JOIN hints allowed")
    predictions = {
        'dqn_v4': 3,   # HASH_JOIN (should be allowed)
        'ppo_v3': 14,  # FAST_10 (should be blocked)
        'ddpg_v1': 4,  # LOOP_JOIN (should be allowed)
        'sac_v1': 0,   # MAXDOP (should be blocked)
    }
    
    filtered_pred, _ = router.filter_actions_for_query('JOIN_HEAVY', predictions)
    print(f"Original: {predictions}")
    print(f"Filtered: {filtered_pred}")
    
    # Test 3: SIMPLE 쿼리 (모든 액션 → NO_ACTION)
    print("\n[Test 3] SIMPLE Query - All actions → NO_ACTION")
    predictions = {
        'dqn_v4': 3,   # HASH_JOIN (should be blocked)
        'ppo_v3': 14,  # FAST_10 (should be blocked)
        'ddpg_v1': 4,  # LOOP_JOIN (should be blocked)
        'sac_v1': 0,   # MAXDOP (should be blocked)
    }
    
    filtered_pred, _ = router.filter_actions_for_query('SIMPLE', predictions)
    print(f"Original: {predictions}")
    print(f"Filtered: {filtered_pred}")
    
    # Test 4: SQL 쿼리 타입 추론
    print("\n[Test 4] Query Type Inference")
    test_queries = [
        ("SELECT TOP 100 * FROM orders", "TOP"),
        ("WITH cte AS (SELECT * FROM t) SELECT * FROM cte", "CTE"),
        ("SELECT * FROM a JOIN b ON a.id=b.id JOIN c ON b.id=c.id JOIN d ON c.id=d.id", "JOIN_HEAVY"),
        ("SELECT COUNT(*) FROM orders GROUP BY customer_id", "AGGREGATE"),
    ]
    
    for sql, expected in test_queries:
        inferred = router.get_query_type_from_sql(sql)
        status = "✓" if inferred == expected else "✗"
        print(f"  {status} {expected}: {inferred}")
    
    # Print statistics
    print()
    router.print_stats()
    
    print("\n[SUCCESS] Router test completed!")

