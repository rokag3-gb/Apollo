/**********************************************************************
TradingDB Stored Procedures (300) - Composite Script (v2)
Generated: 2025-09-08 10:31:55 UTC
Fixes:
 - Removed undefined @job_name/@payload usage outside dataops procs.
 - Category-specific audit details only use local params.
 - Simplified ORDER BY to deterministic columns (no variable column names).
**********************************************************************/

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO


/* 001) up_t_order_place_market_001
   시장가 주문 접수(매수/매도, TIF/출처 반영)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_market_001
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 002) up_t_order_place_limit_002
   지정가 주문 접수(호가 유효성/가격밴드 체크)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_limit_002
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 003) up_t_order_place_stop_003
   스톱 주문 접수(트리거 가격 진입 시 시장가 전환)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_stop_003
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 004) up_t_order_place_trailing_stop_004
   트레일링 스톱 주문 접수(추적 폭 기반)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_trailing_stop_004
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 005) up_t_order_place_ioc_005
   IOC 즉시체결/잔량취소 주문
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_ioc_005
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 006) up_t_order_place_fok_006
   FOK 전량체결/미체결취소 주문
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_fok_006
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 007) up_t_order_place_gtc_007
   GTC(취소 전까지 유효) 주문
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_gtc_007
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 008) up_t_order_place_gtd_008
   GTD(기한 지정) 주문
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_gtd_008
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 009) up_t_order_replace_order_009
   수정주문(가격/수량 변경)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_replace_order_009
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 010) up_t_order_amend_price_010
   가격만 변경(리프라이스)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_amend_price_010
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 011) up_t_order_amend_qty_011
   수량만 변경(증/감수)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_amend_qty_011
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 012) up_t_order_cancel_single_012
   개별 주문 취소
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_cancel_single_012
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 013) up_t_order_cancel_all_account_013
   계좌 기준 전체 미체결 취소
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_cancel_all_account_013
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 014) up_t_order_cancel_all_symbol_014
   심볼 기준 전체 미체결 취소
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_cancel_all_symbol_014
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 015) up_t_order_bulk_place_015
   대량 주문 일괄 접수(파일/JSON 페이로드)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_bulk_place_015
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 016) up_t_order_bulk_cancel_016
   대량 주문 일괄 취소
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_bulk_cancel_016
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 017) up_t_order_hold_order_017
   사전심사/리스크 사유로 주문 보류
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_hold_order_017
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 018) up_t_order_release_hold_018
   보류 주문 해제
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_release_hold_018
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 019) up_t_order_risk_check_pretrade_019
   사전 리스크체크(증거금/한도)만 수행
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_risk_check_pretrade_019
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 020) up_t_order_set_order_routing_020
   주문 라우팅(시장/브로커/알고리즘) 설정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_set_order_routing_020
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 021) up_t_order_set_order_tif_default_021
   계좌별 기본 TIF 정책 설정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_set_order_tif_default_021
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 022) up_t_order_set_order_notes_022
   주문 메모/출처 기록
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_set_order_notes_022
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 023) up_t_order_suspend_symbol_orders_023
   특정 심볼 주문 일시 중단
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_suspend_symbol_orders_023
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 024) up_t_order_resume_symbol_orders_024
   중단된 심볼 주문 재개
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_resume_symbol_orders_024
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 025) up_t_order_place_bracket_025
   브래킷(진입+익절+손절) 주문
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_bracket_025
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 026) up_t_order_place_oco_026
   OCO(하나 체결 시 다른 하나 취소)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_oco_026
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 027) up_t_order_place_iceberg_027
   아이스버그 주문(노출 수량 제한)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_iceberg_027
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 028) up_t_order_validate_order_028
   주문 유효성만 검사(체결 없음)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_validate_order_028
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 029) up_t_order_set_parent_child_029
   모주문-자주문 관계 설정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_set_parent_child_029
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 030) up_t_order_cancel_conditional_030
   조건부 주문 취소(트리거 기반)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_cancel_conditional_030
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 031) up_t_order_throttle_account_031
   계좌 단위 주문 속도 제한 설정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_throttle_account_031
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 032) up_t_order_throttle_symbol_032
   심볼 단위 주문 속도 제한 설정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_throttle_symbol_032
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 033) up_t_order_place_at_open_033
   장시작 전 제출 주문
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_at_open_033
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 034) up_t_order_place_at_close_034
   장마감 시 제출 주문
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_at_close_034
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 035) up_t_order_place_hidden_035
   히든 주문(노출 0)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_hidden_035
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 036) up_t_order_place_pegged_036
   피그드 주문(베스트호가 연동)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_pegged_036
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 037) up_t_order_route_smart_037
   스마트 라우팅 정책 적용
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_route_smart_037
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 038) up_t_order_cancel_stale_038
   오래된 미체결 자동 취소
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_cancel_stale_038
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 039) up_t_order_place_conditional_price_039
   조건부 가격 트리거 주문
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_conditional_price_039
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 040) up_t_order_place_conditional_time_040
   시간 트리거 주문
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_conditional_time_040
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 041) up_t_order_apply_price_band_041
   가격 밴드 규칙 적용
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_apply_price_band_041
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 042) up_t_order_apply_volatility_pause_042
   변동성 완화장치 발동 시 중지
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_apply_volatility_pause_042
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 043) up_t_order_enrich_order_tags_043
   주문 태깅/메타데이터 보강
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_enrich_order_tags_043
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 044) up_t_order_migrate_orders_044
   주문 마이그레이션(장 이전)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_migrate_orders_044
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 045) up_t_order_split_parent_order_045
   모주문을 다수 자주문으로 분할
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_split_parent_order_045
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 046) up_t_order_merge_child_orders_046
   자주문들을 단일 주문으로 병합
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_merge_child_orders_046
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 047) up_t_order_assign_algo_047
   주문에 알고리즘 전략 할당
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_assign_algo_047
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 048) up_t_order_detach_algo_048
   주문의 알고리즘 전략 해제
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_detach_algo_048
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 049) up_t_order_override_limits_049
   특정 주문 한도 예외 승인
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_override_limits_049
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 050) up_t_order_reject_order_050
   규정 위반 주문 명시적 거절
*/
CREATE OR ALTER PROCEDURE dbo.up_t_order_reject_order_050
    @account_id bigint = NULL,
    @symbol_id bigint = NULL,
    @side varchar(4) = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @tif varchar(10) = NULL,
    @source nvarchar(100) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @symbol_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 51000, 'Invalid order parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            DECLARE @acc_status varchar(20);
            SELECT @acc_status = status FROM dbo.accounts WITH (UPDLOCK) WHERE account_id=@account_id;
            IF @acc_status IS NULL OR @acc_status <> 'ACTIVE' THROW 51001, 'Account not active', 1;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            INSERT dbo.orders(account_id, symbol_id, side, ord_type, qty, price, status, created_at, updated_at, time_in_force, notes)
            VALUES(@account_id, @symbol_id, COALESCE(@side,'BUY'), CASE WHEN @price IS NULL THEN 'MKT' ELSE 'LMT' END,
                   @qty, @price, 'NEW', SYSUTCDATETIME(), SYSUTCDATETIME(), COALESCE(@tif,'GFD'), @source);
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(CONVERT(varchar(50),@symbol_id),''),' side=',COALESCE(@side,''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' tif=',COALESCE(@tif,''),' src=',COALESCE(@source,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 051) up_t_trade_execute_full_051
   주문 전량 체결(가격/수량 확정)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_execute_full_051
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 052) up_t_trade_execute_partial_052
   주문 부분 체결
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_execute_partial_052
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 053) up_t_trade_allocate_block_053
   블록트레이드 배분
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_allocate_block_053
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 054) up_t_trade_deallocate_block_054
   블록 배분 회수/정정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_deallocate_block_054
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 055) up_t_trade_avg_price_group_055
   여러 체결의 평균가 그룹 설정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_avg_price_group_055
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 056) up_t_trade_assign_to_accounts_056
   모체결을 여러 계좌로 분배
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_assign_to_accounts_056
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 057) up_t_trade_cancel_trade_bust_057
   오체결 취소(Bust)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_cancel_trade_bust_057
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 058) up_t_trade_correct_trade_058
   체결 정정(가격/수량)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_correct_trade_058
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 059) up_t_trade_settle_trades_059
   결제 처리(T+2 등)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_settle_trades_059
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 060) up_t_trade_force_close_060
   부적격/위험 계좌 강제 청산
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_force_close_060
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 061) up_t_trade_auto_close_margin_061
   증거금 부족 자동 청산
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_auto_close_margin_061
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 062) up_t_trade_exercise_rights_062
   권리 행사 처리(권리락 전)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_exercise_rights_062
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 063) up_t_trade_assign_rights_063
   권리 배정 처리
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_assign_rights_063
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 064) up_t_trade_reverse_trade_064
   반대 체결로 상쇄
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_reverse_trade_064
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 065) up_t_trade_link_execution_to_order_065
   체결-주문 연결 고도화
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_link_execution_to_order_065
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 066) up_t_trade_unlink_execution_066
   체결과 주문의 링크 해제
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_unlink_execution_066
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 067) up_t_trade_apply_fee_067
   체결 수수료 부과
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_apply_fee_067
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 068) up_t_trade_refund_fee_068
   수수료 환불/감면
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_refund_fee_068
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 069) up_t_trade_apply_tax_069
   체결 세금 부과
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_apply_tax_069
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 070) up_t_trade_refund_tax_070
   세금 환급/수정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_refund_tax_070
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 071) up_t_trade_netting_intraday_071
   당일 체결 순평가/상계
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_netting_intraday_071
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 072) up_t_trade_netting_endofday_072
   종가 기준 순평가/상계
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_netting_endofday_072
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 073) up_t_trade_close_short_073
   공매도 상환 처리
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_close_short_073
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 074) up_t_trade_assign_lot_fifo_074
   FIFO Lot 배정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_assign_lot_fifo_074
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 075) up_t_trade_assign_lot_lifo_075
   LIFO Lot 배정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_assign_lot_lifo_075
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 076) up_t_trade_assign_lot_avg_076
   평균가 Lot 배정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_assign_lot_avg_076
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 077) up_t_trade_settlement_fail_mark_077
   결제 실패 마킹 및 재시도
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_settlement_fail_mark_077
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 078) up_t_trade_reprice_trade_078
   체결 가격 재산정(오류 보정)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_reprice_trade_078
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 079) up_t_trade_split_trade_079
   단일 체결을 분할
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_split_trade_079
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 080) up_t_trade_merge_trades_080
   복수 체결을 병합
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_merge_trades_080
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 081) up_t_trade_late_trade_capture_081
   사후 입력 체결 등록
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_late_trade_capture_081
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 082) up_t_trade_trade_import_file_082
   외부 파일로 체결 일괄 반입
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_trade_import_file_082
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 083) up_t_trade_trade_export_file_083
   체결 데이터 파일로 내보내기
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_trade_export_file_083
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 084) up_t_trade_reconcile_trades_084
   외부원장/브로커와 체결 대사
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_reconcile_trades_084
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 085) up_t_trade_match_executions_085
   주문-체결 매칭
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_match_executions_085
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 086) up_t_trade_unmatch_executions_086
   매칭 해제 및 재매칭
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_unmatch_executions_086
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 087) up_t_trade_apply_trade_corrections_087
   일괄 체결 정정 배치
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_apply_trade_corrections_087
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 088) up_t_trade_toggle_trade_lock_088
   체결 수정 잠금/해제
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_toggle_trade_lock_088
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 089) up_t_trade_mark_trade_suspicious_089
   이상 거래 플래그 설정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_mark_trade_suspicious_089
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 090) up_t_trade_escalate_trade_review_090
   심층 심사 큐로 이관
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_escalate_trade_review_090
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 091) up_t_trade_trade_reroute_settlement_091
   결제 라우팅 변경
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_trade_reroute_settlement_091
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 092) up_t_trade_assign_custodian_092
   체결 보관기관 지정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_assign_custodian_092
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 093) up_t_trade_remove_custodian_093
   보관기관 해제
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_remove_custodian_093
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 094) up_t_trade_apply_trade_fx_fixing_094
   결제 통화 환산(Fixing)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_apply_trade_fx_fixing_094
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 095) up_t_trade_backdate_trade_095
   체결 일자 소급 입력
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_backdate_trade_095
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 096) up_t_trade_cancel_backdated_096
   소급 입력 체결 취소
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_cancel_backdated_096
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 097) up_t_trade_lock_for_audit_097
   감사 대비 수정 잠금
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_lock_for_audit_097
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 098) up_t_trade_unlock_after_audit_098
   감사 종료 후 잠금 해제
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_unlock_after_audit_098
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 099) up_t_trade_explain_trade_changes_099
   변경 사유/코멘트 기록
