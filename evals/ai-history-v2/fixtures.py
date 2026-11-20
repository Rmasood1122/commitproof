"""Build the 8 deterministic fixture repositories for the /ai-history 2.0.0 evals.

Usage: python fixtures.py OUT_DIR

Creates OUT_DIR/a ... OUT_DIR/h. Every commit has a fixed author, a fixed
author date and a fixed committer date, and git runs with an empty global
config and no system config, so the repositories (and their commit ids) are
the same on every machine.

  a  no trailers                     e  lowercase trailers / extra spaces
  b  every commit has a Claude trailer  f  empty repository (no commits)
  c  mixed, with --no-ff merges      g  5,000 synthetic commits (fast-import)
  d  Assisted-by only                h  squash, rebase, cherry-pick, amend
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CLAUDE = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
CLAUDE_GH = "Co-authored-by: Claude <noreply@anthropic.com>"

DANA = ("Dana Lee", "dana@example.com")
PRIYA = ("Priya Nair", "priya@example.com")
SAM = ("Sam Ortiz", "sam@example.com")


def isolated_env(scratch: Path) -> dict:
    """Environment for git: empty global config, no system config, no
    inherited identity or date overrides."""
    scratch.mkdir(parents=True, exist_ok=True)
    empty = scratch / "empty-gitconfig"
    empty.write_text("", encoding="utf-8")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("GIT_AUTHOR_", "GIT_COMMITTER_", "GIT_DIR", "GIT_WORK_TREE"))}
    env.update({"GIT_CONFIG_GLOBAL": str(empty), "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0", "GIT_EDITOR": "true"})
    return env


def rm_tree(path: Path) -> None:
    """shutil.rmtree that also removes git's read-only object files on Windows."""
    def force(func, p, _exc):
        os.chmod(p, 0o700)
        func(p)
    if path.exists():
        shutil.rmtree(path, onexc=force)


def lines(prefix: str, n: int) -> str:
    return "".join(f"{prefix} line {i}\n" for i in range(1, n + 1))


class Repo:
    def __init__(self, path: Path, env: dict):
        self.path, self.env = path, env
        path.mkdir(parents=True)
        self.git("init", "-q", "-b", "main")
        for key, value in (("user.name", "Fixture Builder"), ("user.email", "builder@example.com"),
                           ("core.autocrlf", "false"), ("commit.gpgsign", "false")):
            self.git("config", key, value)

    def git(self, *args: str, who=None, date=None, committer_date=None, stdin: bytes | None = None) -> str:
        env = dict(self.env)
        if who:
            env.update(GIT_AUTHOR_NAME=who[0], GIT_AUTHOR_EMAIL=who[1],
                       GIT_COMMITTER_NAME=who[0], GIT_COMMITTER_EMAIL=who[1])
        if date:
            env["GIT_AUTHOR_DATE"] = date
            env["GIT_COMMITTER_DATE"] = committer_date or date
        elif committer_date:
            env["GIT_COMMITTER_DATE"] = committer_date
        r = subprocess.run(["git", *args], cwd=self.path, env=env, input=stdin, capture_output=True)
        if r.returncode:
            raise RuntimeError(f"git {' '.join(args)} failed in {self.path}:\n{r.stderr.decode('utf-8', 'replace')}")
        return r.stdout.decode("utf-8")

    def put(self, rel: str, content: str | bytes, append: bool = False) -> None:
        p = self.path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode("utf-8") if isinstance(content, str) else content
        with open(p, "ab" if append else "wb") as fh:
            fh.write(data)

    def commit(self, who, date: str, message: str, committer_date: str | None = None) -> str:
        msg = self.path / ".git" / "FIXTURE_MSG"
        msg.write_bytes(message.encode("utf-8"))
        self.git("add", "-A")
        self.git("commit", "-q", "--cleanup=verbatim", "-F", str(msg),
                 who=who, date=date, committer_date=committer_date)
        return self.git("rev-parse", "HEAD").strip()


def d(day: str, hour: int = 10) -> str:
    return f"{day} {hour:02d}:00:00 +0000"


