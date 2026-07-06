"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

const GoogleIcon = () => (
  <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24" fill="currentColor">
    <path
      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      fill="#4285F4"
    />
    <path
      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      fill="#34A853"
    />
    <path
      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
      fill="#FBBC05"
    />
    <path
      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      fill="#EA4335"
    />
  </svg>
);

const Navbar = () => {
  const { user, loading, login, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <nav className="fixed h-16 w-screen px-6 sm:px-10 bg-black/40 backdrop-blur-md border-b border-zinc-800/40 z-[9999] text-zinc-300">
      <div className="flex h-full items-center justify-between max-w-6xl mx-auto">
        <Link
          href="/"
          className="text-lg font-semibold bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent cursor-pointer hover:scale-105 transition-all duration-200"
        >
          TBuddy
        </Link>
        <div className="flex flex-row gap-x-6 sm:gap-x-8 items-center">
          <Link href="/" className="cursor-pointer hover:scale-105 transition-all duration-200 hover:text-white">
            Home
          </Link>
          <Link href="/chat" className="cursor-pointer hover:scale-105 transition-all duration-200 hover:text-white">
            AI Chat
          </Link>
          <div className="cursor-pointer hover:scale-105 transition-all duration-200 hover:text-zinc-100 hidden md:block">
            Services
          </div>
          <div className="cursor-pointer hover:scale-105 transition-all duration-200 hover:text-zinc-100 hidden md:block">
            About us
          </div>
          <div className="cursor-pointer hover:scale-105 transition-all duration-200 hover:text-zinc-100 hidden md:block">
            Pricing
          </div>

          {/* User authentication panel */}
          {loading ? (
            <div className="w-8 h-8 rounded-full border-2 border-zinc-700 border-t-zinc-400 animate-spin" />
          ) : user ? (
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-x-2 px-3 py-1.5 rounded-full hover:bg-zinc-800/40 border border-transparent hover:border-zinc-800/60 transition-all duration-200 cursor-pointer focus:outline-none"
              >
                {user.picture ? (
                  <img
                    src={user.picture}
                    alt={user.name || "User profile"}
                    className="w-7 h-7 rounded-full border border-zinc-700 object-cover"
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <div className="w-7 h-7 rounded-full bg-violet-600 text-white flex items-center justify-center font-bold text-xs">
                    {user.name ? user.name.charAt(0).toUpperCase() : "U"}
                  </div>
                )}
                <span className="text-sm font-medium text-zinc-200 hidden sm:inline-block max-w-[120px] truncate">
                  {user.name.split(" ")[0]}
                </span>
              </button>

              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-zinc-950/90 backdrop-blur-lg border border-zinc-800/80 rounded-2xl shadow-2xl p-2 z-[10000] animate-in fade-in slide-in-from-top-2 duration-200">
                  <div className="px-3 py-2 border-b border-zinc-800/40 mb-1">
                    <p className="text-sm font-medium text-zinc-100 truncate">{user.name}</p>
                    <p className="text-xs text-zinc-400 truncate">{user.email}</p>
                  </div>
                  <button
                    onClick={() => {
                      logout();
                      setDropdownOpen(false);
                    }}
                    className="w-full flex items-center text-left px-3 py-2 text-sm text-rose-400 hover:bg-rose-500/10 active:bg-rose-500/20 rounded-xl transition-all duration-150 cursor-pointer font-medium"
                  >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                      />
                    </svg>
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button
              onClick={login}
              className="flex items-center px-4 py-1.5 text-xs sm:text-sm font-medium text-white bg-white/10 hover:bg-white/20 active:bg-white/25 border border-white/10 hover:border-white/20 backdrop-blur-md rounded-full shadow-lg transition-all duration-200 cursor-pointer scale-100 hover:scale-[1.03] active:scale-[0.97]"
            >
              <GoogleIcon />
              <span>Sign In</span>
            </button>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
