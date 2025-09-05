using System.IO.Pipes;
using System.Text;
using System.Text.Json;
using Apollo.Core.Dto;
using Apollo.Core.Ipc;
using Apollo.Core.Model;

namespace Apollo.Awaker.Ipc;

public class NamedPipeClient : INamedPipeClient, IDisposable
{
    private readonly ILogger<NamedPipeClient> _logger;
    private readonly string _pipeName;
    private readonly string _serverName;
    private readonly TimeSpan _connectTimeout = TimeSpan.FromSeconds(10); // 10초
    private bool _disposed;

    public NamedPipeClient(ILogger<NamedPipeClient> logger, string pipeName = "AirBridgePipe", string serverName = ".")
    {
        _logger = logger;
        _pipeName = pipeName;
        _serverName = serverName;
    }

    public async Task<PongResponse?> SendPingAsync(PingRequest pingRequest)
    {
        try
        {
            using var pipeClient = new NamedPipeClientStream(_serverName, _pipeName, PipeDirection.InOut, PipeOptions.Asynchronous);

            _logger.LogInformation($"NamedPipe 서버에 연결 중... ({_serverName}/{_pipeName})");

            await pipeClient.ConnectAsync(_connectTimeout, CancellationToken.None); // _connectTimeout 10초 이내에 NamedPipeServer에서 응답안오면 exception 발생

            _logger.LogInformation($"NamedPipe 서버에 연결되었습니다.");

            var pingMessage = new PipeMessage("Ping", JsonSerializer.Serialize(pingRequest, AppJsonContext.Default.PingRequest));
            var messageJson = JsonSerializer.Serialize(pingMessage, AppJsonContext.Default.PipeMessage);
            var messageBytes = Encoding.UTF8.GetBytes(messageJson);

            await pipeClient.WriteAsync(messageBytes, 0, messageBytes.Length);
            await pipeClient.FlushAsync();

            _logger.LogInformation($"Ping 메시지 전송 완료");

            var buffer = new byte[1024];
            var bytesRead = await pipeClient.ReadAsync(buffer, 0, buffer.Length); // response 읽어오기

            if (bytesRead > 0)
            {
                var responseMessage = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                var pipeMessage = JsonSerializer.Deserialize<PipeMessage>(responseMessage, AppJsonContext.Default.PipeMessage);
                
                if (pipeMessage?.Type == "Pong")
                {
                    var pongResponse = JsonSerializer.Deserialize<PongResponse>(pipeMessage.Payload, AppJsonContext.Default.PongResponse);

                    _logger.LogInformation($"Pong 응답 수신: {pongResponse?.Status}");

                    return pongResponse;
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, $"NamedPipe 클라이언트 오류: {ex.Message}");
        }

        return null;
    }

    public void Dispose()
    {
        if (!_disposed)
        {
            _disposed = true;
        }
    }
}