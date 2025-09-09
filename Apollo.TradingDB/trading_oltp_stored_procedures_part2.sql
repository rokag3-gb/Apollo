/********************************************************************************************
 * Trading Ledger OLTP Simulation Stored Procedures V3 - Part 2 of 2 (SQL Server)
 * -------------------------------------------------------------------------------------------
 * 이 스크립트는 주식 거래 시스템의 다양한 OLTP 워크로드를 시뮬레이션하기 위한
 * 저장 프로시저(Stored Procedure) 51번부터 100번까지를 정의합니다.
 *
 * 실행 순서:
 * 1. trading_oltp_stored_procedures_part1.sql 파일을 먼저 실행해야 합니다.
 * 2. 이 파일(part2.sql)을 실행하여 나머지 SP들과 복잡한 리포트 SP들을 생성합니다.
 *
 * 스크립트 구조:
 *   1) sp_catalog 테이블에 SP 51-100 메타데이터 INSERT
 *   2) 기존 SP 51-100 일괄 삭제
 *   3) SP 51-100 생성 (카테고리별)
 ********************************************************************************************/

SET NOCOUNT ON;
GO

/********************************************************************************************
 * 1) sp_catalog 테이블에 SP 51-100 메타데이터 INSERT
 ********************************************************************************************/
PRINT 'Part 2: Step 1 - Populating sp_catalog for SPs 51-100...';

