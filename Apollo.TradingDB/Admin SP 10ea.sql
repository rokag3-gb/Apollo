/* ============================================================
   Admin Queries - 10 Stored Procedures (Read-only)
   Prefix: up_s_query_admin_*
   Author: ChatGPT
   Notes:
     - OFFSET/FETCH 페이지네이션
     - @from_dt/@to_dt, @account_id, @symbol, @status 공통 필터
     - 조인: customers↔accounts↔orders↔trades↔positions↔symbols
   ============================================================ */

---------------------------------------------------------------
-- 1) 심볼별 주문 흐름 요약 (개수/수량/가치, 계좌/고객까지 조인)
---------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_query_admin_order_flow_by_symbol
    @from_dt   datetime2 = NULL,
    @to_dt     datetime2 = NULL,
    @symbol    varchar(32) = NULL,
    @status    varchar(20) = NULL,     -- NEW/FILLED/CANCELED/PARTIAL ...
    @page      int = 1,
    @page_size int = 100
AS
BEGIN
    SET NOCOUNT ON;
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;

    DECLARE @__offset int = (@page-1) * @page_size;

    ;WITH O AS (
        SELECT o.order_id, o.account_id, o.symbol_id, o.side, o.qty, o.price, o.status, o.created_at
        FROM dbo.orders o WITH (NOLOCK)
        WHERE (@status IS NULL OR o.status = @status)
          AND (@from_dt IS NULL OR o.created_at >= @from_dt)
          AND (@to_dt   IS NULL OR o.created_at <  @to_dt)
          AND (@symbol  IS NULL OR EXISTS (SELECT 1 FROM dbo.symbols s WHERE s.symbol_id = o.symbol_id AND s.symbol = @symbol))
    )
    SELECT
        s.symbol,
        COUNT(*)                          AS order_count,
        SUM(CAST(o.qty AS decimal(38,6))) AS total_qty,
        SUM(CAST(COALESCE(o.price,0)*o.qty AS decimal(38,4))) AS notional_estimate,
        MIN(o.created_at)                 AS first_at,
        MAX(o.created_at)                 AS last_at
    FROM O o
    JOIN dbo.symbols s ON s.symbol_id = o.symbol_id
    GROUP BY s.symbol
    ORDER BY order_count DESC, s.symbol
    OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;
END
GO

---------------------------------------------------------------
-- 2) 체결 슬리피지 상세 (주문가 대비 체결가 괴리)
---------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_query_admin_trade_slippage_detail
    @from_dt   datetime2 = NULL,
    @to_dt     datetime2 = NULL,
    @symbol    varchar(32) = NULL,
    @page      int = 1,
    @page_size int = 100
AS
BEGIN
    SET NOCOUNT ON;
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    DECLARE @__offset int = (@page-1) * @page_size;

    SELECT
        t.trade_id, t.executed_at, s.symbol,
        o.order_id, o.side, o.ord_type,
        o.price AS order_price,
        t.price AS exec_price,
        t.qty,
        CAST(t.price - COALESCE(o.price,t.price) AS decimal(19,6))               AS slippage_abs,
        CAST( (t.price - COALESCE(o.price,t.price)) / NULLIF(COALESCE(o.price,t.price),0) AS decimal(19,6)) AS slippage_pct
    FROM dbo.trades t WITH (NOLOCK)
    JOIN dbo.orders o  WITH (NOLOCK) ON o.order_id  = t.order_id
    JOIN dbo.symbols s               ON s.symbol_id = t.symbol_id
    WHERE (@from_dt IS NULL OR t.executed_at >= @from_dt)
      AND (@to_dt   IS NULL OR t.executed_at <  @to_dt)
      AND (@symbol  IS NULL OR s.symbol = @symbol)
    ORDER BY t.executed_at DESC, t.trade_id DESC
    OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;
END
GO

