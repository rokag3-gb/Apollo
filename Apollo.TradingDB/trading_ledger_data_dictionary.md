# Trading Ledger 데이터 사전 (Markdown)

- 생성일: 2025-08-22 03:14:34

- 범위: 1) 기준/레퍼런스 ~ 6) 분석 스타 스키마(총 44개 테이블)

## 테이블 요약

| 테이블 | 의미 |
|---|---|
| `ref_country` | 국가 코드/이름 기준 정보. |
| `ref_currency` | 통화 코드, 소수점 자릿수(동전 단위) 기준 정보. |
| `ref_exchange` | 거래소(코드/명칭/시간대/국가) 기준 정보. |
| `ref_market_segment` | 거래소 내 시장 구분(현물/ETF/파생 등). |
| `ref_holiday` | 거래소 휴장일 달력. |
| `ref_trading_session` | 거래소의 거래 세션(정규/연장) 시간대. |
| `ref_security_type` | 증권 유형(Equity/ETF/Bond 등) 정의. |
| `ref_security` | 종목 마스터(티커, 유형, 상장일, 통화 등). |
| `ref_fee_type` | 수수료 유형과 계산 방식. |
| `ref_tax_rule` | 국가·상품유형별 세율 규칙. |
| `ref_corporate_action` | 배당/분할 등 기업행위 정보. |
| `cust_customer` | 고객 마스터(KYC/리스크 프로필 포함). |
| `cust_account` | 거래 계좌(기준통화/개인·법인/개설일 등). |
| `cust_margin_account` | 신용/마진 계좌 한도/유지증거금. |
| `acct_cash_ledger` | 현금원장(입출금/수수료/세금/정정 내역). |
| `acct_fee_schedule` | 계좌별 수수료 약정(율/정액, 적용기간). |
| `acct_risk_limit` | 계좌 리스크 한도(일손실/체결가치/오더수 등). |
| `ord_order` | 주문 원장(사이드/유형/TIF/수량/가격/상태 등). |
| `ord_order_event` | 주문 라이프사이클 이벤트(제출/승인/정정/취소). |
| `exe_execution` | 체결(부분 체결 포함) 상세. |
| `trd_trade_ledger` | 거래 원장(체결을 계정/종목 관점으로 기록). |
| `pos_position` | 실시간 포지션 스냅샷(수량/평균단가). |
| `pos_position_lot` | LOT 단위 포지션(선입선출 등 추적에 사용). |
| `pnl_daily` | 계정 일자별 실현/미실현 손익, 수수료/세금/MTM. |
| `mkt_price_intraday` | 분 단위 등 장중 시세 스냅샷(호가/체결가). |
| `mkt_price_eod` | 종가 기준 일별 시세(EOD). |
| `risk_exposure_snapshot` | 리스크 노출 스냅샷(총/순/VAR/증거금). |
| `risk_breach_log` | 한도 위반 로그(지표/값/임계치). |
| `cmp_rule` | 컴플라이언스 룰 정의(JSON/SQL 표현식). |
| `cmp_alert` | 컴플라이언스 경보(룰/계정/주문/상태). |
| `sys_user` | 내부 사용자 계정(역할/상태/로그인). |
| `sys_api_client` | API 클라이언트(상태/레이트리밋). |
| `sys_audit_log` | 감사 로그(행위자/행위/대상/전후 이미지). |
| `sys_job_run` | 배치/잡 실행 이력(시작/종료/상태/메트릭). |
| `sys_notification` | 시스템 알림(채널/레벨/메시지/메타). |
| `dim_date` | 분석용 날짜 차원(YYYYMMDD/분기/영업일 등). |
| `dim_account` | 분석용 계좌 차원(계좌/고객/통화/유형). |
| `dim_security` | 분석용 종목 차원(거래소/유형/통화). |
| `dim_exchange` | 분석용 거래소 차원. |
| `fact_order` | 주문 팩트(날짜/계좌/종목/수량/가격/상태). |
| `fact_execution` | 체결 팩트(날짜/계좌/종목/수량/가격/수수료/세금). |
| `fact_position_snapshot` | 포지션 스냅샷 팩트(날짜/계좌/종목/수량/평단). |
| `fact_pnl_daily` | 일별 PnL 팩트(실현/미실현/수수료/세금/MTM). |
| `Numbers` | 설명 필요 |