*/
CREATE OR ALTER PROCEDURE dbo.up_t_trade_explain_trade_changes_099
    @execution_id bigint = NULL,
    @order_id bigint = NULL,
    @qty decimal(19,6) = NULL,
    @price decimal(19,6) = NULL,
    @fee decimal(19,4) = NULL,
    @tax decimal(19,4) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @order_id IS NULL OR @qty IS NULL OR @qty <= 0
            THROW 52000, 'Invalid trade parameters', 1;

        DECLARE @side varchar(4), @account_id bigint, @symbol_id bigint;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type='U')
        BEGIN
            SELECT @side = side, @account_id = account_id, @symbol_id = symbol_id
            FROM dbo.orders WITH (UPDLOCK, ROWLOCK)
            WHERE order_id = @order_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type='U')
        BEGIN
            INSERT dbo.trades(order_id, account_id, symbol_id, side, qty, price, executed_at)
            SELECT @order_id, @account_id, @symbol_id, @side, @qty, COALESCE(@price, 0), SYSUTCDATETIME();
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @order_id, CONCAT('exec=',COALESCE(CONVERT(varchar(50),@execution_id),''),' ord=',COALESCE(CONVERT(varchar(50),@order_id),''),' qty=',COALESCE(CONVERT(varchar(50),@qty),''),' px=',COALESCE(CONVERT(varchar(50),@price),''),' fee=',COALESCE(CONVERT(varchar(50),@fee),''),' tax=',COALESCE(CONVERT(varchar(50),@tax),'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 100) up_t_funding_deposit_cash_100
   현금 입금 처리(가상계좌/수기입금 포함)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_deposit_cash_100
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 101) up_t_funding_withdraw_cash_101
   현금 출금 처리(출금한도/비밀번호 확인)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_withdraw_cash_101
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 102) up_t_funding_transfer_cash_102
   계좌 간 현금 이체(동일 통화)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_transfer_cash_102
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 103) up_t_funding_fx_convert_103
   현금 환전(실시간/고시환율 선택)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_fx_convert_103
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 104) up_t_funding_lock_funds_104
   주문/증거금용 현금 잠금
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_lock_funds_104
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 105) up_t_funding_unlock_funds_105
   잠금 해제
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_unlock_funds_105
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 106) up_t_funding_earmark_margin_106
   증거금 자동 배정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_earmark_margin_106
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 107) up_t_funding_release_margin_107
   증거금 자동 회수
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_release_margin_107
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 108) up_t_funding_set_credit_limit_108
   계좌 신용한도 설정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_set_credit_limit_108
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 109) up_t_funding_adjust_credit_limit_109
   신용한도 증감 조정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_adjust_credit_limit_109
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 110) up_t_funding_interest_credit_110
   이자 지급(예수금 이자)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_interest_credit_110
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 111) up_t_funding_interest_debit_111
   이자 차감(신용/마진 비용)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_interest_debit_111
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 112) up_t_funding_fee_charge_112
   수수료 부과(약정/보관/플랫폼)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_fee_charge_112
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 113) up_t_funding_fee_refund_113
   수수료 환불/정정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_fee_refund_113
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 114) up_t_funding_tax_withhold_114
   세금 원천징수
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_tax_withhold_114
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 115) up_t_funding_tax_refund_115
   세금 환급
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_tax_refund_115
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 116) up_t_funding_dividend_cash_116
   현금 배당 지급
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_dividend_cash_116
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 117) up_t_funding_dividend_stock_117
   주식 배당 배분(주수/단수처리)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_dividend_stock_117
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 118) up_t_funding_corporate_action_rights_118
   권리 배정/유상증자 대금 처리
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_corporate_action_rights_118
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 119) up_t_funding_corporate_action_split_cash_adj_119
   액분/병합에 따른 현금 조정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_corporate_action_split_cash_adj_119
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 120) up_t_funding_writeoff_small_balance_120
   소액 잔액 상계/탕감
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_writeoff_small_balance_120
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 121) up_t_funding_reverse_funding_121
   오입금/오출금 반제
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_reverse_funding_121
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 122) up_t_funding_reconcile_cash_bank_122
   은행 계좌와 현금 대사
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_reconcile_cash_bank_122
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 123) up_t_funding_import_bank_stmt_123
   은행 거래명세서 반입/매핑
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_import_bank_stmt_123
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 124) up_t_funding_export_cash_ledger_124
   현금원장 내보내기
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_export_cash_ledger_124
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 125) up_t_funding_sweep_idle_cash_125
   유휴현금 스윕(머니마켓)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_sweep_idle_cash_125
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 126) up_t_funding_funding_hold_126
   자금 보류 플래그 설정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_funding_hold_126
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 127) up_t_funding_funding_release_hold_127
   자금 보류 해제
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_funding_release_hold_127
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 128) up_t_funding_charge_penalty_128
   연체/규정 위반 벌금 부과
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_charge_penalty_128
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 129) up_t_funding_refund_penalty_129
   벌금 환불/정정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_refund_penalty_129
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 130) up_t_funding_change_currency_pref_130
   계좌 기본 통화 변경
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_change_currency_pref_130
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 131) up_t_funding_cash_rounding_adjust_131
   소수점 반올림/절사 정리
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_cash_rounding_adjust_131
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 132) up_t_funding_bulk_deposit_132
   대량 입금 일괄 처리
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_bulk_deposit_132
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 133) up_t_funding_bulk_withdraw_133
   대량 출금 일괄 처리
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_bulk_withdraw_133
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 134) up_t_funding_bulk_fx_convert_134
   대량 환전 일괄 처리
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_bulk_fx_convert_134
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 135) up_t_funding_settlement_cash_in_135
   결제 유입 현금 반영
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_settlement_cash_in_135
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 136) up_t_funding_settlement_cash_out_136
   결제 유출 현금 반영
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_settlement_cash_out_136
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 137) up_t_funding_funding_adjust_manual_137
   현금 수기 조정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_funding_adjust_manual_137
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 138) up_t_funding_standing_order_create_138
   정기이체 설정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_standing_order_create_138
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 139) up_t_funding_standing_order_cancel_139
   정기이체 해지
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_standing_order_cancel_139
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 140) up_t_funding_standing_order_run_140
   정기이체 배치 실행
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_standing_order_run_140
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 141) up_t_funding_cash_hold_for_withdrawal_141
   출금예약 금액 선잠금
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_cash_hold_for_withdrawal_141
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 142) up_t_funding_cash_release_after_withdrawal_142
   출금 완료 후 잠금 해제
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_cash_release_after_withdrawal_142
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 143) up_t_funding_margin_call_notify_143
   마진콜 알림(임계치 하회)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_margin_call_notify_143
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 144) up_t_funding_margin_call_liquidate_144
   마진콜 강제정리
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_margin_call_liquidate_144
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 145) up_t_funding_set_fee_schedule_145
   계좌 수수료 테이블 지정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_set_fee_schedule_145
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 146) up_t_funding_set_tax_profile_146
   계좌 세금 프로파일 지정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_set_tax_profile_146
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 147) up_t_funding_apply_promotional_credit_147
   프로모션 크레딧 지급
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_apply_promotional_credit_147
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 148) up_t_funding_revoke_promotional_credit_148
   프로모션 크레딧 회수
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_revoke_promotional_credit_148
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 149) up_t_funding_sweep_negative_balances_149
   마이너스 잔고 상계