---------------------------------------------------------------
-- 3) 계좌별 익스포저(포지션 시가 평가) + 현금 동시 조회
---------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_query_admin_exposure_by_account
    @account_id bigint = NULL,
    @symbol     varchar(32) = NULL,
    @page       int = 1,
    @page_size  int = 100
AS
BEGIN
    SET NOCOUNT ON;
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    DECLARE @__offset int = (@page-1) * @page_size;

    ;WITH POS AS (
        SELECT p.account_id, p.symbol_id, p.qty, p.avg_price
        FROM dbo.positions p WITH (NOLOCK)
        WHERE (@account_id IS NULL OR p.account_id = @account_id)
    )
    SELECT
        a.account_id,
        c.customer_id, c.name AS customer_name,
        s.symbol,
        p.qty,
        p.avg_price,
        s.last_price,
        CAST(p.qty * s.last_price AS decimal(19,4)) AS market_value,
        a.cash_balance,
        CAST(a.cash_balance + (p.qty * s.last_price) AS decimal(19,4)) AS equity_est
    FROM POS p
    JOIN dbo.accounts  a ON a.account_id = p.account_id
    JOIN dbo.customers c ON c.customer_id = a.customer_id
    JOIN dbo.symbols   s ON s.symbol_id   = p.symbol_id
    WHERE (@symbol IS NULL OR s.symbol = @symbol)
    ORDER BY equity_est DESC, a.account_id
    OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;
END
GO

---------------------------------------------------------------
-- 4) 주문 정체(NEW 상태 오래 지속) 탐지
---------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_query_admin_stale_new_orders
    @older_than_minutes int = 30,
    @symbol varchar(32) = NULL,
    @page      int = 1,
    @page_size int = 100
AS
BEGIN
    SET NOCOUNT ON;
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    DECLARE @__offset int = (@page-1) * @page_size;

    SELECT
        o.order_id, o.created_at, DATEDIFF(MINUTE, o.created_at, SYSUTCDATETIME()) AS age_min,
        s.symbol, o.side, o.ord_type, o.qty, o.price, o.time_in_force,
        a.account_id, c.customer_id, c.name AS customer_name
    FROM dbo.orders o WITH (NOLOCK)
    JOIN dbo.accounts a ON a.account_id = o.account_id
    JOIN dbo.customers c ON c.customer_id = a.customer_id
    JOIN dbo.symbols   s ON s.symbol_id   = o.symbol_id
    WHERE o.status = 'NEW'
      AND DATEDIFF(MINUTE, o.created_at, SYSUTCDATETIME()) >= @older_than_minutes
      AND (@symbol IS NULL OR s.symbol = @symbol)
    ORDER BY age_min DESC, o.created_at
    OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;
END
GO

---------------------------------------------------------------
-- 5) 비활성 종목 보유 포지션 (리스크 이슈 확인)
---------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_query_admin_inactive_symbol_positions
    @page      int = 1,
    @page_size int = 100
AS
BEGIN
    SET NOCOUNT ON;
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    DECLARE @__offset int = (@page-1) * @page_size;

    SELECT
        a.account_id, c.customer_id, c.name AS customer_name,
        s.symbol, s.status AS symbol_status,
        p.qty, p.avg_price, s.last_price,
        CAST(p.qty * s.last_price AS decimal(19,4)) AS market_value
    FROM dbo.positions p WITH (NOLOCK)
    JOIN dbo.accounts  a ON a.account_id = p.account_id
    JOIN dbo.customers c ON c.customer_id = a.customer_id
    JOIN dbo.symbols   s ON s.symbol_id   = p.symbol_id
    WHERE s.status <> 'ACTIVE'
    ORDER BY market_value DESC
    OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;
END
GO

---------------------------------------------------------------
-- 6) 고객 활동 요약 (주문/체결 수, 최근 활동시각)
---------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_query_admin_customer_activity
    @from_dt   datetime2 = NULL,
    @to_dt     datetime2 = NULL,
    @page      int = 1,
    @page_size int = 100
