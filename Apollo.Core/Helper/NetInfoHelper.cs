using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using Apollo.Core.Dto;

namespace Apollo.Core.Helper;

public class NetInfoHelper
{
    // 재사용 가능한 HttpClient (AOT/JIT 공통). 타임아웃은 각 요청에서 CTS로 따로 걸어줌.
    private readonly HttpClient _http = new HttpClient(new SocketsHttpHandler
    {
        PooledConnectionLifetime = TimeSpan.FromMinutes(5),
        AutomaticDecompression = System.Net.DecompressionMethods.None
    });

    /// <summary>호스트네임</summary>
    private string GetHostName() => Dns.GetHostName();

    /// <summary>사설 IPv4의 "대표" 주소를 구함(없으면 UDP 로컬 바인드 추론, 그것도 실패하면 null)</summary>
    private IPAddress? GetPrimaryPrivateIPv4()
    {
        foreach (var ni in GetUsableInterfaces())
        {
            var (v4s, _) = GetUnicastIPs(ni);
            var ip = v4s.FirstOrDefault(IsPrivateIPv4);
            if (ip != null) return ip;
        }

        // 사설대역이 아닌데도 "내가 쓰는" 로컬 IPv4가 필요한 경우: UDP 로컬 바인딩 기법
        // 실제 패킷은 전송되지 않으나, OS가 라우팅을 위해 로컬 주소를 할당함.
        try
        {
            using var socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
            // 198.18.0.1: RFC 2544 테스트넷(전송 안 함). 라우팅이 없으면 실패할 수 있음.
            socket.Connect(new IPEndPoint(IPAddress.Parse("198.18.0.1"), 65530));
            if (socket.LocalEndPoint is IPEndPoint ep)
                return ep.Address;
        }
        catch { /* 무시: 오프라인/라우팅없음 환경 */ }

        return null;
    }

    /// <summary>사설 IPv6의 "대표" 주소를 구함 (없으면 null)</summary>
    private IPAddress? GetPrimaryPrivateIPv6()
    {
        foreach (var ni in GetUsableInterfaces())
        {
            var (_, v6s) = GetUnicastIPs(ni);
            var ip = v6s.FirstOrDefault(IsPrivateIPv6);
            if (ip != null) return ip;
        }
        return null;
    }

    /// <summary>활성화된 NIC 중 게이트웨이가 있는(=기본 라우팅 후보) 인터페이스를 우선 반환</summary>
    private IEnumerable<NetworkInterface> GetUsableInterfaces()
    {
        return NetworkInterface.GetAllNetworkInterfaces()
            .Where(ni =>
                ni.OperationalStatus == OperationalStatus.Up &&
                ni.NetworkInterfaceType != NetworkInterfaceType.Loopback &&
                ni.NetworkInterfaceType != NetworkInterfaceType.Tunnel)
            // 게이트웨이 있는 인터페이스 우선
            .OrderByDescending(ni => ni.GetIPProperties().GatewayAddresses.Any())
            // 인터페이스 메트릭 낮은 것(선호) 우선
            .ThenBy(ni => ni.GetIPProperties().GetIPv4Properties()?.Index ?? int.MaxValue);
    }

    private (List<IPAddress> v4, List<IPAddress> v6) GetUnicastIPs(NetworkInterface ni)
    {
        var props = ni.GetIPProperties();
        var v4 = new List<IPAddress>();
        var v6 = new List<IPAddress>();

        foreach (var ua in props.UnicastAddresses)
        {
            if (ua.Address.AddressFamily == AddressFamily.InterNetwork)
            {
                if (!IPAddress.IsLoopback(ua.Address))
                    v4.Add(ua.Address);
            }
            else if (ua.Address.AddressFamily == AddressFamily.InterNetworkV6)
            {
                if (!IPAddress.IsLoopback(ua.Address))
                    v6.Add(ua.Address);
            }
        }
        return (v4, v6);
    }

    private bool IsPrivateIPv4(IPAddress ip)
    {
        if (ip.AddressFamily != AddressFamily.InterNetwork) return false;
        var b = ip.GetAddressBytes();
        // 10.0.0.0/8
        if (b[0] == 10) return true;
        // 172.16.0.0/12 (172.16~172.31)
        if (b[0] == 172 && b[1] >= 16 && b[1] <= 31) return true;
        // 192.168.0.0/16
        if (b[0] == 192 && b[1] == 168) return true;
        // (옵션) CGNAT 100.64.0.0/10 -> 외부 공개는 아니므로 내부 취급해도 실무에서 유용
        if (b[0] == 100 && (b[1] & 0xC0) == 0x40) return true; // 100.64~100.127
        return false;
    }

    private bool IsPrivateIPv6(IPAddress ip)
    {
        if (ip.AddressFamily != AddressFamily.InterNetworkV6) return false;
        var b = ip.GetAddressBytes();
        // Unique Local Address: fc00::/7 (fc00~fdff)
        return (b[0] & 0xFE) == 0xFC;
        // 참고: fe80::/10 (링크 로컬)은 LAN 범위 라우팅에 적합하지 않아 제외함.
    }

    /// <summary>
    /// 공인 IPv4 주소 조회 (외부 서비스 다중 시도). 성공 시 IPAddress 반환, 실패 시 null
    /// </summary>
    private async Task<IPAddress?> GetPublicIPv4Async(CancellationToken cancel = default)
    {
        string[] endpoints =
        {
            "https://api.ipify.org",        // 순수 텍스트
            "https://checkip.amazonaws.com",// 순수 텍스트
            "https://ifconfig.me/ip",       // 순수 텍스트
            "https://icanhazip.com"         // 순수 텍스트
        };

        foreach (var url in endpoints)
        {
            try
            {
                using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancel);
                cts.CancelAfter(TimeSpan.FromSeconds(2)); // 엔드포인트별 타임아웃

                var s = await _http.GetStringAsync(url, cts.Token).ConfigureAwait(false);
                var line = s.Trim();
                if (IPAddress.TryParse(line, out var ip) && ip.AddressFamily == AddressFamily.InterNetwork)
                    return ip;
            }
            catch
            {
                // 무시하고 다음 엔드포인트 시도
            }
        }
        return null;
    }

    public async Task<NetSnapshot> SnapshotAsync(CancellationToken cancel = default)
    {
        var host = GetHostName();
        var p4 = GetPrimaryPrivateIPv4();
        var p6 = GetPrimaryPrivateIPv6();
        var pub4 = await GetPublicIPv4Async(cancel).ConfigureAwait(false);

        //Console.WriteLine($"SnapshotAsync() 내부에서 NetInfo 불러오기 성공! - host: {host}, private ipv4: {p4}, private ipv6: {p6}, public ipv4: {pub4}");

        return new NetSnapshot(host, p4, p6, pub4);
    }
}