from enum import StrEnum


class PromptStatus(StrEnum):
    """Lifecycle state of a prompt."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"

    def can_transition_to(self, target: "PromptStatus") -> bool:
        return target in _ALLOWED_TRANSITIONS[self]


# Explicit state machine. DELETED -> ACTIVE/INACTIVE is a restore (soft deletion).
_ALLOWED_TRANSITIONS: dict[PromptStatus, frozenset[PromptStatus]] = {
    PromptStatus.ACTIVE: frozenset({PromptStatus.INACTIVE, PromptStatus.DELETED}),
    PromptStatus.INACTIVE: frozenset({PromptStatus.ACTIVE, PromptStatus.DELETED}),
    PromptStatus.DELETED: frozenset({PromptStatus.ACTIVE, PromptStatus.INACTIVE}),
}
