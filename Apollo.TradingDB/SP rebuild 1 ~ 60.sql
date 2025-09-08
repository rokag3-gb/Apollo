/* ==============================================================
   SP Catalog & Run Log DDL (공통)  — idempotent rebuild
   ============================================================== */
SET NOCOUNT ON;
SET XACT_ABORT ON;

-- 1) sp_run_* (간단 실행 로깅)
IF OBJECT_ID('dbo.sp_run_param','U') IS NOT NULL DROP TABLE dbo.sp_run_param;
IF OBJECT_ID('dbo.sp_run_log','U')   IS NOT NULL DROP TABLE dbo.sp_run_log;

CREATE TABLE dbo.sp_run_log(
  run_id        BIGINT IDENTITY(1,1) PRIMARY KEY,
  sp_name       SYSNAME NOT NULL,
  started_utc   DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
  finished_utc  DATETIME2(3) NULL,
  status        NVARCHAR(16) NOT NULL,           -- START/OK/ERROR
  error_message NVARCHAR(4000) NULL
);

CREATE TABLE dbo.sp_run_param(
  run_param_id BIGINT IDENTITY(1,1) PRIMARY KEY,
  run_id       BIGINT NOT NULL,
  param_name   NVARCHAR(128) NOT NULL,
  param_value  NVARCHAR(4000) NULL
);

-- 2) sp_catalog (이번 배치에선 1~60만 insert, 이후 배치에서 계속 추가)
IF OBJECT_ID('dbo.sp_catalog','U') IS NOT NULL DROP TABLE dbo.sp_catalog;
CREATE TABLE dbo.sp_catalog(
  sp_id          INT         NOT NULL PRIMARY KEY,
  sp_name        SYSNAME     NOT NULL,
  category_no    INT         NOT NULL,
  category_name  NVARCHAR(50)NOT NULL,
  caller         NVARCHAR(20)NOT NULL,           -- 일반사용자/증권사 관리자/시스템배치
  type           NVARCHAR(8) NOT NULL,           -- SELECT/EXECUTE
  summary        NVARCHAR(400) NULL,
  remark         NVARCHAR(400) NULL
);

SET IDENTITY_INSERT dbo.sp_run_log OFF;  -- (명시적 ID 사용 안함)
GO

/* ==============================================================
   sp_catalog (Batch 1: 1~60)
   ============================================================== */
INSERT dbo.sp_catalog(sp_id, sp_name, category_no, category_name, caller, type, summary, remark)
VALUES
-- Orders / Executions (1~15)
(1 ,N'up_t_order_place_limit_001',      8,N'주문·체결',N'일반사용자',N'EXECUTE',N'지정가 주문 접수 및 기본 검증/감사로그/홀드 반영',N'RW 트랜잭션, READ COMMITTED'),
(2 ,N'up_t_order_place_market_002',     8,N'주문·체결',N'일반사용자',N'EXECUTE',N'시장가 주문 접수',N'RW 트랜잭션'),
(3 ,N'up_t_order_cancel_003',           8,N'주문·체결',N'일반사용자',N'EXECUTE',N'주문 취소',N'상태/이벤트 기록'),
(4 ,N'up_t_order_amend_price_004',      8,N'주문·체결',N'일반사용자',N'EXECUTE',N'주문 가격 변경',N'낙관적 동시성'),
(5 ,N'up_t_order_amend_qty_005',        8,N'주문·체결',N'일반사용자',N'EXECUTE',N'주문 수량 변경',N'낙관적 동시성'),
(6 ,N'up_s_order_status_006',           8,N'주문·체결',N'일반사용자',N'SELECT', N'단일 주문 상태/이벤트 조회',N'조인/필터'),
(7 ,N'up_s_order_history_007',          8,N'주문·체결',N'일반사용자',N'SELECT', N'계좌/기간별 주문 이력 페이징 조회',N'인덱스 사용'),
(8 ,N'up_t_order_route_primary_008',    8,N'주문·체결',N'시스템배치',N'EXECUTE',N'주문 라우팅 플래그 업데이트(기본 라우트)',N'이벤트 부가'),
(9 ,N'up_t_order_risk_check_009',       8,N'주문·체결',N'시스템배치',N'EXECUTE',N'계좌 리스크 한도 점검 및 위반 기록',N'리스크 테이블 참조'),
(10,N'up_s_orders_by_symbol_010',       8,N'주문·체결',N'일반사용자',N'SELECT', N'심볼/기간 기준 주문 조회',N'필터/정렬'),

(11,N'up_t_execution_apply_011',        8,N'주문·체결',N'시스템배치',N'EXECUTE',N'체결 반영(실행 추가, 주문상태 갱신)',N'RW 트랜잭션'),
(12,N'up_s_execution_history_012',      8,N'주문·체결',N'일반사용자',N'SELECT', N'계좌/기간 체결 이력 조회',N'커버링 인덱스'),
(13,N'up_t_trade_ledger_post_013',      8,N'주문·체결',N'시스템배치',N'EXECUTE',N'체결→거래원장 기록화',N'RW 트랜잭션'),
(14,N'up_s_trade_ledger_query_014',     8,N'주문·체결',N'일반사용자',N'SELECT', N'거래원장 조회(계좌/심볼/기간)',N'범위스캔'),
(15,N'up_t_fee_tax_apply_015',          8,N'주문·체결',N'시스템배치',N'EXECUTE',N'체결 수수료/세금 재계산 반영',N'수정 갱신'),

-- Funding / Cash (16~20)
(16,N'up_t_funding_deposit_016',        5,N'입금·출금',N'일반사용자',N'EXECUTE',N'입금 처리(현금원장 기록, 잔액계산)',N'RW 트랜잭션'),
(17,N'up_t_funding_withdraw_017',       5,N'입금·출금',N'일반사용자',N'EXECUTE',N'출금 처리(잔액 체크/원장기록)',N'RW 트랜잭션'),
(18,N'up_t_funding_transfer_internal_018',5,N'입금·출금',N'일반사용자',N'EXECUTE',N'계좌 간 내부 이체',N'트랜잭션/양쪽 원장'),
(19,N'up_s_cash_ledger_query_019',      5,N'입금·출금',N'일반사용자',N'SELECT', N'현금원장 조회',N'필터/정렬'),
(20,N'up_t_funding_retry_failed_020',   5,N'입금·출금',N'시스템배치',N'EXECUTE',N'실패건 재시도 마킹',N'잡 로그 기록'),

-- Symbols / Market Data (21~25)
(21,N'up_t_symbol_create_021',          2,N'기준정보',N'증권사 관리자',N'EXECUTE',N'신규 심볼 등록',N'기준정보 작성'),
(22,N'up_t_symbol_update_022',          2,N'기준정보',N'증권사 관리자',N'EXECUTE',N'심볼 속성 갱신',N'기준정보 수정'),
(23,N'up_s_symbol_search_023',          2,N'기준정보',N'일반사용자',N'SELECT', N'심볼/ISIN 검색',N'인덱스/부분일치'),
(24,N'up_t_market_price_ingest_024',    9,N'시세·마켓데이터',N'시스템배치',N'EXECUTE',N'분봉틱 삽입/업서트',N'집계용 시세'),
(25,N'up_s_market_price_last_025',      9,N'시세·마켓데이터',N'일반사용자',N'SELECT', N'최근 시세 조회',N'MAX(ts)'),

-- Positions / PnL (26~30)
(26,N'up_t_position_apply_exec_026',    7,N'포지션·잔고',N'시스템배치',N'EXECUTE',N'체결 반영 포지션 증감/평단가 갱신',N'UPSERT'),
(27,N'up_s_position_by_account_027',    7,N'포지션·잔고',N'일반사용자',N'SELECT', N'계좌 보유포지션 조회',N'UQ 활용'),
(28,N'up_t_position_snapshot_save_028', 7,N'포지션·잔고',N'시스템배치',N'EXECUTE',N'포지션 스냅샷 저장',N'일배치'),
(29,N'up_s_position_snapshot_get_029',  7,N'포지션·잔고',N'증권사 관리자',N'SELECT', N'스냅샷 조회',N'키 조회'),
(30,N'up_s_pnl_daily_query_030',        7,N'포지션·잔고',N'증권사 관리자',N'SELECT', N'일별 PnL 집계 조회',N'날짜 키'),

