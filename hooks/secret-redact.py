#!/usr/bin/env python3
"""
PostToolUse hook (matcher: Bash) — backstop that redacts secret-shaped strings
from a command's output BEFORE the model ingests it, via `updatedToolOutput`.

This is defense-in-depth: the deny rules and secret-guard block the obvious
paths; this catches an accidental leak (a token in a stack trace, a header
echoed on error). It only rewrites output when it actually finds a match, so
normal output passes through untouched.

Redacts: AWS keys, GitHub/GitLab/Slack/Google/Stripe tokens, JWTs, bearer/auth
headers, private-key blocks, and key=value pairs whose key is secret-shaped.
"""
import json
import re
import sys

REDACTION = "[REDACTED-SECRET]"

# (pattern, replacement) — replacement may use \g<1> to keep a non-secret prefix.
PATTERNS = [
    # Private key blocks (whole block).
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), REDACTION),
    # AWS access key ids.
    (re.compile(r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|ANPA|ANVA)[0-9A-Z]{16}\b"), REDACTION),
    # GitHub / GitLab tokens.
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"), REDACTION),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}\b"), REDACTION),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"), REDACTION),
    # Slack tokens & webhooks.
    (re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b"), REDACTION),
    # Google API keys.
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), REDACTION),
    # Stripe / OpenAI-style secret keys.
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), REDACTION),
    (re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b"), REDACTION),
    # JWTs.
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), REDACTION),
    # Authorization / bearer headers — keep the header name, drop the value.
    (re.compile(r"(?i)(authorization\s*[:=]\s*(?:bearer|basic|token)\s+)\S+"), r"\g<1>" + REDACTION),
    (re.compile(r"(?i)(x-api-key\s*[:=]\s*)\S+"), r"\g<1>" + REDACTION),
    # key=value / key: value where the key is secret-shaped — redact the value only.
    (re.compile(
        r"(?i)\b([\w.-]*(?:api[_-]?key|secret|token|passwd|password|pwd|access[_-]?key|private[_-]?key)[\w.-]*\s*[:=]\s*)"
        r"[\"']?[A-Za-z0-9_\-./+=]{8,}[\"']?"
    ), r"\g<1>" + REDACTION),
]


def redact(text: str) -> tuple[str, bool]:
    out = text
    for pat, repl in PATTERNS:
        out = pat.sub(repl, out)
    return out, (out != text)


def extract_output(resp) -> str:
    if isinstance(resp, str):
        return resp
    if isinstance(resp, dict):
        parts = [str(resp.get(k, "")) for k in ("stdout", "stderr", "output") if resp.get(k)]
        if parts:
            return "\n".join(parts)
        return json.dumps(resp)
    return "" if resp is None else str(resp)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    resp = data.get("tool_response", data.get("tool_output"))
    text = extract_output(resp)
    if not text:
        return 0
    redacted, changed = redact(text)
    if changed:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "updatedToolOutput": redacted,
            }
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
