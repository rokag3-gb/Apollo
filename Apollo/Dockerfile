# .NET 8 SDK를 사용하여 빌드
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# 프로젝트 파일을 복사하고 의존성 복원
COPY ["AirBridge.csproj", "./"]
RUN dotnet restore "AirBridge.csproj"

# 소스 코드를 복사하고 빌드
COPY . .
RUN dotnet build "AirBridge.csproj" -c Release -o /app/build

# 게시
FROM build AS publish
RUN dotnet publish "AirBridge.csproj" -c Release -o /app/publish

# 런타임 이미지
FROM mcr.microsoft.com/dotnet/runtime:8.0 AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "AirBridge.dll"]