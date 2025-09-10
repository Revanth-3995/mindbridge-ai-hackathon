'use client';

import React, { createContext, useContext, useReducer, useEffect, useCallback, ReactNode } from 'react';
import { User, AuthState, AuthAction, LoginCredentials, RegisterData, AuthError } from '../hooks/useAuth';

// Initial state
const initialState: AuthState = {
  user: null,
  token: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
};

// Auth reducer
function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'AUTH_START':
      return {
        ...state,
        isLoading: true,
        error: null,
      };
    
    case 'AUTH_SUCCESS':
      const authSuccessPayload = action.payload as { user: User; token: string; refreshToken: string };
      return {
        ...state,
        user: authSuccessPayload.user,
        token: authSuccessPayload.token,
        refreshToken: authSuccessPayload.refreshToken,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      };
    
    case 'AUTH_FAILURE':
      return {
        ...state,
        user: null,
        token: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
        error: action.payload as AuthError,
      };
    
    case 'LOGOUT':
      return {
        ...state,
        user: null,
        token: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      };
    
    case 'UPDATE_USER':
      return {
        ...state,
        user: action.payload as User,
      };
    
    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      };
    
    default:
      return state;
  }
}

// Context
const AuthContext = createContext<{
  state: AuthState;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  refreshAuthToken: () => Promise<void>;
  updateUser: (user: User) => void;
  clearError: () => void;
} | null>(null);

// Token management utilities
const TOKEN_KEY = 'mindbridge_token';
const REFRESH_TOKEN_KEY = 'mindbridge_refresh_token';
const USER_KEY = 'mindbridge_user';

const saveTokens = (token: string, refreshToken: string, user: User) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
};

const clearTokens = () => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
};

const getStoredTokens = () => {
  if (typeof window === 'undefined') return { token: null, refreshToken: null, user: null };
  
  const token = localStorage.getItem(TOKEN_KEY);
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  const userStr = localStorage.getItem(USER_KEY);
  const user = userStr ? JSON.parse(userStr) : null;
  
  return { token, refreshToken, user };
};

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Auth provider component
export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Refresh auth token
  const refreshAuthToken = useCallback(async () => {
    if (!state.refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: state.refreshToken }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Token refresh failed');
      }

      const { access_token, refresh_token, user } = data;
      
      saveTokens(access_token, refresh_token, user);
      
      dispatch({
        type: 'AUTH_SUCCESS',
        payload: {
          user,
          token: access_token,
          refreshToken: refresh_token,
        },
      });
    } catch (error) {
      clearTokens();
      dispatch({ type: 'LOGOUT' });
      throw error;
    }
  }, [state.refreshToken]);

  // Initialize auth state from localStorage
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const { token, refreshToken, user } = getStoredTokens();
        
        if (token && user) {
          // Verify token is still valid
          const response = await fetch(`${API_BASE_URL}/api/v1/auth/profile`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });
          
          if (response.ok) {
            const userData = await response.json();
            dispatch({
              type: 'AUTH_SUCCESS',
              payload: {
                user: userData,
                token,
                refreshToken: refreshToken || '',
              },
            });
          } else {
            // Token is invalid, try to refresh
            if (refreshToken) {
              await refreshAuthToken();
            } else {
              clearTokens();
              dispatch({ type: 'LOGOUT' });
            }
          }
        } else {
          dispatch({ type: 'LOGOUT' });
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        clearTokens();
        dispatch({ type: 'LOGOUT' });
      }
    };

    initializeAuth();
  }, [refreshAuthToken]);

  // Auto-refresh token before expiration
  useEffect(() => {
    if (!state.token || !state.refreshToken) return;

    const refreshInterval = setInterval(async () => {
      try {
        await refreshAuthToken();
      } catch (error) {
        console.error('Auto-refresh failed:', error);
        dispatch({ type: 'LOGOUT' });
      }
    }, 25 * 60 * 1000); // Refresh every 25 minutes

    return () => clearInterval(refreshInterval);
  }, [state.token, state.refreshToken, refreshAuthToken]);

  // Login function
  const login = async (credentials: LoginCredentials) => {
    dispatch({ type: 'AUTH_START' });
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }

      const { access_token, refresh_token, user } = data;
      
      saveTokens(access_token, refresh_token, user);
      
      dispatch({
        type: 'AUTH_SUCCESS',
        payload: {
          user,
          token: access_token,
          refreshToken: refresh_token,
        },
      });
    } catch (error) {
      const authError: AuthError = {
        message: error instanceof Error ? error.message : 'Login failed',
        code: 'LOGIN_FAILED',
      };
      dispatch({ type: 'AUTH_FAILURE', payload: authError });
      throw authError;
    }
  };

  // Register function
  const register = async (data: RegisterData) => {
    dispatch({ type: 'AUTH_START' });
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || 'Registration failed');
      }

      // Auto-login after successful registration
      await login({
        email: data.email,
        password: data.password,
      });
    } catch (error) {
      const authError: AuthError = {
        message: error instanceof Error ? error.message : 'Registration failed',
        code: 'REGISTRATION_FAILED',
      };
      dispatch({ type: 'AUTH_FAILURE', payload: authError });
      throw authError;
    }
  };

  // Logout function
  const logout = async () => {
    try {
      if (state.token) {
        await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${state.token}`,
          },
        });
      }
    } catch (error) {
      console.error('Logout API call failed:', error);
    } finally {
      clearTokens();
      dispatch({ type: 'LOGOUT' });
    }
  };

  // Update user profile
  const updateUser = (user: User) => {
    dispatch({ type: 'UPDATE_USER', payload: user });
    if (typeof window !== 'undefined') {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    }
  };

  // Clear error
  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  const value = {
    state,
    login,
    register,
    logout,
    refreshAuthToken,
    updateUser,
    clearError,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook to use auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Higher-order component for protected routes
export function withAuth<P extends object>(
  Component: React.ComponentType<P>
): React.ComponentType<P> {
  return function AuthenticatedComponent(props: P) {
    const { state } = useAuth();
    
    if (state.isLoading) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
        </div>
      );
    }
    
    if (!state.isAuthenticated) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">Authentication Required</h1>
            <p className="text-gray-600 mb-4">Please log in to access this page.</p>
            <a 
              href="/auth/login" 
              className="inline-block bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Go to Login
            </a>
          </div>
        </div>
      );
    }
    
    return <Component {...props} />;
  };
}
