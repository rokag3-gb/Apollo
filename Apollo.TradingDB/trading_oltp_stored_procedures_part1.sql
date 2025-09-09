/********************************************************************************************
 * Trading Ledger OLTP Simulation Stored Procedures V3 - Part 1 of 2 (SQL Server)
 * -------------------------------------------------------------------------------------------
 * 이 스크립트는 주식 거래 시스템의 다양한 OLTP 워크로드를 시뮬레이션하기 위한
 * 저장 프로시저(Stored Procedure) 1번부터 50번까지를 정의합니다.
 *
 * 실행 순서:
 * 1. 이 파일(part1.sql)을 먼저 실행하여 sp_catalog 테이블과 기본 SP들을 생성합니다.
 * 2. trading_oltp_stored_procedures_part2.sql 파일을 실행하여 나머지 SP들을 생성합니다.
 *
 * 스크립트 구조:
 *   1) sp_catalog 테이블 생성
 *   2) sp_catalog 테이블에 SP 1-50 메타데이터 INSERT
 *   3) 기존 SP 1-50 일괄 삭제
 *   4) SP 1-50 생성 (카테고리별)
 ********************************************************************************************/

SET NOCOUNT ON;
GO

/********************************************************************************************
 * 1) sp_catalog 테이블 생성
 ********************************************************************************************/
PRINT 'Part 1: Step 1 - Creating sp_catalog table...';

