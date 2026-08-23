import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@chatline/design-system/components/Button";
import { Input } from "@chatline/design-system/components/Input";
import { AuthCard } from "./AuthCard";
import { OAuthButtons } from "./OAuthButtons";
import { LoginValues, loginSchema } from "@/lib/schemas";
import { authErrorMessage, useAuth } from "@/hooks/useAuth";

export function LoginForm({
  onSwitchToSignup,
  onForgotPassword,
}: {
  onSwitchToSignup: () => void;
  onForgotPassword: () => void;
}) {
  const { login } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (values: LoginValues) => {
    setFormError(null);
    try {
      await login(values.email, values.password);
    } catch (err) {
      // Backend intentionally returns the same message for "no such user"
      // and "wrong password" to avoid leaking which emails are registered.
      setFormError(authErrorMessage(err));
    }
  };

  return (
    <AuthCard
      title="Welcome back"
      subtitle="Log in to continue your conversations."
      footer={
        <>
          Don't have an account?{" "}
          <button
            type="button"
            onClick={onSwitchToSignup}
            className="font-medium text-accent-600 dark:text-accent-400 hover:underline"
          >
            Sign up
          </button>
        </>
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
        <div className="flex flex-col gap-1.5">
          <Input
            label="Password"
            type="password"
            placeholder="Your password"
            autoComplete="current-password"
            {...register("password")}
            errorText={errors.password?.message}
          />
          <button
            type="button"
            onClick={onForgotPassword}
            className="self-end text-meta font-medium text-accent-600 dark:text-accent-400 hover:underline"
          >
            Forgot password?
          </button>
        </div>

        {formError && (
          <p role="alert" className="text-meta text-danger">
            {formError}
          </p>
        )}

        <Button type="submit" variant="primary" className="w-full" loading={isSubmitting}>
          Log in
        </Button>
      </form>

      <div className="my-4 flex items-center gap-3">
        <div className="h-px flex-1 bg-border dark:bg-border-dark" />
        <span className="text-meta text-ink/50 dark:text-ink-dark/50">or</span>
        <div className="h-px flex-1 bg-border dark:bg-border-dark" />
      </div>

      <OAuthButtons />
    </AuthCard>
  );
}
