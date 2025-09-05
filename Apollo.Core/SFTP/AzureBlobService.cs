using Microsoft.Extensions.Logging.Abstractions;
using Renci.SshNet;
using Apollo.Core.Model;
using Apollo.Core.Helper;

namespace Apollo.Core.Sftp;

public interface IAzureBlobService
{
    Task<List<AzureBlob>> GetBlobList(string path);
    Task<AzureBlob> GetBlob(string path);
    Task DownloadFile(string remoteFilePath, string localFilePath);
    Task UploadFile(string localFilePath, string remoteFilePath);
    Task MkDir(string path);
    Task RemoveDir(string path);
    Task RenameDir(string oldPath, string newPath);
}

public class AzureBlobService : IAzureBlobService, IDisposable
{
    private readonly ILogger<AzureBlobService> _logger;
    private readonly AzureBlobSftpConfig? _config;
/*
# dotnet-dump 분석을 통한 AzureBlobService 개선 (2025.08.08)

1. SFTP 수명 단축: SftpClient를 매 호출마다 생성/연결/해제
* 현재 AzureBlobService는 _sftp 필드를 보관하고, 메서드 내에서 연결만 붙입니다. 장시간 대기 시 Renci.SshNet 내부 버퍼/스트림이 오래 붙잡히기 쉽습니다.
* 권장: _sftp 필드를 제거하고, 각 메서드에서 using var sftp = CreateAndConnectClient(); 패턴으로 짧게 생성-사용-해제하세요. 또한 Task.Run으로 감싸지 말고 동기로 호출해 스레드풀이 불필요하게 늘지 않게 합니다.
* 조치사항:
1) SftpClient를 매 호출마다 생성/연결/해제하도록 변경
2) AzureBlobService 생성자에서 SftpClient를 생성하지 않도록 변경
3) CreateAndConnectSftpClient 메서드로 SftpClient 생성 및 연결 로직 분리
4) 각 메서드 내부에서 using var sftp = CreateAndConnectSftpClient(); 패턴으로 SftpClient를 사용하고 해당 메서드 작동 완료 이후에 GC 통해서 자동 반납되도록 수정

2. LoggerFactory 새로 만들지 않기
* 현재 AzureBlobService(AzureBlobSftpConfig) 생성자에서 new LoggerFactory()를 매번 생성합니다. 이건 IDisposable이며 내부 버퍼/스레드 등을 붙잡을 수 있어 장기 실행 서비스에는 좋지 않습니다.
* 권장: 기본 생성자는 NullLogger<AzureBlobService>.Instance로 대체하거나 아예 제거하고, DI로만 주입 받게 하세요
* 조치사항:
1) LoggerFactory를 사용하지 않고 NullLogger<AzureBlobService>.Instance를 사용하도록 변경
2) 생성자 1개로 통합하고, ILogger<AzureBlobService>를 DI로 주입받도록 변경
*/
    private bool _disposed;

    public AzureBlobService(AzureBlobSftpConfig config)
    {
        _logger = NullLogger<AzureBlobService>.Instance;
        _config = config ?? throw new ArgumentNullException(nameof(config));
    }

    private SftpClient CreateAndConnectSftpClient()
    {
        if (_config is null)
            throw new InvalidOperationException("Configuration is null");

        // 프라이빗키 파일 로드
        PrivateKeyFile privateKey;
        var authMethods = new AuthenticationMethod[1];

        if (_config.private_key_path is not null && File.Exists(_config.private_key_path))
        {
            using (var fs = new FileStream(_config.private_key_path, FileMode.Open, FileAccess.Read))
            {
                privateKey = new PrivateKeyFile(fs);
                // privateKey = string.IsNullOrEmpty(passphrase)
                //     ? new PrivateKeyFile(fs)
                //     : new PrivateKeyFile(fs, passphrase);
            }

            // var keyFiles = new[] { privateKey };

            authMethods = new AuthenticationMethod[]
            {
                new PrivateKeyAuthenticationMethod(_config.username, new[] { privateKey })
            };
        }
        else if (!string.IsNullOrEmpty(_config.password))
        {
            authMethods = new AuthenticationMethod[]
            {
                new PasswordAuthenticationMethod(_config.username, _config.password)
            };
        }
        else
        {
            throw new InvalidOperationException("Either password or private_key_path must be provided");
        }

        var connectionInfo = new ConnectionInfo(_config.host, _config.port, _config.username, authMethods);
        var sftp = new SftpClient(connectionInfo);
        sftp.ConnectionInfo.Timeout = TimeSpan.FromSeconds(10);
        sftp.OperationTimeout = TimeSpan.FromMinutes(5);
        sftp.KeepAliveInterval = TimeSpan.FromSeconds(30);
        sftp.BufferSize = 32 * 1024; // LOH(85KB) 넘지 않도록 안전한 기본값
        sftp.Connect();

        return sftp;
    }

    private string GetBlobType(bool IsDirectory)
    {
        return IsDirectory ? "directory" : "file";
    }

