
/********************************************************************************************
 Trading Ledger OLTP/Analytics Schema (SQL Server) + Sample Seed Data
 Sections covered:
  1) Reference
  2) Customer/Account/Portfolio
  3) Trading Core (Orders/Executions/Ledger/Positions/Prices)
  4) Risk & Compliance
  5) Ops & Audit
  6) Analytics Star Schema (dim/fact)
 
 Notes
 - Keep everything in dbo for simplicity.
 - Seed sizes are controlled by variables.
 - Uses a generated Numbers table for fast seeding.
 - Tested target: SQL Server 2019+
********************************************************************************************/

SET NOCOUNT ON;
SET XACT_ABORT ON;

---------------------------------------------------------------------------------------------
-- Create Database (optional) - comment out if you want to use an existing DB
---------------------------------------------------------------------------------------------
/*
IF DB_ID('TradingDB') IS NULL
BEGIN
  CREATE DATABASE TradingDB;
END
GO
USE TradingDB;
GO
*/

---------------------------------------------------------------------------------------------
-- Drop existing objects (idempotent rebuild)
---------------------------------------------------------------------------------------------
PRINT 'Dropping old objects if exist...';

-- Drop Facts/Dimensions first (FK dependencies)
IF OBJECT_ID('dbo.fact_pnl_daily','U') IS NOT NULL DROP TABLE dbo.fact_pnl_daily;
IF OBJECT_ID('dbo.fact_position_snapshot','U') IS NOT NULL DROP TABLE dbo.fact_position_snapshot;
IF OBJECT_ID('dbo.fact_execution','U') IS NOT NULL DROP TABLE dbo.fact_execution;
IF OBJECT_ID('dbo.fact_order','U') IS NOT NULL DROP TABLE dbo.fact_order;
IF OBJECT_ID('dbo.dim_exchange','U') IS NOT NULL DROP TABLE dbo.dim_exchange;
IF OBJECT_ID('dbo.dim_security','U') IS NOT NULL DROP TABLE dbo.dim_security;
IF OBJECT_ID('dbo.dim_account','U') IS NOT NULL DROP TABLE dbo.dim_account;
IF OBJECT_ID('dbo.dim_date','U') IS NOT NULL DROP TABLE dbo.dim_date;

-- Ops/Audit
IF OBJECT_ID('dbo.sys_notification','U') IS NOT NULL DROP TABLE dbo.sys_notification;
IF OBJECT_ID('dbo.sys_job_run','U') IS NOT NULL DROP TABLE dbo.sys_job_run;
IF OBJECT_ID('dbo.sys_audit_log','U') IS NOT NULL DROP TABLE dbo.sys_audit_log;
IF OBJECT_ID('dbo.sys_api_client','U') IS NOT NULL DROP TABLE dbo.sys_api_client;
IF OBJECT_ID('dbo.sys_user','U') IS NOT NULL DROP TABLE dbo.sys_user;

-- Risk & Compliance
IF OBJECT_ID('dbo.cmp_alert','U') IS NOT NULL DROP TABLE dbo.cmp_alert;
IF OBJECT_ID('dbo.cmp_rule','U') IS NOT NULL DROP TABLE dbo.cmp_rule;
IF OBJECT_ID('dbo.risk_breach_log','U') IS NOT NULL DROP TABLE dbo.risk_breach_log;
IF OBJECT_ID('dbo.risk_exposure_snapshot','U') IS NOT NULL DROP TABLE dbo.risk_exposure_snapshot;

-- Trading Core
IF OBJECT_ID('dbo.pnl_daily','U') IS NOT NULL DROP TABLE dbo.pnl_daily;
IF OBJECT_ID('dbo.pos_position_lot','U') IS NOT NULL DROP TABLE dbo.pos_position_lot;
IF OBJECT_ID('dbo.pos_position','U') IS NOT NULL DROP TABLE dbo.pos_position;
IF OBJECT_ID('dbo.trd_trade_ledger','U') IS NOT NULL DROP TABLE dbo.trd_trade_ledger;
IF OBJECT_ID('dbo.exe_execution','U') IS NOT NULL DROP TABLE dbo.exe_execution;
IF OBJECT_ID('dbo.ord_order_event','U') IS NOT NULL DROP TABLE dbo.ord_order_event;
IF OBJECT_ID('dbo.ord_order','U') IS NOT NULL DROP TABLE dbo.ord_order;
IF OBJECT_ID('dbo.mkt_price_eod','U') IS NOT NULL DROP TABLE dbo.mkt_price_eod;
IF OBJECT_ID('dbo.mkt_price_intraday','U') IS NOT NULL DROP TABLE dbo.mkt_price_intraday;

-- Accounts
IF OBJECT_ID('dbo.acct_risk_limit','U') IS NOT NULL DROP TABLE dbo.acct_risk_limit;
IF OBJECT_ID('dbo.acct_fee_schedule','U') IS NOT NULL DROP TABLE dbo.acct_fee_schedule;
IF OBJECT_ID('dbo.acct_cash_ledger','U') IS NOT NULL DROP TABLE dbo.acct_cash_ledger;
IF OBJECT_ID('dbo.cust_margin_account','U') IS NOT NULL DROP TABLE dbo.cust_margin_account;
IF OBJECT_ID('dbo.cust_account','U') IS NOT NULL DROP TABLE dbo.cust_account;
IF OBJECT_ID('dbo.cust_customer','U') IS NOT NULL DROP TABLE dbo.cust_customer;

-- Reference
IF OBJECT_ID('dbo.ref_corporate_action','U') IS NOT NULL DROP TABLE dbo.ref_corporate_action;
IF OBJECT_ID('dbo.ref_tax_rule','U') IS NOT NULL DROP TABLE dbo.ref_tax_rule;
IF OBJECT_ID('dbo.ref_fee_type','U') IS NOT NULL DROP TABLE dbo.ref_fee_type;
IF OBJECT_ID('dbo.ref_security','U') IS NOT NULL DROP TABLE dbo.ref_security;
IF OBJECT_ID('dbo.ref_security_type','U') IS NOT NULL DROP TABLE dbo.ref_security_type;
IF OBJECT_ID('dbo.ref_trading_session','U') IS NOT NULL DROP TABLE dbo.ref_trading_session;
IF OBJECT_ID('dbo.ref_holiday','U') IS NOT NULL DROP TABLE dbo.ref_holiday;
IF OBJECT_ID('dbo.ref_market_segment','U') IS NOT NULL DROP TABLE dbo.ref_market_segment;
IF OBJECT_ID('dbo.ref_exchange','U') IS NOT NULL DROP TABLE dbo.ref_exchange;
IF OBJECT_ID('dbo.ref_currency','U') IS NOT NULL DROP TABLE dbo.ref_currency;
IF OBJECT_ID('dbo.ref_country','U') IS NOT NULL DROP TABLE dbo.ref_country;

IF OBJECT_ID('dbo.Numbers','U') IS NOT NULL DROP TABLE dbo.Numbers;
PRINT 'Drop completed.';

---------------------------------------------------------------------------------------------
-- Helper: Numbers table for fast bulk inserts
---------------------------------------------------------------------------------------------
PRINT 'Creating Numbers table...';

CREATE TABLE dbo.Numbers(n INT NOT NULL PRIMARY KEY);
;WITH cte(n) AS (
  SELECT 1
  UNION ALL
  SELECT n+1 FROM cte WHERE n < 200000
)
INSERT dbo.Numbers(n)
SELECT n FROM cte
OPTION (MAXRECURSION 0);

---------------------------------------------------------------------------------------------
-- 1) Reference
---------------------------------------------------------------------------------------------
PRINT 'Creating Reference tables...';

