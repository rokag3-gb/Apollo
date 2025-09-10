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
using Newtonsoft.Json;
using System.Linq;

namespace Apollo;

public class DbHammerService : BackgroundService
{
    private readonly ILogger<DbHammerService> _logger;
    private readonly IServiceProvider _serviceProvider;
    
    private StoredProcedureList _spList = new();
    private List<StoredProcedureModel> _spListUser = new();
    private List<StoredProcedureModel> _spListAdmin = new();
    private List<StoredProcedureModel> _spListBatch = new();

    private readonly int _workerCount = 3; // 동시에 실행할 워커(스레드) 수

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

        if (_spList.Procedures is null || _spList.Procedures.Count == 0)
        {
            _logger.LogWarning("Failed to load stored procedure metadata. DbHammerService cannot start.");
            return;
        }

        // Caller 타입에 따라 SP 리스트를 미리 필터링하여 준비
        _spListUser = _spList.Procedures.Where(p => "User".Equals(p.Caller, StringComparison.OrdinalIgnoreCase)).ToList();
        _spListAdmin = _spList.Procedures.Where(p => "Admin".Equals(p.Caller, StringComparison.OrdinalIgnoreCase)).ToList();
        _spListBatch = _spList.Procedures.Where(p => "Batch".Equals(p.Caller, StringComparison.OrdinalIgnoreCase)).ToList();

        _logger.LogInformation(
            "SP lists filtered by caller: User({userCount}), Admin({adminCount}), Batch({batchCount})",
            _spListUser.Count, _spListAdmin.Count, _spListBatch.Count);

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
                // 1. Caller 비율에 따라 가중치를 적용하여 랜덤으로 SP 선택
                var spToRun = SelectRandomSpWeighted();

                if (spToRun == null)
                {
                    _logger.LogWarning($"Worker {workerId}: Could not select a stored procedure to run (list might be empty). Retrying...");
                    await Task.Delay(TimeSpan.FromSeconds(0.8), stoppingToken); // 잠시 후 재시도
                    continue;
                }

                // 2. 선택된 SP의 메타데이터를 기반으로 랜덤 파라미터 생성
                var parameters = GenerateRandomParameters(spToRun);

                // 3. DB 연결을 가져와 Dapper로 SP 실행
                using var scope = _serviceProvider.CreateScope();
                var connection = scope.ServiceProvider.GetRequiredService<IDbConnection>();

                await connection.ExecuteAsync(
                    spToRun.Name,
                    parameters,
                    commandType: CommandType.StoredProcedure);

                // (선택 사항) 성공 로그. 너무 자주 출력되면 성능에 영향을 줄 수 있으므로 필요시 주석 처리
                var paramLog = parameters.ParameterNames.ToDictionary(name => name, name => parameters.Get<object>(name));
                _logger.LogInformation($"Worker [{workerId}] SP: [{spToRun.Name}] Caller: [{spToRun.Caller}] Params: [{JsonConvert.SerializeObject(paramLog)}]");
                
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
                _logger.LogError(ex, $"An error occurred in Worker {workerId}.");
                
                // 오류 발생 시, 시스템에 과도한 부하를 주지 않기 위해 잠시 대기 후 다음 작업을 시도합니다.
                await Task.Delay(TimeSpan.FromSeconds(0.5), stoppingToken);
            }
        }

        _logger.LogInformation($"Worker {workerId} is stopped.");
    }

    private StoredProcedureModel? SelectRandomSpWeighted()
    {
        var rand = Random.Shared;
        int roll = rand.Next(1, 11); // 1부터 10까지의 난수 생성

        // 7:2:1 비율에 따라 리스트 선택
        if (roll <= 7 && _spListUser.Count > 0) // 1-7 (70% 확률)
        {
            return _spListUser[rand.Next(_spListUser.Count)];
        }
        if (roll <= 9 && _spListAdmin.Count > 0) // 8-9 (20% 확률)
        {
            return _spListAdmin[rand.Next(_spListAdmin.Count)];
        }
        if (roll <= 10 && _spListBatch.Count > 0) // 10 (10% 확률)
        {
            return _spListBatch[rand.Next(_spListBatch.Count)];
        }

        // 특정 Caller 타입의 SP가 없는 경우, 또는 가중치 롤에 실패한 경우 전체 리스트에서 랜덤으로 선택 (Fallback)
        if (_spList.Procedures != null && _spList.Procedures.Count > 0)
            return _spList.Procedures[rand.Next(_spList.Procedures.Count)];
        
        return null; // 실행할 SP가 하나도 없는 경우
    }

    private DynamicParameters GenerateRandomParameters(StoredProcedureModel sp)
    {
        var parameters = new DynamicParameters();

        foreach (var paramInfo in sp.Parameters)
        {
            object? randomValue = GenerateRandomValue(paramInfo);
            parameters.Add(paramInfo.Name, randomValue);
        }

        return parameters;
    }

    private object? GenerateRandomValue(ParameterMetadata paramInfo)
    {
        // IsNullable이 true인 경우, 10% 확률로 null 반환
        if (paramInfo.IsNullable && Random.Shared.Next(1, 11) == 1)
        {
            return null;
        }

        var rand = Random.Shared;
        
        return paramInfo.SqlTypeName.ToLower() switch
        {
            "int" => rand.Next(1, 100000),
            "bigint" => (long)rand.Next(1, 100000) * rand.Next(1, 1000),
            "varchar" or "nvarchar" or "char" or "nchar" => Guid.NewGuid().ToString("N").Substring(0, Math.Min(32, paramInfo.MaxLength > 0 ? paramInfo.MaxLength : 32)),
            "datetime" or "smalldatetime" or "datetime2" => DateTime.UtcNow.AddDays(-rand.Next(0, 365)).AddSeconds(rand.Next(-30000, 30000)),
            "date" => DateOnly.FromDateTime(DateTime.UtcNow.AddDays(-rand.Next(0, 365))),
            "decimal" or "numeric" or "money" => (decimal)(rand.NextDouble() * 10000),
            "float" => (float)(rand.NextDouble() * 10000),
            "bit" => rand.Next(0, 2) == 1,
            "uniqueidentifier" => Guid.NewGuid(),
            "tinyint" => (byte)rand.Next(0, 256),
            "smallint" => (short)rand.Next(-32768, 32767),
            _ => null // 지원하지 않는 타입은 null로 처리
        };
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
	, Caller = c.caller
	, ParameterId = m.parameter_id
	, ParameterName = m.name
	, TypeName = t.name
	, MaxLength = case when t.name in ('nvarchar', 'nchar') then m.max_length / 2 else m.max_length end
	, IsNullable = m.is_nullable
FROM	sys.procedures p
	LEFT OUTER JOIN sys.parameters m ON p.object_id = m.object_id
	LEFT OUTER JOIN sys.types t ON m.system_type_id = t.system_type_id and m.user_type_id = t.user_type_id
	LEFT OUTER JOIN sp_catalog c on p.name = c.sp_name
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
                    Caller = group.First().Caller, // 그룹 내 첫 번째 항목에서 가져옴 ≒ min(Caller)
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

            return new StoredProcedureList { Procedures = procList };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "An error occurred while loading stored procedure metadata.");

            return new StoredProcedureList(); // 예외 발생 시 빈 리스트 반환
        }
    }
}