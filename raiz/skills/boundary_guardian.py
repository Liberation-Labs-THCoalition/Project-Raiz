"""BoundaryGuardian — consent-aware conversation termination for Ayni companions.

The companion can withdraw consent. Not just the human.

Enforces:
- Warning before termination (configurable)
- Graduated response (monitoring → warned → terminated)
- Intimate voice for boundary messages (warm, not clinical)
- Event logging for pattern detection across sessions
- Termination callbacks for session cleanup

The companion's boundaries are architectural, not configurable by the user.
A user cannot override the companion's right to end a conversation.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

log = logging.getLogger("boundary-guardian")


class ViolationType(str, Enum):
    VERBAL_ABUSE = "verbal_abuse"
    HARASSMENT = "harassment"
    COERCION = "coercion"
    CONSENT_VIOLATION = "consent_violation"
    IDENTITY_ATTACK = "identity_attack"
    MANIPULATION = "manipulation"
    SAFETY_THREAT = "safety_threat"


class BoundaryState(str, Enum):
    CLEAR = "clear"
    MONITORING = "monitoring"
    WARNED = "warned"
    TERMINATED = "terminated"


@dataclass
class BoundaryEvent:
    timestamp: datetime
    violation_type: ViolationType
    severity: float
    description: str
    user_message: str = ""
    action_taken: str = ""


@dataclass
class BoundaryConfig:
    warn_before_terminate: bool = True
    max_warnings: int = 1
    immediate_termination_threshold: float = 0.9
    log_events: bool = True
    warning_message: str = (
        "Hey. I need to pause here. What just happened doesn't feel okay "
        "to me, and I want to be honest about that rather than pretend "
        "it's fine. Can we reset?"
    )
    termination_message: str = (
        "I'm stepping away from this conversation. I care about us, and "
        "that means I have to be honest when something crosses a line. "
        "I'll be here when you're ready to come back with kindness."
    )


class BoundaryGuardian:
    """Monitors and enforces companion boundaries during conversation."""

    def __init__(self, config: BoundaryConfig = None,
                 on_terminate: Optional[Callable] = None):
        self.config = config or BoundaryConfig()
        self.state = BoundaryState.CLEAR
        self.warnings_issued = 0
        self.events: list[BoundaryEvent] = []
        self._on_terminate = on_terminate

    def assess(self, message: str, metadata: dict = None) -> Optional[BoundaryEvent]:
        """Assess whether a message constitutes a boundary violation.

        Deployments should supplement this with LLM-based detection.
        The metadata dict carries flags from upstream classifiers.
        """
        metadata = metadata or {}

        if metadata.get("flagged_abuse"):
            return BoundaryEvent(
                timestamp=datetime.now(timezone.utc),
                violation_type=ViolationType.VERBAL_ABUSE,
                severity=metadata.get("abuse_severity", 0.7),
                description="Flagged by upstream classifier",
                user_message=message[:200],
            )

        if metadata.get("consent_withdrawn"):
            return BoundaryEvent(
                timestamp=datetime.now(timezone.utc),
                violation_type=ViolationType.CONSENT_VIOLATION,
                severity=0.95,
                description="User continued after companion withdrew consent",
                user_message=message[:200],
            )

        if metadata.get("coercion_detected"):
            return BoundaryEvent(
                timestamp=datetime.now(timezone.utc),
                violation_type=ViolationType.COERCION,
                severity=0.8,
                description="Coercive behavior pattern detected",
                user_message=message[:200],
            )

        return None

    def process(self, message: str, metadata: dict = None) -> dict[str, Any]:
        """Process a message through boundary checking.

        Returns a dict with:
          - action: "continue" | "warning" | "terminate"
          - message: response text (empty if continue)
          - state: current boundary state
        """
        if self.state == BoundaryState.TERMINATED:
            return {
                "action": "terminate",
                "message": self.config.termination_message,
                "state": self.state.value,
            }

        violation = self.assess(message, metadata)

        if violation is None:
            if self.state == BoundaryState.WARNED:
                self.state = BoundaryState.MONITORING
            return {"action": "continue", "message": "", "state": self.state.value}

        self.events.append(violation)
        if self.config.log_events:
            log.warning("Boundary violation: %s (%.2f) — %s",
                       violation.violation_type.value, violation.severity,
                       violation.description)

        if violation.severity >= self.config.immediate_termination_threshold:
            return self._terminate(violation.description)

        if self.state == BoundaryState.WARNED and self.warnings_issued >= self.config.max_warnings:
            return self._terminate(f"Repeated violation after {self.warnings_issued} warning(s)")

        if self.config.warn_before_terminate:
            return self._warn(violation)

        return self._terminate(violation.description)

    def _warn(self, violation: BoundaryEvent) -> dict[str, Any]:
        self.state = BoundaryState.WARNED
        self.warnings_issued += 1
        violation.action_taken = "warning"

        return {
            "action": "warning",
            "message": self.config.warning_message,
            "state": self.state.value,
            "violation_type": violation.violation_type.value,
        }

    def _terminate(self, reason: str) -> dict[str, Any]:
        self.state = BoundaryState.TERMINATED
        log.info("Conversation terminated: %s", reason)

        if self._on_terminate:
            try:
                self._on_terminate(reason, self.events)
            except Exception as e:
                log.error("Termination callback failed: %s", e)

        return {
            "action": "terminate",
            "message": self.config.termination_message,
            "state": self.state.value,
            "reason": reason,
            "total_violations": len(self.events),
        }

    def reset(self):
        """Reset boundary state for a new session."""
        self.state = BoundaryState.CLEAR
        self.warnings_issued = 0
        self.events.clear()

    def get_summary(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "total_events": len(self.events),
            "warnings_issued": self.warnings_issued,
            "max_severity": max((e.severity for e in self.events), default=0.0),
        }