CREATE TABLE dbo.ref_country (
  country_code  CHAR(2)    NOT NULL PRIMARY KEY,
  name          NVARCHAR(100) NOT NULL
);

CREATE TABLE dbo.ref_currency (
  currency_code CHAR(3)    NOT NULL PRIMARY KEY,
  name          NVARCHAR(50) NOT NULL,
  minor_unit    TINYINT    NOT NULL DEFAULT 2
);

CREATE TABLE dbo.ref_exchange (
  exchange_id   INT IDENTITY(1,1) PRIMARY KEY,
  code          NVARCHAR(16) NOT NULL UNIQUE,
  name          NVARCHAR(100) NOT NULL,
  tz            NVARCHAR(40) NOT NULL,  -- e.g., Asia/Seoul
  country_code  CHAR(2) NOT NULL
);

CREATE TABLE dbo.ref_market_segment (
  segment_id    INT IDENTITY(1,1) PRIMARY KEY,
  exchange_id   INT NOT NULL,
  name          NVARCHAR(100) NOT NULL
);

CREATE TABLE dbo.ref_holiday (
  exchange_id   INT NOT NULL,
  holiday_date  DATE NOT NULL,
  description   NVARCHAR(200) NULL,
  CONSTRAINT PK_ref_holiday PRIMARY KEY(exchange_id, holiday_date)
);

CREATE TABLE dbo.ref_trading_session (
  session_id    INT IDENTITY(1,1) PRIMARY KEY,
  exchange_id   INT NOT NULL,
  session_type  NVARCHAR(16) NOT NULL,   -- REG/EXT
  start_time    TIME(0) NOT NULL,
  end_time      TIME(0) NOT NULL
);

CREATE TABLE dbo.ref_security_type (
  type_code     NVARCHAR(16) NOT NULL PRIMARY KEY,  -- Equity/ETF/Bond/Option/Future
  description   NVARCHAR(100) NULL
);

CREATE TABLE dbo.ref_security (
  security_id   BIGINT IDENTITY(1,1) PRIMARY KEY,
  symbol        NVARCHAR(32)  NOT NULL,
  isin          NVARCHAR(12)  NULL,
  exchange_id   INT           NOT NULL,
  type_code     NVARCHAR(16)  NOT NULL,
  currency_code CHAR(3)       NOT NULL,
  lot_size      INT           NOT NULL DEFAULT 1,
  listed_date   DATE          NOT NULL,
  delisted_date DATE          NULL
);
CREATE INDEX IX_ref_security_symbol ON dbo.ref_security(symbol);

CREATE TABLE dbo.ref_fee_type (
  fee_type_id   INT IDENTITY(1,1) PRIMARY KEY,
  name          NVARCHAR(100) NOT NULL,
  calc_method   NVARCHAR(20)  NOT NULL   -- PCT/FIXED/TIERED
);

CREATE TABLE dbo.ref_tax_rule (
  tax_rule_id   INT IDENTITY(1,1) PRIMARY KEY,
  country_code  CHAR(2)       NOT NULL,
  security_type NVARCHAR(16)  NOT NULL,
  rate          DECIMAL(9,6)  NOT NULL,  -- e.g., 0.001
  effective_from DATE         NOT NULL,
  effective_to   DATE         NULL
);

CREATE TABLE dbo.ref_corporate_action (
  ca_id         BIGINT IDENTITY(1,1) PRIMARY KEY,
  security_id   BIGINT         NOT NULL,
  ca_type       NVARCHAR(20)   NOT NULL,  -- DIV/SPLIT/MERGER
  ex_date       DATE           NOT NULL,
  pay_date      DATE           NULL,
  ratio         DECIMAL(18,8)  NULL,
  amount        DECIMAL(18,8)  NULL
);

---------------------------------------------------------------------------------------------
-- 2) Customer / Account / Portfolio
---------------------------------------------------------------------------------------------
PRINT 'Creating Customer/Account tables...';

CREATE TABLE dbo.cust_customer (
  customer_id   BIGINT IDENTITY(1,1) PRIMARY KEY,
  name          NVARCHAR(100) NOT NULL,
  birth         DATE          NULL,
  country_code  CHAR(2)       NOT NULL,
  kyc_level     TINYINT       NOT NULL DEFAULT 1,
  risk_profile  NVARCHAR(16)  NOT NULL DEFAULT N'NORMAL'
);

CREATE TABLE dbo.cust_account (
  account_id    BIGINT IDENTITY(1,1) PRIMARY KEY,
  customer_id   BIGINT        NOT NULL,
  base_currency CHAR(3)       NOT NULL,
  account_type  NVARCHAR(16)  NOT NULL, -- 개인/법인
  opened_at     DATETIME2(3)  NOT NULL DEFAULT SYSUTCDATETIME(),
  closed_at     DATETIME2(3)  NULL
);

CREATE TABLE dbo.cust_margin_account (
  margin_account_id BIGINT IDENTITY(1,1) PRIMARY KEY,
  account_id        BIGINT NOT NULL UNIQUE,
  credit_limit      DECIMAL(18,2) NOT NULL DEFAULT 0,
  maintenance_margin_rate DECIMAL(9,6) NOT NULL DEFAULT 0.25
);

CREATE TABLE dbo.acct_cash_ledger (
  cash_ledger_id BIGINT IDENTITY(1,1) PRIMARY KEY,
  account_id     BIGINT        NOT NULL,
  currency_code  CHAR(3)       NOT NULL,
  txn_time       DATETIME2(3)  NOT NULL DEFAULT SYSUTCDATETIME(),
  txn_type       NVARCHAR(16)  NOT NULL, -- DEPOSIT/WITHDRAW/FEE/TAX/ADJ
  amount         DECIMAL(18,4) NOT NULL,
  balance_after  DECIMAL(18,4) NOT NULL,
  ref_id         NVARCHAR(64)  NULL
);
CREATE INDEX IX_acct_cash_ledger_acc_time ON dbo.acct_cash_ledger(account_id, txn_time);

CREATE TABLE dbo.acct_fee_schedule (
  fee_sched_id  BIGINT IDENTITY(1,1) PRIMARY KEY,
  account_id    BIGINT       NOT NULL,
  fee_type_id   INT          NOT NULL,
  value         DECIMAL(18,6) NOT NULL,
  unit          NVARCHAR(8)  NOT NULL,  -- PCT/FIXED
  effective_from DATE        NOT NULL,
  effective_to   DATE        NULL
);

CREATE TABLE dbo.acct_risk_limit (
  limit_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
  account_id    BIGINT       NOT NULL,
  kind          NVARCHAR(32) NOT NULL,  -- DAILY_LOSS/NOTIONAL/ORDER_CNT
  threshold     DECIMAL(18,4) NOT NULL,
  window_min    INT           NOT NULL DEFAULT 1440, -- rolling minutes
  active        BIT           NOT NULL DEFAULT 1
);

---------------------------------------------------------------------------------------------
-- 3) Trading Core
---------------------------------------------------------------------------------------------
PRINT 'Creating Trading Core tables...';