def build_a(r: Repo) -> None:
    """No trailers. Body text that mentions Claude is not a trailer."""
    plan = [
        (DANA, "2026-01-05", "Add parser", "parser.py", 30, ""),
        (PRIYA, "2026-01-09", "Add tests", "test_parser.py", 22, "Asked Claude to review the loop.\n"),
        (DANA, "2026-01-14", "Handle empty input", "parser.py", 6, ""),
        (SAM, "2026-01-21", "Add CLI", "cli.py", 18, ""),
        (DANA, "2026-02-02", "Add docs", "README.md", 12,
         "\U0001F916 Generated with [Claude Code](https://claude.com/claude-code)\n"),
        (PRIYA, "2026-02-06", "Speed up parser", "parser.py", 9, ""),
        (DANA, "2026-02-11", "Add config", "config.py", 14, ""),
        (SAM, "2026-02-19", "Fix CLI flags", "cli.py", 4, ""),
        (DANA, "2026-03-03", "Refactor", "parser.py", 7, ""),
        (PRIYA, "2026-03-10", "More tests", "test_parser.py", 11, ""),
        (DANA, "2026-03-17", "Release notes", "CHANGES.md", 5, ""),
    ]
    for who, day, subject, path, n, body in plan:
        r.put(path, lines(subject, n), append=True)
        r.commit(who, d(day), subject + ("\n\n" + body if body else "\n"))
    r.put("logo.bin", bytes(range(256)) * 4)  # binary: numstat prints "-", counts 0
    r.commit(DANA, d("2026-03-24"), "Add logo\n")


def build_b(r: Repo) -> None:
    """Every commit carries a Claude trailer; four are session links."""
    for i in range(10):
        who = PRIYA if i % 5 < 3 else SAM
        day = f"2026-{10 + i // 5:02d}-{3 + 2 * (i % 5):02d}"
        trailer = CLAUDE if i % 5 < 3 else f"Claude-Session: https://claude.ai/code/session_01B{i:04d}"
        r.put(f"src/mod{i}.py", lines(f"mod{i}", 5 + 3 * i))
        r.commit(who, d(day), f"Add module {i}\n\n{trailer}\n")


def build_c(r: Repo) -> None:
    """Mixed history with two --no-ff merges whose messages carry a Claude
    trailer (merges are skipped), name-boundary negatives and a pure rename."""
    r.put("README.md", lines("readme", 10)); r.commit(DANA, d("2026-09-02"), "Add readme\n")
    r.put("app.py", lines("app", 40)); r.commit(PRIYA, d("2026-09-05"), f"Add app\n\n{CLAUDE}\n")
    r.put("data/big.txt", lines("data", 200)); r.commit(DANA, d("2026-09-09"), "Add data file\n")

    r.git("switch", "-q", "-c", "feat-a")
    r.put("a.py", lines("a", 25)); r.commit(SAM, d("2026-09-12"), f"Feature A parser\n\n{CLAUDE_GH}\n")
    r.put("a.py", lines("a2", 10), append=True)
    r.commit(SAM, d("2026-09-15"), "Feature A tests\n\nCo-authored-by: Claudette Ng <claudette@example.com>\n")
    r.put("a_doc.md", lines("adoc", 15))
    r.commit(PRIYA, d("2026-09-20"), "Feature A docs\n\nClaude-Session: https://claude.ai/code/session_01C0003\n")

    r.git("switch", "-q", "main")
    r.git("mv", "data/big.txt", "data/large.txt"); r.commit(DANA, d("2026-09-18"), "Rename data file\n")
    r.git("merge", "-q", "--no-ff", "feat-a", "-m", f"Merge feature A\n\n{CLAUDE}", who=DANA, date=d("2026-09-22"))

    r.git("switch", "-q", "-c", "feat-b")
    r.put("b.py", lines("b", 30))
    r.commit(DANA, d("2026-10-03"), "Feature B\n\nCo-authored-by: Jean-Claude Roy <jc@example.com>\n")
    r.put("b.py", lines("b2", 12), append=True); r.commit(PRIYA, d("2026-10-07"), f"Feature B fix\n\n{CLAUDE}\n")
    r.git("switch", "-q", "main")
    r.put("README.md", lines("readme2", 3), append=True); r.commit(SAM, d("2026-10-05"), "Update readme\n")
    r.git("merge", "-q", "--no-ff", "feat-b", "-m", f"Merge feature B\n\n{CLAUDE}", who=PRIYA, date=d("2026-10-10"))

    r.put("c.py", lines("c", 18)); r.commit(SAM, d("2026-10-20"), f"Add c\n\n{CLAUDE}\n")
    r.put("app.py", lines("app2", 5), append=True); r.commit(DANA, d("2026-11-02"), "Tweak app\n")
    r.put("d.py", lines("d", 22))
    r.commit(PRIYA, d("2026-11-05"), "Add d\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\n")
    r.put("c.py", lines("c2", 4), append=True); r.commit(SAM, d("2026-11-08"), "Fix c\n")
    r.put("e.py", lines("e", 9))
    r.commit(DANA, d("2026-11-12"),
             "Add e\n\nCo-authored-by: claude[bot] <209825114+claude[bot]@users.noreply.github.com>\n")
    r.put("d.py", lines("d2", 6), append=True); r.commit(PRIYA, d("2026-11-14"), "Polish d\n")