-- Risk / Compliance (31~38)
(31,N'up_t_risk_limit_set_031',         10,N'리스크·컴플',N'증권사 관리자',N'EXECUTE',N'계좌 리스크 한도 설정/수정',N'Upsert'),
(32,N'up_t_risk_exposure_snapshot_032', 10,N'리스크·컴플',N'시스템배치',N'EXECUTE',N'노출/마진 스냅샷 적재',N'계산값 입력'),
(33,N'up_s_risk_exposure_recent_033',   10,N'리스크·컴플',N'증권사 관리자',N'SELECT', N'최근 노출 스냅샷 조회',N'정렬/Top'),
(34,N'up_t_risk_breach_log_034',        10,N'리스크·컴플',N'시스템배치',N'EXECUTE',N'위반 로그 적재',N'알림연계'),
(35,N'up_s_risk_breach_recent_035',     10,N'리스크·컴플',N'증권사 관리자',N'SELECT', N'최근 위반 로그 조회',N'기간/계좌'),
(36,N'up_t_cmp_rule_upsert_036',        10,N'리스크·컴플',N'증권사 관리자',N'EXECUTE',N'컴플라이언스 룰 등록/수정',N'룰 JSON'),
(37,N'up_t_cmp_alert_ack_037',          10,N'리스크·컴플',N'증권사 관리자',N'EXECUTE',N'알림 ACK 처리',N'상태 변경'),
(38,N'up_s_cmp_alerts_038',             10,N'리스크·컴플',N'증권사 관리자',N'SELECT', N'알림 목록 조회',N'상태/기간'),

-- Reporting / Ops / Audit / Users (39~60)
(39,N'up_t_report_sched_create_039',    12,N'리포트',N'증권사 관리자',N'EXECUTE',N'리포트 잡 등록',N'sys_job_run 기록'),
(40,N'up_s_report_orders_vs_exec_040',  12,N'리포트',N'증권사 관리자',N'SELECT', N'주문 vs 체결 비교 집계',N'조인집계'),
(41,N'up_t_audit_log_write_041',        11,N'감사·로그',N'시스템배치',N'EXECUTE',N'감사로그 적재',N'표준 포맷'),
(42,N'up_s_audit_log_recent_042',       11,N'감사·로그',N'증권사 관리자',N'SELECT', N'최근 감사로그 조회',N'기간/액터'),
(43,N'up_t_user_create_043',            1,N'인증·사용자',N'증권사 관리자',N'EXECUTE',N'사용자 생성',N'권한 롤 세팅'),
(44,N'up_t_user_disable_044',           1,N'인증·사용자',N'증권사 관리자',N'EXECUTE',N'사용자 비활성',N'상태변경'),
(45,N'up_s_user_list_045',              1,N'인증·사용자',N'증권사 관리자',N'SELECT', N'사용자 목록/필터',N'부분검색'),
(46,N'up_t_api_client_register_046',    1,N'인증·사용자',N'증권사 관리자',N'EXECUTE',N'API 클라이언트 등록',N'레이트리밋'),
(47,N'up_t_api_client_set_rate_047',    1,N'인증·사용자',N'증권사 관리자',N'EXECUTE',N'API 레이트리밋 변경',N'업데이트'),
(48,N'up_s_api_clients_048',            1,N'인증·사용자',N'증권사 관리자',N'SELECT', N'API 클라이언트 리스트',N'상태/정렬'),
(49,N'up_t_notification_send_049',      11,N'감사·로그',N'시스템배치',N'EXECUTE',N'알림 발행(이메일/웹훅)',N'메타 포함'),
(50,N'up_s_notification_recent_050',    11,N'감사·로그',N'증권사 관리자',N'SELECT', N'최근 알림 조회',N'채널/레벨'),
(51,N'up_t_fee_schedule_upsert_051',    6,N'수수료·세금',N'증권사 관리자',N'EXECUTE',N'수수료 스케줄 등록/수정',N'Upsert'),
(52,N'up_s_fee_schedule_052',           6,N'수수료·세금',N'증권사 관리자',N'SELECT', N'계좌/유형별 수수료 스케줄',N'기간필터'),
(53,N'up_t_tax_rule_upsert_053',        6,N'수수료·세금',N'증권사 관리자',N'EXECUTE',N'세금 룰 등록/수정',N'국가/유형'),
(54,N'up_s_tax_rules_054',              6,N'수수료·세금',N'증권사 관리자',N'SELECT', N'세금 룰 조회',N'유효기간'),
(55,N'up_s_order_exec_join_055',        12,N'리포트',N'증권사 관리자',N'SELECT', N'주문-체결 조인 상세',N'페이징'),
(56,N'up_s_cash_flow_by_day_056',       12,N'리포트',N'증권사 관리자',N'SELECT', N'일자별 현금흐름 집계',N'원장합계'),
(57,N'up_t_order_bulk_cancel_057',      8,N'주문·체결',N'증권사 관리자',N'EXECUTE',N'기간/조건 기반 일괄 취소',N'이벤트 기록'),
(58,N'up_t_order_event_append_058',     8,N'주문·체결',N'증권사 관리자',N'EXECUTE',N'주문 이벤트 수동 추가',N'감사용'),
(59,N'up_s_order_events_059',           8,N'주문·체결',N'SELECT', N'주문 이벤트 조회',N'정렬/필터'),
(60,N'up_s_orders_vs_cash_060',         12,N'리포트',N'증권사 관리자',N'SELECT', N'주문금액 vs 자금흐름 비교',N'집계리포트');
GO

/* ==============================================================
   헬퍼: 공통 로깅 매크로 스타일 (개별 SP에 인라인로직으로 포함)
   ============================================================== */
/* 각 SP에서 아래 패턴 사용:
    DECLARE @run_id BIGINT, @sp SYSNAME = OBJECT_SCHEMA_NAME(@@PROCID)+'.'+OBJECT_NAME(@@PROCID);
    INSERT dbo.sp_run_log(sp_name, started_utc, status) VALUES(@sp, SYSUTCDATETIME(),'START');
    SET @run_id = SCOPE_IDENTITY();
    INSERT dbo.sp_run_param(run_id,param_name,param_value) VALUES
      (@run_id,'@p1',CONVERT(NVARCHAR(128),@p1)), ...;
   성공 시:
    UPDATE dbo.sp_run_log SET finished_utc=SYSUTCDATETIME(), status='OK' WHERE run_id=@run_id;
   실패 시 CATCH에서:
    UPDATE dbo.sp_run_log SET finished_utc=SYSUTCDATETIME(), status='ERROR', error_message=ERROR_MESSAGE() WHERE run_id=@run_id;
*/

/* ==============================================================
   Stored Procedures — Batch 1 (1~60)
   ============================================================== */

-------------------------------------------------------------------------------
-- 1) 지정가 주문 접수
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_limit_001
  @account_id   BIGINT,
  @symbol       NVARCHAR(32),
  @side         CHAR(1),                -- 'B'/'S'
  @qty          DECIMAL(18,4),
  @price        DECIMAL(18,4),
  @tif          NVARCHAR(8) = N'GTC',
  @source       NVARCHAR(16) = N'api'
