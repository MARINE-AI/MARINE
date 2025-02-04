"use client";

import SessionProviderWrapper from "@/components/session-provider-wrapper";
import AuthWrapper from "@/components/auth-wrapper";
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
