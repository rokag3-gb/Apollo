using YamlDotNet.Serialization;

namespace Apollo.Core.Model;

[YamlStaticContext]
[YamlSerializable(typeof(AppConfig))]
[YamlSerializable(typeof(ScheduleSection))]
[YamlSerializable(typeof(SourceSection))]
[YamlSerializable(typeof(TargetSection))]
[YamlSerializable(typeof(MountedPathConfig))]
[YamlSerializable(typeof(AzureBlobSftpConfig))]
[YamlSerializable(typeof(AzureBlobSasConfig))]
[YamlSerializable(typeof(NotificationSection))]
[YamlSerializable(typeof(LarkWebhookConfig))]
[YamlSerializable(typeof(AwakerSection))]
[YamlSerializable(typeof(ConnectType))]
[YamlSerializable(typeof(NotificationType))]
public partial class AppConfigYamlContext : StaticContext
{
}