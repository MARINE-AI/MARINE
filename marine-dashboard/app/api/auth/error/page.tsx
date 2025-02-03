'use client';

import { useSearchParams } from 'next/navigation';

export default function ErrorPage() {
  const searchParams = useSearchParams();
  const error = searchParams.get('error');

  let errorMessage = 'An unknown error occurred.';
  
  if (error === 'AccessDenied') {
    errorMessage = 'You do not have permission to sign in. Please use a @vitstudent.ac.in email.';
  }

  return (
    <div className="flex items-center justify-center h-screen bg-black text-white">
      <div className="text-center">
        <h1 className="text-2xl mb-4">Access Denied</h1>
        <p className="mb-4">{errorMessage}</p>
        <a href="/auth/signin" className="text-blue-500">Go back to sign in</a>
      </div>
    </div>
  );
}
