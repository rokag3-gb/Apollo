/* =====================================================================================
   Service Broker Load Generator (Caller별 3-Queue/Service 구성) - Re-runnable Script
   - user/admin/batch 3개 큐 & 서비스
   - 공용 Message Type/Contract
   - 워커 4종(up__work_worker_core + 3래퍼), 빌더 3종, 엔큐어 3종
   ===================================================================================== */
SET NOCOUNT ON;
GO

/* (선택) Broker 활성화: 필요 시 주석 해제
BEGIN TRY
    DECLARE @is_broker_on BIT = (SELECT CASE WHEN is_broker_enabled=1 THEN 1 ELSE 0 END
                                 FROM sys.databases WHERE name = DB_NAME());
    IF @is_broker_on = 0
        EXEC('ALTER DATABASE [' + DB_NAME() + '] SET ENABLE_BROKER WITH ROLLBACK IMMEDIATE;');
END TRY BEGIN CATCH END CATCH;
GO
*/

/* =========================================================================
   1) Message Type & Contract (DROP IF EXISTS → CREATE)
   ========================================================================= */
/*
IF EXISTS (SELECT 1 FROM sys.service_message_types WHERE name = N'//work/message')
    DROP MESSAGE TYPE [//work/message];
GO
CREATE MESSAGE TYPE [//work/message] VALIDATION = NONE;
GO

IF EXISTS (SELECT 1 FROM sys.service_contracts WHERE name = N'work_contract')
    DROP CONTRACT [work_contract];
GO
CREATE CONTRACT [work_contract] ([//work/message] SENT BY INITIATOR);
GO
*/
/* =========================================================================
   2) Services & Queues (user/admin/batch)  — 존재검사 정확히
   - SERVICE: sys.services
   - QUEUE  : OBJECT_ID(...,'SQ')
   ========================================================================= */
-- USER
IF EXISTS (SELECT 1 FROM sys.services WHERE name = N'work_service_user')
    DROP SERVICE work_service_user;
GO
IF OBJECT_ID(N'work_queue_user','SQ') IS NOT NULL
    DROP QUEUE work_queue_user;
GO
CREATE QUEUE  work_queue_user;
GO
CREATE SERVICE work_service_user ON QUEUE dbo.work_queue_user ([work_contract]);
GO

-- ADMIN
IF EXISTS (SELECT 1 FROM sys.services WHERE name = N'work_service_admin')
    DROP SERVICE work_service_admin;
GO
IF OBJECT_ID(N'work_queue_admin','SQ') IS NOT NULL
    DROP QUEUE work_queue_admin;
GO
CREATE QUEUE  work_queue_admin;
GO
CREATE SERVICE work_service_admin ON QUEUE dbo.work_queue_admin ([work_contract]);
GO

-- BATCH
IF EXISTS (SELECT 1 FROM sys.services WHERE name = N'work_service_batch')
    DROP SERVICE work_service_batch;
GO
IF OBJECT_ID(N'work_queue_batch','SQ') IS NOT NULL
    DROP QUEUE work_queue_batch;
GO
CREATE QUEUE  work_queue_batch;
GO
CREATE SERVICE work_service_batch ON QUEUE dbo.work_queue_batch ([work_contract]);
GO

/* =========================================================================
   3) Helper Samplers (계좌/심볼/주문/체결 랜덤 추출)
   ========================================================================= */
IF OBJECT_ID(N'dbo.up_work_pick_account','P') IS NOT NULL DROP PROCEDURE dbo.up_work_pick_account;
GO
CREATE PROCEDURE dbo.up_work_pick_account
    @account_id BIGINT OUTPUT,
    @currency   CHAR(3)  OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP 1 @account_id = account_id, @currency = base_currency
    FROM dbo.cust_account
    ORDER BY NEWID();
END
GO

IF OBJECT_ID(N'dbo.up_work_pick_symbol','P') IS NOT NULL DROP PROCEDURE dbo.up_work_pick_symbol;
GO
CREATE PROCEDURE dbo.up_work_pick_symbol
    @symbol      NVARCHAR(32) OUTPUT,
    @security_id BIGINT       OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP 1 @symbol = symbol, @security_id = security_id
    FROM dbo.ref_security
    WHERE delisted_date IS NULL
    ORDER BY NEWID();
END
GO