AS
BEGIN
  SET NOCOUNT ON;
  DECLARE @run_id BIGINT, @sp SYSNAME=OBJECT_SCHEMA_NAME(@@PROCID)+'.'+OBJECT_NAME(@@PROCID);
  BEGIN TRY
    INSERT dbo.sp_run_log(sp_name,started_utc,status) VALUES(@sp,SYSUTCDATETIME(),'START');
    SET @run_id=SCOPE_IDENTITY();
    INSERT dbo.sp_run_param(run_id,param_name,param_value) VALUES
      (@run_id,'@account_id',CONVERT(NVARCHAR(50),@account_id)),
      (@run_id,'@symbol',@symbol),(@run_id,'@side',@side),
      (@run_id,'@qty',CONVERT(NVARCHAR(50),@qty)),
      (@run_id,'@price',CONVERT(NVARCHAR(50),@price)),
      (@run_id,'@tif',@tif),(@run_id,'@source',@source);

    DECLARE @security_id BIGINT;
    SELECT @security_id=s.security_id FROM dbo.ref_security s WITH (NOLOCK)
    WHERE s.symbol=@symbol AND s.delisted_date IS NULL;
    IF @security_id IS NULL THROW 51000, 'Invalid symbol', 1;

    DECLARE @acct_exists BIT = CASE WHEN EXISTS(SELECT 1 FROM dbo.cust_account WHERE account_id=@account_id AND closed_at IS NULL) THEN 1 ELSE 0 END;
    IF @acct_exists=0 THROW 51001, 'Invalid/Closed account', 1;

    BEGIN TRAN;
      INSERT dbo.ord_order(account_id,security_id,side,order_type,tif,qty,price,status,source,create_time,update_time)
      VALUES(@account_id,@security_id,@side,N'LIMIT',@tif,@qty,@price,N'New',@source,SYSUTCDATETIME(),SYSUTCDATETIME());

      DECLARE @order_id BIGINT = SCOPE_IDENTITY();
      INSERT dbo.ord_order_event(order_id,event_time,event_type,payload)
      VALUES(@order_id,SYSUTCDATETIME(),N'Submit',JSON_OBJECT('src':@source,'tif':@tif,'px':@price,'qty':@qty));

      -- 간단 감사
      INSERT dbo.sys_audit_log(actor,action,target_table,target_pk,before_json,after_json,ip)
      VALUES(N'client:'+ISNULL(@source,'api'),N'ORDER_PLACE',N'ord_order',CONVERT(NVARCHAR(50),@order_id),NULL,
             JSON_OBJECT('symbol':@symbol,'side':@side,'qty':@qty,'price':@price),'N/A');
    COMMIT;

    UPDATE dbo.sp_run_log SET finished_utc=SYSUTCDATETIME(), status='OK' WHERE run_id=@run_id;
    SELECT @order_id AS order_id;
  END TRY
  BEGIN CATCH
    IF XACT_STATE()<>0 ROLLBACK;
    UPDATE dbo.sp_run_log SET finished_utc=SYSUTCDATETIME(),status='ERROR',error_message=ERROR_MESSAGE() WHERE run_id=@run_id;
    THROW;
  END CATCH
END
GO

-------------------------------------------------------------------------------
-- 2) 시장가 주문 접수
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_order_place_market_002
  @account_id BIGINT,
  @symbol     NVARCHAR(32),
  @side       CHAR(1),
  @qty        DECIMAL(18,4),
  @source     NVARCHAR(16)=N'api'
AS
BEGIN
  SET NOCOUNT ON;
  DECLARE @run_id BIGINT, @sp SYSNAME=OBJECT_SCHEMA_NAME(@@PROCID)+'.'+OBJECT_NAME(@@PROCID);
  BEGIN TRY
    INSERT dbo.sp_run_log(sp_name,started_utc,status) VALUES(@sp,SYSUTCDATETIME(),'START');
    SET @run_id=SCOPE_IDENTITY();
    INSERT dbo.sp_run_param(run_id,param_name,param_value) VALUES
      (@run_id,'@account_id',CONVERT(NVARCHAR(50),@account_id)),
      (@run_id,'@symbol',@symbol),(@run_id,'@side',@side),
      (@run_id,'@qty',CONVERT(NVARCHAR(50),@qty));

    DECLARE @security_id BIGINT;
    SELECT @security_id=security_id FROM dbo.ref_security WITH (NOLOCK)
    WHERE symbol=@symbol AND delisted_date IS NULL;
    IF @security_id IS NULL THROW 51000, 'Invalid symbol', 1;

    BEGIN TRAN;
      INSERT dbo.ord_order(account_id,security_id,side,order_type,tif,qty,price,status,source,create_time,update_time)
      VALUES(@account_id,@security_id,@side,N'MARKET',N'IOC',@qty,NULL,N'New',@source,SYSUTCDATETIME(),SYSUTCDATETIME());
      DECLARE @order_id BIGINT=SCOPE_IDENTITY();

      INSERT dbo.ord_order_event(order_id,event_time,event_type,payload)
      VALUES(@order_id,SYSUTCDATETIME(),N'Submit',JSON_OBJECT('src':@source,'type':N'MARKET','qty':@qty));
    COMMIT;

    UPDATE dbo.sp_run_log SET finished_utc=SYSUTCDATETIME(), status='OK' WHERE run_id=@run_id;
    SELECT @order_id AS order_id;
  END TRY
  BEGIN CATCH
    IF XACT_STATE()<>0 ROLLBACK;
    UPDATE dbo.sp_run_log SET finished_utc=SYSUTCDATETIME(),status='ERROR',error_message=ERROR_MESSAGE() WHERE run_id=@run_id;
    THROW;
  END CATCH
END
GO

-------------------------------------------------------------------------------
-- 3) 주문 취소
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_order_cancel_003
  @order_id BIGINT,
  @reason   NVARCHAR(100)=N'user_cancel'
AS
BEGIN
  SET NOCOUNT ON;
  DECLARE @run_id BIGINT,@sp SYSNAME=OBJECT_SCHEMA_NAME(@@PROCID)+'.'+OBJECT_NAME(@@PROCID);
  BEGIN TRY
    INSERT dbo.sp_run_log(sp_name,started_utc,status) VALUES(@sp,SYSUTCDATETIME(),'START');
    SET @run_id=SCOPE_IDENTITY();
    INSERT dbo.sp_run_param(run_id,param_name,param_value) VALUES
      (@run_id,'@order_id',CONVERT(NVARCHAR(50),@order_id)),
      (@run_id,'@reason',@reason);

    BEGIN TRAN;
      UPDATE dbo.ord_order
      SET status=N'Cancelled', update_time=SYSUTCDATETIME()
      WHERE order_id=@order_id AND status IN (N'New',N'PartiallyFilled');
      INSERT dbo.ord_order_event(order_id,event_time,event_type,payload)
      VALUES(@order_id,SYSUTCDATETIME(),N'Cancel',JSON_OBJECT('reason':@reason));
      INSERT dbo.sys_audit_log(actor,action,target_table,target_pk,before_json,after_json,ip)
      VALUES(N'user',N'ORDER_CANCEL',N'ord_order',CONVERT(NVARCHAR(50),@order_id),NULL,JSON_OBJECT('reason':@reason),'N/A');
    COMMIT;

    UPDATE dbo.sp_run_log SET finished_utc=SYSUTCDATETIME(),status='OK' WHERE run_id=@run_id;
  END TRY
  BEGIN CATCH
    IF XACT_STATE()<>0 ROLLBACK;
    UPDATE dbo.sp_run_log SET finished_utc=SYSUTCDATETIME(),status='ERROR',error_message=ERROR_MESSAGE() WHERE run_id=@run_id;
    THROW;
  END CATCH
END
GO

-------------------------------------------------------------------------------
-- 4) 주문 가격 변경
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_order_amend_price_004
  @order_id BIGINT,
  @new_price DECIMAL(18,4)
AS
BEGIN
  SET NOCOUNT ON;
  DECLARE @run_id BIGINT,@sp SYSNAME=OBJECT_SCHEMA_NAME(@@PROCID)+'.'+OBJECT_NAME(@@PROCID);
  BEGIN TRY
    INSERT dbo.sp_run_log(sp_name,started_utc,status) VALUES(@sp,SYSUTCDATETIME(),'START');
    SET @run_id=SCOPE_IDENTITY();
    INSERT dbo.sp_run_param(run_id,param_name,param_value) VALUES
      (@run_id,'@order_id',CONVERT(NVARCHAR(50),@order_id)),
      (@run_id,'@new_price',CONVERT(NVARCHAR(50),@new_price));
    BEGIN TRAN;
      UPDATE dbo.ord_order
      SET price=@new_price, update_time=SYSUTCDATETIME()
      WHERE order_id=@order_id AND order_type=N'LIMIT' AND status IN (N'New',N'PartiallyFilled');
      INSERT dbo.ord_order_event(order_id,event_time,event_type,payload)
      VALUES(@order_id,SYSUTCDATETIME(),N'Replace',JSON_OBJECT('field':N'price','value':@new_price));
    COMMIT;
    UPDATE dbo.sp_run_log SET finished_utc=SYSUTCDATETIME(),status='OK' WHERE run_id=@run_id;
  END TRY
  BEGIN CATCH
    IF XACT_STATE()<>0 ROLLBACK;
    UPDATE dbo.sp_run_log SET finished_utc=SYSUTCDATETIME(),status='ERROR',error_message=ERROR_MESSAGE() WHERE run_id=@run_id;
    THROW;
  END CATCH