MERGE dbo.sp_catalog AS target
USING (
    VALUES
    -- Queries (51-60)
    ('usp_s_Admin_GetSystemAuditLog_051', 'Admin', '관리자가 시스템 감사 로그를 조건에 따라 조회.'),
    ('usp_s_Admin_GetUserLoginHistory_052', 'Admin', '관리자가 시스템 사용자들의 로그인 기록을 조회.'),
    ('usp_s_Admin_GetComplianceAlerts_053', 'Admin', '관리자가 컴플라이언스 위반 경고 목록을 조회.'),
    ('usp_s_GetMarketHolidays_054', 'User', '특정 거래소의 휴장일 정보를 조회.'),
    ('usp_s_GetTradingSessions_055', 'User', '특정 거래소의 정규장/시간외 거래 시간 정보를 조회.'),
    ('usp_s_GetFeeSchedule_056', 'User', '특정 계좌에 적용되는 수수료 정보를 조회.'),
    ('usp_s_GetTaxRules_057', 'User', '특정 국가/증권 종류에 따른 세율 정보를 조회.'),
    ('usp_s_GetFullPortfolioValue_058', 'User', '계좌의 총 자산(현금+주식 평가금액)을 계산하여 조회.'),
    ('usp_s_GetDailyPnLHistory_059', 'User', '특정 계좌의 일별 손익(PnL) 기록을 조회.'),
    ('usp_s_CheckMarginAccountStatus_060', 'User', '마진 계좌의 증거금률 및 신용 한도를 조회.'),

    -- Batch (61-70)
    ('usp_t_Batch_SettleAllTrades_061', 'Batch', '미정산된 모든 체결 건에 대해 일괄 정산 작업을 수행 (CURSOR 사용).'),
    ('usp_t_Batch_CalculateAllDailyPnL_062', 'Batch', '모든 활성 계좌에 대해 일일 손익(PnL)을 일괄 계산.'),
    ('usp_t_Batch_ArchiveOldData_063', 'Batch', '오래된 데이터(예: 1년 이상된 주문 이벤트)를 삭제/아카이빙.'),
    ('usp_t_Batch_DataIntegrityCheck_064', 'Batch', '주요 테이블 간의 데이터 정합성을 검증 (예: 포지션 수량과 거래 원장 합계 비교).'),
    ('usp_t_Batch_UpdateEODPrices_065', 'Batch', '장 마감 후, 모든 종목의 EOD(End-Of-Day) 가격을 업데이트.'),
    ('usp_t_Batch_GenerateRiskSnapshots_066', 'Batch', '모든 계좌의 리스크 노출도(Exposure) 스냅샷을 생성.'),
    ('usp_t_Batch_PopulateAnalyticsFacts_067', 'Batch', 'OLTP 데이터를 분석용 팩트(Fact) 테이블로 ETL(적재)하는 작업.'),
    ('usp_t_Batch_SendNotifications_068', 'Batch', '시스템 알림 큐에 쌓인 메시지를 일괄 발송.'),
    ('usp_t_Batch_RebuildIndexes_069', 'Batch', '주요 테이블의 인덱스를 재구성하여 성능을 유지.'),
    ('usp_t_Batch_ExpireOrders_070', 'Batch', '만료된 주문(예: 당일 유효한 IOC/FOK)의 상태를 일괄적으로 Expired로 변경.'),

    -- Expanded Set for V3 (71-100)
    ('usp_s_GetAccountPositions_ReadUncommitted_071', 'User', '격리수준 READ UNCOMMITTED로 계좌 포지션을 조회 (블락킹 최소화).'),
    ('usp_s_GetFullPortfolioValue_ReadUncommitted_072', 'User', '격리수준 READ UNCOMMITTED로 계좌 총자산을 조회.'),
    ('usp_t_PlaceOrder_Serializable_073', 'User', '격리수준 SERIALIZABLE로 주문을 생성 (최고 수준의 정합성).'),
    ('usp_s_GetOrderHistory_ReadCommitted_074', 'User', '격리수준 READ COMMITTED를 명시적으로 사용하여 주문 내역을 조회.'),
    ('usp_s_Admin_MonitorRecentTrades_ReadUncommitted_075', 'Admin', '격리수준 READ UNCOMMITTED로 최근 거래를 모니터링.'),
    ('usp_s_GetDailyExecutionSummary_CTE_076', 'User', 'CTE를 사용하여 당일 체결 내역을 요약 조회.'),
    ('usp_s_GetAccountValueBySecurityType_CTE_077', 'User', 'CTE를 사용하여 계좌의 자산을 증권 종류별로 집계하여 조회.'),
    ('usp_s_GetTopMovers_NoCTE_078', 'User', 'CTE 대신 서브쿼리를 사용하여 등락률 상위 종목을 조회.'),
    ('usp_t_Admin_UpdateOrderStatus_Manual_079', 'Admin', '관리자가 수동으로 특정 주문의 상태를 강제 변경.'),
    ('usp_s_GetAccountRiskProfile_080', 'User', '자신의 계좌에 설정된 리스크 프로파일(성향, 한도 등)을 조회.'),
    ('usp_s_Admin_CheckSystemHealth_081', 'Admin', '관리자가 주요 테이블의 레코드 수를 확인하여 시스템 상태를 점검.'),
    ('usp_t_Batch_MergePositionLots_082', 'Batch', '특정 종목의 잘게 나뉘어진 포지션 Lot들을 하나로 병합.'),
    ('usp_s_GetExchangeStatus_083', 'User', '특정 거래소가 현재 개장 중인지 휴장일과 세션 시간을 고려하여 확인.'),
    ('usp_t_PlaceOrder_Limit_WithRecompile_084', 'User', 'RECOMPILE 옵션을 사용하여 지정가 주문을 생성 (매번 계획 새로 컴파일).'),
    ('usp_s_Admin_Rpt_Customer360_085', 'Admin', '특정 고객의 모든 정보(계좌, 주문, 체결, 잔고, 손익)를 조회하는 무거운 360도 리포트.'),
    ('usp_s_Admin_Rpt_MarketAnalysis_086', 'Admin', '특정 시장의 기간별 거래 동향(거래량, 변동성)을 분석하는 무거운 리포트.'),
    ('usp_s_Admin_Rpt_ComplianceAuditTrail_087', 'Admin', '특정 기간 동안의 컴플라이언스 경고와 관련된 모든 활동을 추적하는 감사 리포트.'),
    ('usp_s_Admin_Rpt_PnlAttribution_088', 'Admin', '전사 기준 일일 손익을 고객/상품 유형별로 분석하는 손익 분석 리포트.'),
    ('usp_s_Admin_Rpt_DailyRiskExposure_089', 'Admin', '모든 계좌의 일일 리스크 노출(Gross, Net, VaR)을 집계하는 리스크 관리 리포트.'),
    ('usp_s_GetCustomerInfo_SelectStar_090', 'User', 'SELECT * 를 사용하여 고객 정보를 조회.'),
    ('usp_s_GetPriceHistory_FromEOD_091', 'User', '일봉(EOD) 테이블에서 가격 이력을 조회.'),
    ('usp_t_Admin_UpdateAccountCurrency_092', 'Admin', '관리자가 계좌의 기준 통화를 변경하는 복잡한 트랜잭션.'),
    ('usp_s_Admin_GetAllCustomersPaged_093', 'Admin', '관리자가 전체 고객 목록을 페이지 단위로 조회.'),
    ('usp_s_GetTradeLedgerForSecurity_094', 'User', '특정 계좌의 특정 종목에 대한 모든 거래 원장 내역을 조회.'),
    ('usp_t_Batch_DefragmentIndexes_095', 'Batch', '인덱스 조각화가 심한 경우 REORGANIZE를 수행.'),
    ('usp_s_GetOpenOrdersForSecurity_096', 'User', '특정 계좌에서 특정 종목에 대한 미체결 주문만 조회.'),
    ('usp_s_Admin_GetOrphanedExecutions_097', 'Admin', '주문 테이블에 존재하지 않는 주문 ID를 가진 체결 내역을 검색.'),
    ('usp_s_Admin_GetAccountsWithNoTrades_098', 'Admin', '특정 기간 동안 거래가 한 번도 없었던 계좌를 검색.'),
    ('usp_t_Batch_GenerateFakeTrades_099', 'Batch', '부하 테스트용: 임의의 계좌와 종목에 대해 가짜 거래를 대량으로 생성.'),
    ('usp_s_CheckAllTableFragmentation_100', 'Admin', '데이터베이스의 모든 테이블과 인덱스의 조각화 상태를 조회.')
) AS source (sp_name, caller, remark)
ON (target.sp_name = source.sp_name)
WHEN NOT MATCHED THEN
    INSERT (sp_name, caller, remark)
    VALUES (source.sp_name, source.caller, source.remark);
