# -*- coding: utf-8 -*-
"""
Ensemble v2: Continuous-to-Discrete Action Converter

DDPG v1, SAC v1의 continuous action space [0~1]^7을
DQN v4의 discrete action ID (0~18)로 변환합니다.

이는 Ensemble v1에서 DDPG/SAC가 NO_ACTION만 예측하던 문제를 해결합니다.
"""

import os
import sys
import numpy as np
from typing import Dict, Any

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
rlqo_dir = os.path.abspath(os.path.join(current_dir, '..'))
apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, apollo_ml_dir)
sys.path.insert(0, rlqo_dir)

from RLQO.DDPG_v1.config.action_decoder import ContinuousActionDecoder


class ContinuousToDiscreteConverter:
    """
    DDPG/SAC의 continuous action을 DQN v4 discrete action으로 변환
    
    DDPG/SAC Action [0~1]^7:
      [0] MAXDOP: 1~10
      [1] FAST: 0, 10, 20, ..., 100
      [2] ISOLATION: 4 levels (default, READ_COMMITTED, READ_UNCOMMITTED, SNAPSHOT)
      [3] JOIN_HINT: none, hash, merge, loop, force_order
      [4] OPTIMIZER_HINT: 11 types (NONE, FORCESEEK, FORCESCAN, ...)
      [5] COMPATIBILITY: COMPAT_130~160
      [6] USE_RECOMPILE: binary
    
    DQN v4 Discrete Actions (19개):
      0: SET_MAXDOP_1, 1: SET_MAXDOP_4, 2: SET_MAXDOP_8
      3: USE_HASH_JOIN, 4: USE_LOOP_JOIN, 5: USE_MERGE_JOIN
      6: FORCE_JOIN_ORDER, 7: OPTIMIZE_FOR_UNKNOWN
      8: DISABLE_PARAMETER_SNIFFING, 9-11: COMPAT_LEVEL_140/150/160
      12: USE_NOLOCK, 13: RECOMPILE
      14-17: FAST_10/50/100/200, 18: NO_ACTION
    """
    
    def __init__(self, config_path: str = None, verbose: bool = False):
        """
        Args:
            config_path: v1_continuous_action_config.json 경로
            verbose: 변환 과정 로깅 여부
        """
        self.decoder = ContinuousActionDecoder(config_path)
        self.verbose = verbose
        
        # 우선순위: 영향력이 큰 힌트 순서
        self.hint_priority = [
            'join_hint',      # 1순위: 가장 중요 (JOIN 알고리즘)
            'fast_n',         # 2순위: TOP 쿼리에 효과적
            'maxdop',         # 3순위: 병렬 처리 제어
            'use_recompile',  # 4순위: 재컴파일
            'optimizer_hint', # 5순위: 최적화 힌트
            'compatibility',  # 6순위: 호환성 레벨
            'isolation'       # 7순위: 격리 수준 (덜 중요)
        ]
        
        # 통계: 변환 결과 추적
        self.conversion_stats = {
            'total': 0,
            'by_action': {},  # action_id -> count
            'by_priority': {}  # priority_level -> count
        }
    
    def convert(self, continuous_action: np.ndarray) -> int:
        """
        Continuous action을 discrete action ID로 변환
        
        Args:
            continuous_action: [0~1]^7 범위의 연속값
        
        Returns:
            discrete_action_id: 0~18 범위의 discrete action ID
        """
        # 1. Continuous → Hints 디코딩
        hints = self.decoder.decode(continuous_action)
        
        if self.verbose:
            print(f"[Converter] Hints decoded: {hints}")
        
        # 2. 우선순위대로 힌트 검사 및 매핑
        discrete_action = self._map_hints_to_action(hints)
        
        # 3. 통계 업데이트
        self.conversion_stats['total'] += 1
        if discrete_action not in self.conversion_stats['by_action']:
            self.conversion_stats['by_action'][discrete_action] = 0
        self.conversion_stats['by_action'][discrete_action] += 1
        
        if self.verbose:
            print(f"[Converter] Converted to action ID: {discrete_action}")
        
        return discrete_action
    
    def _map_hints_to_action(self, hints: Dict[str, Any]) -> int:
        """
        Hints 딕셔너리를 discrete action ID로 매핑
        
        우선순위 기반 매핑:
        1. JOIN HINT (가장 중요)
        2. FAST N (TOP 쿼리용)
        3. MAXDOP
        4. RECOMPILE
        5. OPTIMIZER HINT
        6. COMPATIBILITY
        7. ISOLATION
        """
        
        # [우선순위 1] JOIN HINT (가장 중요)
        if hints['join_hint'] != 'none':
            join_map = {
                'hash': 3,         # USE_HASH_JOIN
                'loop': 4,         # USE_LOOP_JOIN
                'merge': 5,        # USE_MERGE_JOIN
                'force_order': 6   # FORCE_JOIN_ORDER
            }
            if hints['join_hint'] in join_map:
                self._update_priority_stats('join_hint')
                return join_map[hints['join_hint']]
        
        # [우선순위 2] FAST N (TOP 쿼리용)
        if hints['fast_n'] > 0:
            # FAST 값을 가장 가까운 discrete action으로 매핑
            if hints['fast_n'] <= 25:
                action_id = 14  # FAST_10
            elif hints['fast_n'] <= 75:
                action_id = 15  # FAST_50
            elif hints['fast_n'] <= 150:
                action_id = 16  # FAST_100
            else:
                action_id = 17  # FAST_200
            
            self._update_priority_stats('fast_n')
            return action_id
        
        # [우선순위 3] MAXDOP
        # DDPG/SAC는 1~10 범위이므로, 이를 3개 discrete action으로 매핑
        if hints['maxdop'] <= 1:
            self._update_priority_stats('maxdop')
            return 0  # SET_MAXDOP_1
        elif hints['maxdop'] <= 4:
            self._update_priority_stats('maxdop')
            return 1  # SET_MAXDOP_4
        elif hints['maxdop'] >= 8:
            self._update_priority_stats('maxdop')
            return 2  # SET_MAXDOP_8
        
        # [우선순위 4] RECOMPILE
        if hints['use_recompile']:
            self._update_priority_stats('use_recompile')
            return 13  # RECOMPILE
        
        # [우선순위 5] OPTIMIZER HINT
        if hints['optimizer_hint'] not in ['NONE', None]:
            opt_map = {
                'OPTIMIZE_FOR_UNKNOWN': 7,
                'DISABLE_PARAMETER_SNIFFING': 8,
            }
            if hints['optimizer_hint'] in opt_map:
                self._update_priority_stats('optimizer_hint')
                return opt_map[hints['optimizer_hint']]
        
        # [우선순위 6] COMPATIBILITY LEVEL
        if hints['compatibility'] != 'COMPAT_140':
            compat_map = {
                'COMPAT_140': 9,
                'COMPAT_150': 10,
                'COMPAT_160': 11,
            }
            if hints['compatibility'] in compat_map:
                self._update_priority_stats('compatibility')
                return compat_map[hints['compatibility']]
        
        # [우선순위 7] ISOLATION (NOLOCK)
        if hints['isolation'] == 'READ_UNCOMMITTED':
            self._update_priority_stats('isolation')
            return 12  # USE_NOLOCK
        
        # 기본값: NO_ACTION
        self._update_priority_stats('no_action')
        return 18  # NO_ACTION
    
    def _update_priority_stats(self, priority: str):
        """우선순위별 통계 업데이트"""
        if priority not in self.conversion_stats['by_priority']:
            self.conversion_stats['by_priority'][priority] = 0
        self.conversion_stats['by_priority'][priority] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """변환 통계 반환"""
        return self.conversion_stats.copy()
    
    def reset_stats(self):
        """통계 초기화"""
        self.conversion_stats = {
            'total': 0,
            'by_action': {},
            'by_priority': {}
        }
    
    def print_stats(self):
        """변환 통계 출력"""
        print("=" * 80)
        print("Continuous-to-Discrete Conversion Statistics")
        print("=" * 80)
        print(f"Total conversions: {self.conversion_stats['total']}")
        
        print("\nBy Action ID:")
        for action_id in sorted(self.conversion_stats['by_action'].keys()):
            count = self.conversion_stats['by_action'][action_id]
            pct = count / self.conversion_stats['total'] * 100
            print(f"  Action {action_id}: {count} ({pct:.1f}%)")
        
        print("\nBy Priority:")
        for priority in sorted(self.conversion_stats['by_priority'].keys()):
            count = self.conversion_stats['by_priority'][priority]
            pct = count / self.conversion_stats['total'] * 100
            print(f"  {priority}: {count} ({pct:.1f}%)")
        print("=" * 80)