CREATE TABLE dbo.ord_order (
  order_id     BIGINT IDENTITY(1,1) PRIMARY KEY,
  account_id   BIGINT        NOT NULL,
  security_id  BIGINT        NOT NULL,
  side         CHAR(1)       NOT NULL,  -- B/S
  order_type   NVARCHAR(16)  NOT NULL,  -- LIMIT/MARKET/STOP
  tif          NVARCHAR(8)   NULL,      -- GTC/IOC/FOK
  qty          DECIMAL(18,4) NOT NULL,
  price        DECIMAL(18,4) NULL,
  status       NVARCHAR(16)  NOT NULL,  -- New/Filled/PartiallyFilled/Cancelled
  source       NVARCHAR(16)  NOT NULL,  -- api/gui/fix
  create_time  DATETIME2(3)  NOT NULL DEFAULT SYSUTCDATETIME(),
  update_time  DATETIME2(3)  NOT NULL DEFAULT SYSUTCDATETIME(),
  parent_order_id BIGINT NULL
);
CREATE INDEX IX_ord_order_acc_time ON dbo.ord_order(account_id, create_time);
CREATE INDEX IX_ord_order_sec_time ON dbo.ord_order(security_id, create_time);

CREATE TABLE dbo.ord_order_event (
  event_id     BIGINT IDENTITY(1,1) PRIMARY KEY,
  order_id     BIGINT        NOT NULL,
  event_time   DATETIME2(3)  NOT NULL DEFAULT SYSUTCDATETIME(),
  event_type   NVARCHAR(16)  NOT NULL,   -- Submit/Ack/Reject/Cancel/Replace
  payload      NVARCHAR(MAX) NULL
);
CREATE INDEX IX_ord_event_order_time ON dbo.ord_order_event(order_id, event_time);

CREATE TABLE dbo.exe_execution (
  execution_id BIGINT IDENTITY(1,1) PRIMARY KEY,
  order_id     BIGINT        NOT NULL,
  exec_time    DATETIME2(3)  NOT NULL,
  exec_qty     DECIMAL(18,4) NOT NULL,
  exec_price   DECIMAL(18,4) NOT NULL,
  venue        NVARCHAR(16)  NULL,
  liquidity    CHAR(1)       NULL, -- M/T
  fee          DECIMAL(18,4) NOT NULL DEFAULT 0,
  tax          DECIMAL(18,4) NOT NULL DEFAULT 0,
  trade_id     NVARCHAR(64)  NULL
);
CREATE INDEX IX_execution_order_time ON dbo.exe_execution(order_id, exec_time);

CREATE TABLE dbo.trd_trade_ledger (
  trade_ledger_id BIGINT IDENTITY(1,1) PRIMARY KEY,
  account_id      BIGINT        NOT NULL,
  security_id     BIGINT        NOT NULL,
  trade_time      DATETIME2(3)  NOT NULL,
  qty             DECIMAL(18,4) NOT NULL,  -- +buy / -sell
  price           DECIMAL(18,4) NOT NULL,
  fee             DECIMAL(18,4) NOT NULL DEFAULT 0,
  tax             DECIMAL(18,4) NOT NULL DEFAULT 0,
  execution_id    BIGINT        NOT NULL
);
CREATE INDEX IX_trade_ledger_acc_time ON dbo.trd_trade_ledger(account_id, trade_time) INCLUDE(security_id, qty, price);

CREATE TABLE dbo.pos_position (
  position_id     BIGINT IDENTITY(1,1) PRIMARY KEY,
  account_id      BIGINT NOT NULL,
  security_id     BIGINT NOT NULL,
  qty             DECIMAL(18,4) NOT NULL,
  avg_price       DECIMAL(18,6) NOT NULL,
  last_update_time DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
  CONSTRAINT UQ_pos_account_security UNIQUE(account_id, security_id)
);

CREATE TABLE dbo.pos_position_lot (
  lot_id          BIGINT IDENTITY(1,1) PRIMARY KEY,
  position_id     BIGINT NOT NULL,
  open_time       DATETIME2(3) NOT NULL,
  open_qty        DECIMAL(18,4) NOT NULL,
  open_price      DECIMAL(18,6) NOT NULL,
  remaining_qty   DECIMAL(18,4) NOT NULL
);

CREATE TABLE dbo.pnl_daily (
  account_id    BIGINT NOT NULL,
  as_of_date    DATE   NOT NULL,
  realized_pnl  DECIMAL(18,4) NOT NULL DEFAULT 0,
  unrealized_pnl DECIMAL(18,4) NOT NULL DEFAULT 0,
  fees          DECIMAL(18,4) NOT NULL DEFAULT 0,
  taxes         DECIMAL(18,4) NOT NULL DEFAULT 0,
  mtm_value     DECIMAL(18,4) NOT NULL DEFAULT 0,
  CONSTRAINT PK_pnl_daily PRIMARY KEY(account_id, as_of_date)
);

CREATE TABLE dbo.mkt_price_intraday (
  security_id   BIGINT NOT NULL,
  ts            DATETIME2(0) NOT NULL,
  last_price    DECIMAL(18,6) NOT NULL,
  bid           DECIMAL(18,6) NULL,
  ask           DECIMAL(18,6) NULL,
  bid_size      INT NULL,
  ask_size      INT NULL,
  volume        BIGINT NULL,
  CONSTRAINT PK_mkt_price_intraday PRIMARY KEY(security_id, ts)
);

CREATE TABLE dbo.mkt_price_eod (
  security_id   BIGINT NOT NULL,
  trade_date    DATE NOT NULL,
  [open]        DECIMAL(18,6) NOT NULL,
  high          DECIMAL(18,6) NOT NULL,
  low           DECIMAL(18,6) NOT NULL,
  [close]       DECIMAL(18,6) NOT NULL,
  adj_close     DECIMAL(18,6) NULL,
  volume        BIGINT NOT NULL,
  CONSTRAINT PK_mkt_price_eod PRIMARY KEY(security_id, trade_date)
);

---------------------------------------------------------------------------------------------
-- 4) Risk & Compliance
---------------------------------------------------------------------------------------------
PRINT 'Creating Risk & Compliance tables...';

CREATE TABLE dbo.risk_exposure_snapshot (
  snapshot_id   BIGINT IDENTITY(1,1) PRIMARY KEY,
  account_id    BIGINT NOT NULL,
  ts            DATETIME2(3) NOT NULL,
  gross         DECIMAL(18,4) NOT NULL,
  net           DECIMAL(18,4) NOT NULL,
  var_1d        DECIMAL(18,4) NOT NULL,
  margin_required DECIMAL(18,4) NOT NULL
);

CREATE TABLE dbo.risk_breach_log (
  breach_id     BIGINT IDENTITY(1,1) PRIMARY KEY,
  account_id    BIGINT NOT NULL,
  ts            DATETIME2(3) NOT NULL,
  limit_id      BIGINT NULL,
  metric        NVARCHAR(32) NOT NULL,
  value         DECIMAL(18,4) NOT NULL,
  threshold     DECIMAL(18,4) NOT NULL
);

CREATE TABLE dbo.cmp_rule (
  rule_id       BIGINT IDENTITY(1,1) PRIMARY KEY,
  name          NVARCHAR(100) NOT NULL,
  rule_expr     NVARCHAR(MAX) NOT NULL, -- JSON/SQL
  severity      NVARCHAR(16)  NOT NULL  -- INFO/WARN/CRIT
);

CREATE TABLE dbo.cmp_alert (
  alert_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
  rule_id       BIGINT NOT NULL,
  account_id    BIGINT NULL,
  order_id      BIGINT NULL,
  ts            DATETIME2(3) NOT NULL,
  status        NVARCHAR(16) NOT NULL,  -- Open/Ack/Closed
  notes         NVARCHAR(400) NULL
);

---------------------------------------------------------------------------------------------
-- 5) Ops & Audit
---------------------------------------------------------------------------------------------
PRINT 'Creating Ops & Audit tables...';

