'use client';

import React from 'react';

export default function TestPage() {
  const handleClick = () => {
    alert('Button clicked! This is a test alert.');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center space-y-6 p-8">
        <h1 className="text-4xl font-bold text-gray-900">
          Test Page
        </h1>
        
        <p className="text-lg text-gray-600 max-w-md mx-auto">
          This is a test page to verify the Next.js setup.
        </p>
        
        <button
          onClick={handleClick}
          className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 hover:shadow-lg transition-all duration-200 transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Click Me
        </button>
      </div>
    </div>
  );
}