## `ref_country` — 국가 코드/이름 기준 정보.

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `country_code` | CHAR(2) | NO | YES |  | 분류/코드 값 |
| `name` | NVARCHAR(100) | NO | NO |  | 설명/상태/메타 정보 |

## `ref_currency` — 통화 코드, 소수점 자릿수(동전 단위) 기준 정보.

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `currency_code` | CHAR(3) | NO | YES |  | 분류/코드 값 |
| `minor_unit` | TINYINT | NO | NO | 2 | 규정/제한/설정 값 |
| `name` | NVARCHAR(50) | NO | NO |  | 설명/상태/메타 정보 |

## `ref_exchange` — 거래소(코드/명칭/시간대/국가) 기준 정보.

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `exchange_id` | INT IDENTITY | YES | YES |  | EXCHANGE 식별자(FK 가능) |
| `code` | NVARCHAR(16) | NO | NO |  | 설명/상태/메타 정보 |
| `country_code` | CHAR(2) | NO | NO |  | 분류/코드 값 |
| `name` | NVARCHAR(100) | NO | NO |  | 설명/상태/메타 정보 |
| `tz` | NVARCHAR(40) | NO | NO |  | 분류/코드 값 |

## `ref_market_segment` — 거래소 내 시장 구분(현물/ETF/파생 등).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `segment_id` | INT IDENTITY | YES | YES |  | SEGMENT 식별자(FK 가능) |
| `exchange_id` | INT | NO | NO |  | EXCHANGE 식별자(FK 가능) |
| `name` | NVARCHAR(100) | NO | NO |  | 설명/상태/메타 정보 |

## `ref_holiday` — 거래소 휴장일 달력.

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `exchange_id` | INT | NO | YES |  | EXCHANGE 식별자(FK 가능) |
| `holiday_date` | DATE | NO | YES |  | 일자 |
| `description` | NVARCHAR(200) | YES | NO |  | 설명/상태/메타 정보 |

## `ref_trading_session` — 거래소의 거래 세션(정규/연장) 시간대.

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `session_id` | INT IDENTITY | YES | YES |  | SESSION 식별자(FK 가능) |
| `end_time` | TIME(0) | NO | NO |  | 타임스탬프 |
| `exchange_id` | INT | NO | NO |  | EXCHANGE 식별자(FK 가능) |
| `session_type` | NVARCHAR(16) | NO | NO |  | 분류/코드 값 |
| `start_time` | TIME(0) | NO | NO |  | 타임스탬프 |

## `ref_security_type` — 증권 유형(Equity/ETF/Bond 등) 정의.

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `type_code` | NVARCHAR(16) | NO | YES |  | 분류/코드 값 |
| `description` | NVARCHAR(100) | YES | NO |  | 설명/상태/메타 정보 |

## `ref_security` — 종목 마스터(티커, 유형, 상장일, 통화 등).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `security_id` | BIGINT IDENTITY | YES | YES |  | SECURITY 식별자(FK 가능) |
| `currency_code` | CHAR(3) | NO | NO |  | 분류/코드 값 |
| `delisted_date` | DATE | YES | NO |  | 일자 |
| `exchange_id` | INT | NO | NO |  | EXCHANGE 식별자(FK 가능) |
| `isin` | NVARCHAR(12) | YES | NO |  | 종목 식별자/코드 |
| `listed_date` | DATE | NO | NO |  | 일자 |
| `lot_size` | INT | NO | NO | 1 | 규정/제한/설정 값 |
| `symbol` | NVARCHAR(32) | NO | NO |  | 종목 식별자/코드 |
| `type_code` | NVARCHAR(16) | NO | NO |  | 분류/코드 값 |

