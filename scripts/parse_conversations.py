import json
import os

from dotenv import load_dotenv
from openai import OpenAI

with open("conversations.json", "r") as f:
    data = json.load(f)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

training_examples = []

for convo in data:
    messages = convo["conversation"]
    history = []

    for i in range(len(messages) - 1):

        current = messages[i]
        next_msg = messages[i+1]

        if current["direction"] == "in" and next_msg["direction"] == "out":

            example = {
                "clientSequence": current["text"],
                "chatHistory": history.copy(),
                "consultantReply": next_msg["text"]
            }

            training_examples.append(example)

        role = "client" if current["direction"] == "in" else "consultant"

        history.append({
            "role": role,
            "message": current["text"]
        })

SYSTEM_PROMPT = (
    "You are a helpful visa consultant helping people apply for the Thailand DTV visa. "
    "Respond in a friendly, human conversational style similar to the consultant replies in the dataset."
)

ANALYSIS_SYSTEM_PROMPT = (
    "You are an expert reviewer of AI assistant responses for Thailand DTV visa consultations. "
    "Compare the AI reply to the real consultant reply from the dataset. "
    "Explain what the AI response missed and how the prompt should be improved. "
    "Be concrete and concise."
)

for idx, ex in enumerate(training_examples[:3]):
    # Build OpenAI API messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    # Add chat history (role mapping)
    for item in ex["chatHistory"]:
        role = "user" if item["role"] == "client" else "assistant"
        messages.append({
            "role": role,
            "content": item["message"]
        })
    # Add current client message
    messages.append({
        "role": "user",
        "content": ex["clientSequence"]
    })

    # Call OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
        )
        ai_reply = (response.choices[0].message.content or "").strip()
    except Exception as e:
        ai_reply = f"[OpenAI API error: {e}]"

    real_reply = (ex.get("consultantReply") or "").strip()

    analysis = ""
    analysis_messages = [
        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Client message:\n"
                f"{ex['clientSequence']}\n\n"
                "Chat history (JSON):\n"
                f"{json.dumps(ex['chatHistory'], ensure_ascii=False, indent=2)}\n\n"
                "REAL CONSULTANT REPLY:\n"
                f"{real_reply}\n\n"
                "AI REPLY:\n"
                f"{ai_reply}\n\n"
                "Please answer with:\n"
                "- What the AI response missed\n"
                "- How the prompt should be improved"
            ),
        },
    ]

    try:
        analysis_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=analysis_messages,
            temperature=0.2,
        )
        analysis = (analysis_response.choices[0].message.content or "").strip()
    except Exception as e:
        analysis = f"[OpenAI API error: {e}]"

    # Print the formatted output
    print("CLIENT:")
    print(ex["clientSequence"])
    print()
    print("CHAT HISTORY:")
    print(json.dumps(ex["chatHistory"], ensure_ascii=False, indent=2))
    print()
    print("REAL CONSULTANT REPLY")
    print(real_reply)
    print()
    print("AI REPLY:")
    print(ai_reply)
    print()
    print("ANALYSIS")
    print(analysis)
    print()