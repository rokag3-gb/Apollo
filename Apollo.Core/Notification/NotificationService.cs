using Apollo.Core.Dto;
using Apollo.Core.Model;

namespace Apollo.Core.Notification;

public class NotificationService
{
    private readonly INotificationSenderFactory _factory;
    private readonly ILogger<NotificationService> _logger;

    public NotificationService(INotificationSenderFactory factory, ILogger<NotificationService> logger)
    {
        _factory = factory;
        _logger = logger;
    }

    public void Notify(NotificationType type, NotificationMessage notificationMessage)
    {
        if (!Conf.Current.notification.enabled)
        {
            _logger.LogInformation($"AirBridgeConfig.yaml > notification > enabled: false 이므로 알림을 발송하지 않습니다.");
            return;
        }

        var sender = _factory.Create(type);

        sender.Send(notificationMessage);
    }
}