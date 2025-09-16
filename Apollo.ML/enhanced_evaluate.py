# -*- coding: utf-8 -*-
"""
회귀 모델 평가 모듈
다양한 회귀 평가 메트릭과 분석 기능을 제공합니다.
"""

import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    mean_absolute_percentage_error, median_absolute_error,
    explained_variance_score, max_error
)
from sklearn.model_selection import cross_val_score, TimeSeriesSplit, train_test_split
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

def load_model_and_data():
    """저장된 모델과 데이터를 로드합니다."""
    try:
        model = joblib.load('artifacts/model.joblib')
        scaler = joblib.load('artifacts/scaler.joblib')
        
        # 피처 엔지니어링된 데이터 로드
        df_preprocessed = pd.read_parquet('artifacts/enhanced_features.parquet')
        
        # 피처와 타겟 분리 (수치형 컬럼만)
        numeric_cols = df_preprocessed.select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = [col for col in numeric_cols if col not in ['plan_id', 'query_id', 'last_ms']]
        
        # 문자열 컬럼 제외 (스케일링할 수 없음)
        string_cols = df_preprocessed.select_dtypes(include=['object']).columns.tolist()
        feature_cols = [col for col in feature_cols if col not in string_cols]
        
        X_processed = df_preprocessed[feature_cols]
        y_processed = df_preprocessed['last_ms']
        
        feature_importance = pd.read_csv('artifacts/model_importance.csv')
        
        # 훈련 시와 동일한 분할 적용 (random_state=42)
        X_train, X_val, y_train, y_val = train_test_split(
            X_processed, y_processed, test_size=0.2, random_state=42
        )
        
        print("모델과 데이터 로드 완료")
        print(f"피처 엔지니어링된 데이터 크기: {df_preprocessed.shape}")
        print(f"훈련 데이터 크기: {X_train.shape}")
        print(f"검증 데이터 크기: {X_val.shape}")
        
        return model, scaler, X_train, X_val, y_train, y_val, feature_importance
    except Exception as e:
        print(f"데이터 로드 실패: {e}")
        return None, None, None, None, None, None, None

def calculate_regression_metrics(y_true, y_pred):
    """회귀 모델을 위한 다양한 평가 메트릭을 계산합니다."""
    
    # 기본 메트릭
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    
    # 추가 메트릭
    mape = mean_absolute_percentage_error(y_true, y_pred) * 100
    medae = median_absolute_error(y_true, y_pred)
    evs = explained_variance_score(y_true, y_pred)
    max_err = max_error(y_true, y_pred)
    
    # MAPE 대안 (0으로 나누기 방지)
    mape_alt = np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1e-8))) * 100
    
    # 상대적 오차
    relative_error = np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1e-8)))
    
    # 대칭 MAPE (Symmetric MAPE)
    smape = np.mean(2 * np.abs(y_true - y_pred) / (np.abs(y_true) + np.abs(y_pred) + 1e-8)) * 100
    
    # Mean Absolute Scaled Error (MASE) - 시계열 데이터용
    naive_forecast_error = np.mean(np.abs(np.diff(y_true)))
    mase = mae / (naive_forecast_error + 1e-8)
    
    # 잔차 통계
    residuals = y_true - y_pred
    residual_std = np.std(residuals)
    residual_mean = np.mean(residuals)
    
    # 정규성 검정 (Shapiro-Wilk)
    if len(residuals) <= 5000:  # 샘플 크기 제한
        shapiro_stat, shapiro_p = stats.shapiro(residuals)
    else:
        shapiro_stat, shapiro_p = np.nan, np.nan
    
    return {
        'mse': mse,
        'rmse': rmse,
        'mae': mae,
        'r2': r2,
        'mape': mape,
        'mape_alt': mape_alt,
        'medae': medae,
        'evs': evs,
        'max_error': max_err,
        'relative_error': relative_error,
        'smape': smape,
        'mase': mase,
        'residual_std': residual_std,
        'residual_mean': residual_mean,
        'shapiro_stat': shapiro_stat,
        'shapiro_p': shapiro_p
    }

