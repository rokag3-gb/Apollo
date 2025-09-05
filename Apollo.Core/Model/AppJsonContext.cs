using System.Text.Json.Serialization;
using Apollo.Core.Dto;

namespace Apollo.Core.Model;

[JsonSourceGenerationOptions(
    WriteIndented = false,
    GenerationMode = JsonSourceGenerationMode.Metadata // AOT friendly
)]
[JsonSerializable(typeof(PipeMessage))]
[JsonSerializable(typeof(PingRequest))]
[JsonSerializable(typeof(PongResponse))]
public partial class AppJsonContext : JsonSerializerContext
{
}