"use client";

import { ArrowRight, Droplet, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { api, friendlyError, refreshCsrfToken } from "@/lib/api";

type LoginResponse = {
  user: { id: number; name: string; role: string };
  redirect: string;
  session_expires_in: number;
};

export default function Home() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await refreshCsrfToken();
      const result = await api<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      await refreshCsrfToken();
      window.location.assign(result.redirect);
    } catch (reason) {
      setError(friendlyError(reason));
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-story" aria-labelledby="story-title">
        <div className="brand"><span className="brand-mark"><Droplet size={21} fill="currentColor" /></span> bloodline</div>
        <div className="story-copy">
          <span className="eyebrow">Care, connected</span>
          <h1 id="story-title">Every unit has a story.</h1>
          <p>A thoughtful workspace for the people who keep donation, inventory, and care moving together.</p>
        </div>
        <div className="story-note">A synthetic-data demonstration of the BBMS project.</div>
      </section>
      <section className="auth-panel" aria-label="Sign in">
        <div className="auth-card">
          <span className="eyebrow">Welcome back</span>
          <h2>Sign in to your workspace</h2>
          <p>Your role determines the workspace and actions available to you.</p>
          <form onSubmit={submit}>
            <div className="field">
              <label htmlFor="email">Email address</label>
              <input id="email" name="email" type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input id="password" name="password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} />
            </div>
            {error && <div className="error-box" role="alert">{error}</div>}
            <button className="button button-primary full-width" disabled={busy} type="submit">
              {busy ? "Signing in…" : "Continue"}<ArrowRight size={17} aria-hidden="true" />
            </button>
          </form>
          <div className="auth-foot">
            <span>New donor or recipient?</span>
            <Link className="inline-link" href="/register">Create an account</Link>
          </div>
          <div className="auth-foot"><span><ShieldCheck size={14} aria-hidden="true" /> Protected by a secure server session</span></div>
        </div>
      </section>
    </main>
  );
}
