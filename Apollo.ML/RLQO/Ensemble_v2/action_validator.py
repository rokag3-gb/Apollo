# -*- coding: utf-8 -*-
"""
Ensemble v2: Action Validator

액션의 안전성을 검증하고 부적합한 액션을 필터링합니다.
과거 실패 패턴을 학습하여 동일한 실패를 반복하지 않습니다.
"""

from typing import Dict, Optional, Tuple
import json
import os


class ActionValidator:
    """
    액션 검증 및 안전성 체크
    
    주요 기능:
    1. 쿼리 특성 기반 액션 검증 (Baseline, Query Type)
    2. 과거 실패 패턴 추적 및 회피
    3. 위험한 액션 조합 차단
    """
    
    def __init__(
        self,
        min_baseline_for_maxdop: float = 10.0,
        failure_rate_threshold: float = 0.5,
        enable_failure_tracking: bool = True,
        verbose: bool = False
    ):
        """
        Args:
            min_baseline_for_maxdop: MAXDOP를 적용할 최소 baseline (ms)
            failure_rate_threshold: 액션을 차단할 실패율 임계값
            enable_failure_tracking: 실패 패턴 추적 활성화
            verbose: 검증 과정 로깅 여부
        """
        self.min_baseline_for_maxdop = min_baseline_for_maxdop
        self.failure_rate_threshold = failure_rate_threshold
        self.enable_failure_tracking = enable_failure_tracking
        self.verbose = verbose
        
        # 과거 실패 패턴 추적
        # (query_type, action_id) → {'total': int, 'failures': int, 'failure_rate': float}
        self.failure_history = {}
        
        # 통계
        self.validation_stats = {
            'total_validations': 0,
            'actions_rejected': 0,
            'rejection_reasons': {},  # reason -> count
        }
    
    def is_safe_action(
        self,
        action_id: int,
        query_info: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        액션이 안전한지 검증
        
        Args:
            action_id: 액션 ID (0~18)
            query_info: 쿼리 정보 {'type': str, 'baseline_ms': float, ...}
        
        Returns:
            is_safe: 안전 여부
            reason: 불안전한 경우 이유 (안전하면 None)
        """
        self.validation_stats['total_validations'] += 1
        
        query_type = query_info.get('type', 'UNKNOWN')
        baseline_ms = query_info.get('baseline_ms', 0)
        
        # 규칙 1: Baseline < min_baseline → MAXDOP 계열 제외
        if baseline_ms < self.min_baseline_for_maxdop and action_id in [0, 1, 2]:
            reason = f"Baseline too fast ({baseline_ms:.1f}ms) for MAXDOP"
            self._record_rejection(reason)
            return False, reason
        
        # 규칙 2: TOP 쿼리 → LOOP_JOIN 제외
        if query_type == 'TOP' and action_id == 4:
            reason = "LOOP_JOIN not recommended for TOP queries"
            self._record_rejection(reason)
            return False, reason
        
        # 규칙 3: SIMPLE 쿼리 → NO_ACTION만 허용
        if query_type == 'SIMPLE' and action_id != 18:
            reason = "Only NO_ACTION allowed for SIMPLE queries"
            self._record_rejection(reason)
            return False, reason
        
        # 규칙 4: 과거 실패율 > threshold → 제외
        if self.enable_failure_tracking:
            key = (query_type, action_id)
            if key in self.failure_history:
                failure_rate = self.failure_history[key]['failure_rate']
                if failure_rate > self.failure_rate_threshold:
                    reason = f"High failure rate ({failure_rate:.1%}) for {query_type} + Action {action_id}"
                    self._record_rejection(reason)
                    return False, reason
        
        # 안전함
        return True, None
    
    def filter_unsafe_actions(
        self,
        predictions: Dict[str, int],
        confidences: Dict[str, float],
        query_info: Dict
    ) -> Tuple[Dict[str, int], Dict[str, float]]:
        """
        불안전한 액션을 필터링
        
        Args:
            predictions: {model_name: action_id}
            confidences: {model_name: confidence}
            query_info: 쿼리 정보
        
        Returns:
            filtered_predictions: 필터링된 예측
            filtered_confidences: 필터링된 confidence
        """
        filtered_predictions = {}
        filtered_confidences = {}
        
        for model_name, action_id in predictions.items():
            is_safe, reason = self.is_safe_action(action_id, query_info)
            
            if is_safe:
                filtered_predictions[model_name] = action_id
                filtered_confidences[model_name] = confidences[model_name]
            else:
                # 불안전한 액션 → NO_ACTION으로 대체
                filtered_predictions[model_name] = 18  # NO_ACTION
                filtered_confidences[model_name] = confidences[model_name] * 0.3  # Confidence 크게 감소
                
                if self.verbose:
                    print(f"[Validator] {model_name}: Action {action_id} rejected ({reason}), "
                          f"replaced with NO_ACTION")
        
        return filtered_predictions, filtered_confidences
    
    def record_action_result(
        self,
        query_type: str,
        action_id: int,
        speedup: float
    ):
        """
        액션 실행 결과를 기록하여 실패 패턴 학습
        
        Args:
            query_type: 쿼리 타입
            action_id: 액션 ID
            speedup: 성능 향상률 (< 0.9이면 실패로 간주)
        """
        if not self.enable_failure_tracking:
            return
        
        key = (query_type, action_id)
        
        if key not in self.failure_history:
            self.failure_history[key] = {
                'total': 0,
                'failures': 0,
                'failure_rate': 0.0
            }
        
        # 기록 업데이트
        self.failure_history[key]['total'] += 1
        
        if speedup < 0.9:  # 10% 이상 성능 저하 = 실패
            self.failure_history[key]['failures'] += 1
        
        # 실패율 계산
        total = self.failure_history[key]['total']
        failures = self.failure_history[key]['failures']
        self.failure_history[key]['failure_rate'] = failures / total if total > 0 else 0.0
    
    def _record_rejection(self, reason: str):
        """거부 사유 통계 업데이트"""
        self.validation_stats['actions_rejected'] += 1
        
        if reason not in self.validation_stats['rejection_reasons']:
            self.validation_stats['rejection_reasons'][reason] = 0
        self.validation_stats['rejection_reasons'][reason] += 1
    
    def get_failure_history(self) -> Dict:
        """실패 이력 반환"""
        return self.failure_history.copy()
    
    def save_failure_history(self, filepath: str):
        """실패 이력을 파일로 저장"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.failure_history, f, indent=2)
        
        if self.verbose:
            print(f"[Validator] Failure history saved to {filepath}")
    
    def load_failure_history(self, filepath: str):
        """파일에서 실패 이력 로드"""
        if not os.path.exists(filepath):
            if self.verbose:
                print(f"[Validator] No failure history found at {filepath}")
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        # JSON key는 string이므로 tuple로 변환
        self.failure_history = {}
        for key_str, value in loaded.items():
            # key_str: "['TOP', 4]" 형식
            key = eval(key_str)  # tuple로 변환
            self.failure_history[key] = value
        
        if self.verbose:
            print(f"[Validator] Failure history loaded from {filepath} ({len(self.failure_history)} entries)")
    
    def get_stats(self) -> Dict:
        """검증 통계 반환"""
        return self.validation_stats.copy()
    
    def reset_stats(self):
        """통계 초기화"""
        self.validation_stats = {
            'total_validations': 0,
            'actions_rejected': 0,
            'rejection_reasons': {},
        }
    
    def print_stats(self):
        """검증 통계 출력"""
        print("=" * 80)
        print("Action Validator Statistics")
        print("=" * 80)
        print(f"Total validations: {self.validation_stats['total_validations']}")
        print(f"Actions rejected: {self.validation_stats['actions_rejected']}")
        
        if self.validation_stats['actions_rejected'] > 0:
            reject_rate = self.validation_stats['actions_rejected'] / self.validation_stats['total_validations'] * 100
            print(f"Rejection rate: {reject_rate:.1f}%")
        
        if self.validation_stats['rejection_reasons']:
            print("\nRejection Reasons:")
            for reason, count in sorted(
                self.validation_stats['rejection_reasons'].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                print(f"  {reason}: {count}")
        
        if self.failure_history:
            print(f"\nFailure History: {len(self.failure_history)} patterns tracked")
            
            # 실패율이 높은 패턴 출력
            high_failure = [(k, v) for k, v in self.failure_history.items() 
                           if v['failure_rate'] > self.failure_rate_threshold]
            
            if high_failure:
                print(f"\nHigh-Failure Patterns (> {self.failure_rate_threshold:.0%}):")
                for (qtype, action_id), stats in sorted(high_failure, key=lambda x: x[1]['failure_rate'], reverse=True)[:5]:
                    print(f"  {qtype} + Action {action_id}: {stats['failure_rate']:.1%} "
                          f"({stats['failures']}/{stats['total']})")
        
        print("=" * 80)


# Test code
if __name__ == '__main__':
    print("=" * 80)
    print("Testing Action Validator")
    print("=" * 80)
    
    validator = ActionValidator(verbose=True)
    
    # Test 1: Baseline 체크
    print("\n[Test 1] Baseline Check - MAXDOP on fast query")
    query_info = {'type': 'SIMPLE', 'baseline_ms': 5.0}
    is_safe, reason = validator.is_safe_action(action_id=0, query_info=query_info)  # MAXDOP_1
    print(f"  Result: {'Safe' if is_safe else 'Unsafe'}")
    if reason:
        print(f"  Reason: {reason}")
    
    # Test 2: TOP 쿼리 + LOOP_JOIN
    print("\n[Test 2] TOP Query + LOOP_JOIN")
    query_info = {'type': 'TOP', 'baseline_ms': 100.0}
    is_safe, reason = validator.is_safe_action(action_id=4, query_info=query_info)  # LOOP_JOIN
    print(f"  Result: {'Safe' if is_safe else 'Unsafe'}")
    if reason:
        print(f"  Reason: {reason}")
    
    # Test 3: 실패 패턴 학습
    print("\n[Test 3] Failure Pattern Learning")
    validator.record_action_result('TOP', 4, speedup=0.3)  # 실패
    validator.record_action_result('TOP', 4, speedup=0.5)  # 실패
    validator.record_action_result('TOP', 4, speedup=0.8)  # 실패
    validator.record_action_result('TOP', 4, speedup=1.2)  # 성공
    
    # 이제 TOP + LOOP_JOIN은 실패율 75%로 차단되어야 함
    query_info = {'type': 'TOP', 'baseline_ms': 100.0}
    is_safe, reason = validator.is_safe_action(action_id=4, query_info=query_info)
    print(f"  After learning: {'Safe' if is_safe else 'Unsafe'}")
    if reason:
        print(f"  Reason: {reason}")
    
    # Test 4: 필터링
    print("\n[Test 4] Filtering Unsafe Actions")
    predictions = {
        'dqn_v4': 0,   # MAXDOP_1 (unsafe for fast query)
        'ppo_v3': 14,  # FAST_10 (safe)
        'ddpg_v1': 4,  # LOOP_JOIN (unsafe for TOP)
        'sac_v1': 18,  # NO_ACTION (safe)
    }
    confidences = {
        'dqn_v4': 0.8,
        'ppo_v3': 0.7,
        'ddpg_v1': 0.6,
        'sac_v1': 0.5,
    }
    query_info = {'type': 'TOP', 'baseline_ms': 5.0}
    
    filtered_pred, filtered_conf = validator.filter_unsafe_actions(predictions, confidences, query_info)
    print(f"  Original: {predictions}")
    print(f"  Filtered: {filtered_pred}")
    print(f"  Confidences: {confidences}")
    print(f"  Filtered conf: {filtered_conf}")
    
    # Print statistics
    print()
    validator.print_stats()
    
    print("\n[SUCCESS] Validator test completed!")