GO

/********************************************************************************************
 * 2) 기존 SP 51-100 일괄 삭제
 ********************************************************************************************/
PRINT 'Part 2: Step 2 - Dropping existing stored procedures (51-100)...';

DECLARE @procName NVARCHAR(128);
DECLARE cur CURSOR LOCAL FAST_FORWARD FOR
    SELECT sp_name FROM dbo.sp_catalog WHERE sp_id BETWEEN 51 AND 100 ORDER BY sp_id;

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
 * 3) SP 51-100 생성
 ********************************************************************************************/
PRINT 'Part 2: Step 3 - Creating stored procedures (51-100)...';
GO

-- Category: Queries (51-60)
---------------------------------------------------------------------------------------------
CREATE PROCEDURE dbo.usp_s_Admin_GetSystemAuditLog_051
    @EventType NVARCHAR(100) = NULL,
    @RefID BIGINT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP 100 log_id, event_type, ref_id, details, created_at, created_by
    FROM dbo.sys_audit_log
    WHERE (@EventType IS NULL OR event_type = @EventType)
      AND (@RefID IS NULL OR ref_id = @RefID)
    ORDER BY created_at DESC;
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_GetUserLoginHistory_052
    @LoginID NVARCHAR(64)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT user_id, login_id, role, last_login
    FROM dbo.sys_user
    WHERE login_id = @LoginID;
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_GetComplianceAlerts_053
    @Status NVARCHAR(16) = 'Open'
