using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.DependencyInjection;
using System;
using System.Collections.Generic;
using System.Data;
using System.Threading;
using System.Threading.Tasks;
using Dapper;
using Apollo.Core.Model;

namespace Apollo.Scheduler;

public class DbHammerService : BackgroundService
{
    private readonly ILogger<DbHammerService> _logger;
    private readonly IServiceProvider _serviceProvider;
    private readonly int _workerCount = 10; // 동시에 실행할 워커(스레드) 수
    private StoredProcedureList _spList = new();

    public DbHammerService(ILogger<DbHammerService> logger, IServiceProvider serviceProvider)
    {
        _logger = logger;
        _serviceProvider = serviceProvider;
    }
    
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation($"DbHammerService is starting with {_workerCount} workers.");

        // 저장프로시저 메타데이터 로드
        _spList = await GetStoredProcedureList();

        if (_spList.SPs?.Count == 0)
        {
            _logger.LogWarning("Failed to load stored procedure metadata. DbHammerService cannot start.");
            return;
        }

        var workerTasks = new List<Task>();

        for (int i = 0; i < _workerCount; i++)
        {
            // workerId: 각 워커에 고유 ID를 부여하여 로그 추적을 용이하게 함.
            // E.g., 1, 2, ..., 99, 100
            workerTasks.Add(RunWorkerAsync(i + 1, stoppingToken));
        }

        await Task.WhenAll(workerTasks);

        _logger.LogInformation($"DbHammerService has stopped.");
    }

    private async Task RunWorkerAsync(int workerId, CancellationToken stoppingToken)
    {
        _logger.LogInformation($"Worker {workerId} is starting.");

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                // DbContext는 스레드에 안전하지 않으므로, 각 작업 범위(scope) 내에서 새로 생성해야 합니다.
                using var scope = _serviceProvider.CreateScope();
                
                // TODO: Entity Framework Core DbContext를 DI 컨테이너로부터 받아와야 합니다.
                // var dbContext = scope.ServiceProvider.GetRequiredService<MyDbContext>();
                
                _logger.LogInformation("Worker {WorkerId} is executing a query.", workerId);
                
                // TODO: 실제 DB 쿼리 로직을 구현해야 합니다.
                // await dbContext.Users.Take(10).ToListAsync(stoppingToken);
                
                // (선택 사항) 실제 사용자 행동과 유사한 패턴을 만들기 위해 쿼리 사이에 임의의 지연 시간을 줄 수 있습니다.
                await Task.Delay(TimeSpan.FromMilliseconds(100), stoppingToken);
            }
            catch (OperationCanceledException)
            {
                // 서비스가 중지될 때 Task.Delay에서 발생하는 예외는 정상적인 동작이므로 무시합니다.
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "An error occurred in Worker {WorkerId}.", workerId);
                
                // 오류 발생 시, 시스템에 과도한 부하를 주지 않기 위해 잠시 대기 후 다음 작업을 시도합니다.
                await Task.Delay(TimeSpan.FromSeconds(1), stoppingToken);
            }
        }

        _logger.LogInformation($"Worker {workerId} is stopped.");
    }

    private async Task<StoredProcedureList> GetStoredProcedureList()
    {
        // DB에서 SP 메타데이터 로드
        try
        {
            _logger.LogInformation("Loading stored procedure metadata from database...");

            using var scope = _serviceProvider.CreateScope();
            var connection = scope.ServiceProvider.GetRequiredService<IDbConnection>();

            // DB의 시스템 뷰를 조회하여 SP와 파라미터 정보를 가져오는 SQL 쿼리
            var sql = @"/* DbHammerService에서 SP와 파라미터 조회 */
SELECT	ProcedureName = p.name
	, ParameterId = m.parameter_id
	, ParameterName = m.name
	, TypeName = t.name
	, MaxLength = case when t.name in ('nvarchar', 'nchar') then m.max_length / 2 else m.max_length end
	, IsNullable = m.is_nullable
FROM	sys.procedures p
	LEFT OUTER JOIN sys.parameters m ON p.object_id = m.object_id
	LEFT OUTER JOIN sys.types t ON m.system_type_id = t.system_type_id and m.user_type_id = t.user_type_id
WHERE	p.is_ms_shipped = 0 -- Microsoft 기본 제공 SP 제외
ORDER BY ProcedureName, m.parameter_id;";
            sql = sql.Trim();

            // 쿼리 실행
            var rawList = await connection.QueryAsync<StoredProcedureRawdata>(sql);

            var procList = rawList
                .GroupBy(row => row.ProcedureName) // 프로시저 이름으로 그룹화
                .Select(group => new StoredProcedureModel // 각 그룹을 ProcedureMetadata 객체로 변환
                {
                    Name = group.Key, // 그룹의 키가 프로시저 이름
                    Parameters = group
                        .Where(row => row.ParameterName != null) // 파라미터가 없는 SP의 경우를 대비
                        .Select(row => new ParameterMetadata // 각 그룹의 항목들을 ParameterMetadata 객체로 변환
                        {
                            Name = row.ParameterName ?? "",
                            SqlTypeName = row.TypeName ?? "",
                            MaxLength = row.MaxLength ?? 0,
                            IsNullable = row.IsNullable ?? true
                        }).ToList()
                }).ToList();

            _logger.LogInformation($"{procList.Count} Stored Procedures metadata loaded.");

            return new StoredProcedureList { SPs = procList };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "An error occurred while loading stored procedure metadata.");

            return new StoredProcedureList(); // 예외 발생 시 빈 리스트 반환
        }
    }
}