
# AirBridge

AirBridge는 다양한 소스(로컬, Azure Blob 등)에서 파일을 주기적으로 동기화하고, 알림(예: Lark, Email, SMS)을 전송하는 .NET 8 기반의 확장 가능한 콘솔 애플리케이션입니다.
Cronos 라이브러리를 활용하여 크론 스케줄링을 정밀하게 지원하며, YAML 기반의 설정과 DI(의존성 주입) 구조로 유연한 확장성을 제공합니다.

---

## 주요 기능

- 크론 스케줄링: Cronos 라이브러리로 초 단위까지 정밀한 스케줄 지원
- 파일 감시: FileWatcher를 사용한 near-realtime 로컬 파일 감시 및 검사
- YAML 설정: 동작 방식, 소스/타겟, 알림 채널 등 모든 설정을 YAML로 관리
- 다양한 소스/타겟 지원: 로컬 경로, Azure Blob SFTP 등
- 알림 시스템: Lark, Email, SMS 등 다양한 채널로 작업 결과 알림
- DI 기반 확장성: Microsoft.Extensions.Hosting 및 DI 컨테이너 활용
- 로깅: 콘솔 기반의 심플한 로깅 지원

---

## 설치 및 의존성

### 필수

- .NET 8 SDK

### 주요 NuGet 패키지

- [Cronos](https://github.com/HangfireIO/Cronos) (스케줄링)
- Microsoft.Extensions.Hosting (호스팅/DI)
- Newtonsoft.Json (JSON 처리)
- SSH.NET (SFTP 지원)
- YamlDotNet (YAML 파싱)

```shell
dotnet add package Cronos --version 0.11.0
```

---

## 프로젝트 구조


```
AirBridge.sln
├── AirBridge/                # 메인 실행 프로젝트
│   ├── Program.cs            # 진입점, DI/호스트 구성
│   ├── Scheduler/
│   │   ├── CronPollingService.cs  # 크론 스케줄러 서비스
│   └── ...
├── AirBridge.Core/           # 핵심 라이브러리
│   ├── Yaml/                 # 설정 로더 및 모델
│   ├── Notification/         # 알림 채널/팩토리/서비스
│   ├── SFTP/                 # Azure Blob SFTP 연동
│   ├── Credential/           # 시크릿/자격증명
│   ├── FileWatcher/          # 파일 감시 구현체
│   ├── Model/                # 데이터 모델
│   └── ...
└── AirBridge.Awaker/         # (예정) 감시 및 자동 재시작 콘솔 앱
    └── ...
```

---

## AirBridge.Awaker (예정)

**AirBridge.Awaker**는 AirBridge 프로세스의 상태를 감시하고, 프로세스가 없거나 응답이 없을 경우 자동으로 AirBridge를 재실행하는 별도의 콘솔 응용 프로그램입니다.

- 독립 실행형 감시/재시작 도구 (Windows 서비스 또는 데몬 형태로도 확장 가능)
- AirBridge의 안정적 운영을 위한 헬스체크 및 자동 복구 역할
- 향후 다양한 감시 정책(프로세스, 포트, 응답 등) 및 알림 연동도 확장 가능

> **예정된 구조**
> - AirBridge.Awaker/
>   - Program.cs (감시/재시작 로직)
>   - ...

---

---

## 설정 예시 (`BaseDirectory + /AirBridgeConfig.yaml`)

```yaml
schedule:
  cron_expression:
  - 0/5 * * * * *
  - 0/8 * * * * *
  time_zone: Korea Standard Time

source:
  type: mounted_path
  mounted_path:
    path: ~/ledger/root/

target:
  type: azure_blob_sftp
  azure_blob_sftp:
    host: <your_storage_account>.blob.core.windows.net
    port: 22
    username: <your_local_user>
    password: <your_password>
```

---

## 작동 방식

1. YAML 설정 로드: 실행 시 `AirBridgeConfig.yaml`을 읽어 전체 동작을 설정합니다.
2. DI/호스트 구성: .NET Generic Host로 서비스 등록 및 DI 구성
3. 스케줄링: `CronPollingService`가 Cronos로 스케줄을 파싱, 주기적으로 작업 실행 -> `FileWatcher`
4. 파일 감시: `FileWatcher`가 설정된 폴더를 near-realtime으로 감시하여 파일 변경 감지
5. 파일 동기화: 소스에서 타겟(Azure Blob 등)으로 파일을 동기화
6. 알림 전송: 작업 결과를 Lark, Email, SMS 등으로 전송

---

## 파일 감시 기능

AirBridge는 `FileWatcher` 구현체에서 로컬 폴더의 파일 변경을 near-realtime으로 감시하고 검사합니다. Linux(RHEL) / Windows 를 모두 커버합니다.

### 주요 특징

- **폴링 기반 감시**: 설정된 간격(기본 2초)으로 폴더를 주기적으로 검사
- **이벤트 기반 처리**: 파일 생성, 변경, 삭제 이벤트를 개별적으로 처리
- **파일 유효성 검사**: 파일 확장자, 크기, 내용 형식 검증
- **설정 기반 동작**: YAML 설정으로 감시 폴더, 간격, 파일 형식 등 제어

---

## 확장 및 커스터마이징

- 알림 채널 추가: `INotificationSender` 구현체 추가 및 DI 등록.<br>
_(Email 및 SMS에 대한 발송 구현체는 아직 작업 전)_
- 새로운 소스/타겟: YamlModel 및 서비스 구현 확장
- 설정 파일만 변경해 다양한 배포/운영 시나리오 적용 가능

---

## 라이선스

MIT License