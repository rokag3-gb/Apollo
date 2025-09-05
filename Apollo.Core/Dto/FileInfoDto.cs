namespace Apollo.Core.Dto;

public record FileInfoDto(
    string Name, // "20250717105000_NXT_IF_BusinessDay"
    string FullPath, // "C:\\AirBridgeTestLedgerRoot\\20250717105000_NXT_IF_BusinessDay"
    string Extension,
    long? Length,
    bool IsReadOnly,
    UnixFileMode UnixFileMode,
    string DirectoryName, // "C:\\AirBridgeTestLedgerRoot"
    DirectoryInfoDto DirectoryInfoDto,
    DateTime CreationTime,
    DateTime CreationTimeUtc,
    DateTime LastAccessTime,
    DateTime LastAccessTimeUtc,
    DateTime LastWriteTime,
    DateTime LastWriteTimeUtc
);

public record DirectoryInfoDto(
    string Name, // "AirBridgeTestLedgerRoot"
    string FullPath, // "C:\\AirBridgeTestLedgerRoot"
    UnixFileMode UnixFileMode,
    DateTime CreationTime,
    DateTime CreationTimeUtc,
    DateTime LastAccessTime,
    DateTime LastAccessTimeUtc,
    DateTime LastWriteTime,
    DateTime LastWriteTimeUtc
);