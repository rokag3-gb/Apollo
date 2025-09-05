using Newtonsoft.Json;
using System.Globalization;
using Apollo.Core.Dto;
using Apollo.Core.Model;
using Apollo.Core.Notification;
using Apollo.Core.Sftp;

namespace Apollo.Core;

public interface IFileService
{
    public Task TransferAllFiles();

    public void CleanUpExpiredArchivedFiles(int _retentionDays);

    public void CleanUpExpiredLogFiles(string _rootLogDir, int _retentionDays);

    IEnumerable<string>? GetAllFiles(string _dir);
}

public class FileService : IFileService
{
    private readonly ILogger<FileService> _logger;
    private readonly NotificationService _notifier;
    private readonly string _rootDir;
    private readonly string _rootArchivedDir;
    private const string _templateBody = "{freeText}\n"
                            + "\n"
                            + "{fileList}\n"
                            + "\n";

    private const string _templateFooter = "💻 Host: {HostName}\n"
                            + "({PublicIPv4}, {PrivateIPv4})\n"
                            + "시작: {StartedAt}\n"
                            + "종료: {CompletedAt}\n"
                            + "({Duration} 소요)";

    public FileService(ILogger<FileService> logger, NotificationService notifier)
    {
        _logger = logger;
        _notifier = notifier;
        _rootDir = Conf.Current.source.mounted_path?.path ?? "";
        _rootArchivedDir = Conf.Current.source.mounted_path?.archive_path ?? "";
    }

