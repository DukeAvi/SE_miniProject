"use client";

import { FormEvent, useState } from "react";
import { api, bloodGroups, friendlyError, localDate } from "@/lib/api";

type Donor = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  has_donor_profile: boolean;
};

type Props = {
  mutate: (path: string, method: string, body?: unknown) => Promise<boolean>;
};

export default function StaffDonorWorkflows({ mutate }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Donor[]>([]);
  const [selected, setSelected] = useState<Donor | null>(null);
  const [lookupMessage, setLookupMessage] = useState("");
  const [lookupError, setLookupError] = useState("");
  const [lookupBusy, setLookupBusy] = useState(false);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLookupMessage("");
    setLookupError("");
    setSelected(null);
    setResults([]);
    const normalized = query.trim();
    if (normalized.length < 2) {
      setLookupMessage("Enter at least two characters to search.");
      return;
    }
    setLookupBusy(true);
    try {
      const response = await api<{ results: Donor[] }>(
        `/donors/staff/donors?q=${encodeURIComponent(normalized)}`,
      );
      setResults(response.results);
      setLookupMessage(response.results.length ? "Select the matching donor." : "No donors matched that search.");
    } catch (reason) {
      setLookupError(friendlyError(reason));
    } finally {
      setLookupBusy(false);
    }
  }

  async function completeProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const values = new FormData(event.currentTarget);
    const saved = await mutate("/donors/staff/donor-profiles", "POST", {
      donor_id: selected.id,
      birth_date: values.get("birth_date"),
      weight_kg: values.get("weight_kg"),
      blood_group: values.get("blood_group"),
    });
    if (saved) setSelected({ ...selected, has_donor_profile: true });
  }

  async function recordDonation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected?.has_donor_profile) return;
    const element = event.currentTarget;
    const values = new FormData(element);
    const saved = await mutate("/donations", "POST", {
      donor_id: selected.id,
      donation_date: values.get("donation_date"),
      blood_group: values.get("blood_group"),
      component: "WHOLE_BLOOD",
      quantity_units: Number(values.get("quantity_units")),
      status: "COMPLETED",
      screening_weight_kg: values.get("screening_weight_kg"),
    });
    if (saved) element.reset();
  }

  return (
    <div className="stack">
      <section className="panel panel-pad" aria-labelledby="donor-lookup-title">
        <div className="panel-heading"><div><span className="eyebrow">Staff donor selection</span><h2 id="donor-lookup-title">Find a donor</h2></div></div>
        <form className="inline-form" onSubmit={search}>
          <div className="field"><label htmlFor="donor-lookup-query">Name or email</label><input id="donor-lookup-query" type="search" value={query} minLength={2} maxLength={100} onChange={(event) => setQuery(event.target.value)} required /></div>
          <button className="button button-primary" disabled={lookupBusy}>{lookupBusy ? "Searching…" : "Search donors"}</button>
        </form>
        {lookupMessage && <p className="info-box" role="status" aria-live="polite">{lookupMessage}</p>}
        {lookupError && <p className="error-box" role="alert">{lookupError}</p>}
        {results.length > 0 && <ul className="donor-results" aria-label="Matching donors">{results.map((donor) => (
          <li key={donor.id}>
            <button className="button button-soft" type="button" aria-pressed={selected?.id === donor.id} onClick={() => setSelected(donor)}>
              {donor.first_name} {donor.last_name} · {donor.email} · account {donor.id}
            </button>
            <span className="muted-copy">{donor.has_donor_profile ? "Verified profile" : "Profile verification needed"}</span>
          </li>
        ))}</ul>}
      </section>

      {selected && !selected.has_donor_profile && <section className="panel panel-pad" aria-labelledby="profile-verification-title">
        <div className="panel-heading"><div><span className="eyebrow">Donor onboarding</span><h2 id="profile-verification-title">Complete verified donor details</h2></div></div>
        <p className="muted-copy">Enter details from the approved verification process. Use synthetic values for this demo. Creating a profile does not mean the donor is eligible to donate; the eligibility rules are checked separately.</p>
        <form className="form-grid" onSubmit={completeProfile}>
          <div className="field"><label htmlFor="verified-birth-date">Birth date</label><input id="verified-birth-date" name="birth_date" type="date" max={localDate()} required /></div>
          <div className="field"><label htmlFor="verified-weight">Verified weight (kg)</label><input id="verified-weight" name="weight_kg" type="number" min="0" max="999.99" step="0.01" required /></div>
          <div className="field"><label htmlFor="verified-blood-group">Verified blood group</label><select id="verified-blood-group" name="blood_group">{bloodGroups.map((group) => <option key={group}>{group}</option>)}</select></div>
          <div className="form-actions"><button className="button button-primary">Save verified donor profile</button></div>
        </form>
      </section>}

      <section className="panel panel-pad" aria-labelledby="record-donation-title">
        <div className="panel-heading"><div><span className="eyebrow">Staff action</span><h2 id="record-donation-title">Record completed donation</h2></div></div>
        {!selected ? <p className="empty-state">Search for and select a donor before recording a donation.</p>
          : !selected.has_donor_profile ? <p className="info-box" role="status">Complete staff profile verification above before recording a donation.</p>
            : <>
              <p className="muted-copy">Selected donor: {selected.first_name} {selected.last_name} · {selected.email} · account {selected.id}</p>
              <form className="form-grid" onSubmit={recordDonation}>
                <div className="field"><label htmlFor="donation-date">Donation date</label><input id="donation-date" name="donation_date" type="date" max={localDate()} required /></div>
                <div className="field"><label htmlFor="donation-group">Blood group</label><select id="donation-group" name="blood_group">{bloodGroups.map((group) => <option key={group}>{group}</option>)}</select></div>
                <div className="field"><label htmlFor="donation-units">Quantity units</label><input id="donation-units" name="quantity_units" type="number" min="1" max="20" defaultValue="1" required /></div>
                <div className="field"><label htmlFor="screening-weight">Screening weight (kg)</label><input id="screening-weight" name="screening_weight_kg" type="number" min="0" step="0.01" required /></div>
                <div className="form-actions"><button className="button button-primary">Record donation</button></div>
              </form>
            </>}
      </section>
    </div>
  );
}