def build_d(r: Repo) -> None:
    """Assisted-by only: counts when the value starts with the word Claude,
    or is exactly LLM (any letter case, spaces around the colon and at the
    end allowed, CRLF allowed)."""
    kees, greg = ("Kees Example", "kees@example.com"), ("Greg Example", "greg@example.com")
    msgs = [
        (kees, "Fix overflow\n\nAssisted-by: Claude:claude-opus-5-5 coccinelle\n"),
        (greg, "Tidy driver\n\nAssisted-by: claude-code\n"),
        (kees, "Rework locking\n\nAssisted-by: LLM\n"),                     # counts: exactly LLM
        (greg, "Add helper\n\nAssisted-by: GitHub Copilot\n"),
        (kees, "Fix leak\n\nAssisted-by: Anthropic Claude\n"),
        (greg, "Fix race\n\nAssisted-by: Claude:claude-sonnet-5-5\nSigned-off-by: Greg Example <greg@example.com>\n"),
        (kees, "Update docs\n\nSigned-off-by: Kees Example <kees@example.com>\n"),
        (greg, "Rename flag\n\nAssisted-by: Claudebot\n"),
        (kees, "Port test\n\nAssisted-by: LLM:gpt-4o\n"),                  # not counted: names a model
        (greg, "Split file\n\nAssisted-by: LLMs\n"),                       # not counted: not exactly LLM
        (kees, "Clean up\n\nassisted-by :  llm  \n"),                      # counts: case and spaces
        (greg, "Wrap up (CRLF)\r\n\r\nAssisted-by: LLM\r\n"),              # counts: CRLF line ending
    ]
    for i, (who, msg) in enumerate(msgs):
        r.put(f"drivers/x{i}.c", lines(f"x{i}", 4 + i))
        r.commit(who, d(f"2026-0{5 + i // 4}-{10 + i:02d}"), msg)


def build_e(r: Repo) -> None:
    """Letter case and spacing variants, a CRLF message, an indented
    trailer (not counted) and a body line shaped like a trailer (counted)."""
    riley, jo = ("Riley Chen", "riley@example.com"), ("Jo Park", "jo@example.com")
    msgs = [
        (riley, "One\n\nco-authored-by: claude <noreply@anthropic.com>\n"),
        (jo, "Two\n\nCO-AUTHORED-BY:CLAUDE\n"),
        (riley, "Three\n\nCo-Authored-By:\tClaude <noreply@anthropic.com>\n"),
        (jo, "Four\n\nCo-Authored-By :  Claude <noreply@anthropic.com>\n"),
        (riley, "Five\n\nclaude-session:abc123\n"),
        (jo, "Six (CRLF)\r\n\r\nCo-Authored-By: Claude <noreply@anthropic.com>\r\n"),
        (riley, "Seven\n\n Co-Authored-By: Claude <noreply@anthropic.com>\n"),
        (jo, "Eight\n\nWe tag AI help like this:\nCo-Authored-By: Claude is the form we use.\n\nThat is all.\n"),
        (riley, "Nine\n"),
        (jo, "Ten\n\nCo-Authored-By: CLAUDE-BOT <bot@example.com>\n"),
    ]
    for i, (who, msg) in enumerate(msgs):
        r.put(f"f{i}.txt", lines(f"f{i}", 2 + i))
        r.commit(who, d(f"2026-07-{1 + 2 * i:02d}"), msg)


def build_g(r: Repo) -> None:
    """5,000 commits through git fast-import: 20 authors with distinct
    counts (155, 165, ... 345), spread evenly over 30 months; a Claude
    trailer when i % 20 < 7; i % 50 + 1 lines added per commit."""
    names = ["Ada Byrne", "Ben Okafor", "Cleo Marsh", "Dev Rao", "Eli Stone", "Fay Lin", "Gus Ward",
             "Hana Ito", "Ivo Petrov", "Jin Park", "Kai Moss", "Lea Roth", "Max Hale", "Nia Cole",
             "Oto Saar", "Pia Lund", "Quinn Ray", "Rui Sato", "Sia Vance", "Tom Webb"]
    counts = [155 + 10 * k for k in range(20)]
    assert sum(counts) == 5000
    order = sorted(((j + 0.5) / counts[k], k) for k in range(20) for j in range(counts[k]))
    start = datetime(2024, 6, 1, tzinfo=timezone.utc)
    end = datetime(2026, 11, 20, tzinfo=timezone.utc)
    step = (end - start) / 5000
    trailers = [CLAUDE, "Claude-Session: https://claude.ai/code/session_01G{i:05d}",
                "Assisted-by: Claude:claude-opus-5-5"]
    out = bytearray()

    def data(b: bytes) -> None:
        out.extend(b"data %d\n" % len(b)); out.extend(b); out.extend(b"\n")

    for i, (_, k) in enumerate(order):
        ts = int((start + step * i).timestamp())
        who = f"{names[k]} <{names[k].split()[0].lower()}@example.com> {ts} +0000\n".encode()
        msg = f"Change {i}\n"
        if i % 20 < 7:
            msg += "\n" + trailers[i % 3].format(i=i) + "\n"
        out.extend(b"commit refs/heads/main\nmark :%d\nauthor " % (i + 1) + who + b"committer " + who)
        data(msg.encode())
        if i:
            out.extend(b"from :%d\n" % i)
        out.extend(f"M 644 inline d/{i // 100:02d}/{i}.txt\n".encode())
        data(lines(f"c{i}", i % 50 + 1).encode())
    r.git("fast-import", "--quiet", stdin=bytes(out))
    r.git("reset", "-q", "--hard", "main")