IF OBJECT_ID('dbo.sp_catalog', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.sp_catalog (
        sp_id INT IDENTITY(1,1) PRIMARY KEY,
        sp_name NVARCHAR(128) NOT NULL UNIQUE,
        caller NVARCHAR(20) NOT NULL, -- 'User', 'Admin', 'Batch'
        remark NVARCHAR(500) NOT NULL
    );
END
GO

/********************************************************************************************
 * 2) sp_catalog 테이블에 SP 1-50 메타데이터 INSERT
 ********************************************************************************************/
PRINT 'Part 1: Step 2 - Populating sp_catalog for SPs 1-50...';

-- 혹시 모를 중복을 피하기 위해 MERGE 사용
MERGE dbo.sp_catalog AS target
USING (
    VALUES
    -- Market Data (1-8)
    ('usp_t_UpdateSecurityPrice_001', 'Batch', '특정 종목의 현재가를 갱신 (기본).'),
    ('usp_t_UpdateMarketPricesBulk_002', 'Batch', '다수 종목의 시세를 랜덤하게 일괄 갱신.'),
    ('usp_s_GetSecurityPrice_003', 'User', '특정 종목의 최신 시세를 조회 (기본).'),
    ('usp_s_GetSecurityPriceWithNolock_004', 'User', '특정 종목의 최신 시세를 NOLOCK 힌트를 사용하여 조회 (Dirty Read).'),
    ('usp_s_GetMultipleSecurityPrices_005', 'User', '쉼표로 구분된 여러 종목 ID를 받아 시세를 한 번에 조회.'),
    ('usp_s_GetPriceHistory_006', 'User', '특정 종목의 지정된 기간 동안의 분봉 데이터를 조회.'),
    ('usp_s_GetTopMovers_007', 'User', '전일 종가 대비 등락률 상위 N개 종목 조회.'),
    ('usp_s_GetWorstMovers_008', 'User', '전일 종가 대비 등락률 하위 N개 종목 조회.'),

    -- Customer & Account (9-20)
    ('usp_t_RegisterCustomer_009', 'User', '신규 고객 정보를 등록.'),
    ('usp_t_OpenAccount_010', 'User', '기존 고객의 신규 계좌를 개설.'),
    ('usp_t_DepositCash_011', 'User', '특정 계좌에 현금을 입금. 트랜잭션 처리 포함.'),
    ('usp_t_WithdrawCash_012', 'User', '특정 계좌에서 현금을 출금. 잔고 확인 및 트랜잭션 처리 포함.'),
    ('usp_s_GetCustomerInfo_013', 'User', '고객 ID로 고객의 기본 정보를 조회.'),
    ('usp_s_GetCustomerAccounts_014', 'User', '고객 ID로 해당 고객이 소유한 모든 계좌 목록을 조회.'),
    ('usp_s_GetAccountCashBalance_015', 'User', '특정 계좌의 통화별 현금 잔액을 조회.'),
    ('usp_t_Admin_UpdateCustomerKYC_016', 'Admin', '관리자가 특정 고객의 KYC 레벨을 변경.'),
    ('usp_s_Admin_SearchCustomers_017', 'Admin', '관리자가 이름, 국가 등으로 고객을 검색 (LIKE, RECOMPILE 힌트 사용).'),
    ('usp_s_Admin_GetFullAccountDetails_018', 'Admin', '관리자가 계좌의 모든 상세 정보(고객정보, 잔고, 포지션)를 JOIN하여 조회.'),
    ('usp_s_Batch_GetActiveAccounts_019', 'Batch', '배치 작업용: 현재 활성화된 모든 계좌 목록을 조회.'),
    ('usp_t_Admin_ToggleAccountStatus_020', 'Admin', '관리자가 특정 계좌를 활성/비활성 처리.'),

    -- Trading (21-45)
    ('usp_t_PlaceOrder_Limit_021', 'User', '지정가(LIMIT) 매수/매도 주문을 생성.'),
    ('usp_t_PlaceOrder_Market_022', 'User', '시장가(MARKET) 매수/매도 주문을 생성하고 즉시 체결 시뮬레이션.'),
    ('usp_t_CancelOrder_023', 'User', '미체결 주문을 취소.'),
    ('usp_s_GetOrderStatus_024', 'User', '특정 주문의 현재 상태를 조회.'),
    ('usp_s_GetAccountPositions_025', 'User', '특정 계좌의 현재 보유 종목(포지션) 목록을 조회 (기본).'),
    ('usp_s_GetAccountPositions_TempTable_026', 'User', '임시 테이블(#)을 사용하여 특정 계좌의 포지션 목록을 조회.'),
    ('usp_s_GetAccountPositions_TableVar_027', 'User', '테이블 변수(@)를 사용하여 특정 계좌의 포지션 목록을 조회.'),
    ('usp_s_GetOpenOrders_028', 'User', '특정 계좌의 미체결(New, PartiallyFilled) 주문 목록을 조회.'),
    ('usp_s_GetOrderHistory_029', 'User', '특정 계좌의 지정된 기간 동안의 모든 주문 내역을 조회.'),
    ('usp_s_GetOrderHistory_SelectStar_030', 'User', 'SELECT * 를 사용하여 특정 계좌의 주문 내역을 조회.'),
    ('usp_s_GetExecutionHistory_031', 'User', '특정 주문에 대한 모든 체결 내역을 조회.'),
    ('usp_s_GetDailyExecutionSummary_032', 'User', '특정 계좌의 당일 체결 내역을 요약하여 조회.'),
    ('usp_t_SettleTrade_033', 'Batch', '단일 체결 건에 대한 정산 처리(원장 기록, 현금/포지션 업데이트).'),
    ('usp_s_Admin_FindLargeOrders_034', 'Admin', '관리자가 지정된 금액 이상의 대량 주문을 검색.'),
    ('usp_s_Admin_MonitorRecentTrades_035', 'Admin', '관리자가 최근 N분 동안의 모든 거래를 실시간으로 모니터링.'),
    ('usp_s_Admin_CheckRiskLimit_036', 'Admin', '관리자가 특정 계좌의 리스크 한도(일일 손실 등) 위반 여부를 확인.'),
    ('usp_t_Admin_ManualExecution_037', 'Admin', '관리자가 수동으로 체결 데이터를 입력.'),
    ('usp_s_GetOrderAndExecutions_038', 'User', '주문 한 건과 그에 따른 체결 내역을 함께 조회 (JOIN).'),
    ('usp_s_GetOrderAndExecutions_LoopJoin_039', 'User', 'LOOP JOIN 힌트를 사용하여 주문과 체결 내역을 조회.'),
    ('usp_s_GetOrderAndExecutions_HashJoin_040', 'User', 'HASH JOIN 힌트를 사용하여 주문과 체결 내역을 조회.'),
    ('usp_s_GetOrdersWithExists_041', 'User', 'EXISTS 절을 사용하여 체결 내역이 있는 주문만 조회.'),
    ('usp_s_GetOrdersWithIn_042', 'User', 'IN 절을 사용하여 체결 내역이 있는 주문만 조회.'),
    ('usp_s_GetOrdersBySource_043', 'Admin', '주문 소스(api, gui, fix)별로 주문 목록을 조회.'),
    ('usp_t_PlaceOrder_Complex_044', 'User', '여러 옵션(TIF, Stop Price 등)을 포함하는 복합 주문 생성.'),
    ('usp_s_GetPositionLots_045', 'User', '특정 포지션의 개별 Lot(취득 내역) 정보를 조회.'),

    -- Queries (46-50)
    ('usp_s_GetMostTradedSecurities_046', 'User', '당일 거래량 상위 N개 종목을 조회.'),
    ('usp_s_GetHighestTurnoverSecurities_047', 'User', '당일 거래대금 상위 N개 종목을 조회.'),
    ('usp_s_SearchSecurityBySymbol_048', 'User', '종목명(symbol)으로 종목 정보를 검색 (LIKE).'),
    ('usp_s_GetAccountCashLedger_Paged_049', 'User', '특정 계좌의 입출금 내역을 페이지 단위로 조회 (OFFSET/FETCH).'),
    ('usp_s_GetCorporateActions_050', 'User', '특정 종목의 권리락(배당, 분할 등) 정보를 조회.')
) AS source (sp_name, caller, remark)
ON (target.sp_name = source.sp_name)
WHEN NOT MATCHED THEN
    INSERT (sp_name, caller, remark)
    VALUES (source.sp_name, source.caller, source.remark);
GO

/********************************************************************************************
 * 3) 기존 SP 1-50 일괄 삭제
 ********************************************************************************************/
PRINT 'Part 1: Step 3 - Dropping existing stored procedures (1-50)...';

DECLARE @procName NVARCHAR(128);
DECLARE cur CURSOR LOCAL FAST_FORWARD FOR
    SELECT sp_name FROM dbo.sp_catalog WHERE sp_id BETWEEN 1 AND 50 ORDER BY sp_id;

OPEN cur;
FETCH NEXT FROM cur INTO @procName;

WHILE @@FETCH_STATUS = 0
BEGIN
    IF OBJECT_ID(@procName, 'P') IS NOT NULL
    BEGIN
        EXEC('DROP PROCEDURE ' + @procName);
    END
    FETCH NEXT FROM cur INTO @procName;
END

CLOSE cur;
DEALLOCATE cur;
GO


/********************************************************************************************
 * 4) SP 1-50 생성
 ********************************************************************************************/
PRINT 'Part 1: Step 4 - Creating stored procedures (1-50)...';
GO

-- Category: Market Data (1-8)
---------------------------------------------------------------------------------------------

CREATE PROCEDURE dbo.usp_t_UpdateSecurityPrice_001
    @SecurityID BIGINT,
    @NewPrice DECIMAL(18, 6),
    @TradeVolume BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO dbo.mkt_price_intraday (security_id, ts, last_price, volume)
    VALUES (@SecurityID, SYSUTCDATETIME(), @NewPrice, @TradeVolume);
END;
GO

CREATE PROCEDURE dbo.usp_t_UpdateMarketPricesBulk_002
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE TOP (100) p
    SET
        last_price = last_price * (1 + (CAST(CRYPT_GEN_RANDOM(2) AS SMALLINT) % 400 - 200) / 10000.0),
        ts = SYSUTCDATETIME(),
        volume = volume + (ABS(CHECKSUM(NEWID())) % 1000)
    FROM dbo.mkt_price_intraday p
    WHERE p.ts = (SELECT MAX(ts) FROM dbo.mkt_price_intraday i WHERE i.security_id = p.security_id);
END;
GO

CREATE PROCEDURE dbo.usp_s_GetSecurityPrice_003
    @SecurityID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP 1 security_id, ts, last_price, bid, ask, volume
    FROM dbo.mkt_price_intraday
    WHERE security_id = @SecurityID
    ORDER BY ts DESC;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetSecurityPriceWithNolock_004
    @SecurityID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP 1 security_id, ts, last_price, bid, ask, volume
    FROM dbo.mkt_price_intraday WITH (NOLOCK)
    WHERE security_id = @SecurityID
    ORDER BY ts DESC;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetMultipleSecurityPrices_005
    @SecurityIDs VARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT p.security_id, p.ts, p.last_price
    FROM dbo.mkt_price_intraday p
    INNER JOIN (
        SELECT security_id, MAX(ts) AS max_ts
        FROM dbo.mkt_price_intraday
        WHERE security_id IN (SELECT value FROM STRING_SPLIT(@SecurityIDs, ','))
        GROUP BY security_id
    ) AS latest ON p.security_id = latest.security_id AND p.ts = latest.max_ts;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetPriceHistory_006
    @SecurityID BIGINT,
    @StartTime DATETIME2,
    @EndTime DATETIME2
AS
BEGIN
    SET NOCOUNT ON;
    SELECT security_id, ts, last_price, volume
    FROM dbo.mkt_price_intraday
    WHERE security_id = @SecurityID AND ts BETWEEN @StartTime AND @EndTime
    ORDER BY ts;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetTopMovers_007
    @TopN INT = 10
AS
BEGIN
    SET NOCOUNT ON;
    WITH YesterdayPrice AS (
        SELECT security_id, [close]
        FROM dbo.mkt_price_eod
        WHERE trade_date = (SELECT MAX(trade_date) FROM dbo.mkt_price_eod)
    ),
    TodayPrice AS (
        SELECT security_id, last_price, ROW_NUMBER() OVER(PARTITION BY security_id ORDER BY ts DESC) as rn
        FROM dbo.mkt_price_intraday
    )
    SELECT TOP (@TopN) t.security_id, s.symbol, y.[close] as yesterday_close, t.last_price as current_price,
           (t.last_price - y.[close]) / y.[close] * 100 AS change_pct
    FROM TodayPrice t
    JOIN YesterdayPrice y ON t.security_id = y.security_id
    JOIN dbo.ref_security s ON t.security_id = s.security_id
    WHERE t.rn = 1 AND y.[close] > 0
    ORDER BY change_pct DESC;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetWorstMovers_008
    @TopN INT = 10
AS
BEGIN
    SET NOCOUNT ON;
    WITH YesterdayPrice AS (
        SELECT security_id, [close]
        FROM dbo.mkt_price_eod
        WHERE trade_date = (SELECT MAX(trade_date) FROM dbo.mkt_price_eod)
    ),
    TodayPrice AS (
        SELECT security_id, last_price, ROW_NUMBER() OVER(PARTITION BY security_id ORDER BY ts DESC) as rn
        FROM dbo.mkt_price_intraday
    )
    SELECT TOP (@TopN) t.security_id, s.symbol, y.[close] as yesterday_close, t.last_price as current_price,
           (t.last_price - y.[close]) / y.[close] * 100 AS change_pct
    FROM TodayPrice t
    JOIN YesterdayPrice y ON t.security_id = y.security_id
    JOIN dbo.ref_security s ON t.security_id = s.security_id
    WHERE t.rn = 1 AND y.[close] > 0
    ORDER BY change_pct ASC;
END;
GO

-- Category: Customer & Account (9-20)
---------------------------------------------------------------------------------------------

CREATE PROCEDURE dbo.usp_t_RegisterCustomer_009
    @Name NVARCHAR(100),
    @CountryCode CHAR(2),
    @BirthDate DATE,
    @CustomerID BIGINT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO dbo.cust_customer (name, birth, country_code, kyc_level, risk_profile)
    VALUES (@Name, @BirthDate, @CountryCode, 1, N'NORMAL');
    SET @CustomerID = SCOPE_IDENTITY();
END;
GO

CREATE PROCEDURE dbo.usp_t_OpenAccount_010
    @CustomerID BIGINT,
    @BaseCurrency CHAR(3),
    @AccountType NVARCHAR(16),
    @AccountID BIGINT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    IF NOT EXISTS (SELECT 1 FROM dbo.cust_customer WHERE customer_id = @CustomerID)
    BEGIN
        RAISERROR('Customer not found.', 16, 1);
        RETURN;
    END
    INSERT INTO dbo.cust_account (customer_id, base_currency, account_type)
    VALUES (@CustomerID, @BaseCurrency, @AccountType);
    SET @AccountID = SCOPE_IDENTITY();
END;
GO

CREATE PROCEDURE dbo.usp_t_DepositCash_011
    @AccountID BIGINT,
    @Amount DECIMAL(18, 4)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRANSACTION;
    
    DECLARE @Currency CHAR(3);
    SELECT @Currency = base_currency FROM dbo.cust_account WHERE account_id = @AccountID;
    
    IF @Currency IS NULL
    BEGIN
        RAISERROR('Account not found.', 16, 1);
        ROLLBACK;
        RETURN;
    END
    
    IF @Amount <= 0
    BEGIN
        RAISERROR('Deposit must be positive.', 16, 1);
        ROLLBACK;
        RETURN;
    END
    
    DECLARE @BalanceAfter DECIMAL(18, 4);
    
    SELECT TOP 1 @BalanceAfter = balance_after
    FROM dbo.acct_cash_ledger
    WHERE account_id = @AccountID AND currency_code = @Currency
    ORDER BY txn_time DESC, cash_ledger_id DESC;
    
    SET @BalanceAfter = ISNULL(@BalanceAfter, 0) + @Amount;
    
    INSERT INTO dbo.acct_cash_ledger (account_id, currency_code, txn_type, amount, balance_after)
    VALUES (@AccountID, @Currency, 'DEPOSIT', @Amount, @BalanceAfter);
    
    COMMIT;
END;
GO

CREATE PROCEDURE dbo.usp_t_WithdrawCash_012
    @AccountID BIGINT,
    @Amount DECIMAL(18, 4)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRANSACTION;

    DECLARE @Currency CHAR(3);
    SELECT @Currency = base_currency FROM dbo.cust_account WHERE account_id = @AccountID;

    IF @Currency IS NULL
    BEGIN
        RAISERROR('Account not found.', 16, 1);
        ROLLBACK; RETURN;
    END

    IF @Amount <= 0
    BEGIN
        RAISERROR('Withdrawal must be positive.', 16, 1);
        ROLLBACK; RETURN;
    END

    DECLARE @CurrentBalance DECIMAL(18, 4);
    SELECT TOP 1 @CurrentBalance = balance_after
    FROM dbo.acct_cash_ledger
    WHERE account_id = @AccountID AND currency_code = @Currency
    ORDER BY txn_time DESC, cash_ledger_id DESC;

    IF ISNULL(@CurrentBalance, 0) < @Amount
    BEGIN
        RAISERROR('Insufficient funds.', 16, 1);
        ROLLBACK; RETURN;
    END

    DECLARE @BalanceAfter DECIMAL(18, 4) = ISNULL(@CurrentBalance, 0) - @Amount;

    INSERT INTO dbo.acct_cash_ledger (account_id, currency_code, txn_type, amount, balance_after)
    VALUES (@AccountID, @Currency, 'WITHDRAW', -@Amount, @BalanceAfter);

    COMMIT;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetCustomerInfo_013
    @CustomerID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT customer_id, name, birth, country_code, kyc_level, risk_profile
    FROM dbo.cust_customer
    WHERE customer_id = @CustomerID;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetCustomerAccounts_014
    @CustomerID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT account_id, base_currency, account_type, opened_at, closed_at
    FROM dbo.cust_account
    WHERE customer_id = @CustomerID;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetAccountCashBalance_015
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT account_id, currency_code, MAX(balance_after) as current_balance
    FROM (
        SELECT account_id, currency_code, balance_after,
               ROW_NUMBER() OVER(PARTITION BY currency_code ORDER BY txn_time DESC, cash_ledger_id DESC) as rn
        FROM dbo.acct_cash_ledger
        WHERE account_id = @AccountID
    ) T
    WHERE rn = 1
    GROUP BY account_id, currency_code;
END;
GO

CREATE PROCEDURE dbo.usp_t_Admin_UpdateCustomerKYC_016
    @CustomerID BIGINT,
    @NewKycLevel TINYINT
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.cust_customer
    SET kyc_level = @NewKycLevel
    WHERE customer_id = @CustomerID;
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_SearchCustomers_017
    @SearchName NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT customer_id, name, country_code
    FROM dbo.cust_customer
    WHERE name LIKE '%' + @SearchName + '%'
    OPTION (RECOMPILE);
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_GetFullAccountDetails_018
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT c.*, a.*, m.credit_limit
    FROM dbo.cust_account a
    JOIN dbo.cust_customer c ON a.customer_id = c.customer_id
    LEFT JOIN dbo.cust_margin_account m ON a.account_id = m.account_id
    WHERE a.account_id = @AccountID;
END;
GO

CREATE PROCEDURE dbo.usp_s_Batch_GetActiveAccounts_019
AS
BEGIN
    SET NOCOUNT ON;
    SELECT account_id, customer_id, base_currency
    FROM dbo.cust_account
    WHERE closed_at IS NULL;
END;
GO

CREATE PROCEDURE dbo.usp_t_Admin_ToggleAccountStatus_020
    @AccountID BIGINT,
    @IsActive BIT
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.cust_account
    SET closed_at = CASE WHEN @IsActive = 0 THEN SYSUTCDATETIME() ELSE NULL END
    WHERE account_id = @AccountID;
END;
GO

-- Category: Trading (21-45)
---------------------------------------------------------------------------------------------

CREATE PROCEDURE dbo.usp_t_PlaceOrder_Limit_021
    @AccountID BIGINT,
    @SecurityID BIGINT,
    @Side CHAR(1),
    @Quantity DECIMAL(18,4),
    @Price DECIMAL(18,4)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRAN;
    IF @Side = 'S'
    BEGIN
        DECLARE @Qty DECIMAL(18,4) = 0;
        SELECT @Qty = ISNULL(qty,0)
        FROM dbo.pos_position
        WHERE account_id = @AccountID AND security_id = @SecurityID;

        IF @Qty < @Quantity
        BEGIN
            RAISERROR('Insufficient position.', 16, 1);
            ROLLBACK;
            RETURN;
        END;
    END
    INSERT INTO dbo.ord_order (account_id, security_id, side, order_type, qty, price, status)
    VALUES (@AccountID, @SecurityID, @Side, 'LIMIT', @Quantity, @Price, 'New');
    COMMIT;
END;
GO

CREATE PROCEDURE dbo.usp_t_PlaceOrder_Market_022
    @AccountID BIGINT,
    @SecurityID BIGINT,
    @Side CHAR(1),
    @Quantity DECIMAL(18,4)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRAN;
    DECLARE @OrderID BIGINT;
    INSERT INTO dbo.ord_order (account_id, security_id, side, order_type, qty, status)
    VALUES (@AccountID, @SecurityID, @Side, 'MARKET', @Quantity, 'New');
    SET @OrderID = SCOPE_IDENTITY();

    DECLARE @ExecPrice DECIMAL(18, 4);
    SELECT TOP 1 @ExecPrice = last_price
    FROM dbo.mkt_price_intraday
    WHERE security_id = @SecurityID
    ORDER BY ts DESC;

    INSERT INTO dbo.exe_execution(order_id, exec_time, exec_qty, exec_price)
    VALUES (@OrderID, SYSUTCDATETIME(), @Quantity, @ExecPrice);

    UPDATE dbo.ord_order SET status = 'Filled' WHERE order_id = @OrderID;
    COMMIT;
END;
GO

CREATE PROCEDURE dbo.usp_t_CancelOrder_023
    @OrderID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @Status NVARCHAR(16);
    SELECT @Status = status FROM dbo.ord_order WHERE order_id = @OrderID;

    IF @Status IN ('New', 'PartiallyFilled')
    BEGIN
        UPDATE dbo.ord_order SET status = 'Cancelled' WHERE order_id = @OrderID;
        INSERT INTO dbo.ord_order_event (order_id, event_type) VALUES (@OrderID, 'Cancel');
    END
    ELSE
    BEGIN
        RAISERROR('Order cannot be cancelled.', 16, 1);
        RETURN;
    END
END;
GO

CREATE PROCEDURE dbo.usp_s_GetOrderStatus_024
    @OrderID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT order_id, status, qty, price, create_time
    FROM dbo.ord_order
    WHERE order_id = @OrderID;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetAccountPositions_025
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT p.security_id, s.symbol, p.qty, p.avg_price
    FROM dbo.pos_position p
    JOIN dbo.ref_security s ON p.security_id = s.security_id
    WHERE p.account_id = @AccountID;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetAccountPositions_TempTable_026
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    CREATE TABLE #pos(security_id BIGINT, qty DECIMAL(18,4), avg_price DECIMAL(18,6));

    INSERT INTO #pos (security_id, qty, avg_price)
    SELECT security_id, qty, avg_price
    FROM dbo.pos_position
    WHERE account_id = @AccountID;

    SELECT p.security_id, s.symbol, p.qty, p.avg_price
    FROM #pos p
    JOIN dbo.ref_security s ON p.security_id = s.security_id;

    DROP TABLE #pos;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetAccountPositions_TableVar_027
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @pos TABLE(security_id BIGINT, qty DECIMAL(18,4), avg_price DECIMAL(18,6));

    INSERT INTO @pos (security_id, qty, avg_price)
    SELECT security_id, qty, avg_price
    FROM dbo.pos_position
    WHERE account_id = @AccountID;

    SELECT p.security_id, s.symbol, p.qty, p.avg_price
    FROM @pos p
    JOIN dbo.ref_security s ON p.security_id = s.security_id;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetOpenOrders_028
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT order_id, security_id, side, qty, price, status, create_time
    FROM dbo.ord_order
    WHERE account_id = @AccountID AND status IN ('New', 'PartiallyFilled');
END;
GO

CREATE PROCEDURE dbo.usp_s_GetOrderHistory_029
    @AccountID BIGINT,
    @StartDate DATE,
    @EndDate DATE
AS
BEGIN
    SET NOCOUNT ON;
    SELECT order_id, security_id, side, qty, price, status, create_time
    FROM dbo.ord_order
    WHERE account_id = @AccountID AND create_time BETWEEN @StartDate AND @EndDate;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetOrderHistory_SelectStar_030
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT *
    FROM dbo.ord_order
    WHERE account_id = @AccountID;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetExecutionHistory_031
    @OrderID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT execution_id, exec_time, exec_qty, exec_price, fee, tax
    FROM dbo.exe_execution
    WHERE order_id = @OrderID;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetDailyExecutionSummary_032
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT o.security_id, s.symbol, o.side, SUM(e.exec_qty) total_qty, AVG(e.exec_price) avg_price
    FROM dbo.exe_execution e
    JOIN dbo.ord_order o ON e.order_id = o.order_id
    JOIN dbo.ref_security s ON o.security_id = s.security_id
    WHERE o.account_id = @AccountID AND CAST(e.exec_time AS DATE) = CAST(GETDATE() AS DATE)
    GROUP BY o.security_id, s.symbol, o.side;
END;
GO

CREATE PROCEDURE dbo.usp_t_SettleTrade_033
    @ExecutionID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRAN;

    DECLARE @AccountID BIGINT, @SecID BIGINT, @Side CHAR(1), @Qty DECIMAL(18,4), @Price DECIMAL(18,4), @Fee DECIMAL(18,4), @Tax DECIMAL(18,4);

    SELECT @AccountID=o.account_id, @SecID=o.security_id, @Side=o.side, @Qty=e.exec_qty, @Price=e.exec_price, @Fee=e.fee, @Tax=e.tax
    FROM dbo.exe_execution e
    JOIN dbo.ord_order o ON e.order_id=o.order_id
    WHERE e.execution_id=@ExecutionID;

    IF @@ROWCOUNT=0
    BEGIN
        ROLLBACK;
        RETURN;
    END

    INSERT INTO dbo.trd_trade_ledger(account_id, security_id, trade_time, qty, price, fee, tax, execution_id)
    VALUES (@AccountID, @SecID, GETDATE(), CASE @Side WHEN 'B' THEN @Qty ELSE -@Qty END, @Price, @Fee, @Tax, @ExecutionID);

    COMMIT;
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_FindLargeOrders_034
    @MinNotional DECIMAL(18,2)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT o.order_id, o.account_id, s.symbol, o.qty, o.price, o.qty * o.price AS notional
    FROM dbo.ord_order o
    JOIN dbo.ref_security s ON o.security_id=s.security_id
    WHERE o.qty * o.price >= @MinNotional;
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_MonitorRecentTrades_035
    @Minutes INT = 5
AS
BEGIN
    SET NOCOUNT ON;
    SELECT e.execution_id, o.account_id, s.symbol, o.side, e.exec_qty, e.exec_price, e.exec_time
    FROM dbo.exe_execution e
    JOIN dbo.ord_order o ON e.order_id=o.order_id
    JOIN dbo.ref_security s ON o.security_id=s.security_id
    WHERE e.exec_time >= DATEADD(MINUTE, -@Minutes, GETDATE())
    ORDER BY e.exec_time DESC;
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_CheckRiskLimit_036
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT limit_id, kind, threshold, active
    FROM dbo.acct_risk_limit
    WHERE account_id = @AccountID AND active = 1;
END;
GO

CREATE PROCEDURE dbo.usp_t_Admin_ManualExecution_037
    @OrderID BIGINT,
    @ExecQty DECIMAL(18,4),
    @ExecPrice DECIMAL(18,4)
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO dbo.exe_execution(order_id, exec_time, exec_qty, exec_price, venue)
    VALUES (@OrderID, GETDATE(), @ExecQty, @ExecPrice, 'MANUAL');
END;
GO

CREATE PROCEDURE dbo.usp_s_GetOrderAndExecutions_038
    @OrderID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT o.*, e.*
    FROM dbo.ord_order o
    LEFT JOIN dbo.exe_execution e ON o.order_id = e.order_id
    WHERE o.order_id = @OrderID;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetOrderAndExecutions_LoopJoin_039
    @OrderID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT o.*, e.*
    FROM dbo.ord_order o
    INNER LOOP JOIN dbo.exe_execution e ON o.order_id = e.order_id
    WHERE o.order_id = @OrderID;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetOrderAndExecutions_HashJoin_040
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT o.order_id, e.execution_id
    FROM dbo.ord_order o
    INNER HASH JOIN dbo.exe_execution e ON o.order_id = e.order_id
    WHERE o.account_id = @AccountID;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetOrdersWithExists_041
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT order_id, status
    FROM dbo.ord_order o
    WHERE account_id = @AccountID
      AND EXISTS (SELECT 1 FROM dbo.exe_execution e WHERE e.order_id = o.order_id);
END;
GO

CREATE PROCEDURE dbo.usp_s_GetOrdersWithIn_042
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT order_id, status
    FROM dbo.ord_order
    WHERE account_id = @AccountID
      AND order_id IN (SELECT order_id FROM dbo.exe_execution);
END;
GO

CREATE PROCEDURE dbo.usp_s_GetOrdersBySource_043
    @Source NVARCHAR(16)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP 100 order_id, account_id, status
    FROM dbo.ord_order
    WHERE source = @Source;
END;
GO

CREATE PROCEDURE dbo.usp_t_PlaceOrder_Complex_044
    @AccountID BIGINT,
    @SecurityID BIGINT,
    @Side CHAR(1),
    @OrderType NVARCHAR(16),
    @Tif NVARCHAR(8),
    @Quantity DECIMAL(18,4),
    @Price DECIMAL(18,4) = NULL,
    @ParentOrderID BIGINT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO dbo.ord_order (account_id, security_id, side, order_type, tif, qty, price, parent_order_id, status)
    VALUES (@AccountID, @SecurityID, @Side, @OrderType, @Tif, @Quantity, @Price, @ParentOrderID, 'New');
END;
GO

CREATE PROCEDURE dbo.usp_s_GetPositionLots_045
    @PositionID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT lot_id, open_time, open_qty, open_price, remaining_qty
    FROM dbo.pos_position_lot
    WHERE position_id = @PositionID;
END;
GO

-- Category: Queries (46-50)
---------------------------------------------------------------------------------------------
CREATE PROCEDURE dbo.usp_s_GetMostTradedSecurities_046
    @TopN INT = 10
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@TopN) s.security_id, s.symbol, SUM(e.exec_qty) AS total_volume
    FROM dbo.exe_execution e
    JOIN dbo.ord_order o ON e.order_id = o.order_id
    JOIN dbo.ref_security s ON o.security_id = s.security_id
    WHERE CAST(e.exec_time AS DATE) = CAST(GETDATE() AS DATE)
    GROUP BY s.security_id, s.symbol
    ORDER BY total_volume DESC;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetHighestTurnoverSecurities_047
    @TopN INT = 10
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@TopN) s.security_id, s.symbol, SUM(e.exec_qty * e.exec_price) AS total_turnover
    FROM dbo.exe_execution e
    JOIN dbo.ord_order o ON e.order_id = o.order_id
    JOIN dbo.ref_security s ON o.security_id = s.security_id
    WHERE CAST(e.exec_time AS DATE) = CAST(GETDATE() AS DATE)
    GROUP BY s.security_id, s.symbol
    ORDER BY total_turnover DESC;
END;
GO

CREATE PROCEDURE dbo.usp_s_SearchSecurityBySymbol_048
    @Symbol VARCHAR(32)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT security_id, symbol, isin, type_code
    FROM dbo.ref_security
    WHERE symbol LIKE @Symbol + '%';
END;
GO

CREATE PROCEDURE dbo.usp_s_GetAccountCashLedger_Paged_049
    @AccountID BIGINT,
    @PageNumber INT = 1,
    @PageSize INT = 20
AS
BEGIN
    SET NOCOUNT ON;
    SELECT cash_ledger_id, txn_time, txn_type, amount, balance_after
    FROM dbo.acct_cash_ledger
    WHERE account_id = @AccountID
    ORDER BY txn_time DESC, cash_ledger_id DESC
    OFFSET (@PageNumber - 1) * @PageSize ROWS
    FETCH NEXT @PageSize ROWS ONLY;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetCorporateActions_050
    @SecurityID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT ca_id, ca_type, ex_date, pay_date, ratio, amount
    FROM dbo.ref_corporate_action
    WHERE security_id = @SecurityID;
END;
GO

PRINT 'Part 1 of 2 completed successfully.';
GO
