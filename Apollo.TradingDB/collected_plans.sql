use TradingDB;

batch_t_collected_plans
usp_augment_collected_plans

select ((140000 * 7) + (70000 * 1)) * 0.8
select ((72000 * 7) + (70000 * 1)) * 0.8

--EXEC dbo.usp_augment_collected_plans @target_rows = 8200, @batch_size = 30;
--EXEC dbo.usp_augment_collected_plans @target_rows = 12590, @batch_size = 30;
--EXEC dbo.usp_augment_collected_plans @target_rows = 21456, @batch_size = 200;
--EXEC dbo.usp_augment_collected_plans @target_rows = 32974, @batch_size = 200;
--EXEC dbo.usp_augment_collected_plans @target_rows = 38062, @batch_size = 200;
--EXEC dbo.usp_augment_collected_plans @target_rows = 51714, @batch_size = 1000;
--EXEC dbo.usp_augment_collected_plans @target_rows = 65960, @batch_size = 200;
--EXEC dbo.usp_augment_collected_plans @target_rows = 78960, @batch_size = 400;
--EXEC dbo.usp_augment_collected_plans @target_rows = 105209, @batch_size = 1000;
--EXEC dbo.usp_augment_collected_plans @target_rows = 142637, @batch_size = 700;
--EXEC dbo.usp_augment_collected_plans @target_rows = 190406, @batch_size = 1000;

select  count(1)
        , min_collected_at = min(collected_at)
        , max_collected_at = max(collected_at)
        , min_last_exec_time = min(last_exec_time)
        , max_last_exec_time = max(last_exec_time)
from    collected_plans (nolock);

select TOP 20 * from collected_plans;

sp_columns collected_plans

select  convert(varchar(13), collected_at, 120)
        , count(1)
from    collected_plans
group by convert(varchar(13), collected_at, 120)
order by 1;

------------------------------------------------------------------

-- 테이블 49개
select  *
from    sys.objects
where   type = 'U'

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

-- 한번도 호출 안됨
usp_t_PlaceOrder_Limit_WithRecompile_084

-- dmv 활용해서 SP의 execution_count
select  s.db_name
        , s.schema_name
        , p.object_id
        , p.name
        , s.execution_count
        , s.cached_time
        , s.last_execution_time
        , s.total_elapsed_time
        , avg_elapsed_time = s.total_elapsed_time / s.execution_count
        , s.total_worker_time
        , avg_worker_time = s.total_worker_time / s.execution_count
FROM	sys.procedures p
        outer apply (
        SELECT  ps.object_id
                , db_name = min(DB_NAME(ps.database_id))
                , schema_name = min(OBJECT_SCHEMA_NAME(ps.object_id, ps.database_id))
                , execution_count = sum(ps.execution_count)
                , cached_time = min(ps.cached_time)
                , last_execution_time = max(ps.last_execution_time)
                , total_elapsed_time = sum(ps.total_elapsed_time)
                , total_worker_time = sum(ps.total_worker_time)
        FROM    sys.dm_exec_procedure_stats ps
        WHERE   ps.object_id = p.object_id
        group by ps.object_id
        ) s
WHERE	p.is_ms_shipped = 0
--order by execution_count;
--order by avg_worker_time desc;
order by avg_elapsed_time desc;


-- RL Phase 2에서 평가에 사용할 샘플 쿼리 목록 (성능 문제를 가진) -> Top 5 [avg_worker_time] 와 Top 5 [avg_elapsed_time] 의 합집합
usp_t_Batch_SettleAllTrades_061
usp_s_Admin_Rpt_DailyRiskExposure_089
usp_s_Admin_MonitorRecentTrades_035
usp_s_Admin_MonitorRecentTrades_ReadUncommitted_075
usp_s_Admin_GetOrphanedExecutions_097
usp_s_CheckAllTableFragmentation_100
usp_t_Batch_GenerateRiskSnapshots_066

---

SET STATISTICS IO ON; SET STATISTICS TIME ON; SET STATISTICS XML ON;
SELECT TOP 100 execution_id FROM dbo.exe_execution e;

SELECT TOP 200 AccountID=o.account_id, SecID=o.security_id, Side=o.side, Qty=e.exec_qty, Price=e.exec_price, Fee=e.fee, Tax=e.tax FROM dbo.exe_execution e JOIN dbo.ord_order o ON e.order_id=o.order_id;

SELECT TOP 300 * FROM dbo.risk_exposure_snapshot WHERE CAST(ts AS DATE) = cast(getdate() as date);

SELECT TOP 400 e.execution_id, o.account_id, s.symbol, o.side, e.exec_qty, e.exec_price, e.exec_time FROM dbo.exe_execution e JOIN dbo.ord_order o ON e.order_id=o.order_id JOIN dbo.ref_security s ON o.security_id=s.security_id ORDER BY e.exec_time DESC;

SELECT e.* FROM dbo.exe_execution e WHERE NOT EXISTS (SELECT 1 FROM dbo.ord_order o WHERE o.order_id = e.order_id);

SELECT OBJECT_NAME(ips.object_id) AS TableName, si.name AS IndexName, ips.index_type_desc, ips.avg_fragmentation_in_percent FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'SAMPLED') AS ips JOIN sys.indexes AS si ON ips.object_id = si.object_id AND ips.index_id = si.index_id WHERE ips.avg_fragmentation_in_percent > 30.0 ORDER BY ips.avg_fragmentation_in_percent DESC;

