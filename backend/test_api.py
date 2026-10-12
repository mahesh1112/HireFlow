from groq import Groq
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from repository root (two levels up from this file)
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
  raise RuntimeError("GROQ_API_KEY not found in .env or environment")

client = Groq(api_key=api_key)
completion = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
      {
        "role": "user",
        "content": "Tell me any joke\n"
      },
      {
        "role": "assistant",
        "content": "Sure, here's a classic one for you:\n\n**Why don’t scientists trust atoms?**\n\nBecause they **make up** everything! 😄"
      },
      {
        "role": "user",
        "content": ""
      }
    ],
    temperature=1,
    max_completion_tokens=8192,
    top_p=1,
    reasoning_effort="medium",
    stream=True,
    stop=None
)

for chunk in completion:
    print(chunk.choices[0].delta.content or "", end="")
