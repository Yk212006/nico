import asyncio

from nico.app import NicoApp
from nico.config.settings import Settings
from nico.config_profiles import load_profile


async def main() -> None:
    profile = load_profile("default")
    app = NicoApp(settings=Settings(default_provider=profile["provider"]))
    response = await app.chat("What is the weather in London?")
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
