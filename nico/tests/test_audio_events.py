from nico.events import (
    SpeechStarted,
    SpeechEnded,
    ListeningStarted,
    ListeningEnded,
    VadSpeechDetected,
    VadSilenceDetected,
    InterruptionDetected,
    subscribe,
    unsubscribe,
    clear_all,
)


async def _noop(_event):
    pass


def test_speech_started_event() -> None:
    event = SpeechStarted(text="hello", provider="openai")
    assert event.text == "hello"
    assert event.provider == "openai"


def test_speech_ended_event() -> None:
    event = SpeechEnded(text="hello", duration_ms=500.0)
    assert event.text == "hello"
    assert event.duration_ms == 500.0


def test_listening_started_event() -> None:
    event = ListeningStarted()
    assert isinstance(event, ListeningStarted)


def test_listening_ended_event() -> None:
    event = ListeningEnded(transcript="hello")
    assert event.transcript == "hello"


def test_vad_speech_detected_event() -> None:
    event = VadSpeechDetected(energy=0.8)
    assert event.energy == 0.8


def test_vad_silence_detected_event() -> None:
    event = VadSilenceDetected(silence_duration_ms=1500.0)
    assert event.silence_duration_ms == 1500.0


def test_interruption_detected_event() -> None:
    event = InterruptionDetected()
    assert isinstance(event, InterruptionDetected)


def test_subscribe_and_unsubscribe_audio_events() -> None:
    subscribe(SpeechStarted, _noop)
    unsubscribe(SpeechStarted, _noop)
    clear_all()


def test_all_audio_events_are_nico_events() -> None:
    from nico.events import NicoEvent
    assert issubclass(SpeechStarted, NicoEvent)
    assert issubclass(SpeechEnded, NicoEvent)
    assert issubclass(ListeningStarted, NicoEvent)
    assert issubclass(ListeningEnded, NicoEvent)
    assert issubclass(VadSpeechDetected, NicoEvent)
    assert issubclass(VadSilenceDetected, NicoEvent)
    assert issubclass(InterruptionDetected, NicoEvent)
