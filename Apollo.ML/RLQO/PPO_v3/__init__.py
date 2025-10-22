# -*- coding: utf-8 -*-
"""
PPO v3: Query Plan Optimization using Proximal Policy Optimization

주요 개선사항:
- 쿼리 개수: 9개 → 30개
- Action Space: 19개 → 44개 (FAST 10개, MAXDOP 10개, ISOLATION 3개, 고급 DBA 액션 10개)
- 하이브리드 학습: Simulation 100K + RealDB 50K Fine-tuning
"""

__version__ = "3.0.0"

