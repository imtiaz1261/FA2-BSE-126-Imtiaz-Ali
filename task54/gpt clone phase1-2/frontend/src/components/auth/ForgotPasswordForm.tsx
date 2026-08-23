import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@chatline/design-system/components/Button";
import { Input } from "@chatline/design-system/components/Input";
import { AuthCard } from "./AuthCard";
import { ForgotPasswordValues, forgotPasswordSchema } from "@/lib/schemas";
import { authErrorMessage } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";

export function ForgotPasswordForm({ onBackToLogin }: { onBackToLogin: () => void }) {
  const [sent, setSent] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordValues>({ resolver: zodResolver(forgotPasswordSchema) });

  const onSubmit = async (values: ForgotPasswordValues) => {
    setFormError(null);
    try {
      await authApi.forgotPassword(values.email);
      setSent(true); // backend always returns the same neutral message
    } catch (err) {
      setFormError(authErrorMessage(err));
    }
  };

  if (sent) {
    return (
      <AuthCard title="Check your email" subtitle="We've sent a password reset link if that account exists.">
        <Button variant="secondary" className="w-full" onClick={onBackToLogin}>
          Back to log in
        </Button>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Reset your password"
      subtitle="Enter your email and we'll send you a reset link."
      footer={
        <button
          type="button"
          onClick={onBackToLogin}
          className="font-medium text-accent-600 dark:text-accent-400 hover:underline"
        >
          Back to log in
        </button>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <Input
          label="Email"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
          {...register("email")}
          errorText={errors.email?.message}
        />
        {formError && (
          <p role="alert" className="text-meta text-danger">
            {formError}
          </p>
        )}
        <Button type="submit" variant="primary" className="w-full" loading={isSubmitting}>
          Send reset link
        </Button>
      </form>
    </AuthCard>
  );
}
