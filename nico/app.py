from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from nico.audio import (
    DefaultAudioOutput,
    DefaultMicrophone,
    DefaultSpeechToText,
    DefaultTextToSpeech,
    DefaultWakeWordDetector,
    VoicePipeline,
)
from nico.bootstrap import AppBootstrap
from nico.brain.claude_provider import ClaudeProvider
from nico.brain.gemini_provider import GeminiProvider
from nico.brain.ollama_provider import OllamaProvider
from nico.brain.openai_provider import OpenAIProvider
from nico.brain.router import ProviderRouter
from nico.config.settings import Settings
from nico.config.prompts import PromptTemplates
from nico.context import ConversationContext
from nico.integrations.google.dispatcher import GoogleServiceDispatcher
from nico.lifecycle import AppLifecycle
from nico.memory.manager import MemoryManager
from nico.orchestrator import IntentOrchestrator
from nico.registry import ServiceRegistry
from nico.tools import build_tool_manager
from nico.tools.manager import ToolManager
from nico.scheduler import TaskScheduler
from nico.notifications import NotificationService
from nico.utils.logging import get_logger, log_event, log_error
from nico.utils.sanitize import sanitize_input


class NicoApp:
    """Application container and coordinator for the NICO assistant.

    Wires together memory, router, tool execution, events, and background services.
    Supports chat, streaming, and tool execution.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.logger = get_logger("nico.app")
        
        # Load prompt templates
        self.prompts = PromptTemplates()

        # Initialize core state and memory
        self.memory_manager = MemoryManager()
        self.context = ConversationContext()

        # Dependency Injection & Lifecycle Setup
        self.bootstrap = AppBootstrap()
        self.registry = self.bootstrap.registry

        # Configure AI Providers & Router (needed early for vision tool)
        providers = {
            "openai": OpenAIProvider(
                api_key=self.settings.openai_api_key,
                model=self.settings.openai_model,
            ),
            "claude": ClaudeProvider(
                api_key=self.settings.anthropic_api_key,
                model=self.settings.anthropic_model,
            ),
            "gemini": GeminiProvider(
                api_key=self.settings.gemini_api_key,
                model=self.settings.gemini_model,
            ),
            "ollama": OllamaProvider(
                base_url=self.settings.ollama_base_url,
                model=self.settings.ollama_model,
            ),
        }
        self.router = ProviderRouter(
            providers, default_provider=self.settings.default_provider
        )

        self.tool_manager = (
            build_tool_manager(router=self.router, app=self) if self.settings.enable_tools else ToolManager()
        )
        self.orchestrator = IntentOrchestrator(self.tool_manager)

        # Google service integrations
        self.google_dispatcher = GoogleServiceDispatcher()

        # Voice / Audio pipeline
        self._voice_pipeline: VoicePipeline | None = None
        self._audio_output: DefaultAudioOutput | None = None
        self._init_voice()

        # Background Services
        self.scheduler = TaskScheduler()
        self.notifications = NotificationService()

        # Register services for Dependency Injection lookup
        self.registry.register("settings", self.settings)
        self.registry.register("tool_manager", self.tool_manager)
        self.registry.register("router", self.router)
        self.registry.register("scheduler", self.scheduler)
        self.registry.register("notifications", self.notifications)
        self.registry.register("memory_manager", self.memory_manager)
        self.registry.register("google_dispatcher", self.google_dispatcher)

        # Wire lifecycle control
        self.lifecycle = AppLifecycle([self.scheduler])

    async def chat(self, message: str) -> str:
        """Process a text turn. Routes provider switches, tools, or plain chat."""
        message = sanitize_input(message)

        # 1. Check for manual provider command switch
        routed = self.router.handle_command(message)
        if routed is not None:
            log_event(self.logger, "provider_selected", provider=routed)
            try:
                from nico.events import ProviderChanged, publish
                await publish(ProviderChanged(to_provider=routed))
            except Exception:
                pass
            return f"Switched provider to {routed}"

        # Start conversation lifecycle event
        try:
            from nico.events import ConversationStarted, publish
            await publish(ConversationStarted())
        except Exception:
            pass

        await self.context.update(message)

        # 2. Check Intent Orchestration
        decision = await self.orchestrator.handle(message)
        if decision["intent"] == "tool":
            tool_name = decision["tool_name"]
            tool_kwargs = decision.get("tool_kwargs") or {}
            
            try:
                # Execute with extracted arguments
                tool_result = await self.tool_manager.execute(tool_name, **tool_kwargs)
                log_event(self.logger, "tool_executed", tool_name=tool_name)
                
                self.memory_manager.add_turn("user", message)
                self.memory_manager.add_turn("assistant", f"Tool result: {tool_result}")
                
                return f"Tool result: {tool_result}"
            except Exception as exc:
                log_error(self.logger, "tool_failed", exc, tool_name=tool_name)
                return f"Error executing tool '{tool_name}': {exc}"
            finally:
                try:
                    from nico.events import ConversationEnded, publish
                    await publish(ConversationEnded())
                except Exception:
                    pass

        # 2b. Hardware intent (shutdown, restart)
        if decision["intent"] == "hardware":
            from nico.hardware.system import SystemController
            action = decision.get("tool_name", "shutdown")
            kwargs = decision.get("tool_kwargs") or {}
            confirmed = kwargs.get("confirm", False)
            controller = SystemController(require_confirmation=not confirmed)
            if action == "shutdown":
                result = controller.shutdown()
            else:
                result = controller.restart()
            return str(result)

        # 2c. Integration intent (email, calendar, home)
        if decision["intent"] == "integration":
            action = decision.get("tool_name", "")
            kwargs = decision.get("tool_kwargs") or {}
            action_map = {"email": "gmail", "calendar": "calendar", "home": "home"}

            mapped = action_map.get(action)
            if mapped:
                kwargs.pop("action", None)
                result = await self.google_dispatcher.handle(mapped, **kwargs)
                self.memory_manager.add_turn("user", message)
                self.memory_manager.add_turn("assistant", f"Integration result: {result}")
                return f"Integration result: {result}"

        # 3. Plain LLM Conversation chat
        self.memory_manager.add_turn("user", message)
        
        try:
            response = await self.router.chat(
                message,
                system_prompt=self.prompts.system_prompt,
            )
            self.memory_manager.add_turn("assistant", response)
            log_event(
                self.logger,
                "conversation_turn",
                topic=self.context.last_topic,
                followups=self.context.followup_count,
                summary=self.context.summary(),
            )
            return response
        except Exception as exc:
            log_error(self.logger, "chat_failed", exc)
            return f"Error: {exc}"
        finally:
            try:
                from nico.events import ConversationEnded, publish
                await publish(ConversationEnded())
            except Exception:
                pass

    async def stream_chat(self, message: str) -> AsyncIterator[str]:
        """Stream conversational tokens with history and system prompts."""
        message = sanitize_input(message)

        # Start conversation lifecycle event
        try:
            from nico.events import ConversationStarted, publish
            await publish(ConversationStarted())
        except Exception:
            pass

        await self.context.update(message)
        self.memory_manager.add_turn("user", message)

        accumulated = []
        try:
            async for token in self.router.stream_chat(
                message,
                system_prompt=self.prompts.system_prompt,
            ):
                accumulated.append(token)
                yield token
            
            full_response = "".join(accumulated)
            self.memory_manager.add_turn("assistant", full_response)
        except Exception as exc:
            log_error(self.logger, "stream_failed", exc)
            yield f"\n[Streaming error: {exc}]"
        finally:
            try:
                from nico.events import ConversationEnded, publish
                await publish(ConversationEnded())
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Voice
    # ------------------------------------------------------------------

    def _init_voice(self) -> None:
        """Initialize voice pipeline if voice is enabled in settings."""
        if not self.settings.enable_voice:
            return

        try:
            mic = DefaultMicrophone(
                device_index=self.settings.audio_input_device,
            )
            stt = DefaultSpeechToText(
                provider=self.settings.stt_provider,
                api_key=self.settings.openai_api_key,
            )
            tts = DefaultTextToSpeech(
                provider=self.settings.tts_provider,
                api_key=self.settings.openai_api_key,
            )
            ww = DefaultWakeWordDetector(
                wake_word=self.settings.wake_word,
            )

            async def _handler(text: str) -> str:
                return await self.chat(text)

            self._voice_pipeline = VoicePipeline(
                microphone=mic,
                speech_to_text=stt,
                text_to_speech=tts,
                wake_word_detector=ww,
                conversation_handler=_handler,
            )

            self._audio_output = DefaultAudioOutput(
                device_index=self.settings.audio_output_device,
            )

            self.registry.register("voice_pipeline", self._voice_pipeline)
            self.registry.register("audio_output", self._audio_output)

            log_event(self.logger, "voice_initialized")
        except Exception as exc:
            log_error(self.logger, "voice_init_failed", exc)

    @property
    def voice_pipeline(self) -> VoicePipeline | None:
        """Return the voice pipeline if voice is enabled, else ``None``."""
        return self._voice_pipeline

    async def voice_chat(self) -> str | None:
        """Run a single voice conversation turn.

        Returns:
            The response text, or ``None`` if voice is not configured.
        """
        if self._voice_pipeline is None:
            log_event(self.logger, "voice_unavailable")
            return None

        result = await self._voice_pipeline.process_audio()

        if result.audio and self._audio_output:
            if self.settings.enable_interruption:
                self._audio_output.play_stream(
                    self._voice_pipeline.text_to_speech.stream_synthesize(result.response)
                )
            else:
                await self._audio_output.play(result.audio)

        return result.response

    # ------------------------------------------------------------------
    # Vision / Image analysis
    # ------------------------------------------------------------------

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str = "Describe this image in detail",
    ) -> str:
        """Analyze an image using the active provider's vision capability."""
        return await self.router.vision(prompt, image_bytes)
