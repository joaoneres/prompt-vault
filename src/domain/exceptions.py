from .status import PromptStatus


class DomainError(Exception):
    """Base class for all business-rule violations."""


class InvalidPromptError(DomainError):
    """Raised when a prompt or version is built with invalid data."""


class InvalidStateTransitionError(DomainError):
    def __init__(self, current: PromptStatus, target: PromptStatus) -> None:
        super().__init__(f"Cannot transition prompt from '{current}' to '{target}'")
        self.current = current
        self.target = target


class PromptDeletedError(DomainError):
    def __init__(self, action: str) -> None:
        super().__init__(f"Cannot {action} a deleted prompt; restore it first")
        self.action = action


class VersionNotFoundError(DomainError):
    def __init__(self, number: int) -> None:
        super().__init__(f"Version {number} does not exist in this prompt")
        self.number = number


class InvalidVersionComparisonError(DomainError):
    def __init__(self, number: int) -> None:
        super().__init__(f"Cannot compare version {number} with itself")
        self.number = number