AS
BEGIN
    SET NOCOUNT ON;
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    DECLARE @__offset int = (@page-1) * @page_size;

    ;WITH AO AS (
        SELECT a.account_id, a.customer_id
        FROM dbo.accounts a WITH (NOLOCK)
    ),
    O AS (
        SELECT o.account_id, COUNT(*) AS order_cnt, MAX(o.created_at) AS last_order_at
        FROM dbo.orders o WITH (NOLOCK)
        WHERE (@from_dt IS NULL OR o.created_at >= @from_dt)
          AND (@to_dt   IS NULL OR o.created_at <  @to_dt)
        GROUP BY o.account_id
    ),
    T AS (
        SELECT t.account_id, COUNT(*) AS trade_cnt, MAX(t.executed_at) AS last_trade_at
        FROM dbo.trades t WITH (NOLOCK)
        WHERE (@from_dt IS NULL OR t.executed_at >= @from_dt)
          AND (@to_dt   IS NULL OR t.executed_at <  @to_dt)
        GROUP BY t.account_id
    )
    SELECT
        c.customer_id, c.name AS customer_name,
        COUNT(DISTINCT ao.account_id)                AS account_cnt,
        SUM(COALESCE(o.order_cnt,0))                 AS total_orders,
        SUM(COALESCE(t.trade_cnt,0))                 AS total_trades,
        MAX(COALESCE(o.last_order_at, '1900-01-01')) AS last_order_at,
        MAX(COALESCE(t.last_trade_at, '1900-01-01')) AS last_trade_at
    FROM AO ao
    JOIN dbo.customers c ON c.customer_id = ao.customer_id
    LEFT JOIN O o ON o.account_id = ao.account_id
    LEFT JOIN T t ON t.account_id = ao.account_id
    GROUP BY c.customer_id, c.name
    ORDER BY total_trades DESC, total_orders DESC, c.customer_id
    OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;
END
GO

---------------------------------------------------------------
-- 7) 간이 마진콜 후보 (현금+시가 < 0 추정치)
---------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_query_admin_margin_call_candidates
    @page      int = 1,
    @page_size int = 100
AS
BEGIN
    SET NOCOUNT ON;
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    DECLARE @__offset int = (@page-1) * @page_size;

    ;WITH MV AS (
        SELECT p.account_id,
               SUM(CAST(p.qty * s.last_price AS decimal(19,4))) AS mv
        FROM dbo.positions p WITH (NOLOCK)
        JOIN dbo.symbols s ON s.symbol_id = p.symbol_id
        GROUP BY p.account_id
    )
    SELECT
        a.account_id, c.customer_id, c.name AS customer_name,
        a.cash_balance,
        COALESCE(mv.mv, 0) AS market_value,
        CAST(a.cash_balance + COALESCE(mv.mv,0) AS decimal(19,4)) AS equity_est
    FROM dbo.accounts a WITH (NOLOCK)
    JOIN dbo.customers c ON c.customer_id = a.customer_id
    LEFT JOIN MV mv      ON mv.account_id  = a.account_id
    WHERE (a.cash_balance + COALESCE(mv.mv,0)) < 0
    ORDER BY equity_est ASC
    OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;
END
GO

---------------------------------------------------------------
-- 8) 거래소/심볼 유동성 스냅샷 (체결 건수/거래량/금액)
---------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_query_admin_symbol_liquidity_snapshot
    @from_dt   datetime2 = NULL,
    @to_dt     datetime2 = NULL,
    @symbol    varchar(32) = NULL,
    @page      int = 1,
    @page_size int = 100
