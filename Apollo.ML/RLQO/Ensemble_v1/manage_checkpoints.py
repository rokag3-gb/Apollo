# -*- coding: utf-8 -*-
"""
Ensemble v1: Checkpoint Management

체크포인트를 관리하는 유틸리티 스크립트
"""

import os
import sys
import json
from datetime import datetime

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
checkpoint_dir = os.path.join(current_dir, 'results', 'checkpoints')


def list_checkpoints():
    """저장된 체크포인트 목록 표시"""
    print("=" * 80)
    print("Saved Checkpoints")
    print("=" * 80)
    
    if not os.path.exists(checkpoint_dir):
        print("No checkpoints directory found.")
        return
    
    checkpoint_files = [f for f in os.listdir(checkpoint_dir) if f.endswith('.json')]
    
    if not checkpoint_files:
        print("No checkpoints found.")
        return
    
    for filename in sorted(checkpoint_files):
        filepath = os.path.join(checkpoint_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            strategy = data.get('voting_strategy', 'unknown')
            n_queries = data.get('n_queries', 0)
            completed = len(data.get('query_results', {}))
            timestamp = data.get('timestamp', 'unknown')
            
            print(f"\n{filename}")
            print(f"  Strategy:  {strategy}")
            print(f"  Progress:  {completed}/{n_queries} queries ({completed/n_queries*100:.1f}%)")
            print(f"  Timestamp: {timestamp}")
            
            if 'summary' in data:
                summary = data['summary']
                print(f"  Results:   Mean Speedup: {summary['mean_speedup']:.3f}x, "
                      f"Win Rate: {summary['win_rate']*100:.1f}%")
            
        except Exception as e:
            print(f"\n{filename}")
            print(f"  [ERROR] Failed to read: {e}")
    
    print("\n" + "=" * 80)


def delete_checkpoint(strategy: str):
    """특정 전략의 체크포인트 삭제"""
    filename = f"checkpoint_{strategy}.json"
    filepath = os.path.join(checkpoint_dir, filename)
    
    if not os.path.exists(filepath):
        print(f"[ERROR] Checkpoint not found: {filename}")
        return
    
    try:
        os.remove(filepath)
        print(f"[OK] Deleted: {filename}")
    except Exception as e:
        print(f"[ERROR] Failed to delete: {e}")


def delete_all_checkpoints():
    """모든 체크포인트 삭제"""
    if not os.path.exists(checkpoint_dir):
        print("No checkpoints directory found.")
        return
    
    checkpoint_files = [f for f in os.listdir(checkpoint_dir) if f.endswith('.json')]
    
    if not checkpoint_files:
        print("No checkpoints to delete.")
        return
    
    print(f"Found {len(checkpoint_files)} checkpoint(s):")
    for f in checkpoint_files:
        print(f"  - {f}")
    
    confirm = input("\nDelete all checkpoints? (yes/no): ")
    
    if confirm.lower() == 'yes':
        for filename in checkpoint_files:
            filepath = os.path.join(checkpoint_dir, filename)
            try:
                os.remove(filepath)
                print(f"[OK] Deleted: {filename}")
            except Exception as e:
                print(f"[ERROR] Failed to delete {filename}: {e}")
        print("\n[OK] All checkpoints deleted.")
    else:
        print("\n[CANCELLED] No checkpoints deleted.")


def show_checkpoint_details(strategy: str):
    """체크포인트 상세 정보 표시"""
    filename = f"checkpoint_{strategy}.json"
    filepath = os.path.join(checkpoint_dir, filename)
    
    if not os.path.exists(filepath):
        print(f"[ERROR] Checkpoint not found: {filename}")
        return
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("=" * 80)
        print(f"Checkpoint Details: {strategy.upper()}")
        print("=" * 80)
        
        print(f"\nGeneral Information:")
        print(f"  Strategy:  {data.get('voting_strategy', 'unknown')}")
        print(f"  Timestamp: {data.get('timestamp', 'unknown')}")
        print(f"  Queries:   {data.get('n_queries', 0)}")
        print(f"  Episodes:  {data.get('n_episodes', 0)}")
        
        query_results = data.get('query_results', {})
        print(f"\nProgress:")
        print(f"  Completed: {len(query_results)} queries")
        print(f"  Remaining: {data.get('n_queries', 0) - len(query_results)} queries")
        
        completed_queries = sorted([int(k) for k in query_results.keys()])
        print(f"  Completed query IDs: {completed_queries}")
        
        if 'summary' in data:
            summary = data['summary']
            print(f"\nCurrent Results:")
            print(f"  Mean Speedup:   {summary['mean_speedup']:.3f}x")
            print(f"  Median Speedup: {summary['median_speedup']:.3f}x")
            print(f"  Max Speedup:    {summary['max_speedup']:.3f}x")
            print(f"  Win Rate:       {summary['win_rate']*100:.1f}%")
            print(f"  Safe Rate:      {summary['safe_rate']*100:.1f}%")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"[ERROR] Failed to read checkpoint: {e}")


def main():
    """Main CLI"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_checkpoints.py list")
        print("  python manage_checkpoints.py details <strategy>")
        print("  python manage_checkpoints.py delete <strategy>")
        print("  python manage_checkpoints.py delete-all")
        print("\nExample:")
        print("  python manage_checkpoints.py list")
        print("  python manage_checkpoints.py details weighted")
        print("  python manage_checkpoints.py delete weighted")
        return
    
    command = sys.argv[1]
    
    if command == 'list':
        list_checkpoints()
    
    elif command == 'details':
        if len(sys.argv) < 3:
            print("[ERROR] Strategy name required")
            print("Usage: python manage_checkpoints.py details <strategy>")
            return
        strategy = sys.argv[2]
        show_checkpoint_details(strategy)
    
    elif command == 'delete':
        if len(sys.argv) < 3:
            print("[ERROR] Strategy name required")
            print("Usage: python manage_checkpoints.py delete <strategy>")
            return
        strategy = sys.argv[2]
        delete_checkpoint(strategy)
    
    elif command == 'delete-all':
        delete_all_checkpoints()
    
    else:
        print(f"[ERROR] Unknown command: {command}")
        print("Available commands: list, details, delete, delete-all")


if __name__ == '__main__':
    main()