## `ref_fee_type` — 수수료 유형과 계산 방식.

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `fee_type_id` | INT IDENTITY | YES | YES |  | FEE TYPE 식별자(FK 가능) |
| `calc_method` | NVARCHAR(20) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `name` | NVARCHAR(100) | NO | NO |  | 설명/상태/메타 정보 |

## `ref_tax_rule` — 국가·상품유형별 세율 규칙.

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `tax_rule_id` | INT IDENTITY | YES | YES |  | TAX RULE 식별자(FK 가능) |
| `country_code` | CHAR(2) | NO | NO |  | 분류/코드 값 |
| `effective_from` | DATE | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `effective_to` | DATE | YES | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `rate` | DECIMAL(9,6) | NO | NO |  | 규정/제한/설정 값 |
| `security_type` | NVARCHAR(16) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |

## `ref_corporate_action` — 배당/분할 등 기업행위 정보.

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `ca_id` | BIGINT IDENTITY | YES | YES |  | CA 식별자(FK 가능) |
| `amount` | DECIMAL(18,8) | YES | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `ca_type` | NVARCHAR(20) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `ex_date` | DATE | NO | NO |  | 일자 |
| `pay_date` | DATE | YES | NO |  | 일자 |
| `ratio` | DECIMAL(18,8) | YES | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `security_id` | BIGINT | NO | NO |  | SECURITY 식별자(FK 가능) |

## `cust_customer` — 고객 마스터(KYC/리스크 프로필 포함).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `customer_id` | BIGINT IDENTITY | YES | YES |  | CUSTOMER 식별자(FK 가능) |
| `birth` | DATE | YES | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `country_code` | CHAR(2) | NO | NO |  | 분류/코드 값 |
| `kyc_level` | TINYINT | NO | NO | 1 | 규정/제한/설정 값 |
| `name` | NVARCHAR(100) | NO | NO |  | 설명/상태/메타 정보 |
| `risk_profile` | NVARCHAR(16) | NO | NO | N'NORMAL' | 규정/제한/설정 값 |

## `cust_account` — 거래 계좌(기준통화/개인·법인/개설일 등).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `account_id` | BIGINT IDENTITY | YES | YES |  | ACCOUNT 식별자(FK 가능) |
| `account_type` | NVARCHAR(16) | NO | NO |  | 분류/코드 값 |
| `base_currency` | CHAR(3) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `closed_at` | DATETIME2(3) | YES | NO |  | 타임스탬프 |
| `customer_id` | BIGINT | NO | NO |  | CUSTOMER 식별자(FK 가능) |
| `opened_at` | DATETIME2(3) | NO | NO | SYSUTCDATETIME() | 타임스탬프 |

## `cust_margin_account` — 신용/마진 계좌 한도/유지증거금.

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `margin_account_id` | BIGINT IDENTITY | YES | YES |  | MARGIN ACCOUNT 식별자(FK 가능) |
| `account_id` | BIGINT | NO | NO |  | ACCOUNT 식별자(FK 가능) |
| `credit_limit` | DECIMAL(18,2) | NO | NO | 0 | 규정/제한/설정 값 |
| `maintenance_margin_rate` | DECIMAL(9,6) | NO | NO | 0.25 | 리스크/한도 관련 값 |

## `acct_cash_ledger` — 현금원장(입출금/수수료/세금/정정 내역).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `cash_ledger_id` | BIGINT IDENTITY | YES | YES |  | CASH LEDGER 식별자(FK 가능) |
| `account_id` | BIGINT | NO | NO |  | ACCOUNT 식별자(FK 가능) |
| `amount` | DECIMAL(18,4) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `balance_after` | DECIMAL(18,4) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `currency_code` | CHAR(3) | NO | NO |  | 분류/코드 값 |
| `ref_id` | NVARCHAR(64) | YES | NO |  | REF 식별자(FK 가능) |
| `txn_time` | DATETIME2(3) | NO | NO | SYSUTCDATETIME() | 타임스탬프 |
| `txn_type` | NVARCHAR(16) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |

