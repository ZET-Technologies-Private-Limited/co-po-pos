/**
 * FORM & INPUT SMALL FEATURES IMPLEMENTATION GUIDE
 * 
 * All 10 features are implemented and ready to use across the application.
 * This guide shows usage examples for each feature.
 */

// ════════════════════════════════════════════════════════════════════════════════════
// SF-01: Auto-trim whitespace on blur and submit
// ════════════════════════════════════════════════════════════════════════════════════
/**
 * USAGE: FormInput component
 * 
 * <FormInput
 *   label="Full Name"
 *   value={name}
 *   onChange={setName}
 *   autoTrim={true}  // ← Automatically trims leading/trailing spaces on blur
 * />
 * 
 * Utility: trimWhitespace(value: string) from @/lib/formUtils
 */

// ════════════════════════════════════════════════════════════════════════════════════
// SF-02: Auto-uppercase IDs
// ════════════════════════════════════════════════════════════════════════════════════
/**
 * USAGE: FormInput component for Employee ID or Roll Number fields
 * 
 * <FormInput
 *   label="Employee ID"
 *   value={empId}
 *   onChange={setEmpId}
 *   autoUppercase={true}  // ← Converts to uppercase as user types
 *   placeholder="FAC2024001"
 * />
 * 
 * Utility: uppercaseID(value: string) from @/lib/formUtils
 */

// ════════════════════════════════════════════════════════════════════════════════════
// SF-03: Number input step lock (integers only)
// ════════════════════════════════════════════════════════════════════════════════════
/**
 * USAGE: FormInput component for marks and numeric fields
 * 
 * <FormInput
 *   label="Marks"
 *   value={marks}
 *   onChange={setMarks}
 *   integerOnly={true}  // ← Only allows digits 0-9, blocks decimals
 * />
 * 
 * ADVANCED USAGE: MarksEntryTable component (SF-10 enhanced)
 * Automatically enforces integer input on all mark cells with tab navigation
 * 
 * Utility: enforceIntegerOnly(value: string) from @/lib/formUtils
 */

// ════════════════════════════════════════════════════════════════════════════════════
// SF-04: Date range validation for exam dates
// ════════════════════════════════════════════════════════════════════════════════════
/**
 * USAGE: Custom hook or inline validation
 * 
 * const handleExamDateChange = (date: string) => {
 *   const isValid = isDateInRange(
 *     date,
 *     academicYearStart,
 *     academicYearEnd
 *   );
 *   if (!isValid) {
 *     setError(`Date must be within AY ${academicYear}`);
 *   }
 * };
 * 
 * Utility: isDateInRange(date: string, startDate: string, endDate: string) 
 * from @/lib/formUtils
 */

// ════════════════════════════════════════════════════════════════════════════════════
// SF-05: Paste formatting strip (plain text only)
// ════════════════════════════════════════════════════════════════════════════════════
/**
 * USAGE: FormInput textarea component
 * 
 * <FormInput
 *   label="Syllabus Content"
 *   type="textarea"
 *   value={syllabus}
 *   onChange={setSyllabus}
 *   // ← Automatically strips HTML formatting when pasting from Word/PDF
 * />
 * 
 * Utility: stripPasteFormatting(html: string) from @/lib/formUtils
 * FormInput handles paste event automatically in textarea mode
 */

// ════════════════════════════════════════════════════════════════════════════════════
// SF-06: Character counter with color warning
// ════════════════════════════════════════════════════════════════════════════════════
/**
 * USAGE: FormInput component with character limit
 * 
 * <FormInput
 *   label="CO Statement"
 *   value={statement}
 *   onChange={setStatement}
 *   maxLength={200}
 *   showCharCounter={true}  // ← Shows "45 / 200" counter
 *   // Counter turns red at 90% (180 chars)
 * />
 * 
 * Colors:
 * - white/50 (0-70%)
 * - amber-500 (70-90%)
 * - text-alert/red (90%+)
 * 
 * Utilities:
 * - getCharCountColor(current, max) → CSS class
 * - formatCharCount(current, max) → "X / max" string
 */

// ════════════════════════════════════════════════════════════════════════════════════
// SF-07: Required field asterisk
// ════════════════════════════════════════════════════════════════════════════════════
/**
 * USAGE: FormInput component
 * 
 * <FormInput
 *   label="Course Code"
 *   value={code}
 *   onChange={setCode}
 *   required={true}  // ← Adds red asterisk to label automatically
 * />
 * 
 * CSS: All required fields show red '*' via CSS after pseudo-element
 */

// ════════════════════════════════════════════════════════════════════════════════════
// SF-08: Duplicate check on blur
// ════════════════════════════════════════════════════════════════════════════════════
/**
 * USAGE: FormInput component with duplicate checking
 * 
 * <FormInput
 *   label="Employee ID"
 *   value={empId}
 *   onChange={setEmpId}
 *   checkDuplicates={true}  // ← Checks on blur
 *   existingValues={existingEmployeeIds}
 *   // Shows "Already exists" error if found
 * />
 * 
 * Behavior:
 * - Debounces for 500ms
 * - Shows spinner while checking
 * - Displays error if duplicate found
 * - Case-insensitive comparison
 * 
 * Utility: checkDuplicate(value, existingValues) from @/lib/formUtils
 */

