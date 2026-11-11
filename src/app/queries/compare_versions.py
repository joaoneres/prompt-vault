from dataclasses import dataclass
from uuid import UUID

from domain import DiffStrategy, VersionDiff
from port import PromptRepository

from .._helpers import require_prompt


@dataclass(frozen=True, slots=True)
class CompareVersionsQuery:
    prompt_id: UUID
    from_version: int
    to_version: int


class CompareVersionsUseCase:
    def __init__(self, prompts: PromptRepository, strategy: DiffStrategy) -> None:
        self._prompts = prompts
        self._strategy = strategy

    async def execute(self, query: CompareVersionsQuery) -> VersionDiff:
        prompt = await require_prompt(self._prompts, query.prompt_id)
        return prompt.diff(query.from_version, query.to_version, self._strategy)
