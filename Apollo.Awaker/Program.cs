using System.Diagnostics;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.DependencyInjection;
using Apollo.Awaker.Ipc;
using Apollo.Core;
using Apollo.Core.Helper;
using Apollo.Core.Ipc;
using Serilog;

namespace Apollo.Awaker;

class Program
{
    static async Task Main(string[] args)
    {
        // Serilog 설정
        // 최대 50MB * 최대 60개 파일 = 최대 3GB
        // logs 폴더의 용량이 최대 3GB 선에서 유지됨
        Log.Logger = new LoggerConfiguration()
            .MinimumLevel.Information()
            .Enrich.FromLogContext()
            .WriteTo.Console(
                outputTemplate: "{Timestamp:yyyy-MM-dd HH:mm:ss.fff} [{Level:u4}] [{SourceContext}] {Message:lj}{NewLine}{Exception}"
            )
            .WriteTo.File(
                path: "logs/AirBridge-.log",
                // path: $"logs/{DateTime.Now:yyyy-MM-dd}-AirBridge.Awaker.log",
                rollingInterval: RollingInterval.Day,
                rollOnFileSizeLimit: true,
                outputTemplate: "{Timestamp:yyyy-MM-dd HH:mm:ss.fff} [{Level:u4}] [{SourceContext}] {Message:lj}{NewLine}{Exception}",
                fileSizeLimitBytes: 50 * 1024 * 1024, // 50MB 초과하면 새 파일 생성.
                retainedFileCountLimit: 60, // 매일 1개 로그 파일 생성. 즉 최대 60일간 보관. 실시간 삭제는 아니고, 새 로그 파일 생성 시 체크.
                buffered: false // 권장: 즉시쓰기. 메모리 버퍼 최소화
            )
            .CreateLogger();

        try
        {
            // 호스트 빌더 설정
            var host = Host.CreateDefaultBuilder(args)
                .UseSerilog() // 모든 Logger<T>는 Serilog을 사용
                .ConfigureServices(services =>
                {
                    services.AddSingleton<YamlConfigHelper>();
                    services.AddSingleton<NetInfoHelper>();
                    services.AddSingleton<INamedPipeClient, NamedPipeClient>();

                    services.AddHostedService<WakeUpService>();
                })
                .Build();

            // Microsoft.Extensions.Logging 방식으로 변경
            var logger = host.Services.GetRequiredService<ILogger<Program>>();

            // 종료 시그널 핸들러 등록
            Console.CancelKeyPress += (sender, e) =>
            {
                e.Cancel = true; // 기본 종료 동작 취소

                logger.LogInformation($"Ctrl+C 신호를 받았습니다. 프로그램을 안전하게 종료합니다.");

                Environment.Exit(0); // 강제 종료
            };

            // 프로세스 종료 이벤트 등록
            AppDomain.CurrentDomain.ProcessExit += (sender, e) =>
            {
                logger.LogInformation($"프로그램 종료 신호를 받았습니다.");

                // AirBridge 프로세스도 함께 종료
                KillAirBridgeProcess(logger);
            };

            try
            {
                logger.LogInformation($"AirBridge.Awaker {AssemblyInfo.HeadVer} Started! ({AssemblyInfo.InformationVersion})");

                // YAML 설정 파일 로드 -> new LoggerFactory()로 YamlConfigHelper을 직접 만들지 말고 DI에서 꺼내 쓰는 방식으로 변경
                var yamlConfigHelper = host.Services.GetRequiredService<YamlConfigHelper>();
                Conf.Current = yamlConfigHelper.Load();
                yamlConfigHelper = null; // 명시적 메모리 해제

                // NetInfo Snapshot 불러오기
                var netInfoHelper = host.Services.GetRequiredService<NetInfoHelper>();
                Conf.CurrentNetInfo = await netInfoHelper.SnapshotAsync();

                logger.LogInformation($"NET Info 불러오기 성공!");
                logger.LogInformation($"HostName = [{Conf.CurrentNetInfo.HostName}], Private IPv4 = [{Conf.CurrentNetInfo.PrivateIPv4}], Public IPv4 = [{Conf.CurrentNetInfo.PublicIPv4}], Private IPv6 = [{Conf.CurrentNetInfo.PrivateIPv6}]");

                await host.RunAsync();
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "AirBridge.Awaker 실행 중 오류가 발생했습니다.");
            }
        }
        catch (Exception ex)
        {
            Log.Fatal(ex, "AirBridge.Awaker 시작 중 오류가 발생했습니다.");
        }
        finally
        {
            Log.CloseAndFlush();
        }
    }

    private static void KillAirBridgeProcess(ILogger<Program> logger)
    {
        try
        {
            var processes = Process.GetProcessesByName("AirBridge");

            foreach (var process in processes)
            {
                try
                {
                    if (!process.HasExited)
                    {
                        logger.LogInformation($"AirBridge 프로세스 종료 중... (PID: {process.Id})");

                        process.Kill(); // AirBridge 프로세스 종료

                        process.WaitForExit(TimeSpan.FromSeconds(4)); // 4초 대기

                        logger.LogInformation($"AirBridge 프로세스 종료 완료 (PID: {process.Id})");
                    }
                }
                catch (Exception ex)
                {
                    logger.LogError(ex, $"프로세스 종료 중 예외 발생 (PID: {process.Id}): {ex.Message}");
                }
            }
        }
        catch (Exception ex)
        {
            logger.LogError(ex, $"AirBridge 프로세스 종료 중 오류: {ex.Message}");
        }
    }
}