export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

import { getFirebaseAuth, isDemoLoginEnabled, waitForAuthReady } from "@/lib/firebase";

/**
 * Builds auth headers. A signed-in Firebase user always wins (fresh ID token each call, the SDK
 * refreshes it when expired). The demo-persona headers are used only when no Firebase user exists,
 * and the backend ignores them unless ENABLE_DEMO_AUTH is on.
 */
export async function getAuthHeaders(): Promise<Record<string, string>> {
  await waitForAuthReady();
  const fbUser = getFirebaseAuth()?.currentUser;
  if (fbUser) {
    return { Authorization: `Bearer ${await fbUser.getIdToken()}` };
  }
  if (typeof window !== "undefined" && !(isDemoLoginEnabled && localStorage.getItem("assesscraft_user"))) {
    throw new Error("Not signed in");
  }
  const user = getStoredUser();
  return {
    Authorization: `Bearer demo-${user.role}-token`,
    "x-demo-user": user.email,
    "x-demo-role": user.role,
  };
}

export type UserRole = "admin" | "lecturer" | "moderator";

export interface UserSession {
  uid?: string;
  email: string;
  displayName: string;
  /** Primary role (the first of `roles`). */
  role: UserRole;
  /** Every role the user holds; older sessions may omit it. */
  roles?: UserRole[];
  token?: string;
}

export function getStoredUser(): UserSession {
  if (typeof window === "undefined") {
    return {
      email: "lecturer@demo",
      displayName: "Dr. Samantha Chen (Lecturer)",
      role: "lecturer",
    };
  }
  const saved = localStorage.getItem("assesscraft_user");
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch {
      // fallback
    }
  }
  return {
    email: "lecturer@demo",
    displayName: "Dr. Samantha Chen (Lecturer)",
    role: "lecturer",
  };
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  for (const [k, v] of Object.entries(await getAuthHeaders())) headers.set(k, v);

  const url = `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorDetail: any = errorText;
      try {
        const errorJson = JSON.parse(errorText);
        errorDetail = errorJson.detail || errorText;
        if (typeof errorDetail === "object") {
          errorDetail = Array.isArray(errorDetail)
            ? errorDetail.map((e: any) => e.msg || JSON.stringify(e)).join(", ")
            : JSON.stringify(errorDetail);
        }
      } catch {}
      throw new Error(`API Error (${response.status}): ${errorDetail}`);
    }

    // Handle empty responses
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      return await response.json();
    }
    return (await response.text()) as unknown as T;
  } catch (error: any) {
    // 404s are expected for not-yet-generated resources; callers decide whether they matter.
    if (!String(error?.message).includes("(404)")) {
      console.error(`[API Request Failed] ${path}:`, error.message);
    }
    throw error;
  }
}

export async function apiDownload(path: string, filename: string): Promise<void> {
  const headers = new Headers(await getAuthHeaders());

  const url = `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const response = await fetch(url, { headers });
  if (!response.ok) {
    throw new Error(`Download failed (${response.status}): ${response.statusText}`);
  }
  // When Cloud Storage is configured the API returns a short-lived signed URL instead of the bytes.
  if ((response.headers.get("content-type") || "").includes("application/json")) {
    const { signedUrl } = (await response.json()) as { signedUrl?: string };
    if (signedUrl) {
      window.location.assign(signedUrl);
      return;
    }
    throw new Error("Download failed: export response did not include a signed URL");
  }
  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(blobUrl);
  document.body.removeChild(a);
}
