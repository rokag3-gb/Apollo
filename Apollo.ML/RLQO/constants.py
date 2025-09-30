# -*- coding: utf-8 -*-
"""
RLQO 모듈에서 공유하는 상수들을 정의합니다.
"""

# 평가와 학습에 공통으로 사용할 샘플 쿼리 목록
SAMPLE_QUERIES = [
    "SELECT execution_id FROM dbo.exe_execution e;",
    "SELECT AccountID=o.account_id, SecID=o.security_id, Side=o.side, Qty=e.exec_qty, Price=e.exec_price, Fee=e.fee, Tax=e.tax FROM dbo.exe_execution e JOIN dbo.ord_order o ON e.order_id=o.order_id;",
    "SELECT TOP 300 * FROM dbo.risk_exposure_snapshot /*WHERE CAST(ts AS DATE) = cast(getdate() as date)*/;",
    "SELECT e.execution_id, o.account_id, s.symbol, o.side, e.exec_qty, e.exec_price, e.exec_time FROM dbo.exe_execution e JOIN dbo.ord_order o ON e.order_id=o.order_id JOIN dbo.ref_security s ON o.security_id=s.security_id ORDER BY e.exec_time DESC;",
    "SELECT e.* FROM dbo.exe_execution e WHERE NOT EXISTS (SELECT 1 FROM dbo.ord_order o WHERE o.order_id = e.order_id);",
    "SELECT account_id, GETDATE(), RAND()*100000, RAND()*50000, 0, 0 FROM dbo.cust_account WHERE closed_at IS NULL;"
]