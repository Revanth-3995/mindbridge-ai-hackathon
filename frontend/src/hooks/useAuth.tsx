'use client';

import { useAuth } from '../context/AuthContext';

// TypeScript interfaces
export interface User {
  id: string;
  email: string;
  created_at: string;
  updated_at: string;
  baseline_mood?: 'very_negative' | 'negative' | 'neutral' | 'positive' | 'very_positive';
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  is_active: boolean;
  email_verified: boolean;
  privacy_settings?: {
    profile_visibility: 'public' | 'private' | 'friends_only';
    data_sharing: boolean;
    analytics_tracking: boolean;
    marketing_emails: boolean;
  };
}

export interface LoginCredentials {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterData {
  email: string;
  password: string;
  confirm_password: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  privacy_settings?: {
    profile_visibility: 'public' | 'private' | 'friends_only';
    data_sharing: boolean;
    analytics_tracking: boolean;
    marketing_emails: boolean;
  };
  terms_accepted: boolean;
  privacy_policy_accepted: boolean;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: AuthError | null;
}

export interface AuthError {
  message: string;
  code: string;
  details?: Record<string, string>;
}

export interface AuthAction {
  type: 'AUTH_START' | 'AUTH_SUCCESS' | 'AUTH_FAILURE' | 'LOGOUT' | 'UPDATE_USER' | 'CLEAR_ERROR';
  payload?: unknown;
}

export interface OnboardingData {
  baseline_mood: 'very_negative' | 'negative' | 'neutral' | 'positive' | 'very_positive';
  emergency_contact_name: string;
  emergency_contact_phone: string;
  notification_preferences: {
    email_notifications: boolean;
    push_notifications: boolean;
    crisis_alerts: boolean;
    weekly_reports: boolean;
  };
  privacy_settings: {
    profile_visibility: 'public' | 'private' | 'friends_only';
    data_sharing: boolean;
    analytics_tracking: boolean;
    marketing_emails: boolean;
  };
  phq9_responses: {
    interest_pleasure: number;
    mood: number;
    sleep: number;
    energy: number;
    appetite: number;
    self_worth: number;
    concentration: number;
    psychomotor: number;
    suicidal_thoughts: number;
  };
}

// Re-export the useAuth hook from AuthContext
export { useAuth } from '../context/AuthContext';

// Additional utility hooks
export function useAuthState() {
  const { state } = useAuth();
  return state;
}

export function useAuthActions() {
  const { login, register, logout, refreshAuthToken, updateUser, clearError } = useAuth();
  return {
    login,
    register,
    logout,
    refreshAuthToken,
    updateUser,
    clearError,
  };
}

export function useUser() {
  const { state } = useAuth();
  return state.user;
}

export function useIsAuthenticated() {
  const { state } = useAuth();
  return state.isAuthenticated;
}

export function useAuthLoading() {
  const { state } = useAuth();
  return state.isLoading;
}

export function useAuthError() {
  const { state } = useAuth();
  return state.error;
}

// Error types for better error handling
export const AUTH_ERROR_CODES = {
  LOGIN_FAILED: 'LOGIN_FAILED',
  REGISTRATION_FAILED: 'REGISTRATION_FAILED',
  TOKEN_REFRESH_FAILED: 'TOKEN_REFRESH_FAILED',
  NETWORK_ERROR: 'NETWORK_ERROR',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  SERVER_ERROR: 'SERVER_ERROR',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  RATE_LIMITED: 'RATE_LIMITED',
} as const;

export type AuthErrorCode = typeof AUTH_ERROR_CODES[keyof typeof AUTH_ERROR_CODES];

// Utility functions for error handling
export function isAuthError(error: unknown): error is AuthError {
  return !!(error && typeof error === 'object' && 'message' in error && 'code' in error);
}

export function getErrorMessage(error: AuthError | Error | string): string {
  if (typeof error === 'string') {
    return error;
  }
  
  if (isAuthError(error)) {
    return error.message;
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return 'An unknown error occurred';
}

export function getErrorCode(error: AuthError | Error | string): string {
  if (isAuthError(error)) {
    return error.code;
  }
  
  if (error instanceof Error) {
    return 'UNKNOWN_ERROR';
  }
  
  return 'UNKNOWN_ERROR';
}

// Validation schemas (can be used with form libraries)
export const loginValidationSchema = {
  email: {
    required: 'Email is required',
    pattern: {
      value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
      message: 'Invalid email address',
    },
  },
  password: {
    required: 'Password is required',
    minLength: {
      value: 8,
      message: 'Password must be at least 8 characters',
    },
  },
};

export const registerValidationSchema = {
  email: {
    required: 'Email is required',
    pattern: {
      value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
      message: 'Invalid email address',
    },
  },
  password: {
    required: 'Password is required',
    minLength: {
      value: 8,
      message: 'Password must be at least 8 characters',
    },
    pattern: {
      value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
      message: 'Password must contain uppercase, lowercase, number, and special character',
    },
  },
  confirm_password: {
    required: 'Password confirmation is required',
    validate: (value: string, formValues: Record<string, unknown>) => 
      value === (formValues.password as string) || 'Passwords do not match',
  },
  terms_accepted: {
    required: 'You must accept the terms of service',
    validate: (value: boolean) => value === true || 'You must accept the terms of service',
  },
  privacy_policy_accepted: {
    required: 'You must accept the privacy policy',
    validate: (value: boolean) => value === true || 'You must accept the privacy policy',
  },
};

// Password strength utility
export function calculatePasswordStrength(password: string): {
  score: number;
  feedback: string[];
  strength: 'weak' | 'fair' | 'good' | 'strong';
} {
  const feedback: string[] = [];
  let score = 0;
  
  if (password.length >= 8) {
    score += 1;
  } else {
    feedback.push('At least 8 characters');
  }
  
  if (/[a-z]/.test(password)) {
    score += 1;
  } else {
    feedback.push('Lowercase letter');
  }
  
  if (/[A-Z]/.test(password)) {
    score += 1;
  } else {
    feedback.push('Uppercase letter');
  }
  
  if (/\d/.test(password)) {
    score += 1;
  } else {
    feedback.push('Number');
  }
  
  if (/[@$!%*?&]/.test(password)) {
    score += 1;
  } else {
    feedback.push('Special character (@$!%*?&)');
  }
  
  if (password.length >= 12) {
    score += 1;
  }
  
  let strength: 'weak' | 'fair' | 'good' | 'strong';
  if (score <= 2) {
    strength = 'weak';
  } else if (score <= 3) {
    strength = 'fair';
  } else if (score <= 4) {
    strength = 'good';
  } else {
    strength = 'strong';
  }
  
  return { score, feedback, strength };
}