END
GO

-------------------------------------------------------------------------------
-- 5) 주문 수량 변경
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_order_amend_qty_005
  @order_id BIGINT,
  @new_qty  DECIMAL(18,4)
AS
BEGIN
  SET NOCOUNT ON;
  DECLARE @run_id BIGINT,@sp SYSNAME=OBJECT_SCHEMA_NAME(@@PROCID)+'.'+OBJECT_NAME(@@PROCID);
  BEGIN TRY
    INSERT dbo.sp_run_log(sp_name,started_utc,status) VALUES(@sp,SYSUTCDATETIME(),'START');
    SET @run_id=SCOPE_IDENTITY();
    INSERT dbo.sp_run_param(run_id,param_name,param_value) VALUES
      (@run_id,'@order_id',CONVERT(NVARCHAR(50),@order_id)),
      (@run_id,'@new_qty',CONVERT(NVARCHAR(50),@new_qty));
    BEGIN TRAN;
      UPDATE dbo.ord_order
      SET qty=@new_qty, update_time=SYSUTCDATETIME()
      WHERE order_id=@order_id AND status IN (N'New',N'PartiallyFilled');
      INSERT dbo.ord_order_event(order_id,event_time,event_type,payload)
      VALUES(@order_id,SYSUTCDATETIME(),N'Replace',JSON_OBJECT('field':N'qty','value':@new_qty));
    COMMIT;
    UPDATE dbo.sp_run_log SET finished_utc=SYSUTCDATETIME(),status='OK' WHERE run_id=@run_id;
  END TRY
  BEGIN CATCH
    IF XACT_STATE()<>0 ROLLBACK;
    UPDATE dbo.sp_run_log SET finished_utc=SYSUTCDATETIME(),status='ERROR',error_message=ERROR_MESSAGE() WHERE run_id=@run_id;
    THROW;
  END CATCH
END
GO

-------------------------------------------------------------------------------
-- 6) 단일 주문 상태/이벤트 조회
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_order_status_006
  @order_id BIGINT
AS
BEGIN
  SET NOCOUNT ON;
  SELECT o.order_id,o.account_id,o.security_id,s.symbol,o.side,o.order_type,o.tif,o.qty,o.price,o.status,o.create_time,o.update_time
  FROM dbo.ord_order o
  JOIN dbo.ref_security s ON s.security_id=o.security_id
  WHERE o.order_id=@order_id;

  SELECT e.event_time,e.event_type,e.payload
  FROM dbo.ord_order_event e
  WHERE e.order_id=@order_id
  ORDER BY e.event_time;
END
GO

-------------------------------------------------------------------------------
-- 7) 계좌/기간 주문 이력 (페이징)
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_order_history_007
  @account_id BIGINT,
  @from_utc   DATETIME2,
  @to_utc     DATETIME2,
  @page       INT = 1,
  @page_size  INT = 100
AS
BEGIN
  SET NOCOUNT ON;
  WITH base AS (
    SELECT o.*, s.symbol, ROW_NUMBER() OVER(ORDER BY o.create_time DESC) AS rn
    FROM dbo.ord_order o
    JOIN dbo.ref_security s ON s.security_id=o.security_id
    WHERE o.account_id=@account_id AND o.create_time BETWEEN @from_utc AND @to_utc
  )
  SELECT *
  FROM base
  WHERE rn BETWEEN (@page-1)*@page_size+1 AND @page*@page_size
  ORDER BY rn;
END
GO

-------------------------------------------------------------------------------
-- 8) 기본 라우트 플래그 (예시: 이벤트 추가로 대체)
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_order_route_primary_008
  @order_id BIGINT
AS
BEGIN
  SET NOCOUNT ON;
  INSERT dbo.ord_order_event(order_id,event_time,event_type,payload)
  VALUES(@order_id,SYSUTCDATETIME(),N'Route',N'{"route":"PRIMARY"}');
END
GO

-------------------------------------------------------------------------------
-- 9) 리스크 체크(간단 위반 기록)
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_order_risk_check_009
  @account_id BIGINT,
  @metric     NVARCHAR(32),
  @value      DECIMAL(18,4),
  @threshold  DECIMAL(18,4)
AS
BEGIN
  SET NOCOUNT ON;
  IF @value > @threshold
    INSERT dbo.risk_breach_log(account_id,ts,limit_id,metric,value,threshold)
    VALUES(@account_id,SYSUTCDATETIME(),NULL,@metric,@value,@threshold);
END
GO

-------------------------------------------------------------------------------
-- 10) 심볼/기간 주문 조회
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_orders_by_symbol_010
  @symbol   NVARCHAR(32),
  @from_utc DATETIME2,
  @to_utc   DATETIME2
AS
BEGIN
  SET NOCOUNT ON;
  SELECT o.*, s.symbol
  FROM dbo.ord_order o
  JOIN dbo.ref_security s ON s.security_id=o.security_id
  WHERE s.symbol=@symbol AND o.create_time BETWEEN @from_utc AND @to_utc
  ORDER BY o.create_time DESC;
END
GO

-------------------------------------------------------------------------------
-- 11) 체결 반영
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_execution_apply_011
  @order_id  BIGINT,
  @exec_qty  DECIMAL(18,4),
  @exec_price DECIMAL(18,4),
  @venue     NVARCHAR(16) = N'XNAS',
  @liq       CHAR(1) = 'M'
AS
BEGIN
  SET NOCOUNT ON;
  DECLARE @run_id BIGINT,@sp SYSNAME=OBJECT_SCHEMA_NAME(@@PROCID)+'.'+OBJECT_NAME(@@PROCID);
  BEGIN TRY
    INSERT dbo.sp_run_log(sp_name,started_utc,status) VALUES(@sp,SYSUTCDATETIME(),'START');
    SET @run_id=SCOPE_IDENTITY();

    BEGIN TRAN;
      INSERT dbo.exe_execution(order_id,exec_time,exec_qty,exec_price,venue,liquidity)
      VALUES(@order_id,SYSUTCDATETIME(),@exec_qty,@exec_price,@venue,@liq);
      UPDATE dbo.ord_order
      SET status=CASE WHEN qty<=@exec_qty OR qty<=ISNULL((SELECT SUM(exec_qty) FROM dbo.exe_execution WHERE order_id=@order_id),0) THEN N'Filled' ELSE N'PartiallyFilled' END,
          update_time=SYSUTCDATETIME()
      WHERE order_id=@order_id;
    COMMIT;

    UPDATE dbo.sp_run_log SET finished_utc=SYSUTCDATETIME(),status='OK' WHERE run_id=@run_id;
  END TRY
  BEGIN CATCH
    IF XACT_STATE()<>0 ROLLBACK;
    UPDATE dbo.sp_run_log SET finished_utc=SYSUTCDATETIME(),status='ERROR',error_message=ERROR_MESSAGE() WHERE run_id=@run_id;
    THROW;
  END CATCH
END
GO

-------------------------------------------------------------------------------
-- 12) 체결 이력 조회
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_execution_history_012
  @account_id BIGINT,
  @from_utc   DATETIME2,
  @to_utc     DATETIME2
