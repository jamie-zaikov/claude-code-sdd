#!/usr/bin/env python3
"""Inert-text helpers for secret-guard.py (kept apart so the guard stays under the module
size limit).

`without_inert_text(command)` returns the command with the text that no guard rule may
see: the body of a quoted here-doc that `cat`/`tee` writes to a data file, and the search
pattern of grep/egrep/fgrep/rg. Every helper fails closed: on any doubt it removes nothing.
See the "Inert text" section of secret-guard.py for the contract.

A here-doc body counts as inert only when nothing after it in the SAME command can run it:
the operator line ends at the operator, and every later command is a plain `sdd-status.py`
call. A file written here and run by a LATER, separate Bash call is not seen — the same
limit as a script written with the Write tool (see "Limits" in secret-guard.py).
"""
import os
import re

# --- Inert text: removed before the rules run (see "Inert text" in the module doc). -----
# Every helper below fails closed: on any doubt it removes nothing, so the command is
# checked exactly as before.

# A here-doc operator: `<<'EOF'`, `<<"EOF"`, `<<-'EOF'` (quoted: the body is literal), or a
# bare `<<EOF` / `<<\EOF` (found only so that its body is skipped by the lexer).
_HD_OP = re.compile(r"<<(-?)[ \t]*(?:(['\"])([A-Za-z_][\w.-]*)\2|(\\?)([A-Za-z_][\w.-]*))")
HEREDOC_CONSUMERS = ("cat", "tee")
# Where the simple command that owns the operator starts. `(`, `` ` `` and `{` are not
# here on purpose: `$(cat <<'EOF' ...)` feeds the body to another command (e.g. `bash -c`).
_CMD_START = re.compile(r"(?:&&|\|\||[;&|\n])")


# The body is skipped only when it lands in a DATA file (a summary, a status record, a PR
# body). A script body (`.py`, `.sh`, no extension) stays checked: the same command may run
# it next, and the old check was the only thing that stopped a script that opens a store.
DATA_SUFFIXES = (".md", ".markdown", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".csv",
                 ".tsv", ".log")
# `NAME=value` as a whole command (followed by a separator). A prefix assignment such as
# `S=a.md cat > "$S"` does not count: Bash expands `$S` before it applies the prefix.
_ASSIGN = re.compile(r"(?:^|(?<=[;&|\n]))[ \t]*([A-Za-z_]\w*)=(\"[^\"$`\\]*\"|'[^']*'|[^\s;&|$`\"'\\]*)"
                     r"(?=[ \t]*(?:[;&|\n]|$))")
# After an inert here-doc, only status-record commands may follow: `python3 .../sdd-status.py`
# with plain words (no `$(`, backtick, glob, `;`, `|`, redirect). Anything else could run the
# written file in a way no name search can see (`bash "${S}"`, `bash ./*.md`, `sh<a.md`).
# One shell word made of plain pieces (`$W/spec-memory/x.md` is `$W` + `/spec-memory/x.md`).
# The pieces never overlap (a bare piece is ONE character; `$`, `"` and `'` each start
# exactly one other kind), so the outer `+` cannot backtrack exponentially.
_PLAIN_WORD = (r"(?:[\w./:=@,+%-]|\$[A-Za-z_]\w*(?!\w)|\"(?:\$[A-Za-z_]\w*|[^\"$`\\*?\[]*)\""
               r"|'[^'*?\[]*')+")
# Only the INSTALLED status tool (under the home folder), never any file of that name.
# The absolute form is THIS user's home folder, read when the hook runs (not any
# `/Users/<name>`: `/Users/Shared` is writable by every user).
_HOME = re.escape(os.path.expanduser("~").rstrip("/") or "/nonexistent-home")
_STATUS_CMD = re.compile(
    rf"[ \t]*python3?[ \t]+(?:~|\$HOME|\"\$HOME\"|{_HOME})"
    rf"/\.claude/tools/sdd-status\.py(?:[ \t]+{_PLAIN_WORD})*"
    # Output may be dropped (`>/dev/null`, `2>&1`): a redirect to /dev/null runs nothing.
    r"(?:[ \t]*[12]?>[ \t]*(?:/dev/null|&[12]))*[ \t]*")
