use TradingDB;

-- 테이블 49개
select  *
from    sys.objects
where   type = 'U'

batch_t_collected_plans
usp_augment_collected_plans

--EXEC dbo.usp_augment_collected_plans @target_rows = 11567, @batch_size = 300;
--EXEC dbo.usp_augment_collected_plans @target_rows = 8200, @batch_size = 30;
--EXEC dbo.usp_augment_collected_plans @target_rows = 12590, @batch_size = 30;
--EXEC dbo.usp_augment_collected_plans @target_rows = 21456, @batch_size = 200;

select count(1) from collected_plans;
select TOP 20 * from collected_plans;

sp_columns collected_plans

select  convert(varchar(13), collected_at, 120)
        , count(1)
from    collected_plans
group by convert(varchar(13), collected_at, 120)
order by 1;

------------------------------------------------------------------

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
order by execution_count;


usp_t_PlaceOrder_Limit_WithRecompile_084

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