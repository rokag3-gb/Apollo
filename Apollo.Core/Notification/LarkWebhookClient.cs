using Apollo.Core.Dto;
using Apollo.Core.Model;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
// using Newtonsoft.Json;

namespace Apollo.Core.Notification;

public class LarkWebhookClient
{
    private readonly string _webhookUrl;
    private readonly string _secretToken;
    private readonly HttpClient _httpClient;

    public LarkWebhookClient(string webhookUrl, string secretToken)
    {
        _webhookUrl = webhookUrl;
        _secretToken = secretToken;
        _httpClient = new HttpClient();
    }

    private string GenerateSignature(string secret, string timestamp)
    {
        string stringToSign = $"{timestamp}\n{secret}";
        byte[] keyBytes = Encoding.UTF8.GetBytes(stringToSign);
        byte[] emptyBytes = Array.Empty<byte>();

        using var hmac = new HMACSHA256(keyBytes);
        byte[] hash = hmac.ComputeHash(emptyBytes);

        return Convert.ToBase64String(hash);
    }

    public async Task SendMessageAsync(string message)
    {
        // Unix timestamp in seconds
        string timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString();
        //Console.WriteLine($"[DEBUG] Request payload timestamp: {timestamp}");
        //Console.WriteLine($"[DEBUG] Current UTC time: {DateTimeOffset.UtcNow}");

        var sign = GenerateSignature(_secretToken, timestamp);

        // Lark 간단 텍스트
        /*var payload = new
        {
            timestamp = timestamp,
            sign = sign,
            msg_type = "text",
            content = new { text = message }
        };*/

        // Lark 마크다운
        /*var payload = new
        {
            timestamp = timestamp,
            sign = sign,
            msg_type = "post",
            content = new
            {
                post = new
                {
                    en_us = new
                    {
                        title = "결제 내역 보고서",
                        content = new object[][]
                        {
                            new object[]
                            {
                                new
                                {
                                    tag = "text",
                                    text = "🔔 "
                                },
                                new
                                {
                                    tag = "text",
                                    text = "**결제 내역 보고서**   _243_\n"
                                }
                            },
                            new object[]
                            {
                                new
                                {
                                    tag = "text",
                                    text = "- 오늘 결제 건수: 5건\n- 결제 총액: ₩2,345,000\n"
                                }
                            },
                            new object[]
                            {
                                new
                                {
                                    tag = "a",
                                    text = "자세히 보기",
                                    href = "https://example.com/report"
                                }
                            }
                        }
                    }
                }
            }
        };*/

        // Lark 성공 카드 메시지 (마크다운)
        /*var payload = new
        {
            timestamp = timestamp,
            sign = sign,
            msg_type = "interactive",
            card = new
            {
                header = new
                {
                    title = new
                    {
                        tag = "plain_text",
                        content = "😊 AirBridge batch result message (테스트)"
                    },
                    template = "green" // "blue" (기본), "wathet" (밝은 파랑), "turquoise" (민트색), "green", "yellow", "orange", "red", "purple", "grey"
                },
                elements = new object[]
                {
                    new
                    {
                        tag = "div",
                        text = new
                        {
                            tag = "lark_md",
                            content = "**AirBridge 처리 결과입니다.**\n_(AirBridge는 중계 서버 애플리케이션의 이름입니다.)_"
                        }
                    },
                    new
                    {
                        tag = "div",
                        text = new
                        {
                            tag = "lark_md",
                            content = "**94개 파일에 대한 batch가 완료되었습니다.**\n"
                            + "\n"
                            + "_NXT_IF_Derivatives_: **47**개\n"
                            + "_NXT_IF_Employees_: **1**개\n"
                            + "_NXT_IF_BusinessDay_: **9**개\n"
                            + "_NXT_IF_PB_Securities_: **34**개\n"
                            + "_NXT_IF_Derivatives_Receivable_: **3**개\n"
                            + "\n"
                            + "_ene of message_"
                        }
                    }
                }
            }
        };*/

        // Lark 실패 카드 메시지 (마크다운)
        var payload = new LarkPayload
        {
            Timestamp = timestamp,
            Sign = sign,
            MsgType = "interactive",
            Card = new LarkCard
            {
                Header = new LarkHeader
                {
                    Title = new LarkTitle
                    {
                        Tag = "plain_text",
                        Content = "[ACTION REQUIRED] ☠️ AirBridge batch result message (테스트)"
                    },
                    Template = "red" // "blue" (기본), "wathet" (밝은 파랑), "turquoise" (민트색), "green", "yellow", "orange", "red", "purple", "grey"
                },
                Elements = new LarkElement[]
                {
                    new LarkElement
                    {
                        Tag = "div",
                        Text = new LarkText
                        {
                            Tag = "lark_md",
                            Content = "**AirBridge 처리 결과입니다.**\n_(AirBridge는 중계 서버 애플리케이션의 이름입니다.)_"
                        }
                    },
                    new LarkElement
                    {
                        Tag = "div",
                        Text = new LarkText
                        {
                            Tag = "lark_md",
                            Content = "**94개 파일에 대한 batch가 완료되었습니다.**\n"
                            + "\n"
                            + "_NXT_IF_Derivatives_: **47**개\n"
                            + "_NXT_IF_Employees_: **1**개\n"
                            + "_NXT_IF_BusinessDay_: **9**개\n"
                            + "_NXT_IF_PB_Securities_: **34**개\n"
                            + "_NXT_IF_Derivatives_Receivable_: **3**개\n"
                            + "\n"
                            + "_ene of message_"
                        }
                    }
                }
            }
        };

        // Lark 텍스트 + 마크다운 + 버튼
        /*var payload = new
        {
            timestamp = timestamp,
            sign = sign,
            msg_type = "interactive",
            card = new
            {
                header = new
                {
                    title = new
                    {
                        tag = "plain_text",
                        content = "😊 Lark 메시지 테스트 발송"
                    },
                    template = "green" // "blue" (기본), "wathet" (밝은 파랑), "turquoise" (민트색), "green", "yellow", "orange", "red", "purple", "grey"
                },
                elements = new object[]
                {
                    new
                    {
                        tag = "div",
                        text = new
                        {
                            tag = "lark_md",
                            content = "**지금 처리하겠습니까?** _(궁금궁금)_"
                        }
                    },
                    new
                    {
                        tag = "div",
                        text = new
                        {
                            tag = "lark_md",
                            content = "# markdown 시작 - 대제목\n"
                            + "## 중제목\n"
                            + "### 소제목\n"
                            + "\n"
                            + "- 목록1\n"
                            + "- 목록2\n"
                            + "\n"
                            + "1. 순서1\n"
                            + "2. 순서2\n"
                            + "\n"
                            + "**굵게Bold**, *기울임Italic1*, _기울임Italic2_, ~~취소선strikethrough~~, `인라인 코드`\n"
                            + "\n"
                            + "[](https://naver.com)\n"
                            + "\n"
                            + "> 인용문\n"
                            + "가나다라마바사\n"
                            + "\n"
                            + "```shell\n"
                            + "cp * ~/test/test-root/\n"
                            + "```\n"
                            + "\n"
                            + "_ene of message_"
                        }
                    },
                    // msg_type = "interactive" 에서는 tag "a" 사용 불가
                    new
                    {
                        tag = "a",
                        text = "NXT Ledger I/F Schema (estimation)",
                        href = "https://nsgbpjpgygq3.sg.larksuite.com/docx/GUZudqWlRo5KZ7x0uV7lkxtkgcb"
                    },
                    // tag = "button" 은 해당 action event를 받아서 처리해줄 수 있는 별도의 서버 개발이 필요함.
                    new
                    {
                        tag = "action",
                        actions = new object[]
                        {
                            new
                            {
                                tag = "button",
                                text = new
                                {
                                    tag = "plain_text",
                                    content = "승인"
                                },
                                type = "primary",
                                value = new { action = "approve" }
                            },
                            new
                            {
                                tag = "button",
                                text = new
                                {
                                    tag = "plain_text",
                                    content = "거절"
                                },
                                type = "danger",
                                value = new { action = "reject" }
                            }
                        }
                    }
                }
            }
        }; */

        var content = new StringContent(
            // JsonConvert.SerializeObject(payload),
            JsonSerializer.Serialize(payload, LarkJsonContext.Default.LarkPayload),
            Encoding.UTF8,
            "application/json"
        );

        var response = await _httpClient.PostAsync(_webhookUrl, content);
        var responseBody = await response.Content.ReadAsStringAsync();

        if (!response.IsSuccessStatusCode)
        {
            throw new Exception($"Failed to send message: {responseBody}");
        }

        // var result = JsonConvert.DeserializeObject<WebhookResponse>(responseBody);
        var result = JsonSerializer.Deserialize<WebhookResponse>(responseBody, LarkJsonContext.Default.WebhookResponse);
        if (result?.Code != 0)
        {
            throw new Exception($"Failed to send message: {result?.Msg}");
        }
    }

