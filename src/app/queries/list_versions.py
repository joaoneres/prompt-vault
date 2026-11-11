from dataclasses import dataclass
from uuid import UUID

from domain import PromptVersion
from port import PromptRepository

from .._helpers import require_prompt


@dataclass(frozen=True, slots=True)
class ListVersionsQuery:
    prompt_id: UUID


class ListVersionsUseCase:
    def __init__(self, prompts: PromptRepository) -> None:
        self._prompts = prompts

    async def execute(self, query: ListVersionsQuery) -> tuple[PromptVersion, ...]:
        prompt = await require_prompt(self._prompts, query.prompt_id)
        return prompt.versions
