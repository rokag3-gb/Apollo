# -*- coding: utf-8 -*-
"""
PPO v2 Custom Callbacks

Early Stopping 및 기타 유용한 콜백 구현
"""

import numpy as np
from stable_baselines3.common.callbacks import BaseCallback


class EarlyStoppingCallback(BaseCallback):
    """
    Best 성능 도달 후 N episodes 동안 개선 없으면 조기 종료
    
    Args:
        patience: 개선 없이 기다릴 에피소드 수
        min_delta: 개선으로 인정할 최소 변화량
        verbose: 진행 상황 출력 여부
    """
    
    def __init__(self, patience: int = 10, min_delta: float = 0.01, verbose: bool = True):
        super().__init__(verbose)
        self.patience = patience
        self.min_delta = min_delta
        self.best_mean_reward = -np.inf
        self.episodes_without_improvement = 0
        self.episode_rewards = []
        self.episode_count = 0
        
    def _on_step(self) -> bool:
        """
        매 스텝마다 호출
        
        Returns:
            True: 학습 계속
            False: 학습 중단
        """
        # 에피소드 완료 확인
        if self.locals.get('dones', [False])[0]:
            # 에피소드 보상 수집
            info = self.locals.get('infos', [{}])[0]
            if 'episode' in info:
                episode_reward = info['episode']['r']
                self.episode_rewards.append(episode_reward)
                self.episode_count += 1
                
                # 최근 10개 에피소드 평균 보상 계산
                if len(self.episode_rewards) >= 10:
                    recent_rewards = self.episode_rewards[-10:]
                    mean_reward = np.mean(recent_rewards)
                    
                    # Best reward 갱신 확인
                    if mean_reward > self.best_mean_reward + self.min_delta:
                        if self.verbose:
                            print(f"\n[Early Stop] 개선! Mean Reward: {mean_reward:.2f} (Best: {self.best_mean_reward:.2f})")
                        self.best_mean_reward = mean_reward
                        self.episodes_without_improvement = 0
                    else:
                        self.episodes_without_improvement += 1
                        if self.verbose and self.episodes_without_improvement % 5 == 0:
                            print(f"[Early Stop] 개선 없음: {self.episodes_without_improvement}/{self.patience} episodes")
                    
                    # Early stopping 조건 확인
                    if self.episodes_without_improvement >= self.patience:
                        if self.verbose:
                            print(f"\n[Early Stop] {self.patience} episodes 동안 개선 없음. 학습 중단.")
                            print(f"Best Mean Reward: {self.best_mean_reward:.2f}")
                        return False  # 학습 중단
        
        return True  # 학습 계속


class ActionDiversityCallback(BaseCallback):
    """
    액션 다양성 모니터링 콜백
    
    같은 액션이 N번 연속으로 선택되면 경고
    """
    
    def __init__(self, max_consecutive: int = 5, verbose: bool = True):
        super().__init__(verbose)
        self.max_consecutive = max_consecutive
        self.last_action = None
        self.consecutive_count = 0
        self.action_counts = {}
        
    def _on_step(self) -> bool:
        """
        매 스텝마다 호출하여 액션 다양성 추적
        
        Returns:
            True: 항상 계속 (경고만 출력)
        """
        # 현재 액션 가져오기
        actions = self.locals.get('actions', None)
        if actions is not None:
            action = int(actions[0]) if len(actions) > 0 else None
            
            if action is not None:
                # 액션 카운팅
                self.action_counts[action] = self.action_counts.get(action, 0) + 1
                
                # 연속 동일 액션 체크
                if action == self.last_action:
                    self.consecutive_count += 1
                    
                    if self.consecutive_count >= self.max_consecutive and self.verbose:
                        if self.consecutive_count == self.max_consecutive:
                            print(f"\n[Warning] Action {action}이(가) {self.consecutive_count}번 연속 선택됨!")
                else:
                    self.consecutive_count = 1
                    self.last_action = action
        
        return True  # 항상 계속


if __name__ == '__main__':
    print("=== PPO v2 Custom Callbacks ===\n")
    print("1. EarlyStoppingCallback:")
    print("   - Best 성능 도달 후 N episodes 동안 개선 없으면 조기 종료")
    print("   - patience: 기다릴 에피소드 수 (기본값: 10)")
    print("   - min_delta: 개선 인정 최소값 (기본값: 0.01)")
    print("\n2. ActionDiversityCallback:")
    print("   - 같은 액션이 N번 연속 선택되면 경고")
    print("   - max_consecutive: 연속 허용 횟수 (기본값: 5)")


