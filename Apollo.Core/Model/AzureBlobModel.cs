namespace Apollo.Core.Model;

public record AzureBlob(
    string Name,
    string FullName,
    string Type,
    long? Length,
    DateTimeOffset? LastWriteTime,
    DateTimeOffset? LastAccessTime
);