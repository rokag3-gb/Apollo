use TradingDB;

-- 테이블 49개
select  *
from    sys.objects
where   type = 'U'

exec TradingDB.dbo.batch_t_collected_plans;

select * from collected_plans;

sp_columns collected_plans

-- SP 99개
select  *
--select  'drop proc ' + object_name(object_id) + ';'
from    sys.all_sql_modules
where   object_id > 0
and     object_name(object_id) like 'up_%'
and     object_name(object_id) not in ('batch_t_collected_plans');

select  p.*
FROM	sys.procedures p
WHERE	p.is_ms_shipped = 0 -- Microsoft 기본 제공 SP 제외

sp_helptext up_s_query_admin_audit_event_summary


select *
from sp_catalog
where sp_name like 'usp_t_%'

sp_helptext usp_t_UpdateSecurityPrice_001

select *
from sys.parameters



SELECT	ProcedureName = p.name
	, Caller = c.caller
	, ParameterId = m.parameter_id
	, ParameterName = m.name
	, TypeName = t.name
	, MaxLength = case when t.name in ('nvarchar', 'nchar') then m.max_length / 2 else m.max_length end
	, IsNullable = m.is_nullable
	--, pm.*
FROM	sys.procedures p
	LEFT OUTER JOIN sys.parameters m ON p.object_id = m.object_id
	LEFT OUTER JOIN sys.types t ON m.system_type_id = t.system_type_id and m.user_type_id = t.user_type_id
	LEFT OUTER JOIN sp_catalog c on p.name = c.sp_name
WHERE	p.is_ms_shipped = 0 -- Microsoft 기본 제공 SP 제외
--AND	p.name LIKE 'usp_t_RegisterCustomer_009%' -- 특정 패턴의 SP만 가져오고 싶을 경우
ORDER BY ProcedureName, m.parameter_id;


SELECT	ParameterName = m.name
FROM	sys.procedures p
	LEFT OUTER JOIN sys.parameters m ON p.object_id = m.object_id
	LEFT OUTER JOIN sys.types t ON m.system_type_id = t.system_type_id and m.user_type_id = t.user_type_id
	LEFT OUTER JOIN sp_catalog c on p.name = c.sp_name
WHERE	p.is_ms_shipped = 0 -- Microsoft 기본 제공 SP 제외
group by m.name



sp_helptext stp_Users_Insert
sp_helptext stp_UserSecurities_Insert


-- Blocking Query (9/11)
usp_s_Admin_MonitorRecentTrades_035
usp_t_Batch_SettleAllTrades_061
usp_t_Batch_GenerateRiskSnapshots_066
usp_t_Batch_RebuildIndexes_069
usp_s_Admin_MonitorRecentTrades_ReadUncommitted_075

-- SP 채택 목록에서 제외 (ALTER INDEX REBUILD, REORGANIZE)
DROP PROC usp_t_Batch_RebuildIndexes_069;
DROP PROC usp_t_Batch_DefragmentIndexes_095;

-- Blocking Query (9/12)
usp_t_Batch_GenerateRiskSnapshots_066






------------------------------------------------------------------

DROP TABLE IF EXISTS dbo.collected_plans;

CREATE TABLE dbo.collected_plans
(
  collected_at       datetime2      NOT NULL DEFAULT sysdatetime(),
  query_id           bigint         NOT NULL,
  plan_id            bigint         NOT NULL,
  --seq_id             bigint identity(1, 1) not null,
  query_hash         binary(8)      NULL,
  plan_hash          binary(8)      NULL,
  sql_text           nvarchar(max)  NULL,
  plan_xml           xml            NOT NULL,
  count_exec         bigint         NULL,
  last_ms            float          NULL,
  avg_ms             float          NULL,
  last_cpu_ms        float          NULL,
  last_reads         bigint         NULL,
  max_used_mem_kb    bigint         NULL,
  max_dop            int            NULL,
  last_exec_time     datetime2      NULL,
  CONSTRAINT PK_collected_plans PRIMARY KEY (collected_at, query_id, plan_id) -- seq_id
);

------------------------------------------------------------------

CREATE OR ALTER PROC batch_t_collected_plans
        @LAST_HOUR INT = 3
AS
DECLARE @batch_ts datetime2(3) = SYSUTCDATETIME();
set nocount on;