# Test code
if __name__ == '__main__':
    print("=" * 80)
    print("Testing Continuous-to-Discrete Converter")
    print("=" * 80)
    
    converter = ContinuousToDiscreteConverter(verbose=True)
    
    # Test 1: JOIN HINT (should map to action 3, 4, 5, 6)
    print("\n[Test 1] JOIN HINT")
    test_actions = [
        np.array([0.5, 0.0, 0.0, 0.2, 0.0, 0.0, 0.0]),  # hash join
        np.array([0.5, 0.0, 0.0, 0.6, 0.0, 0.0, 0.0]),  # loop join
        np.array([0.5, 0.0, 0.0, 0.4, 0.0, 0.0, 0.0]),  # merge join
    ]
    for action in test_actions:
        discrete = converter.convert(action)
        print(f"  Converted to: {discrete}")
    
    # Test 2: FAST N (should map to action 14, 15, 16, 17)
    print("\n[Test 2] FAST N")
    test_actions = [
        np.array([0.5, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0]),  # FAST 10
        np.array([0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0]),  # FAST 50
        np.array([0.5, 0.9, 0.0, 0.0, 0.0, 0.0, 0.0]),  # FAST 90
    ]
    for action in test_actions:
        discrete = converter.convert(action)
        print(f"  Converted to: {discrete}")
    
    # Test 3: MAXDOP (should map to action 0, 1, 2)
    print("\n[Test 3] MAXDOP")
    test_actions = [
        np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),  # MAXDOP 1
        np.array([0.4, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),  # MAXDOP 4
        np.array([0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),  # MAXDOP 9
    ]
    for action in test_actions:
        discrete = converter.convert(action)
        print(f"  Converted to: {discrete}")
    
    # Test 4: NO_ACTION (should map to action 18)
    print("\n[Test 4] NO_ACTION")
    test_action = np.array([0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # default, no hints
    discrete = converter.convert(test_action)
    print(f"  Converted to: {discrete}")
    
    # Print statistics
    print()
    converter.print_stats()
    
    print("\n[SUCCESS] Converter test completed!")