*/
CREATE OR ALTER PROCEDURE dbo.up_t_funding_sweep_negative_balances_149
    @account_id bigint = NULL,
    @amount decimal(19,4) = NULL,
    @currency_code char(3) = NULL,
    @ref_id nvarchar(64) = NULL,
    @requested_by nvarchar(100) = N'system'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @account_id IS NULL OR @amount IS NULL
            THROW 53000, 'Invalid funding parameters', 1;

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.accounts') AND type='U')
        BEGIN
            UPDATE dbo.accounts
               SET cash_balance = COALESCE(cash_balance,0) + @amount
             WHERE account_id = @account_id;
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), @account_id, CONCAT('acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' amt=',COALESCE(CONVERT(varchar(50),@amount),''),' ccy=',COALESCE(@currency_code,''),' ref=',COALESCE(@ref_id,'')), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 150) up_t_dataops_cob_close_of_business_150
   장마감 배치: 체결확정/평가/정산 준비
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_cob_close_of_business_150
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 151) up_t_dataops_oob_open_of_business_151
   장개시 배치: 마스터/한도 초기화
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_oob_open_of_business_151
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 152) up_t_dataops_recalc_positions_152
   포지션 재계산(체결/이관 반영)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_recalc_positions_152
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 153) up_t_dataops_recalc_pnl_intraday_153
   당일 PnL 재산정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_recalc_pnl_intraday_153
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 154) up_t_dataops_recalc_pnl_eod_154
   종가 기준 PnL 재산정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_recalc_pnl_eod_154
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 155) up_t_dataops_revalue_fx_155
   FX 재평가 및 환산
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_revalue_fx_155
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 156) up_t_dataops_refresh_symbol_master_156
   심볼 마스터 동기화(상장/폐지 반영)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_refresh_symbol_master_156
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 157) up_t_dataops_import_prices_intraday_157
   분봉/틱 가격 반입
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_import_prices_intraday_157
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 158) up_t_dataops_import_prices_eod_158
   일봉 종가 데이터 반입
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_import_prices_eod_158
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 159) up_t_dataops_backfill_prices_159
   가격 이력 누락 구간 보정
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_backfill_prices_159
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 160) up_t_dataops_rebuild_indexes_160
   핵심 테이블 인덱스 재구성
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_rebuild_indexes_160
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 161) up_t_dataops_update_stats_161
   통계정보 업데이트
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_update_stats_161
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 162) up_t_dataops_purge_old_orders_162
   오래된 주문 데이터 정리
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_purge_old_orders_162
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 163) up_t_dataops_purge_old_trades_163
   오래된 체결 데이터 정리
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_purge_old_trades_163
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 164) up_t_dataops_purge_old_audit_164
   오래된 감사로그 정리
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_purge_old_audit_164
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 165) up_t_dataops_archive_trades_monthly_165
   월 단위 체결 아카이브
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_archive_trades_monthly_165
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 166) up_t_dataops_archive_orders_monthly_166
   월 단위 주문 아카이브
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_archive_orders_monthly_166
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 167) up_t_dataops_snapshot_nav_167
   계좌 NAV 스냅샷 적재
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_snapshot_nav_167
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 168) up_t_dataops_export_regulatory_168
   규제 보고 파일 생성/전송
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_export_regulatory_168
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 169) up_t_dataops_export_statements_169
   명세서 일괄 생성/배포
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_export_statements_169
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 170) up_t_dataops_reconcile_positions_170
   보관기관/외부원장과 포지션 대사
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_reconcile_positions_170
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 171) up_t_dataops_reconcile_cash_171
   은행/보관기관과 현금 대사
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_reconcile_cash_171
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 172) up_t_dataops_risk_limits_check_172
   한도 점검 및 위반 플래그
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_risk_limits_check_172
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 173) up_t_dataops_fix_stale_locks_173
   경합/좀비 잠금 정리
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_fix_stale_locks_173
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 174) up_t_dataops_retry_failed_jobs_174
   실패 배치 재시도 큐 처리
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_retry_failed_jobs_174
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 175) up_t_dataops_job_heartbeat_175
   잡 헬스체크/하트비트 기록
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_job_heartbeat_175
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 176) up_t_dataops_materialize_views_176
   집계뷰/스냅샷뷰 갱신
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_materialize_views_176
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 177) up_t_dataops_rollup_intraday_agg_177
   분단위/시간단위 집계 롤업
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_rollup_intraday_agg_177
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 178) up_t_dataops_rollup_eod_agg_178
   일/월 단위 집계 롤업
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_rollup_eod_agg_178
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 179) up_t_dataops_generate_kpis_179
   핵심 KPI 산출/저장
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_generate_kpis_179
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 180) up_t_dataops_sync_reference_tables_180
   거래소/통화/휴장일 등 기준정보 동기화
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_sync_reference_tables_180
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 181) up_t_dataops_vacuum_partitions_181
   파티션 컴팩션/정리
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_vacuum_partitions_181
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 182) up_t_dataops_rotate_audit_partitions_182
   감사 테이블 파티션 로테이션
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_rotate_audit_partitions_182
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 183) up_t_dataops_seed_demo_data_183
   개발/테스트용 더미 데이터 적재
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_seed_demo_data_183
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 184) up_t_dataops_truncate_demo_data_184
   더미 데이터 초기화
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_truncate_demo_data_184
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 185) up_t_dataops_health_check_185
   데이터 품질/무결성 점검
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_health_check_185
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 186) up_t_dataops_detect_anomalies_186
   이상치 탐지(기본 통계)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_detect_anomalies_186
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 187) up_t_dataops_rebuild_caches_187
   요약/랭킹 캐시 재구축
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_rebuild_caches_187
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 188) up_t_dataops_refresh_permissions_188
   권한/역할 매핑 갱신
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_refresh_permissions_188
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 189) up_t_dataops_sync_holidays_189
   거래소 휴장일 캘린더 동기화
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_sync_holidays_189
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 190) up_t_dataops_init_trading_day_190
   거래일 초기화(시퀀스/카운터)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_init_trading_day_190
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 191) up_t_dataops_close_trading_day_191
   거래일 마감(검증/잠금)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_close_trading_day_191
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 192) up_t_dataops_rollover_trading_day_192
   거래일 롤오버(장마감→다음일)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_rollover_trading_day_192
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 193) up_t_dataops_ingest_corporate_actions_193
   기업행사 데이터 반입
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_ingest_corporate_actions_193
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 194) up_t_dataops_apply_corporate_actions_194
   기업행사 일괄 적용
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_apply_corporate_actions_194
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 195) up_t_dataops_reprice_splits_mergers_195
   액면분할/병합 리프라이싱
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_reprice_splits_mergers_195
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 196) up_t_dataops_gc_temp_staging_196
   스테이징 임시데이터 가비지 컬렉션
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_gc_temp_staging_196
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 197) up_t_dataops_mask_pii_197
   개인정보 마스킹/익명화 작업
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_mask_pii_197
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 198) up_t_dataops_decrypt_sensitive_198
   민감정보 복호화(감사 승인 필요)
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_decrypt_sensitive_198
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 199) up_t_dataops_snapshot_configs_199
   환경설정 스냅샷 백업