AS
BEGIN
  SET NOCOUNT ON;
  SELECT x.*, o.account_id, s.symbol
  FROM dbo.exe_execution x
  JOIN dbo.ord_order o ON o.order_id=x.order_id
  JOIN dbo.ref_security s ON s.security_id=o.security_id
  WHERE o.account_id=@account_id AND x.exec_time BETWEEN @from_utc AND @to_utc
  ORDER BY x.exec_time DESC;
END
GO

-------------------------------------------------------------------------------
-- 13) 체결→거래원장 기록
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_trade_ledger_post_013
  @execution_id BIGINT
AS
BEGIN
  SET NOCOUNT ON;
  DECLARE @order_id BIGINT,@account_id BIGINT,@security_id BIGINT,@qty DECIMAL(18,4),@price DECIMAL(18,4),@ts DATETIME2(3);
  SELECT @order_id=e.order_id, @qty=e.exec_qty, @price=e.exec_price, @ts=e.exec_time
  FROM dbo.exe_execution e WHERE e.execution_id=@execution_id;
  SELECT @account_id=o.account_id,@security_id=o.security_id FROM dbo.ord_order o WHERE o.order_id=@order_id;

  IF @order_id IS NULL RETURN;

  INSERT dbo.trd_trade_ledger(account_id,security_id,trade_time,qty,price,fee,tax,execution_id)
  VALUES(@account_id,@security_id,@ts,@qty,@price,0,0,@execution_id);
END
GO

-------------------------------------------------------------------------------
-- 14) 거래원장 조회
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_trade_ledger_query_014
  @account_id BIGINT,
  @from_utc   DATETIME2,
  @to_utc     DATETIME2
AS
BEGIN
  SET NOCOUNT ON;
  SELECT tl.*, s.symbol
  FROM dbo.trd_trade_ledger tl
  JOIN dbo.ref_security s ON s.security_id=tl.security_id
  WHERE tl.account_id=@account_id AND tl.trade_time BETWEEN @from_utc AND @to_utc
  ORDER BY tl.trade_time DESC;
END
GO

-------------------------------------------------------------------------------
-- 15) 체결 수수료/세금 계산 반영(단순)
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_fee_tax_apply_015
  @execution_id BIGINT,
  @fee_rate     DECIMAL(9,6)=0.001,
  @tax_rate     DECIMAL(9,6)=0.0005
AS
BEGIN
  SET NOCOUNT ON;
  DECLARE @qty DECIMAL(18,4),@px DECIMAL(18,4);
  SELECT @qty=exec_qty,@px=exec_price FROM dbo.exe_execution WHERE execution_id=@execution_id;
  IF @qty IS NULL RETURN;
  UPDATE dbo.exe_execution
    SET fee = @qty*@px*@fee_rate, tax=@qty*@px*@tax_rate
  WHERE execution_id=@execution_id;
END
GO

-------------------------------------------------------------------------------
-- 16) 입금
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_funding_deposit_016
  @account_id BIGINT,
  @currency   CHAR(3),
  @amount     DECIMAL(18,4),
  @ref_id     NVARCHAR(64)=NULL
AS
BEGIN
  SET NOCOUNT ON;
  DECLARE @last_balance DECIMAL(18,4)=ISNULL((SELECT TOP 1 balance_after FROM dbo.acct_cash_ledger
                                              WHERE account_id=@account_id AND currency_code=@currency
                                              ORDER BY txn_time DESC),0);
  DECLARE @new_balance DECIMAL(18,4)=@last_balance+@amount;
  INSERT dbo.acct_cash_ledger(account_id,currency_code,txn_time,txn_type,amount,balance_after,ref_id)
  VALUES(@account_id,@currency,SYSUTCDATETIME(),N'DEPOSIT',@amount,@new_balance,@ref_id);
END
GO

-------------------------------------------------------------------------------
-- 17) 출금
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_funding_withdraw_017
  @account_id BIGINT,
  @currency   CHAR(3),
  @amount     DECIMAL(18,4),
  @ref_id     NVARCHAR(64)=NULL
AS
BEGIN
  SET NOCOUNT ON;
  DECLARE @last_balance DECIMAL(18,4)=ISNULL((SELECT TOP 1 balance_after FROM dbo.acct_cash_ledger
                                              WHERE account_id=@account_id AND currency_code=@currency
                                              ORDER BY txn_time DESC),0);
  IF @last_balance < @amount THROW 52001,'Insufficient balance',1;
  DECLARE @new_balance DECIMAL(18,4)=@last_balance-@amount;
  INSERT dbo.acct_cash_ledger(account_id,currency_code,txn_time,txn_type,amount,balance_after,ref_id)
  VALUES(@account_id,@currency,SYSUTCDATETIME(),N'WITHDRAW',-@amount,@new_balance,@ref_id);
END
GO

-------------------------------------------------------------------------------
-- 18) 내부이체
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_funding_transfer_internal_018
  @from_account BIGINT,
  @to_account   BIGINT,
  @currency     CHAR(3),
  @amount       DECIMAL(18,4),
  @ref_id       NVARCHAR(64)=NULL
AS
BEGIN
  SET NOCOUNT ON;
  BEGIN TRAN;
    EXEC dbo.up_t_funding_withdraw_017 @account_id=@from_account, @currency=@currency, @amount=@amount, @ref_id=@ref_id;
    EXEC dbo.up_t_funding_deposit_016  @account_id=@to_account,   @currency=@currency, @amount=@amount, @ref_id=@ref_id;
  COMMIT;
END
GO

-------------------------------------------------------------------------------
-- 19) 현금원장 조회
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_cash_ledger_query_019
  @account_id BIGINT,
  @currency   CHAR(3),
  @from_utc   DATETIME2,
  @to_utc     DATETIME2
AS
BEGIN
  SET NOCOUNT ON;
  SELECT * FROM dbo.acct_cash_ledger
  WHERE account_id=@account_id AND currency_code=@currency
    AND txn_time BETWEEN @from_utc AND @to_utc
  ORDER BY txn_time DESC;
END
GO

-------------------------------------------------------------------------------
-- 20) 실패건 재시도 마킹(예: sys_job_run)
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_funding_retry_failed_020
  @job_name NVARCHAR(100),
  @note     NVARCHAR(MAX)=NULL
AS
BEGIN
  SET NOCOUNT ON;
  INSERT dbo.sys_job_run(job_name,started_at,ended_at,status,metrics_json)
  VALUES(@job_name,SYSUTCDATETIME(),NULL,N'SCHEDULED',@note);
END
GO

-------------------------------------------------------------------------------
-- 21) 심볼 생성
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_symbol_create_021
  @symbol NVARCHAR(32),
  @isin   NVARCHAR(12)=NULL,
  @exchange_id INT,
  @type_code   NVARCHAR(16),
  @currency    CHAR(3),
  @lot_size    INT = 1,
  @listed_date DATE = NULL
AS
BEGIN
  SET NOCOUNT ON;
  IF @listed_date IS NULL SET @listed_date = CAST(SYSUTCDATETIME() AS DATE);
  INSERT dbo.ref_security(symbol,isin,exchange_id,type_code,currency_code,lot_size,listed_date,delisted_date)
  VALUES(@symbol,@isin,@exchange_id,@type_code,@currency,@lot_size,@listed_date,NULL);
END
GO

-------------------------------------------------------------------------------
-- 22) 심볼 업데이트
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_symbol_update_022
  @security_id BIGINT,
  @currency    CHAR(3)=NULL,
  @lot_size    INT=NULL,
  @delisted_date DATE=NULL
AS
BEGIN
  SET NOCOUNT ON;
  UPDATE dbo.ref_security
    SET currency_code=COALESCE(@currency,currency_code),
        lot_size     =COALESCE(@lot_size,lot_size),
        delisted_date=COALESCE(@delisted_date,delisted_date)
  WHERE security_id=@security_id;
END
GO

-------------------------------------------------------------------------------
-- 23) 심볼 검색
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_symbol_search_023
  @q NVARCHAR(64)
AS
BEGIN
  SET NOCOUNT ON;
  SELECT TOP 200 security_id,symbol,isin,exchange_id,type_code,currency_code,listed_date,delisted_date
  FROM dbo.ref_security
  WHERE symbol LIKE @q+'%' OR ISNULL(isin,'') LIKE @q+'%'
  ORDER BY symbol;