# Before the cat/tee, the whole command may only set up: `cd <plain path>`, one plain
# `NAME=value`, or a status command. Anything else (`trap ... EXIT`, `(...) &`, an earlier
# script write) could run the written file later in the same command.
# Setup names are one or two capital letters only (`S`, `W`, `SM`): never `HOME` (moves
# `~`), `PATH` (picks `python3`), `IFS`, `ENV`, `BASH_ENV`, `PYTHONPATH`, `LD_*`, `DYLD_*`,
# and no lowercase name (zsh ties `path`, `fpath`, `cdpath`, `manpath` to their arrays).
_SETUP_CMD = re.compile(
    rf"[ \t]*(?:cd[ \t]+{_PLAIN_WORD}|[A-Z]{{1,2}}={_PLAIN_WORD}?)[ \t]*")


def _only_setup(head: str) -> bool:
    for segment in re.split(r"\n|&&|;", head):
        if segment.strip() and not (_SETUP_CMD.fullmatch(segment)
                                    or _STATUS_CMD.fullmatch(segment)):
            return False
    return True


def _resolve_target(target: str, command: str, before: int):
    """The file names a here-doc target stands for (the literal, the resolved value, and
    their base names), or None when the target is not a plain data file."""
    if target.startswith('"') and target.endswith('"') and len(target) >= 2:
        target = target[1:-1]
    if any(c in target for c in "\"'\\`"):
        return None
    names = {target}
    var = re.fullmatch(r"\$([A-Za-z_]\w*)", target)
    if var:  # `cat > "$S" <<'EOF'` with `S=.../x.md` earlier in the same command
        name, head = var.group(1), command[:before]
        values = [v.strip("\"'") for n, v in _ASSIGN.findall(head) if n == name]
        # Exactly one assignment, and no other way to set the name (`S+=`, `for S in`,
        # `read S`, `export S=...`): the bare name occurs once, in that assignment.
        if len(values) != 1 or len(re.findall(rf"(?<![\w$]){name}(?!\w)", head)) != 1:
            return None
        target = values[0]
        names.add(target)
    if not target.lower().endswith(DATA_SUFFIXES):
        return None
    names |= {n.rsplit("/", 1)[-1] for n in names}
    return {n for n in names if n}


def _only_status_commands(tail: str, rest: str) -> bool:
    """True when nothing follows the operator on its line and every later command is a
    plain `sdd-status.py` call (joined by newlines, `&&` or `;`)."""
    if tail.strip():
        return False
    for segment in re.split(r"\n|&&|;", rest):
        if segment.strip() and not _STATUS_CMD.fullmatch(segment):
            return False
    return True


def _heredoc_is_inert(line: str, op: re.Match, command: str, at: int, rest: str) -> bool:
    """`at`: offset of the line in `command`; `rest`: the command text after the body."""
    if op.group(2) is None or line.count("<<") != 1:
        return False
    head = line[: op.start()]
    if "\\" in head:
        return False
    starts = list(_CMD_START.finditer(head))
    owner_at = starts[-1].end() if starts else 0
    owner = head[owner_at:]
    # Everything before the owner — earlier lines and this line — must be plain setup. The
    # separator right before the owner must be `;`, `&&` or a newline (not `|`, `||`, `&`).
    if starts and starts[-1].group(0) not in (";", "&&", "\n"):
        return False
    if not _only_setup(command[: at + (starts[-1].start() if starts else 0)]):
        return False
    words = owner.split()
    if not words or words[0] not in HEREDOC_CONSUMERS:
        return False
    # `"$S"` (a plain variable as the target) is fine; `$(...)`, `${...}`, backticks and an
    # input redirect are not.
    if any(c in owner for c in "`(){}<#'"):
        return False
    if words[0] == "cat":
        redirect = re.fullmatch(r"cat[ \t]+>>?[ \t]*(\S+)", owner.strip())
        if not redirect:
            return False
        targets = [redirect.group(1)]
    else:  # tee [-a] FILE... [> /dev/null] — every file must be a data file
        targets = [w for w in words[1:] if w not in ("-a", "--append")]
        targets = [w for w in targets if w not in (">", ">>", "/dev/null")
                   and not w.startswith(">")]
        if not targets:
            return False
    if any(_resolve_target(target, command, at + op.start()) is None for target in targets):
        return False
    return _only_status_commands(line[op.end():], rest)


