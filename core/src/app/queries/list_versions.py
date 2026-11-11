from dataclasses import dataclass
from uuid import UUID

from domain import Prompt
from port import PromptRepository

from .._helpers import require_prompt


@dataclass(frozen=True, slots=True)
class ListVersionsQuery:
    prompt_id: UUID


class ListVersionsUseCase:
    def __init__(self, prompts: PromptRepository) -> None:
        self._prompts = prompts

    async def execute(self, query: ListVersionsQuery) -> Prompt:
        return await require_prompt(self._prompts, query.prompt_id)
