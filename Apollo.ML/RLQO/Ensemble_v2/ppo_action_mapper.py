# -*- coding: utf-8 -*-
"""
Ensemble v2: PPO Action Mapper

PPO v3의 44개 액션을 DQN v4의 19개 액션으로 매핑합니다.
이는 Ensemble 투표 시점에만 사용되며, PPO 모델 자체는 수정하지 않습니다.

매핑 원칙:
1. FAST, MAXDOP, JOIN hints는 의미상 가장 가까운 값으로 매핑
2. DQN에 없는 액션(ISOLATION, 고급 힌트)은 NO_ACTION(18)로 매핑
3. 안전성 우선: 애매한 경우 보수적으로 매핑
"""

from collections import defaultdict
from typing import Dict


class PPOToDQNActionMapper:
    """
    PPO v3 (44 actions) → DQN v4 (19 actions) 매핑
    
    DQN v4 액션 구성 (19개):
    0-2: MAXDOP (1, 4, 8)
    3-6: JOIN hints (HASH, LOOP, MERGE, FORCE_ORDER)
    7-13: 기타 힌트 (OPTIMIZE_FOR_UNKNOWN, DISABLE_PARAM_SNIFF, COMPAT levels, RECOMPILE)
    14-17: FAST (10, 50, 100, 200)
    18: NO_ACTION
    
    PPO v3 액션 구성 (44개):
    0-9: FAST (10, 20, 30, ..., 100)
    10-19: MAXDOP (1, 2, 3, ..., 10)
    20-22: ISOLATION (READ_COMMITTED, READ_UNCOMMITTED, SNAPSHOT)
    23-26: JOIN hints (HASH, LOOP, MERGE, FORCE_ORDER)
    27-42: 고급 DBA 힌트
    43: NO_ACTION
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.mapping_stats = {
            'total': 0,
            'by_ppo_action': defaultdict(int),
            'by_dqn_action': defaultdict(int),
            'by_category': defaultdict(int)
        }
        
        # PPO → DQN 매핑 테이블
        self.MAPPING = self._create_mapping()
        
        # 역방향 참조용 (디버깅)
        self.PPO_ACTION_NAMES = self._get_ppo_action_names()
        self.DQN_ACTION_NAMES = self._get_dqn_action_names()
    
    def _create_mapping(self) -> Dict[int, int]:
        """매핑 테이블 생성"""
        mapping = {}
        
        # ==========================================
        # FAST 매핑 (PPO 0-9 → DQN 14-17)
        # ==========================================
        # 안전성 우선: 가장 가까운 작은 값으로 매핑
        mapping[0] = 14   # FAST_10 → FAST_10 ✓
        mapping[1] = 14   # FAST_20 → FAST_10 (보수적)
        mapping[2] = 14   # FAST_30 → FAST_10 (보수적)
        mapping[3] = 15   # FAST_40 → FAST_50
        mapping[4] = 15   # FAST_50 → FAST_50 ✓
        mapping[5] = 15   # FAST_60 → FAST_50
        mapping[6] = 16   # FAST_70 → FAST_100
        mapping[7] = 16   # FAST_80 → FAST_100
        mapping[8] = 16   # FAST_90 → FAST_100
        mapping[9] = 16   # FAST_100 → FAST_100 ✓
        
        # ==========================================
        # MAXDOP 매핑 (PPO 10-19 → DQN 0-2)
        # ==========================================
        # 가장 가까운 값으로 매핑 (1, 4, 8)
        mapping[10] = 0   # MAXDOP_1 → MAXDOP_1 ✓
        mapping[11] = 0   # MAXDOP_2 → MAXDOP_1 (보수적)
        mapping[12] = 1   # MAXDOP_3 → MAXDOP_4
        mapping[13] = 1   # MAXDOP_4 → MAXDOP_4 ✓
        mapping[14] = 1   # MAXDOP_5 → MAXDOP_4
        mapping[15] = 1   # MAXDOP_6 → MAXDOP_4
        mapping[16] = 2   # MAXDOP_7 → MAXDOP_8
        mapping[17] = 2   # MAXDOP_8 → MAXDOP_8 ✓
        mapping[18] = 2   # MAXDOP_9 → MAXDOP_8
        mapping[19] = 2   # MAXDOP_10 → MAXDOP_8
        
        # ==========================================
        # ISOLATION 매핑 (PPO 20-22 → DQN 18)
        # ==========================================
        # DQN에 없는 기능 → NO_ACTION (안전하게)
        mapping[20] = 18  # ISOLATION_READ_COMMITTED → NO_ACTION
        mapping[21] = 18  # ISOLATION_READ_UNCOMMITTED → NO_ACTION
        mapping[22] = 18  # ISOLATION_SNAPSHOT → NO_ACTION
        
        # ==========================================
        # JOIN hints 매핑 (PPO 23-26 → DQN 3-6)
        # ==========================================
        # 동일한 액션이므로 직접 매핑 ✓
        mapping[23] = 3   # USE_HASH_JOIN → HASH_JOIN ✓
        mapping[24] = 5   # USE_MERGE_JOIN → MERGE_JOIN ✓
        mapping[25] = 4   # USE_LOOP_JOIN → LOOP_JOIN ✓
        mapping[26] = 6   # FORCE_JOIN_ORDER → FORCE_ORDER ✓
        
        # ==========================================
        # 공통 힌트 매핑 (PPO 27-32 → DQN 7-13)
        # ==========================================
        mapping[27] = 7   # OPTIMIZE_FOR_UNKNOWN → OPTIMIZE_FOR_UNKNOWN ✓
        mapping[28] = 8   # DISABLE_PARAMETER_SNIFFING → DISABLE_PARAMETER_SNIFFING ✓
        mapping[29] = 9   # COMPAT_LEVEL_140 → COMPAT_LEVEL_140 ✓
        mapping[30] = 10  # COMPAT_LEVEL_150 → COMPAT_LEVEL_150 ✓
        mapping[31] = 11  # COMPAT_LEVEL_160 → COMPAT_LEVEL_160 ✓
        mapping[32] = 13  # RECOMPILE → RECOMPILE ✓
        
        # ==========================================
        # 고급 힌트 매핑 (PPO 33-42 → DQN 18)
        # ==========================================
        # DQN에 없는 고급 힌트 → NO_ACTION
        mapping[33] = 18  # FORCESEEK → NO_ACTION
        mapping[34] = 18  # FORCESCAN → NO_ACTION
        mapping[35] = 18  # DISABLE_OPTIMIZER_ROWGOAL → NO_ACTION
        mapping[36] = 18  # ENABLE_QUERY_OPTIMIZER_HOTFIXES → NO_ACTION
        mapping[37] = 18  # KEEPFIXED_PLAN → NO_ACTION
        mapping[38] = 18  # FORCE_LEGACY_CARDINALITY_ESTIMATION → NO_ACTION
        mapping[39] = 18  # DISALLOW_BATCH_MODE → NO_ACTION
        mapping[40] = 18  # ALLOW_BATCH_MODE → NO_ACTION
        mapping[41] = 18  # ASSUME_JOIN_PREDICATE_DEPENDS_ON_FILTERS → NO_ACTION
        mapping[42] = 18  # ASSUME_MIN_SELECTIVITY_FOR_FILTER_ESTIMATES → NO_ACTION
        
        # ==========================================
        # NO_ACTION 매핑 (PPO 43 → DQN 18)
        # ==========================================
        mapping[43] = 18  # NO_ACTION → NO_ACTION ✓
        
        return mapping
    
    def _get_ppo_action_names(self) -> Dict[int, str]:
        """PPO 액션 이름 (디버깅용)"""
        return {
            0: "FAST_10", 1: "FAST_20", 2: "FAST_30", 3: "FAST_40", 4: "FAST_50",
            5: "FAST_60", 6: "FAST_70", 7: "FAST_80", 8: "FAST_90", 9: "FAST_100",
            10: "MAXDOP_1", 11: "MAXDOP_2", 12: "MAXDOP_3", 13: "MAXDOP_4", 14: "MAXDOP_5",
            15: "MAXDOP_6", 16: "MAXDOP_7", 17: "MAXDOP_8", 18: "MAXDOP_9", 19: "MAXDOP_10",
            20: "ISOLATION_READ_COMMITTED", 21: "ISOLATION_READ_UNCOMMITTED", 22: "ISOLATION_SNAPSHOT",
            23: "USE_HASH_JOIN", 24: "USE_MERGE_JOIN", 25: "USE_LOOP_JOIN", 26: "FORCE_JOIN_ORDER",
            27: "OPTIMIZE_FOR_UNKNOWN", 28: "DISABLE_PARAMETER_SNIFFING",
            29: "COMPAT_LEVEL_140", 30: "COMPAT_LEVEL_150", 31: "COMPAT_LEVEL_160",
            32: "RECOMPILE", 33: "FORCESEEK", 34: "FORCESCAN",
            35: "DISABLE_OPTIMIZER_ROWGOAL", 36: "ENABLE_QUERY_OPTIMIZER_HOTFIXES",
            37: "KEEPFIXED_PLAN", 38: "FORCE_LEGACY_CARDINALITY_ESTIMATION",
            39: "DISALLOW_BATCH_MODE", 40: "ALLOW_BATCH_MODE",
            41: "ASSUME_JOIN_PREDICATE_DEPENDS_ON_FILTERS",
            42: "ASSUME_MIN_SELECTIVITY_FOR_FILTER_ESTIMATES",
            43: "NO_ACTION"
        }
    
    def _get_dqn_action_names(self) -> Dict[int, str]:
        """DQN 액션 이름 (디버깅용)"""
        return {
            0: "MAXDOP_1", 1: "MAXDOP_4", 2: "MAXDOP_8",
            3: "HASH_JOIN", 4: "LOOP_JOIN", 5: "MERGE_JOIN", 6: "FORCE_ORDER",
            7: "OPTIMIZE_FOR_UNKNOWN", 8: "DISABLE_PARAMETER_SNIFFING",
            9: "COMPAT_LEVEL_140", 10: "COMPAT_LEVEL_150", 11: "COMPAT_LEVEL_160",
            12: "USE_NOLOCK", 13: "RECOMPILE",
            14: "FAST_10", 15: "FAST_50", 16: "FAST_100", 17: "FAST_200",
            18: "NO_ACTION"
        }
    
    def convert(self, ppo_action: int) -> int:
        """
        PPO 액션을 DQN 액션으로 변환
        
        Args:
            ppo_action: PPO v3 액션 ID (0~43)
        
        Returns:
            dqn_action: DQN v4 액션 ID (0~18)
        """
        if ppo_action < 0 or ppo_action > 43:
            if self.verbose:
                print(f"[WARN] Invalid PPO action {ppo_action}, defaulting to NO_ACTION")
            return 18  # NO_ACTION
        
        dqn_action = self.MAPPING.get(ppo_action, 18)
        
        # 통계 업데이트
        self.mapping_stats['total'] += 1
        self.mapping_stats['by_ppo_action'][ppo_action] += 1
        self.mapping_stats['by_dqn_action'][dqn_action] += 1
        
        # 카테고리별 통계
        if 0 <= ppo_action <= 9:
            category = 'fast'
        elif 10 <= ppo_action <= 19:
            category = 'maxdop'
        elif 20 <= ppo_action <= 22:
            category = 'isolation'
        elif 23 <= ppo_action <= 26:
            category = 'join_hint'
        elif 27 <= ppo_action <= 32:
            category = 'common_hint'
        elif 33 <= ppo_action <= 42:
            category = 'advanced_hint'
        else:  # 43
            category = 'no_action'
        
        self.mapping_stats['by_category'][category] += 1
        
        if self.verbose:
            ppo_name = self.PPO_ACTION_NAMES.get(ppo_action, f"UNKNOWN_{ppo_action}")
            dqn_name = self.DQN_ACTION_NAMES.get(dqn_action, f"UNKNOWN_{dqn_action}")
            exact = "[EXACT]" if self._is_exact_match(ppo_action, dqn_action) else "[APPROX]"
            print(f"  [MAPPER] PPO {ppo_action:2d} ({ppo_name:20s}) -> DQN {dqn_action:2d} ({dqn_name:20s}) {exact}")
        
        return dqn_action
    
    def _is_exact_match(self, ppo_action: int, dqn_action: int) -> bool:
        """정확한 매핑인지 근사 매핑인지 확인"""
        # 정확한 매핑: 액션의 의미가 완전히 동일
        exact_matches = {
            0: 14,   # FAST_10
            4: 15,   # FAST_50
            9: 16,   # FAST_100
            10: 0,   # MAXDOP_1
            13: 1,   # MAXDOP_4
            17: 2,   # MAXDOP_8
            23: 3,   # HASH_JOIN
            24: 5,   # MERGE_JOIN
            25: 4,   # LOOP_JOIN
            26: 6,   # FORCE_ORDER
            27: 7,   # OPTIMIZE_FOR_UNKNOWN
            28: 8,   # DISABLE_PARAMETER_SNIFFING
            29: 9,   # COMPAT_140
            30: 10,  # COMPAT_150
            31: 11,  # COMPAT_160
            32: 13,  # RECOMPILE
            43: 18,  # NO_ACTION
        }
        
        return exact_matches.get(ppo_action) == dqn_action
    
    def get_stats(self) -> Dict:
        """매핑 통계 반환"""
        return {
            'total': self.mapping_stats['total'],
            'by_ppo_action': dict(self.mapping_stats['by_ppo_action']),
            'by_dqn_action': dict(self.mapping_stats['by_dqn_action']),
            'by_category': dict(self.mapping_stats['by_category'])
        }
    
    def print_stats(self):
        """매핑 통계 출력"""
        stats = self.get_stats()
        
        print("\n" + "=" * 80)
        print(" PPO -> DQN Action Mapping Statistics")
        print("=" * 80)
        
        print(f"\nTotal mappings: {stats['total']}")
        
        print("\n[1] By Category:")
        for category, count in sorted(stats['by_category'].items()):
            pct = 100.0 * count / stats['total'] if stats['total'] > 0 else 0
            print(f"  {category:20s}: {count:4d} ({pct:5.1f}%)")
        
        print("\n[2] Top 10 PPO Actions:")
        top_ppo = sorted(stats['by_ppo_action'].items(), key=lambda x: x[1], reverse=True)[:10]
        for ppo_action, count in top_ppo:
            ppo_name = self.PPO_ACTION_NAMES.get(ppo_action, f"UNKNOWN_{ppo_action}")
            dqn_action = self.MAPPING[ppo_action]
            dqn_name = self.DQN_ACTION_NAMES.get(dqn_action, f"UNKNOWN_{dqn_action}")
            pct = 100.0 * count / stats['total'] if stats['total'] > 0 else 0
            print(f"  PPO {ppo_action:2d} ({ppo_name:20s}) -> DQN {dqn_action:2d} ({dqn_name:20s}): {count:4d} ({pct:5.1f}%)")
        
        print("\n[3] DQN Action Distribution:")
        for dqn_action in sorted(stats['by_dqn_action'].keys()):
            count = stats['by_dqn_action'][dqn_action]
            dqn_name = self.DQN_ACTION_NAMES.get(dqn_action, f"UNKNOWN_{dqn_action}")
            pct = 100.0 * count / stats['total'] if stats['total'] > 0 else 0
            print(f"  DQN {dqn_action:2d} ({dqn_name:20s}): {count:4d} ({pct:5.1f}%)")
        
        print("=" * 80)


if __name__ == '__main__':
    # 테스트
    mapper = PPOToDQNActionMapper(verbose=True)
    
    print("=" * 80)
    print(" PPO -> DQN Action Mapper Test")
    print("=" * 80)
    
    # 주요 액션 변환 테스트
    test_actions = [
        (0, "FAST_10"),
        (4, "FAST_50"),
        (9, "FAST_100"),
        (10, "MAXDOP_1"),
        (13, "MAXDOP_4"),
        (17, "MAXDOP_8"),
        (23, "USE_HASH_JOIN"),
        (25, "USE_LOOP_JOIN"),
        (20, "ISOLATION_READ_UNCOMMITTED"),
        (33, "FORCESEEK"),
        (43, "NO_ACTION")
    ]
    
    print("\n[Test] Sample Conversions:")
    for ppo_action, ppo_name in test_actions:
        dqn_action = mapper.convert(ppo_action)
        dqn_name = mapper.DQN_ACTION_NAMES[dqn_action]
        exact = "[EXACT]" if mapper._is_exact_match(ppo_action, dqn_action) else "[APPROX]"
        print(f"  PPO {ppo_action:2d} ({ppo_name:30s}) -> DQN {dqn_action:2d} ({dqn_name:20s}) {exact}")
    
    print("\n" + "=" * 80)
    print(" [OK] All tests passed!")
    print("=" * 80)

