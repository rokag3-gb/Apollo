import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 데이터 로드
print("=== 데이터셋 분석 ===")
df_raw = pd.read_parquet('artifacts/collected_plans.parquet')
df_feat = pd.read_parquet('artifacts/features.parquet')

print(f"\n=== Raw 데이터셋 ===")
print(f"총 행수: {len(df_raw):,}")
print(f"컬럼: {list(df_raw.columns)}")

print(f"\n=== 타겟 변수 (last_ms) 통계 ===")
print(df_raw['last_ms'].describe())

print(f"\n=== 타겟 변수 분포 ===")
print(f"최소값: {df_raw['last_ms'].min():.2f}ms")
print(f"최대값: {df_raw['last_ms'].max():.2f}ms")
print(f"중앙값: {df_raw['last_ms'].median():.2f}ms")
print(f"표준편차: {df_raw['last_ms'].std():.2f}ms")
print(f"분산: {df_raw['last_ms'].var():.2f}ms²")

# 타겟 변수 분포 분석
print(f"\n=== 타겟 변수 분포 세부 분석 ===")
print(f"0-1ms: {len(df_raw[df_raw['last_ms'] < 1]):,} ({len(df_raw[df_raw['last_ms'] < 1])/len(df_raw)*100:.1f}%)")
print(f"1-100ms: {len(df_raw[(df_raw['last_ms'] >= 1) & (df_raw['last_ms'] < 100)]):,} ({len(df_raw[(df_raw['last_ms'] >= 1) & (df_raw['last_ms'] < 100)])/len(df_raw)*100:.1f}%)")
print(f"100-1000ms: {len(df_raw[(df_raw['last_ms'] >= 100) & (df_raw['last_ms'] < 1000)]):,} ({len(df_raw[(df_raw['last_ms'] >= 100) & (df_raw['last_ms'] < 1000)])/len(df_raw)*100:.1f}%)")
print(f"1000ms+: {len(df_raw[df_raw['last_ms'] >= 1000]):,} ({len(df_raw[df_raw['last_ms'] >= 1000])/len(df_raw)*100:.1f}%)")

print(f"\n=== 피처 데이터셋 ===")
print(f"총 행수: {len(df_feat):,}")
print(f"피처 수: {df_feat.shape[1]-2}")

print(f"\n=== 피처별 기본 통계 ===")
print("피처 목록:")
for col in df_feat.columns:
    if col not in ['plan_id', 'last_ms']:
        print(f"  - {col}")

print(f"\n=== 피처별 분산 분석 ===")
feature_cols = [col for col in df_feat.columns if col not in ['plan_id', 'last_ms']]
for col in feature_cols[:10]:  # 처음 10개 피처만
    var = df_feat[col].var()
    print(f"  {col}: 분산 = {var:.4f}")

print(f"\n=== 타겟 변수와 피처 간 상관관계 (상위 10개) ===")
# 숫자형 피처만 선택
numeric_cols = df_feat.select_dtypes(include=[np.number]).columns
correlations = df_feat[numeric_cols].corr()['last_ms'].abs().sort_values(ascending=False)[:11]
print(correlations)

print(f"\n=== 피처별 분산 분석 (전체) ===")
for col in feature_cols:
    try:
        var = df_feat[col].var()
        print(f"  {col}: 분산 = {var:.4f}")
    except:
        print(f"  {col}: 분산 계산 불가 (문자열 데이터)")

print(f"\n=== 데이터 품질 분석 ===")
print(f"결측값이 있는 피처:")
for col in df_feat.columns:
    missing = df_feat[col].isnull().sum()
    if missing > 0:
        print(f"  {col}: {missing}개 ({missing/len(df_feat)*100:.1f}%)")

print(f"\n=== 타겟 변수 로그 변환 후 분포 ===")
# 0보다 큰 값만 로그 변환
df_feat['last_ms_log'] = np.log1p(df_feat['last_ms'])
print(f"로그 변환 후 표준편차: {df_feat['last_ms_log'].std():.2f}")
print(f"로그 변환 후 분산: {df_feat['last_ms_log'].var():.2f}")
