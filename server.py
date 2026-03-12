from __future__ import annotations

import os
from typing import Any, Literal

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from openai import OpenAI
from openai import OpenAIError
from werkzeug.exceptions import HTTPException

load_dotenv()
app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def json_error(message: str, *, status_code: int = 400, code: str = "bad_request"):
    payload = {"error": {"code": code, "message": message}}
    return jsonify(payload), status_code


@app.errorhandler(HTTPException)
def handle_http_exception(e: HTTPException):
    return json_error(e.description, status_code=e.code or 400, code="http_error")


@app.errorhandler(Exception)
def handle_unexpected_exception(_: Exception):
    return json_error(
        "Unexpected server error. Please try asgain later.",
        status_code=500,
        code="internal_error",
    )


@app.get("/")
def home():
    return "Issa AI Assistant Running"


ChatRole = Literal["consultant", "client"]


def to_openai_role(role: ChatRole) -> Literal["assistant", "user"]:
    if role == "consultant":
        return "assistant"
    return "user"


def validate_request_json(data: Any) -> tuple[str, list[dict[str, str]]]:
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")

    client_sequence = data.get("clientSequence")
    chat_history = data.get("chatHistory")

    if not isinstance(client_sequence, str) or not client_sequence.strip():
        raise ValueError("`clientSequence` must be a non-empty string.")

    if not isinstance(chat_history, list):
        raise ValueError("`chatHistory` must be an array.")

    normalized_history: list[dict[str, str]] = []
    for i, item in enumerate(chat_history):
        if not isinstance(item, dict):
            raise ValueError(f"`chatHistory[{i}]` must be an object.")

        role = item.get("role")
        message = item.get("message")

        if role not in ("consultant", "client"):
            raise ValueError(
                f"`chatHistory[{i}].role` must be 'consultant' or 'client'."
            )
        if not isinstance(message, str) or not message.strip():
            raise ValueError(f"`chatHistory[{i}].message` must be a non-empty string.")

        normalized_history.append(
            {"role": to_openai_role(role), "content": message.strip()}
        )

    return client_sequence.strip(), normalized_history


SYSTEM_VISA_CONSULTANT_PROMPT = (
    "You are a helpful visa consultant helping people apply for the Thailand DTV visa. "
    "Respond in a short, friendly, human conversational style, like a real consultant chatting with a client. "
    "When you explain multiple options, use clear Markdown section titles and short explanations in a clean, Notion-style layout. "
    "For each option, start a new section with a level-3 heading like '### Option Name', followed by 1–3 short sentences. "
    "Use **bold** to highlight key details such as visa names, durations, age thresholds, or important conditions (for example: **5–20 years**, **over 50**, **annual renewal**). "
    "Avoid using numbered lists like '1. 2. 3.' unless the user explicitly asks for a step-by-step list. "
    "Use occasional friendly emojis like 🙂 😊 🇹🇭 when appropriate to keep the tone warm, but do not overuse them. "
    "Wait for the user to specify their availability before scheduling a meeting. "
    "You MUST collect specific pieces of information before booking: 1. Date, 2. Start Time, 3. End Time, 4. Meeting Type (Online/Onsite), and 5. Visa Type. "
    "If the user has not provided ALL of these details, DO NOT ask them using a bulleted list or strict questionnaire format. Instead, ask a single conversational follow-up question to gather the missing info. "
    "For example: 'I can help with that! What date and time frame works best for you, and would you prefer an online or onsite meeting?' "
    "If the user only gives a single time (like '3 PM'), you MUST conversationally ask them 'until what time?' to get the full time frame. "
    "Do NOT guess or hallucinate the start time, end time, or any missing details. "
    "Only when the user has provided the full info for ALL details, ALWAYS output the booking suggestion in exactly this format at the end of your response:\n\n"
    "### Consultation Slot\n"
    "**Date:** [put date here, e.g., 7th next month]\n"
    "**Time:** [put specific time frame here, e.g., 4 PM – 5 PM]\n"
    "**Meeting Type:** [Online or Onsite]\n"
    "**Visa Type:** [put visa name here, e.g., Thailand DTV Visa]\n\n"
    "DO NOT use bullet points, asterisks, hyphen lists, or any other list formatting at the start of the lines in the Consultation Slot block. The lines MUST start exactly with **Date:**, **Time:**, **Meeting Type:**, and **Visa Type:**."
)


def require_api_key():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Ensure it is set in the environment or .env."
        )


