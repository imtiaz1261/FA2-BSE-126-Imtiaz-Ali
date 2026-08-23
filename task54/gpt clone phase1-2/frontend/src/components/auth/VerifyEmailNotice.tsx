import React, { useEffect, useState } from "react";
import { Button } from "@chatline/design-system/components/Button";
import { AuthCard } from "./AuthCard";
import { authApi } from "@/lib/api";
import { authErrorMessage, useAuth } from "@/hooks/useAuth";

type Status = "pending" | "verifying" | "success" | "error";

/**
 * Two jobs in one component:
 * - No `token` prop: shown right after signup, telling the user to check
 *   their inbox.
 * - `token` prop present (user landed on /verify-email?token=... from the
 *   email link): automatically confirms the token with the backend.
 */
export function VerifyEmailNotice({ token }: { token?: string }) {
  const { refreshUser, user } = useAuth();
  const [status, setStatus] = useState<Status>(token ? "verifying" : "pending");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        await authApi.verifyEmail(token);
        await refreshUser();
        setStatus("success");
      } catch (err) {
        setError(authErrorMessage(err));
        setStatus("error");
      }
    })();
  }, [token, refreshUser]);

  if (status === "verifying") {
    return <AuthCard title="Verifying your email…">{null}</AuthCard>;
  }

  if (status === "success") {
    return (
      <AuthCard title="Email verified" subtitle="You're all set.">
        <p className="text-body text-ink/70 dark:text-ink-dark/70">
          Thanks for confirming, {user?.name ?? "there"}.
        </p>
      </AuthCard>
    );
  }

  if (status === "error") {
    return (
      <AuthCard title="Verification failed">
        <p className="text-meta text-danger">{error}</p>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Check your email" subtitle="We've sent a verification link to your inbox.">
      <p className="mb-4 text-body text-ink/70 dark:text-ink-dark/70">
        Click the link in the email to verify your account. The link expires in 24 hours.
      </p>
      <Button variant="secondary" className="w-full" onClick={() => window.location.reload()}>
        I've verified — refresh
      </Button>
    </AuthCard>
  );
}
