'use client';

import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth, RegisterData, AuthError, calculatePasswordStrength } from '../../../hooks/useAuth';
import { ErrorBoundary } from '../../../components/ErrorBoundary';

// Step validation schemas
const credentialsSchema = yup.object({
  email: yup
    .string()
    .required('Email is required')
    .email('Invalid email address'),
  password: yup
    .string()
    .required('Password is required')
    .min(8, 'Password must be at least 8 characters')
    .matches(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
      'Password must contain uppercase, lowercase, number, and special character'
    ),
  confirm_password: yup
    .string()
    .required('Password confirmation is required')
    .oneOf([yup.ref('password')], 'Passwords must match'),
});

const profileSchema = yup.object({
  emergency_contact_name: yup
    .string()
    .required('Emergency contact name is required')
    .min(2, 'Name must be at least 2 characters'),
  emergency_contact_phone: yup
    .string()
    .required('Emergency contact phone is required')
    .matches(/^\+?[\d\s\-\(\)]+$/, 'Invalid phone number format'),
});

const preferencesSchema = yup.object({
  privacy_settings: yup.object({
    profile_visibility: yup
      .string()
      .oneOf(['public', 'private', 'friends_only'])
      .required('Profile visibility is required'),
    data_sharing: yup.boolean().required(),
    analytics_tracking: yup.boolean().required(),
    marketing_emails: yup.boolean().required(),
  }),
  terms_accepted: yup
    .boolean()
    .oneOf([true], 'You must accept the terms of service')
    .required(),
  privacy_policy_accepted: yup
    .boolean()
    .oneOf([true], 'You must accept the privacy policy')
    .required(),
});

const fullSchema = credentialsSchema.concat(profileSchema).concat(preferencesSchema);

type RegisterFormData = yup.InferType<typeof fullSchema>;

