using YamlDotNet.Serialization;

namespace Apollo.Core.Model;

public class AppConfig
{
    public ScheduleSection schedule { get; set; } = new();
    public SourceSection source { get; set; } = new();
    public TargetSection target { get; set; } = new();
    public NotificationSection notification { get; set; } = new();
    public AwakerSection awaker { get; set; } = new();
}

public class ScheduleSection
{
    public List<string> cron_expression { get; set; } = new();
    public string time_zone { get; set; } = "Asia/Seoul"; // 기본값은 로컬 시간대
}

public enum ConnectType
{
    mounted_path, // 로컬 파일 시스템 또는 네트워크 드라이브
    azure_blob_sftp, // Azure Blob SFTP 방식
    azure_blob_sas // Azure Blob SAS(Shared Access Signature) token 방식
}

public enum NotificationType
{
    Lark_Webhook, // Lark Webhook
    Email,
    Sms
}

public class SourceSection
{
    public ConnectType type { get; set; } = ConnectType.mounted_path;

    [YamlMember(DefaultValuesHandling = DefaultValuesHandling.OmitNull)] // null이면 YAML에서 제외
    public MountedPathConfig? mounted_path { get; set; }

    [YamlMember(DefaultValuesHandling = DefaultValuesHandling.OmitNull)]
    public AzureBlobSftpConfig? azure_blob_sftp { get; set; }

    [YamlMember(DefaultValuesHandling = DefaultValuesHandling.OmitNull)]
    public AzureBlobSasConfig? azure_blob_sas { get; set; }
}

public class TargetSection
{
    public ConnectType type { get; set; } = ConnectType.azure_blob_sftp;
    
    [YamlMember(DefaultValuesHandling = DefaultValuesHandling.OmitNull)]
    public MountedPathConfig? mounted_path { get; set; }
    
    [YamlMember(DefaultValuesHandling = DefaultValuesHandling.OmitNull)]
    public AzureBlobSftpConfig? azure_blob_sftp { get; set; }
    
    [YamlMember(DefaultValuesHandling = DefaultValuesHandling.OmitNull)]
    public AzureBlobSasConfig? azure_blob_sas { get; set; }
}

public class MountedPathConfig
{
    public string path { get; set; } = ""; // 기본 path
    public string archive_path { get; set; } = ""; // 처리 완료한 파일을 이동시킬 path
}

public class AzureBlobSftpConfig
{
    public string host { get; set; } = "";
    public int port { get; set; }
    public string username { get; set; } = "";
    public string? password { get; set; } = ""; // 또는 private key
    public string? private_key_path { get; set; } = ""; // "C:/path/to/your/private_key.pem"
    // public bool sftp_auto_on_off { get; set; } = true; // SFTP 접속 후 작업이 끝나면 자동으로 SFTP 서버를 끄고, 작업 시작 전에 자동으로 켜는 기능 (Azure VM에서 SFTP 서버를 운영할 때 유용)
}

public class AzureBlobSasConfig
{
    public string account_name { get; set; } = ""; // "mystorageaccount"
    public string container_name { get; set; } = ""; // "mycontainer"
    public string sas_token { get; set; } = ""; // "sp=racwdlmeop&st=2025-07-30T01:40:20Z&se=2025-12-31T14:59:59Z&spr=https&sv=2024-11-04&sr=c&sig=1bxptQjisc%2BAfG10elQqr%2BBuWgckKb0NG7G9aE4x1QQ%3D"
}

public class NotificationSection
{
    public NotificationType type { get; set; } = NotificationType.Lark_Webhook;

    [YamlMember(DefaultValuesHandling = DefaultValuesHandling.OmitNull)]
    public LarkWebhookConfig? lark_webhook { get; set; }

    public bool enabled { get; set; } = true; // 알림 기능 사용 여부
}

public class LarkWebhookConfig
{
    public string webhook_url { get; set; } = "";
    public string secret_token { get; set; } = "";
}

public class AwakerSection
{
    public double ping_interval_min { get; set; } = 0;
}