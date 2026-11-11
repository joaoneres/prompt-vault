from dataclasses import dataclass
from uuid import UUID

from domain import Prompt, PromptVersion
from port import EventPublisher, UnitOfWork

from .._helpers import require_prompt


@dataclass(frozen=True, slots=True)
class UpdateContentCommand:
    prompt_id: UUID
    content: str


class UpdateContentUseCase:
    def __init__(self, uow: UnitOfWork, publisher: EventPublisher) -> None:
        self._uow = uow
        self._publisher = publisher

    async def execute(self, command: UpdateContentCommand) -> tuple[Prompt, PromptVersion]:
        """Change content: never edits in place, it creates and activates a new version."""
        async with self._uow:
            prompt = await require_prompt(self._uow.prompts, command.prompt_id)
            version = prompt.add_version(command.content, activate=True)
            await self._uow.prompts.save(prompt)
            await self._uow.commit()
        await self._publisher.publish(prompt.pull_events())
        return prompt, version
