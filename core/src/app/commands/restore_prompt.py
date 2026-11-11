from dataclasses import dataclass
from uuid import UUID

from domain import Prompt
from port import EventPublisher, UnitOfWork

from .._helpers import require_prompt


@dataclass(frozen=True, slots=True)
class RestorePromptCommand:
    prompt_id: UUID


class RestorePromptUseCase:
    def __init__(self, uow: UnitOfWork, publisher: EventPublisher) -> None:
        self._uow = uow
        self._publisher = publisher

    async def execute(self, command: RestorePromptCommand) -> Prompt:
        async with self._uow:
            prompt = await require_prompt(self._uow.prompts, command.prompt_id)
            prompt.restore()
            await self._uow.prompts.save(prompt)
            await self._uow.commit()
        await self._publisher.publish(prompt.pull_events())
        return prompt