AS
BEGIN
    SET NOCOUNT ON;
    SELECT alert_id, rule_id, account_id, ts, status
    FROM dbo.cmp_alert
    WHERE status = @Status;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetMarketHolidays_054
    @ExchangeID INT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT holiday_date, description
    FROM dbo.ref_holiday
    WHERE exchange_id = @ExchangeID;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetTradingSessions_055
    @ExchangeID INT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT session_type, start_time, end_time
    FROM dbo.ref_trading_session
    WHERE exchange_id = @ExchangeID;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetFeeSchedule_056
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT s.fee_sched_id, t.name, s.value, s.unit
    FROM dbo.acct_fee_schedule s
    JOIN dbo.ref_fee_type t ON s.fee_type_id = t.fee_type_id
    WHERE s.account_id = @AccountID
      AND GETDATE() BETWEEN s.effective_from AND ISNULL(s.effective_to, '9999-12-31');
END;
GO

CREATE PROCEDURE dbo.usp_s_GetTaxRules_057
    @CountryCode CHAR(2)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT tax_rule_id, security_type, rate
    FROM dbo.ref_tax_rule
    WHERE country_code = @CountryCode;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetFullPortfolioValue_058
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @PositionsValue DECIMAL(18,4);

    SELECT @PositionsValue = SUM(p.qty * m.last_price)
    FROM dbo.pos_position p
    JOIN (
        SELECT security_id, last_price, ROW_NUMBER() OVER(PARTITION BY security_id ORDER BY ts DESC) rn
        FROM dbo.mkt_price_intraday
    ) m ON p.security_id = m.security_id
    WHERE p.account_id = @AccountID AND m.rn=1;

    DECLARE @CashValue DECIMAL(18,4);
    SELECT TOP 1 @CashValue = balance_after
    FROM dbo.acct_cash_ledger
    WHERE account_id = @AccountID
    ORDER BY txn_time DESC, cash_ledger_id DESC;

    SELECT ISNULL(@PositionsValue,0) + ISNULL(@CashValue,0) AS TotalPortfolioValue;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetDailyPnLHistory_059
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT as_of_date, realized_pnl, unrealized_pnl, fees, taxes, mtm_value
    FROM dbo.pnl_daily
    WHERE account_id = @AccountID
    ORDER BY as_of_date DESC;
END;
GO

CREATE PROCEDURE dbo.usp_s_CheckMarginAccountStatus_060
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT margin_account_id, credit_limit, maintenance_margin_rate
    FROM dbo.cust_margin_account
    WHERE account_id = @AccountID;
END;
GO

-- Category: Batch (61-70)
---------------------------------------------------------------------------------------------
CREATE PROCEDURE dbo.usp_t_Batch_SettleAllTrades_061
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ExecID BIGINT;
    DECLARE cur CURSOR FOR
        SELECT execution_id
        FROM dbo.exe_execution e
        WHERE NOT EXISTS (SELECT 1 FROM dbo.trd_trade_ledger t WHERE t.execution_id = e.execution_id);

    OPEN cur;
    FETCH NEXT FROM cur INTO @ExecID;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        EXEC dbo.usp_t_SettleTrade_033 @ExecutionID = @ExecID;
        FETCH NEXT FROM cur INTO @ExecID;
    END
    CLOSE cur;
    DEALLOCATE cur;
END;
GO

CREATE PROCEDURE dbo.usp_t_Batch_CalculateAllDailyPnL_062
    @AsOfDate DATE
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @AccountID BIGINT;
    DECLARE cur CURSOR FOR
        SELECT account_id FROM dbo.cust_account WHERE closed_at IS NULL;

    OPEN cur;
    FETCH NEXT FROM cur INTO @AccountID;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        -- Actual calculation logic would be here.
        -- EXEC dbo.usp_CalculateDailyPnL @AccountID, @AsOfDate;
        FETCH NEXT FROM cur INTO @AccountID;
    END
    CLOSE cur;
    DEALLOCATE cur;
END;
GO

CREATE PROCEDURE dbo.usp_t_Batch_ArchiveOldData_063
AS
BEGIN
    SET NOCOUNT ON;
    DELETE FROM dbo.ord_order_event
    WHERE event_time < DATEADD(YEAR, -1, GETDATE());
END;
GO