CREATE TABLE dbo.sys_user (
  user_id     BIGINT IDENTITY(1,1) PRIMARY KEY,
  login_id    NVARCHAR(64) NOT NULL UNIQUE,
  role        NVARCHAR(32) NOT NULL,  -- admin/ops/trader
  status      NVARCHAR(16) NOT NULL DEFAULT N'ACTIVE',
  last_login  DATETIME2(3) NULL
);

CREATE TABLE dbo.sys_api_client (
  client_id   BIGINT IDENTITY(1,1) PRIMARY KEY,
  name        NVARCHAR(100) NOT NULL,
  status      NVARCHAR(16) NOT NULL DEFAULT N'ACTIVE',
  rate_limit  INT NOT NULL DEFAULT 1000
);

CREATE TABLE dbo.sys_audit_log
(
    log_id      bigint IDENTITY(1,1) PRIMARY KEY,   -- 로그 고유 ID
    event_type  nvarchar(100)    NOT NULL,          -- 이벤트 종류 (PROC.~, ORDER.NEW 등)
    ref_id      bigint           NULL,              -- 참조 ID (계좌, 주문, 체결 등 관련 키)
    details     nvarchar(max)    NULL,              -- 상세 내용 (파라미터 dump 등)
    created_at  datetime2(3)     NOT NULL DEFAULT SYSUTCDATETIME(), -- 생성 시각
    created_by  nvarchar(100)    NOT NULL           -- 실행자 (user/system/batch 등)
);

-- 조회 성능을 위해 필요한 인덱스 추가
CREATE INDEX IX_sys_audit_log_event_type ON dbo.sys_audit_log(event_type);
CREATE INDEX IX_sys_audit_log_ref_id     ON dbo.sys_audit_log(ref_id);
CREATE INDEX IX_sys_audit_log_created_at ON dbo.sys_audit_log(created_at);

CREATE TABLE dbo.sys_job_run (
  job_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
  job_name    NVARCHAR(100) NOT NULL,
  started_at  DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
  ended_at    DATETIME2(3) NULL,
  status      NVARCHAR(16) NOT NULL,
  metrics_json NVARCHAR(MAX) NULL
);

CREATE TABLE dbo.sys_notification (
  notif_id    BIGINT IDENTITY(1,1) PRIMARY KEY,
  ts          DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
  channel     NVARCHAR(16) NOT NULL, -- email/webhook
  level       NVARCHAR(16) NOT NULL, -- INFO/WARN/ERROR
  message     NVARCHAR(400) NOT NULL,
  meta_json   NVARCHAR(MAX) NULL
);

---------------------------------------------------------------------------------------------
-- 6) Analytics Star Schema
---------------------------------------------------------------------------------------------
PRINT 'Creating Analytics (Star) tables...';

CREATE TABLE dbo.dim_date (
  date_key      INT PRIMARY KEY,  -- YYYYMMDD
  [date]        DATE NOT NULL,
  year          INT NOT NULL,
  quarter       TINYINT NOT NULL,
  month         TINYINT NOT NULL,
  day           TINYINT NOT NULL,
  dow           TINYINT NOT NULL, -- 1=Mon..7=Sun
  is_business_day BIT NOT NULL
);

CREATE TABLE dbo.dim_account (
  account_key   BIGINT IDENTITY(1,1) PRIMARY KEY,
  account_id    BIGINT NOT NULL,
  customer_id   BIGINT NOT NULL,
  base_currency CHAR(3) NOT NULL,
  account_type  NVARCHAR(16) NOT NULL
);

CREATE TABLE dbo.dim_security (
  security_key  BIGINT IDENTITY(1,1) PRIMARY KEY,
  security_id   BIGINT NOT NULL,
  symbol        NVARCHAR(32) NOT NULL,
  exchange_id   INT NOT NULL,
  type_code     NVARCHAR(16) NOT NULL,
  currency_code CHAR(3) NOT NULL
);

CREATE TABLE dbo.dim_exchange (
  exchange_key  INT IDENTITY(1,1) PRIMARY KEY,
  exchange_id   INT NOT NULL,
  code          NVARCHAR(16) NOT NULL,
  name          NVARCHAR(100) NOT NULL,
  tz            NVARCHAR(40) NOT NULL
);

CREATE TABLE dbo.fact_order (
  order_id      BIGINT PRIMARY KEY,
  date_key      INT NOT NULL,
  account_key   BIGINT NOT NULL,
  security_key  BIGINT NOT NULL,
  side          CHAR(1) NOT NULL,
  order_type    NVARCHAR(16) NOT NULL,
  qty           DECIMAL(18,4) NOT NULL,
  price         DECIMAL(18,4) NULL,
  status        NVARCHAR(16) NOT NULL
);

CREATE TABLE dbo.fact_execution (
  execution_id  BIGINT PRIMARY KEY,
  date_key      INT NOT NULL,
  order_id      BIGINT NOT NULL,
  account_key   BIGINT NOT NULL,
  security_key  BIGINT NOT NULL,
  exec_qty      DECIMAL(18,4) NOT NULL,
  exec_price    DECIMAL(18,4) NOT NULL,
  fee           DECIMAL(18,4) NOT NULL,
  tax           DECIMAL(18,4) NOT NULL
);

CREATE TABLE dbo.fact_position_snapshot (
  snapshot_id   BIGINT IDENTITY(1,1) PRIMARY KEY,
  date_key      INT NOT NULL,
  account_key   BIGINT NOT NULL,
  security_key  BIGINT NOT NULL,
  qty           DECIMAL(18,4) NOT NULL,
  avg_price     DECIMAL(18,6) NOT NULL
);

CREATE TABLE dbo.fact_pnl_daily (
  account_key   BIGINT NOT NULL,
  date_key      INT NOT NULL,
  realized_pnl  DECIMAL(18,4) NOT NULL,
  unrealized_pnl DECIMAL(18,4) NOT NULL,
  fees          DECIMAL(18,4) NOT NULL,
  taxes         DECIMAL(18,4) NOT NULL,
  mtm_value     DECIMAL(18,4) NOT NULL,
  CONSTRAINT PK_fact_pnl_daily PRIMARY KEY(account_key, date_key)
);

---------------------------------------------------------------------------------------------
-- Foreign Keys (basic subset to keep script readable; expand as needed)
---------------------------------------------------------------------------------------------
PRINT 'Adding basic foreign keys...';

ALTER TABLE dbo.ref_exchange
  ADD CONSTRAINT FK_ref_exchange_country
  FOREIGN KEY(country_code) REFERENCES dbo.ref_country(country_code);

ALTER TABLE dbo.ref_market_segment
  ADD CONSTRAINT FK_ref_market_segment_exchange
  FOREIGN KEY(exchange_id) REFERENCES dbo.ref_exchange(exchange_id);

ALTER TABLE dbo.ref_holiday
  ADD CONSTRAINT FK_ref_holiday_exchange
  FOREIGN KEY(exchange_id) REFERENCES dbo.ref_exchange(exchange_id);

ALTER TABLE dbo.ref_trading_session
  ADD CONSTRAINT FK_ref_trading_session_exchange
  FOREIGN KEY(exchange_id) REFERENCES dbo.ref_exchange(exchange_id);

ALTER TABLE dbo.ref_security
  ADD CONSTRAINT FK_ref_security_exchange
  FOREIGN KEY(exchange_id) REFERENCES dbo.ref_exchange(exchange_id);

ALTER TABLE dbo.ref_security
  ADD CONSTRAINT FK_ref_security_type
  FOREIGN KEY(type_code) REFERENCES dbo.ref_security_type(type_code);

ALTER TABLE dbo.ref_security
  ADD CONSTRAINT FK_ref_security_currency
  FOREIGN KEY(currency_code) REFERENCES dbo.ref_currency(currency_code);

