import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai_engine.llm.llm_client import LLMClient
from app.core.config.settings import get_settings

async def main():
    s = get_settings()
    print(f"timeout_setting={s.llm_request_timeout_sec}s  provider={s.llm_provider}  gemini_key_set={bool(s.gemini_api_key)}")

    c = LLMClient()
    print(f"llm_initialized={bool(c.llm)}")

    prompt = (
        'Generate exactly 2 Course Outcomes for "Data Structures" course.\n'
        'Return ONLY JSON array:\n'
        '[\n'
        '  {"code":"CO1","statement":"Students will be able to recall ...","bloom_level":"remember","description":"test"},\n'
        '  {"code":"CO2","statement":"Students will be able to implement ...","bloom_level":"apply","description":"test"}\n'
        ']\n'
    )

    print("Calling LLM...")
    try:
        result = await asyncio.wait_for(
            c.generate_completion(prompt),
            timeout=90.0
        )
        print(f"SUCCESS  raw_len={len(result) if result else 0}")
        if result:
            print(result[:500])
    except asyncio.TimeoutError:
        print("OUTER_TIMEOUT after 90s")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
