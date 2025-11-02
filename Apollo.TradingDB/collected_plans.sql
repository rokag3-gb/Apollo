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

------------------------------------------------------------------

SET STATISTICS IO ON; SET STATISTICS TIME ON; SET STATISTICS XML ON;
SELECT TOP 100 execution_id FROM dbo.exe_execution e;

SELECT TOP 200 AccountID=o.account_id, SecID=o.security_id, Side=o.side, Qty=e.exec_qty, Price=e.exec_price, Fee=e.fee, Tax=e.tax FROM dbo.exe_execution e JOIN dbo.ord_order o ON e.order_id=o.order_id;

SELECT TOP 300 * FROM dbo.risk_exposure_snapshot WHERE CAST(ts AS DATE) = cast(getdate() as date);

SELECT TOP 400 e.execution_id, o.account_id, s.symbol, o.side, e.exec_qty, e.exec_price, e.exec_time FROM dbo.exe_execution e JOIN dbo.ord_order o ON e.order_id=o.order_id JOIN dbo.ref_security s ON o.security_id=s.security_id ORDER BY e.exec_time DESC;

SELECT e.* FROM dbo.exe_execution e WHERE NOT EXISTS (SELECT 1 FROM dbo.ord_order o WHERE o.order_id = e.order_id);

SELECT OBJECT_NAME(ips.object_id) AS TableName, si.name AS IndexName, ips.index_type_desc, ips.avg_fragmentation_in_percent FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'SAMPLED') AS ips JOIN sys.indexes AS si ON ips.object_id = si.object_id AND ips.index_id = si.index_id WHERE ips.avg_fragmentation_in_percent > 30.0 ORDER BY ips.avg_fragmentation_in_percent DESC;

SELECT account_id, GETDATE(), RAND()*100000, RAND()*50000, 0, 0 FROM dbo.cust_account WHERE closed_at IS NULL;

------------------------------------------------------------------

select  original_query_text
from    rlqo_optimization_proposals
where   proposal_id = 122

select  optimized_query_text
from    rlqo_optimization_proposals
where   proposal_id = 122


select  *
from    rlqo_optimization_proposals
where   approval_status = 'PENDING';

update  a
set     proposal_datetime = dateadd(day, -5, proposal_datetime)
from    rlqo_optimization_proposals a


------------------------------------------------------------------

-- =============================================
-- RLQO 쿼리 최적화 제안 테이블
-- Ensemble v2 모델이 제안한 쿼리 개선 사항 저장
-- =============================================

USE TradingDB;
GO

IF OBJECT_ID('dbo.rlqo_optimization_proposals', 'U') IS NOT NULL
    DROP TABLE dbo.rlqo_optimization_proposals;
GO

CREATE TABLE dbo.rlqo_optimization_proposals
(
    -- 기본 정보
    proposal_id             BIGINT IDENTITY(1,1) PRIMARY KEY,
    proposal_datetime       DATETIME2(3) NOT NULL DEFAULT SYSDATETIME(),
    model_name              NVARCHAR(100) NOT NULL,         -- 예: 'Ensemble_v2', 'PPO_v3', 'DDPG_v1'
    
    -- 쿼리 텍스트
    original_query_text     NVARCHAR(MAX) NOT NULL,         -- 기존 쿼리
    optimized_query_text    NVARCHAR(MAX) NOT NULL,         -- 수정된 쿼리 (힌트 포함)
    query_hash              VARBINARY(8) NULL,              -- 쿼리 식별용 해시
    
    -- 성능 메트릭: Baseline (기존 쿼리)
    baseline_elapsed_time_ms    DECIMAL(18,3) NOT NULL,
    baseline_cpu_time_ms        DECIMAL(18,3) NOT NULL,
    baseline_logical_reads      BIGINT NOT NULL,
    baseline_physical_reads     BIGINT NULL,
    baseline_writes             BIGINT NULL,
    
    -- 성능 메트릭: Optimized (수정된 쿼리)
    optimized_elapsed_time_ms   DECIMAL(18,3) NOT NULL,
    optimized_cpu_time_ms       DECIMAL(18,3) NOT NULL,
    optimized_logical_reads     BIGINT NOT NULL,
    optimized_physical_reads    BIGINT NULL,
    optimized_writes            BIGINT NULL,
    
    -- 성능 개선율
    speedup_ratio               DECIMAL(10,4) NOT NULL,     -- elapsed_time 기준 개선율
    cpu_improvement_ratio       DECIMAL(10,4) NULL,         -- CPU time 개선율
    reads_improvement_ratio     DECIMAL(10,4) NULL,         -- Logical reads 개선율
    
    -- 추가 정보
    query_type                  NVARCHAR(50) NULL,          -- 예: 'SIMPLE', 'CTE', 'JOIN_HEAVY'
    episode_count               INT NULL,                   -- 실행 횟수 (평균값인 경우)
    confidence_score            DECIMAL(5,4) NULL,          -- 모델 신뢰도 (있는 경우)
    
    -- 승인 및 적용 관리
    approval_status             NVARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- 'PENDING', 'APPROVED', 'REJECTED', 'APPLIED'
    reviewed_by                 NVARCHAR(100) NULL,         -- DB 엔지니어 이름
    reviewed_datetime           DATETIME2(3) NULL,
    applied_datetime            DATETIME2(3) NULL,
    rollback_datetime           DATETIME2(3) NULL,
    
    -- 비고
    notes                       NVARCHAR(MAX) NULL,         -- 리뷰 의견, 적용 결과 등
    
    -- 인덱스
    INDEX IX_proposal_datetime (proposal_datetime DESC),
    INDEX IX_model_name (model_name),
    INDEX IX_approval_status (approval_status),
    INDEX IX_speedup_ratio (speedup_ratio DESC)
);
GO

-- =============================================
-- 설명용 Extended Properties
-- =============================================
EXEC sys.sp_addextendedproperty 
    @name=N'MS_Description', 
    @value=N'RLQO(Reinforcement Learning Query Optimizer) 모델이 제안한 쿼리 최적화 내역을 저장하는 테이블. DB 엔지니어가 검토하고 승인/적용 여부를 관리함.',
    @level0type=N'SCHEMA', @level0name=N'dbo',
    @level1type=N'TABLE',  @level1name=N'rlqo_optimization_proposals';
GO

EXEC sys.sp_addextendedproperty 
    @name=N'MS_Description', 
    @value=N'기존 쿼리 대비 실행 시간(elapsed_time) 개선율. 2.172는 2.172배 빨라졌음을 의미.',
    @level0type=N'SCHEMA', @level0name=N'dbo',
    @level1type=N'TABLE',  @level1name=N'rlqo_optimization_proposals',
    @level2type=N'COLUMN', @level2name=N'speedup_ratio';
GO

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