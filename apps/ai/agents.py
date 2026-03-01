from __future__ import annotations as _annotations

from collections.abc import Awaitable, Callable
from enum import StrEnum

from django.conf import settings
from django.utils import timezone
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.toolsets import AbstractToolset

from apps.ai.tools import admin_db, email_toolset, weather_toolset
from apps.ai.types import UserDependencies
from apps.chat.prompts import get_default_system_prompt
from apps.users.models import CustomUser

# Type alias for instruction items (can be strings or callables)
InstructionsType = str | Callable[[RunContext[UserDependencies]], Awaitable[str]] | Callable[[], str]


async def add_user_name(ctx: RunContext[UserDependencies]) -> str:
    return f"The user's name is {ctx.deps.user.get_display_name()}"


async def add_user_email(ctx: RunContext[UserDependencies]) -> str:
    return f"The user's email is {ctx.deps.user.email}"


async def current_datetime(ctx: RunContext[UserDependencies]) -> str:
    return f"The current datetime is {timezone.now()}"


DEFAULT_INSTRUCTIONS: list[InstructionsType] = [
    get_default_system_prompt(),
    add_user_name,
    add_user_email,
    current_datetime,
]


class AgentTypes(StrEnum):
    CHAT = "chat"  # Simple chat, no tools
    WEATHER = "weather"
    ADMIN = "admin"

    @classmethod
    def from_string(cls, value: str) -> AgentTypes:
        """Convert a string to AgentTypes, defaulting to CHAT for invalid values."""
        try:
            return cls(value)
        except ValueError:
            return cls.CHAT


def get_agent(agent_type: AgentTypes = AgentTypes.CHAT) -> Agent[UserDependencies]:
    if agent_type == AgentTypes.CHAT:
        return get_chat_agent()
    elif agent_type == AgentTypes.WEATHER:
        return get_weather_agent()
    elif agent_type == AgentTypes.ADMIN:
        return get_admin_agent()
    else:
        raise ValueError(f"Invalid agent type: {agent_type}")


def get_chat_agent():
    """Simple chat agent with no tools."""
    return _get_agent([])


def get_weather_agent():
    return _get_agent([weather_toolset])


def get_admin_agent():
    return _get_agent([admin_db, email_toolset])


def _get_agent(toolsets: list[AbstractToolset]):
    return Agent(
        settings.DEFAULT_AI_MODEL,
        toolsets=toolsets,
        instructions=DEFAULT_INSTRUCTIONS,
        retries=2,
        deps_type=UserDependencies,
    )


def convert_openai_to_pydantic_messages(openai_messages: list[dict]) -> list[ModelMessage]:
    """Convert OpenAI-style messages to Pydantic AI ModelMessage format."""
    pydantic_messages: list[ModelMessage] = []

    for msg in openai_messages:
        role = msg.get("role")
        content = msg.get("content")

        if not isinstance(content, str):
            continue  # Skip messages without valid string content

        if role == "user":
            pydantic_messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            pydantic_messages.append(ModelResponse(parts=[TextPart(content=content)]))
        elif role in ["system", "developer"]:
            pydantic_messages.append(ModelRequest(parts=[SystemPromptPart(content=content)]))

    return pydantic_messages


async def run_agent(
    agent: Agent[UserDependencies],
    user: CustomUser,
    message: str,
    message_history: list[dict] | None = None,
    event_stream_handler: Callable | None = None,
):
    """Run an agent and return the response."""
    deps = UserDependencies(user=user)
    pydantic_messages = convert_openai_to_pydantic_messages(message_history) if message_history else None
    result = await agent.run(
        message, message_history=pydantic_messages, deps=deps, event_stream_handler=event_stream_handler
    )
    return result.output


async def run_agent_streaming(
    agent: Agent[UserDependencies],
    user: CustomUser,
    message: str,
    message_history: list[dict] | None = None,
    event_stream_handler: Callable | None = None,
):
    """Run an agent and stream the response."""
    deps = UserDependencies(user=user)
    pydantic_messages = convert_openai_to_pydantic_messages(message_history) if message_history else None
    async with agent.run_stream(
        message, message_history=pydantic_messages, deps=deps, event_stream_handler=event_stream_handler
    ) as result:
        async for text in result.stream_text(delta=True):
            yield text
