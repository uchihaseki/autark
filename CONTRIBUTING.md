# Contributing to AUTARK

Thanks for helping improve AUTARK. The project is early, so contributions that clarify concepts, strengthen safety, improve examples, and stabilize extension points are especially valuable.

## Development Setup

```bash
git clone <your-autark-repo-url>
cd autark
python -m pip install -e ".[dev]"
PYTHONPATH=src pytest -q
```

## Good First Contributions

- Improve documentation and examples.
- Add or refine evaluation cases.
- Add tests for artifact staging, rollback, validation, and audit behavior.
- Propose new adapters for agent domains.
- Improve external proposer examples and documentation.
- Clarify error messages in the CLI.

## Design Principles

- Keep `autark.core` domain-neutral.
- Keep dry-run as the default behavior.
- Do not let proposers commit artifacts directly.
- Make proposals, validation decisions, and audit logs inspectable.
- Prefer optional integrations over mandatory provider dependencies.
- Add tests for behavior that can change artifacts or validation decisions.

## Pull Request Checklist

Before opening a PR, please check:

- [ ] The change has a clear motivation.
- [ ] Public behavior is documented when needed.
- [ ] Tests were added or updated for changed behavior.
- [ ] `PYTHONPATH=src pytest -q` passes locally.
- [ ] New adapters keep domain-specific logic outside `autark.core`.
- [ ] New proposers return `CandidateChange` objects and do not commit directly.
- [ ] External services, credentials, or network calls are optional and documented.

## Adapter Contributions

Adapter PRs should include:

- a short README or docs section explaining the domain;
- example cases and artifacts when possible;
- tests for the adapter wiring;
- clear evaluator and validation behavior;
- no provider-specific dependency in the default install unless discussed first.

See `docs/adapter-guide.md`.

## Security and Misuse

Do not submit changes that enable destructive actions, unauthorized testing, credential misuse, stealth, evasion, mass targeting, or unsafe automatic commits. See `SECURITY.md` for the project safety policy.