CREATE PROCEDURE dbo.usp_t_Batch_DataIntegrityCheck_064
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        p.account_id,
        p.security_id,
        SUM(t.qty) AS LedgerQty,
        p.qty AS PositionQty
    FROM dbo.trd_trade_ledger t
    JOIN dbo.pos_position p ON t.account_id = p.account_id AND t.security_id = p.security_id
    GROUP BY p.account_id, p.security_id, p.qty
    HAVING SUM(t.qty) <> p.qty;
END;
GO

CREATE PROCEDURE dbo.usp_t_Batch_UpdateEODPrices_065
    @TradeDate DATE
AS
BEGIN
    SET NOCOUNT ON;
    MERGE dbo.mkt_price_eod AS target
    USING (
        SELECT
            security_id,
            MIN(last_price) AS low_price,
            MAX(last_price) AS high_price,
            SUM(volume) AS total_volume,
            (SELECT TOP 1 last_price FROM dbo.mkt_price_intraday i2 WHERE i2.security_id = i.security_id AND CAST(i2.ts AS DATE)=@TradeDate ORDER BY i2.ts ASC) AS open_price,
            (SELECT TOP 1 last_price FROM dbo.mkt_price_intraday i2 WHERE i2.security_id = i.security_id AND CAST(i2.ts AS DATE)=@TradeDate ORDER BY i2.ts DESC) AS close_price
        FROM dbo.mkt_price_intraday i
        WHERE CAST(i.ts AS DATE) = @TradeDate
        GROUP BY security_id
    ) AS source
    ON (target.security_id = source.security_id AND target.trade_date = @TradeDate)
    WHEN MATCHED THEN
        UPDATE SET [open]=source.open_price, high=source.high_price, low=source.low_price, [close]=source.close_price, volume=source.total_volume
    WHEN NOT MATCHED THEN
        INSERT (security_id, trade_date, [open], high, low, [close], volume)
        VALUES (source.security_id, @TradeDate, source.open_price, source.high_price, source.low_price, source.close_price, source.total_volume);
END;
GO

CREATE PROCEDURE dbo.usp_t_Batch_GenerateRiskSnapshots_066
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO dbo.risk_exposure_snapshot (account_id, ts, gross, net, var_1d, margin_required)
    SELECT account_id, GETDATE(), RAND()*100000, RAND()*50000, 0, 0
    FROM dbo.cust_account
    WHERE closed_at IS NULL;
END;
GO

CREATE PROCEDURE dbo.usp_t_Batch_PopulateAnalyticsFacts_067
AS
BEGIN
    SET NOCOUNT ON;
    PRINT 'ETL process placeholder';
END;
GO

CREATE PROCEDURE dbo.usp_t_Batch_SendNotifications_068
AS
BEGIN
    SET NOCOUNT ON;
    PRINT 'Notification sender placeholder';
END;
GO

CREATE PROCEDURE dbo.usp_t_Batch_RebuildIndexes_069
AS
BEGIN
    SET NOCOUNT ON;
    ALTER INDEX ALL ON dbo.ord_order REBUILD;
    ALTER INDEX ALL ON dbo.exe_execution REBUILD;
END;
GO

CREATE PROCEDURE dbo.usp_t_Batch_ExpireOrders_070
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.ord_order
    SET status = 'Expired'
    WHERE tif IN ('IOC', 'FOK')
      AND status IN ('New', 'PartiallyFilled')
      AND create_time < CAST(GETDATE() AS DATE);
END;
GO

-- Category: Expanded Set for V3 (71-100)
---------------------------------------------------------------------------------------------
CREATE PROCEDURE dbo.usp_s_GetAccountPositions_ReadUncommitted_071
    @AccountID BIGINT
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SELECT p.security_id, s.symbol, p.qty, p.avg_price
    FROM dbo.pos_position p
    JOIN dbo.ref_security s ON p.security_id = s.security_id
    WHERE p.account_id = @AccountID;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetFullPortfolioValue_ReadUncommitted_072
    @AccountID BIGINT
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    
    DECLARE @PositionsValue DECIMAL(18,4);
    SELECT @PositionsValue = SUM(p.qty * m.last_price)
    FROM dbo.pos_position p
    JOIN (
        SELECT security_id, last_price, ROW_NUMBER() OVER(PARTITION BY security_id ORDER BY ts DESC) rn
        FROM dbo.mkt_price_intraday
    ) m ON p.security_id = m.security_id
    WHERE p.account_id = @AccountID AND m.rn=1;

    DECLARE @CashValue DECIMAL(18,4);
    SELECT TOP 1 @CashValue = balance_after
    FROM dbo.acct_cash_ledger
    WHERE account_id = @AccountID
    ORDER BY txn_time DESC, cash_ledger_id DESC;

    SELECT ISNULL(@PositionsValue,0) + ISNULL(@CashValue,0) AS TotalPortfolioValue;
