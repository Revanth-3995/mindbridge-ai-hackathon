'use client';

import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../../hooks/useAuth';
import { ErrorBoundary } from '../../../components/ErrorBoundary';

// PHQ-9 questions (simplified for onboarding)
const phq9Questions = [
  {
    id: 'interest_pleasure',
    question: 'Little interest or pleasure in doing things',
    options: [
      { value: 0, label: 'Not at all' },
      { value: 1, label: 'Several days' },
      { value: 2, label: 'More than half the days' },
      { value: 3, label: 'Nearly every day' },
    ],
  },
  {
    id: 'mood',
    question: 'Feeling down, depressed, or hopeless',
    options: [
      { value: 0, label: 'Not at all' },
      { value: 1, label: 'Several days' },
      { value: 2, label: 'More than half the days' },
      { value: 3, label: 'Nearly every day' },
    ],
  },
  {
    id: 'sleep',
    question: 'Trouble falling or staying asleep, or sleeping too much',
    options: [
      { value: 0, label: 'Not at all' },
      { value: 1, label: 'Several days' },
      { value: 2, label: 'More than half the days' },
      { value: 3, label: 'Nearly every day' },
    ],
  },
  {
    id: 'energy',
    question: 'Feeling tired or having little energy',
    options: [
      { value: 0, label: 'Not at all' },
      { value: 1, label: 'Several days' },
      { value: 2, label: 'More than half the days' },
      { value: 3, label: 'Nearly every day' },
    ],
  },
  {
    id: 'appetite',
    question: 'Poor appetite or overeating',
    options: [
      { value: 0, label: 'Not at all' },
      { value: 1, label: 'Several days' },
      { value: 2, label: 'More than half the days' },
      { value: 3, label: 'Nearly every day' },
    ],
  },
  {
    id: 'self_worth',
    question: 'Feeling bad about yourself or that you are a failure',
    options: [
      { value: 0, label: 'Not at all' },
      { value: 1, label: 'Several days' },
      { value: 2, label: 'More than half the days' },
      { value: 3, label: 'Nearly every day' },
    ],
  },
  {
    id: 'concentration',
    question: 'Trouble concentrating on things',
    options: [
      { value: 0, label: 'Not at all' },
      { value: 1, label: 'Several days' },
      { value: 2, label: 'More than half the days' },
      { value: 3, label: 'Nearly every day' },
    ],
  },
  {
    id: 'psychomotor',
    question: 'Moving or speaking so slowly that other people could have noticed',
    options: [
      { value: 0, label: 'Not at all' },
      { value: 1, label: 'Several days' },
      { value: 2, label: 'More than half the days' },
      { value: 3, label: 'Nearly every day' },
    ],
  },
  {
    id: 'suicidal_thoughts',
    question: 'Thoughts that you would be better off dead or of hurting yourself',
    options: [
      { value: 0, label: 'Not at all' },
      { value: 1, label: 'Several days' },
      { value: 2, label: 'More than half the days' },
      { value: 3, label: 'Nearly every day' },
    ],
  },
];

// Validation schema
const onboardingSchema = yup.object({
  baseline_mood: yup
    .string()
    .oneOf(['very_negative', 'negative', 'neutral', 'positive', 'very_positive'])
    .required('Please select your baseline mood'),
  emergency_contact_name: yup
    .string()
    .required('Emergency contact name is required'),
  emergency_contact_phone: yup
    .string()
    .required('Emergency contact phone is required'),
  notification_preferences: yup.object({
    email_notifications: yup.boolean().required(),
    push_notifications: yup.boolean().required(),
    crisis_alerts: yup.boolean().required(),
    weekly_reports: yup.boolean().required(),
  }),
  privacy_settings: yup.object({
    profile_visibility: yup
      .string()
      .oneOf(['public', 'private', 'friends_only'])
      .required(),
    data_sharing: yup.boolean().required(),
    analytics_tracking: yup.boolean().required(),
    marketing_emails: yup.boolean().required(),
  }),
  phq9_responses: yup.object().shape(
    phq9Questions.reduce((acc, question) => {
      acc[question.id] = yup.number().min(0).max(3).required();
      return acc;
    }, {} as Record<string, yup.NumberSchema>)
  ),
});

