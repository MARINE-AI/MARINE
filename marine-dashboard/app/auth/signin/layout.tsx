"use client";

import AuthWrapper from "../../components/auth-wrapper";
import SessionProviderWrapper from "../../components/session-provider-wrapper";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
      </head>
      <body>
        <SessionProviderWrapper>
          <AuthWrapper>{children}</AuthWrapper>
        </SessionProviderWrapper>
      </body>
    </html>
  );
}
