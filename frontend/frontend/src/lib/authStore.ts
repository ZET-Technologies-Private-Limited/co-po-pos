// ============================================================
// Auth Store — Backend-backed authentication & role mapping
// ============================================================
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import apiClient, { type LoginRequest, type TokenResponse } from './apiClient';

export type Role = "admin" | "department_head" | "subject_lead" | "faculty" | "student";

export type PermissionLevel = "yes" | "view" | "own" | "no";

// Backend roles from FastAPI (UserRole enum) → frontend roles used in UI
type BackendRole = "admin" | "faculty" | "hod" | "course_lead" | "accreditation_officer" | "viewer";

function mapBackendRoleToFrontend(role: string): Role | null {
  const r = role.toLowerCase() as BackendRole;
  switch (r) {
    case "admin":
      return "admin";
    case "faculty":
      return "faculty";
    case "hod":
      return "department_head";
    case "course_lead":
    case "accreditation_officer":
      return "subject_lead";
    case "viewer":
      return "student";
    default:
      return null;
  }
}

export const PERMISSIONS: Record<string, Record<Role, PermissionLevel>> = {
  login:                    { faculty: "yes",  subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "yes"  },
  dashboard:                { faculty: "yes",  subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "view" },
  co_generation:            { faculty: "yes",  subject_lead: "no",   department_head: "no",   admin: "no",   student: "no"   },
  co_library_view:          { faculty: "yes",  subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "no"   },
  co_edit:                  { faculty: "yes",  subject_lead: "no",   department_head: "no",   admin: "no",   student: "no"   },
  co_po_matrix:             { faculty: "yes",  subject_lead: "view", department_head: "yes",  admin: "yes",  student: "no"   },
  exam_config:              { faculty: "yes",  subject_lead: "no",   department_head: "no",   admin: "no",   student: "no"   },
  question_upload:          { faculty: "yes",  subject_lead: "no",   department_head: "no",   admin: "no",   student: "no"   },
  ai_question_mapping:      { faculty: "yes",  subject_lead: "no",   department_head: "no",   admin: "no",   student: "no"   },
  question_mapping_override: { faculty: "yes", subject_lead: "no",   department_head: "no",   admin: "no",   student: "no"   },
  marks_upload:             { faculty: "yes",  subject_lead: "no",   department_head: "no",   admin: "no",   student: "no"   },
  marks_manual_entry:       { faculty: "yes",  subject_lead: "no",   department_head: "no",   admin: "no",   student: "no"   },
  marks_validation:         { faculty: "yes",  subject_lead: "no",   department_head: "no",   admin: "no",   student: "no"   },
  marks_lock_submit:        { faculty: "yes",  subject_lead: "no",   department_head: "no",   admin: "no",   student: "no"   },
  co_attainment:            { faculty: "own",  subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "no"   },
  marks_approval:           { faculty: "no",   subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "no"   },
  po_attainment:            { faculty: "own",  subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "no"   },
  pso_attainment:           { faculty: "own",  subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "no"   },
  ay_trend:                 { faculty: "no",   subject_lead: "no",   department_head: "yes",  admin: "yes",  student: "no"   },
  low_co_alerts:            { faculty: "no",  subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "no"   },
  remedial_entry:           { faculty: "yes",  subject_lead: "view", department_head: "yes",  admin: "yes",  student: "no"   },
  student_report:           { faculty: "own",  subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "own"  },
  co_attainment_chart:      { faculty: "own",  subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "view" },
  po_pso_chart:             { faculty: "no",   subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "no"   },
  dept_summary:             { faculty: "no",   subject_lead: "no",   department_head: "yes",  admin: "yes",  student: "no"   },
  export_pdf:               { faculty: "own",  subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "no"   },
  export_excel:             { faculty: "own",  subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "no"   },
  nba_export:               { faculty: "no",   subject_lead: "no",   department_head: "yes",  admin: "yes",  student: "no"   },
  admin_dashboard:          { faculty: "no",   subject_lead: "no",   department_head: "no",   admin: "yes",  student: "no"   },
  user_management:          { faculty: "no",   subject_lead: "no",   department_head: "no",   admin: "yes",  student: "no"   },
  ay_setup:                 { faculty: "no",   subject_lead: "no",   department_head: "no",   admin: "yes",  student: "no"   },
  threshold_config:         { faculty: "no",   subject_lead: "no",   department_head: "view", admin: "yes",  student: "no"   },
  co_library_manage:        { faculty: "no",   subject_lead: "no",   department_head: "no",   admin: "yes",  student: "no"   },
  audit_trail:              { faculty: "no",   subject_lead: "view", department_head: "view", admin: "yes",  student: "no"   },
  notifications:            { faculty: "yes",  subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "yes"  },
  year_end_lock:            { faculty: "no",   subject_lead: "no",   department_head: "yes",  admin: "yes",  student: "no"   },
  student_co_view:          { faculty: "no",   subject_lead: "no",   department_head: "no",   admin: "no",   student: "yes"  },
  student_marks_view:       { faculty: "no",   subject_lead: "no",   department_head: "no",   admin: "no",   student: "yes"  },
  profile:                  { faculty: "yes",  subject_lead: "yes",  department_head: "yes",  admin: "yes",  student: "yes"  },
};