type OnboardingFormData = yup.InferType<typeof onboardingSchema>;

// Error boundary component
class OnboardingErrorBoundary extends ErrorBoundary {
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
                We encountered an error while loading the onboarding page.
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
  { id: 'welcome', title: 'Welcome', description: 'Get started with Mind Bridge AI' },
  { id: 'mood', title: 'Mood Assessment', description: 'Help us understand your baseline' },
  { id: 'emergency', title: 'Emergency Contact', description: 'Safety first' },
  { id: 'preferences', title: 'Preferences', description: 'Customize your experience' },
  { id: 'tutorial', title: 'Tutorial', description: 'Learn how to use the app' },
];

export default function OnboardingPage() {
  const router = useRouter();
  const { state, updateUser } = useAuth();
  const [currentStep, setCurrentStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [phq9Score, setPhq9Score] = useState(0);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
    trigger,
  } = useForm<OnboardingFormData>({
    resolver: yupResolver(onboardingSchema),
    mode: 'onChange',
  });

  const watchedPhq9 = watch('phq9_responses');

  // Calculate PHQ-9 score
  useEffect(() => {
    if (watchedPhq9) {
      const score = Object.values(watchedPhq9).reduce((sum, value) => (sum || 0) + (value || 0), 0);
      setPhq9Score(score || 0);
    }
  }, [watchedPhq9]);

  // Redirect if not authenticated
  useEffect(() => {
    if (!state.isAuthenticated && !state.isLoading) {
      router.push('/auth/login');
    }
  }, [state.isAuthenticated, state.isLoading, router]);

  // Set default values
  useEffect(() => {
    setValue('notification_preferences.email_notifications', true);
    setValue('notification_preferences.push_notifications', true);
    setValue('notification_preferences.crisis_alerts', true);
    setValue('notification_preferences.weekly_reports', false);
    setValue('privacy_settings.profile_visibility', 'private');
    setValue('privacy_settings.data_sharing', false);
    setValue('privacy_settings.analytics_tracking', true);
    setValue('privacy_settings.marketing_emails', false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  const nextStep = async () => {
    let isValid = false;
    
    if (currentStep === 1) {
      isValid = await trigger(['baseline_mood']);
    } else if (currentStep === 2) {
      isValid = await trigger(['phq9_responses']);
    } else if (currentStep === 3) {
      isValid = await trigger(['emergency_contact_name', 'emergency_contact_phone']);
    } else if (currentStep === 4) {
      isValid = await trigger(['notification_preferences', 'privacy_settings']);
    }
    
    if (isValid) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    setCurrentStep(currentStep - 1);
  };

  const onSubmit = async (data: OnboardingFormData) => {
    setIsSubmitting(true);

    try {
      // Update user profile with onboarding data
      const updatedUser = {
        ...state.user!,
        baseline_mood: data.baseline_mood,
        emergency_contact_name: data.emergency_contact_name,
        emergency_contact_phone: data.emergency_contact_phone,
        privacy_settings: data.privacy_settings,
      };

      updateUser(updatedUser);

      // TODO: Send PHQ-9 responses to backend
      console.log('PHQ-9 responses:', data.phq9_responses);
      console.log('PHQ-9 score:', phq9Score);

      // Redirect to dashboard
      router.push('/dashboard');
    } catch (error) {
      console.error('Onboarding error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getPhq9Severity = (score: number) => {
    if (score <= 4) return { level: 'Minimal', color: 'text-green-600' };
    if (score <= 9) return { level: 'Mild', color: 'text-yellow-600' };
    if (score <= 14) return { level: 'Moderate', color: 'text-orange-600' };
    if (score <= 19) return { level: 'Moderately Severe', color: 'text-red-600' };
    return { level: 'Severe', color: 'text-red-800' };
  };

  if (state.isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!state.isAuthenticated) {
    return null;
  }

  return (
    <OnboardingErrorBoundary>
      <div className="min-h-screen bg-gray-50">
        {/* Progress bar */}
        <div className="bg-white shadow">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center">
                <h1 className="text-xl font-semibold text-gray-900">Mind Bridge AI</h1>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-500">
                  Step {currentStep + 1} of {steps.length}
                </span>
                <div className="w-32 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
          <form onSubmit={handleSubmit(onSubmit)}>
            {/* Step 1: Welcome */}
            {currentStep === 0 && (
              <div className="text-center space-y-6">
                <div className="mx-auto h-24 w-24 bg-blue-100 rounded-full flex items-center justify-center">
                  <svg className="h-12 w-12 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                  </svg>
                </div>
                <h2 className="text-3xl font-bold text-gray-900">Welcome to Mind Bridge AI</h2>
                  <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                    We&apos;re here to support your mental health journey. Let&apos;s set up your profile 
                    to provide you with personalized care and support.
                  </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
                  <div className="text-center">
                    <div className="mx-auto h-12 w-12 bg-green-100 rounded-full flex items-center justify-center mb-3">
                      <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h3 className="font-semibold text-gray-900">Personalized Care</h3>
                    <p className="text-sm text-gray-600">AI-powered mental health support tailored to you</p>
                  </div>
                  <div className="text-center">
                    <div className="mx-auto h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center mb-3">
                      <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                      </svg>
                    </div>
                    <h3 className="font-semibold text-gray-900">Peer Support</h3>
                    <p className="text-sm text-gray-600">Connect with others on similar journeys</p>
                  </div>
                  <div className="text-center">
                    <div className="mx-auto h-12 w-12 bg-purple-100 rounded-full flex items-center justify-center mb-3">
                      <svg className="h-6 w-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                    </div>
                    <h3 className="font-semibold text-gray-900">Progress Tracking</h3>
                    <p className="text-sm text-gray-600">Monitor your mental health journey</p>
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Mood Assessment */}
            {currentStep === 1 && (
              <div className="space-y-6">
                <div className="text-center">
                  <h2 className="text-2xl font-bold text-gray-900">Baseline Mood Assessment</h2>
                  <p className="text-gray-600 mt-2">
                    Help us understand your current mental state to provide better support.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    How would you describe your overall mood lately?
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
                    {[
                      { value: 'very_negative', label: 'Very Negative', color: 'bg-red-100 text-red-800 border-red-200' },
                      { value: 'negative', label: 'Negative', color: 'bg-orange-100 text-orange-800 border-orange-200' },
                      { value: 'neutral', label: 'Neutral', color: 'bg-gray-100 text-gray-800 border-gray-200' },
                      { value: 'positive', label: 'Positive', color: 'bg-green-100 text-green-800 border-green-200' },
                      { value: 'very_positive', label: 'Very Positive', color: 'bg-blue-100 text-blue-800 border-blue-200' },
                    ].map((option) => (
                      <label key={option.value} className="cursor-pointer">
                        <input
                          {...register('baseline_mood')}
                          type="radio"
                          value={option.value}
                          className="sr-only"
                        />
                        <div className={`p-3 rounded-lg border-2 text-center transition-all ${
                          watch('baseline_mood') === option.value
                            ? `${option.color} border-current`
                            : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300'
                        }`}>
                          <div className="text-sm font-medium">{option.label}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                  {errors.baseline_mood && (
                    <p className="mt-2 text-sm text-red-600">{errors.baseline_mood.message}</p>
                  )}
                </div>
              </div>
            )}

            {/* Step 3: PHQ-9 Assessment */}
            {currentStep === 2 && (
              <div className="space-y-6">
                <div className="text-center">
                  <h2 className="text-2xl font-bold text-gray-900">Mental Health Assessment</h2>
                  <p className="text-gray-600 mt-2">
                    Please answer these questions about how you&apos;ve been feeling over the last 2 weeks.
                  </p>
                </div>

                <div className="space-y-6">
                  {phq9Questions.map((question, index) => (
                    <div key={question.id} className="bg-white p-6 rounded-lg shadow-sm border">
                      <h3 className="text-lg font-medium text-gray-900 mb-4">
                        {index + 1}. {question.question}
                      </h3>
                      <div className="space-y-2">
                        {question.options.map((option) => (
                          <label key={option.value} className="flex items-center">
                            <input
                              {...register(`phq9_responses.${question.id}`)}
                              type="radio"
                              value={option.value}
                              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                            />
                            <span className="ml-3 text-sm text-gray-700">{option.label}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>

                {phq9Score > 0 && (
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <div className="flex items-center">
                      <svg className="h-5 w-5 text-blue-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <div>
                        <p className="text-sm font-medium text-blue-800">
                          Current Assessment Score: {phq9Score}
                        </p>
                        <p className={`text-sm ${getPhq9Severity(phq9Score).color}`}>
                          Severity Level: {getPhq9Severity(phq9Score).level}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Step 4: Emergency Contact */}
            {currentStep === 3 && (
              <div className="space-y-6">
                <div className="text-center">
                  <h2 className="text-2xl font-bold text-gray-900">Emergency Contact</h2>
                  <p className="text-gray-600 mt-2">
                    We&apos;ll use this information to contact someone if we detect signs of crisis.
                  </p>
                </div>

                <div className="bg-white p-6 rounded-lg shadow-sm border space-y-4">
                  <div>
                    <label htmlFor="emergency_contact_name" className="block text-sm font-medium text-gray-700">
                      Emergency Contact Name
                    </label>
                    <input
                      {...register('emergency_contact_name')}
                      type="text"
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500"
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
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="+1 (555) 123-4567"
                    />
                    {errors.emergency_contact_phone && (
                      <p className="mt-1 text-sm text-red-600">{errors.emergency_contact_phone.message}</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Step 5: Preferences */}
            {currentStep === 4 && (
              <div className="space-y-6">
                <div className="text-center">
                  <h2 className="text-2xl font-bold text-gray-900">Notification Preferences</h2>
                  <p className="text-gray-600 mt-2">
                    Choose how you&apos;d like to receive updates and alerts.
                  </p>
                </div>

                <div className="bg-white p-6 rounded-lg shadow-sm border space-y-4">
                  <h3 className="text-lg font-medium text-gray-900">Notifications</h3>
                  
                  {[
                    { key: 'email_notifications', label: 'Email notifications', description: 'Receive updates via email' },
                    { key: 'push_notifications', label: 'Push notifications', description: 'Receive push notifications on your device' },
                    { key: 'crisis_alerts', label: 'Crisis alerts', description: 'Important safety alerts (recommended)' },
                    { key: 'weekly_reports', label: 'Weekly reports', description: 'Weekly summary of your progress' },
                  ].map((pref) => (
                    <label key={pref.key} className="flex items-start">
                      <input
                        {...register(`notification_preferences.${pref.key}` as keyof OnboardingFormData)}
                        type="checkbox"
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-1"
                      />
                      <div className="ml-3">
                        <div className="text-sm font-medium text-gray-700">{pref.label}</div>
                        <div className="text-sm text-gray-500">{pref.description}</div>
                      </div>
                    </label>
                  ))}
                </div>

                <div className="bg-white p-6 rounded-lg shadow-sm border space-y-4">
                  <h3 className="text-lg font-medium text-gray-900">Privacy Settings</h3>
                  
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
                    {[
                      { key: 'data_sharing', label: 'Allow data sharing for research (anonymized)' },
                      { key: 'analytics_tracking', label: 'Enable analytics tracking to improve the service' },
                      { key: 'marketing_emails', label: 'Receive marketing emails and updates' },
                    ].map((pref) => (
                      <label key={pref.key} className="flex items-center">
                        <input
                          {...register(`privacy_settings.${pref.key}` as keyof OnboardingFormData)}
                          type="checkbox"
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <span className="ml-2 text-sm text-gray-700">{pref.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Navigation buttons */}
            <div className="flex justify-between mt-8">
              <button
                type="button"
                onClick={prevStep}
                disabled={currentStep === 0}
                className="px-6 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>

              {currentStep < steps.length - 1 ? (
                <button
                  type="button"
                  onClick={nextStep}
                  className="px-6 py-2 border border-transparent rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Next
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-6 py-2 border border-transparent rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? 'Completing Setup...' : 'Complete Setup'}
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </OnboardingErrorBoundary>
  );
}