## `acct_fee_schedule` — 계좌별 수수료 약정(율/정액, 적용기간).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `fee_sched_id` | BIGINT IDENTITY | YES | YES |  | FEE SCHED 식별자(FK 가능) |
| `account_id` | BIGINT | NO | NO |  | ACCOUNT 식별자(FK 가능) |
| `effective_from` | DATE | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `effective_to` | DATE | YES | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `fee_type_id` | INT | NO | NO |  | FEE TYPE 식별자(FK 가능) |
| `unit` | NVARCHAR(8) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `value` | DECIMAL(18,6) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |

## `acct_risk_limit` — 계좌 리스크 한도(일손실/체결가치/오더수 등).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `limit_id` | BIGINT IDENTITY | YES | YES |  | LIMIT 식별자(FK 가능) |
| `account_id` | BIGINT | NO | NO |  | ACCOUNT 식별자(FK 가능) |
| `active` | BIT | NO | NO | 1 | 컬럼 의미(도메인에 맞게 사용) |
| `kind` | NVARCHAR(32) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `threshold` | DECIMAL(18,4) | NO | NO |  | 리스크/한도 관련 값 |
| `window_min` | INT | NO | NO | 1440 | 규정/제한/설정 값 |

## `ord_order` — 주문 원장(사이드/유형/TIF/수량/가격/상태 등).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `order_id` | BIGINT IDENTITY | YES | YES |  | ORDER 식별자(FK 가능) |
| `account_id` | BIGINT | NO | NO |  | ACCOUNT 식별자(FK 가능) |
| `create_time` | DATETIME2(3) | NO | NO | SYSUTCDATETIME() | 타임스탬프 |
| `order_type` | NVARCHAR(16) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `parent_order_id` | BIGINT | YES | NO |  | PARENT ORDER 식별자(FK 가능) |
| `price` | DECIMAL(18,4) | YES | NO |  | 가격 |
| `qty` | DECIMAL(18,4) | NO | NO |  | 수량 |
| `security_id` | BIGINT | NO | NO |  | SECURITY 식별자(FK 가능) |
| `side` | CHAR(1) | NO | NO |  | 매수/매도 구분(B/S) |
| `source` | NVARCHAR(16) | NO | NO |  | 설명/상태/메타 정보 |
| `status` | NVARCHAR(16) | NO | NO |  | 설명/상태/메타 정보 |
| `tif` | NVARCHAR(8) | YES | NO |  | 설명/상태/메타 정보 |
| `update_time` | DATETIME2(3) | NO | NO | SYSUTCDATETIME() | 일자 |

## `ord_order_event` — 주문 라이프사이클 이벤트(제출/승인/정정/취소).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `event_id` | BIGINT IDENTITY | YES | YES |  | EVENT 식별자(FK 가능) |
| `event_time` | DATETIME2(3) | NO | NO | SYSUTCDATETIME() | 타임스탬프 |
| `event_type` | NVARCHAR(16) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `order_id` | BIGINT | NO | NO |  | ORDER 식별자(FK 가능) |
| `payload` | NVARCHAR | YES | NO |  | 설명/상태/메타 정보 |

## `exe_execution` — 체결(부분 체결 포함) 상세.

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `execution_id` | BIGINT IDENTITY | YES | YES |  | EXECUTION 식별자(FK 가능) |
| `exec_price` | DECIMAL(18,4) | NO | NO |  | 가격 |
| `exec_qty` | DECIMAL(18,4) | NO | NO |  | 수량 |
| `exec_time` | DATETIME2(3) | NO | NO |  | 타임스탬프 |
| `fee` | DECIMAL(18,4) | NO | NO | 0 | 수수료 |
| `liquidity` | CHAR(1) | YES | NO |  | 설명/상태/메타 정보 |
| `order_id` | BIGINT | NO | NO |  | ORDER 식별자(FK 가능) |
| `tax` | DECIMAL(18,4) | NO | NO | 0 | 세금 |
| `trade_id` | NVARCHAR(64) | YES | NO |  | TRADE 식별자(FK 가능) |
| `venue` | NVARCHAR(16) | YES | NO |  | 설명/상태/메타 정보 |