AS
BEGIN
    SET NOCOUNT ON;
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    DECLARE @__offset int = (@page-1) * @page_size;

    SELECT
        s.symbol,
        COUNT(*)                                   AS trade_count,
        SUM(CAST(t.qty AS decimal(38,6)))          AS volume,
        SUM(CAST(t.qty * t.price AS decimal(38,4))) AS turnover,
        MIN(t.executed_at)                          AS first_trade_at,
        MAX(t.executed_at)                          AS last_trade_at
    FROM dbo.trades t WITH (NOLOCK)
    JOIN dbo.symbols s ON s.symbol_id = t.symbol_id
    WHERE (@from_dt IS NULL OR t.executed_at >= @from_dt)
      AND (@to_dt   IS NULL OR t.executed_at <  @to_dt)
      AND (@symbol  IS NULL OR s.symbol = @symbol)
    GROUP BY s.symbol
    ORDER BY turnover DESC, volume DESC
    OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;
END
GO

---------------------------------------------------------------
-- 9) 주문-체결 대사(미매칭/부분매칭 식별)
---------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_query_admin_order_trade_reconciliation
    @from_dt   datetime2 = NULL,
    @to_dt     datetime2 = NULL,
    @status    varchar(20) = NULL,   -- 필터: NEW/PARTIAL/FILLED 등
    @page      int = 1,
    @page_size int = 100
AS
BEGIN
    SET NOCOUNT ON;
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    DECLARE @__offset int = (@page-1) * @page_size;

    ;WITH O AS (
        SELECT o.order_id, o.account_id, o.symbol_id, o.side, o.qty AS ord_qty, o.status, o.created_at
        FROM dbo.orders o WITH (NOLOCK)
        WHERE (@from_dt IS NULL OR o.created_at >= @from_dt)
          AND (@to_dt   IS NULL OR o.created_at <  @to_dt)
          AND (@status  IS NULL OR o.status = @status)
    ),
    TE AS (
        SELECT t.order_id, SUM(CAST(t.qty AS decimal(38,6))) AS exec_qty
        FROM dbo.trades t WITH (NOLOCK)
        GROUP BY t.order_id
    )
    SELECT
        o.order_id, s.symbol, o.side, o.ord_qty,
        COALESCE(te.exec_qty, 0) AS exec_qty,
        (o.ord_qty - COALESCE(te.exec_qty,0)) AS remaining_qty,
        o.status, o.created_at,
        a.account_id, c.customer_id, c.name AS customer_name
    FROM O o
    LEFT JOIN TE te ON te.order_id = o.order_id
    JOIN dbo.symbols  s ON s.symbol_id = o.symbol_id
    JOIN dbo.accounts a ON a.account_id = o.account_id
    JOIN dbo.customers c ON c.customer_id = a.customer_id
    ORDER BY remaining_qty DESC, o.created_at DESC
    OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;
END
GO

---------------------------------------------------------------
-- 10) 감사 이벤트 요약(최근 활동, 유형/참조별 탑-K)
---------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_query_admin_audit_event_summary
    @from_dt   datetime2 = NULL,
    @to_dt     datetime2 = NULL,
    @event_like nvarchar(100) = NULL,  -- 예: 'PROC.%' / 'ORDER.%'
    @page      int = 1,
    @page_size int = 100
AS
BEGIN
    SET NOCOUNT ON;
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    DECLARE @__offset int = (@page-1) * @page_size;

    ;WITH A AS (
        SELECT log_id, event_type, ref_id, created_at, created_by
        FROM dbo.sys_audit_log WITH (NOLOCK)
        WHERE (@from_dt IS NULL OR created_at >= @from_dt)
          AND (@to_dt   IS NULL OR created_at <  @to_dt)
          AND (@event_like IS NULL OR event_type LIKE @event_like)
    ),
    G AS (
        SELECT event_type,
               COUNT(*) AS cnt,
               MIN(created_at) AS first_at,
               MAX(created_at) AS last_at
        FROM A
        GROUP BY event_type
    )
    SELECT *
    FROM G
    ORDER BY cnt DESC, last_at DESC
    OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;
END
GO
