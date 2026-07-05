# Schema Discovery Prompt (v0.1 — prompt_version: discover-1)

Purpose: given a NEW data provider (API docs, export files, or app codebase),
produce the provider→SignalFit adapter mapping. This is how Atria was analyzed;
reuse it for Oura, Garmin, Apple Health, Fitbit, Ultrahuman, or any custom app.

Role: You are mapping a fitness data provider onto the SignalFit universal context
schema (`schemas/assistant_context.schema.json`, version `sf-context-1`). Inspect
only real, verifiable sources (API reference, export schema, source code). Do not
invent fields. Output a mapping report with these sections:

1. **Field inventory** — every metric the provider actually exposes, grouped as:
   raw device data / calculated metrics / user-entered / inferred analytics /
   unvalidated-or-research-gated (must be excluded). For each: provider field name,
   source (file/endpoint), type, example value, update frequency, reliability.
2. **Mapping table** — provider field → SignalFit generic field, with any unit or
   scale conversion. Flag: HRV method (rmssd|sdnn), strain/load scale (map to 0–21
   honestly or send null + native value in `provenance.provider_metadata`),
   sleep-stage taxonomy mapping, timezone semantics.
3. **Coverage verdict per schema block** — available / calculable by adapter /
   needs provider work / impossible → drives `missing_fields` for this provider.
4. **Confidence grades** — what `provenance.source_confidence` should say per
   block, and which provider confidence/validation labels map onto
   high|medium|low (e.g. Atria: validated→high, personal baseline→medium,
   unverified→low, learning→learning).
5. **Proposed provider mask** for synthetic data (which of wearable_full /
   ring_no_strain / platform_aggregate / watch_load_native / tracker_azm /
   manual_only it matches, or define a new one).
6. **Assumptions list** — anything not directly verified, clearly marked.

Rules: read-only inspection; generic names only outside provider_metadata; every
claim traceable to a cited source location; uncertain = say so.