def _strip_inert_heredocs(command: str) -> str:
    """Drop the body of each inert here-doc. A small shell lexer tracks quotes, comments and
    every here-doc body, so an operator inside a string or a comment is never taken for a
    real one. Any doubt (an unclosed quote at a here-doc, `$'...'`, a missing terminator)
    returns the command unchanged."""
    lines = command.split("\n")
    offsets, pos = [], 0
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1
    out, i, quote, subst = [], 0, None, False
    while i < len(lines):
        line = lines[i]
        out.append(line)
        pending, j, n = [], 0, len(line)
        while j < n:
            c = line[j]
            if quote == "'":
                quote = None if c == "'" else quote
                j += 1
                continue
            if c == "`" or line.startswith("$(", j):
                subst = True  # nested quoting inside $(...) / `...` is not modelled
            if quote == '"':
                if c == "\\":
                    j += 2
                    continue
                quote = None if c == '"' else quote
                j += 1
                continue
            if c == "\\":
                j += 2
                continue
            if c == "$" and line.startswith("$'", j):
                return command
            if c in "'\"":
                quote = c
                j += 1
                continue
            if c == "#" and (j == 0 or line[j - 1] in " \t;&|()"):
                break  # a comment runs to the end of the line
            if line.startswith("<<<", j):
                j += 3
                continue
            if line.startswith("<<", j):
                op = _HD_OP.match(line, j)
                if not op or subst:
                    return command
                pending.append((op, op.group(3) or op.group(5), op.group(1) == "-"))
                j = op.end()
                continue
            j += 1
        if pending and quote:
            return command
        i += 1
        for op, delim, dash in pending:
            body_start = i
            while i < len(lines) and (lines[i].lstrip("\t") if dash else lines[i]) != delim:
                i += 1
            if i >= len(lines):
                return command  # no terminator: not a here-doc this guard understands
            rest = "\n".join(lines[i + 1:])
            if not (len(pending) == 1 and _heredoc_is_inert(
                    line, op, command, offsets[body_start - 1], rest)):
                out.extend(lines[body_start:i])
            out.append(lines[i])
            i += 1
    return "\n".join(out)


