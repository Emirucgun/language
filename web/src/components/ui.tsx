// Sade yapı taşları: blueprint "süs yok" diyor; okunabilirlik ve büyük dokunma alanı öncelik.
import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Screen({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col gap-6 px-4 py-8">
      {title && <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>}
      {children}
    </main>
  );
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" }) {
  const styles = {
    primary: "bg-foreground text-background hover:opacity-90",
    secondary: "border border-line bg-card hover:bg-muted",
    ghost: "text-subtle hover:text-foreground underline-offset-4 hover:underline",
  }[variant];
  return (
    <button
      className={`min-h-12 rounded-xl px-4 text-base font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
      {...props}
    />
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-2xl border border-line bg-card p-4 ${className}`}>{children}</section>;
}

export function ErrorText({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="text-sm text-danger">
      {message}
    </p>
  );
}

export function Loading({ label = "Yükleniyor…" }: { label?: string }) {
  return (
    <p className="text-subtle" aria-live="polite">
      {label}
    </p>
  );
}

export const inputClass =
  "min-h-12 w-full rounded-xl border border-line bg-card px-3 text-base outline-none focus:border-foreground";
