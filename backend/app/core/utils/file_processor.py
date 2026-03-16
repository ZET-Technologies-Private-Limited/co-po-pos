"""
File processing utilities for handling uploaded CSV, XLSX, and other file formats.
Provides unified interface for extracting and parsing data from various file types.
"""

import io
import csv
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Union, Optional, Tuple


async def parse_csv_file(content: bytes) -> List[Dict[str, Any]]:
    """
    Parse CSV file content and return list of row dictionaries.
    
    Args:
        content: Raw file bytes
        
    Returns:
        List of dictionaries where keys are column headers
        
    Raises:
        ValueError: If CSV parsing fails
    """
    try:
        # Try UTF-8 first
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        # Fall back to latin-1
        text = content.decode('latin-1', errors='replace')
    
    try:
        # Parse using csv.DictReader
        lines = text.strip().split('\n')
        if not lines or not lines[0].strip():
            raise ValueError("CSV file is empty")
        
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        
        if not rows:
            raise ValueError("No data rows found in CSV file")
        
        return rows
    except Exception as e:
        raise ValueError(f"CSV parsing failed: {str(e)}")


async def parse_excel_file(content: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse Excel file (.xlsx or .xls) and return data and sheet names.
    
    Args:
        content: Raw file bytes
        
    Returns:
        Tuple of (rows list, sheet names list)
        
    Raises:
        ValueError: If Excel parsing fails
    """
    try:
        import openpyxl
        from openpyxl.utils import get_column_letter
    except ImportError:
        # Fall back to pandas if openpyxl not available
        try:
            import pandas as pd
            df = pd.read_excel(io.BytesIO(content), sheet_name=0)
            rows = df.fillna('').to_dict('records')
            return rows, []
        except Exception as e:
            raise ValueError(f"Excel parsing failed (no openpyxl): {str(e)}")
    
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        sheet = wb.active
        
        if not sheet or sheet.max_row == 0:
            raise ValueError("Excel sheet is empty")
        
        # Get headers from first row
        headers = []
        for col_idx in range(1, sheet.max_column + 1):
            header = sheet.cell(row=1, column=col_idx).value
            headers.append(str(header or f"Column_{col_idx}").strip())
        
        # Parse data rows
        rows = []
        for row_idx in range(2, sheet.max_row + 1):
            row_data = {}
            for col_idx, header in enumerate(headers, 1):
                cell_value = sheet.cell(row=row_idx, column=col_idx).value
                row_data[header] = str(cell_value or "").strip()
            
            # Only add if row has at least one non-empty cell
            if any(row_data.values()):
                rows.append(row_data)
        
        if not rows:
            raise ValueError("No data rows found in Excel file")
        
        return rows, list(wb.sheetnames)
    
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Excel parsing failed: {str(e)}")


def _extract_question_from_line(raw_line: str) -> Optional[Dict[str, Any]]:
    line = re.sub(r"\s+", " ", str(raw_line or "")).strip()
    if not line:
        return None

    # Remove common leading labels like "Q1)", "1.", "Question 3:"
    line = re.sub(r"^(?:question\s*)?\d+[\)\.:\-]\s*", "", line, flags=re.IGNORECASE)
    line = re.sub(r"^[\-\*]\s*", "", line)

    marks = 5.0
    patterns = [
        r"\((\d+(?:\.\d+)?)\s*marks?\)$",
        r"\[(\d+(?:\.\d+)?)\s*marks?\]$",
        r"(?:marks?|m)\s*[:\-]?\s*(\d+(?:\.\d+)?)$",
        r"-\s*(\d+(?:\.\d+)?)\s*marks?$",
    ]
    for pattern in patterns:
        m = re.search(pattern, line, flags=re.IGNORECASE)
        if not m:
            continue
        try:
            marks = float(m.group(1))
        except Exception:
            marks = 5.0
        line = (line[: m.start()] + line[m.end() :]).strip(" -:;,.\t")
        break

    if len(line) < 6:
        return None

    return {
        "question_text": line,
        "marks": marks,
        "bloom_level": "understand",
        "co_code": None,
    }


def _questions_from_lines(lines: List[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in lines:
        item = _extract_question_from_line(raw)
        if item:
            rows.append(item)
    return rows


async def parse_text_question_file(content: bytes) -> List[Dict[str, Any]]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1", errors="replace")

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    rows = _questions_from_lines(lines)
    if not rows:
        raise ValueError("No recognizable question rows found in text file")
    return rows


async def parse_docx_question_file(content: bytes) -> List[Dict[str, Any]]:
    try:
        from docx import Document as DocxDocument
    except ImportError as e:
        raise ValueError(f"DOCX parsing requires python-docx: {str(e)}")

    try:
        doc = DocxDocument(io.BytesIO(content))
        lines = [p.text.strip() for p in doc.paragraphs if str(p.text or "").strip()]
        rows = _questions_from_lines(lines)
        if not rows:
            raise ValueError("No recognizable question rows found in DOCX file")
        return rows
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"DOCX parsing failed: {str(e)}")


async def parse_odt_question_file(content: bytes) -> List[Dict[str, Any]]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            xml_bytes = zf.read("content.xml")
    except Exception as e:
        raise ValueError(f"ODF parsing failed: invalid ODT/ODF archive ({str(e)})")

    try:
        root = ET.fromstring(xml_bytes)
        ns = {"text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}
        lines: List[str] = []
        for p in root.findall(".//text:p", ns):
            txt = "".join(p.itertext()).strip()
            if txt:
                lines.append(txt)

        rows = _questions_from_lines(lines)
        if not rows:
            raise ValueError("No recognizable question rows found in ODF document")
        return rows
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"ODF content parsing failed: {str(e)}")


async def parse_ods_file(content: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    try:
        import pandas as pd
        sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, engine="odf")
        if not sheets:
            raise ValueError("ODS workbook is empty")

        first_sheet_name = next(iter(sheets.keys()))
        df = sheets[first_sheet_name]
        rows = df.fillna("").to_dict("records")
        if not rows:
            raise ValueError("No data rows found in ODS file")
        return rows, list(sheets.keys())
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"ODS parsing failed: {str(e)}")


def _sniff_zip_file_type(content: bytes) -> Optional[str]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = set(zf.namelist())
            if "word/document.xml" in names:
                return "docx"
            if "xl/workbook.xml" in names:
                return "xlsx"
            if "mimetype" in names:
                try:
                    mt = zf.read("mimetype").decode("utf-8", errors="ignore").strip().lower()
                    if "opendocument.spreadsheet" in mt:
                        return "ods"
                    if "opendocument.text" in mt:
                        return "odt"
                except Exception:
                    pass
            if "content.xml" in names:
                # Generic ODF fallback when mimetype is missing.
                return "odt"
    except Exception:
        return None
    return None


def _infer_ext_from_content_type(content_type: Optional[str]) -> Optional[str]:
    ct = (content_type or "").lower().strip()
    if not ct:
        return None
    if "wordprocessingml" in ct:
        return "docx"
    if "opendocument.text" in ct:
        return "odt"
    if "opendocument.spreadsheet" in ct:
        return "ods"
    if ct in {"text/csv", "application/csv"}:
        return "csv"
    if ct == "text/plain":
        return "txt"
    if "msword" in ct:
        return "doc"
    if "spreadsheetml" in ct:
        return "xlsx"
    return None


async def parse_file_by_type(
    content: bytes, 
    filename: str,
    allowed_extensions: Optional[Tuple[str, ...]] = None,
    content_type: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    """
    Auto-detect file type and parse accordingly.
    
    Args:
        content: Raw file bytes
        filename: Original filename (used for type detection)
        
    Returns:
        Tuple of (rows, detected_format, metadata)
        
    Raises:
        ValueError: If file type is unsupported or parsing fails
    """
    filename_lower = (filename or "").lower()
    file_ext = filename_lower.split('.')[-1] if '.' in filename_lower else ""

    ext_aliases = {
        "dox": "docx",
        "dof": "docx",
        "do": "docx",
        "text": "txt",
        "xlsm": "xlsx",
    }
    if file_ext in ext_aliases:
        file_ext = ext_aliases[file_ext]
    
    metadata = {
        "original_filename": filename,
        "detected_format": None,
        "file_size_bytes": len(content),
        "encoding": "utf-8",
        "parsing_notes": []
    }

    allowed = tuple((allowed_extensions or ("csv", "xlsx", "xls")))
    allowed_set = {str(ext).lower().lstrip(".") for ext in allowed}

    if not file_ext:
        inferred = _infer_ext_from_content_type(content_type)
        if inferred:
            file_ext = inferred
            metadata["parsing_notes"].append(f"Detected extension from content-type: .{file_ext}")

    if file_ext not in allowed_set:
        sniffed = _sniff_zip_file_type(content)
        if sniffed and sniffed in allowed_set:
            file_ext = sniffed
            metadata["parsing_notes"].append(f"Detected extension from file signature: .{file_ext}")
    
    try:
        if file_ext not in allowed_set:
            supported = ", ".join(f".{ext}" for ext in sorted(allowed_set))
            raise ValueError(f"Unsupported file type: .{file_ext}. Supported: {supported}")

        if file_ext in ('csv',):
            rows = await parse_csv_file(content)
            metadata["detected_format"] = "CSV"
            return rows, "CSV", metadata
        
        elif file_ext in ('xlsx', 'xls'):
            rows, sheet_names = await parse_excel_file(content)
            metadata["detected_format"] = "Excel"
            metadata["sheet_names"] = sheet_names
            return rows, "Excel", metadata

        elif file_ext in ('ods',):
            rows, sheet_names = await parse_ods_file(content)
            metadata["detected_format"] = "ODS"
            metadata["sheet_names"] = sheet_names
            return rows, "ODS", metadata

        elif file_ext in ('docx',):
            rows = await parse_docx_question_file(content)
            metadata["detected_format"] = "DOCX"
            metadata["parsing_notes"].append("Questions extracted from DOCX paragraphs")
            return rows, "DOCX", metadata

        elif file_ext in ('doc',):
            rows = await parse_text_question_file(content)
            metadata["detected_format"] = "DOC"
            metadata["parsing_notes"].append("Legacy DOC parsed as text; validate extracted rows")
            return rows, "DOC", metadata

        elif file_ext in ('odt', 'odf'):
            rows = await parse_odt_question_file(content)
            metadata["detected_format"] = "ODF"
            metadata["parsing_notes"].append("Questions extracted from ODF text paragraphs")
            return rows, "ODF", metadata

        elif file_ext in ('txt',):
            rows = await parse_text_question_file(content)
            metadata["detected_format"] = "Text"
            metadata["parsing_notes"].append("Questions extracted line-by-line from text file")
            return rows, "Text", metadata
        
        else:
            supported = ", ".join(f".{ext}" for ext in sorted(allowed_set))
            raise ValueError(f"Unsupported file type: .{file_ext}. Supported: {supported}")
    
    except ValueError as e:
        metadata["error"] = str(e)
        raise
    except Exception as e:
        metadata["error"] = f"Unexpected error: {str(e)}"
        raise ValueError(f"File parsing error: {str(e)}")


def extract_question_data(row: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Extract question data from a spreadsheet row.
    
    Expected columns (case-insensitive, flexible naming):
    - question_text (or question, q_text, text)
    - marks (or marks, max_marks, points)
    - bloom_level (or bloom, level, bt_level)
    - co_code (or co, co_mapping, course_outcome)
    
    Args:
        row: Dictionary from parsed spreadsheet row
        
    Returns:
        Normalized question dictionary or None if invalid
    """
    if not row:
        return None
    
    # Normalize keys to lowercase
    norm_row = {k.lower().replace(' ', '_'): v for k, v in row.items()}
    
    # Extract fields with flexible key matching
    question_text = (
        norm_row.get('question_text') or 
        norm_row.get('question') or 
        norm_row.get('q_text') or 
        norm_row.get('text') or 
        ""
    ).strip()
    
    marks_str = (
        norm_row.get('marks') or 
        norm_row.get('max_marks') or 
        norm_row.get('points') or 
        "0"
    ).strip()
    
    bloom_level = (
        norm_row.get('bloom_level') or 
        norm_row.get('bloom') or 
        norm_row.get('level') or 
        norm_row.get('bt_level') or 
        "understand"
    ).strip().lower()
    
    co_code = (
        norm_row.get('co_code') or 
        norm_row.get('co') or 
        norm_row.get('co_mapping') or 
        norm_row.get('course_outcome') or 
        ""
    ).strip()
    
    # Validate
    if not question_text:
        return None
    
    try:
        marks = float(marks_str) if marks_str else 0.0
    except ValueError:
        marks = 0.0
    
    # Normalize bloom level
    bloom_map = {
        'remember': 'remember',
        'understand': 'understand',
        'apply': 'apply',
        'analyze': 'analyze',
        'evaluate': 'evaluate',
        'create': 'create',
        'l1': 'remember',
        'l2': 'understand',
        'l3': 'apply',
        'l4': 'analyze',
        'l5': 'evaluate',
        'l6': 'create',
    }
    bloom_level = bloom_map.get(bloom_level, 'understand')
    
    return {
        'question_text': question_text,
        'marks': marks,
        'bloom_level': bloom_level,
        'co_code': co_code if co_code else None
    }


def extract_marks_data(row: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Extract student marks data from spreadsheet row.
    
    Expected columns (case-insensitive):
    - student_id (or enrollment_no, roll_no, reg_no)
    - student_name (or name) [optional]
    - marks columns (can be Q1, Q2, or 1, 2, etc.)
    
    Args:
        row: Dictionary from parsed spreadsheet row
        
    Returns:
        Normalized marks dictionary or None if invalid
    """
    if not row:
        return None
    
    # Normalize keys
    norm_row = {k.lower().replace(' ', '_'): v for k, v in row.items()}
    
    # Extract student ID
    student_id = (
        norm_row.get('student_id') or 
        norm_row.get('enrollment_no') or 
        norm_row.get('roll_no') or 
        norm_row.get('reg_no') or 
        norm_row.get('id') or 
        ""
    ).strip()
    
    if not student_id:
        return None
    
    student_name = (
        norm_row.get('student_name') or 
        norm_row.get('name') or 
        ""
    ).strip()
    
    # Extract marks (Q1, Q2, or just digits)
    question_marks = {}
    for key, value in norm_row.items():
        if key.startswith('q') and len(key) > 1:
            try:
                q_num = int(key[1:])
                marks_val = float(value) if value else 0.0
                question_marks[q_num] = marks_val
            except (ValueError, IndexError):
                pass
        elif key.isdigit():
            try:
                q_num = int(key)
                marks_val = float(value) if value else 0.0
                question_marks[q_num] = marks_val
            except ValueError:
                pass
    
    return {
        'student_id': student_id,
        'student_name': student_name,
        'question_marks': question_marks
    }


def extract_attainment_data(row: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Extract CO attainment data from spreadsheet row.
    
    Expected columns (case-insensitive):
    - co_code (or co, outcome_code)
    - attainment_percentage (or percentage, attainment, pct)
    - attainment_level (or level, l1/l2/l3)
    
    Args:
        row: Dictionary from parsed spreadsheet row
        
    Returns:
        Normalized attainment dictionary or None if invalid
    """
    if not row:
        return None
    
    # Normalize keys
    norm_row = {k.lower().replace(' ', '_'): v for k, v in row.items()}
    
    # Extract CO code
    co_code = (
        norm_row.get('co_code') or 
        norm_row.get('co') or 
        norm_row.get('outcome_code') or 
        ""
    ).strip()
    
    if not co_code:
        return None
    
    # Extract percentage
    pct_str = (
        norm_row.get('attainment_percentage') or 
        norm_row.get('percentage') or 
        norm_row.get('attainment') or 
        norm_row.get('pct') or 
        "0"
    ).strip()
    
    try:
        attainment_percentage = float(pct_str)
    except ValueError:
        attainment_percentage = 0.0
    
    # Clamp to 0-100
    attainment_percentage = max(0, min(100, attainment_percentage))
    
    # Extract level
    level_str = (
        norm_row.get('attainment_level') or 
        norm_row.get('level') or 
        ""
    ).strip().lower()
    
    # Infer level from percentage if not provided
    if not level_str:
        if attainment_percentage >= 70:
            level_str = 'level 3'
        elif attainment_percentage >= 60:
            level_str = 'level 2'
        else:
            level_str = 'level 1'
    
    return {
        'co_code': co_code,
        'attainment_percentage': attainment_percentage,
        'attainment_level': level_str
    }


def validate_question_collection(questions: List[Dict[str, Any]]) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Validate a collection of extracted questions.
    
    Args:
        questions: List of question dictionaries
        
    Returns:
        Tuple of (is_valid, validation_message, validated_questions)
    """
    if not questions:
        return False, "No questions to validate", []
    
    validated = []
    errors = []
    
    for idx, q in enumerate(questions, 1):
        if not isinstance(q, dict):
            errors.append(f"Row {idx}: Not a dictionary")
            continue
        
        if not q.get('question_text', '').strip():
            errors.append(f"Row {idx}: Missing question_text")
            continue
        
        if not isinstance(q.get('marks'), (int, float)) or q['marks'] < 0:
            errors.append(f"Row {idx}: Invalid marks (must be positive number)")
            continue
        
        validated.append(q)
    
    is_valid = len(validated) > 0 and len(errors) == 0
    message = f"Validated {len(validated)}/{len(questions)} questions"
    
    if errors:
        message += f"\nWarnings/Errors:\n" + "\n".join(errors[:5])
        if len(errors) > 5:
            message += f"\n...and {len(errors) - 5} more"
    
    return is_valid, message, validated


def validate_marks_collection(marks_list: List[Dict[str, Any]]) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Validate a collection of extracted student marks.
    
    Args:
        marks_list: List of marks dictionaries
        
    Returns:
        Tuple of (is_valid, validation_message, validated_marks)
    """
    if not marks_list:
        return False, "No marks to validate", []
    
    validated = []
    errors = []
    
    for idx, m in enumerate(marks_list, 1):
        if not isinstance(m, dict):
            errors.append(f"Row {idx}: Not a dictionary")
            continue
        
        if not m.get('student_id', '').strip():
            errors.append(f"Row {idx}: Missing student_id")
            continue
        
        if not m.get('question_marks'):
            errors.append(f"Row {idx}: No question marks found")
            continue
        
        validated.append(m)
    
    is_valid = len(validated) > 0 and len(errors) == 0
    message = f"Validated {len(validated)}/{len(marks_list)} student records"
    
    if errors:
        message += f"\nWarnings/Errors:\n" + "\n".join(errors[:5])
        if len(errors) > 5:
            message += f"\n...and {len(errors) - 5} more"
    
    return is_valid, message, validated
