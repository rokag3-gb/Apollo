using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;
using YamlDotNet.RepresentationModel;
using Apollo.Core.Model;
using Apollo.Core.Credential;

namespace Apollo.Core.Helper;

public class YamlConfigHelper
{
    private readonly ILogger<YamlConfigHelper> _logger;

    public YamlConfigHelper(ILogger<YamlConfigHelper> logger)
    {
        _logger = logger;
    }

    public AppConfig Load()
    {
        AppConfig appConfig = new AppConfig();

        //var yamlFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", "AirBridge.Core", "AirBridgeConfig.yaml");
        var yamlFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "AirBridgeConfig.yaml");

        //_logger.LogInformation($"AppDomain.CurrentDomain.BaseDirectory = {AppDomain.CurrentDomain.BaseDirectory}"); // = "C:\source\AirBridge\AirBridge\bin\Debug\net8.0\"
        //_logger.LogInformation($"AppDomain.CurrentDomain.DynamicDirectory = {AppDomain.CurrentDomain.DynamicDirectory}"); // = null
        //_logger.LogInformation($"yamlFilePath = {yamlFilePath}"); // = "C:\source\AirBridge\AirBridge\bin\Debug\net8.0\AirBridgeConfig.yaml"

        if (!File.Exists(yamlFilePath)) // 파일이 없으면 모두 default 값으로 AppConfig 인스턴스화
        {
            try
            {
                appConfig = new AppConfig()
                {
                    schedule = new ScheduleSection
                    {
                        cron_expression = new List<string> {
                            // 초 분 시 일 월 요일
                            // "0/30 * 4-19 * * *", // 새벽4시 ~ 오후7시 사이 매 30초 마다
                            // "* 0/1 * * * *", // 매 1분 마다 (PRD)
                            "*/10 * * * * *", // 매 10초 마다 (DEV/TEST)
                        },
                        time_zone = TimeZoneInfo.Local.Id // 로컬시간 (OS kernel 시간대)
                    },
                    source = new SourceSection
                    {
                        type = ConnectType.mounted_path,
                        mounted_path = new MountedPathConfig
                        {
                            path = "/opt/airbridge/ledger/", // 원본 경로
                            archive_path = "/opt/airbridge/archive/", // 처리 후 보관 경로
                        }
                    },
                    target = new TargetSection
                    {
                        type = ConnectType.azure_blob_sftp,
                        azure_blob_sftp = new AzureBlobSftpConfig
                        {
                            host = AzureBlobSecret.Host,
                            port = AzureBlobSecret.Port,
                            username = AzureBlobSecret.Username,
                            password = AzureBlobSecret.Password, // default는 AzureBlobSecret 안에 비밀번호 사용
                        }
                    },
                    notification = new NotificationSection
                    {
                        type = NotificationType.Lark_Webhook,
                        lark_webhook = new LarkWebhookConfig
                        {
                            webhook_url = LarkSecret.WebhookUrl,
                            secret_token = LarkSecret.SecretToken
                        },
                        enabled = true, // 알림 기능 사용 여부
                    },
                    awaker = new AwakerSection
                    {
                        ping_interval_min = 0.5 // 30초
                    }
                };

                // appConfig를 YAML 파일로 저장하기 위해 직렬화. 모든 프로퍼티를 snake_case로 설정 (UnderscoredNamingConvention.Instance)
                var serializer = new StaticSerializerBuilder(new AppConfigYamlContext())
                    .WithNamingConvention(UnderscoredNamingConvention.Instance)
                    .Build();

                var yamlContent = serializer.Serialize(appConfig);

                // 디렉토리가 존재하지 않으면 생성
                var directory = Path.GetDirectoryName(yamlFilePath);
                if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
                {
                    Directory.CreateDirectory(directory);
                }

                File.WriteAllText(yamlFilePath, yamlContent);
                _logger.LogInformation($"기본 설정으로 YAML 파일을 생성했습니다: {yamlFilePath}");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "YAML 파일 생성 중 오류 발생");
                throw;
            }
        }
        else if (File.Exists(yamlFilePath)) // AirBridgeConfig.yaml 파일이 존재하면 해당 파일 로드
        {
            try
            {
                // YAML 파일을 읽어 AppConfig 객체로 변환
                // var yaml = File.ReadAllText(yamlFilePath);
                using var fs = File.OpenRead(yamlFilePath);
                using var sr = new StreamReader(fs, detectEncodingFromByteOrderMarks: true);
                var yaml = sr.ReadToEnd();

                _logger.LogInformation($"YAML text 불러오기 정상");

                var stream = new YamlStream();
                using var reader = new StringReader(yaml);
                stream.Load(reader); // 문법 에러면 여기서 터짐

                _logger.LogInformation($"YAML syntax 정상");

                // YAML 파일에서 읽어온 string을 역직렬화. 모든 프로퍼티를 snake_case로 설정 (UnderscoredNamingConvention.Instance)
                var deserializer = new StaticDeserializerBuilder(new AppConfigYamlContext())
                    .WithNamingConvention(UnderscoredNamingConvention.Instance)
                    .Build();

                // 디버깅을 위하여 AppConfig의 실제 타입 출력
                //_logger.LogDebug($"사용하는 AppConfig 타입: {typeof(AppConfig).FullName}");

                appConfig = deserializer.Deserialize<AppConfig>(yaml);
            }
            catch (YamlDotNet.Core.YamlException ex)
            {
                _logger.LogError(ex, $"YAML 문법 오류: {ex.Message}");
                throw;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"YAML 문법 오류: {ex.Message}");
                throw;
            }
        }

        return appConfig;
    }
}