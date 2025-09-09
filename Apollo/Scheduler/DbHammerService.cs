using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace Apollo.Scheduler
{
    public class DbHammerService : BackgroundService
    {
        private readonly ILogger<DbHammerService> _logger;
        private readonly IServiceProvider _serviceProvider;
        private readonly int _workerCount = 100; // 동시에 실행할 워커(스레드) 수

        public DbHammerService(ILogger<DbHammerService> logger, IServiceProvider serviceProvider)
        {
            _logger = logger;
            _serviceProvider = serviceProvider;
        }

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            _logger.LogInformation("DbHammerService is starting with {WorkerCount} workers.", _workerCount);

            var workerTasks = new List<Task>();
            for (int i = 0; i < _workerCount; i++)
            {
                // 각 워커에 고유 ID를 부여하여 로그 추적을 용이하게 합니다.
                workerTasks.Add(RunWorkerAsync(i + 1, stoppingToken));
            }

            await Task.WhenAll(workerTasks);

            _logger.LogInformation("DbHammerService has stopped.");
        }

        private async Task RunWorkerAsync(int workerId, CancellationToken stoppingToken)
        {
            _logger.LogInformation("Worker {WorkerId} is starting.", workerId);

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

            _logger.LogInformation("Worker {WorkerId} is stopping.", workerId);
        }
    }
}