IF OBJECT_ID(N'dbo.up_work_pick_order','P') IS NOT NULL DROP PROCEDURE dbo.up_work_pick_order;
GO
CREATE PROCEDURE dbo.up_work_pick_order
    @order_id BIGINT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP 1 @order_id = order_id FROM dbo.ord_order ORDER BY NEWID();
END
GO

IF OBJECT_ID(N'dbo.up_work_pick_execution','P') IS NOT NULL DROP PROCEDURE dbo.up_work_pick_execution;
GO
CREATE PROCEDURE dbo.up_work_pick_execution
    @execution_id BIGINT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP 1 @execution_id = execution_id FROM dbo.exe_execution ORDER BY NEWID();
END
GO

/* =========================================================================
   4) Worker Core + Wrappers (Activation에서 파라미터 불가 → 래퍼 필요)
   ========================================================================= */
IF OBJECT_ID(N'dbo.up__work_worker_core','P') IS NOT NULL DROP PROCEDURE dbo.up__work_worker_core;
GO
CREATE PROCEDURE dbo.up__work_worker_core
    @queue SYSNAME
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @handle UNIQUEIDENTIFIER, @msg NVARCHAR(MAX), @sp SYSNAME, @params NVARCHAR(MAX);

    WHILE (1=1)
    BEGIN
        -- 동적 FROM <queue> (RECEIVE는 고정 테이블명만 허용 → sp_executesql로 우회)
        DECLARE @sql NVARCHAR(MAX) = N'
            WAITFOR (RECEIVE TOP(1)
                @h = conversation_handle,
                @m = CAST(message_body AS NVARCHAR(MAX))
             FROM ' + QUOTENAME(@queue) + N'), TIMEOUT 5000;';
        SET @handle = NULL; SET @msg = NULL;
        EXEC sp_executesql @sql, N'@h UNIQUEIDENTIFIER OUTPUT, @m NVARCHAR(MAX) OUTPUT',
                           @h=@handle OUTPUT, @m=@msg OUTPUT;

        IF @handle IS NULL BREAK;

        SELECT @sp     = JSON_VALUE(@msg, N'$.sp'),
               @params = JSON_VALUE(@msg, N'$.params');

        BEGIN TRY
            DECLARE @exec NVARCHAR(MAX) =
                   N'EXEC ' + QUOTENAME(PARSENAME(@sp,2)) + N'.' + QUOTENAME(PARSENAME(@sp,1))
                 + CASE WHEN @params IS NULL OR @params=N'' THEN N'' ELSE N' ' + @params END;
            EXEC (@exec);
        END TRY
        BEGIN CATCH
            -- 각 SP 내부에서 sp_run_log에 실패 기록함. 여기선 넘어감.
        END CATCH;

        END CONVERSATION @handle;
    END
END
GO

IF OBJECT_ID(N'dbo.up_work_worker_user','P') IS NOT NULL DROP PROCEDURE dbo.up_work_worker_user;
GO
CREATE PROCEDURE dbo.up_work_worker_user AS EXEC dbo.up__work_worker_core @queue = N'dbo.work_queue_user';
GO

IF OBJECT_ID(N'dbo.up_work_worker_admin','P') IS NOT NULL DROP PROCEDURE dbo.up_work_worker_admin;
GO
CREATE PROCEDURE dbo.up_work_worker_admin AS EXEC dbo.up__work_worker_core @queue = N'dbo.work_queue_admin';
GO

IF OBJECT_ID(N'dbo.up_work_worker_batch','P') IS NOT NULL DROP PROCEDURE dbo.up_work_worker_batch;
GO
CREATE PROCEDURE dbo.up_work_worker_batch AS EXEC dbo.up__work_worker_core @queue = N'dbo.work_queue_batch';
GO

/* =========================================================================
   5) Activation (큐별 동시성 독립 조절)
   ========================================================================= */
ALTER QUEUE dbo.work_queue_user
  WITH STATUS=ON, ACTIVATION(STATUS=ON, PROCEDURE_NAME=dbo.up_work_worker_user,  MAX_QUEUE_READERS=32, EXECUTE AS SELF);
GO
ALTER QUEUE dbo.work_queue_admin
  WITH STATUS=ON, ACTIVATION(STATUS=ON, PROCEDURE_NAME=dbo.up_work_worker_admin, MAX_QUEUE_READERS=16, EXECUTE AS SELF);
