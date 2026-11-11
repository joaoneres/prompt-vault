from uuid import UUID

from domain import Prompt
from port import PromptRepository

from .exceptions import PromptNotFoundError


async def require_prompt(prompts: PromptRepository, prompt_id: UUID) -> Prompt:
    prompt = await prompts.get(prompt_id)
    if prompt is None:
        raise PromptNotFoundError(prompt_id)
    return prompt
