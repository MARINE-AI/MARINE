'use client';

import { SessionProvider } from 'next-auth/react';
import React from 'react';

interface SessionProviderWrapperProps {
  children: React.ReactNode;
}

const SessionProviderWrapper: React.FC<SessionProviderWrapperProps> = ({ children }) => {
  return <SessionProvider>{children}</SessionProvider>;
};

export default SessionProviderWrapper;