// Error boundary component
class RegisterErrorBoundary extends ErrorBoundary {
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full space-y-8 p-8">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-red-600 mb-4">
                Something went wrong
              </h2>
              <p className="text-gray-600 mb-4">
                We encountered an error while loading the registration page.
              </p>
              <button
                onClick={() => window.location.reload()}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const steps = [
  { id: 'credentials', title: 'Account Details', description: 'Create your account' },
  { id: 'profile', title: 'Profile Setup', description: 'Add emergency contact' },
  { id: 'preferences', title: 'Preferences', description: 'Configure your settings' },
];

export default function RegisterPage() {
  const router = useRouter();
  const { register: registerUser, state, clearError } = useAuth();
  const [currentStep, setCurrentStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
    setError,
    trigger,
  } = useForm<RegisterFormData>({
    resolver: yupResolver(fullSchema),
    mode: 'onChange',
  });

  const watchedPassword = watch('password', '');
  const passwordStrength = calculatePasswordStrength(watchedPassword);

  // Redirect if already authenticated
  useEffect(() => {
    if (state.isAuthenticated && !state.isLoading) {
      router.push('/dashboard');
    }
  }, [state.isAuthenticated, state.isLoading, router]);

  // Clear errors when component mounts
  useEffect(() => {
    clearError();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  // Set default values
  useEffect(() => {
    setValue('privacy_settings.profile_visibility', 'private');
    setValue('privacy_settings.data_sharing', false);
    setValue('privacy_settings.analytics_tracking', true);
    setValue('privacy_settings.marketing_emails', false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  const nextStep = async () => {
    let isValid = false;
    
    if (currentStep === 0) {
      isValid = await trigger(['email', 'password', 'confirm_password']);
    } else if (currentStep === 1) {
      isValid = await trigger(['emergency_contact_name', 'emergency_contact_phone']);
    }
    
    if (isValid) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    setCurrentStep(currentStep - 1);
  };

  const onSubmit = async (data: RegisterFormData) => {
    setIsSubmitting(true);
    clearError();

    try {
      await registerUser(data as RegisterData);
      router.push('/auth/onboarding');
    } catch (error) {
      const authError = error as AuthError;
      
      if (authError.code === 'VALIDATION_ERROR') {
        // Handle field-specific validation errors
        Object.keys(authError.details || {}).forEach(field => {
          setError(field as keyof RegisterFormData, { message: authError.details?.[field] || 'Validation error' });
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const getPasswordStrengthColor = (strength: string) => {
    switch (strength) {
      case 'weak': return 'bg-red-500';
      case 'fair': return 'bg-yellow-500';
      case 'good': return 'bg-blue-500';
      case 'strong': return 'bg-green-500';
      default: return 'bg-gray-300';
    }
  };

  if (state.isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <RegisterErrorBoundary>
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl w-full space-y-8">
          <div>
            <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
              Create your account
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600">
              Already have an account?{' '}
              <Link
                href="/auth/login"
                className="font-medium text-blue-600 hover:text-blue-500"
              >
                Sign in here
              </Link>
            </p>
          </div>

          {/* Progress indicator */}
          <div className="mb-8">
            <div className="flex items-center justify-between">
              {steps.map((step, index) => (
                <div key={step.id} className="flex items-center">
                  <div
                    className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
                      index <= currentStep
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-300 text-gray-500'
                    }`}
                  >
                    {index + 1}
                  </div>
                  <div className="ml-2">
                    <p className={`text-sm font-medium ${
                      index <= currentStep ? 'text-blue-600' : 'text-gray-500'
                    }`}>
                      {step.title}
                    </p>
                    <p className="text-xs text-gray-500">{step.description}</p>
                  </div>
                  {index < steps.length - 1 && (
                    <div className={`w-16 h-0.5 mx-4 ${
                      index < currentStep ? 'bg-blue-600' : 'bg-gray-300'
                    }`} />
                  )}
                </div>
              ))}
            </div>
          </div>

          <form className="mt-8 space-y-6" onSubmit={handleSubmit(onSubmit)}>
            {/* Step 1: Credentials */}
            {currentStep === 0 && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Account Details</h3>
                
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                    Email address
                  </label>
                  <input
                    {...register('email')}
                    type="email"
                    autoComplete="email"
                    className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="Enter your email"
                  />
                  {errors.email && (
                    <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                    Password
                  </label>
                  <div className="mt-1 relative">
                    <input
                      {...register('password')}
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      className="appearance-none relative block w-full px-3 py-2 pr-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      placeholder="Create a strong password"
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 pr-3 flex items-center"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? (
                        <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                        </svg>
                      ) : (
                        <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      )}
                    </button>
                  </div>
                  
                  {/* Password strength indicator */}
                  {watchedPassword && (
                    <div className="mt-2">
                      <div className="flex items-center space-x-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full transition-all duration-300 ${getPasswordStrengthColor(passwordStrength.strength)}`}
                            style={{ width: `${(passwordStrength.score / 6) * 100}%` }}
                          />
                        </div>
                        <span className={`text-xs font-medium ${
                          passwordStrength.strength === 'weak' ? 'text-red-600' :
                          passwordStrength.strength === 'fair' ? 'text-yellow-600' :
                          passwordStrength.strength === 'good' ? 'text-blue-600' :
                          'text-green-600'
                        }`}>
                          {passwordStrength.strength}
                        </span>
                      </div>
                      {passwordStrength.feedback.length > 0 && (
                        <ul className="mt-1 text-xs text-gray-600">
                          {passwordStrength.feedback.map((item, index) => (
                            <li key={index} className="flex items-center">
                              <span className="text-red-500 mr-1">•</span>
                              {item}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                  
                  {errors.password && (
                    <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="confirm_password" className="block text-sm font-medium text-gray-700">
                    Confirm Password
                  </label>
                  <div className="mt-1 relative">
                    <input
                      {...register('confirm_password')}
                      type={showConfirmPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      className="appearance-none relative block w-full px-3 py-2 pr-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      placeholder="Confirm your password"
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 pr-3 flex items-center"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    >
                      {showConfirmPassword ? (
                        <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                        </svg>
                      ) : (
                        <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      )}
                    </button>
                  </div>
                  {errors.confirm_password && (
                    <p className="mt-1 text-sm text-red-600">{errors.confirm_password.message}</p>
                  )}
                </div>
              </div>
            )}

            {/* Step 2: Profile */}
            {currentStep === 1 && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Emergency Contact</h3>
                <p className="text-sm text-gray-600 mb-4">
                  We&apos;ll use this information to contact someone if we detect signs of crisis.
                </p>
                
                <div>
                  <label htmlFor="emergency_contact_name" className="block text-sm font-medium text-gray-700">
                    Emergency Contact Name
                  </label>
                  <input
                    {...register('emergency_contact_name')}
                    type="text"
                    className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="Enter full name"
                  />
                  {errors.emergency_contact_name && (
                    <p className="mt-1 text-sm text-red-600">{errors.emergency_contact_name.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="emergency_contact_phone" className="block text-sm font-medium text-gray-700">
                    Emergency Contact Phone
                  </label>
                  <input
                    {...register('emergency_contact_phone')}
                    type="tel"
                    className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="+1 (555) 123-4567"
                  />
                  {errors.emergency_contact_phone && (
                    <p className="mt-1 text-sm text-red-600">{errors.emergency_contact_phone.message}</p>
                  )}
                </div>
              </div>
            )}

            {/* Step 3: Preferences */}
            {currentStep === 2 && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Privacy & Preferences</h3>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Profile Visibility
                  </label>
                  <div className="space-y-2">
                    {[
                      { value: 'private', label: 'Private - Only you can see your profile' },
                      { value: 'friends_only', label: 'Friends Only - Only connected users can see your profile' },
                      { value: 'public', label: 'Public - Anyone can see your profile' },
                    ].map((option) => (
                      <label key={option.value} className="flex items-center">
                        <input
                          {...register('privacy_settings.profile_visibility')}
                          type="radio"
                          value={option.value}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                        />
                        <span className="ml-2 text-sm text-gray-700">{option.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  <label className="flex items-center">
                    <input
                      {...register('privacy_settings.data_sharing')}
                      type="checkbox"
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      Allow data sharing for research (anonymized)
                    </span>
                  </label>

                  <label className="flex items-center">
                    <input
                      {...register('privacy_settings.analytics_tracking')}
                      type="checkbox"
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      Enable analytics tracking to improve the service
                    </span>
                  </label>

                  <label className="flex items-center">
                    <input
                      {...register('privacy_settings.marketing_emails')}
                      type="checkbox"
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      Receive marketing emails and updates
                    </span>
                  </label>
                </div>

                <div className="border-t pt-4 space-y-3">
                  <label className="flex items-start">
                    <input
                      {...register('terms_accepted')}
                      type="checkbox"
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-1"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      I agree to the{' '}
                      <Link href="/terms" className="text-blue-600 hover:text-blue-500">
                        Terms of Service
                      </Link>
                    </span>
                  </label>
                  {errors.terms_accepted && (
                    <p className="text-sm text-red-600">{errors.terms_accepted.message}</p>
                  )}

                  <label className="flex items-start">
                    <input
                      {...register('privacy_policy_accepted')}
                      type="checkbox"
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-1"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      I agree to the{' '}
                      <Link href="/privacy" className="text-blue-600 hover:text-blue-500">
                        Privacy Policy
                      </Link>
                    </span>
                  </label>
                  {errors.privacy_policy_accepted && (
                    <p className="text-sm text-red-600">{errors.privacy_policy_accepted.message}</p>
                  )}
                </div>
              </div>
            )}

            {/* Global error message */}
            {state.error && (
              <div className="rounded-md bg-red-50 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800">
                      {state.error.message}
                    </h3>
                  </div>
                </div>
              </div>
            )}

            {/* Navigation buttons */}
            <div className="flex justify-between">
              <button
                type="button"
                onClick={prevStep}
                disabled={currentStep === 0}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>

              {currentStep < steps.length - 1 ? (
                <button
                  type="button"
                  onClick={nextStep}
                  className="px-4 py-2 border border-transparent rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Next
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 border border-transparent rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? 'Creating Account...' : 'Create Account'}
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </RegisterErrorBoundary>
  );
}
