import { z } from "zod";
/**
 * Mirrors the backend's password rule (schemas.py::validate_password_strength)
 * so the user sees the same requirement inline, before submitting.
 */
export const passwordSchema = z
    .string()
    .min(8, "Must be at least 8 characters.")
    .regex(/[A-Z]/, "Must include an uppercase letter.")
    .regex(/[a-z]/, "Must include a lowercase letter.")
    .regex(/\d/, "Must include a number.");
export const signupSchema = z.object({
    name: z.string().min(1, "Enter your name.").max(120).optional().or(z.literal("")),
    email: z.string().min(1, "Enter your email.").email("Enter a valid email address."),
    password: passwordSchema,
});
export const loginSchema = z.object({
    email: z.string().min(1, "Enter your email.").email("Enter a valid email address."),
    password: z.string().min(1, "Enter your password."),
});
export const forgotPasswordSchema = z.object({
    email: z.string().min(1, "Enter your email.").email("Enter a valid email address."),
});
export const resetPasswordSchema = z
    .object({
    password: passwordSchema,
    confirmPassword: z.string().min(1, "Confirm your new password."),
})
    .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match.",
    path: ["confirmPassword"],
});
export const onboardingSchema = z.object({
    name: z.string().min(1, "Enter your name.").max(120),
    useCase: z.string().min(1, "Choose what you're here for."),
    themePreference: z.enum(["light", "dark", "system"]),
    dataUsageOptIn: z.boolean(),
});