def evaluate_model_performance(model, scaler, X, y, feature_cols, data_type=""):
    """모델 성능을 종합적으로 평가합니다."""
    
    print(f"=== {data_type} 데이터 성능 평가 ===")
    
    # 데이터 스케일링
    X_scaled = scaler.transform(X)
    
    # 예측
    y_pred = model.predict(X_scaled)
    
    # 메트릭 계산
    metrics = calculate_regression_metrics(y, y_pred)
    
    # 결과 출력
    print(f"\n📊 기본 메트릭:")
    print(f"  RMSE: {metrics['rmse']:.2f}")
    print(f"  MAE: {metrics['mae']:.2f}")
    print(f"  R²: {metrics['r2']:.4f}")
    print(f"  EVS: {metrics['evs']:.4f}")
    
    print(f"\n📈 오차 분석:")
    print(f"  MAPE: {metrics['mape']:.2f}%")
    print(f"  MAPE (대안): {metrics['mape_alt']:.2f}%")
    print(f"  SMAPE: {metrics['smape']:.2f}%")
    print(f"  MASE: {metrics['mase']:.4f}")
    print(f"  상대 오차: {metrics['relative_error']:.4f}")
    
    print(f"\n📋 분포 분석:")
    print(f"  중앙값 절대 오차: {metrics['medae']:.2f}")
    print(f"  최대 오차: {metrics['max_error']:.2f}")
    print(f"  잔차 평균: {metrics['residual_mean']:.2f}")
    print(f"  잔차 표준편차: {metrics['residual_std']:.2f}")
    
    # 정규성 검정 결과
    if not np.isnan(metrics['shapiro_p']):
        print(f"\n🔍 정규성 검정 (Shapiro-Wilk):")
        print(f"  통계량: {metrics['shapiro_stat']:.4f}")
        print(f"  p-value: {metrics['shapiro_p']:.4f}")
        if metrics['shapiro_p'] > 0.05:
            print("  ✅ 잔차가 정규분포를 따름 (p > 0.05)")
        else:
            print("  ❌ 잔차가 정규분포를 따르지 않음 (p ≤ 0.05)")
    
    return metrics, y_pred

def analyze_performance_by_ranges(y_true, y_pred):
    """성능을 구간별로 분석합니다."""
    
    print(f"\n=== 성능 구간별 분석 ===")
    
    # 구간 정의
    ranges = [
        (0, 1, "1ms 미만"),
        (1, 10, "1-10ms"),
        (10, 100, "10-100ms"),
        (100, 1000, "100ms-1s"),
        (1000, float('inf'), "1s 이상")
    ]
    
    for min_val, max_val, label in ranges:
        if max_val == float('inf'):
            mask = y_true >= min_val
        else:
            mask = (y_true >= min_val) & (y_true < max_val)
        
        if mask.sum() > 0:
            subset_y_true = y_true[mask]
            subset_y_pred = y_pred[mask]
            
            subset_r2 = r2_score(subset_y_true, subset_y_pred)
            subset_mae = mean_absolute_error(subset_y_true, subset_y_pred)
            subset_mape = np.mean(np.abs((subset_y_true - subset_y_pred) / np.maximum(subset_y_true, 1e-8))) * 100
            
            print(f"  {label}: R²={subset_r2:.4f}, MAE={subset_mae:.2f}, MAPE={subset_mape:.2f}% (n={mask.sum()})")

