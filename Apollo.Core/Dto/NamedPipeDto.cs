namespace Apollo.Core.Dto;

/// <summary>
/// NamedPipe(IPC) Message DTO
/// </summary>
/// <param name="Type"></param>
/// <param name="Payload"></param>
public record PipeMessage(string Type, string Payload);

/// <summary>
/// NamedPipe(IPC) Ping 요청 DTO
/// </summary>
/// <param name="Time"></param>
public record PingRequest(DateTime Time);

/// <summary>
/// NamedPipe(IPC) Ping 요청에 대한 Pong 응답 DTO
/// </summary>
/// <param name="Alive"></param>
/// <param name="Status"></param>
public record PongResponse(bool Alive, string Status);