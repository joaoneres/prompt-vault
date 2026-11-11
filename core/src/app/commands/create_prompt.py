from dataclasses import dataclass
from uuid import UUID

from domain import Prompt
from port import EventPublisher, UnitOfWork


@dataclass(frozen=True, slots=True)
class CreatePromptCommand:
    name: str
    content: str


class CreatePromptUseCase:
    def __init__(self, uow: UnitOfWork, publisher: EventPublisher) -> None:
        self._uow = uow
        self._publisher = publisher

    async def execute(self, command: CreatePromptCommand) -> UUID:
        prompt = Prompt.create(command.name, command.content)
        async with self._uow:
            await self._uow.prompts.save(prompt)
            await self._uow.commit()
        await self._publisher.publish(prompt.pull_events())
        return prompt.id
