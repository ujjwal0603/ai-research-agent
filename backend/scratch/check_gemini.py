import asyncio
from config.settings import get_settings
import google.generativeai as genai

async def main():
    settings = get_settings()
    genai.configure(api_key=settings.GEMINI_API_KEY)
    print("Available models:")
    for m in genai.list_models():
        if 'embedContent' in m.supported_generation_methods:
            print(m.name)

if __name__ == "__main__":
    asyncio.run(main())
