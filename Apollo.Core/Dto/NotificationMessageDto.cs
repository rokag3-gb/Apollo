namespace Apollo.Core.Dto;

/// <summary>
/// NotificationService에서 취급하는 message payload 규격
/// </summary>
/// <param name="Title">제목</param>
/// <param name="Body">본문</param>
/// <param name="Attachment">(선택)첨부파일. 추후 타입이 변경될 수 있음.</param>
public record NotificationMessage(NotificationStyle Style, string Title, string Body, byte[]? Attachment);

public enum NotificationStyle
{
    Information, // #정상 #파란색 #단순정보전달
    Success, // #성공 #초록색 #이상없음
    Warning, // #경고 #주황색 #일부성공 #일부실패
    Error // #에러 #빨간색 #실패
}