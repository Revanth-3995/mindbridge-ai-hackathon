# Authentication System

This directory contains the complete authentication system for the Mind Bridge AI frontend application.

## Components

### Context (`context/AuthContext.tsx`)
- **AuthProvider**: React context provider for global authentication state
- **useAuth**: Custom hook to access authentication context
- **withAuth**: Higher-order component for protected routes
- **Token Management**: Automatic token refresh and localStorage persistence
- **Error Handling**: Comprehensive error handling with retry logic

### Hooks (`hooks/useAuth.tsx`)
- **TypeScript Interfaces**: Complete type definitions for all auth-related data
- **Utility Hooks**: Specialized hooks for different aspects of auth state
- **Validation Schemas**: Yup schemas for form validation
- **Password Strength**: Utility function for password strength calculation
- **Error Types**: Comprehensive error handling with specific error codes

### Pages

#### Login (`app/auth/login/page.tsx`)
- **React Hook Form**: Form handling with validation
- **Yup Validation**: Client-side validation with error messages
- **Password Visibility**: Toggle for password field
- **Remember Me**: Persistent login option
- **Social Login**: Google OAuth integration (placeholder)
- **Error Boundaries**: Graceful error handling

#### Register (`app/auth/register/page.tsx`)
- **Multi-step Form**: 3-step registration process
- **Real-time Validation**: Live form validation
- **Password Strength**: Visual password strength indicator
- **Progress Indicator**: Step-by-step progress tracking
- **Terms & Privacy**: Legal agreement checkboxes

#### Onboarding (`app/auth/onboarding/page.tsx`)
- **Welcome Screen**: Introduction to the platform
- **Mood Assessment**: Baseline mood selection
- **PHQ-9 Assessment**: Mental health screening questionnaire
- **Emergency Contact**: Safety contact information
- **Preferences**: Notification and privacy settings
- **Tutorial**: User guidance (placeholder)

### Components (`components/ErrorBoundary.tsx`)
- **Error Boundary**: React error boundary for graceful error handling
- **withErrorBoundary**: HOC for wrapping components
- **useErrorHandler**: Hook for error handling in functional components

## Features

### Security
- JWT token management with automatic refresh
- Secure token storage in localStorage
- Password strength validation
- Input sanitization and validation
- Rate limiting support

### User Experience
- Multi-step forms with progress indicators
- Real-time validation feedback
- Loading states and error handling
- Responsive design with Tailwind CSS
- Accessibility features

### Mental Health Focus
- PHQ-9 depression screening
- Baseline mood assessment
- Emergency contact collection
- Crisis detection preparation
- Privacy-conscious design

## Usage

### Basic Setup
```tsx
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './hooks/useAuth';

function App() {
  return (
    <AuthProvider>
      <YourApp />
    </AuthProvider>
  );
}

function YourComponent() {
  const { state, login, logout } = useAuth();
  
  if (state.isLoading) return <div>Loading...</div>;
  if (!state.isAuthenticated) return <div>Please log in</div>;
  
  return <div>Welcome, {state.user?.email}!</div>;
}
```

### Protected Routes
```tsx
import { withAuth } from './context/AuthContext';

const ProtectedComponent = withAuth(YourComponent);
```

### Form Validation
```tsx
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import { loginValidationSchema } from './hooks/useAuth';

const { register, handleSubmit, formState: { errors } } = useForm({
  resolver: yupResolver(loginValidationSchema)
});
```

## API Integration

The authentication system integrates with the FastAPI backend:

- **Login**: `POST /api/v1/auth/login`
- **Register**: `POST /api/v1/auth/register`
- **Refresh**: `POST /api/v1/auth/refresh`
- **Logout**: `POST /api/v1/auth/logout`
- **Profile**: `GET /api/v1/auth/profile`

## Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Dependencies

- `react-hook-form`: Form handling and validation
- `@hookform/resolvers`: Yup integration for React Hook Form
- `yup`: Schema validation
- `next`: React framework
- `typescript`: Type safety

## Error Handling

The system includes comprehensive error handling:

- **Network Errors**: Automatic retry with exponential backoff
- **Validation Errors**: Field-specific error messages
- **Authentication Errors**: Clear error messages with recovery options
- **Boundary Errors**: Graceful fallback UI for unexpected errors

## Security Considerations

- Tokens are stored securely in localStorage
- Automatic token refresh prevents session expiration
- Input validation prevents malicious data
- Error messages don't expose sensitive information
- Rate limiting prevents brute force attacks
