import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@chatline/design-system/components/Button";
import { Input } from "@chatline/design-system/components/Input";
import { Modal } from "@/components/ui/Modal";
import { OnboardingValues, onboardingSchema } from "@/lib/schemas";
import { authApi } from "@/lib/api";
import { authErrorMessage, useAuth } from "@/hooks/useAuth";

const USE_CASES = [
  { value: "work", label: "Work & productivity" },
  { value: "learning", label: "Learning & research" },
  { value: "coding", label: "Coding & development" },
  { value: "creative", label: "Creative writing" },
  { value: "personal", label: "Personal use" },
] as const;

const THEMES = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "Match system" },
] as const;

const STEP_LABELS = ["About you", "What you're here for", "Look & feel"];

/**
 * Shown once, right after signup/first login, when `user.onboarding_completed`
 * is false. Not dismissible (see Modal's `dismissible={false}`) — the person
 * completes all 3 steps, matching the "first-run onboarding modal" spec.
 */
export function OnboardingModal({ open, onComplete }: { open: boolean; onComplete: () => void }) {
  const { user, refreshUser } = useAuth();
  const [step, setStep] = useState(0);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    trigger,
    formState: { errors, isSubmitting },
  } = useForm<OnboardingValues>({
    resolver: zodResolver(onboardingSchema),
    defaultValues: {
      name: user?.name ?? "",
      useCase: "",
      themePreference: "system",
      dataUsageOptIn: false,
    },
  });

  const values = watch();

  const goNext = async () => {
    const fieldsByStep: (keyof OnboardingValues)[][] = [["name"], ["useCase"], ["themePreference"]];
    const valid = await trigger(fieldsByStep[step]);
    if (valid) setStep((s) => Math.min(s + 1, STEP_LABELS.length - 1));
  };
  const goBack = () => setStep((s) => Math.max(s - 1, 0));

  const onSubmit = async (data: OnboardingValues) => {
    setSubmitError(null);
    try {
      await authApi.completeOnboarding({
        name: data.name,
        use_case: data.useCase,
        theme_preference: data.themePreference,
        data_usage_opt_in: data.dataUsageOptIn,
      });
      await refreshUser();
      onComplete();
    } catch (err) {
      setSubmitError(authErrorMessage(err));
    }
  };

  return (
    <Modal open={open} dismissible={false} title="Set up your account">
      {/* Step indicator */}
      <div className="mb-5 flex items-center gap-2">
        {STEP_LABELS.map((label, i) => (
          <div key={label} className="flex flex-1 items-center gap-2">
            <div
              className={`h-1.5 flex-1 rounded-full ${
                i <= step ? "bg-accent-600 dark:bg-accent-400" : "bg-border dark:bg-border-dark"
              }`}
            />
          </div>
        ))}
      </div>
      <p className="mb-4 text-meta text-ink/60 dark:text-ink-dark/60">
        Step {step + 1} of {STEP_LABELS.length}: {STEP_LABELS[step]}
      </p>

      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        {step === 0 && (
          <div className="flex flex-col gap-4">
            <Input
              label="What should we call you?"
              placeholder="Ada Lovelace"
              {...register("name")}
              errorText={errors.name?.message}
            />
          </div>
        )}

        {step === 1 && (
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 text-meta font-medium text-ink dark:text-ink-dark">
              What will you mostly use Chatline for?
            </legend>
            {USE_CASES.map((option) => (
              <label
                key={option.value}
                className={`flex cursor-pointer items-center gap-3 rounded-control border px-3 py-2.5 text-body transition-colors ${
                  values.useCase === option.value
                    ? "border-accent-600 dark:border-accent-400 bg-accent-600/5"
                    : "border-border dark:border-border-dark hover:border-accent-600/50"
                }`}
              >
                <input
                  type="radio"
                  value={option.value}
                  className="accent-accent-600"
                  {...register("useCase")}
                />
                {option.label}
              </label>
            ))}
            {errors.useCase && <p className="text-meta text-danger">{errors.useCase.message}</p>}
          </fieldset>
        )}

        {step === 2 && (
          <div className="flex flex-col gap-5">
            <fieldset className="flex flex-col gap-2">
              <legend className="mb-1 text-meta font-medium text-ink dark:text-ink-dark">
                Choose a theme
              </legend>
              <div className="flex gap-2">
                {THEMES.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setValue("themePreference", option.value, { shouldValidate: true })}
                    className={`flex-1 rounded-control border px-3 py-2 text-meta font-medium transition-colors ${
                      values.themePreference === option.value
                        ? "border-accent-600 dark:border-accent-400 text-accent-600 dark:text-accent-400"
                        : "border-border dark:border-border-dark text-ink/70 dark:text-ink-dark/70"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </fieldset>

            <label className="flex items-start gap-3 text-body">
              <input
                type="checkbox"
                className="mt-1 accent-accent-600"
                {...register("dataUsageOptIn")}
              />
              <span className="text-ink/80 dark:text-ink-dark/80">
                Help improve Chatline by allowing my conversations to be used for
                model improvement. You can change this anytime in Settings.
              </span>
            </label>
          </div>
        )}

        {submitError && (
          <p role="alert" className="mt-4 text-meta text-danger">
            {submitError}
          </p>
        )}

        <div className="mt-6 flex justify-between gap-2">
          <Button type="button" variant="ghost" onClick={goBack} disabled={step === 0}>
            Back
          </Button>
          {step < STEP_LABELS.length - 1 ? (
            <Button type="button" variant="primary" onClick={goNext}>
              Continue
            </Button>
          ) : (
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Finish setup
            </Button>
          )}
        </div>
      </form>
    </Modal>
  );
}
