# -*- coding: utf-8 -*-
"""
TD3 v1: Twin Delayed DDPG

DDPG v1의 개선 버전:
1. Twin Critic Networks (Q1, Q2) - overestimation 방지
2. Delayed Policy Updates - 안정성 향상
3. Target Policy Smoothing - 노이즈 추가로 과적합 방지

예상 성능: 2.0~2.2x (DDPG v1 1.88x → 10~20% 추가 개선)
"""

__version__ = "1.0.0"
__author__ = "Apollo RLQO Team"

