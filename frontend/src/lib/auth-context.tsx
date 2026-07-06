"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

export interface GoogleUser {
  user_id: string;
  email: string;
  name: string;
  picture?: string;
  email_verified?: boolean;
}

interface AuthContextType {
  user: GoogleUser | null;
  token: string | null;
  loading: boolean;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Helper function to extract auth headers in fetch calls
export function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("google_id_token");
  return token ? { "Authorization": `Bearer ${token}` } : {};
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<GoogleUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isPopup, setIsPopup] = useState<boolean>(false);

  // 1. Intercept popup OAuth redirects immediately to avoid site rendering in popups
  useEffect(() => {
    if (typeof window !== "undefined") {
      const hash = window.location.hash;
      if (window.opener && hash.includes("id_token=")) {
        setIsPopup(true);
        const params = new URLSearchParams(hash.substring(1));
        const idToken = params.get("id_token");
        if (idToken) {
          window.opener.postMessage(
            { type: "GOOGLE_AUTH_SUCCESS", id_token: idToken },
            window.location.origin
          );
          window.close();
        }
      }
    }
  }, []);

  const fetchProfile = async (idToken: string) => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
      const res = await fetch(`${apiBase}/api/v2/orchestrator/auth/user`, {
        headers: {
          "Authorization": `Bearer ${idToken}`,
        },
      });

      if (res.ok) {
        const profile = await res.json();
        setUser(profile);
        setToken(idToken);
      } else {
        console.warn("Invalid or expired session token, logging out...");
        localStorage.removeItem("google_id_token");
        setUser(null);
        setToken(null);
      }
    } catch (error) {
      console.error("Failed to load user profile:", error);
    } finally {
      setLoading(false);
    }
  };

  // 2. Hydrate token and fetch user on load
  useEffect(() => {
    if (isPopup) return; // skip for popup window itself

    const storedToken = localStorage.getItem("google_id_token");
    if (storedToken) {
      fetchProfile(storedToken);
    } else {
      setLoading(false);
    }

    // Listener for messages from Google Auth popup
    const handleAuthMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      if (event.data && event.data.type === "GOOGLE_AUTH_SUCCESS") {
        const idToken = event.data.id_token;
        localStorage.setItem("google_id_token", idToken);
        setLoading(true);
        fetchProfile(idToken);
      }
    };

    window.addEventListener("message", handleAuthMessage);
    return () => window.removeEventListener("message", handleAuthMessage);
  }, [isPopup]);

  const login = () => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    if (!clientId || clientId.includes("your-google-client-id")) {
      alert("Google Client ID is not configured in .env.local yet! Please set NEXT_PUBLIC_GOOGLE_CLIENT_ID.");
      return;
    }

    const redirectUri = window.location.origin;
    const responseType = "id_token";
    const scope = "openid profile email";
    const nonce = Math.random().toString(36).substring(2, 15);

    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
      `client_id=${encodeURIComponent(clientId)}&` +
      `redirect_uri=${encodeURIComponent(redirectUri)}&` +
      `response_type=${encodeURIComponent(responseType)}&` +
      `scope=${encodeURIComponent(scope)}&` +
      `nonce=${encodeURIComponent(nonce)}`;

    const width = 500;
    const height = 650;
    const left = window.screen.width / 2 - width / 2;
    const top = window.screen.height / 2 - height / 2;

    window.open(
      authUrl,
      "google-signin-popup",
      `width=${width},height=${height},left=${left},top=${top},status=no,resizable=yes,scrollbars=yes`
    );
  };

  const logout = () => {
    localStorage.removeItem("google_id_token");
    setUser(null);
    setToken(null);
  };

  // If this window is just the popup redirecting/closing, show simple layout
  if (isPopup) {
    return (
      <div className="min-h-screen bg-black text-zinc-200 flex flex-col items-center justify-center gap-y-4">
        <div className="w-8 h-8 rounded-full border-2 border-violet-500 border-t-transparent animate-spin"></div>
        <p className="text-sm font-medium animate-pulse">Completing Sign-In...</p>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
