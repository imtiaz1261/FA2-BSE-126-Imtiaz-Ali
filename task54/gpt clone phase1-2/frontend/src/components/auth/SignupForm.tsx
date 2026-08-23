import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@chatline/design-system/components/Button";
import { Input } from "@chatline/design-system/components/Input";
import { AuthCard } from "./AuthCard";
import { OAuthButtons } from "./OAuthButtons";
import { SignupValues, signupSchema } from "@/lib/schemas";
import { authErrorMessage, useAuth } from "@/hooks/useAuth";

export function SignupForm({ onSwitchToLogin }: { onSwitchToLogin: () => void }) {
  const { signup } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupValues>({ resolver: zodResolver(signupSchema) });

  const onSubmit = async (values: SignupValues) => {
    setFormError(null);
    try {
      await signup(values.email, values.password, values.name || undefined);
      // Successful signup logs the user in immediately (see backend
      // /auth/signup); the caller can now show the "verify your email" /
      // onboarding flow based on `user.is_verified` / `onboarding_completed`.
    } catch (err) {
      setFormError(authErrorMessage(err));
    }
  };

  return (
    <AuthCard
      title="Create your account"
      subtitle="Start chatting in under a minute."
      footer={
        <>
          Already have an account?{" "}
          <button
            type="button"
            onClick={onSwitchToLogin}
            className="font-medium text-accent-600 dark:text-accent-400 hover:underline"
          >
            Log in
          </button>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <Input label="Name" placeholder="Ada Lovelace" {...register("name")} errorText={errors.name?.message} />
        <Input
          label="Email"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
          {...register("email")}
          errorText={errors.email?.message}
        />
        <Input
          label="Password"
          type="password"
          placeholder="At least 8 characters"
          autoComplete="new-password"
          helperText={!errors.password ? "Use 8+ characters with a mix of case and a number." : undefined}
          {...register("password")}
          errorText={errors.password?.message}
        />

        {formError && (
          <p role="alert" className="text-meta text-danger">
            {formError}
          </p>
        )}

        <Button type="submit" variant="primary" className="w-full" loading={isSubmitting}>
          Create account
        </Button>
      </form>

      <div className="my-4 flex items-center gap-3">
        <div className="h-px flex-1 bg-border dark:bg-border-dark" />
        <span className="text-meta text-ink/50 dark:text-ink-dark/50">or</span>
        <div className="h-px flex-1 bg-border dark:bg-border-dark" />
      </div>

      <OAuthButtons />

      <p className="mt-4 text-center text-meta text-ink/50 dark:text-ink-dark/50">
        By continuing you agree to our Terms and Privacy Policy.
      </p>
    </AuthCard>
  );
}