    public async Task SendMessageAsync(NotificationMessage notificationMessage)
    {
        // Unix timestamp in seconds
        string timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString();
        //Console.WriteLine($"[DEBUG] Request payload timestamp: {timestamp}");
        //Console.WriteLine($"[DEBUG] Current UTC time: {DateTimeOffset.UtcNow}");

        var sign = GenerateSignature(_secretToken, timestamp);

        // Lark interactive card with markdown
        var payload = new LarkPayload
        {
            Timestamp = timestamp,
            Sign = sign,
            MsgType = "interactive",
            Card = new LarkCard
            {
                Header = new LarkHeader
                {
                    Title = new LarkTitle
                    {
                        Tag = "plain_text",
                        Content = notificationMessage.Title // "[ACTION REQUIRED] ☠️ AirBridge batch result message (테스트)"
                    },
                    // 카드 상단 배경색: "blue" (기본), "wathet" (밝은 파랑), "turquoise" (민트색), "green", "yellow", "orange", "red", "purple", "grey"
                    //Template = "red"
                    //Template = switch case notificationMessage.Style
                    Template = notificationMessage.Style switch
                    {
                        NotificationStyle.Information => "blue",
                        NotificationStyle.Success => "green",
                        NotificationStyle.Warning => "orange",
                        NotificationStyle.Error => "red",
                        _ => throw new NotSupportedException($"지원하지 않는 알림 채널입니다: {notificationMessage.Style}")
                    }
                },
                Elements = new LarkElement[]
                {
                    new LarkElement
                    {
                        Tag = "div",
                        Text = new LarkText
                        {
                            Tag = "lark_md",
                            Content = notificationMessage.Body
                        }
                    }
                }
            }
        };

        var content = new StringContent(
            JsonSerializer.Serialize(payload, LarkJsonContext.Default.LarkPayload),
            Encoding.UTF8,
            "application/json"
        );

        var response = await _httpClient.PostAsync(_webhookUrl, content);
        var responseBody = await response.Content.ReadAsStringAsync();

        if (!response.IsSuccessStatusCode)
        {
            throw new Exception($"Failed to send message: {responseBody}");
        }

        // var result = JsonConvert.DeserializeObject<WebhookResponse>(responseBody);
        var result = JsonSerializer.Deserialize<WebhookResponse>(responseBody, LarkJsonContext.Default.WebhookResponse);
        if (result?.Code != 0)
        {
            throw new Exception($"Failed to send message: {result?.Msg}");
        }
    }
}