GO
ALTER QUEUE dbo.work_queue_batch
  WITH STATUS=ON, ACTIVATION(STATUS=ON, PROCEDURE_NAME=dbo.up_work_worker_batch, MAX_QUEUE_READERS=8,  EXECUTE AS SELF);
GO

/* =========================================================================
   6) Message Builders (caller별) 
      - 주요 패밀리에 대해 실제 파라미터 생성
      - 기타는 안전한 조회로 폴백
   ========================================================================= */
IF OBJECT_ID(N'dbo.up_work_build_msg_user','P') IS NOT NULL DROP PROCEDURE dbo.up_work_build_msg_user;
GO
CREATE PROCEDURE dbo.up_work_build_msg_user
    @kind NVARCHAR(40),           -- 'order_place_limit' | 'order_place_market' | 'trade_fill_apply' | 'fund_deposit_req' | 'fund_deposit_cfm' | 'risk_breach_query' | 'query_otj' | ...
    @msg  NVARCHAR(MAX) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @acc BIGINT, @cur CHAR(3), @sym NVARCHAR(32), @sid BIGINT, @order_id BIGINT;
    EXEC dbo.up_work_pick_account @account_id=@acc OUTPUT, @currency=@cur OUTPUT;
    EXEC dbo.up_work_pick_symbol  @symbol=@sym OUTPUT,     @security_id=@sid OUTPUT;

    DECLARE @qty  DECIMAL(18,4) = CAST(1 + (ABS(CHECKSUM(NEWID())) % 200) AS DECIMAL(18,4));
    DECLARE @px   DECIMAL(18,4) = CAST(((ABS(CHECKSUM(NEWID())) % 50000) / 100.0) + 5 AS DECIMAL(18,4));
    DECLARE @side CHAR(1)       = CASE WHEN ABS(CHECKSUM(NEWID())) % 2 = 0 THEN 'B' ELSE 'S' END;
    DECLARE @now  DATETIME2(3)  = SYSUTCDATETIME();

    IF @kind = 'order_place_limit'
        SELECT @msg = N'{"sp":"dbo.up_t_order_place_limit_001","params":"@account_id=' + CAST(@acc AS NVARCHAR(32))
                    + N',@symbol=N''' + REPLACE(@sym,'''','''''') + N''',@side=''' + @side + N''',@qty='
                    + CONVERT(NVARCHAR(50),@qty) + N',@price=' + CONVERT(NVARCHAR(50),@px)
                    + N',@tif=N''DAY'',@source=N''LOAD''"}';
    ELSE IF @kind = 'order_place_market'
        SELECT @msg = N'{"sp":"dbo.up_t_order_place_market_001","params":"@account_id=' + CAST(@acc AS NVARCHAR(32))
                    + N',@symbol=N''' + REPLACE(@sym,'''','''''') + N''',@side=''' + @side + N''',@qty='
                    + CONVERT(NVARCHAR(50),@qty) + N',@source=N''LOAD''"}';
    ELSE IF @kind = 'trade_fill_apply'
    BEGIN
        EXEC dbo.up_work_pick_order @order_id OUTPUT;
        IF @order_id IS NULL
            SELECT @msg = N'{"sp":"dbo.up_s_position_positions_001","params":"@account_id=' + CAST(@acc AS NVARCHAR(32)) + N'"}';
        ELSE
            SELECT @msg = N'{"sp":"dbo.up_t_trade_fill_apply_001","params":"@order_id=' + CAST(@order_id AS NVARCHAR(32))
                        + N',@exec_qty=' + CONVERT(NVARCHAR(50),@qty) + N',@exec_price=' + CONVERT(NVARCHAR(50),@px)
                        + N',@exec_time=''' + CONVERT(NVARCHAR(33),@now,126) + N''',@venue=N''SIM'',@liquidity=''A''"}';
    END
    ELSE IF @kind = 'fund_deposit_req'
        SELECT @msg = N'{"sp":"dbo.up_t_funding_deposit_request_001","params":"@account_id=' + CAST(@acc AS NVARCHAR(32))
                    + N',@amount=' + CONVERT(NVARCHAR(50),@qty*100) + N',@currency_code=''' + @cur + N''',@reference=''DEP_REQ_''"}';
    ELSE IF @kind = 'fund_deposit_cfm'
        SELECT @msg = N'{"sp":"dbo.up_t_funding_deposit_confirm_001","params":"@account_id=' + CAST(@acc AS NVARCHAR(32))
                    + N',@amount=' + CONVERT(NVARCHAR(50),@qty*100) + N',@currency_code=''' + @cur + N''',@reference=''DEP_CFM_''"}';
    ELSE IF @kind = 'risk_breach_query'
        SELECT @msg = N'{"sp":"dbo.up_s_risk_breach_events_001","params":"@account_id=' + CAST(@acc AS NVARCHAR(32))
                    + N',@from_utc=''' + CONVERT(NVARCHAR(33), DATEADD(DAY,-7,@now), 126) + N''',@to_utc=''' + CONVERT(NVARCHAR(33), @now, 126) + N''',@metric=NULL"}';
    ELSE IF @kind = 'query_otj'
        SELECT @msg = N'{"sp":"dbo.up_s_query_order_trade_join_001","params":"@account_id=' + CAST(@acc AS NVARCHAR(32))
                    + N',@symbol=N''' + REPLACE(@sym,'''','''''') + N''',@from_utc=''' + CONVERT(NVARCHAR(33), DATEADD(DAY,-2,@now), 126)
                    + N''',@to_utc=''' + CONVERT(NVARCHAR(33), @now, 126) + N'''}';
    ELSE
        -- 폴백: 가벼운 조회
        SELECT @msg = N'{"sp":"dbo.up_s_position_positions_001","params":"@account_id=' + CAST(@acc AS NVARCHAR(32)) + N'"}';
END
GO

IF OBJECT_ID(N'dbo.up_work_build_msg_admin','P') IS NOT NULL DROP PROCEDURE dbo.up_work_build_msg_admin;
GO
CREATE PROCEDURE dbo.up_work_build_msg_admin
    @kind NVARCHAR(40),
    @msg  NVARCHAR(MAX) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    -- 관리자 쿼리 위주 프리셋
    DECLARE @acc BIGINT, @cur CHAR(3), @sym NVARCHAR(32), @sid BIGINT;
    EXEC dbo.up_work_pick_account @account_id=@acc OUTPUT, @currency=@cur OUTPUT;
    EXEC dbo.up_work_pick_symbol  @symbol=@sym OUTPUT,     @security_id=@sid OUTPUT;

    DECLARE @now DATETIME2(3) = SYSUTCDATETIME();

    IF @kind = 'query_otj'
        SELECT @msg = N'{"sp":"dbo.up_s_query_order_trade_join_001","params":"@account_id=' + CAST(@acc AS NVARCHAR(32))
                    + N',@symbol=N''' + REPLACE(@sym,'''','''''') + N''',@from_utc=''' + CONVERT(NVARCHAR(33), DATEADD(DAY,-2,@now), 126)
                    + N''',@to_utc=''' + CONVERT(NVARCHAR(33), @now, 126) + N'''}';
    ELSE IF @kind = 'risk_breach_query'
        SELECT @msg = N'{"sp":"dbo.up_s_risk_breach_events_001","params":"@account_id=' + CAST(@acc AS NVARCHAR(32))
                    + N',@from_utc=''' + CONVERT(NVARCHAR(33), DATEADD(DAY,-7,@now), 126) + N''',@to_utc=''' + CONVERT(NVARCHAR(33), @now, 126) + N''',@metric=NULL"}';
    ELSE
        SELECT @msg = N'{"sp":"dbo.up_s_position_positions_001","params":"@account_id=' + CAST(@acc AS NVARCHAR(32)) + N'"}';
END
GO

IF OBJECT_ID(N'dbo.up_work_build_msg_batch','P') IS NOT NULL DROP PROCEDURE dbo.up_work_build_msg_batch;
GO
CREATE PROCEDURE dbo.up_work_build_msg_batch
    @kind NVARCHAR(40),
    @msg  NVARCHAR(MAX) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @acc BIGINT, @cur CHAR(3), @sym NVARCHAR(32), @sid BIGINT;
    EXEC dbo.up_work_pick_account @account_id=@acc OUTPUT, @currency=@cur OUTPUT;
    EXEC dbo.up_work_pick_symbol  @symbol=@sym OUTPUT,     @security_id=@sid OUTPUT;

    DECLARE @now DATETIME2(3) = SYSUTCDATETIME();

    IF @kind = 'dataops_stats'
        SELECT @msg = N'{"sp":"dbo.up_t_dataops_stats_update_001","params":"@job_name=N''stats_update'',@metrics_json=N''{}''"}';
    ELSE IF @kind = 'report_sched'
        SELECT @msg = N'{"sp":"dbo.up_t_report_sched_create_001","params":"@account_id=' + CAST(@acc AS NVARCHAR(32)) + N',@symbol=N''' + REPLACE(@sym,'''','''''') + N''',@from_utc=NULL,@to_utc=NULL"}';
    ELSE IF @kind = 'recon_eod'
        SELECT @msg = N'{"sp":"dbo.up_t_recon_eod_close_001","params":"@name=N''EOD_CLOSE'',@payload=N''{}''"}';
    ELSE
        SELECT @msg = N'{"sp":"dbo.up_s_position_positions_001","params":"@account_id=' + CAST(@acc AS NVARCHAR(32)) + N'"}';
END
GO

/* =========================================================================
   7) Enqueuers (caller별)  — 자기 큐/서비스로 전송
   ========================================================================= */
IF OBJECT_ID(N'dbo.up_work_enqueue_many_user','P') IS NOT NULL DROP PROCEDURE dbo.up_work_enqueue_many_user;
GO
CREATE PROCEDURE dbo.up_work_enqueue_many_user
    @total INT = 2000,
    @concurrency INT = 32,
    @mix NVARCHAR(20) = N'orders'   -- 'orders' | 'core' | 'random'
AS
BEGIN
    SET NOCOUNT ON;
    EXEC('ALTER QUEUE dbo.work_queue_user WITH ACTIVATION (MAX_QUEUE_READERS = ' + CAST(@concurrency AS NVARCHAR(10)) + ');');

    DECLARE @i INT = 0, @h UNIQUEIDENTIFIER, @msg NVARCHAR(MAX), @kind NVARCHAR(40);

    WHILE @i < @total
    BEGIN
        SET @kind = CASE @mix
            WHEN 'orders' THEN CASE ABS(CHECKSUM(NEWID())) % 2 WHEN 0 THEN 'order_place_limit' WHEN 1 THEN 'order_place_market' END
            WHEN 'random' THEN CASE ABS(CHECKSUM(NEWID())) % 6 WHEN 0 THEN 'order_place_limit' WHEN 1 THEN 'order_place_market' WHEN 2 THEN 'trade_fill_apply' WHEN 3 THEN 'fund_deposit_req' WHEN 4 THEN 'fund_deposit_cfm' ELSE 'query_otj' END
            ELSE               CASE ABS(CHECKSUM(NEWID())) % 4 WHEN 0 THEN 'order_place_limit' WHEN 1 THEN 'trade_fill_apply' WHEN 2 THEN 'fund_deposit_req' ELSE 'risk_breach_query' END
        END;

        EXEC dbo.up_work_build_msg_user @kind=@kind, @msg=@msg OUTPUT;

        BEGIN DIALOG CONVERSATION @h
            FROM SERVICE dbo.work_service_user
            TO SERVICE   'dbo.work_service_user'
            ON CONTRACT  work_contract
            WITH ENCRYPTION = OFF;

        SEND ON CONVERSATION @h MESSAGE TYPE [//work/message] (CAST(@msg AS VARBINARY(MAX)));
        END CONVERSATION @h;

        SET @i += 1;
    END
END
GO

IF OBJECT_ID(N'dbo.up_work_enqueue_many_admin','P') IS NOT NULL DROP PROCEDURE dbo.up_work_enqueue_many_admin;
GO
CREATE PROCEDURE dbo.up_work_enqueue_many_admin
    @total INT = 2000,
    @concurrency INT = 16,
    @mix NVARCHAR(20) = N'core'     -- 'core' | 'random'
AS
BEGIN
    SET NOCOUNT ON;
    EXEC('ALTER QUEUE dbo.work_queue_admin WITH ACTIVATION (MAX_QUEUE_READERS = ' + CAST(@concurrency AS NVARCHAR(10)) + ');');

    DECLARE @i INT = 0, @h UNIQUEIDENTIFIER, @msg NVARCHAR(MAX), @kind NVARCHAR(40);

    WHILE @i < @total
    BEGIN
        SET @kind = CASE @mix
            WHEN 'random' THEN CASE ABS(CHECKSUM(NEWID())) % 4 WHEN 0 THEN 'query_otj' WHEN 1 THEN 'risk_breach_query' WHEN 2 THEN 'trade_fill_apply' ELSE 'order_place_market' END
            ELSE               CASE ABS(CHECKSUM(NEWID())) % 2 WHEN 0 THEN 'query_otj' ELSE 'risk_breach_query' END
        END;

        EXEC dbo.up_work_build_msg_admin @kind=@kind, @msg=@msg OUTPUT;

        BEGIN DIALOG CONVERSATION @h
            FROM SERVICE dbo.work_service_admin
            TO SERVICE   'dbo.work_service_admin'
            ON CONTRACT  work_contract
            WITH ENCRYPTION = OFF;

        SEND ON CONVERSATION @h MESSAGE TYPE [//work/message] (CAST(@msg AS VARBINARY(MAX)));
        END CONVERSATION @h;

        SET @i += 1;
    END
END
GO

IF OBJECT_ID(N'dbo.up_work_enqueue_many_batch','P') IS NOT NULL DROP PROCEDURE dbo.up_work_enqueue_many_batch;
GO
CREATE PROCEDURE dbo.up_work_enqueue_many_batch
    @total INT = 1000,
    @concurrency INT = 8,
    @mix NVARCHAR(20) = N'batch'    -- 'batch' | 'random'
AS
BEGIN
    SET NOCOUNT ON;
    EXEC('ALTER QUEUE dbo.work_queue_batch WITH ACTIVATION (MAX_QUEUE_READERS = ' + CAST(@concurrency AS NVARCHAR(10)) + ');');

    DECLARE @i INT = 0, @h UNIQUEIDENTIFIER, @msg NVARCHAR(MAX), @kind NVARCHAR(40);

    WHILE @i < @total
    BEGIN
        SET @kind = CASE @mix
            WHEN 'random' THEN CASE ABS(CHECKSUM(NEWID())) % 5 WHEN 0 THEN 'dataops_stats' WHEN 1 THEN 'report_sched' WHEN 2 THEN 'recon_eod' WHEN 3 THEN 'risk_breach_query' ELSE 'query_otj' END
            ELSE               CASE ABS(CHECKSUM(NEWID())) % 3 WHEN 0 THEN 'dataops_stats' WHEN 1 THEN 'report_sched' ELSE 'recon_eod' END
        END;

        EXEC dbo.up_work_build_msg_batch @kind=@kind, @msg=@msg OUTPUT;

        BEGIN DIALOG CONVERSATION @h
            FROM SERVICE dbo.work_service_batch
            TO SERVICE   'dbo.work_service_batch'
            ON CONTRACT  work_contract
            WITH ENCRYPTION = OFF;

        SEND ON CONVERSATION @h MESSAGE TYPE [//work/message] (CAST(@msg AS VARBINARY(MAX)));
        END CONVERSATION @h;

        SET @i += 1;
    END
END
GO

/* =========================================================================
   8) Quick Start
   ========================================================================= */
/*
-- 사용자/관리자/배치 각각 투입 예시
EXEC dbo.up_work_enqueue_many_user  @total=4000, @concurrency=48, @mix='orders';
EXEC dbo.up_work_enqueue_many_admin @total=2000, @concurrency=24, @mix='core';
EXEC dbo.up_work_enqueue_many_batch @total=1000, @concurrency=8,  @mix='batch';

-- 진행 확인
SELECT TOP 200 * FROM dbo.sp_run_log ORDER BY run_id DESC;

-- 일시정지/재개
ALTER QUEUE dbo.work_queue_user  WITH STATUS=OFF;  ALTER QUEUE dbo.work_queue_user  WITH STATUS=ON;
ALTER QUEUE dbo.work_queue_admin WITH STATUS=OFF;  ALTER QUEUE dbo.work_queue_admin WITH STATUS=ON;
ALTER QUEUE dbo.work_queue_batch WITH STATUS=OFF;  ALTER QUEUE dbo.work_queue_batch WITH STATUS=ON;
*/
