import React from "react";

export function PrimaryButton({
  children,
  secondary = false,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  secondary?: boolean;
}) {
  return (
    <button
      className={`primary-button ${secondary ? "secondary" : ""}`}
      {...props}
    >
      {children}
    </button>
  );
}
