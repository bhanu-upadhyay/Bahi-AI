"use client";

import React, { useState } from "react";
import Link from "next/link";
import { GraduationCap, Lock, Mail, ArrowRight } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("sarah.jenkins@university.edu");
  const [password, setPassword] = useState("••••••••••••");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    window.location.href = "/dashboard";
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <div className="w-full max-w-md bg-white p-8 rounded-2xl border border-slate-200/90 shadow-xl space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-sky-600 text-white font-bold shadow-md shadow-sky-900/30">
            <GraduationCap className="h-6 w-6" />
          </div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900">
            Sign In to Bahi-AI AP
          </h2>
          <p className="text-xs text-slate-500">
            University Accounts Payable & Invoice Processing Portal
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">University Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                required
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            className="w-full py-2.5 px-4 rounded-lg bg-sky-600 hover:bg-sky-700 text-white font-semibold text-xs shadow-md shadow-sky-900/20 transition flex items-center justify-center space-x-1.5"
          >
            <span>Enter AP Workspace</span>
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        <div className="pt-4 border-t border-slate-100 text-center text-xs text-slate-400">
          Demo roles: Finance Admin, Finance Officer, Procurement Officer, HOD, Vendor
        </div>
      </div>
    </div>
  );
}