SELECT account_id, GETDATE(), RAND()*100000, RAND()*50000, 0, 0 FROM dbo.cust_account WHERE closed_at IS NULL;





SELECT execution_id FROM dbo.exe_execution e;
SELECT AccountID=o.account_id, SecID=o.security_id, Side=o.side, Qty=e.exec_qty, Price=e.exec_price, Fee=e.fee, Tax=e.tax FROM dbo.exe_execution e JOIN dbo.ord_order o ON e.order_id=o.order_id;

SELECT TOP 3000 * FROM dbo.risk_exposure_snapshot /*WHERE CAST(ts AS DATE) = cast(getdate() as date)*/;

SELECT e.execution_id, o.account_id, s.symbol, o.side, e.exec_qty, e.exec_price, e.exec_time FROM dbo.exe_execution e JOIN dbo.ord_order o ON e.order_id=o.order_id JOIN dbo.ref_security s ON o.security_id=s.security_id ORDER BY e.exec_time DESC;
SELECT e.* FROM dbo.exe_execution e WHERE NOT EXISTS (SELECT 1 FROM dbo.ord_order o WHERE o.order_id = e.order_id);
SELECT account_id, GETDATE(), RAND()*100000, RAND()*50000, 0, 0 FROM dbo.cust_account WHERE closed_at IS NULL;

SET TRANSACTION ISOLATION LEVEL READ COMMITTED
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
SET TRANSACTION ISOLATION LEVEL READ SNAPSHOT

---

select  top 1 *
from    collected_plans
where   sql_text like '%usp_t_Batch_SettleAllTrades_061%'

DBA_All_Sessions @SessionStatus = '(All)'


KB 1,385,051
1,447,896

select 480000 + 636719 + 331177

select 11000000.0 / 36
월 원리금 305,556

select 14087820.0 / 36
월 원리금 391,329

select datediff(day, '2025-07-14', '2025-12-31') / 365.0
select 136496 - 134448


SELECT  TOP 200 account_id,
        ts,
        gross,
        net,
        var_1d,
        margin_required,
        (gross - net) AS long_short_imbalance
FROM    dbo.risk_exposure_snapshot
WHERE   ts >= DATEADD(DAY, DATEDIFF(DAY, 0, GETDATE()) - 7, 0)
AND     ts < DATEADD(DAY, DATEDIFF(DAY, 0, GETDATE()) + 1, 0)
ORDER BY ts DESC, gross DESC
OPTION (RECOMPILE, LOOP JOIN)
;

create nonclustered index idx_risk_exposure_snapshot_ts on dbo.risk_exposure_snapshot (ts);

------------------------------------------------------------------

select * from collected_plans where est_total_subtree_cost is null;

-- backfill query
WITH XMLNAMESPACES (DEFAULT 'http://schemas.microsoft.com/sqlserver/2004/07/showplan')
update  a
set     est_total_subtree_cost = isnull(isnull(d.est_total_subtree_cost1, d.est_total_subtree_cost2), d.est_total_subtree_cost3)
from    collected_plans a
        cross apply (
        select  est_total_subtree_cost1 = c.plan_xml.value(
                  '(/ShowPlanXML/BatchSequence/Batch/Statements/*/QueryPlan/RelOp/@EstimatedTotalSubtreeCost)[1]',
                  'float'
                )
                , est_total_subtree_cost2 = c.plan_xml.value(
                  '(/ShowPlanXML/BatchSequence/Batch/Statements/*/*/QueryPlan/RelOp/@EstimatedTotalSubtreeCost)[1]',
                  'float'
                )
                , est_total_subtree_cost3 = c.plan_xml.value(
                  '(/ShowPlanXML/BatchSequence/Batch/Statements/*/*/*/QueryPlan/RelOp/@EstimatedTotalSubtreeCost)[1]',
                  'float'
                )
        from    collected_plans c
        where   c.collected_at = a.collected_at
        and     c.query_id = a.query_id
        and     c.plan_id = a.plan_id
        ) d
where   a.est_total_subtree_cost is null

------------------------------------------------------------------

DROP TABLE IF EXISTS dbo.collected_plans;

CREATE TABLE dbo.collected_plans
(
  collected_at       datetime2      NOT NULL DEFAULT sysdatetime(),
  query_id           bigint         NOT NULL,
  plan_id            bigint         NOT NULL,
  query_hash         binary(8)      NULL,
  plan_hash          binary(8)      NULL,
  sql_text           nvarchar(max)  NULL,
  plan_xml           xml            NOT NULL,
  count_exec         bigint         NULL,
  est_total_subtree_cost float null,
  last_ms            float          NULL,
  avg_ms             float          NULL,
  last_cpu_ms        float          NULL,
  last_reads         bigint         NULL,
  max_used_mem_kb    bigint         NULL,
  max_dop            int            NULL,
  last_exec_time     datetime2      NULL,
  CONSTRAINT PK_collected_plans PRIMARY KEY (collected_at, query_id, plan_id)
);

alter TABLE dbo.collected_plans add est_total_subtree_cost float null;

------------------------------------------------------------------