    public async Task TransferAllFiles()
    {
        DateTime startedAt = DateTime.Now;
        DateTime completedAt;

        try
        {
            var files = GetAllFiles(_rootDir);
            var TotalCount = files?.Count() ?? 0;

            List<string> successFiles = new List<string>();
            List<string> failedFiles = new List<string>();

            string _footer = _templateFooter;

            if (Conf.CurrentNetInfo.PublicIPv4?.ToString() == Conf.CurrentNetInfo.PrivateIPv4?.ToString())
            {
                _footer = _footer
                    .Replace("({PublicIPv4}, {PrivateIPv4})", "({PublicIPv4})");
            }

            _footer = _footer
                    .Replace("{HostName}", Conf.CurrentNetInfo.HostName)
                    .Replace("{PublicIPv4}", Conf.CurrentNetInfo.PublicIPv4?.ToString() ?? "")
                    .Replace("{PrivateIPv4}", Conf.CurrentNetInfo.PrivateIPv4?.ToString() ?? "")
                    .Replace("{StartedAt}", $"{startedAt:MM-dd HH:mm:ss.fff}");

            // source (mounted_path) 안에 아무 파일이 없을 경우
            if (files is null || !files.Any())
            {
                //if ((startedAt.Hour == 9 && startedAt.Minute == 0 && startedAt.Second >= 0 && startedAt.Second < 10) // 09:00
                //    || (startedAt.Hour == 15 && startedAt.Minute == 0 && startedAt.Second >= 0 && startedAt.Second < 10) // 15:00
                //    || (startedAt.Hour == 21 && startedAt.Minute == 0 && startedAt.Second >= 0 && startedAt.Second < 10) // 21:00
                //    )
                //{
                    completedAt = DateTime.Now;
                    TimeSpan duration2 = completedAt - startedAt;

                    _footer = _footer
                        .Replace("{CompletedAt}", $"{completedAt:MM-dd HH:mm:ss.fff}")
                        .Replace("{Duration}", $"{duration2.TotalHours:00}:{duration2.Minutes:00}:{duration2.Seconds:00}.{duration2.Milliseconds:000}")
                        ;

                    NotifyMessage(TotalCount, successFiles, failedFiles, _footer);
                //}

                _logger.LogInformation($"TransferAllFiles - No files found in the source directory: {_rootDir}");

                return;
            }


            // AzureBlobService 직접 생성
            AzureBlobSftpConfig? config = Conf.Current.target.azure_blob_sftp;
            if (config is null)
            {
                _logger.LogError("Conf.Current.target.azure_blob_sftp is null. Please check your AirBridgeConfig.yaml file.");
                return;
            }


            // 모든 파일에 대해 처리하는 loop 시작
            foreach (var file in files)
            {
                var fi = new FileInfo(file);

                if (!fi.Exists)
                {
                    _logger.LogWarning($"fileInfo is not exists. - {fi.FullName}");
                    continue;
                }

                FileInfoDto _fi = new FileInfoDto(
                    fi.Name,
                    fi.FullName,
                    fi.Extension,
                    fi.Length,
                    fi.IsReadOnly,
                    fi.UnixFileMode,
                    DirectoryName: fi.DirectoryName ?? "",
                    DirectoryInfoDto: new DirectoryInfoDto(
                        fi.Directory?.Name ?? "",
                        fi.Directory?.FullName ?? "",
                        fi.Directory?.UnixFileMode ?? UnixFileMode.None,
                        fi.Directory?.CreationTime ?? DateTime.Now,
                        fi.Directory?.CreationTimeUtc ?? DateTime.UtcNow,
                        fi.Directory?.LastAccessTime ?? DateTime.Now,
                        fi.Directory?.LastAccessTimeUtc ?? DateTime.UtcNow,
                        fi.Directory?.LastWriteTime ?? DateTime.Now,
                        fi.Directory?.LastWriteTimeUtc ?? DateTime.UtcNow
                    ),
                    fi.CreationTime,
                    fi.CreationTimeUtc,
                    fi.LastAccessTime,
                    fi.LastAccessTimeUtc,
                    fi.LastWriteTime,
                    fi.LastWriteTimeUtc
                );

                _logger.LogInformation($"_fi.Name = {_fi.Name}, _fi.FullPath = {_fi.FullPath}, _fi = {JsonConvert.SerializeObject(_fi, Formatting.None)}");

                /*
                FileInfoDto Example Value:

                ```json
                {
                    "Name": "20250701220000_NXT_IF_Derivatives_Receivable",
                    "FullPath": "C:\\AirBridgeTestLedgerRoot\\aback\\20250701220000_NXT_IF_Derivatives_Receivable",
                    "Extension": "",
                    "Length": 520,
                    "IsReadOnly": false,
                    "UnixFileMode": -1,
                    "DirectoryName": "C:\\AirBridgeTestLedgerRoot\\aback",
                    "DirectoryInfoDto": {
                        "Name": "aback",
                        "FullPath": "C:\\AirBridgeTestLedgerRoot\\aback",
                        "UnixFileMode": -1,
                        "CreationTime": "2025-08-22T10:03:24.9781533+09:00",
                        "CreationTimeUtc": "2025-08-22T01:03:24.9781533Z",
                        "LastAccessTime": "2025-08-28T09:03:18.7650738+09:00",
                        "LastAccessTimeUtc": "2025-08-28T00:03:18.7650738Z",
                        "LastWriteTime": "2025-08-22T10:08:33.6255447+09:00",
                        "LastWriteTimeUtc": "2025-08-22T01:08:33.6255447Z"
                    },
                    "CreationTime": "2025-08-04T11:14:37.1145199+09:00",
                    "CreationTimeUtc": "2025-08-04T02:14:37.1145199Z",
                    "LastAccessTime": "2025-08-25T12:57:41.4109867+09:00",
                    "LastAccessTimeUtc": "2025-08-25T03:57:41.4109867Z",
                    "LastWriteTime": "2025-08-04T10:22:32.8629765+09:00",
                    "LastWriteTimeUtc": "2025-08-04T01:22:32.8629765Z"
                }
                ```
                */

                // 클래스 전역 변수 private AzureBlobService? _blob 필드는 사용하지 않고, 대신 지역 using var blob = new AzureBlobService(...); 으로 수명주기를 짧게 잡아줌.
                using var _blob = new AzureBlobService(config);

                // DirectoryName "C:\\AirBridgeTestLedgerRoot\\aback" 중에서 mounted_path "C:\\AirBridgeTestLedgerRoot" 을 "" 으로 변경
                // 결론은 "\\aback" 이런 형태의 상대경로만 남는다.
                string relativeDir = _fi.DirectoryName // "C:\\AirBridgeTestLedgerRoot\\aback"
                    .Replace(_rootDir, "") // "\\aback"
                    .Replace(@"\", ""); // "aback"

                try
                {
                    // SFTP home directory 하위에 폴더 생성
                    await _blob.MkDir($"{relativeDir}");

                    _logger.LogInformation($"Azure Blob 폴더 생성 성공: {relativeDir}");

                    // 파일 업로드 (무조건 Overwrite)
                    await _blob.UploadFile(_fi.FullPath, $"{relativeDir}/{fi.Name}");

                    _logger.LogInformation($"Azure Blob 파일 업로드 성공: {relativeDir}/{fi.Name}");
                }
                catch (Exception ex)
                {
                    failedFiles.Add(_fi.FullPath);

                    _logger.LogError(ex, $"Azure Blob 처리 중 에러 발생! {ex.Message}");
                    continue;
                }
                finally
                {
                    _blob?.Dispose();
                }

                // 원본 파일을 path -> archive_path 으로 이동
                try
                {
                    if (Conf.Current.source.mounted_path is not null)
                    {
                        // archive_path/relativeDir 디렉토리 없으면 생성
                        if (!Directory.Exists(Path.Combine(Conf.Current.source.mounted_path.archive_path, relativeDir)))
                            Directory.CreateDirectory(Path.Combine(Conf.Current.source.mounted_path.archive_path, relativeDir));

                        // archive_path/relativeDir/fileName 존재하면 삭제
                        if (File.Exists(Path.Combine(Conf.Current.source.mounted_path.archive_path, relativeDir, _fi.Name)))
                            File.Delete(Path.Combine(Conf.Current.source.mounted_path.archive_path, relativeDir, _fi.Name));

                        // 파일 이동
                        File.Move(_fi.FullPath,
                            Path.Combine(Conf.Current.source.mounted_path.archive_path, relativeDir, _fi.Name)
                            );

                        _logger.LogInformation($"archive path로 파일 보관 성공! -> archive_path = {Path.Combine(Conf.Current.source.mounted_path.archive_path, relativeDir, _fi.Name)}");
                    }
                }
                catch (Exception ex)
                {
                    failedFiles.Add(_fi.FullPath);

                    _logger.LogError(ex, $"archive path로 파일 보관 중 에러 발생! {ex.Message}");
                    continue;
                }

                successFiles.Add(_fi.FullPath);
            }

            // 메시지 발송 준비

            // Config 상에 설정된 경로는 ""으로 일괄 변경. (모든 파일의 FullPath 앞쪽은 다 동일함)
            successFiles = successFiles.Select(s => s.Replace(_rootDir, "")).ToList();
            failedFiles = failedFiles.Select(s => s.Replace(_rootDir, "")).ToList();

            completedAt = DateTime.Now;
            TimeSpan duration = completedAt - startedAt;

            _footer = _footer
                .Replace("{CompletedAt}", $"{completedAt:MM-dd HH:mm:ss.fff}")
                .Replace("{Duration}", $"{duration.TotalHours:00}:{duration.Minutes:00}:{duration.Seconds:00}.{duration.Milliseconds:000}");

            // 메시지 발송
            NotifyMessage(TotalCount, successFiles, failedFiles, _footer);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, $"TransferAllFiles() 내부에서 에러 발생!: {ex.Message}");
            return;
        }
    }

