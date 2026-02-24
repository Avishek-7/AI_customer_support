export function getStoredToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return localStorage.getItem("token");
}

export function setStoredToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.setItem("token", token);
}

export function clearStoredToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.removeItem("token");
}

export function getAuthHeaders(token?: string | null): Record<string, string> {
  const resolvedToken = token ?? getStoredToken();
  if (!resolvedToken) {
    return {};
  }
  return { Authorization: `Bearer ${resolvedToken}` };
}
