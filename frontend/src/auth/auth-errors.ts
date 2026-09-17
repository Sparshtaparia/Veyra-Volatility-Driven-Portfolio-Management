type AuthProviderError = { message?: string; code?: string }

export function authErrorMessage(error: AuthProviderError | null | undefined): string {
  const message = error?.message?.toLowerCase() ?? ""
  const code = error?.code?.toLowerCase() ?? ""

  if (message.includes("rate limit") || code.includes("rate_limit")) {
    return "Too many verification emails were requested. Please wait a few minutes before trying again."
  }
  if (message.includes("already registered") || message.includes("already exists")) {
    return "An account already exists for this email. Sign in instead."
  }
  if (message.includes("invalid login credentials") || message.includes("invalid credentials")) {
    return "Email or password is incorrect."
  }
  if (message.includes("email not confirmed")) {
    return "Please confirm your email before signing in."
  }
  if (message.includes("password") && (message.includes("weak") || message.includes("characters"))) {
    return "Choose a stronger password with at least 8 characters."
  }
  return "Authentication could not be completed. Please try again."
}
