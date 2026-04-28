import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

openai_client = None


def get_openai_client():
    global openai_client
    if openai_client is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY is not set in .env")
        openai_client = OpenAI(api_key=key)
    return openai_client


def get_file_suggestions(lines):
    log_text = "".join(lines)
    client = get_openai_client()

    system_prompt = (
        "You are my file cache prediction assistant. "
        "Given a list of some of my file operations, predict which file paths "
        "are most likely to be accessed again soon and should be pre cached. "
        "Please just only reply with only a newline separated list of absolute POSIX file paths."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Recent I/O operations:\n{log_text}"},
        ],
        temperature=0.2,
    )

    raw = response.choices[0].message.content or ""
    paths = [line.strip() for line in raw.splitlines() if line.strip().startswith("/")]
    return paths
