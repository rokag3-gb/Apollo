# -*- coding: utf-8 -*-
"""
OPTION (RECOMPILE) 추가 테스트
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from RLQO.DQN_v4.env.v4_db_env import apply_action_to_sql

# 테스트 케이스
test_cases = [
    # Case 1: NO_ACTION (OPTION 절 없음)
    {
        "name": "NO_ACTION without OPTION",
        "sql": "SELECT * FROM table WHERE id = 1",
        "action": {"type": "BASELINE", "value": ""},
        "expected_keywords": ["OPTION (RECOMPILE)"]
    },
    
    # Case 2: NO_ACTION (세미콜론 있음)
    {
        "name": "NO_ACTION with semicolon",
        "sql": "SELECT * FROM table WHERE id = 1;",
        "action": {"type": "BASELINE", "value": ""},
        "expected_keywords": ["OPTION (RECOMPILE);"]
    },
    
    # Case 3: HINT (MAXDOP)
    {
        "name": "MAXDOP hint",
        "sql": "SELECT * FROM table WHERE id = 1",
        "action": {"type": "HINT", "value": "MAXDOP 4"},
        "expected_keywords": ["OPTION (RECOMPILE, MAXDOP 4)"]
    },
    
    # Case 4: HINT with existing OPTION
    {
        "name": "HINT with existing OPTION",
        "sql": "SELECT * FROM table WHERE id = 1 OPTION (FAST 10)",
        "action": {"type": "HINT", "value": "MAXDOP 4"},
        "expected_keywords": ["OPTION (RECOMPILE, MAXDOP 4,", "FAST 10)"]
    },
    
    # Case 5: Multiple hints
    {
        "name": "Multiple hints",
        "sql": "SELECT * FROM table WHERE id = 1",
        "action": {"type": "HINT", "value": "HASH JOIN"},
        "expected_keywords": ["OPTION (RECOMPILE, HASH JOIN)"]
    },
    
    # Case 6: CTE query
    {
        "name": "CTE query",
        "sql": "WITH cte AS (SELECT * FROM table) SELECT * FROM cte",
        "action": {"type": "BASELINE", "value": ""},
        "expected_keywords": ["OPTION (RECOMPILE)"]
    },
    
    # Case 7: 대소문자 혼합
    {
        "name": "Mixed case OPTION",
        "sql": "SELECT * FROM table WHERE id = 1 option (fast 10)",
        "action": {"type": "HINT", "value": "MAXDOP 4"},
        "expected_keywords": ["RECOMPILE", "MAXDOP 4", "fast 10"]
    }
]

print("=" * 80)
print("OPTION (RECOMPILE) 추가 테스트")
print("=" * 80)

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    print(f"\n[Test {i}] {test['name']}")
    print(f"  Input SQL: {test['sql']}")
    
    result_sql = apply_action_to_sql(test['sql'], test['action'])
    print(f"  Result SQL: {result_sql}")
    
    # 키워드 체크
    all_found = True
    for keyword in test['expected_keywords']:
        if keyword not in result_sql:
            print(f"  [FAIL] Missing keyword: '{keyword}'")
            all_found = False
            failed += 1
            break
    
    if all_found:
        print(f"  [PASS]")
        passed += 1

print("\n" + "=" * 80)
print(f"Test Results: {passed} passed, {failed} failed")
print("=" * 80)

if failed == 0:
    print("\n✓ All tests passed!")
else:
    print(f"\n✗ {failed} test(s) failed!")
    sys.exit(1)