[JsonSourceGenerationOptions(PropertyNamingPolicy = JsonKnownNamingPolicy.SnakeCaseLower)]
[JsonSerializable(typeof(LarkPayload))]
[JsonSerializable(typeof(LarkCard))]
[JsonSerializable(typeof(LarkHeader))]
[JsonSerializable(typeof(LarkTitle))]
[JsonSerializable(typeof(LarkElement))]
[JsonSerializable(typeof(LarkText))]
[JsonSerializable(typeof(WebhookResponse))]
internal partial class LarkJsonContext : JsonSerializerContext
{
}

class LarkPayload
{
    public string Timestamp { get; set; } = string.Empty;
    public string Sign { get; set; } = string.Empty;
    public string MsgType { get; set; } = string.Empty;
    public LarkCard Card { get; set; } = new();
}

class LarkCard
{
    public LarkHeader Header { get; set; } = new();
    public object[] Elements { get; set; } = Array.Empty<object>();
}

class LarkHeader
{
    public LarkTitle Title { get; set; } = new();
    public string Template { get; set; } = string.Empty;
}

class LarkTitle
{
    public string Tag { get; set; } = string.Empty;
    public string Content { get; set; } = string.Empty;
}

class LarkElement
{
    public string Tag { get; set; } = string.Empty;
    public LarkText Text { get; set; } = new();
}

class LarkText
{
    public string Tag { get; set; } = string.Empty;
    public string Content { get; set; } = string.Empty;
}

class WebhookResponse
{
    /*
    Symptom: 리눅스 AOT 환경에서 다음 오류 발생
    -> "Newtonsoft.Json.JsonSerializationException: Unable to find a constructor to use for type AirBridge.Core.Notification.LarkWebhookClient+WebhookResponse. A class should either have a default cosntructor, one cosntructor with arguments or a cosntructor marked with the JsonConstructor attribute. Path 'code', line 1, position 8."

    Cause: Newtonsoft.Json이 리눅스 AOT 환경에서 내부적으로 리플렉션을 사용해 WebhookResponse 객체를 생성하려고 할 때, 기본 생성자가 없거나 AOT 환경에서 생성자를 찾지 못해서 발생하는 오류
    
    Solution: AOT 환경에서는 리플렉션이 제한되기 때문에, 기본 생성자를 명시적으로 추가해준다.
    */
    public WebhookResponse() // 기본 생성자 추가
    {
    }

    [JsonPropertyName("code")]
    public int Code { get; set; }

    [JsonPropertyName("msg")]
    public string? Msg { get; set; }
}