*/
CREATE OR ALTER PROCEDURE dbo.up_t_dataops_snapshot_configs_199
    @job_name sysname = NULL,
    @payload nvarchar(max) = NULL,
    @run_date date = NULL,
    @requested_by nvarchar(100) = N'batch'
AS
BEGIN
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;

        IF @job_name IS NULL THROW 54000, 'job_name required', 1;
        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.job_runs') AND type='U')
        BEGIN
            INSERT dbo.job_runs(job_name, payload, run_date, created_at)
            VALUES(@job_name, @payload, @run_date, SYSUTCDATETIME());
        END

        IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
        BEGIN
            INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
            VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL, CONCAT('job=',COALESCE(@job_name,''),' payload_len=',LEN(COALESCE(@payload,N''))), SYSUTCDATETIME(), COALESCE(@requested_by, N'system'));
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK;
        DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
        RETURN -1;
    END CATCH

END
GO


/* 200) up_s_query_positions_by_account_200
   계좌 보유 종목/평균가/평가손익 조회
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_positions_by_account_200
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.positions') AND type = 'U')
    BEGIN
        SELECT p.*, s.symbol, s.last_price
        FROM dbo.positions p
        LEFT JOIN dbo.symbols s ON s.symbol_id = p.symbol_id
        WHERE (@account_id IS NULL OR p.account_id = @account_id)
          AND (@symbol IS NULL OR s.symbol = @symbol)
        ORDER BY s.symbol
        OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;

        RETURN 0;
    END

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 201) up_s_query_open_orders_201
   미체결 주문 목록 조회(페이지/정렬)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_open_orders_201
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type = 'U')
    BEGIN
        SELECT o.*
        FROM dbo.orders o
        WHERE (@account_id IS NULL OR o.account_id = @account_id)
          AND (@symbol IS NULL OR EXISTS (SELECT 1 FROM dbo.symbols s WHERE s.symbol_id = o.symbol_id AND s.symbol = @symbol))
          AND (@status IS NULL OR o.status = @status)
          AND (@from_dt IS NULL OR o.created_at >= @from_dt)
          AND (@to_dt IS NULL OR o.created_at <  @to_dt)
        ORDER BY o.created_at DESC
        OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;

        RETURN 0;
    END

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 202) up_s_query_order_history_202
   주문 이력 조회(기간/상태 필터)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_order_history_202
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 203) up_s_query_trades_by_account_203
   계좌 체결 이력 조회(기간/심볼)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_trades_by_account_203
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type = 'U')
    BEGIN
        SELECT t.*
        FROM dbo.trades t
        WHERE (@account_id IS NULL OR t.account_id = @account_id)
          AND (@symbol IS NULL OR EXISTS (SELECT 1 FROM dbo.symbols s WHERE s.symbol_id = t.symbol_id AND s.symbol = @symbol))
          AND (@from_dt IS NULL OR t.executed_at >= @from_dt)
          AND (@to_dt IS NULL OR t.executed_at <  @to_dt)
        ORDER BY t.executed_at DESC
        OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;

        RETURN 0;
    END

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 204) up_s_query_trades_by_symbol_204
   심볼별 체결 이력 조회
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_trades_by_symbol_204
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type = 'U')
    BEGIN
        SELECT t.*
        FROM dbo.trades t
        WHERE (@account_id IS NULL OR t.account_id = @account_id)
          AND (@symbol IS NULL OR EXISTS (SELECT 1 FROM dbo.symbols s WHERE s.symbol_id = t.symbol_id AND s.symbol = @symbol))
          AND (@from_dt IS NULL OR t.executed_at >= @from_dt)
          AND (@to_dt IS NULL OR t.executed_at <  @to_dt)
        ORDER BY t.executed_at DESC
        OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;

        RETURN 0;
    END

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 205) up_s_query_cash_ledger_205
   현금 원장(입출금/수수료/세금)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_cash_ledger_205
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 206) up_s_query_funding_history_206
   자금 이동 이력
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_funding_history_206
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 207) up_s_query_pnl_intraday_207
   당일 손익 요약
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_pnl_intraday_207
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 208) up_s_query_pnl_period_208
   기간별 손익(일/월 집계)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_pnl_period_208
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 209) up_s_query_market_price_history_209
   가격 이력(분/일봉)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_market_price_history_209
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 210) up_s_query_risk_exposure_210
   리스크 노출(심볼/섹터/지역)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_risk_exposure_210
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 211) up_s_query_credit_usage_211
   신용한도 사용 현황
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_credit_usage_211
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 212) up_s_query_regulatory_flags_212
   규제/감사 플래그 목록
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_regulatory_flags_212
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 213) up_s_query_corporate_actions_history_213
   기업행사 이력
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_corporate_actions_history_213
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 214) up_s_query_audit_log_by_ref_214
   감사 로그(참조ID 기반)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_audit_log_by_ref_214
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 215) up_s_query_orders_heatmap_215
   주문 밀도/시간대 히트맵
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_orders_heatmap_215
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.orders') AND type = 'U')
    BEGIN
        SELECT o.*
        FROM dbo.orders o
        WHERE (@account_id IS NULL OR o.account_id = @account_id)
          AND (@symbol IS NULL OR EXISTS (SELECT 1 FROM dbo.symbols s WHERE s.symbol_id = o.symbol_id AND s.symbol = @symbol))
          AND (@status IS NULL OR o.status = @status)
          AND (@from_dt IS NULL OR o.created_at >= @from_dt)
          AND (@to_dt IS NULL OR o.created_at <  @to_dt)
        ORDER BY o.created_at DESC
        OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;

        RETURN 0;
    END

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 216) up_s_query_trades_slippage_216
   체결 슬리피지 분석
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_trades_slippage_216
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.trades') AND type = 'U')
    BEGIN
        SELECT t.*
        FROM dbo.trades t
        WHERE (@account_id IS NULL OR t.account_id = @account_id)
          AND (@symbol IS NULL OR EXISTS (SELECT 1 FROM dbo.symbols s WHERE s.symbol_id = t.symbol_id AND s.symbol = @symbol))
          AND (@from_dt IS NULL OR t.executed_at >= @from_dt)
          AND (@to_dt IS NULL OR t.executed_at <  @to_dt)
        ORDER BY t.executed_at DESC
        OFFSET @__offset ROWS FETCH NEXT @page_size ROWS ONLY;

        RETURN 0;
    END

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 217) up_s_query_best_execution_217
   베스트 실행 품질 지표
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_best_execution_217
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 218) up_s_query_liquidity_consumption_218
   유동성 소비 분석
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_liquidity_consumption_218
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 219) up_s_query_latency_breakdown_219
   지연시간 분해(각 단계)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_latency_breakdown_219
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 220) up_s_query_kpi_dashboard_220
   핵심 KPI 조회
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_kpi_dashboard_220
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 221) up_s_query_nav_snapshot_221
   계좌별 NAV 스냅샷
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_nav_snapshot_221
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 222) up_s_query_recon_cash_status_222
   현금 대사 상태
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_recon_cash_status_222
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 223) up_s_query_recon_position_status_223
   포지션 대사 상태
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_recon_position_status_223
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 224) up_s_query_limits_breaches_224
   한도 위반 현황
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_limits_breaches_224
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 225) up_s_query_margin_status_225
   증거금 상태(콜/청산)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_margin_status_225
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 226) up_s_query_symbol_master_226
   심볼 마스터/상태/가격
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_symbol_master_226
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 227) up_s_query_holiday_calendar_227
   거래소 휴장일 캘린더
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_holiday_calendar_227
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 228) up_s_query_account_profile_228
   계좌 기본정보/설정
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_account_profile_228
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 229) up_s_query_customer_profile_229
   고객 기본정보/상태
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_customer_profile_229
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 230) up_s_query_fee_tables_230
   수수료 테이블 정의
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_fee_tables_230
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 231) up_s_query_tax_profiles_231
   세금 프로파일 정의
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_tax_profiles_231
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 232) up_s_query_job_runs_232
   배치 잡 실행 이력/상태
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_job_runs_232
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 233) up_s_query_job_errors_233
   배치 오류/재시도 현황
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_job_errors_233
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 234) up_s_query_anomalies_recent_234
   최근 이상치 탐지 결과
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_anomalies_recent_234
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 235) up_s_query_permissions_map_235
   권한/역할 매핑
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_permissions_map_235
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 236) up_s_query_audit_recent_236
   최근 감사 로그 Top N
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_audit_recent_236
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 237) up_s_query_order_flow_by_exchange_237
   거래소별 주문 흐름
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_order_flow_by_exchange_237
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 238) up_s_query_trade_flow_by_broker_238
   브로커별 체결 흐름
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_trade_flow_by_broker_238
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 239) up_s_query_symbol_rankings_239
   거래량/체결금액 랭킹
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_symbol_rankings_239
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 240) up_s_query_watchlist_240
   관심종목 리스트
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_watchlist_240
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 241) up_s_query_alert_rules_241
   알림 규칙 설정 조회
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_alert_rules_241
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 242) up_s_query_execution_quality_detail_242
   체결 품질 세부
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_execution_quality_detail_242
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 243) up_s_query_position_lot_details_243
   Lot 단위 포지션 상세
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_position_lot_details_243
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 244) up_s_query_cash_projection_244
   현금 전망(정산/예정)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_cash_projection_244
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 245) up_s_query_exposure_by_currency_245
   통화별 익스포저
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_exposure_by_currency_245
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 246) up_s_query_exposure_by_sector_246
   섹터별 익스포저
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_exposure_by_sector_246
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 247) up_s_query_order_book_snapshot_247
   호가 스냅샷(내부 캐시 기준)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_order_book_snapshot_247
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 248) up_s_query_latency_trends_248
   지연시간 추세
*/
CREATE OR ALTER PROCEDURE dbo.up_s_query_latency_trends_248
    @account_id bigint = NULL,
    @symbol varchar(32) = NULL,
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @status varchar(20) = NULL,
    @page int = 1,
    @page_size int = 100,
    @sort_by sysname = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @__offset int = (@page-1) * @page_size;

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('query acc=',COALESCE(CONVERT(varchar(50),@account_id),''),' sym=',COALESCE(@symbol,''),' status=',COALESCE(@status,'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 249) up_s_report_daily_statement_249
   일일 거래명세서 생성(PDF/CSV)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_daily_statement_249
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 250) up_s_report_monthly_statement_250
   월간 거래명세서 생성/배포
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_monthly_statement_250
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 251) up_s_report_tax_statement_251
   연간 세무 보고서 생성
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_tax_statement_251
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 252) up_s_report_fee_summary_252
   수수료 요약 리포트
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_fee_summary_252
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 253) up_s_report_tax_summary_253
   세금 요약 리포트
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_tax_summary_253
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 254) up_s_report_regulatory_mi_254
   규제기관 보고(MI/거래내역)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_regulatory_mi_254
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 255) up_s_report_execution_quality_255
   베스트 실행 품질 리포트
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_execution_quality_255
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 256) up_s_report_slippage_summary_256
   슬리피지 요약 리포트
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_slippage_summary_256
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 257) up_s_report_eod_summary_257
   종가 요약/잔고/PnL
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_eod_summary_257
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 258) up_s_report_intraday_summary_258
   당일 실시간 요약
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_intraday_summary_258
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 259) up_s_report_customer_activity_259
   고객 활동 리포트
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_customer_activity_259
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 260) up_s_report_account_activity_260
   계좌 활동 리포트
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_account_activity_260
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 261) up_s_report_top_symbols_261
   거래 상위 심볼 랭킹
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_top_symbols_261
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 262) up_s_report_broker_performance_262
   브로커 성과 비교
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_broker_performance_262
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 263) up_s_report_exchange_latency_263
   거래소별 지연시간 리포트
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_exchange_latency_263
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 264) up_s_report_risk_limit_breaches_264
   리스크 한도 위반 보고
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_risk_limit_breaches_264
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 265) up_s_report_margin_calls_265
   마진콜 발생 현황
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_margin_calls_265
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 266) up_s_report_pnl_breakdown_266
   손익 분해(수수료/세금/환산 포함)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_pnl_breakdown_266
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 267) up_s_report_audit_summary_267
   감사 요약/주요 이벤트
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_audit_summary_267
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 268) up_s_report_anomaly_summary_268
   이상 탐지 요약
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_anomaly_summary_268
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 269) up_s_report_cash_reconciliation_269
   현금 대사 리포트
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_cash_reconciliation_269
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 270) up_s_report_position_reconciliation_270
   포지션 대사 리포트
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_position_reconciliation_270
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 271) up_s_report_statement_distribution_271
   명세서 배포 현황
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_statement_distribution_271
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 272) up_s_report_failed_jobs_272
   실패한 배치/재시도 내역
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_failed_jobs_272
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 273) up_s_report_capacity_utilization_273
   DB/시스템 용량 활용도
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_capacity_utilization_273
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 274) up_s_report_kpi_summary_274
   핵심 KPI 리포트
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_kpi_summary_274
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 275) up_s_report_growth_metrics_275
   성장 지표(고객/거래량)
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_growth_metrics_275
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 276) up_s_report_retention_metrics_276
   고객 유지율/활성도
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_retention_metrics_276
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 277) up_s_report_churn_signals_277
   이탈 조짐 신호
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_churn_signals_277
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 278) up_s_report_latency_outliers_278
   지연시간 아웃라이어
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_latency_outliers_278
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 279) up_s_report_compliance_exceptions_279
   컴플라이언스 예외
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_compliance_exceptions_279
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 280) up_s_report_permission_changes_280
   권한 변경 이력 보고
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_permission_changes_280
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 281) up_s_report_holidays_effect_281
   휴장일 영향 분석
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_holidays_effect_281
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 282) up_s_report_liquidity_report_282
   유동성 지표 보고
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_liquidity_report_282
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 283) up_s_report_execution_costs_283
   체결 비용 분석
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_execution_costs_283
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 284) up_s_report_fees_vs_revenue_284
   수수료 vs 수익 분석
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_fees_vs_revenue_284
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 285) up_s_report_customer_segments_285
   고객 세그먼트 분석
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_customer_segments_285
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 286) up_s_report_symbol_correlations_286
   심볼 상관관계 분석
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_symbol_correlations_286
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 287) up_s_report_risk_scenarios_287
   리스크 시나리오 스트레스 테스트
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_risk_scenarios_287
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 288) up_s_report_pnl_attribution_288
   손익 귀속 분석
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_pnl_attribution_288
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 289) up_s_report_regulatory_audit_pack_289
   감사 패키지 생성/압축
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_regulatory_audit_pack_289
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 290) up_s_report_daily_ops_checklist_290
   운영 점검표 보고
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_daily_ops_checklist_290
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 291) up_s_report_capacity_forecast_291
   용량 예측/증설 계획
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_capacity_forecast_291
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 292) up_s_report_job_sla_breaches_292
   잡 SLA 위반 보고
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_job_sla_breaches_292
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 293) up_s_report_alert_summary_293
   알림/경보 요약
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_alert_summary_293
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 294) up_s_report_statement_resend_294
   명세서 재발송 현황
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_statement_resend_294
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 295) up_s_report_watchlist_activity_295
   관심종목 활동 보고
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_watchlist_activity_295
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 296) up_s_report_regulatory_holdings_296
   규제 기준 보유 현황
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_regulatory_holdings_296
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 297) up_s_report_dividend_summary_297
   배당 요약 보고
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_dividend_summary_297
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 298) up_s_report_system_health_298
   시스템 헬스/장애 지표 요약
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_system_health_298
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 299) up_s_report_user_activity_299
   사용자 활동/접속 리포트
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_user_activity_299
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO


/* 300) up_s_report_sla_scorecard_300
   서비스 레벨 스코어카드
*/
CREATE OR ALTER PROCEDURE dbo.up_s_report_sla_scorecard_300
    @from_dt datetime2 = NULL,
    @to_dt datetime2 = NULL,
    @format varchar(10) = 'CSV',
    @filter_json nvarchar(max) = NULL,
    @recipient nvarchar(320) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    -- no paging for report procs

    -- Generic query placeholder; replace with actual SELECT against reporting tables.
    SELECT OBJECT_NAME(@@PROCID) AS proc_name;

    IF EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.sys_audit_log') AND type='U')
    BEGIN
        INSERT dbo.sys_audit_log(event_type, ref_id, details, created_at, created_by)
        VALUES('PROC.' + OBJECT_NAME(@@PROCID), NULL,
               CONCAT('report ',COALESCE(@format,''),' period=',COALESCE(CONVERT(varchar(32),@from_dt,126),''),'~',COALESCE(CONVERT(varchar(32),@to_dt,126),'')),
               SYSUTCDATETIME(), N'system');
    END

END
GO

