using System.Diagnostics;
using Microsoft.Extensions.Hosting;
using Apollo.Core;
using Apollo.Core.Ipc;
using Apollo.Core.Dto;

namespace Apollo.Awaker.Ipc;

public class WakeUpService : BackgroundService
{
    private readonly ILogger<WakeUpService> _logger;
    private readonly INamedPipeClient _namedPipeClient;
    private readonly string _processName = "AirBridge";
    private readonly string _executePath;
    private readonly bool _isAot;
    private readonly TimeSpan _pingIntervalMinutes = TimeSpan.FromMinutes(Conf.Current.awaker.ping_interval_min);
    private string _seperatedLine = new string('=', 30);

    public WakeUpService(ILogger<WakeUpService> logger, INamedPipeClient namedPipeClient)
    {
        _logger = logger;
        _namedPipeClient = namedPipeClient;

        var (path, isAot) = FindExecutablePath();
        _executePath = path;
        _isAot = isAot;

        _logger.LogInformation($"File.Exists(_executePath) = {File.Exists(_executePath)}, isAot = {_isAot}, _executePath: {_executePath}");
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation($"WakeUpService started. - ({_pingIntervalMinutes.Seconds / 60d}분 간격으로 AirBridge (NamedPipeServer) 에게 ping 전송)");

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await CheckHealth();
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "AirBridge 모니터링 중 오류가 발생했습니다.");
            }
            finally
            {
                await Task.Delay(_pingIntervalMinutes, stoppingToken); // _pingIntervalMinutes 만큼 대기
            }
        }

        _logger.LogInformation("WakeUpService stopped.");
    }

    public override async Task StopAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("WakeUpService 종료 신호를 받았습니다.");

        try
        {
            // AirBridge 프로세스 종료는 진입점(Program.cs)에서 처리할 것
            // Kill();

            // 사실상 StopAsync() 는 아무 역할 없는 상태임

            // 잠시 대기하여 프로세스가 완전히 종료되도록 함
            await Task.Delay(TimeSpan.FromSeconds(1), cancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "WakeUpService 종료 중 오류가 발생했습니다.");
        }

        await base.StopAsync(cancellationToken);
    }

    private async Task CheckHealth()
    {
        try
        {
            _logger.LogInformation($"{_seperatedLine}");
            _logger.LogInformation("AirBridge 상태 확인 중...");

            var pingRequest = new PingRequest(DateTime.UtcNow);

            // 타임아웃을 설정하여 ping 요청
            var pongResponse = await _namedPipeClient.SendPingAsync(pingRequest);

            if (pongResponse?.Alive is true)
            {
                _logger.LogInformation($"AirBridge가 정상 동작 중입니다. 상태: \"{pongResponse.Status}\"");
            }
            else
            {
                _logger.LogWarning("AirBridge로부터 응답이 없습니다. 재시작을 시도합니다.");

                await Restart();
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "AirBridge 상태 확인 중 오류가 발생했습니다.");

            await Restart();
        }
        finally
        {
            _logger.LogInformation($"{_seperatedLine}");
        }
    }

    private async Task Restart()
    {
        try
        {
            _logger.LogWarning("AirBridge 재시작을 시작합니다.");

            // 기존 AirBridge 프로세스 종료
            var existingProcesses = Process.GetProcessesByName(_processName);

            foreach (var process in existingProcesses)
            {
                try
                {
                    if (!process.HasExited)
                    {
                        _logger.LogInformation($"기존 AirBridge 프로세스 종료 중... (PID: {process.Id})");

                        process.Kill();

                        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));

                        await process.WaitForExitAsync(cts.Token);

                        _logger.LogInformation($"기존 AirBridge 프로세스 종료 및 대기 완료 (PID: {process.Id})");
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, $"프로세스 종료 중 예외 발생 (PID: {process.Id})");
                }
            }

            // 잠시 대기 (2초)
            await Task.Delay(TimeSpan.FromSeconds(2));

            // AirBridge 재시작
            if (File.Exists(_executePath))
            {
                var startInfo = new ProcessStartInfo();

                if (_isAot)
                {
                    startInfo.FileName = _executePath;
                }
                else
                {
                    startInfo.FileName = "dotnet";
                    startInfo.Arguments = _executePath;
                }

                startInfo.UseShellExecute = false;
                startInfo.CreateNoWindow = true;
                startInfo.WorkingDirectory = Path.GetDirectoryName(_executePath);

                var process = Process.Start(startInfo);

                // 재시작 후 잠시 대기 (1초)
                await Task.Delay(TimeSpan.FromSeconds(1));

                if (process is not null)
                {
                    _logger.LogInformation($"AirBridge가 재시작되었습니다. (PID: {process.Id})");

                    // 재시작 후 잠시 대기 (1초)
                    await Task.Delay(TimeSpan.FromSeconds(1));
                }
                else
                {
                    _logger.LogError("AirBridge 재시작 실패.");
                }
            }
            else
            {
                _logger.LogError($"AirBridge 실행 파일을 찾을 수 없습니다: {_executePath}");
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "AirBridge 재시작 중 오류가 발생했습니다.");
        }
    }

    private (string path, bool isAot) FindExecutablePath()
    {
        var baseDir = AppDomain.CurrentDomain.BaseDirectory;
        var debugDir = AppDomain.CurrentDomain.BaseDirectory.Replace("AirBridge.Awaker", "AirBridge");
        // 로컬 Debug 환경에서는 "C:\source\AirBridge\AirBridge.Awaker\bin\Debug\net8.0" 에서 실행되고 있는 "AirBridge.Awaker.exe"가
        // "C:\source\AirBridge\AirBridge\bin\Debug\net8.0" 에 존재하는 "AirBridge.exe"를 찾아서 실행시켜야 함.

        // var debugDir = Path.Combine(baseDir, "..", "..", "AirBridge", "bin", "Debug", "net8.0");

        // PRD환경 먼저, DEV환경 나중에
        var searchDirs = new[] { baseDir, debugDir };
        var fileNames = new[] {
            "AirBridge", // AOT binary
            "AirBridge.dll", // JIT binary
            "AirBridge.exe" // JIT binary
        };
        
        foreach (var dir in searchDirs)
        {
            foreach (var name in fileNames)
            {
                var path = Path.Combine(dir, name);

                if (File.Exists(path))
                {
                    var isAot = !path.EndsWith(".dll") && !path.EndsWith(".exe"); // AOT binary는 확장자(.dll, .exe 등) 가 없음

                    return (path, isAot);
                }
            }
        }
        
        _logger.LogWarning("AirBridge 실행 파일을 찾을 수 없습니다.");

        return (string.Empty, false);
    }
}