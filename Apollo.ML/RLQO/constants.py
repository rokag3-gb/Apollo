# -*- coding: utf-8 -*-
"""
RLQO 모듈에서 공유하는 상수들을 정의합니다.
"""

# 평가와 학습에 공통으로 사용할 샘플 쿼리 목록
SAMPLE_QUERIES = [
    # [인덱스 0] 계좌별 일별 거래 통계 (5-way JOIN + GROUP BY + 집계) - 약 20-30ms
    """
    SELECT 
        a.account_id, 
        c.name AS customer_name,
        CAST(e.exec_time AS DATE) AS trade_date,
        COUNT(DISTINCT o.order_id) AS order_count,
        COUNT(e.execution_id) AS execution_count,
        SUM(e.exec_qty * e.exec_price) AS total_trade_value,
        SUM(e.fee) AS total_fees,
        SUM(e.tax) AS total_taxes
    FROM dbo.exe_execution e
    JOIN dbo.ord_order o ON e.order_id = o.order_id
    JOIN dbo.cust_account a ON o.account_id = a.account_id
    JOIN dbo.cust_customer c ON a.customer_id = c.customer_id
    JOIN dbo.ref_security s ON o.security_id = s.security_id
    WHERE e.exec_time >= DATEADD(DAY, -30, GETDATE())
    GROUP BY a.account_id, c.name, CAST(e.exec_time AS DATE)
    HAVING SUM(e.exec_qty * e.exec_price) > 1000
    ORDER BY trade_date DESC, total_trade_value DESC;
    """,
    
    # [인덱스 1] 거래소별 종목별 평균 체결가격과 거래량 (윈도우 함수 + 서브쿼리) - 약 7-10ms
    """
    WITH ExecutionStats AS (
        SELECT 
            s.security_id,
            s.symbol,
            ex.name AS exchange_name,
            e.exec_price,
            e.exec_qty,
            e.exec_time,
            ROW_NUMBER() OVER (PARTITION BY s.security_id ORDER BY e.exec_time DESC) AS rn,
            AVG(e.exec_price) OVER (PARTITION BY s.security_id) AS avg_price,
            SUM(e.exec_qty) OVER (PARTITION BY s.security_id) AS total_volume
        FROM dbo.exe_execution e
        JOIN dbo.ord_order o ON e.order_id = o.order_id
        JOIN dbo.ref_security s ON o.security_id = s.security_id
        JOIN dbo.ref_exchange ex ON s.exchange_id = ex.exchange_id
        WHERE e.exec_time >= DATEADD(HOUR, -24, GETDATE())
    )
    SELECT 
        security_id, 
        symbol, 
        exchange_name, 
        avg_price, 
        total_volume,
        exec_price AS last_price,
        exec_time AS last_exec_time
    FROM ExecutionStats
    WHERE rn = 1
    ORDER BY total_volume DESC;
    """,
    
    # [인덱스 2] 대용량 테이블 전체 스캔 (매우 느림!) - 약 1,000-2,000ms ⚠️
    "SELECT execution_id FROM dbo.exe_execution e;",
    
    # [인덱스 3] 2-way JOIN (대용량, 매우 느림!) - 약 5,000-7,000ms ⚠️⚠️
    "SELECT Top 100 AccountID=o.account_id, SecID=o.security_id, Side=o.side, Qty=e.exec_qty, Price=e.exec_price, Fee=e.fee, Tax=e.tax FROM dbo.exe_execution e JOIN dbo.ord_order o ON e.order_id=o.order_id order by Qty desc;",
    
    # [인덱스 4] 3-way JOIN + ORDER BY (극도로 느림!) - 약 10,000-14,000ms ⚠️⚠️⚠️ ← 가장 느린 쿼리!
    "SELECT Top 200 e.execution_id, o.account_id, s.symbol, o.side, e.exec_qty, e.exec_price, e.exec_time FROM dbo.exe_execution e JOIN dbo.ord_order o ON e.order_id=o.order_id JOIN dbo.ref_security s ON o.security_id=s.security_id ORDER BY e.exec_time DESC;",
    
    # [인덱스 5] NOT EXISTS (서브쿼리) - 약 600ms
    "SELECT e.* FROM dbo.exe_execution e WHERE NOT EXISTS (SELECT 1 FROM dbo.ord_order o WHERE o.order_id = e.order_id);",
    
    # [인덱스 6] RAND() 함수 (빠름) - 약 30-40ms
    "SELECT account_id, GETDATE(), RAND()*100000, RAND()*50000, 0, 0 FROM dbo.cust_account WHERE closed_at IS NULL;",
    
    # [인덱스 7] 주문 체결률과 평균 슬리피지 분석 (복잡한 LEFT JOIN + CASE + 집계) - 약 25-30ms
    """
    SELECT 
        o.account_id,
        s.symbol,
        s.type_code AS security_type,
        ex.name AS exchange_name,
        o.side,
        COUNT(o.order_id) AS total_orders,
        COUNT(e.execution_id) AS executed_orders,
        CAST(COUNT(e.execution_id) AS FLOAT) / NULLIF(COUNT(o.order_id), 0) * 100 AS fill_rate_pct,
        SUM(o.qty) AS total_order_qty,
        SUM(e.exec_qty) AS total_exec_qty,
        AVG(CASE WHEN o.price IS NOT NULL THEN ABS(e.exec_price - o.price) ELSE 0 END) AS avg_slippage,
        SUM(e.fee + e.tax) AS total_costs
    FROM dbo.ord_order o
    LEFT JOIN dbo.exe_execution e ON o.order_id = e.order_id
    JOIN dbo.ref_security s ON o.security_id = s.security_id
    JOIN dbo.ref_exchange ex ON s.exchange_id = ex.exchange_id
    WHERE o.create_time >= DATEADD(DAY, -14, GETDATE())
        AND o.status IN ('FILLED', 'PARTIALLY_FILLED', 'PENDING')
    GROUP BY o.account_id, s.symbol, s.type_code, ex.name, o.side
    ORDER BY total_orders DESC;
    """,
    
    # [인덱스 8] 포지션 수익률 분석 (LAG 함수, 데이터 없으면 0ms) - 약 0ms (데이터 없음)
    """
    WITH DailyPnL AS (
        SELECT 
            p.account_id,
            p.as_of_date,
            p.realized_pnl,
            p.unrealized_pnl,
            p.fees,
            p.taxes,
            p.mtm_value,
            (p.realized_pnl + p.unrealized_pnl - p.fees - p.taxes) AS net_pnl,
            LAG(p.mtm_value, 1) OVER (PARTITION BY p.account_id ORDER BY p.as_of_date) AS prev_mtm_value,
            LAG(p.as_of_date, 1) OVER (PARTITION BY p.account_id ORDER BY p.as_of_date) AS prev_date
        FROM dbo.pnl_daily p
        WHERE p.as_of_date >= DATEADD(DAY, -60, GETDATE())
    )
    SELECT 
        d.account_id,
        a.base_currency,
        c.name AS customer_name,
        d.as_of_date,
        d.net_pnl,
        d.mtm_value,
        d.prev_mtm_value,
        CASE 
            WHEN d.prev_mtm_value IS NOT NULL AND d.prev_mtm_value != 0 
            THEN ((d.mtm_value - d.prev_mtm_value) / ABS(d.prev_mtm_value)) * 100
            ELSE 0 
        END AS daily_return_pct
    FROM DailyPnL d
    JOIN dbo.cust_account a ON d.account_id = a.account_id
    JOIN dbo.cust_customer c ON a.customer_id = c.customer_id
    WHERE d.net_pnl IS NOT NULL
    ORDER BY d.account_id, d.as_of_date DESC;
    """,
    
    # [인덱스 9] 복합 거래 패턴 분석 (UNION ALL, 빠름) - 약 25-30ms
    """
    SELECT 
        'HIGH_FREQUENCY' AS trader_type,
        o.account_id,
        COUNT(o.order_id) AS order_count,
        AVG(DATEDIFF(SECOND, o.create_time, o.update_time)) AS avg_order_duration_sec,
        SUM(e.exec_qty * e.exec_price) AS total_value
    FROM dbo.ord_order o
    JOIN dbo.exe_execution e ON o.order_id = e.order_id
    WHERE o.create_time >= DATEADD(HOUR, -4, GETDATE())
    GROUP BY o.account_id
    HAVING COUNT(o.order_id) > 50
    UNION ALL
    SELECT 
        'LARGE_TRADE' AS trader_type,
        o.account_id,
        COUNT(o.order_id) AS order_count,
        AVG(DATEDIFF(SECOND, o.create_time, o.update_time)) AS avg_order_duration_sec,
        SUM(e.exec_qty * e.exec_price) AS total_value
    FROM dbo.ord_order o
    JOIN dbo.exe_execution e ON o.order_id = e.order_id
    WHERE o.create_time >= DATEADD(HOUR, -4, GETDATE())
    GROUP BY o.account_id
    HAVING SUM(e.exec_qty * e.exec_price) > 100000
    ORDER BY order_count DESC;
    """
]