def cross_validation_analysis(model, scaler, X, y, cv_folds=5):
    """교차 검증을 통한 모델 안정성 분석"""
    
    print(f"\n=== 교차 검증 분석 ({cv_folds}-fold) ===")
    
    # 데이터 스케일링
    X_scaled = scaler.transform(X)
    
    # 시계열 분할 (데이터가 시간순으로 정렬되어 있다고 가정)
    tscv = TimeSeriesSplit(n_splits=cv_folds)
    
    # R² 점수 계산
    r2_scores = cross_val_score(model, X_scaled, y, cv=tscv, scoring='r2')
    mse_scores = -cross_val_score(model, X_scaled, y, cv=tscv, scoring='neg_mean_squared_error')
    mae_scores = -cross_val_score(model, X_scaled, y, cv=tscv, scoring='neg_mean_absolute_error')
    
    print(f"R² 점수: {r2_scores.mean():.4f} ± {r2_scores.std():.4f}")
    print(f"RMSE: {np.sqrt(mse_scores.mean()):.2f} ± {np.sqrt(mse_scores.std()):.2f}")
    print(f"MAE: {mae_scores.mean():.2f} ± {mae_scores.std():.2f}")
    
    # 안정성 평가
    cv_std = r2_scores.std()
    if cv_std < 0.01:
        stability = "🟢 매우 안정적"
    elif cv_std < 0.05:
        stability = "🟡 안정적"
    else:
        stability = "🟠 불안정"
    
    print(f"안정성: {stability} (CV std: {cv_std:.4f})")
    
    return {
        'r2_scores': r2_scores,
        'mse_scores': mse_scores,
        'mae_scores': mae_scores,
        'cv_std': cv_std
    }

def analyze_feature_importance(feature_importance, top_n=15):
    """피처 중요도 분석"""
    
    print(f"\n=== 피처 중요도 분석 (상위 {top_n}개) ===")
    
    top_features = feature_importance.head(top_n)
    
    for idx, row in top_features.iterrows():
        print(f"  {idx+1:2d}. {row['feature']:<25} : {row['importance']:.4f}")
    
    # 중요도 분포 분석
    total_importance = feature_importance['importance'].sum()
    top_n_importance = top_features['importance'].sum()
    coverage = (top_n_importance / total_importance) * 100
    
    print(f"\n상위 {top_n}개 피처의 중요도 비율: {coverage:.1f}%")

def residual_analysis(y_true, y_pred):
    """잔차 분석"""
    
    print(f"\n=== 잔차 분석 ===")
    
    residuals = y_true - y_pred
    
    # 잔차 통계
    print(f"잔차 평균: {residuals.mean():.4f}")
    print(f"잔차 표준편차: {residuals.std():.4f}")
    print(f"잔차 최솟값: {residuals.min():.4f}")
    print(f"잔차 최댓값: {residuals.max():.4f}")
    
    # 이상치 탐지 (IQR 방법)
    Q1 = residuals.quantile(0.25)
    Q3 = residuals.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    outliers = residuals[(residuals < lower_bound) | (residuals > upper_bound)]
    outlier_ratio = len(outliers) / len(residuals) * 100
    
    print(f"이상치 비율: {outlier_ratio:.2f}% ({len(outliers)}/{len(residuals)})")
    
    # 잔차와 예측값의 상관관계 (Heteroscedasticity 체크)
    correlation = np.corrcoef(residuals, y_pred)[0, 1]
    print(f"잔차-예측값 상관관계: {correlation:.4f}")
    
    if abs(correlation) > 0.3:
        print("  ⚠️  이분산성 의심 (상관관계 > 0.3)")
    else:
        print("  ✅ 등분산성 가정 만족")

