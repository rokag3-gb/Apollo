using System.Data;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Data.SqlClient;
using Serilog;
using Serilog.Enrichers.CallerInfo;
using Apollo.Core;
using Apollo.Core.Helper;
using Apollo.Core.Credential;

namespace Apollo;

class Program
{
    static async Task Main(string[] args)
    {
        try
        {
            // ASCII Art 출력
            Console.WriteLine(new string('=', 34));
            Console.WriteLine(@"");
            Console.WriteLine(@"     db               8 8");
            Console.WriteLine(@"    dPYb   88b. .d8b. 8 8 .d8b.");
            Console.WriteLine(@"   dPwwYb  8  8 8' .8 8 8 8' .8");
            Console.WriteLine(@"  dP    Yb 88P' `Y8P' 8 8 `Y8P'");
            Console.WriteLine(@"           8");
            Console.WriteLine(@"");
            Console.WriteLine(new string('=', 34));

            // Serilog 설정
            // 최대 50MB * 최대 60개 파일 = 최대 3GB
            // logs 폴더의 용량이 최대 3GB 선에서 유지됨
            Log.Logger = new LoggerConfiguration()
                .MinimumLevel.Information()
                .Enrich.FromLogContext()
                .Enrich.WithCallerInfo(
                    includeFileInfo: true,
                    assemblyPrefix: "Apollo", // Apollo, Apollo.Core 전부 매칭
                    filePathDepth: 2 // SourceFile 경로를 뒤에서 2개 디렉토리만 남김
                )
                .WriteTo.Console(
                    outputTemplate: "{Timestamp:yyyy-MM-dd HH:mm:ss.fff} [{Level:u4}] [{SourceContext}] {Message:lj}{NewLine}{Exception}" // [{Namespace}.{Method}():{LineNumber}]
                )
                .WriteTo.File(
                    path: "logs/Apollo-.log",
                    rollingInterval: RollingInterval.Day,
                    rollOnFileSizeLimit: true,
                    outputTemplate: "{Timestamp:yyyy-MM-dd HH:mm:ss.fff} [{Level:u4}] [{SourceContext}] {Message:lj}{NewLine}{Exception}",
                    fileSizeLimitBytes: 50 * 1024 * 1024, // 50MB 초과하면 새 파일 생성.
                    retainedFileCountLimit: 60, // 매일 1개 로그 파일 생성. 즉 최대 60일간 보관. 실시간 삭제는 아니고, 새 로그 파일 생성 시 체크.
                    buffered: false // 권장: 즉시쓰기. 메모리 버퍼 최소화
                )
                .CreateLogger();

            // arguments 통해서 버전정보 출력
            if (args is not null && args.Length > 0)
            {
                if (args.Any(arg =>
                    arg == "-v" || arg == "-ver" || arg == "-version"
                    || arg == "-i" || arg == "-info"
                    || arg == "-h" || arg == "-help")
                    )
                {
                    try
                    {
                        Console.WriteLine(
                            //$"Title: {AssemblyInfo.Title}\n" +
                            $"Product: {AssemblyInfo.Product}\n" +
                            $"Version: {AssemblyInfo.HeadVer} ({AssemblyInfo.InformationVersion})\n" +
                            $"Description: {AssemblyInfo.Description}\n" +
                            $"Company: {AssemblyInfo.Company}\n" +
                            $"Manager: {AssemblyInfo.Manager}\n" +
                            $"{AssemblyInfo.Copyright}\n"
                        );
                        Console.WriteLine(new string('=', 54));
                        Console.WriteLine("");
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"버전 정보를 읽는 중 오류 발생: {ex.Message}");
                    }
                }
                else
                {
                    Console.WriteLine($"Unknown Parameter. - 사용 가능한 파라미터: -v, -ver, -version, -i, -info, -h, -help");
                }

                return; // 즉시 종료
            }

            // 호스트 빌더 설정
            var host = Host.CreateDefaultBuilder(args)
                .UseSerilog() // 모든 Logger<T>는 Serilog을 사용
                .ConfigureServices((hostContext, services) =>
                {
                    // DB Connection 등록 (Dapper)
                    services.AddTransient<IDbConnection>(c => new SqlConnection(SqlConnectionSecret.TradingDB));

                    services.AddHostedService<DbHammerService>();

                    services.AddSingleton<YamlConfigHelper>();
                    services.AddSingleton<NetInfoHelper>();

                    services.AddTransient<Core.Notification.LarkNotificationSender>();
                    services.AddTransient<Core.Notification.EmailNotificationSender>();
                    services.AddTransient<Core.Notification.SmsNotificationSender>();
                    services.AddSingleton<Core.Notification.INotificationSenderFactory, Core.Notification.NotificationSenderFactory>();
                    services.AddSingleton<Core.Notification.NotificationService>();
                })
                .Build();

            var logger = host.Services.GetRequiredService<ILogger<Program>>();
            logger.LogInformation($"Apollo {AssemblyInfo.HeadVer} Started! ({AssemblyInfo.InformationVersion})");

            // YAML 설정 파일 로드 -> new LoggerFactory()로 YamlConfigHelper을 직접 만들지 말고 DI에서 꺼내 쓰는 방식으로 변경
            var yamlConfigHelper = host.Services.GetRequiredService<YamlConfigHelper>();
            Conf.Current = yamlConfigHelper.Load();
            yamlConfigHelper = null;

            // NetInfo Snapshot 불러오기
            var netInfoHelper = host.Services.GetRequiredService<NetInfoHelper>();
            Conf.CurrentNetInfo = await netInfoHelper.SnapshotAsync();
            netInfoHelper = null;

            logger.LogInformation($"NET Info 불러오기 성공!");
            logger.LogInformation($"HostName = [{Conf.CurrentNetInfo.HostName}], Private IPv4 = [{Conf.CurrentNetInfo.PrivateIPv4}], Public IPv4 = [{Conf.CurrentNetInfo.PublicIPv4}], Private IPv6 = [{Conf.CurrentNetInfo.PrivateIPv6}]");

            await host.RunAsync();
        }
        catch (Exception ex)
        {
            Log.Fatal(ex, "Apollo 시작 중 오류가 발생했습니다.");
        }
        finally
        {
            Log.CloseAndFlush();
        }
    }
}