END
GO

-------------------------------------------------------------------------------
-- 24) 시세 인제스트(분해상도)
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_market_price_ingest_024
  @security_id BIGINT,
  @ts          DATETIME2(0),
  @last_price  DECIMAL(18,6),
  @bid         DECIMAL(18,6)=NULL,
  @ask         DECIMAL(18,6)=NULL,
  @bid_size    INT=NULL,
  @ask_size    INT=NULL
AS
BEGIN
  SET NOCOUNT ON;
  INSERT dbo.mkt_price_intraday(security_id,ts,last_price,bid,ask,bid_size,ask_size)
  VALUES(@security_id,@ts,@last_price,@bid,@ask,@bid_size,@ask_size);
END
GO

-------------------------------------------------------------------------------
-- 25) 최근 시세
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_market_price_last_025
  @security_id BIGINT
AS
BEGIN
  SET NOCOUNT ON;
  SELECT TOP 1 * FROM dbo.mkt_price_intraday
  WHERE security_id=@security_id
  ORDER BY ts DESC;
END
GO

-------------------------------------------------------------------------------
-- 26) 포지션 반영(체결 기반)
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_position_apply_exec_026
  @execution_id BIGINT
AS
BEGIN
  SET NOCOUNT ON;
  DECLARE @order_id BIGINT,@account_id BIGINT,@security_id BIGINT,@qty DECIMAL(18,4),@price DECIMAL(18,6),@exec_time DATETIME2(3);
  SELECT @order_id=e.order_id,@qty=e.exec_qty,@price=e.exec_price,@exec_time=e.exec_time FROM dbo.exe_execution e WHERE e.execution_id=@execution_id;
  SELECT @account_id=o.account_id,@security_id=o.security_id FROM dbo.ord_order o WHERE o.order_id=@order_id;
  IF @order_id IS NULL RETURN;

  BEGIN TRAN;
    -- upsert 포지션
    IF EXISTS(SELECT 1 FROM dbo.pos_position WHERE account_id=@account_id AND security_id=@security_id)
    BEGIN
      DECLARE @old_qty DECIMAL(18,4),@old_avg DECIMAL(18,6);
      SELECT @old_qty=qty,@old_avg=avg_price FROM dbo.pos_position WHERE account_id=@account_id AND security_id=@security_id;
      DECLARE @new_qty DECIMAL(18,4)=@old_qty+@qty;
      DECLARE @new_avg DECIMAL(18,6)=CASE WHEN @new_qty=0 THEN 0 ELSE ((@old_qty*@old_avg)+(@qty*@price))/NULLIF(@new_qty,0) END;
      UPDATE dbo.pos_position
        SET qty=@new_qty, avg_price=@new_avg, last_update_time=SYSUTCDATETIME()
      WHERE account_id=@account_id AND security_id=@security_id;
    END
    ELSE
    BEGIN
      INSERT dbo.pos_position(account_id,security_id,qty,avg_price,last_update_time)
      VALUES(@account_id,@security_id,@qty,@price,SYSUTCDATETIME());
    END
  COMMIT;
END
GO

-------------------------------------------------------------------------------
-- 27) 계좌 포지션 조회
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_position_by_account_027
  @account_id BIGINT
AS
BEGIN
  SET NOCOUNT ON;
  SELECT p.*, s.symbol FROM dbo.pos_position p
  JOIN dbo.ref_security s ON s.security_id=p.security_id
  WHERE p.account_id=@account_id
  ORDER BY s.symbol;
END
GO

-------------------------------------------------------------------------------
-- 28) 포지션 스냅샷 저장
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_position_snapshot_save_028
  @account_id BIGINT
AS
BEGIN
  SET NOCOUNT ON;
  DECLARE @ts DATETIME2(3)=SYSUTCDATETIME();
  INSERT dbo.risk_exposure_snapshot(account_id,ts,gross,net,var_1d,margin_required)
  SELECT p.account_id, @ts,
         SUM(ABS(p.qty)*ISNULL(mp.last_price,0)) AS gross,
         SUM(p.qty*ISNULL(mp.last_price,0)) AS net,
         0 AS var_1d, 0 AS margin_required
  FROM dbo.pos_position p
  LEFT JOIN dbo.mkt_price_intraday mp ON mp.security_id=p.security_id AND mp.ts=(SELECT MAX(ts) FROM dbo.mkt_price_intraday WHERE security_id=p.security_id)
  WHERE p.account_id=@account_id
  GROUP BY p.account_id;
END
GO

-------------------------------------------------------------------------------
-- 29) 포지션 스냅샷 조회(최근)
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_position_snapshot_get_029
  @account_id BIGINT
AS
BEGIN
  SET NOCOUNT ON;
  SELECT TOP 1 * FROM dbo.risk_exposure_snapshot
  WHERE account_id=@account_id
  ORDER BY ts DESC;
END
GO

-------------------------------------------------------------------------------
-- 30) 일별 PnL 조회
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_pnl_daily_query_030
  @account_id BIGINT,
  @from_date  DATE,
  @to_date    DATE
AS
BEGIN
  SET NOCOUNT ON;
  SELECT * FROM dbo.pnl_daily
  WHERE account_id=@account_id AND as_of_date BETWEEN @from_date AND @to_date
  ORDER BY as_of_date;
END
GO

-------------------------------------------------------------------------------
-- 31) 리스크 한도 설정
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_risk_limit_set_031
  @account_id BIGINT,
  @kind       NVARCHAR(32),
  @threshold  DECIMAL(18,4),
  @window_min INT = 1440,
  @active     BIT = 1
AS
BEGIN
  SET NOCOUNT ON;
  IF EXISTS(SELECT 1 FROM dbo.acct_risk_limit WHERE account_id=@account_id AND kind=@kind)
    UPDATE dbo.acct_risk_limit SET threshold=@threshold, window_min=@window_min, active=@active
    WHERE account_id=@account_id AND kind=@kind;
  ELSE
    INSERT dbo.acct_risk_limit(account_id,kind,threshold,window_min,active)
    VALUES(@account_id,@kind,@threshold,@window_min,@active);
END
GO

-------------------------------------------------------------------------------
-- 32) 노출 스냅샷 적재(직접 입력)
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_risk_exposure_snapshot_032
  @account_id BIGINT,
  @gross DECIMAL(18,4),
  @net   DECIMAL(18,4),
  @var1d DECIMAL(18,4),
  @margin DECIMAL(18,4)
AS
BEGIN
  SET NOCOUNT ON;
  INSERT dbo.risk_exposure_snapshot(account_id,ts,gross,net,var_1d,margin_required)
  VALUES(@account_id,SYSUTCDATETIME(),@gross,@net,@var1d,@margin);
END
GO

-------------------------------------------------------------------------------
-- 33) 최근 노출 스냅샷 조회
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_risk_exposure_recent_033
  @account_id BIGINT
AS
BEGIN
  SET NOCOUNT ON;
  SELECT TOP 20 * FROM dbo.risk_exposure_snapshot
  WHERE account_id=@account_id
  ORDER BY ts DESC;
END
GO

-------------------------------------------------------------------------------
-- 34) 위반 로그 적재
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_risk_breach_log_034
  @account_id BIGINT,
  @metric NVARCHAR(32),
  @value  DECIMAL(18,4),
  @threshold DECIMAL(18,4)
AS
BEGIN
  SET NOCOUNT ON;
  INSERT dbo.risk_breach_log(account_id,ts,limit_id,metric,value,threshold)
  VALUES(@account_id,SYSUTCDATETIME(),NULL,@metric,@value,@threshold);
END
GO

-------------------------------------------------------------------------------
-- 35) 최근 위반 로그 조회
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_risk_breach_recent_035
  @account_id BIGINT,
  @from_utc   DATETIME2,
  @to_utc     DATETIME2
AS
BEGIN
  SET NOCOUNT ON;
  SELECT TOP 500 * FROM dbo.risk_breach_log
  WHERE account_id=@account_id AND ts BETWEEN @from_utc AND @to_utc
  ORDER BY ts DESC;
