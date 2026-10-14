import os
import json

from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "admitiq-secret-key-change-in-production")


# ============================================================
# GROQ API CONFIGURATION
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is not set.")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# Groq model
MODEL = "openai/gpt-oss-120b"


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def index():

    return render_template("studio.html")


# ============================================================
# PROMPT AND API HELPERS
# ============================================================

def require_client():
    if client is None:
        return jsonify({
            "error": "GROQ_API_KEY is missing. Add it to the .env file to enable AI features."
        }), 503
    return None


def completion(prompt, temperature=0.7, top_p=1.0, max_tokens=1800):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content.strip()


def required_text(data, field, label, max_length=500):
    value = data.get(field, "")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Please enter {label}.")
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"{label.capitalize()} must be {max_length} characters or fewer.")
    return value


def number_setting(data, field, default, minimum, maximum):
    try:
        value = float(data.get(field, default))
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number.") from None
    if not minimum <= value <= maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}.")
    return value


def structured_content_prompt(topic, content_type, tone, audience):
    formats = {
        "story": "Write a compelling short story with a clear beginning, development, and satisfying ending.",
        "poem": "Write an original poem with intentional imagery, rhythm, and line breaks.",
        "social": "Write an engaging social media post with a strong hook and a concise call to action."
    }
    if content_type not in formats:
        raise ValueError("Choose story, poem, or social post.")
    return f"""ROLE:
You are an experienced creative writer and content strategist.

CONTEXT:
Create {content_type} content about this topic: {topic}
Intended audience: {audience}
Desired tone: {tone}

CONSTRAINTS:
- Keep the content original, relevant to the topic, and appropriate for the intended audience.
- Do not include a preamble, explanation, or claims presented as facts without support.

OUTPUT FORMAT:
{formats[content_type]}
Return only the finished content."""


def request_data():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Send the request as JSON.")
    return data


def api_error(error, status=400):
    return jsonify({"error": str(error)}), status


@app.route("/api/generate", methods=["POST"])
def api_generate():
    missing_client = require_client()
    if missing_client:
        return missing_client
    try:
        data = request_data()
        topic = required_text(data, "topic", "a topic")
        content_type = data.get("content_type", "story")
        tone = required_text(data, "tone", "a tone", 100)
        audience = required_text(data, "audience", "an audience", 120)
        temperature = number_setting(data, "temperature", 0.7, 0, 2)
        top_p = number_setting(data, "top_p", 1, 0, 1)
        text = completion(
            structured_content_prompt(topic, content_type, tone, audience),
            temperature,
            top_p
        )
        return jsonify({"content": text})
    except ValueError as error:
        return api_error(error)
    except Exception as error:
        return api_error(error, 502)


@app.route("/api/podcast", methods=["POST"])
def api_podcast():
    missing_client = require_client()
    if missing_client:
        return missing_client
    try:
        data = request_data()
        topic = required_text(data, "topic", "a podcast topic")
        audience = required_text(data, "audience", "an audience", 120)
        prompt = f"""ROLE:
You are an experienced podcast producer and interview researcher.

CONTEXT:
Plan one engaging podcast episode about: {topic}
Target audience: {audience}

CONSTRAINTS:
- Keep the concept focused, specific, and useful to the audience.
- Suggest a realistic guest profile, not a fabricated named person.
- Write open-ended questions that invite detailed answers and avoid repetition.

OUTPUT FORMAT:
Use exactly these headings:
Title
Description
Guest type
Interview questions
Under Interview questions, provide 6 numbered questions."""
        return jsonify({"plan": completion(prompt, temperature=0.65, max_tokens=1200)})
    except ValueError as error:
        return api_error(error)
    except Exception as error:
        return api_error(error, 502)


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    missing_client = require_client()
    if missing_client:
        return missing_client
    try:
        data = request_data()
        text = required_text(data, "text", "text to analyze", 8000)
        prompt = f"""ROLE:
You are a careful text analyst.

CONTEXT:
Analyze the user's text, distinguishing its expressed sentiment from objective truth.

CONSTRAINTS:
- Choose one sentiment label: Positive, Negative, or Neutral.
- Return 5 to 8 meaningful keywords or short phrases that appear in the text.
- Give a one-sentence explanation grounded only in the text.
- Return valid JSON only. Do not wrap it in Markdown.

OUTPUT FORMAT:
{{"sentiment":"Positive|Negative|Neutral","keywords":["keyword"],"summary":"one sentence"}}

TEXT TO ANALYZE:
{text}"""
        result = completion(prompt, temperature=0, top_p=1, max_tokens=500)
        if result.startswith("```"):
            result = result.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        analysis = json.loads(result)
        if analysis.get("sentiment") not in {"Positive", "Negative", "Neutral"}:
            raise ValueError("The analysis response had an invalid sentiment label.")
        if not isinstance(analysis.get("keywords"), list) or not isinstance(analysis.get("summary"), str):
            raise ValueError("The analysis response was incomplete. Please try again.")
        return jsonify({"analysis": analysis})
    except json.JSONDecodeError:
        return api_error("The analysis response could not be read. Please try again.", 502)
    except ValueError as error:
        return api_error(error)
    except Exception as error:
        return api_error(error, 502)


@app.route("/api/compare", methods=["POST"])
def api_compare():
    missing_client = require_client()
    if missing_client:
        return missing_client
    try:
        data = request_data()
        topic = required_text(data, "topic", "a topic")
        content_type = data.get("content_type", "story")
        tone = required_text(data, "tone", "a tone", 100)
        audience = required_text(data, "audience", "an audience", 120)
        parameter = data.get("parameter", "temperature")
        if parameter not in {"temperature", "top_p"}:
            raise ValueError("Choose temperature or Top-P to compare.")
        maximum = 2 if parameter == "temperature" else 1
        first = number_setting(data, "value_a", 0.3, 0, maximum)
        second = number_setting(data, "value_b", 1.2 if parameter == "temperature" else 0.8, 0, maximum)
        if first == second:
            raise ValueError("Choose two different parameter values to compare.")
        prompt = structured_content_prompt(topic, content_type, tone, audience)
        settings_a = {"temperature": 0.7, "top_p": 1.0}
        settings_b = settings_a.copy()
        settings_a[parameter] = first
        settings_b[parameter] = second
        output_a = completion(prompt, **settings_a)
        output_b = completion(prompt, **settings_b)
        return jsonify({
            "parameter": parameter,
            "results": [
                {"value": first, "content": output_a},
                {"value": second, "content": output_b}
            ]
        })
    except ValueError as error:
        return api_error(error)
    except Exception as error:
        return api_error(error, 502)


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1")
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug
    )