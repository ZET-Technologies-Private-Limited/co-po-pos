/**
 * File Upload & Export Utilities (SF-43 to SF-50)
 * File validation, naming, and export management
 */

// SF-43: File type validation
export const ALLOWED_FILE_TYPES = {
  EXCEL: ['.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
  PDF: ['.pdf', 'application/pdf'],
  CSV: ['.csv', 'text/csv'],
} as const;

export const validateFileType = (file: File, allowedType: 'EXCEL' | 'PDF' | 'CSV'): boolean => {
  const allowed = ALLOWED_FILE_TYPES[allowedType] as readonly string[];
  const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
  return allowed.includes(fileExt) || allowed.includes(file.type);
};

export const getFileTypeError = (fileName: string, expected: string): string => {
  const ext = '.' + fileName.split('.').pop()?.toLowerCase();
  return `Invalid file type: ${ext}. Only ${expected} files are accepted.`;
};

// SF-44: File size limit (10 MB)
export const MAX_FILE_SIZE_MB = 10;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export const validateFileSize = (file: File): boolean => {
  return file.size <= MAX_FILE_SIZE_BYTES;
};

export const getFileSizeError = (fileSizeMB: number): string => {
  return `File size exceeds limit. Maximum ${MAX_FILE_SIZE_MB} MB allowed (yours: ${fileSizeMB.toFixed(2)} MB)`;
};

export const getFileSizeInMB = (bytes: number): number => {
  return bytes / (1024 * 1024);
};

// SF-45: Upload progress line
export const formatUploadProgress = (loaded: number, total: number): string => {
  const percent = Math.round((loaded / total) * 100);
  return `Uploading... ${percent}%`;
};

export const shouldShowUploadProgress = (fileSizeBytes: number): boolean => {
  return fileSizeBytes > 1024 * 1024; // > 1 MB
};

// SF-46: Generated file naming
export const generateFileName = (
  type: 'CO_Attainment' | 'PO_Attainment' | 'PO_PSO_Mapping' | 'marks_submission' | 'audit_report',
  courseCode: string,
  academicYear: string,
  term?: string
): string => {
  const timestamp = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
  const termSuffix = term ? `_${term}` : '';
  return `${type}_${courseCode}_${academicYear}${termSuffix}_${timestamp}.pdf`;
};

// SF-47: Download link expiry
export const LINK_EXPIRY_HOURS = 24;

export const formatLinkExpiry = (createdAt: Date): string => {
  const expiresAt = new Date(createdAt.getTime() + LINK_EXPIRY_HOURS * 60 * 60 * 1000);
  const now = new Date();
  const hoursRemaining = Math.ceil((expiresAt.getTime() - now.getTime()) / (60 * 60 * 1000));

  if (hoursRemaining <= 0) return 'Link expired';
  if (hoursRemaining === 1) return 'Link expires in 1 hour';
  if (hoursRemaining < 24) return `Link expires in ${hoursRemaining} hours`;

  const daysRemaining = Math.ceil(hoursRemaining / 24);
  return `Link expires in ${daysRemaining} day${daysRemaining > 1 ? 's' : ''}`;
};

export const isLinkExpired = (createdAt: Date): boolean => {
  const expiresAt = new Date(createdAt.getTime() + LINK_EXPIRY_HOURS * 60 * 60 * 1000);
  return new Date() > expiresAt;
};

// SF-48: PDF watermark text
export const getPDFWatermark = (deptName: string, academicYear: string): string => {
  return `Confidential — ${deptName} — AY ${academicYear}`;
};

// SF-49: Excel date formatting
export const formatExcelDate = (date: Date): string => {
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();
  return `${day}-${month}-${year}`;
};

// SF-50: Re-upload handling
export interface UploadDiff {
  newRows: number;
  updatedRows: number;
  unchangedRows: number;
  conflictRows: number;
}

export const calculateUploadDiff = (
  newData: Record<string, any>[],
  existingData: Record<string, any>[],
  keyField: string = 'id'
): UploadDiff => {
  const newIds = new Set(newData.map(r => r[keyField]));
  const existingIds = new Set(existingData.map(r => r[keyField]));

  const newRows = Array.from(newIds).filter(id => !existingIds.has(id)).length;
  const unchangedRows = Array.from(newIds).filter(id => existingIds.has(id)).length;
  const conflictRows = 0; // Would need deeper comparison

  return {
    newRows,
    updatedRows: unchangedRows,
    unchangedRows: 0,
    conflictRows,
  };
};

export const formatReuploadMessage = (diff: UploadDiff): string => {
  return `
New records: ${diff.newRows}
Existing records to update: ${diff.updatedRows}
${diff.conflictRows > 0 ? `Conflicts found: ${diff.conflictRows}` : ''}

Previous marks are preserved. Update conflicting entries? `;
};