    public void CleanUpExpiredArchivedFiles(int _retentionDays)
    {
        try
        {
            var files = GetAllFiles(_rootArchivedDir);

            var expiredArchivedFiles = files?
                .Where(f => {
                    var fi = new FileInfo(f);
                    // "CreationTime": "2025-08-04T11:14:37.1145199+09:00"
                    return fi.CreationTime.AddDays(_retentionDays) < DateTime.Now; // 20250814 에 90일을 더해도 오늘보다 이전 (= 90일 초과)
                })
                .ToList();

            if (expiredArchivedFiles is null || !expiredArchivedFiles.Any())
            {
                _logger.LogInformation($"CleanUpExpiredArchivedFiles - No expired files found in the archived directory: {_rootArchivedDir}");
                return;
            }

            foreach (var file in expiredArchivedFiles)
            {
                if (File.Exists(file))
                {
                    File.Delete(file);

                    _logger.LogInformation($"CleanUpExpiredArchivedFiles - 파일 삭제 완료: {file}");
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, $"CleanUpExpiredArchivedFiles() 내부에서 에러 발생!: {ex.Message}");
            return;
        }
    }

    public void CleanUpExpiredLogFiles(string _rootLogDir, int _retentionDays)
    {
        try
        {
            var files = GetAllFiles(_rootLogDir);

            var expiredLogFiles = files?
                .Where(f => f.EndsWith(".log", StringComparison.OrdinalIgnoreCase))
                .Where(f => {
                    var name = Path.GetFileNameWithoutExtension(f); // "AirBridge-20250814"

                    if (string.IsNullOrEmpty(name) || name.Length < 8) return false;

                    var tail = name.AsSpan(name.Length - 8, 8); // 파일명 끝 8자리: "20250814"

                    DateTime date = DateTime.ParseExact(tail, "yyyyMMdd", CultureInfo.InvariantCulture);

                    return date.AddDays(_retentionDays) < DateTime.Now; // 20250814 에 90일을 더해도 오늘보다 이전 (= 90일 초과)
                })
                .ToList();

            if (expiredLogFiles is null || !expiredLogFiles.Any())
            {
                _logger.LogInformation($"CleanUpExpiredLogFiles - No expired files found in the log directory: {_rootLogDir}");
                return;
            }

            foreach (var file in expiredLogFiles)
            {
                if (File.Exists(file))
                {
                    File.Delete(file);

                    _logger.LogInformation($"CleanUpExpiredLogFiles - 파일 삭제 완료: {file}");
                }

                ////Path.GetFileNameWithoutExtension(logf) = "AirBridge-20250814"
                //var yyyyMMdd = Path.GetFileNameWithoutExtension(file).Substring(10, 8); // "20250814"
                //DateTime fileDate = DateTime.ParseExact(yyyyMMdd, "yyyyMMdd", CultureInfo.InvariantCulture);

                //// 보관일수 _retentionDays 을 초과한 만큼 옛날 파일이면 삭제
                //if (fileDate.AddDays(_retentionDays) < DateTime.Now)
                //{
                //    if (File.Exists(file))
                //    {
                //        File.Delete(file);

                //        _logger.LogInformation($"CleanUpLogFiles - 파일 삭제 완료: {file}");
                //    }
                //}
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, $"CleanUpExpiredLogFiles() 내부에서 에러 발생!: {ex.Message}");
            return;
        }
    }

    public IEnumerable<string>? GetAllFiles(string _dir)
    {
        try
        {
            return Directory.EnumerateFiles(_dir, "*", SearchOption.AllDirectories);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, $"Failed to enumerate files in directory: {_dir}");
            return Array.Empty<string>();
        }
    }

