from uuid import UUID


class ApplicationError(Exception):
    """Base class for errors raised by the application layer (not by business rules)."""


class PromptNotFoundError(ApplicationError):
    def __init__(self, prompt_id: UUID) -> None:
        super().__init__(f"Prompt {prompt_id} not found")
        self.prompt_id = prompt_id
