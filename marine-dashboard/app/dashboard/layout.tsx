"use client";

import SessionProviderWrapper from "@/app/components/session-provider-wrapper";
import AuthWrapper from "@/app/components/auth-wrapper";
import Sidebar from "../components/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SessionProviderWrapper>
        <Sidebar />
      <AuthWrapper>{children}</AuthWrapper>
    </SessionProviderWrapper>
  );
}
