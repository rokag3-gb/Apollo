using System.Diagnostics;
using System.Threading;
using Microsoft.Extensions.Hosting;
using Newtonsoft.Json;
using Apollo.Core;
using Apollo.Core.Model;
using Apollo.Core.Notification;
using Apollo.Core.Sftp;
using Cronos;

namespace Apollo.Scheduler;

public class CronPollingService : BackgroundService
{
    private readonly ILogger<CronPollingService> _logger;
    private readonly IFileService _fileService;
    private readonly NotificationService _notifier;
    private List<CronExpression> _cronExpressions;
    private TimeZoneInfo _timeZone;
    private readonly string _instanceId = Guid.NewGuid().ToString().Substring(36 - 12, 12); // instanceId가 uuid 면 length = 36으로 너무 길어서 의도적으로 우측 끝 12자리로 한정
    private static readonly SemaphoreSlim _semaphore = new SemaphoreSlim(1, 1); // 동시 실행을 제어하기 위한 SemaphoreSlim 추가

    public CronPollingService(ILogger<CronPollingService> logger, IFileService fileService, NotificationService notifier)
    {
        _logger = logger;
        _fileService = fileService;
        _notifier = notifier;

        _logger.LogInformation($"CronPollingService ctor: InstanceId={_instanceId}, PID={Process.GetCurrentProcess().Id}, TID={Environment.CurrentManagedThreadId}");

        _cronExpressions = new List<CronExpression>();

        // Cronos 5 field expression (분 시 일 월 요일)
        // 매 5분마다
        //_cronExpressions.Add(CronExpression.Parse("*/5 * * * *"));

        // Cronos - 6 field expression (초 분 시 일 월 요일)
        // "*/10 * * * * *" -> 매 10초마다
        // "0 0 1 * * *" -> 매일 KST 10시마다 (UTC 1시)
        // "0 0 21,23 * * *" -> 매일 KST 6시, 8시마다 (UTC 21시, 23시)
        // "0 30 20-23 * * *" -> 매일 KST 5시~8시 사이 매 정각 30분마다 (UTC 20시~23시)
        //_cronExpressions.Add(CronExpression.Parse("*/5 * * * * *", CronFormat.IncludeSeconds));

        // Conf.Current 을 _cronExpressions 으로 변환
        Conf.Current.schedule.cron_expression.ForEach(expr =>
        {
            if (CronExpression.TryParse(expr, CronFormat.IncludeSeconds, out var parsedCron))
                _cronExpressions.Add(parsedCron);
            else
                _logger.LogWarning($"Invalid cron expression: {expr}. Using default cron expression.");
        });

        //_timeZone = TimeZoneInfo.FindSystemTimeZoneById("Asia/Seoul"); // KST (Korea Standard Time)
        _timeZone = TimeZoneInfo.FindSystemTimeZoneById(Conf.Current.schedule.time_zone) ?? TimeZoneInfo.Local;

        // _cronExpression = "0,5,10,15,20,25,30,35,40,45,50,55 * * * * *"
        
        var cronExpressionCsv = string.Join(", ", _cronExpressions.Select(expr => $"[{expr}]"));

        // TimeZoneInfo.FindSystemTimeZoneById(Conf.Current.schedule.time_zone)
        // _timeZone.Id = "Asia/Seoul"
        // _timeZone.DisplayName = "(UTC+09:00) 서울"

        // TimeZoneInfo.Local
        // _timeZone.Id = "Korea Standard Time"
        // _timeZone.DisplayName = "(UTC+09:00) 서울"
        _logger.LogInformation($"Cron expression: {cronExpressionCsv}, time zone id: {_timeZone.Id}, time zone name: {_timeZone.DisplayName}");
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("CronPollingService started");

        string strLastExecDate = string.Empty;

        while (!stoppingToken.IsCancellationRequested)
        {
            var nextExecutionTimes = _cronExpressions
                .Select(expr => expr.GetNextOccurrence(DateTimeOffset.UtcNow, _timeZone, false))
                .Where(time => time.HasValue)
                .Select(time => time!.Value)
                .OrderBy(time => time)
                .ToList();

            if (nextExecutionTimes.Any())
            {
                // 바로 실행하면 loop가 과열될 수 있기 때문에 의도적으로 짧은 backoff delay (0.2초) 설정
                await Task.Delay(200, stoppingToken);

                var nextUtc = nextExecutionTimes.First();
                var delay = nextUtc - DateTimeOffset.UtcNow;
                //_logger.LogInformation($"Next runtime (Local): {TimeZoneInfo.ConvertTime(nextUtc, _timeZone)}");

                if (delay.TotalMilliseconds > 0)
                    await Task.Delay(delay, stoppingToken);

                // 세마포어를 즉시 확보할 수 있는지 확인합니다.
                // 0ms를 기다리므로, 즉시 확보할 수 없으면 false를 반환합니다.
                if (!await _semaphore.WaitAsync(0, stoppingToken))
                {
                    _logger.LogWarning("Skipped: Previous run still active running.");
                    continue; // 락을 얻지 못하면 이번 실행은 건너뜁니다.
                }

                try
                {
                    _logger.LogInformation($"Active Running: InstanceId={_instanceId}, PID={Process.GetCurrentProcess().Id}, TID={Environment.CurrentManagedThreadId}");

                    if (_fileService is not null)
                    {
                        // CleanUp 작동은 최초 실행이거나, 최종실행 날짜와 다른 날짜인 경우에만 진입. (= 하루에 한번만 작동시키기 위함)
                        if (string.IsNullOrEmpty(strLastExecDate) || strLastExecDate != DateTime.Now.ToString("yyyyMMdd"))
                        {
                            // {archive_path} 디렉토리 하위에 보관일수(retentionDays) 90일을 초과한 모든 파일 삭제
                            _fileService.CleanUpExpiredArchivedFiles(90);

                            // logs/ 디렉토리 하위에 *.log 중 보관일수(retentionDays) 90일을 초과한 모든 파일 삭제
                            _fileService.CleanUpExpiredLogFiles(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "logs"), 90);
                        }

                        await _fileService.TransferAllFiles();

                        strLastExecDate = DateTime.Now.ToString("yyyyMMdd");
                    }

                    /**************************************************************************/

                    #region Azure Blob(SFTP) test
                    /* Azure Blob(SFTP) test */

                    // AzureBlobSftpConfig? config = Conf.Current.target.azure_blob_sftp ?? Conf.Current.source.azure_blob_sftp;

                    // if (config is null)
                    //     throw new InvalidOperationException("AzureBlobSftpConfig is null. Please check your configuration.");

                    // _blob = new AzureBlobService(config);

                    // 1) Blob 목록 가져오기
                    //List<AzureBlob> blobList = await _blob.GetBlobList(".");
                    //Console.WriteLine(JsonConvert.SerializeObject(blobList, Formatting.Indented));

                    // 2) 특정 Blob 정보 가져오기
                    //AzureBlob single = await _blob.GetBlob("/ledger-root/20250723185600_NXT_IF_Derivatives");
                    //AzureBlob single = await _blob.GetBlob("/ledger-root/test-folder/NXT_IF_Derivatives");
                    //Console.WriteLine(JsonConvert.SerializeObject(single, Formatting.Indented));
                    //_logger.LogInformation($"single = {JsonConvert.SerializeObject(single, Formatting.None)}");

                    // 3) Blob 다운로드 (overwrite)
                    //await _blob.DownloadFile("/ledger-root/20250723185600_NXT_IF_Derivatives", "C:\\source\\test_20250723185600_NXT_IF_Derivatives");

                    // 4) Blob 업로드 (overwrite)
                    //await _blob.UploadFile("C:\\source\\test_20250723185600_NXT_IF_Derivatives", "/ledger-root/test-folder/NXT_IF_Derivatives");

                    // 5) Blob 디렉토리 생성
                    //await _blob.MkDir("/ledger-root/test-folder2");

                    // 6) Blob 디렉토리 삭제
                    //await _blob.RemoveDir("/ledger-root/test-folder2!!");

                    // 7) Blob 디렉토리 네임 변경
                    //await _blob.RenameDir("/ledger-root/test-folder2!!", "/ledger-root/test-folder2");
                    #endregion
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "An error occurred during the scheduled job.");
                }
                finally
                {
                    // 작업이 성공하든 실패하든 반드시 세마포어를 해제합니다.
                    _semaphore.Release();
                }
            }

            //_logger.LogInformation($"polling completed.");
        }

        _logger.LogInformation("CronPollingService stopped.");
    }
}