def strip_markdown(text: str) -> str:
    # Lightweight post-processing to remove code-style backticks while preserving
    # headings and bold emphasis used for structure.
    return text.replace("```", "").replace("`", "").strip()


def build_generation_messages(
    *, client_message: str, normalized_history: list[dict[str, str]]
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_VISA_CONSULTANT_PROMPT},
        *normalized_history,
        {"role": "user", "content": client_message},
    ]


def generate_consultant_reply(*, client_message: str, normalized_history: list[dict[str, str]]) -> str:
    require_api_key()
    messages = build_generation_messages(
        client_message=client_message, normalized_history=normalized_history
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
    )

    ai_reply = strip_markdown(response.choices[0].message.content or "")
    if not ai_reply:
        raise RuntimeError("The AI returned an empty reply.")
    return ai_reply


@app.post("/generate-reply")
def generate_reply():
    try:
        data = request.get_json(silent=False)
    except Exception:
        return json_error("Invalid JSON body.", status_code=400, code="invalid_json")

    try:
        client_message, normalized_history = validate_request_json(data)
    except ValueError as e:
        return json_error(str(e), status_code=400, code="validation_error")

    try:
        ai_reply = generate_consultant_reply(
            client_message=client_message, normalized_history=normalized_history
        )
    except OpenAIError as e:
        return json_error(
            f"OpenAI API error: {str(e)}",
            status_code=502,
            code="openai_error",
        )
    except RuntimeError as e:
        code = "missing_api_key" if "OPENAI_API_KEY" in str(e) else "ai_error"
        status_code = 500 if code == "missing_api_key" else 502
        return json_error(str(e), status_code=status_code, code=code)

    return jsonify({"aiReply": ai_reply})


@app.get("/chat")
def chat_page():
    return render_template("chat.html")