ALTER TABLE dbo.ref_corporate_action
  ADD CONSTRAINT FK_ref_ca_security
  FOREIGN KEY(security_id) REFERENCES dbo.ref_security(security_id);

ALTER TABLE dbo.cust_customer
  ADD CONSTRAINT FK_cust_customer_country
  FOREIGN KEY(country_code) REFERENCES dbo.ref_country(country_code);

ALTER TABLE dbo.cust_account
  ADD CONSTRAINT FK_cust_account_customer
  FOREIGN KEY(customer_id) REFERENCES dbo.cust_customer(customer_id);

ALTER TABLE dbo.cust_account
  ADD CONSTRAINT FK_cust_account_currency
  FOREIGN KEY(base_currency) REFERENCES dbo.ref_currency(currency_code);

ALTER TABLE dbo.cust_margin_account
  ADD CONSTRAINT FK_margin_account_account
  FOREIGN KEY(account_id) REFERENCES dbo.cust_account(account_id);

ALTER TABLE dbo.acct_cash_ledger
  ADD CONSTRAINT FK_cash_ledger_account
  FOREIGN KEY(account_id) REFERENCES dbo.cust_account(account_id);

ALTER TABLE dbo.acct_cash_ledger
  ADD CONSTRAINT FK_cash_ledger_currency
  FOREIGN KEY(currency_code) REFERENCES dbo.ref_currency(currency_code);

ALTER TABLE dbo.acct_fee_schedule
  ADD CONSTRAINT FK_fee_schedule_account
  FOREIGN KEY(account_id) REFERENCES dbo.cust_account(account_id);

ALTER TABLE dbo.acct_fee_schedule
  ADD CONSTRAINT FK_fee_schedule_fee_type
  FOREIGN KEY(fee_type_id) REFERENCES dbo.ref_fee_type(fee_type_id);

ALTER TABLE dbo.acct_risk_limit
  ADD CONSTRAINT FK_risk_limit_account
  FOREIGN KEY(account_id) REFERENCES dbo.cust_account(account_id);

ALTER TABLE dbo.ord_order
  ADD CONSTRAINT FK_order_account
  FOREIGN KEY(account_id) REFERENCES dbo.cust_account(account_id);

ALTER TABLE dbo.ord_order
  ADD CONSTRAINT FK_order_security
  FOREIGN KEY(security_id) REFERENCES dbo.ref_security(security_id);

ALTER TABLE dbo.ord_order_event
  ADD CONSTRAINT FK_order_event_order
  FOREIGN KEY(order_id) REFERENCES dbo.ord_order(order_id);

ALTER TABLE dbo.exe_execution
  ADD CONSTRAINT FK_execution_order
  FOREIGN KEY(order_id) REFERENCES dbo.ord_order(order_id);

ALTER TABLE dbo.trd_trade_ledger
  ADD CONSTRAINT FK_trade_ledger_execution
  FOREIGN KEY(execution_id) REFERENCES dbo.exe_execution(execution_id);

ALTER TABLE dbo.trd_trade_ledger
  ADD CONSTRAINT FK_trade_ledger_account
  FOREIGN KEY(account_id) REFERENCES dbo.cust_account(account_id);

ALTER TABLE dbo.trd_trade_ledger
  ADD CONSTRAINT FK_trade_ledger_security
  FOREIGN KEY(security_id) REFERENCES dbo.ref_security(security_id);

ALTER TABLE dbo.pos_position
  ADD CONSTRAINT FK_pos_account
  FOREIGN KEY(account_id) REFERENCES dbo.cust_account(account_id);

ALTER TABLE dbo.pos_position
  ADD CONSTRAINT FK_pos_security
  FOREIGN KEY(security_id) REFERENCES dbo.ref_security(security_id);

ALTER TABLE dbo.pos_position_lot
  ADD CONSTRAINT FK_pos_lot_position
  FOREIGN KEY(position_id) REFERENCES dbo.pos_position(position_id);

ALTER TABLE dbo.pnl_daily
  ADD CONSTRAINT FK_pnl_daily_account
  FOREIGN KEY(account_id) REFERENCES dbo.cust_account(account_id);

ALTER TABLE dbo.mkt_price_intraday
  ADD CONSTRAINT FK_price_intraday_security
  FOREIGN KEY(security_id) REFERENCES dbo.ref_security(security_id);

ALTER TABLE dbo.mkt_price_eod
  ADD CONSTRAINT FK_price_eod_security
  FOREIGN KEY(security_id) REFERENCES dbo.ref_security(security_id);

---------------------------------------------------------------------------------------------
-- Seed Sizes
---------------------------------------------------------------------------------------------
DECLARE 
  @CountryCount     INT = 5,
  @CurrencyCount    INT = 5,
  @ExchangeCount    INT = 3,
  @SecurityCount    INT = 3000,   -- increase to create heavy joins
  @CustomerCount    INT = 10000, -- 1만
  @AccountPerCust   INT = 2,
  @OrderCount       INT = 100000000,  -- 1억 heavy OLTP
  @ExecPerOrderMax  INT = 20,      -- partial fills
  @IntradayMinutes  INT = 60,     -- 1 hour for demo
  @IntradaySecCount INT = 3000;    -- number of securities with intraday ticks

PRINT 'Seeding Reference data...';

---------------------------------------------------------------------------------------------
-- Seed Reference: Countries, Currencies
---------------------------------------------------------------------------------------------
INSERT INTO dbo.ref_country(country_code, name)
VALUES ('KR',N'Korea'),('US',N'United States'),('JP',N'Japan'),('GB',N'United Kingdom'),('DE',N'Germany');

INSERT INTO dbo.ref_currency(currency_code, name, minor_unit)
VALUES ('KRW',N'Korean Won',0),('USD',N'US Dollar',2),('JPY',N'Japanese Yen',0),('GBP',N'Pound Sterling',2),('EUR',N'Euro',2);

---------------------------------------------------------------------------------------------
-- Exchanges
---------------------------------------------------------------------------------------------
INSERT INTO dbo.ref_exchange(code,name,tz,country_code)
VALUES (N'KRX',N'Korea Exchange',N'Asia/Seoul','KR'),
       (N'NYSE',N'New York Stock Exchange',N'America/New_York','US'),
       (N'TSE',N'Tokyo Stock Exchange',N'Asia/Tokyo','JP');

INSERT INTO dbo.ref_market_segment(exchange_id,name)
SELECT e.exchange_id, s.name
FROM dbo.ref_exchange e
CROSS APPLY (VALUES (N'Cash'),(N'ETF'),(N'Derivatives')) s(name);

-- Holidays (sample)
INSERT INTO dbo.ref_holiday(exchange_id, holiday_date, description)
SELECT e.exchange_id, DATEADD(DAY, n%10, CAST(GETDATE() AS DATE)), N'Sample Holiday'
FROM dbo.ref_exchange e
JOIN dbo.Numbers n ON n.n <= 3;

-- Trading sessions (REG only demo)
INSERT INTO dbo.ref_trading_session(exchange_id, session_type, start_time, end_time)
SELECT exchange_id, N'REG', '09:00', '15:30' FROM dbo.ref_exchange;

-- Security types
INSERT INTO dbo.ref_security_type(type_code, description)
VALUES (N'Equity',N'Common Stock'),
       (N'ETF',N'Exchange Traded Fund'),
       (N'Bond',N'Corporate/Gov Bond');

-- Fee types
INSERT INTO dbo.ref_fee_type(name, calc_method)
VALUES (N'Commission',N'PCT'),
       (N'Exchange Fee',N'PCT'),
       (N'Platform',N'FIXED');

