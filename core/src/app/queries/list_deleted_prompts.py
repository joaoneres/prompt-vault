from collections.abc import Sequence

from domain import Prompt
from port import PromptRepository


class ListDeletedPromptsUseCase:
    def __init__(self, prompts: PromptRepository) -> None:
        self._prompts = prompts

    async def execute(self) -> Sequence[Prompt]:
        return await self._prompts.list_deleted()
