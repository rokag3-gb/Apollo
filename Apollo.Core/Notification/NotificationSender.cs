using Apollo.Core.Dto;

namespace Apollo.Core.Notification;

public interface INotificationSender
{
    Task Send(NotificationMessage notificationMessage);
}

// Lark 발송
public class LarkNotificationSender : INotificationSender
{
    private readonly ILogger<LarkNotificationSender> _logger;

    public LarkNotificationSender(ILogger<LarkNotificationSender> logger)
    {
        _logger = logger;
    }

    public async Task Send(NotificationMessage notificationMessage)
    {
        try
        {
            if (Conf.Current.notification.lark_webhook is not null)
            {
                // Secret 클래스에서 설정 값을 가져와서 사용
                var webhookClient = new LarkWebhookClient(
                    Conf.Current.notification.lark_webhook.webhook_url,
                    Conf.Current.notification.lark_webhook.secret_token
                );

                // 메시지 전송
                await webhookClient.SendMessageAsync(notificationMessage);
            }

            _logger.LogInformation($"[Lark Notification] 성공적으로 발송되었습니다!");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, $"Lark 메시지 발송 중 오류 발생! {ex.Message}");
        }
    }
}

// Email 발송
public class EmailNotificationSender : INotificationSender
{
    private readonly ILogger<EmailNotificationSender> _logger;

    public EmailNotificationSender(ILogger<EmailNotificationSender> logger)
    {
        _logger = logger;
    }

    public async Task Send(NotificationMessage notificationMessage)
    {
        try
        {
            await Task.Run(() =>
            {
                // Email 발송 로직을 여기에 구현

                _logger.LogInformation($"[Email Notification] {notificationMessage.Body}");
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, $"Email 발송 중 오류 발생! {ex.Message}");
        }
    }
}

// SMS 발송
public class SmsNotificationSender : INotificationSender
{
    private readonly ILogger<SmsNotificationSender> _logger;

    public SmsNotificationSender(ILogger<SmsNotificationSender> logger)
    {
        _logger = logger;
    }

    public async Task Send(NotificationMessage notificationMessage)
    {
        try
        {
            await Task.Run(() =>
            {
                // SMS 발송 로직을 여기에 구현

                _logger.LogInformation($"[SMS Notification] {notificationMessage.Body}");
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, $"SMS 발송 중 오류 발생! {ex.Message}");
        }
    }
}