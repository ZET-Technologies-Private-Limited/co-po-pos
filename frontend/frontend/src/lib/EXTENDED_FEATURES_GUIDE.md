# Extended Form & UI Features Implementation (SF-21 to SF-70)

## Overview
All 50 extended features across 7 categories are now implemented as reusable utilities, hooks, and components.

---

## 7.3 Status Indicators & Colour Logic (SF-21 to SF-26)

### Import
```typescript
import * as statusIndicators from '@/lib/statusIndicators';
```

| Feature | Function | Returns | Usage |
|---------|----------|---------|-------|
| **SF-21** | `getCOLevelColor(level)` | CSS class | `<span className={getCOLevelColor('L3')}>Achieved</span>` |
| | `getCOLevelLabel(level)` | Label text | Display human-readable level |
| **SF-22** | `getMarksStatusColor(status)` | CSS class | Status badge styling |
| | `getMarksStatusLabel(status)` | Label text | 'Approved', 'Submitted', etc. |
| **SF-23** | `getWaitTimeColor(hours)` | CSS class | Color based on wait duration |
| | `getWaitTimeLabel(hours)` | Formatted text | '2 days', '5 hours' |
| **SF-24** | `isOverdue(deadline)` | Boolean | Check if past deadline |
| | `getOverdueClass(deadline)` | CSS class | 'text-alert font-bold' if overdue |
| | `getOverdueText(deadline)` | Text | 'Overdue by 2 days' |
| **SF-25** | `getAttainmentColor(%)` | CSS class | Green/Amber/Red based on % |
| | `getAttainmentLevel(%)` | 'L3'\|'L2'\|'L1' | Convert % to level |
| **SF-26** | `getSystemStatusColor(status)` | CSS class | API/DB health indicator |
| | `getSystemStatusLabel(status)` | Label | 'Healthy', 'Degraded', 'Down' |

### Example Usage

```tsx
// CO Attainment Table
<td className={getAttainmentColor(72)}>
  {roundAttainmentPercent(72, 1)}
</td>

// Marks Status
<span className={getMarksStatusColor('approved')}>
  {getMarksStatusLabel('approved')}
</span>

// Overdue Indicator
{isOverdue(deadline) && (
  <span className={getOverdueClass(deadline)}>
    {getOverdueText(deadline)}
  </span>
)}
```

---

## 7.4 Navigation & UX Small Features (SF-27 to SF-34)

### Import
```typescript
import * as navigationUtils from '@/lib/navigationUtils';
import { useReadOnlyMode, useFocusManagement, useAutoRedirectOnContextChange } from '@/lib/navigationUtils';
```

| Feature | Type | Details |
|---------|------|---------|
| **SF-27** | Deep Linking | `generateDeepLink()`, `encodePageState()`, `decodePageState()` |
| **SF-28** | Browser Back/Forward | Works automatically with Next.js routing |
| **SF-29** | Print CSS | Include `printOptimizedStyles` in head, use `triggerPrint()` |
| **SF-30** | Mobile Drawer | Responsive sidebar (collapses on <768px) |
| **SF-31** | Keyboard Navigation | `handleKeyDown()` helper for Escape, Tab, Enter |
| **SF-32** | Focus Management | `useFocusManagement()` hook for form/modal focus |
| **SF-33** | Auto-Redirect | `useAutoRedirectOnContextChange()` hook |
| **SF-34** | Read-Only Mode | `useReadOnlyMode()`, `isReadOnlyMode()` helpers |

### Example Usage

```tsx
// Deep link state
const state = { filters: 'L3', sort: 'date' };
const deepLink = generateDeepLink('/courses/CS301', state);

// Read-only for past academic years
const { isReadOnly, banner, readOnlyProps } = useReadOnlyMode('2023-24', '2024-25');

{banner && <AlertBanner>{banner}</AlertBanner>}
<input {...readOnlyProps} />

// Focus management in forms/modals
const dialogRef = useFocusManagement('[data-first-input]');

// Auto-save and redirect on role change
useAutoRedirectOnContextChange(
  { academicYear: currentYear, userRole },
  pathname
);
```

