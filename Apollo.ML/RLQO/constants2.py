# -*- coding: utf-8 -*-
"""
RLQO 모듈에서 공유하는 상수들을 정의합니다.
(30개 쿼리 확장 버전)
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
    
    
    # [인덱스 9] 당일 거래량 상위 종목 (GROUP BY + 집계) - 약 15-20ms
    """
    SELECT TOP 20
        s.security_id,
        s.symbol,
        SUM(e.exec_qty) AS total_volume,
        COUNT(e.execution_id) AS trade_count,
        AVG(e.exec_price) AS avg_price,
        MIN(e.exec_price) AS low_price,
        MAX(e.exec_price) AS high_price
    FROM dbo.exe_execution e
    JOIN dbo.ord_order o ON e.order_id = o.order_id
    JOIN dbo.ref_security s ON o.security_id = s.security_id
    WHERE CAST(e.exec_time AS DATE) = CAST(GETDATE() AS DATE)
    GROUP BY s.security_id, s.symbol
    ORDER BY total_volume DESC;
    """,
    
    # [인덱스 10] 당일 거래대금 상위 종목 (GROUP BY + 계산 집계) - 약 15-20ms
    """
    SELECT TOP 20
        s.security_id,
        s.symbol,
        SUM(e.exec_qty * e.exec_price) AS total_turnover,
        SUM(e.fee + e.tax) AS total_costs,
        COUNT(DISTINCT o.account_id) AS unique_accounts
    FROM dbo.exe_execution e
    JOIN dbo.ord_order o ON e.order_id = o.order_id
    JOIN dbo.ref_security s ON o.security_id = s.security_id
    WHERE CAST(e.exec_time AS DATE) = CAST(GETDATE() AS DATE)
    GROUP BY s.security_id, s.symbol
    ORDER BY total_turnover DESC;
    """,
    
    # [인덱스 11] 전일 종가 대비 등락률 상위 종목 (CTE + 계산) - 약 10-15ms
    """
    WITH YesterdayPrice AS (
        SELECT security_id, [close]
        FROM dbo.mkt_price_eod
        WHERE trade_date = (SELECT MAX(trade_date) FROM dbo.mkt_price_eod)
    ),
    TodayPrice AS (
        SELECT security_id, last_price, 
               ROW_NUMBER() OVER(PARTITION BY security_id ORDER BY ts DESC) as rn
        FROM dbo.mkt_price_intraday
    )
    SELECT TOP 15
        t.security_id,
        s.symbol,
        y.[close] as yesterday_close,
        t.last_price as current_price,
        (t.last_price - y.[close]) / y.[close] * 100 AS change_pct
    FROM TodayPrice t
    JOIN YesterdayPrice y ON t.security_id = y.security_id
    JOIN dbo.ref_security s ON t.security_id = s.security_id
    WHERE t.rn = 1 AND y.[close] > 0
    ORDER BY change_pct DESC;
    """,
    
    # [인덱스 12] 계좌별 포지션 평가 (포지션 테이블 + 최신 시세) - 약 10-15ms
    """
    SELECT TOP 100
        p.account_id,
        p.security_id,
        s.symbol,
        p.qty,
        p.avg_price,
        m.last_price,
        (m.last_price - p.avg_price) * p.qty AS unrealized_pnl,
        p.last_update_time
    FROM dbo.pos_position p
    JOIN dbo.ref_security s ON p.security_id = s.security_id
    JOIN (
        SELECT security_id, last_price, 
               ROW_NUMBER() OVER(PARTITION BY security_id ORDER BY ts DESC) rn
        FROM dbo.mkt_price_intraday
    ) m ON p.security_id = m.security_id AND m.rn = 1
    ORDER BY unrealized_pnl DESC;
    """,
    
    # [인덱스 13] 미체결 주문 목록 (단순 필터링) - 약 5-8ms
    """
    SELECT TOP 100
        o.order_id,
        o.account_id,
        s.symbol,
        o.side,
        o.order_type,
        o.qty,
        o.price,
        o.status,
        o.create_time
    FROM dbo.ord_order o
    JOIN dbo.ref_security s ON o.security_id = s.security_id
    WHERE o.status IN ('New', 'PartiallyFilled')
    ORDER BY o.create_time DESC;
    """,
    
    # [인덱스 14] 최근 대량 주문 검색 (필터 + 계산) - 약 8-12ms
    """
    SELECT TOP 50
        o.order_id,
        o.account_id,
        s.symbol,
        o.qty,
        o.price,
        o.qty * o.price AS notional,
        o.status,
        o.create_time
    FROM dbo.ord_order o
    JOIN dbo.ref_security s ON o.security_id = s.security_id
    WHERE o.qty * o.price >= 100000
        AND o.create_time >= DATEADD(DAY, -7, GETDATE())
    ORDER BY notional DESC;
    """,
    
    # [인덱스 15] 최근 거래 모니터링 (3-way JOIN + 시간 필터) - 약 200-300ms
    """
    SELECT TOP 500
        e.execution_id,
        o.account_id,
        s.symbol,
        o.side,
        e.exec_qty,
        e.exec_price,
        e.exec_time,
        e.fee,
        e.tax
    FROM dbo.exe_execution e
    JOIN dbo.ord_order o ON e.order_id = o.order_id
    JOIN dbo.ref_security s ON o.security_id = s.security_id
    WHERE e.exec_time >= DATEADD(MINUTE, -30, GETDATE())
    ORDER BY e.exec_time DESC;
    """,
    
    # [인덱스 16] 주문과 체결 내역 함께 조회 (LEFT JOIN) - 약 50-80ms
    """
    SELECT TOP 200
        o.order_id,
        o.account_id,
        s.symbol,
        o.qty,
        o.price,
        o.status,
        e.execution_id,
        e.exec_qty,
        e.exec_price,
        e.exec_time
    FROM dbo.ord_order o
    LEFT JOIN dbo.exe_execution e ON o.order_id = e.order_id
    JOIN dbo.ref_security s ON o.security_id = s.security_id
    WHERE o.create_time >= DATEADD(DAY, -1, GETDATE())
    ORDER BY o.create_time DESC;
    """,
    
    # [인덱스 17] 체결 내역이 있는 주문만 조회 (EXISTS) - 약 40-60ms
    """
    SELECT TOP 100
        o.order_id,
        o.account_id,
        o.status,
        o.qty,
        o.price,
        o.create_time
    FROM dbo.ord_order o
    WHERE o.create_time >= DATEADD(DAY, -7, GETDATE())
      AND EXISTS (SELECT 1 FROM dbo.exe_execution e WHERE e.order_id = o.order_id)
    ORDER BY o.create_time DESC;
    """,
    
    # [인덱스 18] 체결 내역이 있는 주문만 조회 (IN) - 약 50-70ms
    """
    SELECT TOP 100
        o.order_id,
        o.account_id,
        o.status,
        o.qty,
        o.price
    FROM dbo.ord_order o
    WHERE o.create_time >= DATEADD(DAY, -7, GETDATE())
      AND o.order_id IN (SELECT order_id FROM dbo.exe_execution)
    ORDER BY o.create_time DESC;
    """,
    
    # [인덱스 19] 계좌별 현금 잔액 조회 (윈도우 함수) - 약 5-10ms
    """
    SELECT
        account_id,
        currency_code,
        balance_after AS current_balance,
        txn_time AS last_txn_time
    FROM (
        SELECT
            account_id,
            currency_code,
            balance_after,
            txn_time,
            ROW_NUMBER() OVER(PARTITION BY account_id, currency_code 
                             ORDER BY txn_time DESC, cash_ledger_id DESC) as rn
        FROM dbo.acct_cash_ledger
    ) T
    WHERE rn = 1;
    """,
    
    # [인덱스 20] 거래소별 종목 수 및 통계 (간단한 집계) - 약 3-5ms
    """
    SELECT
        ex.exchange_id,
        ex.code AS exchange_code,
        ex.name AS exchange_name,
        COUNT(s.security_id) AS security_count,
        COUNT(CASE WHEN s.delisted_date IS NULL THEN 1 END) AS active_count,
        COUNT(CASE WHEN s.delisted_date IS NOT NULL THEN 1 END) AS delisted_count
    FROM dbo.ref_exchange ex
    LEFT JOIN dbo.ref_security s ON ex.exchange_id = s.exchange_id
    GROUP BY ex.exchange_id, ex.code, ex.name;
    """,
    
    # [인덱스 21] 종목별 최근 가격 이력 (시간 범위 조회) - 약 20-30ms
    """
    SELECT TOP 1000
        security_id,
        ts,
        last_price,
        bid,
        ask,
        volume
    FROM dbo.mkt_price_intraday
    WHERE security_id IN (
        SELECT TOP 10 security_id 
        FROM dbo.ref_security 
        WHERE delisted_date IS NULL 
        ORDER BY NEWID()
    )
    AND ts >= DATEADD(HOUR, -2, GETDATE())
    ORDER BY security_id, ts DESC;
    """,
    
    # [인덱스 22] 고객별 계좌 및 잔액 요약 (다중 JOIN) - 약 15-20ms
    """
    SELECT TOP 100
        c.customer_id,
        c.name AS customer_name,
        c.country_code,
        c.kyc_level,
        COUNT(DISTINCT a.account_id) AS account_count,
        COUNT(DISTINCT CASE WHEN a.closed_at IS NULL THEN a.account_id END) AS active_account_count
    FROM dbo.cust_customer c
    LEFT JOIN dbo.cust_account a ON c.customer_id = a.customer_id
    GROUP BY c.customer_id, c.name, c.country_code, c.kyc_level
    ORDER BY account_count DESC;
    """,
    
    # [인덱스 23] 리스크 노출도 스냅샷 조회 (날짜 필터) - 약 30-50ms
    """
    SELECT TOP 200
        account_id,
        ts,
        gross,
        net,
        var_1d,
        margin_required,
        (gross - net) AS long_short_imbalance
    FROM dbo.risk_exposure_snapshot
    WHERE ts >= DATEADD(DAY, DATEDIFF(DAY, 0, GETDATE()) - 7, 0)
    AND ts < DATEADD(DAY, DATEDIFF(DAY, 0, GETDATE()) + 1, 0)
    ORDER BY ts DESC, gross DESC;
    """,
    # WHERE CAST(ts AS DATE) >= DATEADD(DAY, -7, GETDATE())
    
    # [인덱스 24] 계좌별 주문 소스 분포 (GROUP BY + PIVOT 패턴) - 약 25-35ms
    """
    SELECT
        account_id,
        COUNT(CASE WHEN source = 'api' THEN 1 END) AS api_orders,
        COUNT(CASE WHEN source = 'gui' THEN 1 END) AS gui_orders,
        COUNT(CASE WHEN source = 'fix' THEN 1 END) AS fix_orders,
        COUNT(*) AS total_orders
    FROM dbo.ord_order
    WHERE create_time >= DATEADD(DAY, -7, GETDATE())
    GROUP BY account_id
    HAVING COUNT(*) >= 5
    ORDER BY total_orders DESC;
    """,
    
    # [인덱스 25] 종목 타입별 거래 통계 (복잡한 GROUP BY) - 약 30-40ms
    """
    SELECT
        s.type_code,
        ex.name AS exchange_name,
        COUNT(DISTINCT s.security_id) AS security_count,
        COUNT(DISTINCT o.order_id) AS order_count,
        COUNT(DISTINCT e.execution_id) AS execution_count,
        SUM(e.exec_qty * e.exec_price) AS total_value,
        AVG(e.exec_price) AS avg_price
    FROM dbo.ref_security s
    JOIN dbo.ref_exchange ex ON s.exchange_id = ex.exchange_id
    LEFT JOIN dbo.ord_order o ON s.security_id = o.security_id 
        AND o.create_time >= DATEADD(DAY, -7, GETDATE())
    LEFT JOIN dbo.exe_execution e ON o.order_id = e.order_id
    GROUP BY s.type_code, ex.name
    ORDER BY total_value DESC;
    """,
    
    # [인덱스 26] 마진 계좌 상태 조회 (JOIN + 계산) - 약 5-10ms
    """
    SELECT TOP 50
        m.margin_account_id,
        m.account_id,
        m.credit_limit,
        m.maintenance_margin_rate,
        a.base_currency,
        c.name AS customer_name,
        c.risk_profile
    FROM dbo.cust_margin_account m
    JOIN dbo.cust_account a ON m.account_id = a.account_id
    JOIN dbo.cust_customer c ON a.customer_id = c.customer_id
    WHERE a.closed_at IS NULL;
    """,
    
    # [인덱스 27] 컴플라이언스 경고 현황 (JOIN + 필터) - 약 8-12ms
    """
    SELECT TOP 100
        a.alert_id,
        r.name AS rule_name,
        r.severity,
        a.account_id,
        a.order_id,
        a.ts,
        a.status,
        a.notes
    FROM dbo.cmp_alert a
    JOIN dbo.cmp_rule r ON a.rule_id = r.rule_id
    WHERE a.status = 'Open'
    ORDER BY a.ts DESC;
    """,
    
    # [인덱스 28] 거래 원장 집계 vs 포지션 검증 (복잡한 집계) - 약 100-150ms
    """
    SELECT TOP 100
        t.account_id,
        t.security_id,
        s.symbol,
        SUM(t.qty) AS ledger_qty,
        p.qty AS position_qty,
        SUM(t.qty) - ISNULL(p.qty, 0) AS discrepancy
    FROM dbo.trd_trade_ledger t
    JOIN dbo.ref_security s ON t.security_id = s.security_id
    LEFT JOIN dbo.pos_position p ON t.account_id = p.account_id 
        AND t.security_id = p.security_id
    GROUP BY t.account_id, t.security_id, s.symbol, p.qty
    HAVING ABS(SUM(t.qty) - ISNULL(p.qty, 0)) > 0.01
    ORDER BY discrepancy DESC;
    """,
    
    # [인덱스 29] 종목별 시세 변동성 분석 (EOD 데이터) - 약 15-25ms
    """
    SELECT TOP 50
        s.security_id,
        s.symbol,
        s.type_code,
        COUNT(e.trade_date) AS trading_days,
        AVG(e.[close]) AS avg_close,
        STDEV(e.[close]) AS price_stdev,
        AVG((e.high - e.low) / NULLIF(e.low, 0) * 100) AS avg_daily_range_pct,
        SUM(e.volume) AS total_volume
    FROM dbo.ref_security s
    JOIN dbo.mkt_price_eod e ON s.security_id = e.security_id
    WHERE e.trade_date >= DATEADD(DAY, -30, GETDATE())
    GROUP BY s.security_id, s.symbol, s.type_code
    HAVING COUNT(e.trade_date) >= 20
    ORDER BY price_stdev DESC;
    """
]

# ==============================================================================
# 주석 없이 깔끔하게 정리 (위의 주석 기반 요약):
# ==============================================================================
# 
# 인덱스 | 쿼리 설명                                  | 예상 실행 시간    | 난이도
# -------|--------------------------------------------|--------------------|--------
#   0    | 계좌별 일별 거래 통계 (5-way JOIN + 집계)     | 20-30ms           | 중
#   1    | 거래소별 평균 체결가격 (윈도우 함수)           | 7-10ms            | 중
#   2    | 대용량 테이블 전체 스캔                       | 1,000-2,000ms     | 높음 ⚠️
#   3    | 2-way JOIN (대용량)                        | 5,000-7,000ms     | 매우 높음 ⚠️⚠️
#   4    | 3-way JOIN + ORDER BY (최악!)              | 10,000-14,000ms   | 극도로 높음 ⚠️⚠️⚠️
#   5    | NOT EXISTS (서브쿼리)                       | 600ms             | 중
#   6    | RAND() 함수 (빠름)                         | 30-40ms           | 낮음
#   7    | 주문 체결률 및 슬리피지 분석 (복잡 LEFT JOIN)  | 25-30ms           | 중
#   8    | 포지션 수익률 (LAG, 데이터 없음)             | 0ms               | N/A
#   9    | 당일 거래량 상위 종목 (집계)                 | 15-20ms           | 낮음
#  10    | 당일 거래대금 상위 종목 (계산 집계)           | 15-20ms           | 낮음
#  11    | 전일 종가 대비 등락률 상위 (CTE)             | 10-15ms           | 중
#  12    | 계좌별 포지션 평가 (최신 시세 반영)           | 10-15ms           | 중
#  13    | 미체결 주문 목록 (단순 필터링)                | 5-8ms             | 낮음
#  14    | 최근 대량 주문 검색 (필터 + 계산)            | 8-12ms            | 낮음
#  15    | 최근 거래 모니터링 (3-way JOIN)             | 200-300ms         | 중
#  16    | 주문과 체결 내역 (LEFT JOIN)                | 50-80ms           | 중
#  17    | 체결 내역이 있는 주문 (EXISTS)               | 40-60ms           | 중
#  18    | 체결 내역이 있는 주문 (IN)                  | 50-70ms           | 중
#  19    | 계좌별 현금 잔액 (윈도우 함수)                | 5-10ms            | 낮음
#  20    | 거래소별 종목 통계 (간단 집계)                | 3-5ms             | 낮음
#  21    | 종목별 최근 가격 이력 (범위 조회)             | 20-30ms           | 중
#  22    | 고객별 계좌 요약 (다중 JOIN)                 | 15-20ms           | 중
#  23    | 리스크 노출도 스냅샷 (날짜 필터)              | 30-50ms           | 중
#  24    | 계좌별 주문 소스 분포 (PIVOT 패턴)           | 25-35ms           | 중
#  25    | 종목 타입별 거래 통계 (복잡 GROUP BY)        | 30-40ms           | 중
#  26    | 마진 계좌 상태 조회 (JOIN)                  | 5-10ms            | 낮음
#  27    | 컴플라이언스 경고 현황 (JOIN + 필터)          | 8-12ms            | 낮음
#  28    | 거래 원장 vs 포지션 검증 (복잡 집계)          | 100-150ms         | 높음
#  29    | 종목별 시세 변동성 분석 (통계 함수)           | 15-25ms           | 중
# 
# ==============================================================================

