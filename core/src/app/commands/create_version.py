from dataclasses import dataclass
from uuid import UUID

from port import EventPublisher, UnitOfWork

from .._helpers import require_prompt


@dataclass(frozen=True, slots=True)
class CreateVersionCommand:
    prompt_id: UUID
    content: str
    activate: bool = False


class CreateVersionUseCase:
    def __init__(self, uow: UnitOfWork, publisher: EventPublisher) -> None:
        self._uow = uow
        self._publisher = publisher

    async def execute(self, command: CreateVersionCommand) -> int:
        """Add a new version to an existing prompt. Returns the new version number."""
        async with self._uow:
            prompt = await require_prompt(self._uow.prompts, command.prompt_id)
            version = prompt.add_version(command.content, activate=command.activate)
            await self._uow.prompts.save(prompt)
            await self._uow.commit()
        await self._publisher.publish(prompt.pull_events())
        return version.number
