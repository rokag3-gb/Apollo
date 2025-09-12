using Apollo.Core;
using Apollo.Core.Model;
using Dapper;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Newtonsoft.Json;
using System.Data;
using System.Security.Cryptography;

namespace Apollo;

public class DbHammerService : BackgroundService
{
    private readonly ILogger<DbHammerService> _logger;
    private readonly IServiceProvider _serviceProvider;
    
    private StoredProcedureList _spList = new();
    private List<StoredProcedureModel> _spListUser = new();
    private List<StoredProcedureModel> _spListAdmin = new();
    private List<StoredProcedureModel> _spListBatch = new();

    private readonly int _workerCount = Conf.Current.worker.count; // 동시에 실행할 워커(스레드) 수

    public DbHammerService(ILogger<DbHammerService> logger, IServiceProvider serviceProvider)
    {
        _logger = logger;
        _serviceProvider = serviceProvider;
    }
    
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation($"DbHammerService is starting with {_workerCount} workers.");

        try
        {
            _logger.LogInformation("Starting in 5 seconds... (Press Ctrl+C to cancel)");

            for (int i = 5; i > 0; i--)
            {
                _logger.LogInformation($"{i}...");

                await Task.Delay(1000, stoppingToken);
            }

            _logger.LogInformation("Starting now!");
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Countdown was cancelled.");
            return;
        }

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

        _logger.LogInformation($"SP 총 갯수: {_spList.Procedures.Count}, filtered by caller: User {_spListUser.Count}, Admin {_spListAdmin.Count}, Batch {_spListBatch.Count}");

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
        var wId = workerId.ToString().PadLeft(3, '0');

        _logger.LogInformation($"Worker: {wId} is starting.");

        string tId = string.Empty;

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                // TransactionId 초기화 및 발번. (용도 = 추척용)
                tId = string.Empty;
                tId = Guid.NewGuid().ToString().Substring(36 - 4, 4); // Guid는 length = 36으로 너무 길어서 의도적으로 우측 끝 4자리로 한정

                // 가중치에 따라 랜덤으로 실행할 SP 선택 -> Weight ratio per Caller (User:Batch:Admin = 7:2:1)
                var spToRun = SelectRandomSpWeighted();

                if (spToRun is null)
                {
                    _logger.LogWarning($"Worker: {wId}, 실행시킬 stored procedure를 랜덤 추출하지 못했습니다. 재시도 중...");

                    await Task.Delay(TimeSpan.FromSeconds(1), stoppingToken); // 잠시 후 재시도

                    continue;
                }

                // 선택된 SP의 메타데이터를 기반으로 랜덤 파라미터 생성
                var parameters = GenerateRandomParameters(spToRun);

                // DB 연결 가져오기
                using var scope = _serviceProvider.CreateScope();
                var connection = scope.ServiceProvider.GetRequiredService<IDbConnection>();

                // Dapper.DynamicParameters to Dict.
                var dictParams = parameters.ParameterNames.ToDictionary(
                    name => name,
                    name => parameters.Get<object>(name)
                    );

                _logger.LogInformation($"Worker: {wId}, TId: {tId}, Proc: {spToRun.Name} 실행 준비 - Params: {JsonConvert.SerializeObject(dictParams)}");

                // Dapper로 SP 실행
                await connection.ExecuteAsync(
                    sql: spToRun.Name,
                    param: parameters,
                    commandType: CommandType.StoredProcedure,
                    commandTimeout: 30 // 30초
                    );

                _logger.LogInformation($"Worker: {wId}, TId: {tId}, Proc: {spToRun.Name} 실행 완료!");

