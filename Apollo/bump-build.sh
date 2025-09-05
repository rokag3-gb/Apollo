#!/bin/bash

# 기본값: 스크립트 루트 기준 상위 디렉토리의 AirBridge.Core/AssemblyInfo.cs
ASSEMBLY_INFO_PATH="${1:-$(dirname "$0")/../AirBridge.Core/Model/AssemblyInfo.cs}"

echo "Updating AssemblyInfo at $ASSEMBLY_INFO_PATH"

# 파일 존재 확인
if [ ! -f "$ASSEMBLY_INFO_PATH" ]; then
    echo "AssemblyInfo.cs not found at $ASSEMBLY_INFO_PATH" >&2
    exit 1
fi

# 현재 날짜 yyMM (예: 2508)
YEAR_MONTH=$(date +%y%m)

# 기존 값 추출
OLD_YEAR_MONTH=$(grep -o 'HeadVer_YearMonth.*=.*[0-9]*;' "$ASSEMBLY_INFO_PATH" | grep -o '[0-9]*' || echo "$YEAR_MONTH")
OLD_BUILD=$(grep -o 'HeadVer_Build.*=.*[0-9]*;' "$ASSEMBLY_INFO_PATH" | grep -o '[0-9]*' || echo "0")

# Build 번호 계산
if [ "$YEAR_MONTH" != "$OLD_YEAR_MONTH" ]; then
    NEW_BUILD=1
else
    NEW_BUILD=$((OLD_BUILD + 1))
fi

# Git SHA (7자리 short hash)
GIT_SHA=$(git rev-parse --short=7 HEAD 2>/dev/null || echo "unknown")

# 임시 파일 생성
TEMP_FILE=$(mktemp)

# 파일을 줄별로 읽어서 내용 업데이트
while IFS= read -r line || [ -n "$line" ]; do
    # HeadVer_YearMonth 업데이트
    if [[ $line =~ HeadVer_YearMonth.*=.*[0-9]*\; ]]; then
        echo "    public static int HeadVer_YearMonth { get; } = $YEAR_MONTH;"
    # HeadVer_Build 업데이트
    elif [[ $line =~ HeadVer_Build.*=.*[0-9]*\; ]]; then
        echo "    public static int HeadVer_Build { get; } = $NEW_BUILD;"
    # GitSha 업데이트
    elif [[ $line =~ GitSha.*=.*\".*\"\; ]]; then
        echo "    public static string GitSha { get; } = \"$GIT_SHA\";"
    else
        echo "$line"
    fi
done < "$ASSEMBLY_INFO_PATH" > "$TEMP_FILE"

# 파일 끝의 연속된 빈 줄들을 제거하고 정확히 하나의 개행만 유지
# awk를 사용하여 파일 끝의 빈 줄들을 완전히 제거
awk 'BEGIN{RS="\n"; ORS="\n"} {lines[++count] = $0} END{
    # 마지막 빈 줄들 제거
    while(count > 0 && lines[count] == "") count--;
    # 모든 줄 출력 (마지막 빈 줄 없이)
    for(i=1; i<=count; i++) print lines[i];
}' "$TEMP_FILE" > "$TEMP_FILE.tmp" && mv "$TEMP_FILE.tmp" "$TEMP_FILE"

# 원본 파일에 덮어쓰기
mv "$TEMP_FILE" "$ASSEMBLY_INFO_PATH"

echo "Updated -> YearMonth=$YEAR_MONTH, Build=$NEW_BUILD, GitSha=$GIT_SHA"