END
GO

-------------------------------------------------------------------------------
-- 36) 컴플 룰 업서트
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_cmp_rule_upsert_036
  @rule_id BIGINT = NULL OUTPUT,
  @name NVARCHAR(100),
  @rule_expr NVARCHAR(MAX),
  @severity NVARCHAR(16)
AS
BEGIN
  SET NOCOUNT ON;
  IF @rule_id IS NULL
  BEGIN
    INSERT dbo.cmp_rule(name,rule_expr,severity) VALUES(@name,@rule_expr,@severity);
    SET @rule_id = SCOPE_IDENTITY();
  END
  ELSE
    UPDATE dbo.cmp_rule SET name=@name, rule_expr=@rule_expr, severity=@severity WHERE rule_id=@rule_id;
  SELECT @rule_id AS rule_id;
END
GO

-------------------------------------------------------------------------------
-- 37) 알림 ACK
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_cmp_alert_ack_037
  @alert_id BIGINT,
  @notes NVARCHAR(400)=NULL
AS
BEGIN
  SET NOCOUNT ON;
  UPDATE dbo.cmp_alert SET status=N'Ack', ts=SYSUTCDATETIME(), notes=COALESCE(@notes,notes)
  WHERE alert_id=@alert_id;
END
GO

-------------------------------------------------------------------------------
-- 38) 알림 조회
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_cmp_alerts_038
  @status NVARCHAR(16)=NULL,
  @from_utc DATETIME2=NULL,
  @to_utc   DATETIME2=NULL
AS
BEGIN
  SET NOCOUNT ON;
  SELECT TOP 1000 * FROM dbo.cmp_alert
  WHERE (@status IS NULL OR status=@status)
    AND (@from_utc IS NULL OR ts>=@from_utc)
    AND (@to_utc   IS NULL OR ts<=@to_utc)
  ORDER BY ts DESC;
END
GO

-------------------------------------------------------------------------------
-- 39) 리포트 잡 등록 (sys_job_run)
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_report_sched_create_039
  @job_name NVARCHAR(100),
  @params   NVARCHAR(MAX)=NULL
AS
BEGIN
  SET NOCOUNT ON;
  INSERT dbo.sys_job_run(job_name,started_at,ended_at,status,metrics_json)
  VALUES(@job_name,SYSUTCDATETIME(),NULL,N'SCHEDULED',@params);
END
GO

-------------------------------------------------------------------------------
-- 40) 주문 vs 체결 비교 집계
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_report_orders_vs_exec_040
  @from_utc DATETIME2,
  @to_utc   DATETIME2
AS
BEGIN
  SET NOCOUNT ON;
  SELECT s.symbol,
         COUNT(DISTINCT o.order_id) AS order_cnt,
         COUNT(x.execution_id)      AS exec_cnt,
         SUM(o.qty)                 AS order_qty,
         SUM(x.exec_qty)            AS exec_qty
  FROM dbo.ord_order o
  JOIN dbo.ref_security s ON s.security_id=o.security_id
  LEFT JOIN dbo.exe_execution x ON x.order_id=o.order_id AND x.exec_time BETWEEN @from_utc AND @to_utc
  WHERE o.create_time BETWEEN @from_utc AND @to_utc
  GROUP BY s.symbol
  ORDER BY s.symbol;
END
GO

-------------------------------------------------------------------------------
-- 41) 감사로그 쓰기
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_audit_log_write_041
  @actor NVARCHAR(64),
  @action NVARCHAR(64),
  @table NVARCHAR(64),
  @pk    NVARCHAR(128)=NULL,
  @before NVARCHAR(MAX)=NULL,
  @after  NVARCHAR(MAX)=NULL,
  @ip NVARCHAR(64)=NULL
AS
BEGIN
  SET NOCOUNT ON;
  INSERT dbo.sys_audit_log(actor,action,target_table,target_pk,before_json,after_json,ip)
  VALUES(@actor,@action,@table,@pk,@before,@after,@ip);
END
GO

-------------------------------------------------------------------------------
-- 42) 최근 감사로그
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_audit_log_recent_042
  @from_utc DATETIME2,
  @to_utc   DATETIME2,
  @actor_like NVARCHAR(64)=NULL
AS
BEGIN
  SET NOCOUNT ON;
  SELECT TOP 1000 * FROM dbo.sys_audit_log
  WHERE ts BETWEEN @from_utc AND @to_utc
    AND (@actor_like IS NULL OR actor LIKE @actor_like + N'%')
  ORDER BY ts DESC;
END
GO

-------------------------------------------------------------------------------
-- 43) 사용자 생성
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_user_create_043
  @login_id NVARCHAR(64),
  @role     NVARCHAR(32) = N'trader'
AS
BEGIN
  SET NOCOUNT ON;
  INSERT dbo.sys_user(login_id,role,status,last_login) VALUES(@login_id,@role,N'ACTIVE',NULL);
END
GO

-------------------------------------------------------------------------------
-- 44) 사용자 비활성
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_user_disable_044
  @user_id BIGINT
AS
BEGIN
  SET NOCOUNT ON;
  UPDATE dbo.sys_user SET status=N'DISABLED' WHERE user_id=@user_id;
END
GO

-------------------------------------------------------------------------------
-- 45) 사용자 목록
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_user_list_045
  @role   NVARCHAR(32)=NULL,
  @status NVARCHAR(16)=NULL
AS
BEGIN
  SET NOCOUNT ON;
  SELECT * FROM dbo.sys_user
  WHERE (@role IS NULL OR role=@role)
    AND (@status IS NULL OR status=@status)
  ORDER BY user_id DESC;
END
GO

-------------------------------------------------------------------------------
-- 46) API 클라이언트 등록
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_api_client_register_046
  @name NVARCHAR(100),
  @rate_limit INT = 1000
AS
BEGIN
  SET NOCOUNT ON;
  INSERT dbo.sys_api_client(name,status,rate_limit) VALUES(@name,N'ACTIVE',@rate_limit);
END
GO

-------------------------------------------------------------------------------
-- 47) API Rate 변경
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_api_client_set_rate_047
  @client_id BIGINT,
  @rate_limit INT
AS
BEGIN
  SET NOCOUNT ON;
  UPDATE dbo.sys_api_client SET rate_limit=@rate_limit WHERE client_id=@client_id;
END
GO

-------------------------------------------------------------------------------
-- 48) API 클라이언트 목록
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_api_clients_048
  @status NVARCHAR(16)=NULL
AS
BEGIN
  SET NOCOUNT ON;
  SELECT * FROM dbo.sys_api_client
  WHERE (@status IS NULL OR status=@status)
  ORDER BY client_id DESC;
END
GO

-------------------------------------------------------------------------------
-- 49) 알림 발행
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_notification_send_049
  @channel NVARCHAR(16),   -- email/webhook
  @level   NVARCHAR(16),   -- INFO/WARN/ERROR
  @message NVARCHAR(400),
  @meta    NVARCHAR(MAX)=NULL
AS
BEGIN
  SET NOCOUNT ON;
  INSERT dbo.sys_notification(channel,level,message,meta_json)
  VALUES(@channel,@level,@message,@meta);
END
GO

-------------------------------------------------------------------------------
-- 50) 최근 알림
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_notification_recent_050
  @channel NVARCHAR(16)=NULL,
  @level   NVARCHAR(16)=NULL,
  @from_utc DATETIME2=NULL
AS
BEGIN
  SET NOCOUNT ON;
  SELECT TOP 500 * FROM dbo.sys_notification
  WHERE (@channel IS NULL OR channel=@channel)
    AND (@level IS NULL OR level=@level)
    AND (@from_utc IS NULL OR ts>=@from_utc)
  ORDER BY ts DESC;
END
GO

-------------------------------------------------------------------------------
-- 51) 수수료 스케줄 업서트
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_fee_schedule_upsert_051
  @account_id BIGINT,
  @fee_type_id INT,
  @value       DECIMAL(18,6),
  @unit        NVARCHAR(8),   -- PCT/FIXED
  @from_date   DATE,
  @to_date     DATE = NULL