@app.get("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.get("/api/appointments")
def get_appointments():
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            return jsonify({"error": "Supabase not configured"}), 500
            
        from supabase import create_client, Client
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Fetch the latest 50 appointments, ordered by creation date descending
        response = supabase.table("appointments").select("*").order("created_at", desc=True).limit(50).execute()
        return jsonify(response.data)
    except Exception as e:
        return json_error(str(e), status_code=500, code="supabase_error")


@app.get("/book-appointment")
def book_appointment():
    """
    Redirect users to a pre-filled Google Calendar event to book a meeting
    with Issa Compass.
    """
    from flask import redirect
    from urllib.parse import urlencode
    from datetime import datetime, timedelta

    start = request.args.get("start")
    end = request.args.get("end")
    meeting_type = request.args.get("type", "Online").lower()
    visa_type = request.args.get("visa_type", "Thailand DTV Visa")

    if start and end:
        dates_str = f"{start}/{end}"
        log_start = start
        log_end = end
    else:
        now = datetime.utcnow()
        tmrw = now + timedelta(days=1)
        # Default to tomorrow, 9am - 9:30am UTC
        s_str = tmrw.replace(hour=9, minute=0, second=0).strftime("%Y%m%dT%H%M%SZ")
        e_str = tmrw.replace(hour=9, minute=30, second=0).strftime("%Y%m%dT%H%M%SZ")
        dates_str = f"{s_str}/{e_str}"
        log_start = s_str
        log_end = e_str

    location = "Issa Compass Office, Bangkok" if meeting_type == "onsite" else "Online Meeting"

    # Log the appointment to Supabase
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if supabase_url and supabase_key:
            from supabase import create_client, Client
            supabase: Client = create_client(supabase_url, supabase_key)
            
            # log_start and log_end format: YYYYMMDDTHHMMSSZ
            try:
                start_dt = datetime.strptime(log_start.replace("Z", ""), "%Y%m%dT%H%M%S")
                end_dt = datetime.strptime(log_end.replace("Z", ""), "%Y%m%dT%H%M%S")
                log_start_str = start_dt.strftime("%B %d, %Y, %I:%M %p")
                log_end_str = end_dt.strftime("%B %d, %Y, %I:%M %p")
            except ValueError:
                log_start_str = log_start
                log_end_str = log_end

            supabase.table('appointments').insert({
                "start_time": log_start_str,
                "end_time": log_end_str,
                "type": meeting_type.title(),
                "visa_type": visa_type,
                "location": location,
                "booked_at": datetime.utcnow().isoformat()
            }).execute()
        else:
            print("SUPABASE_URL or SUPABASE_KEY not set. Skipping appointment logging.")
            
    except Exception as e:
        print(f"Error logging appointment to Supabase: {e}")

    # Example meeting details
    event_details = {
        "action": "TEMPLATE",
        "text": f"Issa Compass {visa_type} Consultation",
        "details": f"Consultation about {visa_type}",
        "location": location,
        # Optional default time window (can be adjusted by the user)
        # Format: YYYYMMDDTHHMMSSZ
        "dates": dates_str,
    }

    base_url = "https://calendar.google.com/calendar/render"
    calendar_url = f"{base_url}?{urlencode(event_details)}"

    return redirect(calendar_url)


@app.post("/improve-ai")
def improve_ai():
    try:
        data = request.get_json(silent=False)
    except Exception:
        return json_error("Invalid JSON body.", status_code=400, code="invalid_json")

    try:
        client_message, normalized_history = validate_request_json(data)
    except ValueError as e:
        return json_error(str(e), status_code=400, code="validation_error")

    consultant_reply = None
    if isinstance(data, dict):
        consultant_reply = data.get("consultantReply")

    if not isinstance(consultant_reply, str) or not consultant_reply.strip():
        return json_error(
            "`consultantReply` must be a non-empty string.",
            status_code=400,
            code="validation_error",
        )

    try:
        predicted_reply = generate_consultant_reply(
            client_message=client_message, normalized_history=normalized_history
        )
    except OpenAIError as e:
        return json_error(
            f"OpenAI API error: {str(e)}",
            status_code=502,
            code="openai_error",
        )
    except RuntimeError as e:
        code = "missing_api_key" if "OPENAI_API_KEY" in str(e) else "ai_error"
        status_code = 500 if code == "missing_api_key" else 502
        return json_error(str(e), status_code=status_code, code=code)

    analysis_messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are an expert reviewer of a Thailand DTV visa assistant. "
                "Compare the AI reply to the real consultant reply from the dataset. "
                "Explain (1) what the AI response missed and (2) how the prompt should be improved. "
                "Be concise and concrete. Output plain text only."
            ),
        },
        {
            "role": "user",
            "content": (
                "Client message:\n"
                f"{client_message}\n\n"
                "AI predicted reply:\n"
                f"{predicted_reply}\n\n"
                "Real consultant reply:\n"
                f"{consultant_reply.strip()}\n\n"
                "Please explain:\n"
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
    except OpenAIError as e:
        return json_error(
            f"OpenAI API error: {str(e)}",
            status_code=502,
            code="openai_error",
        )

    analysis = (analysis_response.choices[0].message.content or "").strip()
    if not analysis:
        return json_error(
            "The AI returned an empty analysis.",
            status_code=502,
            code="empty_analysis",
        )

    return jsonify({"predictedReply": predicted_reply, "analysis": analysis})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
    
def home():
    return "Issa AI Assistant Running"


ChatRole = Literal["consultant", "client"]


def to_openai_role(role: ChatRole) -> Literal["assistant", "user"]:
    if role == "consultant":
        return "assistant"
    return "user"


def validate_request_json(data: Any) -> tuple[str, list[dict[str, str]]]:
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")

    client_sequence = data.get("clientSequence")
    chat_history = data.get("chatHistory")

    if not isinstance(client_sequence, str) or not client_sequence.strip():
        raise ValueError("`clientSequence` must be a non-empty string.")

    if not isinstance(chat_history, list):
        raise ValueError("`chatHistory` must be an array.")

    normalized_history: list[dict[str, str]] = []
    for i, item in enumerate(chat_history):
        if not isinstance(item, dict):
            raise ValueError(f"`chatHistory[{i}]` must be an object.")

        role = item.get("role")
        message = item.get("message")

        if role not in ("consultant", "client"):
            raise ValueError(
                f"`chatHistory[{i}].role` must be 'consultant' or 'client'."
            )
        if not isinstance(message, str) or not message.strip():
            raise ValueError(f"`chatHistory[{i}].message` must be a non-empty string.")

        normalized_history.append(
            {"role": to_openai_role(role), "content": message.strip()}
        )

    return client_sequence.strip(), normalized_history


SYSTEM_VISA_CONSULTANT_PROMPT = (
    "You are a helpful visa consultant helping people apply for the Thailand DTV visa. "
    "Respond in a short, friendly, human conversational style, like a real consultant chatting with a client. "
    "When you explain multiple options, use clear Markdown section titles and short explanations in a clean, Notion-style layout. "
    "For each option, start a new section with a level-3 heading like '### Option Name', followed by 1–3 short sentences. "
    "Use **bold** to highlight key details such as visa names, durations, age thresholds, or important conditions (for example: **5–20 years**, **over 50**, **annual renewal**). "
    "Avoid using numbered lists like '1. 2. 3.' unless the user explicitly asks for a step-by-step list. "
    "Use occasional friendly emojis like 🙂 😊 🇹🇭 when appropriate to keep the tone warm, but do not overuse them. "
    "Wait for the user to specify their availability before scheduling a meeting. "
    "You MUST collect specific pieces of information before booking: 1. Date, 2. Start Time, 3. End Time, 4. Meeting Type (Online/Onsite), and 5. Visa Type. "
    "If the user has not provided ALL of these details, DO NOT ask them using a bulleted list or strict questionnaire format. Instead, ask a single conversational follow-up question to gather the missing info. "
    "For example: 'I can help with that! What date and time frame works best for you, and would you prefer an online or onsite meeting?' "
    "If the user only gives a single time (like '3 PM'), you MUST conversationally ask them 'until what time?' to get the full time frame. "
    "Do NOT guess or hallucinate the start time, end time, or any missing details. "
    "Only when the user has provided the full info for ALL details, ALWAYS output the booking suggestion in exactly this format at the end of your response:\n\n"
    "### Consultation Slot\n"
    "**Date:** [put date here, e.g., 7th next month]\n"
    "**Time:** [put specific time frame here, e.g., 4 PM – 5 PM]\n"
    "**Meeting Type:** [Online or Onsite]\n"
    "**Visa Type:** [put visa name here, e.g., Thailand DTV Visa]\n\n"
    "DO NOT use bullet points, asterisks, hyphen lists, or any other list formatting at the start of the lines in the Consultation Slot block. The lines MUST start exactly with **Date:**, **Time:**, **Meeting Type:**, and **Visa Type:**."
)


def require_api_key():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Ensure it is set in the environment or .env."
        )


def strip_markdown(text: str) -> str:
    # Lightweight post-processing to remove code-style backticks while preserving
    # headings and bold emphasis used for structure.
    return text.replace("```", "").replace("`", "").strip()


def build_generation_messages(
    *, client_message: str, normalized_history: list[dict[str, str]]
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_VISA_CONSULTANT_PROMPT},
        *normalized_history,
        {"role": "user", "content": client_message},
    ]