    private void NotifyMessage(int totalCount, List<string> successFiles, List<string> failedFiles, string _footer)
    {
        NotificationStyle _style = NotificationStyle.Information;
        string _title = "AirBridge 원장 중계 처리 알림";
        string _body = _templateBody;

        if (totalCount == 0) // Information -> 전송할 파일이 없는 경우
        {
            _style = NotificationStyle.Information;
            _title = $"({successFiles.Count}/{totalCount}) 🔵 " + _title; // 파란원
            _body = _body
                .Replace("{freeText}\n", "📂 처리할 파일 없음.")
                .Replace("{fileList}\n", "");
        }
        else if (totalCount == successFiles.Count) // Success -> 모든 파일이 성공했을 경우
        {
            _style = NotificationStyle.Success;
            _title = $"({successFiles.Count}/{totalCount}) 🟢 " + _title; // 초록원
            _body = _body
                .Replace("{freeText}", $"📂 총 {totalCount}개 파일 -> 성공 {successFiles.Count}개, 실패 {failedFiles.Count}개")
                .Replace("{fileList}", $"✅ **성공 목록**\n{string.Join("\n", successFiles)}");
        }
        else if (totalCount == failedFiles.Count) // Error -> 모든 파일이 실패했을 경우
        {
            _style = NotificationStyle.Error;
            _title = $"({successFiles.Count}/{totalCount}) [⛔ ACTION REQUIRED] " + _title; // 빨간금지아이콘
            _body = _body
                .Replace("{freeText}", $"📂 총 {totalCount}개 파일 -> 성공 {successFiles.Count}개, 실패 {failedFiles.Count}개")
                .Replace("{fileList}", $"❌ **실패 목록**\n{string.Join("\n", failedFiles)}");
        }
        else // Warning -> 부분 성공 (= 부분 실패)
        {
            _style = NotificationStyle.Warning;
            _title = $"({successFiles.Count}/{totalCount}) 🟢 " + _title; // 초록원
            _body = _body
                .Replace("{freeText}", $"📂 총 {totalCount}개 파일 -> 성공 {successFiles.Count}개, 실패 {failedFiles.Count}개")
                .Replace("{fileList}", $"✅ **성공 목록**\n{string.Join("\n", successFiles)}\n\n❌ **실패 목록**\n{string.Join("\n", failedFiles)}");
        }

        _body += _footer;

        _notifier.Notify(
            NotificationType.Lark_Webhook,
            new NotificationMessage(_style, _title, _body, null)
            );
    }
}