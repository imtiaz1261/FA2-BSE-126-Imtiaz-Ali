import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@chatline/design-system/components/Button";
import { Input } from "@chatline/design-system/components/Input";
import { AuthCard } from "./AuthCard";
import { ResetPasswordValues, resetPasswordSchema } from "@/lib/schemas";
import { authErrorMessage } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";

/** `token` comes from the ?token= query param on the /reset-password page. */
export function ResetPasswordForm({ token, onDone }: { token: string; onDone: () => void }) {
  const [done, setDone] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordValues>({ resolver: zodResolver(resetPasswordSchema) });

  const onSubmit = async (values: ResetPasswordValues) => {
    setFormError(null);
    try {
      await authApi.resetPassword(token, values.password);
      setDone(true);
    } catch (err) {
      setFormError(authErrorMessage(err));
    }
  };

  if (done) {
    return (
      <AuthCard title="Password updated" subtitle="Log in with your new password.">
        <Button variant="primary" className="w-full" onClick={onDone}>
          Continue to log in
        </Button>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Choose a new password">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <Input
          label="New password"
          type="password"
          autoComplete="new-password"
          helperText={!errors.password ? "Use 8+ characters with a mix of case and a number." : undefined}
          {...register("password")}
          errorText={errors.password?.message}
        />
        <Input
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          {...register("confirmPassword")}
          errorText={errors.confirmPassword?.message}
        />
        {formError && (
          <p role="alert" className="text-meta text-danger">
            {formError}
          </p>
        )}
        <Button type="submit" variant="primary" className="w-full" loading={isSubmitting}>
          Reset password
        </Button>
      </form>
    </AuthCard>
  );
}