// ════════════════════════════════════════════════════════════════════════════════════
// SF-09: Confirmation before delete
// ════════════════════════════════════════════════════════════════════════════════════
/**
 * USAGE: useDeleteConfirmation hook + DeleteConfirmationDialog component
 * 
 * // In component:
 * const { showConfirm, requestDelete, confirmDelete, cancelDelete } = useDeleteConfirmation();
 * 
 * // On delete button click:
 * const onDelete = () => {
 *   requestDelete(async () => {
 *     await deleteUser(userId);
 *     addToast('User deleted', 'success');
 *   });
 * };
 * 
 * // In JSX:
 * <DeleteConfirmationDialog
 *   isOpen={showConfirm}
 *   title="Delete User?"
 *   message="This action cannot be undone."
 *   itemName={selectedUser.name}
 *   onConfirm={() => confirmDelete(() => {
 *     // delete logic
 *   })}
 *   onCancel={cancelDelete}
 *   isLoading={isDeleting}
 * />
 * 
 * Features:
 * - Modal backdrop
 * - Item preview (name/identifier)
 * - Loading state
 * - Escape key to cancel
 */

// ════════════════════════════════════════════════════════════════════════════════════
// SF-10: Tab key navigation in marks table
// ════════════════════════════════════════════════════════════════════════════════════
/**
 * USAGE: MarksEntryTable component
 * 
 * <MarksEntryTable
 *   headers={['Roll No', 'Name', 'Q1', 'Q2', 'Q3', ...]}
 *   rows={marksData}
 *   onCellChange={handleCellChange}
 * />
 * 
 * Keyboard Shortcuts:
 * - Tab       → Move to next column (right)
 * - Shift+Tab → Move to previous column (left)
 * - Enter     → Move to next row (down, same column)
 * - ↑↓←→     → Arrow navigation
 * - Click     → Jump to any cell
 * 
 * Auto Features in this table:
 * - Integer-only input (SF-03)
 * - Automatic focus management
 * - Total calculation
 * - Max marks validation
 * 
 * Hook: useTableTabNavigation(rows, cols) from @/lib/useFormFeatures
 */

// ════════════════════════════════════════════════════════════════════════════════════
// CUSTOM HOOKS REFERENCE
// ════════════════════════════════════════════════════════════════════════════════════

/**
 * useCharacterCounter(maxLength)
 * Returns: { count, maxLength, isWarning, handleChange }
 * Warning triggers at 90% of max length
 */

/**
 * useDuplicateCheck(checkFn)
 * Returns: { isDuplicate, isChecking, checkValue }
 * Debounced check with async support
 */

/**
 * useDeleteConfirmation()
 * Returns: { showConfirm, requestDelete, confirmDelete, cancelDelete }
 * Manages confirmation dialog state
 */

/**
 * useTableTabNavigation(rows, cols)
 * Returns: { focusedCell, handleKeyDown }
 * Tab, Enter, and arrow key navigation for tables
 */

// ════════════════════════════════════════════════════════════════════════════════════
// REAL WORLD EXAMPLE: Complete User Form with all features
// ════════════════════════════════════════════════════════════════════════════════════

/**
 * export default function UserForm({ user, onSave, onDelete }) {
 *   const [form, setForm] = useState({
 *     name: user?.name || '',
 *     email: user?.email || '',
 *     empId: user?.empId || '',
 *     bio: user?.bio || '',
 *   });
 *   
 *   const { showConfirm, requestDelete, confirmDelete, cancelDelete } = useDeleteConfirmation();
 *   const [existingEmails, setExistingEmails] = useState([...]);
 *   const [existingEmpIds, setExistingEmpIds] = useState([...]);
 * 
 *   const handleDelete = () => {
 *     requestDelete(async () => {
 *       await deleteUser(user.id);
 *     });
 *   };
 * 
 *   return (
 *     <div className="space-y-6">
 *       <FormInput
 *         label="Full Name"
 *         value={form.name}
 *         onChange={(v) => setForm(p => ({...p, name: v}))}
 *         required
 *         autoTrim        // SF-01
 *       />
 *       
 *       <FormInput
 *         label="Email"
 *         type="email"
 *         value={form.email}
 *         onChange={(v) => setForm(p => ({...p, email: v}))}
 *         required
 *         autoTrim        // SF-01
 *         checkDuplicates // SF-08
 *         existingValues={existingEmails}
 *       />
 *       
 *       <FormInput
 *         label="Employee ID"
 *         value={form.empId}
 *         onChange={(v) => setForm(p => ({...p, empId: v}))}
 *         required
 *         autoTrim        // SF-01
 *         autoUppercase   // SF-02
 *         checkDuplicates // SF-08
 *         existingValues={existingEmpIds}
 *       />
 *       
 *       <FormInput
 *         label="Bio"
 *         type="textarea"
 *         value={form.bio}
 *         onChange={(v) => setForm(p => ({...p, bio: v}))}
 *         maxLength={500}
 *         showCharCounter // SF-06
 *         // SF-05 paste formatting handled automatically
 *       />
 *       
 *       <div className="flex gap-4">
 *         <button onClick={() => onSave(form)}>Save</button>
 *         {user && (
 *           <button onClick={handleDelete} className="text-alert">
 *             Delete
 *           </button>
 *         )}
 *       </div>
 *       
 *       <DeleteConfirmationDialog
 *         isOpen={showConfirm}
 *         title="Delete User?"
 *         itemName={form.name}
 *         onConfirm={() => confirmDelete(async () => {
 *           await onDelete(user.id);
 *         })}
 *         onCancel={cancelDelete}
 *       />
 *     </div>
 *   );
 * }
 */

export const FORM_FEATURES_GUIDE = {
  'SF-01': 'Auto-trim whitespace',
  'SF-02': 'Auto-uppercase IDs',
  'SF-03': 'Integer input lock',
  'SF-04': 'Date range validation',
  'SF-05': 'Paste formatting strip',
  'SF-06': 'Character counter',
  'SF-07': 'Required field asterisk',
  'SF-08': 'Duplicate check',
  'SF-09': 'Delete confirmation',
  'SF-10': 'Tab key navigation',
};