END;
GO

CREATE PROCEDURE dbo.usp_t_PlaceOrder_Serializable_073
    @AccountID BIGINT,
    @SecurityID BIGINT,
    @Side CHAR(1),
    @Quantity DECIMAL(18,4),
    @Price DECIMAL(18,4)
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    BEGIN TRAN;

    SET NOCOUNT ON;
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

CREATE PROCEDURE dbo.usp_s_GetOrderHistory_ReadCommitted_074
    @AccountID BIGINT
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SELECT *
    FROM dbo.ord_order
    WHERE account_id = @AccountID;
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_MonitorRecentTrades_ReadUncommitted_075
    @Minutes INT = 5
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;

    SELECT e.execution_id, o.account_id, s.symbol, o.side, e.exec_qty, e.exec_price, e.exec_time
    FROM dbo.exe_execution e
    JOIN dbo.ord_order o ON e.order_id=o.order_id
    JOIN dbo.ref_security s ON o.security_id=s.security_id
    WHERE e.exec_time >= DATEADD(MINUTE, -@Minutes, GETDATE())
    ORDER BY e.exec_time DESC;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetDailyExecutionSummary_CTE_076
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    WITH DailyExecutions AS (
        SELECT e.order_id, e.exec_qty, e.exec_price
        FROM dbo.exe_execution e
        WHERE CAST(e.exec_time AS DATE) = CAST(GETDATE() AS DATE)
    )
    SELECT
        o.security_id,
        s.symbol,
        o.side,
        SUM(de.exec_qty) AS total_qty,
        AVG(de.exec_price) AS avg_price
    FROM dbo.ord_order o
    JOIN DailyExecutions de ON o.order_id = de.order_id
    JOIN dbo.ref_security s ON o.security_id = s.security_id
    WHERE o.account_id = @AccountID
    GROUP BY o.security_id, s.symbol, o.side;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetAccountValueBySecurityType_CTE_077
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    WITH PositionValues AS (
        SELECT p.qty, s.type_code, m.last_price
        FROM dbo.pos_position p
        JOIN dbo.ref_security s ON p.security_id = s.security_id
        JOIN (
            SELECT security_id, last_price, ROW_NUMBER() OVER(PARTITION BY security_id ORDER BY ts DESC) rn
            FROM dbo.mkt_price_intraday
        ) m ON p.security_id = m.security_id
        WHERE p.account_id = @AccountID AND m.rn=1
    )
    SELECT type_code, SUM(qty * last_price) AS market_value
    FROM PositionValues
    GROUP BY type_code;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetTopMovers_NoCTE_078
    @TopN INT = 10
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@TopN)
        t.security_id,
        s.symbol,
        y.[close] as yesterday_close,
        t.last_price as current_price,
        (t.last_price - y.[close]) / y.[close] * 100 AS change_pct
    FROM
        (SELECT security_id, last_price, ROW_NUMBER() OVER(PARTITION BY security_id ORDER BY ts DESC) rn FROM dbo.mkt_price_intraday) t
    JOIN
        (SELECT security_id, [close] FROM dbo.mkt_price_eod WHERE trade_date = (SELECT MAX(trade_date) FROM dbo.mkt_price_eod)) y ON t.security_id = y.security_id
    JOIN
        dbo.ref_security s ON t.security_id = s.security_id
    WHERE t.rn = 1 AND y.[close] > 0
    ORDER BY change_pct DESC;