# Only a grep at command position (line start or after `;` `&` `|` `(` `` ` ``, optionally
# behind `git` or `xargs <flags>`). The word inside a quoted string (`bash -c "grep ..."`)
# never matches, so the word parse below always starts at a real command.
GREP_FAMILY = re.compile(
    r"(?:^|(?<=[;&|(\n`]))[ \t]*(?:git[ \t]+|xargs(?:[ \t]+-\S+)*[ \t]+)?"
    r"(grep|egrep|fgrep|rg)(?![\w-])"
)
_SHELL_META = set(";&|<>()\n")
# Option tables: only options whose arity is the same in GNU grep, BSD/macOS grep and
# ripgrep respectively. An option not listed makes the command fully checked.
_GREP = {
    "short_bool": set("inrRlLcvwxoshHEFGPaIUZzbq"),
    "short_value": set("ABm"),
    "long_bool": {"--ignore-case", "--line-number", "--recursive", "--dereference-recursive",
                  "--files-with-matches", "--files-without-match", "--count", "--invert-match",
                  "--word-regexp", "--line-regexp", "--only-matching", "--no-messages",
                  "--no-filename", "--with-filename", "--extended-regexp", "--fixed-strings",
                  "--basic-regexp", "--perl-regexp", "--text", "--null", "--quiet", "--silent",
                  "--color", "--colour"},
    "long_value": {"--after-context", "--before-context", "--max-count", "--include",
                   "--exclude", "--exclude-dir"},
}
_RG = {
    "short_bool": set("inlLcvwxosHIFPaUzqSbuN"),
    "short_value": set("ABCmgtTErjM"),
    "long_bool": {"--ignore-case", "--line-number", "--files-with-matches", "--count",
                  "--invert-match", "--word-regexp", "--line-regexp", "--only-matching",
                  "--no-filename", "--with-filename", "--fixed-strings", "--pcre2", "--text",
                  "--quiet", "--hidden", "--no-ignore", "--smart-case", "--case-sensitive",
                  "--multiline", "--follow"},
    "long_value": {"--after-context", "--before-context", "--context", "--max-count", "--glob",
                   "--type", "--type-not", "--encoding", "--replace", "--threads"},
}


def _shell_words(text: str, pos: int):
    """Words of one simple command from `pos`: [(start, end, value)], or None on doubt.

    Stops at the first unquoted shell metacharacter. Returns None for an unclosed quote.
    """
    words, i, n = [], pos, len(text)
    while True:
        while i < n and text[i] in " \t":
            i += 1
        if i >= n or text[i] in _SHELL_META:
            return words
        start, value = i, []
        while i < n and text[i] not in " \t" and text[i] not in _SHELL_META:
            c = text[i]
            if c == "'":
                close = text.find("'", i + 1)
                if close < 0:
                    return None
                value.append(text[i + 1:close])
                i = close + 1
            elif c == '"':
                # Inside "...", a backslash escapes only $ ` " \ and a newline (Bash rules);
                # before any other character it is a literal backslash (`"\.env"`).
                i += 1
                while i < n and text[i] != '"':
                    if text[i] == "\\" and i + 1 < n and text[i + 1] in '$`"\\\n':
                        value.append(text[i + 1])
                        i += 2
                    else:
                        value.append(text[i])
                        i += 1
                if i >= n:
                    return None
                i += 1
            elif c == "\\":
                if i + 1 >= n:
                    return None
                value.append(text[i + 1])
                i += 2
            else:
                value.append(c)
                i += 1
        words.append((start, i, "".join(value)))