    /// <summary>
    /// Gets a list of files and directories in the specified path. (not recursion)
    /// If no path is specified, it defaults to the local user's home directory.
    /// </summary>
    /// <param name="path"></param>
    /// <returns></returns>
    public async Task<List<AzureBlob>> GetBlobList(string path = ".")
    {
        var list = new List<AzureBlob>();

        try
        {
            using var sftp = CreateAndConnectSftpClient();

            // 특정 path에 대한 디렉토리, 파일 목록 조회
            var files = await Task.Run(() => sftp.ListDirectory(path));
            // var files = sftp.ListDirectory(path);

            if (files is not null)
            {
                foreach (var fi in files)
                {
                    if (fi is null)
                        continue;

                    var fileInfo = new AzureBlob(
                        Name: fi.Name,
                        FullName: fi.FullName, // 전체 경로
                        Type: GetBlobType(fi.IsDirectory),
                        Length: fi.Length,
                        LastWriteTime: fi.LastWriteTime,
                        LastAccessTime: fi.LastAccessTime
                    );

                    list.Add(fileInfo);
                }
            }

            return list;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Blob 목록 조회 중 오류 발생");
            throw;
        }
    }

    public async Task<AzureBlob> GetBlob(string path)
    {
        try
        {
            using var sftp = CreateAndConnectSftpClient();

            var blob = await Task.Run(() => sftp.Get(path));

            return new AzureBlob(
                Name: blob?.Name ?? "",
                FullName: blob?.FullName ?? "",
                Type: GetBlobType(blob?.IsDirectory ?? false),
                Length: blob?.Length ?? 0,
                LastWriteTime: blob?.LastWriteTime,
                LastAccessTime: blob?.LastAccessTime
            );
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Blob 정보 조회 중 오류 발생");
            throw;
        }
    }

    /// <summary>
    /// Downloads a file from the SFTP server to a local path. If the file already exists locally, it will be overwritten.
    /// </summary>
    /// <param name="remoteFilePath"></param>
    /// <param name="localFilePath"></param>
    /// <returns></returns>
    public async Task DownloadFile(string remoteFilePath, string localFilePath)
    {
        try
        {
            using var sftp = CreateAndConnectSftpClient();

            using (var fileStream = File.Create(localFilePath))
            {
                await Task.Run(() => sftp.DownloadFile(remoteFilePath, fileStream));
            }

            _logger.LogInformation($"파일 다운로드 완료: {remoteFilePath} -> {localFilePath}");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "파일 다운로드 중 오류 발생");
            throw;
        }
    }

    /// <summary>
    /// Uploads a file from a local path to the SFTP server. If the file already exists on the server, it will be overwritten.
    /// </summary>
    /// <param name="localFilePath"></param>
    /// <param name="remoteFilePath"></param>
    /// <returns></returns>
    public async Task UploadFile(string localFilePath, string remoteFilePath)
    {
        try
        {
            using var sftp = CreateAndConnectSftpClient();

            using (var fileStream = File.OpenRead(localFilePath))
            {
                await Task.Run(() => sftp.UploadFile(fileStream, remoteFilePath));
            }

            _logger.LogInformation($"파일 업로드 완료: {localFilePath} -> {remoteFilePath}");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "파일 업로드 중 오류 발생");
            throw;
        }
    }

    /// <summary>
    /// Creates a directory on the SFTP server at the specified path. If the directory already exists, nothing changed.
    /// </summary>
    /// <param name="path"></param>
    /// <returns></returns>
    public async Task MkDir(string path)
    {
        try
        {
            using var sftp = CreateAndConnectSftpClient();

            await Task.Run(() =>
            {
                if (!sftp.Exists(path)) // path 디렉토리가 없는 경우에만 디렉토리 생성
                    sftp.CreateDirectory(path);
            });

            _logger.LogInformation($"디렉토리 생성 완료: {path}");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "디렉토리 생성 중 오류 발생");
            throw;
        }
    }

    /// <summary>
    /// Deletes a directory on the SFTP server at the specified path. If the directory does not exist, it will not throw an error. (DirectoryNotFound)
    /// </summary>
    /// <param name="path"></param>
    /// <returns></returns>
    public async Task RemoveDir(string path)
    {
        try
        {
            using var sftp = CreateAndConnectSftpClient();

            await Task.Run(() => sftp.DeleteDirectory(path));

            _logger.LogInformation($"디렉토리 삭제 완료: {path}");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "디렉토리 삭제 중 오류 발생");
            throw;
        }
    }

    /// <summary>
    /// Renames a directory on the SFTP server from oldPath to newPath. If the oldPath does not exist, it will throw an error. (SourcePathNotFound)
    /// If the newPath already exists, it will throw an error. (BlobAlreadyExists)
    /// </summary>
    /// <param name="oldPath"></param>
    /// <param name="newPath"></param>
    /// <returns></returns>
    public async Task RenameDir(string oldPath, string newPath)
    {
        try
        {
            using var sftp = CreateAndConnectSftpClient();

            await Task.Run(() => sftp.RenameFile(oldPath, newPath));

            _logger.LogInformation($"디렉토리 이름 변경 완료: {oldPath} -> {newPath}");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "디렉토리 이름 변경 중 오류 발생");
            throw;
        }
    }

    public void Dispose()
    {
        Dispose(true);
        GC.SuppressFinalize(this);
    }
    protected virtual void Dispose(bool disposing)
    {
        if (_disposed)
            return;

        if (disposing)
        {
            try
            {
                // if (_sftp != null)
                // {
                //     if (_sftp.IsConnected)
                //         _sftp.Disconnect();
                    
                //     _sftp.Dispose();
                // }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "SFTP 연결 해제 중 오류 발생");
            }
        }

        // _sftp = null;
        _disposed = true;
    }
    ~AzureBlobService()
    {
        Dispose(false);
    }
}