AS
BEGIN
  SET NOCOUNT ON;
  IF EXISTS(SELECT 1 FROM dbo.acct_fee_schedule WHERE account_id=@account_id AND fee_type_id=@fee_type_id AND effective_from=@from_date)
    UPDATE dbo.acct_fee_schedule
      SET value=@value, unit=@unit, effective_to=@to_date
    WHERE account_id=@account_id AND fee_type_id=@fee_type_id AND effective_from=@from_date;
  ELSE
    INSERT dbo.acct_fee_schedule(account_id,fee_type_id,value,unit,effective_from,effective_to)
    VALUES(@account_id,@fee_type_id,@value,@unit,@from_date,@to_date);
END
GO

-------------------------------------------------------------------------------
-- 52) 수수료 스케줄 조회
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_fee_schedule_052
  @account_id BIGINT,
  @fee_type_id INT=NULL
AS
BEGIN
  SET NOCOUNT ON;
  SELECT * FROM dbo.acct_fee_schedule
  WHERE account_id=@account_id
    AND (@fee_type_id IS NULL OR fee_type_id=@fee_type_id)
  ORDER BY effective_from DESC;
END
GO

-------------------------------------------------------------------------------
-- 53) 세금 룰 업서트
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_tax_rule_upsert_053
  @tax_rule_id INT = NULL OUTPUT,
  @country_code CHAR(2),
  @security_type NVARCHAR(16),
  @rate DECIMAL(9,6),
  @effective_from DATE,
  @effective_to   DATE = NULL
AS
BEGIN
  SET NOCOUNT ON;
  IF @tax_rule_id IS NULL
  BEGIN
    INSERT dbo.ref_tax_rule(country_code,security_type,rate,effective_from,effective_to)
    VALUES(@country_code,@security_type,@rate,@effective_from,@effective_to);
    SET @tax_rule_id = SCOPE_IDENTITY();
  END
  ELSE
    UPDATE dbo.ref_tax_rule
      SET country_code=@country_code, security_type=@security_type, rate=@rate,
          effective_from=@effective_from, effective_to=@effective_to
    WHERE tax_rule_id=@tax_rule_id;
  SELECT @tax_rule_id AS tax_rule_id;
END
GO

-------------------------------------------------------------------------------
-- 54) 세금 룰 조회
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_tax_rules_054
  @country_code CHAR(2)=NULL,
  @security_type NVARCHAR(16)=NULL
AS
BEGIN
  SET NOCOUNT ON;
  SELECT * FROM dbo.ref_tax_rule
  WHERE (@country_code IS NULL OR country_code=@country_code)
    AND (@security_type IS NULL OR security_type=@security_type)
  ORDER BY effective_from DESC;
END
GO

-------------------------------------------------------------------------------
-- 55) 주문-체결 상세 조인(페이징)
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_order_exec_join_055
  @account_id BIGINT=NULL,
  @symbol NVARCHAR(32)=NULL,
  @from_utc DATETIME2,
  @to_utc   DATETIME2,
  @page INT=1, @page_size INT=100
AS
BEGIN
  SET NOCOUNT ON;
  WITH base AS (
    SELECT o.order_id,o.account_id,s.symbol,o.side,o.order_type,o.qty,o.price,o.status,o.create_time,
           x.execution_id,x.exec_qty,x.exec_price,x.exec_time,
           ROW_NUMBER() OVER(ORDER BY o.create_time DESC) AS rn
    FROM dbo.ord_order o
    JOIN dbo.ref_security s ON s.security_id=o.security_id
    LEFT JOIN dbo.exe_execution x ON x.order_id=o.order_id AND x.exec_time BETWEEN @from_utc AND @to_utc
    WHERE o.create_time BETWEEN @from_utc AND @to_utc
      AND (@account_id IS NULL OR o.account_id=@account_id)
      AND (@symbol IS NULL OR s.symbol=@symbol)
  )
  SELECT * FROM base
  WHERE rn BETWEEN (@page-1)*@page_size+1 AND @page*@page_size
  ORDER BY rn;
END
GO

-------------------------------------------------------------------------------
-- 56) 일별 현금 흐름 집계
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_cash_flow_by_day_056
  @account_id BIGINT,
  @currency   CHAR(3),
  @from_date  DATE,
  @to_date    DATE
AS
BEGIN
  SET NOCOUNT ON;
  SELECT CAST(txn_time AS DATE) AS d,
         SUM(CASE WHEN txn_type=N'DEPOSIT'  THEN amount ELSE 0 END) AS dep,
         SUM(CASE WHEN txn_type=N'WITHDRAW' THEN -amount ELSE 0 END) AS wdr,
         SUM(amount) AS net
  FROM dbo.acct_cash_ledger
  WHERE account_id=@account_id AND currency_code=@currency
    AND txn_time >= @from_date AND txn_time < DATEADD(DAY,1,@to_date)
  GROUP BY CAST(txn_time AS DATE)
  ORDER BY d;
END
GO

-------------------------------------------------------------------------------
-- 57) 주문 일괄 취소 (기간/심볼/계좌 조건)
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_order_bulk_cancel_057
  @from_utc DATETIME2,
  @to_utc   DATETIME2,
  @account_id BIGINT=NULL,
  @symbol     NVARCHAR(32)=NULL
AS
BEGIN
  SET NOCOUNT ON;
  DECLARE @security_id BIGINT=NULL;
  IF @symbol IS NOT NULL SELECT @security_id=security_id FROM dbo.ref_security WHERE symbol=@symbol;

  UPDATE o
    SET o.status=N'Cancelled', o.update_time=SYSUTCDATETIME()
  FROM dbo.ord_order o
  WHERE o.create_time BETWEEN @from_utc AND @to_utc
    AND (@account_id IS NULL OR o.account_id=@account_id)
    AND (@security_id IS NULL OR o.security_id=@security_id)
    AND o.status IN (N'New',N'PartiallyFilled');

  INSERT dbo.ord_order_event(order_id,event_time,event_type,payload)
  SELECT o.order_id,SYSUTCDATETIME(),N'Cancel',N'{"bulk":true}'
  FROM dbo.ord_order o
  WHERE o.create_time BETWEEN @from_utc AND @to_utc
    AND (@account_id IS NULL OR o.account_id=@account_id)
    AND (@security_id IS NULL OR o.security_id=@security_id);
END
GO

-------------------------------------------------------------------------------
-- 58) 주문 이벤트 수동 추가
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_t_order_event_append_058
  @order_id BIGINT,
  @event_type NVARCHAR(16),
  @payload NVARCHAR(MAX)=NULL
AS
BEGIN
  SET NOCOUNT ON;
  INSERT dbo.ord_order_event(order_id,event_time,event_type,payload)
  VALUES(@order_id,SYSUTCDATETIME(),@event_type,@payload);
END
GO

-------------------------------------------------------------------------------
-- 59) 주문 이벤트 조회
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_order_events_059
  @order_id BIGINT
AS
BEGIN
  SET NOCOUNT ON;
  SELECT * FROM dbo.ord_order_event
  WHERE order_id=@order_id
  ORDER BY event_time DESC;
END
GO

-------------------------------------------------------------------------------
-- 60) 주문금액 vs 자금흐름 비교 리포트(간단)
-------------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.up_s_orders_vs_cash_060
  @account_id BIGINT,
  @from_utc   DATETIME2,
  @to_utc     DATETIME2
AS
BEGIN
  SET NOCOUNT ON;
  ;WITH ord AS (
    SELECT SUM(ISNULL(price,0)*qty) AS order_notional
    FROM dbo.ord_order o
    WHERE o.account_id=@account_id AND o.create_time BETWEEN @from_utc AND @to_utc
  ),
  cash AS (
    SELECT SUM(amount) AS cash_flow
    FROM dbo.acct_cash_ledger a
    WHERE a.account_id=@account_id AND a.txn_time BETWEEN @from_utc AND @to_utc
  )
  SELECT (SELECT order_notional FROM ord) AS order_notional,
         (SELECT cash_flow     FROM cash) AS cash_flow;
END
GO
