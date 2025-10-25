# -*- coding: utf-8 -*-
"""
DDPG v1: Continuous Action Decoder

연속 action vector [0~1]^7을 실제 SQL 쿼리 힌트로 변환합니다.
"""

import json
import os
import numpy as np
from typing import Dict, Any


class ContinuousActionDecoder:
    """
    7차원 continuous action space를 discrete SQL hints로 변환
    
    Action Vector [0~1]^7:
    [0] MAXDOP: 1~10
    [1] FAST: 0, 10, 20, ..., 100
    [2] ISOLATION: default, READ_COMMITTED, READ_UNCOMMITTED, SNAPSHOT
    [3] JOIN_HINT: none, hash, merge, loop, force_order
    [4] OPTIMIZER_HINT: 10가지 고급 힌트
    [5] COMPATIBILITY: COMPAT_130~160
    [6] USE_RECOMPILE: 0 or 1
    """
    
    def __init__(self, config_path: str = None):
        """
        Args:
            config_path: v1_continuous_action_config.json 경로
                        None이면 기본 경로 사용
        """
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            apollo_ml_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
            config_path = os.path.join(
                apollo_ml_dir, 
                'artifacts', 
                'RLQO', 
                'configs', 
                'v1_continuous_action_config.json'
            )
        
        # Load config
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.action_ranges = self.config['action_ranges']
        self.action_dim = self.config['action_dim']
    
    def decode(self, action_vector: np.ndarray) -> Dict[str, Any]:
        """
        Continuous action vector를 discrete hints로 변환
        
        Args:
            action_vector: [0~1]^7 범위의 연속값
        
        Returns:
            hints: {
                'maxdop': int,
                'fast_n': int,
                'isolation': str,
                'join_hint': str,
                'optimizer_hint': str,
                'compatibility': str,
                'use_recompile': bool
            }
        """
        # Clip to [0, 1] range
        action_vector = np.clip(action_vector, 0.0, 1.0)
        
        hints = {}
        
        # [0] MAXDOP: 1~10
        maxdop_config = self.action_ranges['maxdop']
        min_val = maxdop_config['min']
        max_val = maxdop_config['max']
        hints['maxdop'] = int(action_vector[0] * (max_val - min_val)) + min_val
        
        # [1] FAST: 0, 10, 20, ..., 100
        fast_values = self.action_ranges['fast_n']['values']
        fast_idx = int(action_vector[1] * len(fast_values))
        fast_idx = min(fast_idx, len(fast_values) - 1)  # Clip to valid index
        hints['fast_n'] = fast_values[fast_idx]
        
        # [2] ISOLATION: 4 levels
        isolation_values = self.action_ranges['isolation']['values']
        isolation_idx = int(action_vector[2] * len(isolation_values))
        isolation_idx = min(isolation_idx, len(isolation_values) - 1)
        hints['isolation'] = isolation_values[isolation_idx]
        
        # [3] JOIN_HINT: 5 types
        join_values = self.action_ranges['join_hint']['values']
        join_idx = int(action_vector[3] * len(join_values))
        join_idx = min(join_idx, len(join_values) - 1)
        hints['join_hint'] = join_values[join_idx]
        
        # [4] OPTIMIZER_HINT: 11 types
        optimizer_values = self.action_ranges['optimizer_hint']['values']
        optimizer_idx = int(action_vector[4] * len(optimizer_values))
        optimizer_idx = min(optimizer_idx, len(optimizer_values) - 1)
        hints['optimizer_hint'] = optimizer_values[optimizer_idx]
        
        # [5] COMPATIBILITY: 4 levels
        compat_values = self.action_ranges['compatibility']['values']
        compat_idx = int(action_vector[5] * len(compat_values))
        compat_idx = min(compat_idx, len(compat_values) - 1)
        hints['compatibility'] = compat_values[compat_idx]
        
        # [6] USE_RECOMPILE: binary (threshold at 0.5)
        hints['use_recompile'] = bool(action_vector[6] >= 0.5)
        
        return hints
    
    def encode_hints_to_action(self, hints: Dict[str, Any]) -> np.ndarray:
        """
        역변환: Discrete hints를 continuous action vector로 변환
        (평가 시 참고용)
        
        Args:
            hints: decode()가 반환하는 형식의 dict
        
        Returns:
            action_vector: [0~1]^7
        """
        action = np.zeros(7, dtype=np.float32)
        
        # [0] MAXDOP
        maxdop = hints.get('maxdop', 1)
        min_val = self.action_ranges['maxdop']['min']
        max_val = self.action_ranges['maxdop']['max']
        action[0] = (maxdop - min_val) / (max_val - min_val)
        
        # [1] FAST
        fast_n = hints.get('fast_n', 0)
        fast_values = self.action_ranges['fast_n']['values']
        if fast_n in fast_values:
            action[1] = fast_values.index(fast_n) / len(fast_values)
        else:
            action[1] = 0.0
        
        # [2] ISOLATION
        isolation = hints.get('isolation', 'default')
        isolation_values = self.action_ranges['isolation']['values']
        if isolation in isolation_values:
            action[2] = isolation_values.index(isolation) / len(isolation_values)
        else:
            action[2] = 0.0
        
        # [3] JOIN_HINT
        join_hint = hints.get('join_hint', 'none')
        join_values = self.action_ranges['join_hint']['values']
        if join_hint in join_values:
            action[3] = join_values.index(join_hint) / len(join_values)
        else:
            action[3] = 0.0
        
        # [4] OPTIMIZER_HINT
        optimizer_hint = hints.get('optimizer_hint', 'NONE')
        optimizer_values = self.action_ranges['optimizer_hint']['values']
        if optimizer_hint in optimizer_values:
            action[4] = optimizer_values.index(optimizer_hint) / len(optimizer_values)
        else:
            action[4] = 0.0
        
        # [5] COMPATIBILITY
        compatibility = hints.get('compatibility', 'COMPAT_140')
        compat_values = self.action_ranges['compatibility']['values']
        if compatibility in compat_values:
            action[5] = compat_values.index(compatibility) / len(compat_values)
        else:
            action[5] = 0.25  # COMPAT_140 default
        
        # [6] USE_RECOMPILE
        use_recompile = hints.get('use_recompile', False)
        action[6] = 1.0 if use_recompile else 0.0
        
        return action
    
    def get_action_description(self, action_vector: np.ndarray) -> str:
        """
        Action vector를 사람이 읽을 수 있는 문자열로 변환
        
        Args:
            action_vector: [0~1]^7
        
        Returns:
            description: 예) "MAXDOP=4, FAST=50, ISOLATION=READ_UNCOMMITTED, ..."
        """
        hints = self.decode(action_vector)
        
        parts = []
        parts.append(f"MAXDOP={hints['maxdop']}")
        
        if hints['fast_n'] > 0:
            parts.append(f"FAST={hints['fast_n']}")
        
        if hints['isolation'] != 'default':
            parts.append(f"ISOLATION={hints['isolation']}")
        
        if hints['join_hint'] != 'none':
            parts.append(f"JOIN={hints['join_hint'].upper()}")
        
        if hints['optimizer_hint'] != 'NONE':
            parts.append(f"OPT={hints['optimizer_hint']}")
        
        if hints['compatibility'] != 'COMPAT_140':
            parts.append(f"{hints['compatibility']}")
        
        if hints['use_recompile']:
            parts.append("RECOMPILE")
        
        return ", ".join(parts) if parts else "NO_HINTS"


