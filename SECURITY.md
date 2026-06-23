# Security Policy

AUTARK is intended for authorized, defensive, and research-oriented agent evaluation and improvement workflows.

## Supported Versions

AUTARK is currently pre-`1.0.0`. Security fixes are applied to the latest development line unless a release branch is explicitly announced.

## Reporting a Vulnerability

Please report vulnerabilities privately before public disclosure.

Include:

- affected version or commit;
- reproduction steps;
- expected and actual behavior;
- impact assessment;
- any relevant logs, configs, or proof-of-concept inputs.

If no private reporting channel is listed for the repository yet, open a GitHub issue that requests a private security contact without including exploit details.

## Safety Boundaries

AUTARK should not be used for:

- destructive actions;
- unauthorized security testing;
- credential theft or credential stuffing;
- stealth, evasion, or persistence;
- mass targeting or abuse automation;
- supply-chain compromise;
- denial-of-service activity.

Dual-use integrations must have a clear authorized context, such as defensive testing, research, or a controlled CTF/lab environment.

## Safe-by-Default Expectations

Project changes should preserve these defaults:

- dry-run is the default execution mode;
- committing artifact changes requires explicit user intent;
- proposers return candidate changes instead of mutating artifacts directly;
- validation gates can reject regressions;
- audit logs record material cycle decisions;
- external services and networked providers are opt-in and documented.

## Sensitive Data

Avoid committing real credentials, API keys, private prompts, production traces, customer data, or proprietary eval corpora. Prefer small synthetic examples in tests and docs.
