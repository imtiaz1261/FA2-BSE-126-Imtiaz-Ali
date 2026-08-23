import React from "react";
import { Card } from "@chatline/design-system/components/Card";

export function AuthCard({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas-panel dark:bg-canvas-dark px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <h1 className="text-display font-semibold text-ink dark:text-ink-dark">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-1 text-body text-ink/60 dark:text-ink-dark/60">{subtitle}</p>
          )}
        </div>
        <Card className="p-6">{children}</Card>
        {footer && (
          <p className="mt-4 text-center text-meta text-ink/60 dark:text-ink-dark/60">
            {footer}
          </p>
        )}
      </div>
    </div>
  );
}