# Test code
if __name__ == '__main__':
    decoder = ContinuousActionDecoder()
    
    # Test 1: Random action
    print("=" * 80)
    print("Test 1: Random Action")
    print("=" * 80)
    test_action = np.random.rand(7)
    print(f"Action vector: {test_action}")
    hints = decoder.decode(test_action)
    print(f"Decoded hints: {hints}")
    print(f"Description: {decoder.get_action_description(test_action)}")
    
    # Test 2: Edge cases
    print("\n" + "=" * 80)
    print("Test 2: Edge Cases")
    print("=" * 80)
    
    # All zeros
    action_zeros = np.zeros(7)
    print(f"\nAll zeros: {decoder.decode(action_zeros)}")
    print(f"Description: {decoder.get_action_description(action_zeros)}")
    
    # All ones
    action_ones = np.ones(7)
    print(f"\nAll ones: {decoder.decode(action_ones)}")
    print(f"Description: {decoder.get_action_description(action_ones)}")
    
    # Test 3: Roundtrip
    print("\n" + "=" * 80)
    print("Test 3: Roundtrip (encode -> decode)")
    print("=" * 80)
    original_hints = {
        'maxdop': 4,
        'fast_n': 50,
        'isolation': 'READ_UNCOMMITTED',
        'join_hint': 'hash',
        'optimizer_hint': 'FORCESEEK',
        'compatibility': 'COMPAT_150',
        'use_recompile': True
    }
    print(f"Original hints: {original_hints}")
    action_encoded = decoder.encode_hints_to_action(original_hints)
    print(f"Encoded action: {action_encoded}")
    hints_decoded = decoder.decode(action_encoded)
    print(f"Decoded hints: {hints_decoded}")
    print(f"Match: {original_hints == hints_decoded}")

