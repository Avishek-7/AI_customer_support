type RuntimeEnv = {
  NEXT_PUBLIC_API_URL?: string;
};

export function getRuntimeEnv(): RuntimeEnv {
  if (typeof window === "undefined") {
    return {};
  }
  return (window as typeof window & { __ENV__?: RuntimeEnv }).__ENV__ ?? {};
}

export function getApiBase(): string {
  const runtimeEnv = getRuntimeEnv();
  return runtimeEnv.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_URL || "";
}
