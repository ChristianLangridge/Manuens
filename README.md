# Manuens

### [ *Industry Technical Exercise using Claude Code - 2h time constraint* ] 

**Manuens — the capture layer for the bench.**

You finish a protocol run, paste whatever shorthand you scrawled during it, and Manuens maps it onto
the protocol's required fields and tells you what you still need to write down while you can still
remember it. Two minutes, standing at the bench, immediately after the run.

## Three finding types, kept strictly distinct

Collapsing these into generic "issues" destroys the product — each demands a different response.

| Type | Meaning | Example |
|---|---|---|
| **Deviation** | You did something differently from the protocol, and it's recorded | Protocol says 4h antibody incubation, you recorded 2h |
| **Gap** | A required field was never recorded | New bead lot mentioned, no lot number given |
| **Ambiguity** | Recorded in a form that won't survive being read by someone else | "spun 12k" — rpm not ×g, rotor unknown |

Gaps are the emotional core: they have a half-life, answerable this afternoon, half-lost by Friday,
gone by Tuesday. The findings panel leads with them, ordered by recoverability — not by severity —
because a low-severity finding you can still answer beats a critical one that's already unrecoverable.

## Why severity is weighted by reagent class and step sensitivity

A uniform severity scale makes this a form validator. Two axes matter instead:

- **Gaps:** missing identity/lot for a biological or activity-variable reagent (antibodies, enzymes,
  beads, competent cells, transfection reagents...) is `critical` — lot-to-lot variation in these is
  the single most common root cause of "the assay stopped working." Missing lot for a buffer or salt
  is `low`.
- **Deviations:** severity scales with the step's *sensitivity*, not the raw percentage. Every
  protocol step in the seed data carries an explicit `sensitivity: high | low` field. A 25% deviation
  on an antibody incubation (`high`) is material; a 50% deviation on a wash step (`low`) is noise.

Worked example, from the seeded co-immunoprecipitation protocol: a note says antibody incubation ran
2h instead of the protocol's 4h. That step is `sensitivity: high`, so the 50% deviation is flagged
`material`. The same percentage deviation on a wash step (`sensitivity: low`) would not be.

## Why persistence is in-memory

A deliberate scope decision, not an oversight. State resets on restart. The `RunRepository` /
`ProtocolRepository` interfaces in `app/storage/repository.py` exist precisely so that swapping in
Postgres is a one-file change, and so tests can inject a fake without touching a database.

## Why the LLM extracts but never judges

`ExtractorProtocol` (`app/extraction/base.py`) does exactly one thing: map free text onto the
protocol's step schema, with every value carrying a `source_phrase` for provenance. It never decides
severity, never decides what's missing, and never guesses a step assignment — unplaceable fragments
go to a visible `unassigned` bucket instead of being silently attached to the wrong step. All of the
domain judgment (gaps, deviations, ambiguities, severity, recoverability) lives in `app/analysis/`,
which is pure functions over pydantic models — no I/O, no network, no LLM call in the critical path
of getting a correct answer.

**What was deliberately cut here:** this build ships with `FakeExtractor` only — a deterministic
extractor that recognises the three seeded example notes verbatim and puts anything else entirely in
`unassigned` rather than fabricating structure. `LLMExtractor` (`app/extraction/llm.py`) exists behind
the same interface, with the parse/retry/degrade contract unit-tested without any network call, but is
not wired up with a live API key in this build or exercised by CI. Swapping it in is a one-line change
in `get_extractor()` (`app/main.py`) plus an `ANTHROPIC_API_KEY`.

## Positioning vs ELNs

ELNs are systems of record, optimised for retrieval and audit. They accept whatever you type without
knowing what should have been there. Manuens is the ingest layer that knows what should have been
there — it sits upstream of the ELN, not in competition with it.

## Privacy posture

Bench notes are unpublished IP. The app never logs note content — only `note_length`, `protocol_id`,
`findings_count`, `latency_ms`, and `extraction_status`, as structured JSON to stdout with a request ID
threaded through every line (`app/observability.py`). Input is capped at 20,000 characters. Extracted
content is rendered, never executed — Jinja2 autoescaping stays on throughout.

