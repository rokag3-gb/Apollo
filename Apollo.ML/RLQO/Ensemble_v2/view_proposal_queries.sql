-- =============================================
-- rlqo_optimization_proposals 테이블의 쿼리 텍스트 조회
-- CRLF를 포함한 원본 형태로 출력
-- =============================================

USE TradingDB;
GO

-- 특정 1건 상세 조회 (가장 높은 speedup을 가진 레코드)
DECLARE @proposal_id INT;

-- 최고 성능 개선 쿼리 선택
SELECT TOP 1 @proposal_id = proposal_id
FROM dbo.rlqo_optimization_proposals
WHERE model_name = 'Ensemble_v2_Oracle'
  AND approval_status = 'PENDING'
ORDER BY speedup_ratio DESC;

PRINT '================================================================================';
PRINT '제안 ID: ' + CAST(@proposal_id AS NVARCHAR(10));
PRINT '================================================================================';
PRINT '';

-- 기본 정보
SELECT 
    proposal_id,
    model_name,
    query_type,
    speedup_ratio,
    baseline_elapsed_time_ms,
    optimized_elapsed_time_ms,
    cpu_improvement_ratio,
    reads_improvement_ratio,
    confidence_score,
    approval_status,
    notes,
    proposal_datetime
FROM dbo.rlqo_optimization_proposals
WHERE proposal_id = @proposal_id;

PRINT '';
PRINT '================================================================================';
PRINT '기존 쿼리 (Original Query)';
PRINT '================================================================================';
PRINT '';

-- 기존 쿼리 출력
SELECT original_query_text AS [Original Query Text]
FROM dbo.rlqo_optimization_proposals
WHERE proposal_id = @proposal_id;

PRINT '';
PRINT '================================================================================';
PRINT '제안된 쿼리 (Optimized Query)';
PRINT '================================================================================';
PRINT '';

-- 제안된 쿼리 출력
SELECT optimized_query_text AS [Optimized Query Text]
FROM dbo.rlqo_optimization_proposals
WHERE proposal_id = @proposal_id;

GO

-- =============================================
-- 또는 특정 proposal_id로 직접 조회하려면:
-- =============================================

-- 예시: proposal_id = 3 (최고 성능)
DECLARE @id INT = 3;

PRINT '================================================================================';
PRINT 'Proposal ID: ' + CAST(@id AS NVARCHAR(10));
PRINT '================================================================================';

SELECT 
    '=== 기본 정보 ===' AS Section,
    proposal_id,
    query_type,
    CAST(speedup_ratio AS DECIMAL(10,4)) AS speedup_ratio,
    CAST(baseline_elapsed_time_ms AS DECIMAL(10,2)) AS baseline_ms,
    CAST(optimized_elapsed_time_ms AS DECIMAL(10,2)) AS optimized_ms,
    CAST((baseline_elapsed_time_ms - optimized_elapsed_time_ms) AS DECIMAL(10,2)) AS saved_ms,
    notes
FROM dbo.rlqo_optimization_proposals
WHERE proposal_id = @id;

PRINT '';
PRINT '--- 기존 쿼리 (Original) ---';
SELECT original_query_text 
FROM dbo.rlqo_optimization_proposals
WHERE proposal_id = @id;

PRINT '';
PRINT '--- 제안된 쿼리 (Optimized) ---';
SELECT optimized_query_text 
FROM dbo.rlqo_optimization_proposals
WHERE proposal_id = @id;

GO

-- =============================================
-- SSMS에서 텍스트 결과로 보려면:
-- 쿼리 실행 전 Ctrl+T 누르거나 아래 옵션 설정
-- =============================================

-- SET NOCOUNT ON;
-- 
-- DECLARE @id INT = 3;
-- 
-- DECLARE @original NVARCHAR(MAX);
-- DECLARE @optimized NVARCHAR(MAX);
-- 
-- SELECT 
--     @original = original_query_text,
--     @optimized = optimized_query_text
-- FROM dbo.rlqo_optimization_proposals
-- WHERE proposal_id = @id;
-- 
-- PRINT '================================================================================';
-- PRINT '기존 쿼리';
-- PRINT '================================================================================';
-- PRINT @original;
-- PRINT '';
-- PRINT '================================================================================';
-- PRINT '제안된 쿼리';
-- PRINT '================================================================================';
-- PRINT @optimized;

GO

