using Apollo.Core.Dto;

namespace Apollo.Core.Ipc;

public interface INamedPipeServer
{
    void Start();
    void Stop();
}

public interface INamedPipeClient
{
    Task<PongResponse?> SendPingAsync(PingRequest req);
}