## `trd_trade_ledger` — 거래 원장(체결을 계정/종목 관점으로 기록).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `trade_ledger_id` | BIGINT IDENTITY | YES | YES |  | TRADE LEDGER 식별자(FK 가능) |
| `account_id` | BIGINT | NO | NO |  | ACCOUNT 식별자(FK 가능) |
| `execution_id` | BIGINT | NO | NO |  | EXECUTION 식별자(FK 가능) |
| `fee` | DECIMAL(18,4) | NO | NO | 0 | 수수료 |
| `price` | DECIMAL(18,4) | NO | NO |  | 가격 |
| `qty` | DECIMAL(18,4) | NO | NO |  | 수량 |
| `security_id` | BIGINT | NO | NO |  | SECURITY 식별자(FK 가능) |
| `tax` | DECIMAL(18,4) | NO | NO | 0 | 세금 |
| `trade_time` | DATETIME2(3) | NO | NO |  | 타임스탬프 |

## `pos_position` — 실시간 포지션 스냅샷(수량/평균단가).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `position_id` | BIGINT IDENTITY | YES | YES |  | POSITION 식별자(FK 가능) |
| `account_id` | BIGINT | NO | NO |  | ACCOUNT 식별자(FK 가능) |
| `avg_price` | DECIMAL(18,6) | NO | NO |  | 가격 |
| `last_update_time` | DATETIME2(3) | NO | NO | SYSUTCDATETIME() | 일자 |
| `qty` | DECIMAL(18,4) | NO | NO |  | 수량 |
| `security_id` | BIGINT | NO | NO |  | SECURITY 식별자(FK 가능) |

## `pos_position_lot` — LOT 단위 포지션(선입선출 등 추적에 사용).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `lot_id` | BIGINT IDENTITY | YES | YES |  | LOT 식별자(FK 가능) |
| `open_price` | DECIMAL(18,6) | NO | NO |  | 가격 |
| `open_qty` | DECIMAL(18,4) | NO | NO |  | 수량 |
| `open_time` | DATETIME2(3) | NO | NO |  | 타임스탬프 |
| `position_id` | BIGINT | NO | NO |  | POSITION 식별자(FK 가능) |
| `remaining_qty` | DECIMAL(18,4) | NO | NO |  | 수량 |

## `pnl_daily` — 계정 일자별 실현/미실현 손익, 수수료/세금/MTM.

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `account_id` | BIGINT | NO | YES |  | ACCOUNT 식별자(FK 가능) |
| `as_of_date` | DATE | NO | YES |  | 일자 |
| `fees` | DECIMAL(18,4) | NO | NO | 0 | 수수료 |
| `mtm_value` | DECIMAL(18,4) | NO | NO | 0 | 시가평가 금액(MTM) |
| `realized_pnl` | DECIMAL(18,4) | NO | NO | 0 | 손익/평단/수량 |
| `taxes` | DECIMAL(18,4) | NO | NO | 0 | 세금 |
| `unrealized_pnl` | DECIMAL(18,4) | NO | NO | 0 | 손익/평단/수량 |

## `mkt_price_intraday` — 분 단위 등 장중 시세 스냅샷(호가/체결가).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `security_id` | BIGINT | NO | YES |  | SECURITY 식별자(FK 가능) |
| `ts` | DATETIME2(0) | NO | YES |  | 타임스탬프 |
| `ask` | DECIMAL(18,6) | YES | NO |  | 시세/호가/체결 관련 값 |
| `ask_size` | INT | YES | NO |  | 시세/호가/체결 관련 값 |
| `bid` | DECIMAL(18,6) | YES | NO |  | 시세/호가/체결 관련 값 |
| `bid_size` | INT | YES | NO |  | 시세/호가/체결 관련 값 |
| `last_price` | DECIMAL(18,6) | NO | NO |  | 가격 |
| `volume` | BIGINT | YES | NO |  | 시세/호가/체결 관련 값 |