                // 임의의 지연 시간
                await Task.Delay(TimeSpan.FromSeconds(0.8), stoppingToken);
            }
            catch (OperationCanceledException)
            {
                // 서비스가 중지될 때 발생하는 예외는 정상 동작임
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Worker: {wId}, TId: {tId}, An error occurred! - {ex.Message}");
                
                // 오류 발생 시, 시스템에 과도한 부하를 주지 않기 위해 잠시 대기 후 다음 작업을 시도합니다.
                await Task.Delay(TimeSpan.FromSeconds(0.8), stoppingToken);
            }
        }

        _logger.LogInformation($"Worker: {wId} is graceful termination completed.");
    }

    private StoredProcedureModel? SelectRandomSpWeighted()
    {
        var rand = Random.Shared;
        int roll = rand.Next(1, 11); // 1부터 10까지의 난수 생성

        // User:Batch:Admin = 7:2:1 비율에 따라 리스트 선택
        if (roll <= 7 && _spListUser.Count > 0) // 1-7 (70% 확률)
            return _spListUser[rand.Next(_spListUser.Count)];

        if (roll <= 9 && _spListBatch.Count > 0) // 8-9 (20% 확률)
            return _spListBatch[rand.Next(_spListBatch.Count)];

        if (roll <= 10 && _spListAdmin.Count > 0) // 10 (10% 확률)
            return _spListAdmin[rand.Next(_spListAdmin.Count)];

        // 특정 Caller 타입의 SP가 없는 경우, 또는 가중치 롤에 실패한 경우 전체 리스트에서 랜덤으로 선택 (Fallback)
        if (_spList.Procedures != null && _spList.Procedures.Count > 0)
            return _spList.Procedures[rand.Next(_spList.Procedures.Count)];
        
        return null; // 실행할 SP가 하나도 없는 경우
    }

    private DynamicParameters GenerateRandomParameters(StoredProcedureModel sp)
    {
        var parameters = new DynamicParameters();

        // 파라미터가 없는 SP인 경우 빈 파라미터 반환
        if (sp.Parameters is null || sp.Parameters.Count == 0)
            return parameters;

        foreach (var paramInfo in sp.Parameters)
        {
            object? randomValue = GenerateRandomValue(paramInfo);

            // [유형 4] 해결: randomValue가 null이고, DB에서도 null을 허용하지 않는 파라미터인 경우, 타입에 따른 기본값을 할당하여 "parameter was not supplied" 오류 방지
            if (randomValue is null && !paramInfo.IsNullable)
            {
                randomValue = paramInfo.SqlTypeName.ToLower() switch
                {
                    "int" or "bigint" or "decimal" or "numeric" or "money" or "float" or "tinyint" or "smallint" => 0,
                    "varchar" or "nvarchar" or "char" or "nchar" => string.Empty,
                    "datetime" or "smalldatetime" or "datetime2" or "date" => DateTime.UtcNow,
                    "bit" => false,
                    "uniqueidentifier" => Guid.Empty,
                    _ => null // 그 외에는 어쩔 수 없이 null 유지
                };
            }

            parameters.Add(paramInfo.Name, randomValue);
        }

        return parameters;
    }

    private object? GenerateRandomValue(ParameterMetadata paramInfo)
    {
        var rand = Random.Shared;

        // [유형 3] 해결: 특정 파라미터 이름에 대해서는 null 허용 예외 처리
        bool isPagingParam = paramInfo.Name.Contains("TopN", StringComparison.OrdinalIgnoreCase) ||
                             paramInfo.Name.Contains("PageSize", StringComparison.OrdinalIgnoreCase) ||
                             paramInfo.Name.Contains("PageNumber", StringComparison.OrdinalIgnoreCase);

        // IsNullable이 true이고, 페이징 관련 파라미터가 아닌 경우 10% 확률로 null 반환
        if (paramInfo.IsNullable && !isPagingParam && paramInfo.Name != "@AccountID" && rand.Next(1, 11) == 1)
        {
            return null;
        }
        
        return paramInfo.SqlTypeName.ToLower() switch
        {
            "int" => rand.Next(1, 100000),
            "bigint" => (long)rand.Next(1, 100000) * rand.Next(1, 1000),
            // [유형 3] 해결: MaxLength가 0보다 클 때만 Substring을 적용하고, 최대 길이를 초과하지 않도록 보완
            "varchar" or "nvarchar" or "char" or "nchar" => paramInfo.MaxLength > 0
                ? Guid.NewGuid().ToString("N")[..Math.Min(32, paramInfo.MaxLength)]
                : Guid.NewGuid().ToString("N"),
            "datetime" or "smalldatetime" or "datetime2" => DateTime.UtcNow.AddDays(-rand.Next(0, 365)).AddSeconds(rand.Next(-30000, 30000)),
            // [유형 1] 해결: DateOnly 대신 DateTime 반환
            "date" => DateTime.UtcNow.AddDays(-rand.Next(0, 365)).Date,
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