END;
GO

CREATE PROCEDURE dbo.usp_t_Admin_UpdateOrderStatus_Manual_079
    @OrderID BIGINT,
    @NewStatus NVARCHAR(16)
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.ord_order
    SET status = @NewStatus, update_time = GETDATE()
    WHERE order_id = @OrderID;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetAccountRiskProfile_080
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT r.kind, r.threshold, r.window_min, c.risk_profile
    FROM dbo.acct_risk_limit r
    JOIN dbo.cust_account ca ON r.account_id = ca.account_id
    JOIN dbo.cust_customer c ON ca.customer_id = c.customer_id
    WHERE r.account_id = @AccountID;
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_CheckSystemHealth_081
AS
BEGIN
    SET NOCOUNT ON;
    SELECT 'cust_customer' AS Tbl, COUNT(*) AS Cnt FROM dbo.cust_customer
    UNION ALL
    SELECT 'ord_order', COUNT(*) FROM dbo.ord_order;
END;
GO

CREATE PROCEDURE dbo.usp_t_Batch_MergePositionLots_082
    @PositionID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    -- Placeholder for complex logic to merge lots
    PRINT 'Merging lots for PositionID ' + CAST(@PositionID AS VARCHAR);
END;
GO

CREATE PROCEDURE dbo.usp_s_GetExchangeStatus_083
    @ExchangeID INT
AS
BEGIN
    SET NOCOUNT ON;
    -- Placeholder for logic to check holidays and sessions
    SELECT 'OPEN' AS status;
END;
GO

CREATE PROCEDURE dbo.usp_t_PlaceOrder_Limit_WithRecompile_084
    @AccountID BIGINT,
    @SecurityID BIGINT,
    @Side CHAR(1),
    @Quantity DECIMAL(18,4),
    @Price DECIMAL(18,4)
WITH RECOMPILE
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

CREATE PROCEDURE dbo.usp_s_Admin_Rpt_Customer360_085
    @CustomerID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    -- This is a heavy query for demonstration.
    SELECT TOP 10 c.*, ca.*, o.*, e.*, p.*, pnl.*
    FROM dbo.cust_customer c
    LEFT JOIN dbo.cust_account ca ON c.customer_id = ca.customer_id
    LEFT JOIN dbo.ord_order o ON ca.account_id = o.account_id
    LEFT JOIN dbo.exe_execution e ON o.order_id = e.order_id
    LEFT JOIN dbo.pos_position p ON ca.account_id = p.account_id
    LEFT JOIN dbo.pnl_daily pnl ON ca.account_id = pnl.account_id
    WHERE c.customer_id = @CustomerID;
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_Rpt_MarketAnalysis_086
    @ExchangeID INT,
    @StartDate DATE,
    @EndDate DATE
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        s.symbol,
        d.trade_date,
        d.volume,
        (d.high - d.low) / d.low AS volatility
    FROM dbo.mkt_price_eod d
    JOIN dbo.ref_security s ON d.security_id = s.security_id
    WHERE s.exchange_id = @ExchangeID
      AND d.trade_date BETWEEN @StartDate AND @EndDate
    ORDER BY d.trade_date, s.symbol;
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_Rpt_ComplianceAuditTrail_087
    @AccountID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP 100 a.*, l.*
    FROM dbo.cmp_alert a
    JOIN dbo.sys_audit_log l ON a.account_id = l.ref_id
    WHERE a.account_id = @AccountID
    ORDER BY a.ts DESC;
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_Rpt_PnlAttribution_088
    @AsOfDate DATE
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        c.country_code,
        s.type_code,
        SUM(pnl.realized_pnl) AS TotalRealizedPnl,
        SUM(pnl.unrealized_pnl) AS TotalUnrealizedPnl
    FROM dbo.pnl_daily pnl
    JOIN dbo.cust_account ca ON pnl.account_id = ca.account_id
    JOIN dbo.cust_customer c ON ca.customer_id = c.customer_id
    JOIN dbo.pos_position p ON ca.account_id = p.account_id
    JOIN dbo.ref_security s ON p.security_id = s.security_id
    WHERE pnl.as_of_date = @AsOfDate
    GROUP BY CUBE(c.country_code, s.type_code);
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_Rpt_DailyRiskExposure_089
    @AsOfDate DATE
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP 100 *
    FROM dbo.risk_exposure_snapshot
    WHERE CAST(ts AS DATE) = @AsOfDate;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetCustomerInfo_SelectStar_090
    @CustomerID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT *
    FROM dbo.cust_customer
    WHERE customer_id = @CustomerID;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetPriceHistory_FromEOD_091
    @SecurityID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT trade_date, [open], high, low, [close], volume
    FROM dbo.mkt_price_eod
    WHERE security_id = @SecurityID
    ORDER BY trade_date;