## `mkt_price_eod` — 종가 기준 일별 시세(EOD).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `security_id` | BIGINT | NO | YES |  | SECURITY 식별자(FK 가능) |
| `trade_date` | DATE | NO | YES |  | 일자 |
| `adj_close` | DECIMAL(18,6) | YES | NO |  | 시세/호가/체결 관련 값 |
| `close` | DECIMAL(18,6) | NO | NO |  | 시세/호가/체결 관련 값 |
| `high` | DECIMAL(18,6) | NO | NO |  | 시세/호가/체결 관련 값 |
| `low` | DECIMAL(18,6) | NO | NO |  | 시세/호가/체결 관련 값 |
| `open` | DECIMAL(18,6) | NO | NO |  | 시세/호가/체결 관련 값 |
| `volume` | BIGINT | NO | NO |  | 시세/호가/체결 관련 값 |

## `risk_exposure_snapshot` — 리스크 노출 스냅샷(총/순/VAR/증거금).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `snapshot_id` | BIGINT IDENTITY | YES | YES |  | SNAPSHOT 식별자(FK 가능) |
| `account_id` | BIGINT | NO | NO |  | ACCOUNT 식별자(FK 가능) |
| `gross` | DECIMAL(18,4) | NO | NO |  | 리스크/한도 관련 값 |
| `margin_required` | DECIMAL(18,4) | NO | NO |  | 리스크/한도 관련 값 |
| `net` | DECIMAL(18,4) | NO | NO |  | 리스크/한도 관련 값 |
| `ts` | DATETIME2(3) | NO | NO |  | 타임스탬프 |
| `var_1d` | DECIMAL(18,4) | NO | NO |  | 변동성/리스크 지표 |

## `risk_breach_log` — 한도 위반 로그(지표/값/임계치).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `breach_id` | BIGINT IDENTITY | YES | YES |  | BREACH 식별자(FK 가능) |
| `account_id` | BIGINT | NO | NO |  | ACCOUNT 식별자(FK 가능) |
| `limit_id` | BIGINT | YES | NO |  | LIMIT 식별자(FK 가능) |
| `metric` | NVARCHAR(32) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `threshold` | DECIMAL(18,4) | NO | NO |  | 리스크/한도 관련 값 |
| `ts` | DATETIME2(3) | NO | NO |  | 타임스탬프 |
| `value` | DECIMAL(18,4) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |

## `cmp_rule` — 컴플라이언스 룰 정의(JSON/SQL 표현식).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `rule_id` | BIGINT IDENTITY | YES | YES |  | RULE 식별자(FK 가능) |
| `name` | NVARCHAR(100) | NO | NO |  | 설명/상태/메타 정보 |
| `rule_expr` | NVARCHAR | NO | NO |  | 설명/상태/메타 정보 |
| `severity` | NVARCHAR(16) | NO | NO |  | 설명/상태/메타 정보 |

## `cmp_alert` — 컴플라이언스 경보(룰/계정/주문/상태).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `alert_id` | BIGINT IDENTITY | YES | YES |  | ALERT 식별자(FK 가능) |
| `account_id` | BIGINT | YES | NO |  | ACCOUNT 식별자(FK 가능) |
| `notes` | NVARCHAR(400) | YES | NO |  | 설명/상태/메타 정보 |
| `order_id` | BIGINT | YES | NO |  | ORDER 식별자(FK 가능) |
| `rule_id` | BIGINT | NO | NO |  | RULE 식별자(FK 가능) |
| `status` | NVARCHAR(16) | NO | NO |  | 설명/상태/메타 정보 |
| `ts` | DATETIME2(3) | NO | NO |  | 타임스탬프 |

## `sys_user` — 내부 사용자 계정(역할/상태/로그인).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `user_id` | BIGINT IDENTITY | YES | YES |  | USER 식별자(FK 가능) |
| `last_login` | DATETIME2(3) | YES | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `login_id` | NVARCHAR(64) | NO | NO |  | LOGIN 식별자(FK 가능) |
| `role` | NVARCHAR(32) | NO | NO |  | 설명/상태/메타 정보 |
| `status` | NVARCHAR(16) | NO | NO | N'ACTIVE' | 설명/상태/메타 정보 |

