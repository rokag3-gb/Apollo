using System.IO.Pipes;
using System.Text.Json;
using Apollo.Core.Dto;
using Apollo.Core.Model;

namespace Apollo.Core.Ipc;

public class NamedPipeServer : INamedPipeServer, IDisposable
{
    private readonly ILogger<NamedPipeServer> _logger;
    private readonly string _pipeName;
    private readonly CancellationTokenSource _cancellationTokenSource;
    private Task? _serverTask;
    private bool _disposed;
    private string _seperatedLine = new string('=', 30);

    public NamedPipeServer(ILogger<NamedPipeServer> logger, string pipeName = "AirBridgePipe")
    {
        _logger = logger;
        _pipeName = pipeName;
        _cancellationTokenSource = new CancellationTokenSource();
    }

    public void Start()
    {
        if (_serverTask != null && !_serverTask.IsCompleted)
            return;

        _serverTask = Task.Run(async () => await RunServerAsync(), _cancellationTokenSource.Token);
        
        _logger.LogInformation($"{_seperatedLine}\nNamedPipe 서버가 시작되었습니다. _pipeName: {_pipeName}");
    }

    public void Stop()
    {
        _cancellationTokenSource.Cancel();

        _serverTask?.Wait(TimeSpan.FromSeconds(2)); // 잠시 대기 (2초)

        _logger.LogInformation($"NamedPipe 서버가 중지되었습니다.");
    }

    private async Task RunServerAsync()
    {
        while (!_cancellationTokenSource.Token.IsCancellationRequested)
        {
            try
            {
                // PipeTransmissionMode
                // 이 호출 사이트에는 모든 플랫폼에서 연결할 수 있습니다. 'PipeTransmissionMode.Message'은(는) 'windows'에서 지원됩니다.
                using var pipeServer = new NamedPipeServerStream(_pipeName, PipeDirection.InOut, 1, PipeTransmissionMode.Byte, PipeOptions.Asynchronous);
                //using var pipeServer = new NamedPipeServerStream(_pipeName, PipeDirection.InOut, 1);

                _logger.LogInformation($"NamedPipe client 연결 대기 중...");

                // 만약 AirBridge.Awaker가 죽어있고 AirBridge 자기 혼자 떠있다면 이 부분에서 계속 대기하게 될 것. (NamedPipeClient가 연결될 때까지)
                await pipeServer.WaitForConnectionAsync(_cancellationTokenSource.Token);

                _logger.LogInformation($"{_seperatedLine}");
                _logger.LogInformation($"NamedPipe client가 연결되었습니다.");

                await ReceiveAndResponse(pipeServer);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"NamedPipe 서버 오류: {ex.Message}");

                // 잠시 대기 (1초)
                await Task.Delay(TimeSpan.FromSeconds(1), _cancellationTokenSource.Token);
            }
        }
    }

    private async Task ReceiveAndResponse(NamedPipeServerStream pipeServer)
    {
        try
        {
            var buffer = new byte[1024];
            var bytesRead = await pipeServer.ReadAsync(buffer, 0, buffer.Length, _cancellationTokenSource.Token);

            if (bytesRead > 0)
            {
                var message = System.Text.Encoding.UTF8.GetString(buffer, 0, bytesRead);
                var pipeMessage = JsonSerializer.Deserialize<PipeMessage>(message, AppJsonContext.Default.PipeMessage);

                if (pipeMessage?.Type == "Ping")
                {
                    var pingRequest = JsonSerializer.Deserialize<PingRequest>(pipeMessage.Payload, AppJsonContext.Default.PingRequest);

                    _logger.LogInformation($"Ping 수신: {pingRequest?.Time}");

                    // PongResponse 만들고 -> PipeMessage로 감싸고 -> JSON 직렬화 -> byte[] 로 치환
                    var pongResponse = new PongResponse(true, "AirBridge is alive");
                    var responseMessage = new PipeMessage("Pong", JsonSerializer.Serialize(pongResponse, AppJsonContext.Default.PongResponse));
                    var responseJson = JsonSerializer.Serialize(responseMessage, AppJsonContext.Default.PipeMessage);
                    var responseBytes = System.Text.Encoding.UTF8.GetBytes(responseJson);

                    //await Task.Delay(TimeSpan.FromSeconds(13)); // 인위적으로 client-side(Awaker) 예외를 발생시키기 위하여 11초 대기

                    // Server -> client에게 byte[] 전송
                    await pipeServer.WriteAsync(responseBytes, 0, responseBytes.Length, _cancellationTokenSource.Token);
                    await pipeServer.FlushAsync(_cancellationTokenSource.Token);

                    _logger.LogInformation($"Pong 응답 전송 완료");
                    _logger.LogInformation($"{_seperatedLine}");
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, $"NamedPipe client의 요청 처리 중 오류: {ex.Message}");
        }
        finally
        {
            if (pipeServer.IsConnected)
            {
                pipeServer.Disconnect();
            }
        }
    }

    public void Dispose()
    {
        if (!_disposed)
        {
            Stop();
            _cancellationTokenSource.Dispose();
            _disposed = true;
        }
    }
}