def build_h(r: Repo) -> None:
    """Squash merges (one drops the trailers, one keeps GitHub-style
    trailers), a rebase that moves commits into the next month, a
    cherry-pick and an amend."""
    morgan, alex = ("Morgan Diaz", "morgan@example.com"), ("Alex Kim", "alex@example.com")
    r.put("base.py", lines("base", 20)); r.commit(morgan, d("2026-03-02"), "Base\n")

    r.git("switch", "-q", "-c", "feat-s1")
    r.put("s1.py", lines("s1", 10)); r.commit(morgan, d("2026-03-05"), f"S1 part 1\n\n{CLAUDE}\n")
    r.put("s1.py", lines("s1b", 8), append=True); r.commit(morgan, d("2026-03-06"), f"S1 part 2\n\n{CLAUDE}\n")
    r.git("switch", "-q", "main"); r.git("merge", "-q", "--squash", "feat-s1")
    r.commit(morgan, d("2026-03-10"), "Feature S1 (#12)\n")  # squash message dropped the trailers

    r.git("switch", "-q", "-c", "feat-s2")
    r.put("s2.py", lines("s2", 7)); r.commit(alex, d("2026-03-12"), f"S2 part 1\n\n{CLAUDE_GH}\n")
    r.put("s2.py", lines("s2b", 5), append=True); r.commit(alex, d("2026-03-13"), "S2 part 2\n")
    r.git("switch", "-q", "main"); r.git("merge", "-q", "--squash", "feat-s2")
    r.commit(alex, d("2026-03-15"), f"Feature S2 (#13)\n\n* S2 part 1\n\n{CLAUDE_GH}\n\n* S2 part 2\n")

    r.git("switch", "-q", "-c", "feat-r")
    r.put("r.py", lines("r", 6)); r.commit(alex, d("2026-03-28"), f"R1\n\n{CLAUDE}\n")
    r.put("r.py", lines("r2", 4), append=True); r.commit(alex, d("2026-03-29"), "R2\n")
    r.git("switch", "-q", "main")
    r.put("main.py", lines("main", 3)); r.commit(morgan, d("2026-03-31"), "Main change\n")
    r.git("switch", "-q", "feat-r")
    r.git("rebase", "-q", "main", committer_date=d("2026-04-02"))  # authored in March, committed in April
    r.git("switch", "-q", "main"); r.git("merge", "-q", "--ff-only", "feat-r")

    r.git("switch", "-q", "-c", "side")
    r.put("hotfix.py", lines("hotfix", 2))
    sha = r.commit(morgan, d("2026-04-05"), "Hotfix\n\nClaude-Session: https://claude.ai/code/session_01H0001\n")
    r.git("switch", "-q", "main")
    r.git("cherry-pick", sha, committer_date=d("2026-04-08"))

    r.put("typo.py", lines("typo", 5)); r.commit(morgan, d("2026-04-10"), "Typo\n")
    r.git("commit", "-q", "--amend", "--no-edit", committer_date=d("2026-05-01"))


BUILDERS = {"a": build_a, "b": build_b, "c": build_c, "d": build_d,
            "e": build_e, "f": lambda r: None, "g": build_g, "h": build_h}


def build_all(out: Path, only: str = "abcdefgh") -> dict[str, Path]:
    env = isolated_env(out / "_git")
    made = {}
    for name in only:
        path = out / name
        rm_tree(path)
        BUILDERS[name](Repo(path, env))
        made[name] = path
    return made


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures-out").resolve()
    for name, path in build_all(target, sys.argv[2] if len(sys.argv) > 2 else "abcdefgh").items():
        print(name, path)