WITH rs AS
(
    SELECT
        rs.plan_id,
        SUM(rs.count_executions) AS count_exec,
        MAX(rs.last_duration) / 1000.0 AS last_ms,
        CASE WHEN SUM(rs.count_executions) > 0
             THEN (SUM(rs.count_executions * rs.avg_duration) * 1.0) / SUM(rs.count_executions) / 1000.0
             ELSE NULL
        END AS avg_ms,
        MAX(rs.last_cpu_time) / 1000.0 AS last_cpu_ms,
        MAX(rs.last_logical_io_reads) AS last_reads,
        MAX(rs.max_dop) AS max_dop,
        MAX(rs.last_execution_time) AS last_exec_time,

        -- 메모리: 8KB 페이지 단위 → KB로 변환(×8)
        MAX(rs.max_query_max_used_memory) * 8 AS max_used_mem_kb
        -- 필요하면 최근 실행 기준도 가져올 수 있음:
        -- , MAX(rs.last_query_max_used_memory) * 8 AS last_used_mem_kb
    FROM sys.query_store_runtime_stats AS rs
    WHERE rs.last_execution_time >= DATEADD(hour, @LAST_HOUR * (-1), SYSUTCDATETIME())
    GROUP BY rs.plan_id
)
INSERT dbo.collected_plans
(
    collected_at, query_id, plan_id, query_hash, plan_hash,
    sql_text, plan_xml,
    count_exec, last_ms, avg_ms, last_cpu_ms, last_reads,
    max_used_mem_kb, max_dop, last_exec_time
)
SELECT
    @batch_ts,
    qsq.query_id,
    qsp.plan_id,
    qsq.query_hash,
    CONVERT(varbinary(8), SUBSTRING(HASHBYTES('SHA2_256', qsp.query_plan), 1, 8)) AS plan_hash, -- DMV 없이 대체 해시
    qsqt.query_sql_text,
    TRY_CAST(qsp.query_plan AS xml),
    rs.count_exec,
    rs.last_ms,
    rs.avg_ms,
    rs.last_cpu_ms,
    rs.last_reads,
    rs.max_used_mem_kb,
    rs.max_dop,
    rs.last_exec_time
FROM rs
JOIN sys.query_store_plan       AS qsp  ON qsp.plan_id = rs.plan_id
JOIN sys.query_store_query      AS qsq  ON qsq.query_id = qsp.query_id
JOIN sys.query_store_query_text AS qsqt ON qsqt.query_text_id = qsq.query_text_id
WHERE NOT EXISTS
(
    SELECT 1
    FROM dbo.collected_plans t
    WHERE t.collected_at = @batch_ts
      AND t.query_id     = qsq.query_id
      AND t.plan_id      = qsp.plan_id
);

------------------------------------------------------------------

/*
INSERT dbo.collected_plans (query_id, plan_id, query_hash, plan_hash, sql_text, plan_xml,
                            count_exec, last_ms, avg_ms, last_cpu_ms, last_reads,
                            max_used_mem_kb, max_dop, last_exec_time)
SELECT
    qsq.query_id,
    qsp.plan_id,
    qs.query_hash,
    plan_hash = null, -- qs.plan_hash
    qsqt.query_sql_text,
    TRY_CAST(qsp.query_plan AS xml),
    rs.count_executions,
    rs.last_duration/1000.0       AS last_ms,
    rs.avg_duration/1000.0        AS avg_ms,
    rs.last_cpu_time/1000.0       AS last_cpu_ms,
    rs.last_logical_io_reads      AS last_reads,
    max_used_memory_kb = null, -- rs.max_used_memory_kb
    rs.max_dop,
    rs.last_execution_time
FROM sys.query_store_query qsq
JOIN sys.query_store_plan qsp           ON qsp.query_id = qsq.query_id
JOIN sys.query_store_query_text qsqt    ON qsqt.query_text_id = qsq.query_text_id
JOIN sys.query_store_runtime_stats rs   ON rs.plan_id = qsp.plan_id
CROSS APPLY sys.dm_exec_query_stats qs
WHERE rs.last_execution_time >= DATEADD(minute, -10, sysdatetime());  -- 최근 10분

SELECT TOP (5000)
    DB_NAME()                AS dbname,
    qsq.query_id, qsp.plan_id,
    qsqt.query_sql_text,
    TRY_CAST(qsp.query_plan AS XML) AS plan_xml,
    rs.last_duration/1000.0  AS last_ms,
    rs.avg_duration/1000.0   AS avg_ms,
    rs.last_cpu_time/1000.0  AS cpu_ms,
    rs.last_logical_io_reads AS logical_reads,
    rs.max_used_memory_kb,
    rs.count_executions,
    rs.last_execution_time
FROM sys.query_store_query qsq
JOIN sys.query_store_plan  qsp ON qsp.query_id = qsq.query_id
JOIN sys.query_store_query_text qsqt ON qsqt.query_text_id = qsq.query_text_id
JOIN sys.query_store_runtime_stats rs ON rs.plan_id = qsp.plan_id
WHERE rs.last_execution_time >= DATEADD(hour, -6, SYSDATETIME())
ORDER BY rs.last_execution_time DESC;

select * from sys.query_store_runtime_stats
*/