## `sys_api_client` — API 클라이언트(상태/레이트리밋).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `client_id` | BIGINT IDENTITY | YES | YES |  | CLIENT 식별자(FK 가능) |
| `name` | NVARCHAR(100) | NO | NO |  | 설명/상태/메타 정보 |
| `rate_limit` | INT | NO | NO | 1000 | 규정/제한/설정 값 |
| `status` | NVARCHAR(16) | NO | NO | N'ACTIVE' | 설명/상태/메타 정보 |

## `sys_audit_log` — 감사 로그(행위자/행위/대상/전후 이미지).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `audit_id` | BIGINT IDENTITY | YES | YES |  | AUDIT 식별자(FK 가능) |
| `action` | NVARCHAR(64) | NO | NO |  | 설명/상태/메타 정보 |
| `actor` | NVARCHAR(64) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `after_json` | NVARCHAR | YES | NO |  | 설명/상태/메타 정보 |
| `before_json` | NVARCHAR | YES | NO |  | 설명/상태/메타 정보 |
| `ip` | NVARCHAR(64) | YES | NO |  | 설명/상태/메타 정보 |
| `target_pk` | NVARCHAR(128) | YES | NO |  | 설명/상태/메타 정보 |
| `target_table` | NVARCHAR(64) | NO | NO |  | 설명/상태/메타 정보 |
| `ts` | DATETIME2(3) | NO | NO | SYSUTCDATETIME() | 타임스탬프 |

## `sys_job_run` — 배치/잡 실행 이력(시작/종료/상태/메트릭).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `job_id` | BIGINT IDENTITY | YES | YES |  | JOB 식별자(FK 가능) |
| `ended_at` | DATETIME2(3) | YES | NO |  | 타임스탬프 |
| `job_name` | NVARCHAR(100) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `metrics_json` | NVARCHAR | YES | NO |  | 설명/상태/메타 정보 |
| `started_at` | DATETIME2(3) | NO | NO | SYSUTCDATETIME() | 타임스탬프 |
| `status` | NVARCHAR(16) | NO | NO |  | 설명/상태/메타 정보 |

## `sys_notification` — 시스템 알림(채널/레벨/메시지/메타).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `notif_id` | BIGINT IDENTITY | YES | YES |  | NOTIF 식별자(FK 가능) |
| `channel` | NVARCHAR(16) | NO | NO |  | 설명/상태/메타 정보 |
| `level` | NVARCHAR(16) | NO | NO |  | 설명/상태/메타 정보 |
| `message` | NVARCHAR(400) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `meta_json` | NVARCHAR | YES | NO |  | 설명/상태/메타 정보 |
| `ts` | DATETIME2(3) | NO | NO | SYSUTCDATETIME() | 타임스탬프 |

## `dim_date` — 분석용 날짜 차원(YYYYMMDD/분기/영업일 등).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `date_key` | INT | YES | YES |  | 일자 |
| `date` | DATE | NO | NO |  | 일자 |
| `day` | TINYINT | NO | NO |  | 차원 속성/키 |
| `dow` | TINYINT | NO | NO |  | 차원 속성/키 |
| `is_business_day` | BIT | NO | NO |  | 차원 속성/키 |
| `month` | TINYINT | NO | NO |  | 차원 속성/키 |
| `quarter` | TINYINT | NO | NO |  | 차원 속성/키 |
| `year` | INT | NO | NO |  | 차원 속성/키 |

## `dim_account` — 분석용 계좌 차원(계좌/고객/통화/유형).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `account_key` | BIGINT IDENTITY | YES | YES |  | 컬럼 의미(도메인에 맞게 사용) |
| `account_id` | BIGINT | NO | NO |  | ACCOUNT 식별자(FK 가능) |
| `account_type` | NVARCHAR(16) | NO | NO |  | 분류/코드 값 |
| `base_currency` | CHAR(3) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `customer_id` | BIGINT | NO | NO |  | CUSTOMER 식별자(FK 가능) |