---

## 7.5 Data & Calculation Display (SF-35 to SF-42)

### Import
```typescript
import * as dataDisplay from '@/lib/dataDisplay';
```

| Feature | Function | Purpose |
|---------|----------|---------|
| **SF-35** | `roundAttainmentPercent(value, decimals)` | 72.456 → '72.5%' |
| | `formatStudentMarks(value)` | Integer formatting |
| **SF-36** | `formatAttainmentValue(value, isCalculated)` | '0.0%' vs '—' distinction |
| **SF-37** | `formatQuestionMarks(marks, isAttempted)` | 'N/A' for unattempted |
| **SF-38** | `getLivePreviewLabel(isApproved)` | 'Estimated' or 'Official' |
| **SF-39** | `formatCalculationTimestamp(date)` | '2h ago', 'Just now' |
| **SF-40** | `getAttainmentFormula(type)` | Plain-English formula explanation |
| | `formatWithConfidence(value, confidence)` | '72.5% (high confidence)' |
| **SF-41** | `getThresholdReference()` | Array of {level, range} |
| | `formatThresholdLine()` | 'L3 ≥ 60% \| L2 = 40-59% \| L1 < 40%' |
| **SF-42** | `formatOverrideTooltip(override)` | Original value, who, when, why |

### Example Usage

```tsx
// Attainment display in table
<td className={getAttainmentColor(72.456)}>
  {roundAttainmentPercent(72.456, 1)}
  <small className="text-white/40">{formatCalculationTimestamp(lastCalcDate)}</small>
</td>

// Threshold legend below table
<div className="text-xs text-white/50 mt-4">
  {formatThresholdLine()}
</div>

// Overridden values with tooltip
{override && (
  <span title={formatOverrideTooltip(override)}>
    {roundAttainmentPercent(override.originalValue)}*
  </span>
)}

// CO preview label
<badge>{getLivePreviewLabel(isApproved)}</badge>
```

---

## 7.6 File Upload & Export (SF-43 to SF-50)

### Import
```typescript
import * as fileHandling from '@/lib/fileHandling';
```

| Feature | Function | Purpose |
|---------|----------|---------|
| **SF-43** | `validateFileType(file, 'EXCEL')` | Check .xlsx before upload |
| | `getFileTypeError(name, 'PDF')` | Error message if wrong type |
| **SF-44** | `validateFileSize(file)` | Check ≤ 10 MB |
| | `MAX_FILE_SIZE_MB` | Constant = 10 |
| **SF-45** | `formatUploadProgress(loaded, total)` | 'Uploading... 67%' |
| | `shouldShowUploadProgress(bytes)` | Show for files > 1 MB |
| **SF-46** | `generateFileName(type, course, ay, term)` | Auto-name files |
| **SF-47** | `formatLinkExpiry(createdAt)` | 'Link expires in X hours' |
| | `isLinkExpired(createdAt)` | Check if > 24 hours old |
| | `LINK_EXPIRY_HOURS` | Constant = 24 |
| **SF-48** | `getPDFWatermark(dept, ay)` | 'Confidential — CSE — AY 2024-25' |
| **SF-49** | `formatExcelDate(date)` | DD-MM-YYYY format |
| **SF-50** | `calculateUploadDiff(newData, existing)` | Shows new/updated/unchanged rows |
| | `formatReuploadMessage(diff)` | Confirmation text |

### Example Usage

```tsx
// File upload validation
const handleFileSelect = (file: File) => {
  if (!validateFileType(file, 'EXCEL')) {
    return setError(getFileTypeError(file.name, '.xlsx'));
  }
  if (!validateFileSize(file)) {
    return setError(getFileSizeError(getFileSizeInMB(file.size)));
  }
};

// Upload progress
{shouldShowUploadProgress(file.size) && (
  <div>{formatUploadProgress(uploadedBytes, file.size)}</div>
)}

// Download link expiry
<p className="text-xs text-white/50">
  {formatLinkExpiry(download.createdAt)}
</p>

// PDF watermark
const watermark = getPDFWatermark('Computer Science', '2024-25');
```

