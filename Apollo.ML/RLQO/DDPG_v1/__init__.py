# -*- coding: utf-8 -*-
"""
DDPG v1: Deep Deterministic Policy Gradient for Query Optimization

Continuous action space를 활용한 SQL Server 쿼리 최적화
"""

__version__ = '1.0.0'
__author__ = 'Apollo Team'
__description__ = 'DDPG-based Query Plan Optimization with Continuous Actions'

from .config.action_decoder import ContinuousActionDecoder
from .env.ddpg_sim_env import QueryPlanSimEnvDDPGv1
from .env.ddpg_db_env import QueryPlanRealDBEnvDDPGv1

__all__ = [
    'ContinuousActionDecoder',
    'QueryPlanSimEnvDDPGv1',
    'QueryPlanRealDBEnvDDPGv1'
]