A production deployment for an industry lab would run inference inside the customer's VPC or on-prem,
not against a shared hosted model. `ExtractorProtocol` exists precisely so that swap is a single
implementation change, and the container is already the unit of deployment for it — identifying this
constraint and architecting for it, rather than building it in a short timeboxed session, is the
intended answer here.

## Running locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
EXTRACTOR=fake uvicorn app.main:app --reload
```

Or via Docker Compose (reads a gitignored `.env`; local dev convenience only, not the deployment
mechanism):

```bash
docker compose up --build
```

Visit `http://localhost:8000`, pick the co-immunoprecipitation protocol, and click "Genuinely bad
(the one to demo)" to load the calibration note from the design doc.

## Running tests

```bash
pytest
```

Full suite runs in well under a second, makes zero network calls (`EXTRACTOR=fake` is what every test
uses), and enforces an 80% coverage gate scoped to `app/analysis` and `app/models.py` — the modules
built strictly test-first (red/green/refactor, one behaviour per commit). That gate is not applied to
templates, static assets, or the FastAPI wiring in `main.py`; applying TDD ceremony to markup wastes
the budget without adding confidence.

## CI/CD and deployment

`.github/workflows/ci.yml` runs on every push and PR:

1. **quality** — lint (`ruff check`), format check (`ruff format --check`), type check (`mypy`),
   tests with the coverage gate.
2. **container** (needs `quality`) — builds the image, runs it, smoke-tests `/healthz`, and on push
   pushes SHA-tagged and `latest` images to GHCR (`ghcr.io/<repo>`).
3. **deploy** (needs `container`, main branch only) — POSTs to a Render deploy hook
   (`RENDER_DEPLOY_HOOK_URL` repo secret) to trigger a build of the same commit on Render, then polls
   `/healthz` on the live URL until it's ready or times out. Render itself will not shift traffic to
   the new revision until its own health check on `/healthz` passes, so a red suite never reaches
   production and a broken revision never receives traffic.

**Why Render:** free web-service tier with native Docker support and no credit card required — the
other platforms named as candidates in the original design doc (Fly.io, Railway) both dropped their
free tiers and now require billing to run anything beyond a short trial. The trade-off is that free
Render services sleep after 15 minutes idle and take 30–60s to cold-start on the next request —
acceptable for a demo, not for something needing an always-warm instance.

**Deployment is defined as code:** `render.yaml` in the repo root is a Render Blueprint — the service,
its Dockerfile path, health check path, and env vars are all declared there rather than clicked
together in a dashboard. `autoDeploy` is deliberately `false` so Render never deploys on its own from
a raw git push; only the CI deploy job (after quality + container pass) triggers a deploy, via the hook.

**Rollback:** every image is tagged with its immutable commit SHA; `latest` is a convenience alias,
never a deploy target. Since the app is stateless (§ persistence, above) and images are SHA-tagged,
rollback is redeploying the previous SHA tag — no migration step, no session affinity to worry about.
On Render specifically, rollback is selecting the previous successful deploy in the dashboard, which
rebuilds that same commit.

**Secrets:** never in the repo, a Dockerfile, a build arg, or a log line. CI uses the built-in
`GITHUB_TOKEN` for GHCR and a `RENDER_DEPLOY_HOOK_URL` repo secret to trigger deploys; a live
`ANTHROPIC_API_KEY` would come from GitHub Actions secrets and is not present in this build.

## Container

Multi-stage `Dockerfile`: `python:3.12-slim` builder installs pinned deps into a venv, runtime stage
copies only the venv, `app/`, and `data/`. Runs as a non-root user (`appuser`), exposes 8000, and
carries a `HEALTHCHECK` against `/healthz`. `.dockerignore` excludes `.git`, `tests/`, `.venv`, and
anything that could leak a secret into the build context.

## What was deliberately cut, and why

- **Live LLM extraction** — no API key in this build; `FakeExtractor` only (see above). The interface
  is real and tested; the live call is not exercised.
- **A wired hosting platform** — the deploy job is a documented placeholder pending a platform choice.
- **Auth, users, teams, voice input, ELN integration, protocol authoring UI, cross-run drift analysis,
  any database requiring a migration step** — out of scope from the outset (see the technical design
  document, Part I §2). None of these are needed to demonstrate the core idea: that the value is in
  knowing what *should* have been recorded, not in building another place to type notes.