---

## 7.7 Notification & Alerts (SF-51 to SF-57)

### Import
```typescript
import * as notificationUtils from '@/lib/notificationUtils';
import { useToastManager, useAlertBanners } from '@/lib/notificationUtils';
```

| Feature | Type | Details |
|---------|------|---------|
| **SF-51** | Alert Banners | `useAlertBanners()` — persistent, closeable |
| **SF-52** | Toast Notifications | `useToastManager()` — auto-dismiss in 4s |
| **SF-53** | Error Toast Persistence | Errors don't auto-dismiss |
| **SF-54** | Batch Deduplication | `deduplicateNotifications()` — consolidate 3 emails to 1 |
| **SF-55** | Deadline Countdown | `calculateDeadlineCountdown()` — urgent if < 3 days |
| **SF-56** | Email Format | `formatEmailNotification()` — plain text, one link |
| **SF-57** | Do Not Disturb | `useautoSend`, `isInDNDWindow()` |

### Example Usage

```tsx
// Toast notifications
const { toasts, addSuccess, addError, removeToast } = useToastManager();

const handleSave = async () => {
  try {
    await saveMarks(data);
    addSuccess('Marks saved successfully');
  } catch (err) {
    addError('Failed to save marks');
  }
};

// Alert banners (CO level violations)
const { banners, addBanner, removeBanner } = useAlertBanners();

addBanner({
  type: 'warning',
  title: 'CO Mapping Issue',
  message: 'CO3 is not mapped to any PO',
  action: { label: 'Fix Mapping', handler: () => navigate('/mapping') },
  closeable: true,
});

// Deadline countdown in topbar
{deadlineAlert && (
  <div className="text-amber-500">
    {formatDeadlineCountdown(deadlineAlert)}
  </div>
)}

// DND settings
if (shouldSendNotificationNow('email', dndSettings)) {
  sendEmailNotification(...);
}

// Batch notifications
const deduped = deduplicateNotifications(notifications);
// "Faculty submitted 3 exams" instead of 3 separate messages
```

---

## 7.8 Security & Session (SF-58 to SF-63)

### Import
```typescript
import * as securityUtils from '@/lib/securityUtils';
import { useAutoSave } from '@/lib/securityUtils';
```

| Feature | Type | Details |
|---------|------|---------|
| **SF-58** | Auto-Save | `useAutoSave()` — saves every 30s + on page close |
| | | `retrieveDraft()` — prompt user on next login |
| **SF-59** | Concurrent Sessions | `checkConcurrentSessions()`, `logoutOtherSession()` |
| **SF-60** | Login Counter | `checkLoginAttempts()` — shows '3 of 5' |
| | | Locks after 5 attempts for 15 mins |
| **SF-61** | Data Masking | `maskSensitiveData()`, `isUserAuthorizedForData()` |
| **SF-62** | Audit Logging | `logAuditEntry()` — auto-logged on every save |
| | | `withAuditLog()` — wrapper for save operations |
| **SF-63** | HTTPS Redirect | `enforceHTTPS()`, `getSecurityHeaders()` |

### Example Usage

```tsx
// Auto-save marks
useAutoSave(userId, '/courses/CS301/marks', marksData);

// Check draft on login
const draft = await retrieveDraft(userId, currentPage);
if (draft) {
  showModal('Resume your draft from last session?', draft);
}

// Login attempt counter
const attempts = await checkLoginAttempts(email);
<p className="text-sm text-white/50">
  {formatLoginAttemptMessage(attempts)}
</p>

// Audit log on save
await withAuditLog(
  userId,
  'approve_marks',
  'exam_submission',
  examId,
  async () => await submitMarks(data),
  oldMarks,
  newMarks
);

// Mask sensitive data
const marksForDisplay = maskSensitiveData(allMarks, [
  'studentEmail',
  'studentPhone',
]);
```

---