-- Tax rules
INSERT INTO dbo.ref_tax_rule(country_code, security_type, rate, effective_from, effective_to)
VALUES ('KR',N'Equity',0.001, '2020-01-01', NULL),
       ('US',N'Equity',0.000, '2020-01-01', NULL);

---------------------------------------------------------------------------------------------
-- Securities (bulk)
---------------------------------------------------------------------------------------------
;WITH x AS (
  SELECT TOP (@SecurityCount)
         ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS rn,
         CASE WHEN ABS(CHECKSUM(NEWID()))%3=0 THEN 'Equity'
              WHEN ABS(CHECKSUM(NEWID()))%3=1 THEN 'ETF'
              ELSE 'Bond' END AS type_code,
         (SELECT TOP 1 exchange_id FROM dbo.ref_exchange ORDER BY NEWID()) AS exchange_id,
         (SELECT TOP 1 currency_code FROM dbo.ref_currency ORDER BY NEWID()) AS currency_code
  FROM dbo.Numbers
)
INSERT INTO dbo.ref_security(symbol, isin, exchange_id, type_code, currency_code, lot_size, listed_date, delisted_date)
SELECT CONCAT('SYM', FORMAT(rn,'000000')),
       NULL,
       exchange_id,
       type_code,
       currency_code,
       1,
       DATEADD(DAY, -ABS(CHECKSUM(NEWID()))%1000, CAST(GETDATE() AS DATE)),
       NULL
FROM x;

-- Corporate actions (sample few)
INSERT INTO dbo.ref_corporate_action(security_id, ca_type, ex_date, pay_date, ratio, amount)
SELECT TOP (50) security_id, N'DIV', DATEADD(DAY, 5, CAST(GETDATE() AS DATE)), DATEADD(DAY, 15, CAST(GETDATE() AS DATE)), NULL, 100
FROM dbo.ref_security ORDER BY NEWID();

---------------------------------------------------------------------------------------------
-- Customers & Accounts
---------------------------------------------------------------------------------------------
PRINT 'Seeding Customers & Accounts...';

;WITH c AS (
  SELECT TOP (@CustomerCount)
         ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS rn,
         CASE WHEN ABS(CHECKSUM(NEWID()))%2=0 THEN 'KR' ELSE 'US' END AS country_code
  FROM dbo.Numbers
)
INSERT INTO dbo.cust_customer(name, birth, country_code, kyc_level, risk_profile)
SELECT CONCAT(N'Customer ', rn),
       DATEADD(DAY, - (6000 + rn), CAST(GETDATE() AS DATE)), -- some birth dates
       country_code,
       1 + ABS(CHECKSUM(NEWID()))%3,
       CASE ABS(CHECKSUM(NEWID()))%3 WHEN 0 THEN N'LOW' WHEN 1 THEN N'NORMAL' ELSE N'HIGH' END
FROM c;

-- One account per customer (configurable)
;WITH a AS (
  SELECT customer_id, ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS rn
  FROM dbo.cust_customer
)
INSERT INTO dbo.cust_account(customer_id, base_currency, account_type, opened_at)
SELECT customer_id,
       CASE WHEN ABS(CHECKSUM(NEWID()))%2=0 THEN 'KRW' ELSE 'USD' END,
       CASE WHEN ABS(CHECKSUM(NEWID()))%4=0 THEN N'법인' ELSE N'개인' END,
       DATEADD(DAY, -ABS(CHECKSUM(NEWID()))%365, SYSUTCDATETIME())
FROM a;

-- Some margin accounts
INSERT INTO dbo.cust_margin_account(account_id, credit_limit, maintenance_margin_rate)
SELECT account_id, 10000000 + (ABS(CHECKSUM(NEWID()))%9000000), 0.25
FROM dbo.cust_account
WHERE ABS(CHECKSUM(NEWID()))%5=0;

-- Fee schedules
INSERT INTO dbo.acct_fee_schedule(account_id, fee_type_id, value, unit, effective_from, effective_to)
SELECT account_id, (SELECT TOP 1 fee_type_id FROM dbo.ref_fee_type WHERE calc_method='PCT' ORDER BY fee_type_id),
       0.0005, N'PCT', '2020-01-01', NULL
FROM dbo.cust_account;

-- Risk limits
INSERT INTO dbo.acct_risk_limit(account_id, kind, threshold, window_min, active)
SELECT account_id, N'DAILY_LOSS', 10000000, 1440, 1
FROM dbo.cust_account
WHERE ABS(CHECKSUM(NEWID()))%2=0;

---------------------------------------------------------------------------------------------
-- Seed Cash Ledger small sample (optional)
---------------------------------------------------------------------------------------------
INSERT INTO dbo.acct_cash_ledger(account_id, currency_code, txn_time, txn_type, amount, balance_after, ref_id)
SELECT TOP (1000)
       account_id,
       base_currency,
       DATEADD(MINUTE, -ABS(CHECKSUM(NEWID()))%10000, SYSUTCDATETIME()),
       CASE WHEN ABS(CHECKSUM(NEWID()))%2=0 THEN 'DEPOSIT' ELSE 'FEE' END,
       CAST((ABS(CHECKSUM(NEWID()))%1000000)/10.0 AS DECIMAL(18,4)),
       CAST((ABS(CHECKSUM(NEWID()))%2000000)/10.0 AS DECIMAL(18,4)),
       CONCAT('R', ABS(CHECKSUM(NEWID()))%100000)
FROM dbo.cust_account ORDER BY NEWID();

---------------------------------------------------------------------------------------------
-- Orders
---------------------------------------------------------------------------------------------
PRINT 'Seeding Orders...';

;WITH src AS (
  SELECT TOP (@OrderCount)
         ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS rn,
         (SELECT TOP 1 account_id FROM dbo.cust_account ORDER BY NEWID()) AS account_id,
         (SELECT TOP 1 security_id FROM dbo.ref_security ORDER BY NEWID()) AS security_id
  FROM dbo.Numbers
)
INSERT INTO dbo.ord_order(account_id, security_id, side, order_type, tif, qty, price, status, source, create_time, update_time, parent_order_id)
SELECT account_id,
       security_id,
       CASE WHEN ABS(CHECKSUM(NEWID()))%2=0 THEN 'B' ELSE 'S' END,
       CASE ABS(CHECKSUM(NEWID()))%3 WHEN 0 THEN 'LIMIT' WHEN 1 THEN 'MARKET' ELSE 'STOP' END,
       CASE ABS(CHECKSUM(NEWID()))%3 WHEN 0 THEN 'GTC' WHEN 1 THEN 'IOC' ELSE 'FOK' END,
       CAST(1 + (ABS(CHECKSUM(NEWID()))%1000) AS DECIMAL(18,4)),
       CASE WHEN ABS(CHECKSUM(NEWID()))%2=0 THEN CAST(10 + (ABS(CHECKSUM(NEWID()))%10000)/100.0 AS DECIMAL(18,4)) ELSE NULL END,
       CASE ABS(CHECKSUM(NEWID()))%4 WHEN 0 THEN 'New' WHEN 1 THEN 'PartiallyFilled' WHEN 2 THEN 'Filled' ELSE 'Cancelled' END,
       CASE ABS(CHECKSUM(NEWID()))%3 WHEN 0 THEN 'api' WHEN 1 THEN 'gui' ELSE 'fix' END,
       DATEADD(MINUTE, -ABS(CHECKSUM(NEWID()))%10000, SYSUTCDATETIME()),
       SYSUTCDATETIME(),
       NULL
FROM src;