def generate_consultant_reply(*, client_message: str, normalized_history: list[dict[str, str]]) -> str:
    require_api_key()
    messages = build_generation_messages(
        client_message=client_message, normalized_history=normalized_history
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
    )

    ai_reply = strip_markdown(response.choices[0].message.content or "")
    if not ai_reply:
        raise RuntimeError("The AI returned an empty reply.")
    return ai_reply


@app.post("/generate-reply")
def generate_reply():
    try:
        data = request.get_json(silent=False)
    except Exception:
        return json_error("Invalid JSON body.", status_code=400, code="invalid_json")

    try:
        client_message, normalized_history = validate_request_json(data)
    except ValueError as e:
        return json_error(str(e), status_code=400, code="validation_error")

    try:
        ai_reply = generate_consultant_reply(
            client_message=client_message, normalized_history=normalized_history
        )
    except OpenAIError as e:
        return json_error(
            f"OpenAI API error: {str(e)}",
            status_code=502,
            code="openai_error",
        )
    except RuntimeError as e:
        code = "missing_api_key" if "OPENAI_API_KEY" in str(e) else "ai_error"
        status_code = 500 if code == "missing_api_key" else 502
        return json_error(str(e), status_code=status_code, code=code)

    return jsonify({"aiReply": ai_reply})


@app.get("/chat")
def chat_page():
    return render_template("chat.html")


