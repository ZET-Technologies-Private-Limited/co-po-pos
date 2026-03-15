"""
Marks validation and quality assurance
"""
from typing import List, Dict, Any, Tuple
import pandas as pd
from app.core.logging.system_logger import SystemLogger


class MarksValidationService:
    """Validate student marks data before processing"""
    
    def __init__(self):
        self.logger = SystemLogger("marks_validation")
    
    def validate_marks_dataframe(
        self,
        df: pd.DataFrame,
        expected_columns: List[str] = None
    ) -> Tuple[bool, List[str], pd.DataFrame]:
        """
        Validate marks dataframe
        
        Returns: (is_valid, errors, cleaned_df)
        """
        errors = []
        
        # Check if dataframe is empty
        if df.empty:
            errors.append("Dataframe is empty")
            return False, errors, df
        
        # Check required columns
        if expected_columns:
            missing_cols = [col for col in expected_columns if col not in df.columns]
            if missing_cols:
                errors.append(f"Missing columns: {missing_cols}")
        
        # Check for null values in critical columns
        critical_columns = ["student_id", "question_id", "marks_obtained"]
        for col in critical_columns:
            if col in df.columns and df[col].isnull().any():
                null_count = df[col].isnull().sum()
                errors.append(f"Found {null_count} null values in {col}")
        
        # Validate mark ranges
        if "marks_obtained" in df.columns and "total_marks" in df.columns:
            invalid_rows = df[
                (df["marks_obtained"] < 0) | 
                (df["marks_obtained"] > df["total_marks"])
            ]
            if not invalid_rows.empty:
                errors.append(
                    f"Found {len(invalid_rows)} rows with marks exceeding total"
                )
        
        # Check for duplicates
        if "student_id" in df.columns and "question_id" in df.columns:
            duplicates = df[df.duplicated(
                subset=["student_id", "question_id"],
                keep=False
            )]
            if not duplicates.empty:
                errors.append(
                    f"Found {len(duplicates)} duplicate student-question pairs"
                )
        
        # Clean dataframe
        cleaned_df = df.copy()
        
        # Remove rows with critical null values
        for col in critical_columns:
            if col in cleaned_df.columns:
                cleaned_df = cleaned_df.dropna(subset=[col])
        
        # Ensure marks are numeric
        if "marks_obtained" in cleaned_df.columns:
            cleaned_df["marks_obtained"] = pd.to_numeric(
                cleaned_df["marks_obtained"],
                errors="coerce"
            )
        
        is_valid = len(errors) == 0
        
        self.logger.info(
            "Marks validation completed",
            is_valid=is_valid,
            error_count=len(errors),
            rows_processed=len(cleaned_df)
        )
        
        return is_valid, errors, cleaned_df
    
    def validate_marks_range(
        self,
        marks: float,
        total_marks: float
    ) -> bool:
        """Validate single mark entry"""
        return 0 <= marks <= total_marks
    
    def detect_outliers(
        self,
        marks: List[float],
        method: str = "iqr"
    ) -> List[int]:
        """Detect outliers in mark distribution"""
        if not marks or len(marks) < 4:
            return []
        
        if method == "iqr":
            q1 = sorted(marks)[len(marks) // 4]
            q3 = sorted(marks)[3 * len(marks) // 4]
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outlier_indices = [
                i for i, mark in enumerate(marks)
                if mark < lower_bound or mark > upper_bound
            ]
            return outlier_indices
        
        elif method == "zscore":
            import numpy as np
            mean = np.mean(marks)
            std = np.std(marks)
            
            if std == 0:
                return []
            
            z_scores = np.abs((np.array(marks) - mean) / std)
            outlier_indices = [i for i, z in enumerate(z_scores) if z > 3]
            return outlier_indices
        
        return []
    
    def generate_validation_report(
        self,
        df: pd.DataFrame,
        total_expected_records: int = None
    ) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        report = {
            "total_records": len(df),
            "complete_records": len(df.dropna()),
            "null_records": len(df) - len(df.dropna()),
            "statistics": {}
        }
        
        if total_expected_records:
            report["expected_records"] = total_expected_records
            report["coverage_percentage"] = (len(df) / total_expected_records) * 100
        
        # Mark statistics
        if "marks_obtained" in df.columns:
            marks = pd.to_numeric(df["marks_obtained"], errors="coerce").dropna()
            report["statistics"] = {
                "mean": float(marks.mean()),
                "median": float(marks.median()),
                "std_dev": float(marks.std()),
                "min": float(marks.min()),
                "max": float(marks.max())
            }
        
        return report


# Global service instance
marks_validation_service = MarksValidationService()