-- Order events (1~3 per order)
INSERT INTO dbo.ord_order_event(order_id, event_time, event_type, payload)
SELECT o.order_id,
       DATEADD(SECOND, v.step, o.create_time),
       CASE v.step WHEN 0 THEN 'Submit' WHEN 1 THEN 'Ack' ELSE 'Replace' END,
       NULL
FROM dbo.ord_order o
CROSS APPLY (VALUES (0),(1),(2)) v(step)
WHERE ABS(CHECKSUM(o.order_id))%3 >= v.step;

---------------------------------------------------------------------------------------------
-- Executions (0..@ExecPerOrderMax per order)
---------------------------------------------------------------------------------------------
PRINT 'Seeding Executions & Trade Ledger...';

;WITH src AS (
  SELECT order_id,
         ABS(CHECKSUM(order_id))%(@ExecPerOrderMax+1) AS exec_cnt
  FROM dbo.ord_order
)
INSERT INTO dbo.exe_execution(order_id, exec_time, exec_qty, exec_price, venue, liquidity, fee, tax, trade_id)
SELECT o.order_id,
       DATEADD(SECOND, x.k*5, o.create_time),
       CAST((o.qty / NULLIF(NULLIF(exec_cnt,0),0)) AS DECIMAL(18,4)),
       COALESCE(o.price, CAST(10 + (ABS(CHECKSUM(NEWID()))%10000)/100.0 AS DECIMAL(18,4))),
       CASE WHEN ABS(CHECKSUM(NEWID()))%2=0 THEN 'KRX' ELSE 'NYSE' END,
       CASE WHEN ABS(CHECKSUM(NEWID()))%2=0 THEN 'M' ELSE 'T' END,
       0.0005 * COALESCE(o.price,10),
       0.0003 * COALESCE(o.price,10),
       CONCAT('T', o.order_id, '-', x.k)
FROM src s
JOIN dbo.ord_order o ON o.order_id = s.order_id
CROSS APPLY (
  SELECT TOP (CASE WHEN s.exec_cnt=0 THEN 0 ELSE s.exec_cnt END)
         ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS k
  FROM dbo.Numbers
) x;

-- Trade ledger (1 row per execution; +buy / -sell qty)
INSERT INTO dbo.trd_trade_ledger(account_id, security_id, trade_time, qty, price, fee, tax, execution_id)
SELECT o.account_id, o.security_id, e.exec_time,
       CASE WHEN o.side='B' THEN e.exec_qty ELSE -e.exec_qty END,
       e.exec_price, e.fee, e.tax, e.execution_id
FROM dbo.exe_execution e
JOIN dbo.ord_order o ON o.order_id = e.order_id;

---------------------------------------------------------------------------------------------
-- Positions from ledger aggregation (simple snapshot)
---------------------------------------------------------------------------------------------
PRINT 'Building Positions...';

INSERT INTO dbo.pos_position(account_id, security_id, qty, avg_price, last_update_time)
SELECT account_id, security_id,
       SUM(qty) AS qty,
       CASE WHEN SUM(CASE WHEN qty>0 THEN qty*price ELSE 0 END)=0 THEN 0
            ELSE SUM(CASE WHEN qty>0 THEN qty*price ELSE 0 END)/NULLIF(SUM(CASE WHEN qty>0 THEN qty END),0) END AS avg_price,
       MAX(trade_time)
FROM dbo.trd_trade_ledger
GROUP BY account_id, security_id
HAVING SUM(qty) <> 0;

-- Lots (naive: one lot per positive trade)
INSERT INTO dbo.pos_position_lot(position_id, open_time, open_qty, open_price, remaining_qty)
SELECT p.position_id, MIN(t.trade_time),
       ABS(SUM(CASE WHEN t.qty>0 THEN t.qty ELSE 0 END)),
       AVG(CASE WHEN t.qty>0 THEN t.price END),
       ABS(SUM(CASE WHEN t.qty>0 THEN t.qty ELSE 0 END))
FROM dbo.pos_position p
JOIN dbo.trd_trade_ledger t
  ON t.account_id=p.account_id AND t.security_id=p.security_id
GROUP BY p.position_id;

---------------------------------------------------------------------------------------------
-- Intraday & EOD Prices (subset of securities)
---------------------------------------------------------------------------------------------
PRINT 'Seeding Prices...';

DECLARE @BaseDT DATETIME2(0) = DATEADD(HOUR, -@IntradayMinutes/60, SYSUTCDATETIME());
;WITH secs AS (
  SELECT TOP (@IntradaySecCount) security_id
  FROM dbo.ref_security ORDER BY NEWID()
),
mins AS (
  SELECT TOP (@IntradayMinutes)
         ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS k
  FROM dbo.Numbers
)
INSERT INTO dbo.mkt_price_intraday(security_id, ts, last_price, bid, ask, bid_size, ask_size, volume)
SELECT s.security_id,
       DATEADD(MINUTE, m.k, @BaseDT),
       CAST(10 + (ABS(CHECKSUM(NEWID()))%10000)/100.0 AS DECIMAL(18,6)),
       CAST(10 + (ABS(CHECKSUM(NEWID()))%10000)/100.0 AS DECIMAL(18,6)),
       CAST(10 + (ABS(CHECKSUM(NEWID()))%10000)/100.0 AS DECIMAL(18,6)),
       ABS(CHECKSUM(NEWID()))%1000,
       ABS(CHECKSUM(NEWID()))%1000,
       ABS(CHECKSUM(NEWID()))%100000
FROM secs s CROSS JOIN mins m;

-- EOD prices for all securities for yesterday
INSERT INTO dbo.mkt_price_eod(security_id, trade_date, [open], high, low, [close], adj_close, volume)
SELECT security_id, CAST(DATEADD(DAY,-1,GETDATE()) AS DATE),
       10, 12, 9, 11, 11, 100000 + (ABS(CHECKSUM(NEWID()))%100000)
FROM dbo.ref_security;

---------------------------------------------------------------------------------------------
-- PnL daily (simple demo calc: unrealized from last EOD close)
---------------------------------------------------------------------------------------------
PRINT 'Seeding PnL Daily...';

;WITH last_close AS (
  SELECT security_id, [close]
  FROM dbo.mkt_price_eod
  WHERE trade_date = (SELECT MAX(trade_date) FROM dbo.mkt_price_eod)
),
pos AS (
  SELECT account_id, security_id, qty, avg_price FROM dbo.pos_position
)
INSERT INTO dbo.pnl_daily(account_id, as_of_date, realized_pnl, unrealized_pnl, fees, taxes, mtm_value)
SELECT p.account_id, CAST(GETDATE() AS DATE),
       0,
       CAST((l.[close] - p.avg_price) * p.qty AS DECIMAL(18,4)),
       0,0,
       CAST(l.[close] * p.qty AS DECIMAL(18,4))
FROM pos p
JOIN last_close l ON l.security_id = p.security_id;

---------------------------------------------------------------------------------------------
-- Risk/Compliance seed
---------------------------------------------------------------------------------------------
PRINT 'Seeding Risk/Compliance...';

INSERT INTO dbo.risk_exposure_snapshot(account_id, ts, gross, net, var_1d, margin_required)
SELECT TOP (500)
       account_id,
       DATEADD(MINUTE, -ABS(CHECKSUM(NEWID()))%10000, SYSUTCDATETIME()),
       CAST(ABS(CHECKSUM(NEWID()))%1000000 AS DECIMAL(18,4)),
       CAST((ABS(CHECKSUM(NEWID()))%200000 - 100000) AS DECIMAL(18,4)),
       CAST(ABS(CHECKSUM(NEWID()))%50000 AS DECIMAL(18,4)),
       CAST(ABS(CHECKSUM(NEWID()))%30000 AS DECIMAL(18,4))
