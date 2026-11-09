"use client";

import { ArrowLeft, ArrowRight, Droplet } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { api, friendlyError, refreshCsrfToken } from "@/lib/api";

type RegisteredUser = { role: "DONOR" | "RECIPIENT" };

export default function RegisterPage() {
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", phone: "", password: "", role: "DONOR" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function update(name: string, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await refreshCsrfToken();
      const user = await api<RegisteredUser>("/auth/register", { method: "POST", body: JSON.stringify(form) });
      setForm({ ...form, password: "" });
      setError(`Account created for the ${user.role.toLowerCase()} role. Sign in to continue.`);
      setBusy(false);
    } catch (reason) {
      setError(friendlyError(reason));
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-story" aria-labelledby="register-title">
        <div className="brand"><span className="brand-mark"><Droplet size={21} fill="currentColor" /></span> bloodline</div>
        <div className="story-copy">
          <span className="eyebrow">A place to begin</span>
          <h1 id="register-title">Good care starts with a connection.</h1>
          <p>Create a donor or recipient account. Staff and Admin accounts are managed by an Admin.</p>
        </div>
        <div className="story-note">Use synthetic information for this classroom demo.</div>
      </section>
      <section className="auth-panel" aria-label="Create an account">
        <div className="auth-card">
          <span className="eyebrow">New account</span>
          <h2>Join the workspace</h2>
          <p>All fields are checked by the BBMS server before your account is saved.</p>
          <form onSubmit={submit}>
            <div className="field-grid">
              <div className="field"><label htmlFor="first_name">First name</label><input id="first_name" name="first_name" autoComplete="given-name" required maxLength={150} value={form.first_name} onChange={(event) => update("first_name", event.target.value)} /></div>
              <div className="field"><label htmlFor="last_name">Last name</label><input id="last_name" name="last_name" autoComplete="family-name" required maxLength={150} value={form.last_name} onChange={(event) => update("last_name", event.target.value)} /></div>
            </div>
            <div className="field"><label htmlFor="email">Email address</label><input id="email" name="email" type="email" autoComplete="email" required maxLength={254} value={form.email} onChange={(event) => update("email", event.target.value)} /></div>
            <div className="field"><label htmlFor="phone">Phone number</label><input id="phone" name="phone" type="tel" autoComplete="tel" required maxLength={32} aria-describedby="phone-help" value={form.phone} onChange={(event) => update("phone", event.target.value)} /><small id="phone-help">Include country code, for example +12025550123.</small></div>
            <div className="field"><label htmlFor="role">Account type</label><select id="role" name="role" value={form.role} onChange={(event) => update("role", event.target.value)}><option value="DONOR">Donor</option><option value="RECIPIENT">Recipient</option></select></div>
            <div className="field"><label htmlFor="password">Password</label><input id="password" name="password" type="password" autoComplete="new-password" required maxLength={128} value={form.password} onChange={(event) => update("password", event.target.value)} /><small>Use a unique password for the demo account.</small></div>
            {error && <div className={error.startsWith("Account created") ? "success-box" : "error-box"} role={error.startsWith("Account created") ? "status" : "alert"}>{error}</div>}
            <button className="button button-primary full-width" disabled={busy} type="submit">{busy ? "Creating account…" : "Create account"}<ArrowRight size={17} aria-hidden="true" /></button>
          </form>
          <div className="auth-foot"><Link className="inline-link" href="/"><ArrowLeft size={14} aria-hidden="true" /> Back to sign in</Link></div>
        </div>
      </section>
    </main>
  );
}