# ==============================================================================
# 주석 없이 깔끔하게 정리 (위의 주석 기반 요약):
# ==============================================================================
# 
# 인덱스 | 쿼리 설명                        | 예상 실행 시간    | 난이도
# -------|----------------------------------|-------------------|--------
#   0    | 계좌별 일별 거래 통계 (5-way JOIN)  | 20-30ms          | 중
#   1    | 거래소별 평균 체결가격 (윈도우)      | 7-10ms           | 중
#   2    | 대용량 테이블 전체 스캔             | 1,000-2,000ms    | 높음 ⚠️
#   3    | 2-way JOIN (대용량)               | 5,000-7,000ms    | 매우 높음 ⚠️⚠️
#   4    | 3-way JOIN + ORDER BY (최악!)     | 10,000-14,000ms  | 극도로 높음 ⚠️⚠️⚠️
#   5    | NOT EXISTS (서브쿼리)              | 600ms            | 중
#   6    | RAND() 함수                       | 30-40ms          | 낮음
#   7    | 주문 체결률 분석 (복잡 LEFT JOIN)   | 25-30ms          | 중
#   8    | 포지션 수익률 (LAG, 데이터 없음)    | 0ms              | N/A
#   9    | 복합 패턴 분석 (UNION ALL)         | 25-30ms          | 중
# 
# ==============================================================================