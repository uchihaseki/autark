#!/bin/bash
# Example shell-script proposer for AUTARK.
# Reads JSON from stdin, outputs CandidateChange JSON on stdout.
#
# Usage:
#   cat input.json | bash proposer.sh
#   autark run --proposer external-command --proposer-command "bash examples/shell_proposer/proposer.sh"
#
# The stdin JSON contains: signal, strategy, artifact, context
# The stdout JSON must be a CandidateChange object.

set -euo pipefail

INPUT=$(cat)

# Extract key fields
CATEGORY=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin)['signal']['category'])")
ARTIFACT_ID=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin)['signal']['artifact_id'])")
SIGNAL_ID=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin)['signal']['signal_id'])")
STRATEGY_ID=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin)['strategy']['strategy_id'])")

# Map failure category to repair text
case "$CATEGORY" in
  wrong_answer)
    TEXT="Always compute and verify the answer before responding."
    ;;
  missing_constraint)
    TEXT="Follow all listed constraints explicitly before answering."
    ;;
  format_error)
    TEXT="Use the required output format exactly."
    ;;
  empty_output)
    TEXT="Never return an empty answer."
    ;;
  *)
    TEXT="Improve the artifact to satisfy the failing case while preserving existing behavior."
    ;;
esac

# Output CandidateChange JSON
python3 -c "
import json, uuid
change = {
    'change_id': f'chg-{uuid.uuid4().hex[:8]}',
    'artifact_id': '$ARTIFACT_ID',
    'operations': [{'operation': 'append', 'text': '''$TEXT'''}],
    'rationale': f'Shell-script proposer repair for category=$CATEGORY.',
    'validation_plan': ['Rerun failing cases', 'Check holdout cases for regressions'],
    'metadata': {
        'signal_id': '$SIGNAL_ID',
        'strategy_id': '$STRATEGY_ID',
        'source': 'shell-proposer',
        'before_scores': {},
        'after_scores': {'overall': 0.8},
    },
}
print(json.dumps(change, indent=2))
"