def _grep_pattern_spans(text: str, m: re.Match):
    """Character spans of the search pattern(s) of the grep/rg at `m`; [] on any doubt."""
    table = _RG if m.group(1) == "rg" else _GREP
    is_git = re.match(r"[ \t]*git[ \t]", text[m.start():m.end()].lstrip(";&|(\n`")) is not None
    if is_git and m.group(1) != "grep":
        return []  # `git egrep` / `git rg` are user aliases, which can run anything
    words = _shell_words(text, m.end())
    if not words:
        return []
    # Any `$` or backtick that the shell expands (`$'a\'b'`, `$(...)`, `$VAR`, also inside
    # "...") can change how Bash splits the words, so the parse above is not trusted: keep
    # the full check. Inside '...' both are literal (`'credentials.*\.ts$'`).
    if any(c in _expandable(text[m.end():words[-1][1]]) for c in "$`"):
        return []
    # Pass 1: options. `-e`/`--regexp` values are patterns; then every operand is a file.
    kinds, explicit, k, end_opts, seen_operand = [], False, 0, False, False
    while k < len(words):
        s, e, w = words[k]
        if end_opts or w == "-" or not w.startswith("-"):
            kinds.append("operand")
            seen_operand = True
        elif seen_operand and w == "--" and is_git:
            # `git grep PAT <rev> -- <path>`: for git, `--` always ends the revisions, and
            # POSIXLY_CORRECT does not apply. The paths after it stay operands (checked).
            kinds.append("opt")
            end_opts = True
        elif seen_operand:
            # GNU permutation may be off (POSIXLY_CORRECT), and then this is a file: doubt.
            return []
        elif w == "--":
            kinds.append("opt")
            end_opts = True
        elif w.startswith("--"):
            name, eq, _ = w.partition("=")
            if name == "--regexp":
                explicit = True
                if eq:
                    kinds.append("pattern")
                else:
                    kinds.append("opt")
                    if k + 1 >= len(words):
                        return []
                    kinds.append("pattern")
                    k += 1
            elif name in table["long_value"]:
                kinds.append("opt")
                if not eq:
                    if k + 1 >= len(words):
                        return []
                    kinds.append("opt")  # the value is a file name or glob: still checked
                    k += 1
            elif name in table["long_bool"] and (not eq or name in ("--color", "--colour")):
                kinds.append("opt")
            else:
                return []
        else:  # a short cluster such as -inE, -A2, -epattern
            kinds.append("opt")
            for ci, c in enumerate(w[1:], start=1):
                rest = w[ci + 1:]
                if c in table["short_bool"]:
                    continue
                if c == "e":
                    explicit = True
                    if rest:
                        kinds[-1] = "pattern"
                    else:
                        if k + 1 >= len(words):
                            return []
                        kinds.append("pattern")
                        k += 1
                    break
                if c in table["short_value"]:
                    if not rest:
                        if k + 1 >= len(words):
                            return []
                        kinds.append("opt")
                        k += 1
                    break
                return []
        k += 1
    # Pass 2: without -e the first operand is the pattern (GNU grep permutes options,
    # so pass 1 must see every option first).
    if not explicit:
        for idx, kind in enumerate(kinds):
            if kind == "operand":
                kinds[idx] = "pattern"
                break
    spans = []
    for (s, e, w), kind in zip(words, kinds):
        if kind == "pattern":
            if any(c in _expandable(text[s:e]) for c in "$`"):
                return []
            # An UNQUOTED glob or brace (`.env*`, `.env{,.local}`) or tilde can expand into
            # several words: the first becomes the pattern, the rest become files that grep
            # reads. Only a quoted or escaped literal is one word for sure.
            if any(c in _unquoted(text[s:e]) for c in "*?[]{}~^#"):
                return []
            spans.append((s, e))
    return spans


def _expandable(raw: str) -> str:
    """The characters the shell may expand: everything outside '...' and not escaped by a
    backslash. (Inside "...", `$` and backticks still expand, so they are kept.)"""
    out, i, quote = [], 0, None
    while i < len(raw):
        c = raw[i]
        if quote == "'":
            if c == "'":
                quote = None
        elif c == "\\":
            i += 1
        else:
            if c == '"':
                quote = None if quote == '"' else '"'
            elif c == "'" and quote is None:
                quote = "'"
            else:
                out.append(c)
        i += 1
    return "".join(out)


def _unquoted(raw: str) -> str:
    """The characters of a shell word that are outside quotes and not escaped."""
    out, i, quote = [], 0, None
    while i < len(raw):
        c = raw[i]
        if quote:
            if c == quote:
                quote = None
            elif quote == '"' and c == "\\":
                i += 1
        elif c in "'\"":
            quote = c
        elif c == "\\":
            i += 1
        else:
            out.append(c)
        i += 1
    return "".join(out)


def _blank_grep_patterns(command: str) -> str:
    chars = list(command)
    for m in GREP_FAMILY.finditer(command):
        for s, e in _grep_pattern_spans(command, m):
            chars[s:e] = " " * (e - s)
    return "".join(chars)


def without_inert_text(command: str) -> str:
    return _blank_grep_patterns(_strip_inert_heredocs(command))
