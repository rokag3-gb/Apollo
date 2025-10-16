# -*- coding: utf-8 -*-
"""
PPO v2: Domain-Aware MDP 재설계

핵심 개선:
- State: 79차원 → 18차원 actionable features
- Reward: Log scale 정규화 + clipping [-1, +1]
- Action: Query-Specific (5-7개)
"""

