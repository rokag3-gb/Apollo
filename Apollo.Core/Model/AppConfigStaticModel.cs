using Apollo.Core.Model;
using Apollo.Core.Helper;
using Apollo.Core.Dto;

namespace Apollo.Core;

public static class Conf
{
    public static AppConfig Current { get; set; } = new AppConfig();

    public static NetSnapshot CurrentNetInfo { get; set; } = new();
}