## 7.9 Chatbot Features (SF-64 to SF-70)

### Import
```typescript
import * as chatbotUtils from '@/lib/chatbotUtils';
import {
  useChatbotMemory,
  useChatbotWorkflowDraft,
  generateSuggestedReplies,
} from '@/lib/chatbotUtils';
```

| Feature | Type | Details |
|---------|------|---------|
| **SF-64** | Session Memory | `useChatbotMemory()` — remembers course, POs, history |
| **SF-65** | Partial Regen | `formatCOGenerationPrompt()` — 'redo CO3 only' |
| **SF-66** | BT Justification | `requestBTJustification()`, `bloomLevelDescriptions` |
| **SF-67** | Confidence Score | `getConfidenceLabel()`, `formatConfidenceScore()` — shows % |
| **SF-68** | Suggested Replies | `generateSuggestedReplies()` — context-specific buttons |
| **SF-69** | Fallback Messages | `CHATBOT_FALLBACK_RESPONSES`, `shouldUseFallback()` |
| **SF-70** | Save Draft | `useChatbotWorkflowDraft()` — resume workflow |

### Example Usage

```tsx
// Session memory
const { memory, recordMessage, setCourseContext } = useChatbotMemory(courseId);

setCourseContext(
  'Database Management',
  'CS301',
  sylabusText,
  ['PO1', 'PO2', 'PO3']
);

recordMessage('user', 'Generate COs for this course');

// Partial CO regeneration
const prompt = formatCOGenerationPrompt({
  type: 'partial',
  courseId,
  courseCode: 'CS301',
  courseSyllabus,
  existingCOs: { CO1: 'Statement 1', CO2: 'Statement 2', CO3: 'Statement 3' },
  targetCOs: ['CO2', 'CO3'], // Redo only these
  programOutcomes: ['PO1', 'PO2'],
});

// Confidence display
{result.confidence && (
  <small>{formatConfidenceScore(result.confidence)}</small>
)}

// Suggested reply buttons
{generateSuggestedReplies(lastMessage, 'co_generation').map(reply => (
  <button onClick={() => handleSuggestedReply(reply)}>
    {reply.text}
  </button>
))}

// Fallback message
{shouldUseFallback(botResponse) && (
  <div>{CHATBOT_FALLBACK_RESPONSES.unclear}</div>
)}

// Save & resume workflow
const { draft, saveDraft, clearDraft } = useChatbotWorkflowDraft(
  courseId,
  'co_generation'
);

if (draft) {
  <ResumeWorkflowPrompt draft={draft} />
}
```

---

## Complete Integration Checklist

- [ ] Status indicators for all CO/PO/PSO attainment displays
- [ ] Colour-coded marks status badges
- [ ] Overdue text on deadline-missed items
- [ ] Read-only mode for past academic years
- [ ] Deep link URLs on all major views
- [ ] Print CSS for all report pages
- [ ] Tab/Escape keyboard shortcuts
- [ ] Focus management in all modals/forms
- [ ] Auto-save for marks entry
- [ ] Auto-logout with draft recovery
- [ ] Audit trail for all save operations
- [ ] File upload validation & progress
- [ ] Toast notifications for all actions
- [ ] Deadline countdown in topbar
- [ ] Chatbot memory between sessions
- [ ] Confidence scores on AI suggestions
- [ ] Suggested reply buttons dynamically

---

## Files Available
All features are implemented in:
- `src/lib/statusIndicators.ts` (SF-21 to SF-26)
- `src/lib/navigationUtils.ts` (SF-27 to SF-34)
- `src/lib/dataDisplay.ts` (SF-35 to SF-42)
- `src/lib/fileHandling.ts` (SF-43 to SF-50)
- `src/lib/notificationUtils.ts` (SF-51 to SF-57)
- `src/lib/securityUtils.ts` (SF-58 to SF-63)
- `src/lib/chatbotUtils.ts` (SF-64 to SF-70)

**Total: 70 form & UI features implemented and ready to use locally. No push to GitHub as requested.**