## `dim_security` — 분석용 종목 차원(거래소/유형/통화).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `security_key` | BIGINT IDENTITY | YES | YES |  | 컬럼 의미(도메인에 맞게 사용) |
| `currency_code` | CHAR(3) | NO | NO |  | 분류/코드 값 |
| `exchange_id` | INT | NO | NO |  | EXCHANGE 식별자(FK 가능) |
| `security_id` | BIGINT | NO | NO |  | SECURITY 식별자(FK 가능) |
| `symbol` | NVARCHAR(32) | NO | NO |  | 종목 식별자/코드 |
| `type_code` | NVARCHAR(16) | NO | NO |  | 분류/코드 값 |

## `dim_exchange` — 분석용 거래소 차원.

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `exchange_key` | INT IDENTITY | YES | YES |  | 컬럼 의미(도메인에 맞게 사용) |
| `code` | NVARCHAR(16) | NO | NO |  | 설명/상태/메타 정보 |
| `exchange_id` | INT | NO | NO |  | EXCHANGE 식별자(FK 가능) |
| `name` | NVARCHAR(100) | NO | NO |  | 설명/상태/메타 정보 |
| `tz` | NVARCHAR(40) | NO | NO |  | 분류/코드 값 |

## `fact_order` — 주문 팩트(날짜/계좌/종목/수량/가격/상태).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `order_id` | BIGINT | YES | YES |  | ORDER 식별자(FK 가능) |
| `account_key` | BIGINT | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `date_key` | INT | NO | NO |  | 일자 |
| `order_type` | NVARCHAR(16) | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `price` | DECIMAL(18,4) | YES | NO |  | 가격 |
| `qty` | DECIMAL(18,4) | NO | NO |  | 수량 |
| `security_key` | BIGINT | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `side` | CHAR(1) | NO | NO |  | 매수/매도 구분(B/S) |
| `status` | NVARCHAR(16) | NO | NO |  | 설명/상태/메타 정보 |

## `fact_execution` — 체결 팩트(날짜/계좌/종목/수량/가격/수수료/세금).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `execution_id` | BIGINT | YES | YES |  | EXECUTION 식별자(FK 가능) |
| `account_key` | BIGINT | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `date_key` | INT | NO | NO |  | 일자 |
| `exec_price` | DECIMAL(18,4) | NO | NO |  | 가격 |
| `exec_qty` | DECIMAL(18,4) | NO | NO |  | 수량 |
| `fee` | DECIMAL(18,4) | NO | NO |  | 수수료 |
| `order_id` | BIGINT | NO | NO |  | ORDER 식별자(FK 가능) |
| `security_key` | BIGINT | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `tax` | DECIMAL(18,4) | NO | NO |  | 세금 |

## `fact_position_snapshot` — 포지션 스냅샷 팩트(날짜/계좌/종목/수량/평단).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `snapshot_id` | BIGINT IDENTITY | YES | YES |  | SNAPSHOT 식별자(FK 가능) |
| `account_key` | BIGINT | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |
| `avg_price` | DECIMAL(18,6) | NO | NO |  | 가격 |
| `date_key` | INT | NO | NO |  | 일자 |
| `qty` | DECIMAL(18,4) | NO | NO |  | 수량 |
| `security_key` | BIGINT | NO | NO |  | 컬럼 의미(도메인에 맞게 사용) |

## `fact_pnl_daily` — 일별 PnL 팩트(실현/미실현/수수료/세금/MTM).

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `account_key` | BIGINT | NO | YES |  | 컬럼 의미(도메인에 맞게 사용) |
| `date_key` | INT | NO | YES |  | 일자 |
| `fees` | DECIMAL(18,4) | NO | NO |  | 수수료 |
| `mtm_value` | DECIMAL(18,4) | NO | NO |  | 시가평가 금액(MTM) |
| `realized_pnl` | DECIMAL(18,4) | NO | NO |  | 손익/평단/수량 |
| `taxes` | DECIMAL(18,4) | NO | NO |  | 세금 |
| `unrealized_pnl` | DECIMAL(18,4) | NO | NO |  | 손익/평단/수량 |

## `Numbers` — 

| 컬럼 | 타입 | NULL | PK | 기본값 | 의미 |
|---|---:|:---:|:---:|---|---|
| `n` | INT | NO | YES |  | 컬럼 의미(도메인에 맞게 사용) |