export function can(role: Role | null, feature: string): PermissionLevel {
  if (!role) return "no";
  return PERMISSIONS[feature]?.[role] ?? "no";
}

export function canAccess(role: Role | null, feature: string): boolean {
  const level = can(role, feature);
  return level === "yes" || level === "view" || level === "own";
}

export interface User {
  /** Backend user id (UUID string) */
  id: string;
  name: string;
  email: string;
  employeeId?: string;
  /** Frontend roles derived from backend roles */
  roles: Role[];
  department?: string;
  designation?: string;
  firstLogin?: boolean;
  /** Primary backend role string (e.g. "faculty", "hod") */
  backendRole?: string;
  /** All backend roles available for this user */
  backendRoles?: string[];
}

interface AuthState {
  user: User | null;
  activeRole: Role | null;
  activeAY: string;
  isAuthenticated: boolean;
  loginError: string | null;
  accessToken: string | null;
  /**
   * Login using either email or employee ID.
   * Returns true on success, false on failure.
   */
  login: (
    identifier: string,
    password: string,
    options?: { department?: string; academicYear?: string; rememberMe?: boolean }
  ) => Promise<boolean>;
  logout: () => void;
  setActiveRole: (role: Role) => void;
  setActiveAY: (ay: string) => void;
  hasRole: (role: Role) => boolean;
  can: (feature: string) => PermissionLevel;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      activeRole: null,
      activeAY: "2025-26",
      isAuthenticated: false,
      loginError: null,
      accessToken: null,

      login: async (identifier, password, options) => {
        const trimmed = identifier.trim();
        const isEmail = trimmed.includes("@");

        const payload: LoginRequest = {
          password,
          remember_me: options?.rememberMe ?? false,
        };

        if (isEmail) {
          payload.email = trimmed;
        } else {
          payload.employee_id = trimmed;
        }

        // Send department only if provided — backend rejects if it doesn't match stored value.
        // Do NOT send academic_year — backend validates it against Redis AY configs
        // and will reject valid years that aren't seeded yet.
        if (options?.department) {
          payload.department = options.department;
        }

        try {
          const tokenRes: TokenResponse = await apiClient.login(payload);

          // Try to load secondary roles from backend to support dual-role accounts
          let backendRoles: string[] = [];
          try {
            const roleOptions = await apiClient.getRoleOptions();
            backendRoles = roleOptions.available_roles || [];
          } catch {
            backendRoles = [tokenRes.role];
          }

          if (!backendRoles.length) {
            backendRoles = [tokenRes.role];
          }

          const mappedRoles = backendRoles
            .map(mapBackendRoleToFrontend)
            .filter((r): r is Role => r !== null);

          const primaryRole: Role | null =
            mappedRoles[0] ?? mapBackendRoleToFrontend(tokenRes.role);

          if (!primaryRole) {
            set({
              loginError:
                "Your account role is not supported by this UI. Please contact the administrator.",
            });
            return false;
          }

          const user: User = {
            id: tokenRes.user_id,
            name: trimmed,
            email: isEmail ? trimmed : "",
            employeeId: isEmail ? undefined : trimmed,
            roles: mappedRoles.length ? mappedRoles : [primaryRole],
            department: options?.department,
            firstLogin: false,
            backendRole: tokenRes.role,
            backendRoles,
          };

          set({
            user,
            activeRole: primaryRole,
            isAuthenticated: true,
            loginError: null,
            accessToken: tokenRes.access_token,
          });
          return true;
        } catch (err: any) {
          const message =
            typeof err?.message === "string"
              ? err.message
              : "Invalid credentials or network error.";
          set({ loginError: message, isAuthenticated: false, accessToken: null });
          return false;
        }
      },

      logout: () => {
        apiClient.logout();
        set({
          user: null,
          activeRole: null,
          isAuthenticated: false,
          loginError: null,
          accessToken: null,
        });
      },

      setActiveRole: (role) => set({ activeRole: role }),

      setActiveAY: (ay) => set({ activeAY: ay }),

      hasRole: (role) => {
        const { user, activeRole } = get();
        if (!user) return false;
        return activeRole === role || user.roles.includes(role);
      },

      can: (feature) => can(get().activeRole, feature),
    }),
    { name: "obe-ai-auth" }
  )
);
