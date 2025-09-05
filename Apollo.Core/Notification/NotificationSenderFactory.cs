using Microsoft.Extensions.DependencyInjection;
using Apollo.Core.Model;

namespace Apollo.Core.Notification;

public interface INotificationSenderFactory
{
    INotificationSender Create(NotificationType type);
}

public class NotificationSenderFactory : INotificationSenderFactory
{
    private readonly IServiceProvider _serviceProvider;

    public NotificationSenderFactory(IServiceProvider serviceProvider)
    {
        _serviceProvider = serviceProvider;
    }

    public INotificationSender Create(NotificationType type)
    {
        return type switch
        {
            NotificationType.Lark_Webhook => _serviceProvider.GetRequiredService<LarkNotificationSender>(),
            NotificationType.Email => _serviceProvider.GetRequiredService<EmailNotificationSender>(),
            NotificationType.Sms => _serviceProvider.GetRequiredService<SmsNotificationSender>(),

            _ => throw new NotSupportedException($"지원하지 않는 알림 채널입니다: {type}")
        };
    }
}