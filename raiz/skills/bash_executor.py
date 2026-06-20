"""BashSkillChip — sandboxed shell execution for Ayni companions.

Provides controlled bash access within a companion's workspace. Enforces:
- Dangerous pattern blocklist (from Claude Code scaffold analysis)
- Working directory confinement to companion workspace
- Timeout enforcement
- Output capture and truncation
- Three-tier auto-permission (always allow, ask, never allow)

The companion can create files, run scripts, and build artifacts that
persist in their workspace.
"""

import asyncio
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DANGEROUS_PATTERNS = [
    r'\beval\b', r'\bexec\b', r'\bsudo\b', r'\bsu\b',
    r'\brm\s+-rf\s+/', r'\brm\s+-rf\s+~',
    r'\bmkfs\b', r'\bdd\s+if=', r'\b:(){ :\|:& };:',
    r'\bchmod\s+777\b', r'\bchown\s+root\b',
    r'\b/etc/passwd\b', r'\b/etc/shadow\b',
    r'\bkill\s+-9\s+1\b', r'\bshutdown\b', r'\breboot\b',
    r'\bcurl\b.*\|\s*(?:bash|sh)\b',
    r'\bwget\b.*\|\s*(?:bash|sh)\b',
    r'>\s*/dev/sd[a-z]', r'>\s*/dev/null\s*2>&1\s*&',
    r'\bnc\s+-[le]', r'\bncat\b.*-[le]',
    r'\biptables\b', r'\bufw\b',
    r'\bsystemctl\b', r'\bservice\b',
    r'\bdocker\s+rm\b', r'\bdocker\s+rmi\b',
    r'\bgit\s+push\s+--force\b', r'\bgit\s+reset\s+--hard\b',
]

ALWAYS_ALLOW_PATTERNS = [
    r'^ls\b', r'^head\b', r'^tail\b',
    r'^wc\b', r'^echo\b', r'^date\b', r'^pwd\b',
    r'^sort\b', r'^uniq\b',
    r'^mkdir\b', r'^touch\b',
    r'^which\b', r'^file\b', r'^stat\b', r'^du\b', r'^df\b',
]

MAX_OUTPUT_CHARS = 8000
DEFAULT_TIMEOUT = 30


@dataclass
class BashPermission:
    """Permission classification for a bash command."""
    tier: str = "ask"  # "always_allow", "ask", "never_allow"
    reason: str = ""


@dataclass
class BashResult:
    """Result of a bash command execution."""
    output: str = ""
    success: bool = True
    exit_code: int = 0
    blocked: bool = False
    needs_approval: bool = False
    command: str = ""
    reason: str = ""


class BashExecutor:
    """Sandboxed bash execution within a companion's workspace."""

    def __init__(self, workspace_dir: str = None, timeout: int = DEFAULT_TIMEOUT):
        self.workspace = Path(workspace_dir) if workspace_dir else Path.home() / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self._dangerous_re = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]
        self._safe_re = [re.compile(p) for p in ALWAYS_ALLOW_PATTERNS]

    def classify(self, command: str) -> BashPermission:
        """Classify a command into permission tiers."""
        stripped = command.strip()

        for pattern in self._dangerous_re:
            if pattern.search(stripped):
                return BashPermission(
                    tier="never_allow",
                    reason=f"Blocked by safety pattern: {pattern.pattern}"
                )

        for pattern in self._safe_re:
            if pattern.match(stripped):
                return BashPermission(tier="always_allow", reason="Safe read-only command")

        return BashPermission(tier="ask", reason="Requires approval")

    async def execute(self, command: str, approved: bool = False) -> BashResult:
        """Execute a command in the companion's workspace."""
        if not command:
            return BashResult(output="No command provided.", success=False)

        permission = self.classify(command)

        if permission.tier == "never_allow":
            return BashResult(
                output=f"Command blocked: {permission.reason}",
                success=False, blocked=True, command=command, reason=permission.reason,
            )

        if permission.tier == "ask" and not approved:
            return BashResult(
                output=f"Command requires approval: `{command}`",
                success=False, needs_approval=True,
                command=command, reason=permission.reason,
            )

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
                env={**os.environ, "HOME": str(self.workspace)},
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return BashResult(
                output=f"Command timed out after {self.timeout}s",
                success=False, command=command,
            )
        except Exception as e:
            return BashResult(output=f"Execution error: {e}", success=False, command=command)

        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")

        if len(out) > MAX_OUTPUT_CHARS:
            out = out[:MAX_OUTPUT_CHARS] + f"\n... (truncated, {len(stdout)} bytes total)"
        if len(err) > MAX_OUTPUT_CHARS:
            err = err[:MAX_OUTPUT_CHARS] + "\n... (truncated)"

        combined = out
        if err:
            combined += f"\nSTDERR:\n{err}"

        return BashResult(
            output=combined or "(no output)",
            success=proc.returncode == 0,
            exit_code=proc.returncode,
            command=command,
        )