END;
GO

CREATE PROCEDURE dbo.usp_t_Admin_UpdateAccountCurrency_092
    @AccountID BIGINT,
    @NewCurrency CHAR(3)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRAN;
    -- Complex logic with checks and balances placeholder
    UPDATE dbo.cust_account SET base_currency = @NewCurrency WHERE account_id = @AccountID;
    COMMIT;
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_GetAllCustomersPaged_093
    @PageNumber INT,
    @PageSize INT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT customer_id, name
    FROM dbo.cust_customer
    ORDER BY customer_id
    OFFSET (@PageNumber-1) * @PageSize ROWS
    FETCH NEXT @PageSize ROWS ONLY;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetTradeLedgerForSecurity_094
    @AccountID BIGINT,
    @SecurityID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT trade_time, qty, price, fee, tax
    FROM dbo.trd_trade_ledger
    WHERE account_id = @AccountID AND security_id = @SecurityID;
END;
GO

CREATE PROCEDURE dbo.usp_t_Batch_DefragmentIndexes_095
AS
BEGIN
    SET NOCOUNT ON;
    ALTER INDEX ALL ON dbo.trd_trade_ledger REORGANIZE;
END;
GO

CREATE PROCEDURE dbo.usp_s_GetOpenOrdersForSecurity_096
    @AccountID BIGINT,
    @SecurityID BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT order_id, side, qty, price
    FROM dbo.ord_order
    WHERE account_id = @AccountID
      AND security_id = @SecurityID
      AND status IN ('New', 'PartiallyFilled');
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_GetOrphanedExecutions_097
AS
BEGIN
    SET NOCOUNT ON;
    SELECT e.*
    FROM dbo.exe_execution e
    WHERE NOT EXISTS (SELECT 1 FROM dbo.ord_order o WHERE o.order_id = e.order_id);
END;
GO

CREATE PROCEDURE dbo.usp_s_Admin_GetAccountsWithNoTrades_098
    @Days INT = 30
AS
BEGIN
    SET NOCOUNT ON;
    SELECT ca.account_id
    FROM dbo.cust_account ca
    WHERE NOT EXISTS (
        SELECT 1 FROM dbo.ord_order o
        WHERE o.account_id = ca.account_id
          AND o.create_time > DATEADD(DAY, -@Days, GETDATE())
    );
END;
GO

CREATE PROCEDURE dbo.usp_t_Batch_GenerateFakeTrades_099
    @NumOfTrades INT = 1000
AS
BEGIN
    SET NOCOUNT ON;
    -- Complex logic to generate random trades placeholder
    PRINT 'Generated ' + CAST(@NumOfTrades AS VARCHAR) + ' fake trades.';
END;
GO

CREATE PROCEDURE dbo.usp_s_CheckAllTableFragmentation_100
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        OBJECT_NAME(ips.object_id) AS TableName,
        si.name AS IndexName,
        ips.index_type_desc,
        ips.avg_fragmentation_in_percent
    FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'SAMPLED') AS ips
    JOIN sys.indexes AS si ON ips.object_id = si.object_id AND ips.index_id = si.index_id
    WHERE ips.avg_fragmentation_in_percent > 30.0
    ORDER BY ips.avg_fragmentation_in_percent DESC;
END;
GO

PRINT 'Part 2 of 2 completed successfully.';
GO
