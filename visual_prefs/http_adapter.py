"""Optional OpenAI-compatible multimodal Chat Completions transport. Reads one JSON call."""

import json
import os
import sys
from urllib.request import Request, urlopen


def main():
    item = json.load(sys.stdin)
    parts = [{"type": "text", "text": json.dumps(item["context"], ensure_ascii=False)}]
    for img in item["images"]:
        parts.append({"type": "text", "text": f"{img['t']:.3f} s"})
        parts.append(
            {"type": "image_url", "image_url": {"url": f"data:{img['mime']};base64,{img['data']}"}}
        )
    body = {
        "model": os.environ["VLM_MODEL"],
        "messages": [
            {"role": "system", "content": item["instruction"]},
            {"role": "user", "content": parts},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {"Content-Type": "application/json"}
    token = os.getenv("VLM_API_KEY")
    if token:
        headers["Authorization"] = "Bearer " + token
    url = os.environ["VLM_BASE_URL"].rstrip("/") + "/chat/completions"
    with urlopen(
        Request(url, data=json.dumps(body).encode(), headers=headers), timeout=270
    ) as response:
        result = json.load(response)
    print(json.dumps(json.loads(result["choices"][0]["message"]["content"])))


if __name__ == "__main__":
    main()
