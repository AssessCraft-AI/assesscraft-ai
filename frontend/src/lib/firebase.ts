import { initializeApp, getApps, getApp, type FirebaseApp } from "firebase/app";
import { getAuth, type Auth } from "firebase/auth";

// NEXT_PUBLIC_* values are inlined at build time (see frontend/cloudbuild.yaml and .env.example).
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

export const isFirebaseConfigured = Boolean(firebaseConfig.apiKey && firebaseConfig.projectId);

export const isDemoLoginEnabled =
  process.env.NEXT_PUBLIC_ENABLE_DEMO_LOGIN === "true" ||
  (!isFirebaseConfigured && process.env.NODE_ENV !== "production");

let app: FirebaseApp | null = null;
let authInstance: Auth | null = null;

export function getFirebaseAuth(): Auth | null {
  if (!isFirebaseConfigured) return null;
  if (!authInstance) {
    app = !getApps().length ? initializeApp(firebaseConfig) : getApp();
    authInstance = getAuth(app);
  }
  return authInstance;
}

/** Resolves once Firebase has restored (or ruled out) a persisted session. Immediate when Firebase is not configured. */
export async function waitForAuthReady(): Promise<void> {
  await getFirebaseAuth()?.authStateReady();
}