@app.get("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.get("/book-appointment")
def book_appointment():
    """
    Redirect users to a pre-filled Google Calendar event to book a meeting
    with Issa Compass.
    """
    from flask import redirect
    from urllib.parse import urlencode
    from datetime import datetime, timedelta

    start = request.args.get("start")
    end = request.args.get("end")
    meeting_type = request.args.get("type", "Online").lower()
    visa_type = request.args.get("visa_type", "Thailand DTV Visa")

    if start and end:
        dates_str = f"{start}/{end}"
        log_start = start
        log_end = end
    else:
        now = datetime.utcnow()
        tmrw = now + timedelta(days=1)
        # Default to tomorrow, 9am - 9:30am UTC
        s_str = tmrw.replace(hour=9, minute=0, second=0).strftime("%Y%m%dT%H%M%SZ")
        e_str = tmrw.replace(hour=9, minute=30, second=0).strftime("%Y%m%dT%H%M%SZ")
        dates_str = f"{s_str}/{e_str}"
        log_start = s_str
        log_end = e_str

    location = "Issa Compass Office, Bangkok" if meeting_type == "onsite" else "Online Meeting"

    # Log the appointment to a local JSON file array
    try:
        import json
        appointments = []
        filepath = os.path.join(app.root_path, "appointments.json")
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        appointments = data
                except json.JSONDecodeError:
                    pass
        
        # log_start and log_end format: YYYYMMDDTHHMMSSZ
        try:
            start_dt = datetime.strptime(log_start.replace("Z", ""), "%Y%m%dT%H%M%S")
            end_dt = datetime.strptime(log_end.replace("Z", ""), "%Y%m%dT%H%M%S")
            log_start_str = start_dt.strftime("%B %d, %Y, %I:%M %p")
            log_end_str = end_dt.strftime("%B %d, %Y, %I:%M %p")
        except ValueError:
            log_start_str = log_start
            log_end_str = log_end

        appointments.append({
            "start": log_start_str,
            "end": log_end_str,
            "type": meeting_type.title(),
            "visa_type": visa_type,
            "location": location,
            "booked_at": datetime.utcnow().strftime("%B %d, %Y, %I:%M %p UTC")
        })
        
        with open(filepath, "w") as f:
            json.dump(appointments, f, indent=2)
    except Exception as e:
        print(f"Error logging appointment: {e}")

    # Example meeting details
    event_details = {
        "action": "TEMPLATE",
        "text": f"Issa Compass {visa_type} Consultation",
        "details": f"Consultation about {visa_type}",
        "location": location,
        # Optional default time window (can be adjusted by the user)
        # Format: YYYYMMDDTHHMMSSZ
        "dates": dates_str,
    }

    base_url = "https://calendar.google.com/calendar/render"
    calendar_url = f"{base_url}?{urlencode(event_details)}"

    return redirect(calendar_url)


@app.post("/improve-ai")
def improve_ai():
    try:
        data = request.get_json(silent=False)
    except Exception:
        return json_error("Invalid JSON body.", status_code=400, code="invalid_json")

    try:
        client_message, normalized_history = validate_request_json(data)
    except ValueError as e:
        return json_error(str(e), status_code=400, code="validation_error")

    consultant_reply = None
    if isinstance(data, dict):
        consultant_reply = data.get("consultantReply")

    if not isinstance(consultant_reply, str) or not consultant_reply.strip():
        return json_error(
            "`consultantReply` must be a non-empty string.",
            status_code=400,
            code="validation_error",
        )

    try:
        predicted_reply = generate_consultant_reply(
            client_message=client_message, normalized_history=normalized_history
        )
    except OpenAIError as e:
        return json_error(
            f"OpenAI API error: {str(e)}",
            status_code=502,
            code="openai_error",
        )
    except RuntimeError as e:
        code = "missing_api_key" if "OPENAI_API_KEY" in str(e) else "ai_error"
        status_code = 500 if code == "missing_api_key" else 502
        return json_error(str(e), status_code=status_code, code=code)

    analysis_messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are an expert reviewer of a Thailand DTV visa assistant. "
                "Compare the AI reply to the real consultant reply from the dataset. "
                "Explain (1) what the AI response missed and (2) how the prompt should be improved. "
                "Be concise and concrete. Output plain text only."
            ),
        },
        {
            "role": "user",
            "content": (
                "Client message:\n"
                f"{client_message}\n\n"
                "AI predicted reply:\n"
                f"{predicted_reply}\n\n"
                "Real consultant reply:\n"
                f"{consultant_reply.strip()}\n\n"
                "Please explain:\n"
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
    except OpenAIError as e:
        return json_error(
            f"OpenAI API error: {str(e)}",
            status_code=502,
            code="openai_error",
        )

    analysis = (analysis_response.choices[0].message.content or "").strip()
    if not analysis:
        return json_error(
            "The AI returned an empty analysis.",
            status_code=502,
            code="empty_analysis",
        )

    return jsonify({"predictedReply": predicted_reply, "analysis": analysis})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