def model_quality_assessment(metrics, cv_results=None):
    """모델 품질 종합 평가"""
    
    print(f"\n=== 모델 품질 종합 평가 ===")
    
    # R² 기반 성능 평가
    r2 = metrics['r2']
    if r2 >= 0.9:
        performance = "🟢 우수한 성능"
    elif r2 >= 0.7:
        performance = "🟡 양호한 성능"
    elif r2 >= 0.5:
        performance = "🟠 보통 성능"
    else:
        performance = "🔴 낮은 성능"
    
    print(f"성능: {performance} (R² = {r2:.4f})")
    
    # 정확도 평가 (MAPE 기준)
    mape = metrics['mape_alt']
    if mape < 10:
        accuracy = "🟢 매우 정확"
    elif mape < 20:
        accuracy = "🟡 정확"
    elif mape < 50:
        accuracy = "🟠 보통"
    else:
        accuracy = "🔴 부정확"
    
    print(f"정확도: {accuracy} (MAPE = {mape:.2f}%)")
    
    # 안정성 평가
    if cv_results and 'cv_std' in cv_results:
        cv_std = cv_results['cv_std']
        if cv_std < 0.01:
            stability = "🟢 매우 안정적"
        elif cv_std < 0.05:
            stability = "🟡 안정적"
        else:
            stability = "🟠 불안정"
        print(f"안정성: {stability} (CV std = {cv_std:.4f})")
    
    # 편향성 평가
    residual_mean = abs(metrics['residual_mean'])
    if residual_mean < 1:
        bias = "🟢 편향 없음"
    elif residual_mean < 10:
        bias = "🟡 경미한 편향"
    else:
        bias = "🟠 편향 있음"
    
    print(f"편향성: {bias} (잔차 평균 = {metrics['residual_mean']:.2f})")

def main():
    """메인 실행 함수"""
    
    print("=== 회귀 모델 평가 시작 ===")
    
    # 모델과 데이터 로드 (훈련/검증 분할 포함)
    model, scaler, X_train, X_val, y_train, y_val, feature_importance = load_model_and_data()
    
    if model is None:
        print("❌ 모델 로드 실패. 먼저 enhanced_train.py를 실행하세요.")
        return
    
    # 피처 컬럼명 추출
    feature_cols = X_train.columns.tolist()
    
    # 훈련 데이터 성능 평가
    print("\n" + "="*60)
    metrics_train, y_pred_train = evaluate_model_performance(
        model, scaler, X_train, y_train, feature_cols, "훈련"
    )
    
    # 검증 데이터 성능 평가
    print("\n" + "="*60)
    metrics_val, y_pred_val = evaluate_model_performance(
        model, scaler, X_val, y_val, feature_cols, "검증"
    )
    
    # 훈련/검증 성능 비교
    print(f"\n=== 훈련 vs 검증 성능 비교 ===")
    print(f"R² 점수: 훈련={metrics_train['r2']:.4f}, 검증={metrics_val['r2']:.4f}")
    print(f"RMSE: 훈련={metrics_train['rmse']:.2f}, 검증={metrics_val['rmse']:.2f}")
    print(f"MAE: 훈련={metrics_train['mae']:.2f}, 검증={metrics_val['mae']:.2f}")
    
    # Overfitting 체크
    r2_gap = abs(metrics_train['r2'] - metrics_val['r2'])
    if r2_gap < 0.05:
        print(f"✅ Overfitting 없음 (R² 차이: {r2_gap:.4f})")
    elif r2_gap < 0.1:
        print(f"⚠️  경미한 Overfitting (R² 차이: {r2_gap:.4f})")
    else:
        print(f"❌ Overfitting 의심 (R² 차이: {r2_gap:.4f})")
    
    # 구간별 성능 분석 (검증 데이터 기준)
    analyze_performance_by_ranges(y_val, y_pred_val)
    
    # 교차 검증 분석 (훈련 데이터 기준)
    cv_results = cross_validation_analysis(model, scaler, X_train, y_train)
    
    # 피처 중요도 분석
    analyze_feature_importance(feature_importance)
    
    # 잔차 분석 (검증 데이터 기준)
    residual_analysis(y_val, y_pred_val)
    
    # 모델 품질 종합 평가 (검증 데이터 기준)
    model_quality_assessment(metrics_val, cv_results)
    
    print(f"\n=== 평가 완료 ===")
    print(f"상세한 분석 결과가 출력되었습니다.")
    print(f"모델 성능을 개선하려면 피처 엔지니어링이나 하이퍼파라미터 튜닝을 고려하세요.")

if __name__ == "__main__":
    main()