FROM dbo.cust_account ORDER BY NEWID();

INSERT INTO dbo.cmp_rule(name, rule_expr, severity)
VALUES (N'LargeNotional', N'notional > 1e9', N'WARN'),
       (N'OrderBurst',    N'orders_per_min > 500', N'CRIT');

INSERT INTO dbo.cmp_alert(rule_id, account_id, order_id, ts, status, notes)
SELECT TOP (300)
       (SELECT TOP 1 rule_id FROM dbo.cmp_rule ORDER BY NEWID()),
       (SELECT TOP 1 account_id FROM dbo.cust_account ORDER BY NEWID()),
       (SELECT TOP 1 order_id FROM dbo.ord_order ORDER BY NEWID()),
       DATEADD(MINUTE, -ABS(CHECKSUM(NEWID()))%10000, SYSUTCDATETIME()),
       CASE WHEN ABS(CHECKSUM(NEWID()))%2=0 THEN N'Open' ELSE N'Ack' END,
       N'Auto-generated alert'
FROM dbo.Numbers;

INSERT INTO dbo.risk_breach_log(account_id, ts, limit_id, metric, value, threshold)
SELECT TOP (200)
       account_id,
       DATEADD(MINUTE, -ABS(CHECKSUM(NEWID()))%10000, SYSUTCDATETIME()),
       NULL,
       N'DAILY_LOSS',
       CAST((ABS(CHECKSUM(NEWID()))%200000 - 100000) AS DECIMAL(18,4)),
       100000.00
FROM dbo.cust_account ORDER BY NEWID();

---------------------------------------------------------------------------------------------
-- Ops/Audit seed
---------------------------------------------------------------------------------------------
PRINT 'Seeding Ops/Audit...';

INSERT INTO dbo.sys_user(login_id, role, status, last_login)
VALUES (N'admin',N'admin',N'ACTIVE',SYSUTCDATETIME()),
       (N'ops01',N'ops',N'ACTIVE',NULL),
       (N'trader01',N'trader',N'ACTIVE',NULL);

INSERT INTO dbo.sys_api_client(name, status, rate_limit)
VALUES (N'AB-UI',N'ACTIVE',1000),
       (N'AB-Batch',N'ACTIVE',2000);

INSERT INTO dbo.sys_audit_log(actor, action, target_table, target_pk, before_json, after_json, ip)
SELECT TOP (1000)
       CASE WHEN ABS(CHECKSUM(NEWID()))%2=0 THEN N'user:admin' ELSE N'client:AB-UI' END,
       CASE ABS(CHECKSUM(NEWID()))%4 WHEN 0 THEN N'INSERT' WHEN 1 THEN N'UPDATE' WHEN 2 THEN N'DELETE' ELSE N'UPSERT' END,
       N'ord_order',
       CAST(ABS(CHECKSUM(NEWID()))%@OrderCount AS NVARCHAR(128)),
       NULL,NULL,
       N'127.0.0.1'
FROM dbo.Numbers;

INSERT INTO dbo.sys_job_run(job_name, started_at, ended_at, status, metrics_json)
VALUES (N'ETL-EOD', DATEADD(HOUR,-1,SYSUTCDATETIME()), SYSUTCDATETIME(), N'SUCCESS', N'{"rows":12345}'),
       (N'Risk-Calc', DATEADD(HOUR,-2,SYSUTCDATETIME()), DATEADD(HOUR,-1,SYSUTCDATETIME()), N'FAIL', N'{"error":"timeout"}');

INSERT INTO dbo.sys_notification(channel, level, message, meta_json)
VALUES (N'email',N'INFO',N'Job completed',N'{}'),
       (N'webhook',N'ERROR',N'Risk calc failed',N'{}');

---------------------------------------------------------------------------------------------
-- Analytics: Populate Dimensions
---------------------------------------------------------------------------------------------
PRINT 'Populating Dimensions...';

-- dim_date: last 365 days
INSERT INTO dbo.dim_date(date_key, [date], year, quarter, month, day, dow, is_business_day)
SELECT CONVERT(INT, FORMAT(d,'yyyyMMdd')), d,
       DATEPART(YEAR,d),
       DATEPART(QUARTER,d),
       DATEPART(MONTH,d),
       DATEPART(DAY,d),
       (DATEPART(WEEKDAY,d)+5)%7+1,  -- 1=Mon .. 7=Sun
       CASE WHEN DATENAME(WEEKDAY,d) IN ('Saturday','Sunday') THEN 0 ELSE 1 END
FROM (
  SELECT DATEADD(DAY, -n, CAST(GETDATE() AS DATE)) AS d
  FROM dbo.Numbers WHERE n<=365
) x;

INSERT INTO dbo.dim_account(account_id, customer_id, base_currency, account_type)
SELECT account_id, customer_id, base_currency, account_type
FROM dbo.cust_account;

INSERT INTO dbo.dim_security(security_id, symbol, exchange_id, type_code, currency_code)
SELECT security_id, symbol, exchange_id, type_code, currency_code
FROM dbo.ref_security;

INSERT INTO dbo.dim_exchange(exchange_id, code, name, tz)
SELECT exchange_id, code, name, tz
FROM dbo.ref_exchange;

---------------------------------------------------------------------------------------------
-- Analytics: Populate Facts (thin copy)
---------------------------------------------------------------------------------------------
PRINT 'Populating Facts...';

-- fact_order
INSERT INTO dbo.fact_order(order_id, date_key, account_key, security_key, side, order_type, qty, price, status)
SELECT o.order_id,
       CONVERT(INT, FORMAT(CAST(o.create_time AS DATE),'yyyyMMdd')),
       da.account_key, ds.security_key,
       o.side, o.order_type, o.qty, o.price, o.status
FROM dbo.ord_order o
JOIN dbo.dim_account da ON da.account_id = o.account_id
JOIN dbo.dim_security ds ON ds.security_id = o.security_id;

-- fact_execution
INSERT INTO dbo.fact_execution(execution_id, date_key, order_id, account_key, security_key, exec_qty, exec_price, fee, tax)
SELECT e.execution_id,
       CONVERT(INT, FORMAT(CAST(e.exec_time AS DATE),'yyyyMMdd')),
       e.order_id, da.account_key, ds.security_key,
       e.exec_qty, e.exec_price, e.fee, e.tax
FROM dbo.exe_execution e
JOIN dbo.ord_order o ON o.order_id=e.order_id
JOIN dbo.dim_account da ON da.account_id=o.account_id
JOIN dbo.dim_security ds ON ds.security_id=o.security_id;

-- fact_position_snapshot (today snapshot)
INSERT INTO dbo.fact_position_snapshot(date_key, account_key, security_key, qty, avg_price)
SELECT CONVERT(INT, FORMAT(CAST(GETDATE() AS DATE),'yyyyMMdd')),
       da.account_key, ds.security_key, p.qty, p.avg_price
FROM dbo.pos_position p
JOIN dbo.dim_account da ON da.account_id=p.account_id
JOIN dbo.dim_security ds ON ds.security_id=p.security_id;

-- fact_pnl_daily
INSERT INTO dbo.fact_pnl_daily(account_key, date_key, realized_pnl, unrealized_pnl, fees, taxes, mtm_value)
SELECT da.account_key,
       CONVERT(INT, FORMAT(p.as_of_date,'yyyyMMdd')),
       p.realized_pnl, p.unrealized_pnl, p.fees, p.taxes, p.mtm_value
FROM dbo.pnl_daily p
JOIN dbo.dim_account da ON da.account_id=p.account_id;

PRINT 'Done.';
