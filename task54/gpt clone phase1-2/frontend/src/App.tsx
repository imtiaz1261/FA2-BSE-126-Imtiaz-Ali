import React, { useEffect, useState } from "react";
import { AuthProvider, useAuth } from "@/hooks/useAuth";
import { LoginForm } from "@/components/auth/LoginForm";
import { SignupForm } from "@/components/auth/SignupForm";
import { ForgotPasswordForm } from "@/components/auth/ForgotPasswordForm";
import { ResetPasswordForm } from "@/components/auth/ResetPasswordForm";
import { VerifyEmailNotice } from "@/components/auth/VerifyEmailNotice";
import { OnboardingModal } from "@/components/onboarding/OnboardingModal";
import { ChatWindow } from "@/features/chat/components/ChatWindow";
import { ThemeProvider } from "@chatline/design-system/theme/ThemeProvider";
import { AdminRoute } from "@/components/admin/AdminRoute";
import { AdminOverview } from "@/pages/admin/AdminOverview";
import { AdminUsers } from "@/pages/admin/AdminUsers";
import { AdminUserDetails } from "@/pages/admin/AdminUserDetails";
import { AdminModeration } from "@/pages/admin/AdminModeration";
import { AdminBilling } from "@/pages/admin/AdminBilling";

// Simple route guard since we're not using react-router
const Navigate = ({ to }: { to: string; replace?: boolean }) => {
  useEffect(() => {
    window.location.href = to;
  }, [to]);
  return null;
};

/**
 * Minimal illustrative router — swap for react-router / your framework's
 * router in a real app. This just switches on `window.location.pathname`
 * so the whole auth module is runnable as-is.
 */
type Screen = "login" | "signup" | "forgot-password" | "reset-password" | "verify-email";

function getInitialScreen(): Screen {
  const path = window.location.pathname;
  if (path === "/signup") return "signup";
  if (path === "/forgot-password") return "forgot-password";
  if (path === "/reset-password") return "reset-password";
  if (path === "/verify-email") return "verify-email";
  return "login";
}

function AuthGate() {
  const { user, isLoading, setSessionFromOAuth } = useAuth();
  const [screen, setScreen] = useState<Screen>(getInitialScreen);
  const [showOnboarding, setShowOnboarding] = useState(false);

  const params = new URLSearchParams(window.location.search);
  const token = params.get("token") ?? undefined;
  const path = window.location.pathname;

  useEffect(() => {
    // Handle the OAuth callback: the access token arrives as a URL fragment
    // (see backend/app/routers/oauth.py) rather than a query param, since
    // fragments are never sent to the server or logged.
    if (window.location.pathname === "/oauth/complete") {
      const fragment = new URLSearchParams(window.location.hash.slice(1));
      const accessToken = fragment.get("access_token");
      // Strip the fragment from the URL immediately so the token never lingers
      // in browser history, regardless of whether setSessionFromOAuth succeeds.
      window.history.replaceState({}, "", "/");
      if (accessToken) {
        setSessionFromOAuth(accessToken).catch(() => {
          // Session couldn't be established (e.g. expired token) — the user
          // simply lands back on the login screen since `user` stays null.
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (user && !user.onboarding_completed) setShowOnboarding(true);
  }, [user]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas dark:bg-canvas-dark">
        <p className="text-body text-ink/60 dark:text-ink-dark/60">Loading…</p>
      </div>
    );
  }

  // Handle admin routes
  if (path.startsWith("/admin")) {
    if (!user) return <Navigate to="/login" replace />;
    if (user.role !== "admin") return <Navigate to="/" replace />;

    if (path === "/admin") {
      return <AdminOverview />;
    }
    if (path === "/admin/users") {
      return <AdminUsers />;
    }
    if (path.startsWith("/admin/users/")) {
      const userId = path.split("/").pop();
      return <AdminUserDetails />;
    }
    if (path === "/admin/moderation") {
      return <AdminModeration />;
    }
    if (path === "/admin/billing") {
      return <AdminBilling />;
    }
  }

  if (user) {
    return (
      <>
        <div className="h-screen">
          <ChatWindow userName={user.name || user.email} />
        </div>
        <OnboardingModal open={showOnboarding} onComplete={() => setShowOnboarding(false)} />
      </>
    );
  }

  switch (screen) {
    case "signup":
      return <SignupForm onSwitchToLogin={() => setScreen("login")} />;
    case "forgot-password":
      return <ForgotPasswordForm onBackToLogin={() => setScreen("login")} />;
    case "reset-password":
      return token ? (
        <ResetPasswordForm token={token} onDone={() => setScreen("login")} />
      ) : (
        <ForgotPasswordForm onBackToLogin={() => setScreen("login")} />
      );
    case "verify-email":
      return <VerifyEmailNotice token={token} />;
    default:
      return (
        <LoginForm
          onSwitchToSignup={() => setScreen("signup")}
          onForgotPassword={() => setScreen("forgot-password")}
        />
      );
  }
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AuthGate />
      </AuthProvider>
    </ThemeProvider>
  );
}
