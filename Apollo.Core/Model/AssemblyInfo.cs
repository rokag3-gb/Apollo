namespace Apollo.Core;

public static class AssemblyInfo
{
    // string Name { get; set; } = "abc"; -> "property" (by relfection)
    // string Name => "abc"; -> "property". getter only
    // string Name = "abc"; -> "field". 그냥 변수 그 잡채

    public static string Title { get; } = "Apollo";
    public static string Product { get; } = "Apollo";
    public static string Description { get; } = "Fast, Light and Reliable Data Bridge Service";
    public static string Company { get; } = "Peachsoft";
    public static string Copyright { get; } = $"Copyright © {DateTime.Now.Year} {Company}. All rights reserved.";
    public static string Manager { get; } = "Jung Woo kim";
    public static int HeadVer_Major { get; } = 1;
    public static int HeadVer_YearMonth { get; } = 2509;
    public static int HeadVer_Build { get; } = 6;
    public static string HeadVer { get; } = $"{HeadVer_Major}.{HeadVer_YearMonth}.{HeadVer_Build}";

    /// <summary>
    /// GitSha: Git 7자리 short hash
    /// </summary>
    public static string GitSha { get; } = "d7f47ce";

    /// <summary>
    /// AssemblyVersion: CLR 어셈블리 바인딩, GAC 등에서 로딩 시 쓰이는 공식 버전
    /// 바꿀 때마다 호환성이 깨질 수 있어서 보통 메이저/마이너까지만 관리
    /// 환경에 따라 null일 수 있음
    /// E.g., "1.2508.0.0"
    /// </summary>
    public static string AssemblyVersion { get; } = $"{HeadVer_Major}.{HeadVer_YearMonth}.0.0";

    /// <summary>
    /// FileVersion (= AssemblyFileVersion): 파일 속성 (Windows 탐색기에서 보임)
    /// 빌드마다 build 값을 변경시켜도 문제 없음
    /// E.g., "1.2508.67"
    /// </summary>
    public static string FileVersion { get; } = $"{HeadVer_Major}.{HeadVer_YearMonth}.{HeadVer_Build}";

    /// <summary>
    /// ProductVersion: 파일 속성 (Windows 탐색기에서 보임)
    /// E.g., "1.2508.67"
    /// </summary>
    public static string ProductVersion { get; } = $"{HeadVer_Major}.{HeadVer_YearMonth}.{HeadVer_Build}";

    /// <summary>
    /// InformationVersion: 속성(Attribute) -> [assembly: AssemblyInformationalVersion("1.2.3-beta+abc123")]
    /// 사람이 보는 "표시용 버전". NuGet 패키지 버전, dotnet --info 같은 출력, Program.cs에서 InformationalVersion 읽을 때.
    /// E.g., "1.2508.64.0+30ad10bae9"
    /// </summary>
    public static string InformationVersion { get; } = $"{HeadVer_Major}.{HeadVer_YearMonth}.{HeadVer_Build}+{GitSha}";
}