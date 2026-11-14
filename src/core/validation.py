import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from datetime import datetime
import logging

class DataQualityLevel(Enum):
    """Data quality classification"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNUSABLE = "unusable"

@dataclass
class DataQualityReport:
    """Comprehensive data quality report"""
    symbol: str
    quality_level: DataQualityLevel
    total_records: int
    missing_records: int
    duplicate_records: int
    outliers: int
    date_gaps: int
    first_date: Optional[str]
    last_date: Optional[str]
    issues: List[str]
    score: float  # 0-100 quality score
    
    def is_usable(self) -> bool:
        """Check if data is usable for analysis"""
        return self.quality_level in [
            DataQualityLevel.EXCELLENT,
            DataQualityLevel.GOOD,
            DataQualityLevel.ACCEPTABLE
        ]
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'quality_level': self.quality_level.value,
            'total_records': self.total_records,
            'missing_records': self.missing_records,
            'duplicate_records': self.duplicate_records,
            'outliers': self.outliers,
            'date_gaps': self.date_gaps,
            'first_date': self.first_date,
            'last_date': self.last_date,
            'issues': self.issues,
            'score': self.score,
            'is_usable': self.is_usable()
        }

class DataValidator:
    """
    Enterprise data validation framework
    
    Validates:
    - Completeness (missing data)
    - Consistency (logical errors)
    - Accuracy (outliers, anomalies)
    - Timeliness (data freshness)
    """
    
    def __init__(self, logger: logging.Logger, config):
        self.logger = logger
        self.config = config
    
    def validate_price_data(self, df: pd.DataFrame, symbol: str) -> DataQualityReport:
        """
        Comprehensive validation of price data
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol
        
        Returns:
            DataQualityReport with detailed analysis
        """
        issues = []
        print(f"Validating data for {symbol}...")
        # Minimum required records
        min_required = self.config.get('data.min_history_days', 252)
        if len(df) < min_required:
            issues.append(f"Insufficient records: {len(df)} < {min_required}")
        
        # Missing values
        missing = df.isnull().sum().sum()
        if missing > 0:
            issues.append(f"{missing} missing values found")
        
        # Duplicate dates
        duplicates = df.index.duplicated().sum()
        if duplicates > 0:
            issues.append(f"{duplicates} duplicate dates found")
        
        # Date gaps
        date_gaps = self._find_date_gaps(df)
        if date_gaps > 5:
            issues.append(f"{date_gaps} significant date gaps detected")
        print(f"line 104")
        outliers = 0
        # Price validation
        if 'Close' in df.columns.tolist() or 'close' in df.columns.tolist(): 
            price_col = 'Close' if 'Close' in df.columns.tolist() else 'close'
            print(f"Validating prices in column: {price_col}")
            # Zero or negative prices
            invalid_prices = (df[price_col] <= 0).sum()
            if invalid_prices > 0:
                issues.append(f"{invalid_prices} invalid prices (<=0)")
            print(f"finished checking invalid prices")
            # Extreme price movements (>50% in one day)
            daily_returns = df[price_col].pct_change()
            outliers = (abs(daily_returns) > 0.5).sum()
            if outliers > 0:
                issues.append(f"{outliers} extreme price movements (>50%)")
            print(f"finished checking extreme price movements")
            # Price consistency (OHLC logic)
            if all(col in df.columns for col in ['Open', 'High', 'Low', 'Close']):
                inconsistent = self._check_ohlc_consistency(df)
                if inconsistent > 0:
                    issues.append(f"{inconsistent} OHLC inconsistencies")
            print(f"finished OHLC consistency check")

        print(f"finished price validation")
        # Volume validation
        if 'Volume' in df.columns.to_list() or 'volume' in df.columns.to_list():
            vol_col = 'Volume' if 'Volume' in df.columns.to_list() else 'volume'
            
            # Zero volume days
            zero_volume = (df[vol_col] == 0).sum()
            if zero_volume > int(len(df) * 0.1):  # >10%
                issues.append(
                    f"{zero_volume} zero volume days "
                    f"({zero_volume/len(df)*100:.1f}%)"
                )
            
            # Negative volume
            negative_volume = (df[vol_col] < 0).sum()
            if negative_volume > 0:
                issues.append(f"{negative_volume} negative volume entries")
        print(f"finished volume validation")
        # Calculate quality score (0-100)
        score = self._calculate_quality_score(
            len(df),
            missing,
            duplicates,
            date_gaps,
            outliers if 'Close' in df.columns else 0,
            len(issues)
        )
        print(f"calculated quality score: {score}")
        # Determine quality level
        quality_level = self._determine_quality_level(score)
        print(f"determined quality level: {quality_level.value}")
        # Create report
        report = DataQualityReport(
            symbol=symbol,
            quality_level=quality_level,
            total_records=len(df),
            missing_records=missing,
            duplicate_records=duplicates,
            outliers=outliers if 'Close' in df.columns else 0,
            date_gaps=date_gaps,
            first_date=df.index[0].strftime('%Y-%m-%d') if len(df) > 0 else None,
            last_date=df.index[-1].strftime('%Y-%m-%d') if len(df) > 0 else None,
            issues=issues,
            score=score
        )
        print(f"created data quality report")
        # Log quality issues
        if not report.is_usable():
            self.logger.warning(
                f"Poor data quality for {symbol}: "
                f"Level={quality_level.value}, Score={score:.1f}"
            )
        print(f"Completed validation for {symbol}. Quality Level: {quality_level.value}, Score: {score:.1f}")
        return report
    
    def _find_date_gaps(self, df: pd.DataFrame, max_gap_days: int = 7) -> int:
        """Find significant gaps in date series"""
        gaps = 0
        dates = df.index
        
        for i in range(1, len(dates)):
            days_diff = (dates[i] - dates[i-1]).days
            # Count gaps > 7 days (accounting for weekends/holidays)
            if days_diff > max_gap_days:
                gaps += 1
        
        return gaps
    
    def _check_ohlc_consistency(self, df: pd.DataFrame) -> int:
        """Check OHLC logical consistency"""
        print("Checking OHLC consistency...")
        inconsistent = 0
        
        # High should be >= Open, Close, Low
        inconsistent += (df['High'] < df['Open']).sum()
        inconsistent += (df['High'] < df['Close']).sum()
        inconsistent += (df['High'] < df['Low']).sum()
        
        # Low should be <= Open, Close, High
        inconsistent += (df['Low'] > df['Open']).sum()
        inconsistent += (df['Low'] > df['Close']).sum()
        inconsistent += (df['Low'] > df['High']).sum()
        print(f"Found {inconsistent} OHLC inconsistencies.")
        return inconsistent
    
    def _calculate_quality_score(
        self,
        total_records: int,
        missing: int,
        duplicates: int,
        gaps: int,
        outliers: int,
        num_issues: int
    ) -> float:
        """Calculate overall quality score (0-100)"""
        score = 100.0
        
        # Penalize based on issues
        if total_records > 0:
            score -= (missing / total_records) * 20  # Up to -20 for missing
            score -= (duplicates / total_records) * 15  # Up to -15 for duplicates
            score -= (outliers / total_records) * 10  # Up to -10 for outliers
        
        score -= min(gaps * 2, 20)  # -2 per gap, max -20
        score -= num_issues * 5  # -5 per issue type
        
        return max(0, min(100, score))
    
    def _determine_quality_level(self, score: float) -> DataQualityLevel:
        """Determine quality level from score"""
        if score >= 90:
            return DataQualityLevel.EXCELLENT
        elif score >= 75:
            return DataQualityLevel.GOOD
        elif score >= 60:
            return DataQualityLevel.ACCEPTABLE
        elif score >= 40:
            return DataQualityLevel.POOR
        else:
            return DataQualityLevel.UNUSABLE
    
    def validate_stock_list(self, stocks: List[dict]) -> bool:
        """Validate stock list structure"""
        if not stocks:
            self.logger.error("Stock list is empty")
            return False
        
        required_fields = ['symbol']
        
        for stock in stocks:
            if not all(field in stock for field in required_fields):
                self.logger.error(f"Stock missing required fields: {stock}")
                return False
            
            # Validate symbol format
            if not isinstance(stock['symbol'], str) or not stock['symbol']:
                self.logger.error(f"Invalid symbol: {stock.get('symbol')}")
                return False
        
        return True
