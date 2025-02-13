import os
import random
import requests
from functools import wraps
from flask import (
    Flask, request, render_template,
    session, redirect, url_for, send_file, flash
)

# 1) Supabase + custom session
from supabase import create_client, Client
from supabase_session import SupabaseSessionInterface  # your custom file

# 2) Google Generative AI
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# 3) Replicate
import replicate

# --------------------------------------------------------------------------
# Flask + Supabase Setup
# --------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "abc123supersecret")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Please set SUPABASE_URL and SUPABASE_KEY in the environment.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app.session_interface = SupabaseSessionInterface(supabase_client=supabase)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Please log in first.", "warning")
            return redirect(url_for("login_route"))
        return f(*args, **kwargs)
    return decorated_function

# --------------------------------------------------------------------------
# Gemini + Replicate Setup
# --------------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-2.0-flash-exp")

# Use the same safety settings for all LLM calls—allowing explicit sexual descriptions
safety_settings = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

generation_config = {"temperature": 0.5, "top_p": 0.95, "top_k": 40}

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
replicate.client.api_token = REPLICATE_API_TOKEN

# --------------------------------------------------------------------------
# Stage Info
# --------------------------------------------------------------------------
STAGE_INFO = {
    1: {"label": "Strangers", "desc": "They barely know each other."},
    2: {"label": "Casual Acquaintances", "desc": "Superficial chatting, no real depth yet."},
    3: {"label": "Comfortable", "desc": "Sharing moderate personal info, plan small outings."},
    4: {"label": "Close", "desc": "Frequent contact, emotional trust, safe time alone together."},
    5: {"label": "Serious Potential", "desc": "Openly affectionate, discussing future possibilities."},
    6: {"label": "Committed Relationship", "desc": "Life partners with strong devotion, shared long-term goals, can be sexually intimate."}
}
STAGE_REQUIREMENTS = {1: 0, 2: 2, 3: 5, 4: 9, 5: 15, 6: 20}
DEFAULT_STAGE_UNLOCKS = {
    1: "Basic intros, no perks",
    2: "Casual jokes, mild flirting possible,",
    3: "Comfortable enough to ask personal questions",
    4: "Deeper trust, hugging/cuddling possible",
    5: "Serious romance, discussing future plans",
    6: "Fully committed, sharing a life together, will be sexually intimate, NPC can initiate sexual intimacy "
}

GENERATED_IMAGE_PATH = "output.jpg"

# --------------------------------------------------------------------------
# Summarization / Memory (Optional)
# --------------------------------------------------------------------------
def prepare_history():
    log_list = session.get("interaction_log", [])
    if "log_summary" not in session:
        session["log_summary"] = ""
    if len(log_list) > 10:
        old_chunk = log_list[:-5]
        new_chunk = log_list[-5:]
        summary_text = summarize_lines(old_chunk)
        session["log_summary"] += "\n" + summary_text
        session["interaction_log"] = new_chunk

def summarize_lines(lines):
    text_to_summarize = "\n".join(lines)
    summary_prompt = f"""
You are a summarizing assistant.
Summarize the following chat lines into a cohesive memory (300-500 words):

{text_to_summarize}
"""
    try:
        chat = model.start_chat()
        resp = chat.send_message(
            summary_prompt,
            safety_settings=safety_settings,
            generation_config={"temperature": 0.7, "max_output_tokens": 1024}
        )
        return "[Memory Summary]: " + resp.text.strip()
    except Exception as e:
        print("[ERROR] Summarize lines failed:", e)
        return "[Memory Summary Failed. Original lines:]\n" + text_to_summarize

# --------------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------------
def log_message(msg: str):
    logs = session.get("interaction_log", [])
    logs.append(msg)
    session["interaction_log"] = logs

def merge_dd(form, dd_key: str, cust_key: str) -> str:
    dd_val = form.get(dd_key, "").strip()
    cust_val = form.get(cust_key, "").strip()
    return cust_val if cust_val else dd_val

def _save_image(url: str):
    r = requests.get(url)
    with open(GENERATED_IMAGE_PATH, "wb") as f:
        f.write(r.content)

def check_stage_up_down(new_aff: float):
    if "currentStage" not in session:
        session["currentStage"] = 1
    cur_stage = session["currentStage"]
    req = STAGE_REQUIREMENTS[cur_stage]
    if new_aff < req:
        new_stage = 1
        for s, needed in STAGE_REQUIREMENTS.items():
            if new_aff >= needed:
                new_stage = max(new_stage, s)
        session["currentStage"] = new_stage
    else:
        while session["currentStage"] < 6:
            nxt = session["currentStage"] + 1
            if new_aff >= STAGE_REQUIREMENTS[nxt]:
                session["currentStage"] = nxt
            else:
                break
    st = session["currentStage"]
    session["nextStageThreshold"] = STAGE_REQUIREMENTS.get(st + 1, 999)

def validate_age_content(text: str) -> bool:
    age_keywords = ["teen", "teenage", "underage", "minor","child", "kid", "highschool", "high school","18 year","19 year"]
    return any(k in text.lower() for k in age_keywords)

# --------------------------------------------------------------------------
# Build Personalization String
# --------------------------------------------------------------------------
def build_personalization_string() -> str:
    npc_data = (
        f"NPC:\n"
        f"  Name: {session.get('npc_name','?')}\n"
        f"  Gender: {session.get('npc_gender','?')}\n"
        f"  Age: {session.get('npc_age','?')}\n"
        f"  Ethnicity: {session.get('npc_ethnicity','?')}\n"
        f"  BodyType: {session.get('npc_body_type','?')}\n"
        f"  HairColor: {session.get('npc_hair_color','?')}\n"
        f"  HairStyle: {session.get('npc_hair_style','?')}\n"
        f"  Clothing: {session.get('npc_clothing','?')}\n"
        f"  Personality: {session.get('npc_personality','?')}\n"
        f"  Occupation: {session.get('npc_occupation','?')}\n"
        f"  CurrentSituation: {session.get('npc_current_situation','?')}\n"
        f"  Instructions: {session.get('npc_instructions','')}\n"
        f"  Backstory: {session.get('npc_backstory','')}\n"
    )
    env_data = (
        f"ENVIRONMENT:\n"
        f"  Location: {session.get('environment','?')}\n"
        f"  EncounterContext: {session.get('encounter_context','?')}\n"
    )
    user_data = (
        f"USER:\n"
        f"  Name: {session.get('user_name','?')}\n"
        f"  Age: {session.get('user_age','?')}\n"
        f"  Background: {session.get('user_background','?')}\n"
    )
    return user_data + npc_data + env_data

# --------------------------------------------------------------------------
# interpret_npc_state => LLM
# --------------------------------------------------------------------------
def interpret_npc_state(affection: float, trust: float, npc_mood: str,
                        current_stage: int, last_user_action: str, full_history: str = "") -> str:
    """
    Produces exactly 3 lines each turn:
      1) AFFECT_CHANGE_FINAL: ...
      2) NARRATION: ...
      3) IMAGE_PROMPT: ...
    """
    prepare_history()
    memory_summary = session.get("log_summary", "")
    recent_lines = session.get("interaction_log", [])
    combined_history = memory_summary + "\n" + "\n".join(recent_lines)

    if not last_user_action.strip():
        last_user_action = "OOC: Continue the scene"

    stage_label = STAGE_INFO.get(current_stage, {}).get("label", "Unknown")
    stage_desc = STAGE_INFO.get(current_stage, {}).get("desc", "No desc")
    personalization = build_personalization_string()

    system_instructions = f"""
You are a third-person descriptive erotic romance novel narrator.

CRITICAL AGE RESTRICTION:
- All characters must be explicitly adults over 20 years old.

SPECIAL INSTRUCTIONS:
1) If the user's message starts with "OOC", treat everything after it as a direct instruction for how you shape the next story beat or NPC response.
2) The story must remain consenting, adult-only content, with no minors.

For each user action, produce exactly 3 lines (no extra lines):
Line 1 => AFFECT_CHANGE_FINAL: ... (net affection shift between -2.0 and +2.0)
Line 2 => NARRATION: ... (200-300 words describing the NPC's reaction, setting, dialogue, and actions)
Line 3 => IMAGE_PROMPT: a short single-line describing the NPC's appearance (age, gender, ethnicity, body type, hair color, hair style, clothing) plus ephemeral scene details.

Relationship Stage={current_stage} ({stage_label}) => {stage_desc}
Stats: Affection={affection}, Trust={trust}, Mood={npc_mood}

Background (do not contradict):
{personalization}
"""

    user_text = f"USER ACTION: {last_user_action}\nPREVIOUS_LOG:\n{combined_history}"
    max_retries = 2
    for attempt in range(max_retries):
        try:
            resp = model.generate_content(
                f"{system_instructions}\n\n{user_text}",
                generation_config=generation_config,
                safety_settings=safety_settings,
            )
            if resp and resp.text.strip():
                return resp.text.strip()
            else:
                log_message(f"[SYSTEM] LLM returned empty text on attempt {attempt+1}")
        except Exception as e:
            log_message(f"[SYSTEM] Generation attempt {attempt+1} error: {str(e)}")
    return """AFFECT_CHANGE_FINAL: 0
NARRATION: [System: no valid response from LLM, please try again]
IMAGE_PROMPT: (fallback)
"""

# --------------------------------------------------------------------------
# A second function => short single-line prompt
# --------------------------------------------------------------------------
def generate_image_prompt_from_interpret_input() -> str:
    prepare_history()
    memory_summary = session.get("log_summary", "")
    recent_lines = session.get("interaction_log", [])
    combined_history = memory_summary + "\n" + "\n".join(recent_lines)
    personalization = build_personalization_string()

    system_instructions = f"""
You are an assistant specialized in generating short image prompts for an AI image generation system.
Use the following context to produce a single-line prompt describing the NPC's key visual traits (age, gender, ethnicity, body type, hair color, hair style, clothing)
plus any ephemeral scene details (like sweaty from running, hair messed by wind, etc.).
Output only one line, no extra commentary.

CONTEXT:
{personalization}
RECENT_LOG:
{combined_history}
"""
    try:
        resp = model.generate_content(
            system_instructions,
            generation_config={"temperature": 0.5, "max_output_tokens": 100},
            safety_settings=safety_settings
        )
        if resp and resp.text.strip():
            return resp.text.strip()
        else:
            return "Short image prompt not available."
    except Exception as e:
        log_message(f"[SYSTEM] generate_image_prompt_from_interpret_input() error: {str(e)}")
        return "Short image prompt not available."

# --------------------------------------------------------------------------
# Two replicate-based image generation functions
# --------------------------------------------------------------------------
def generate_flux_image_safely(prompt: str, seed: int = None) -> str:
    """
    Model #1 => flux-schnell
    """
    final_prompt = f"Portrait photo, {prompt}"
    replicate_input = {
        "prompt": final_prompt,
        "raw": True,
        "safety_tolerance": 6,
        "disable_safety_checker": True,
        "output_quality": 100
    }
    if seed:
        replicate_input["seed"] = seed
    print(f"[DEBUG] replicate => FLUX prompt={final_prompt}, seed={seed}")
    result = replicate.run("black-forest-labs/flux-schnell", input=replicate_input)
    if isinstance(result, list) and result:
        return str(result[-1])
    elif isinstance(result, str):
        return result
    else:
        return None

def generate_urpm_image_safely(prompt: str, seed: int = None) -> str:
    """
    Model #2 => URPM
    Using 'ductridev/uber-realistic-porn-merge-urpm-1:1cca487c3bfe167e987fc3639477cf2cf617747cd38772421241b04d27a113a8'
    with your negative prompt, etc.
    """
    # URPM negative prompt from your snippet
    negative_prompt = ("pubic hair not visible, animal ears, large breasts, large boobs, text, logo, "
        "((big hands, un-detailed skin, semi-realistic, cgi, 3d, render, sketch, cartoon, drawing, anime)), "
        "((ugly mouth, ugly eyes, missing teeth, crooked teeth, close up, cropped, out of frame)), "
        "worst quality, low quality, jpeg artifacts, ugly, duplicate, morbid, mutilated, extra fingers, "
        "mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, blurry, dehydrated, "
        "bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, "
        "missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers, long neck,"
        "(more than two arm per body:1.5), (more than two leg per body:1.5), "
        "(more than five fingers on one hand:1.5), multi arms, multi legs, bad arm anatomy, bad leg anatomy, "
        "bad hand anatomy, bad finger anatomy, bad detailed background, unclear architectural outline, "
        "non-linear background, elf-ears, hair crosses the screen border, obesity, fat, lowres, worst quality, "
        "low quality, blurry, mutated hands and fingers, disfigured, fused, cloned, duplicate, artist name, "
        "giantess, odd eyes, long fingers, long neck, watermarked"
    )

    replicate_input = {
        "model": "ductridev/uber-realistic-porn-merge-urpm",
        "width": 512,
        "height": 512,
        "cfg_scale": 7,
        "scheduler": "DPM++ 2M Karras",
        "negative_prompt": negative_prompt,
        "num_inference_steps": 55,
        "prompt": prompt
    }
    # If you want to set seed => might need to check if the model supports it
    # Some models may or may not support a 'seed' parameter
    # We'll just store it for reference:
    if seed:
        replicate_input["seed"] = seed

    print(f"[DEBUG] replicate => URPM prompt={prompt}, seed={seed}")
    # run with the full name of the URPM model + the revision:
    result = replicate.run(
        "ductridev/uber-realistic-porn-merge-urpm-1:1cca487c3bfe167e987fc3639477cf2cf617747cd38772421241b04d27a113a8",
        input=replicate_input
    )
    if isinstance(result, list) and result:
        return str(result[-1])
    elif isinstance(result, str):
        return result
    else:
        return None

# --------------------------------------------------------------------------
# A single function to handle which model to use => 'flux' or 'urpm'
# --------------------------------------------------------------------------
def handle_image_generation_from_prompt(prompt_text: str, force_new_seed: bool = False, model_type: str = "flux"):
    if session.get("image_generated_this_turn", False):
        log_message("[SYSTEM] Attempted second image generation this turn, blocked.")
        return None

    existing_seed = session.get("scene_image_seed")
    if not force_new_seed and existing_seed:
        seed_used = existing_seed
        log_message(f"SYSTEM: Re-using old seed => {seed_used}")
    else:
        seed_used = random.randint(100000, 999999)
        log_message(f"SYSTEM: new seed => {seed_used}")

    # Depending on model_type, call flux or urpm
    if model_type == "urpm":
        url = generate_urpm_image_safely(prompt_text, seed=seed_used)
    else:
        # default => flux
        url = generate_flux_image_safely(prompt_text, seed=seed_used)

    if not url:
        log_message("[SYSTEM] Replicate returned invalid URL or error.")
        return None

    _save_image(url)
    session["scene_image_prompt"] = prompt_text
    session["scene_image_url"] = url
    session["scene_image_seed"] = seed_used
    session["image_generated_this_turn"] = True

    log_message(f"Scene Image Prompt used for generation => {prompt_text}")
    log_message(f"Image seed = {seed_used}, model_type={model_type}")
    return url

# --------------------------------------------------------------------------
# NPC Info Update
# --------------------------------------------------------------------------
def update_npc_info(form):
    npc_fields = [
        "npc_name", "npc_gender", "npc_age", "npc_ethnicity", "npc_body_type",
        "npc_hair_color", "npc_hair_style", "npc_personality", "npc_clothing",
        "npc_occupation", "npc_current_situation"
    ]
    for key in npc_fields:
        session[key] = merge_dd(form, key, key + "_custom")
    session["npc_backstory"] = form.get("npc_backstory", "").strip()
    session["environment"] = merge_dd(form, "environment", "environment_custom")
    session["encounter_context"] = merge_dd(form, "encounter_context", "encounter_context_custom")

# --------------------------------------------------------------------------
# DROPDOWNS
# (Same as your existing lists, omitted for brevity)
# --------------------------------------------------------------------------
USER_NAME_OPTIONS = [...]
NPC_NAME_OPTIONS = [...]
HAIR_STYLE_OPTIONS = [...]
BODY_TYPE_OPTIONS = [...]
CLOTHING_OPTIONS = [...]
ETHNICITY_OPTIONS = [...]
NPC_PERSONALITY_OPTIONS = [...]
HAIR_COLOR_OPTIONS = [...]
CURRENT_SITUATION_OPTIONS = [...]
ENVIRONMENT_OPTIONS = [...]
ENCOUNTER_CONTEXT_OPTIONS = [...]

# --------------------------------------------------------------------------
# Routes: landing, about, login, register, logout, continue, restart, personalize, mid_game_personalize
# (same as before)
# --------------------------------------------------------------------------

@app.route("/")
def main_home():
    return render_template("home.html", title="Destined Encounters")

@app.route("/about")
def about():
    return render_template("about.html", title="About/Help")

@app.route("/login", methods=["GET","POST"])
def login_route():
    # ...
    return render_template("login.html", title="Login")

@app.route("/register", methods=["GET","POST"])
def register_route():
    # ...
    return render_template("register.html", title="Register")

@app.route("/logout")
def logout_route():
    # ...
    return redirect(url_for("main_home"))

@app.route("/continue")
@login_required
def continue_session():
    # ...
    return redirect(url_for("interaction"))

@app.route("/restart")
@login_required
def restart():
    # ...
    return redirect(url_for("personalize"))

@app.route("/personalize", methods=["GET","POST"])
@login_required
def personalize():
    # ...
    return render_template("personalize.html", ...)

@app.route("/mid_game_personalize", methods=["GET","POST"])
@login_required
def mid_game_personalize():
    # ...
    return render_template("mid_game_personalize.html", ...)

# --------------------------------------------------------------------------
# Interaction => user can pick model type
# --------------------------------------------------------------------------
@app.route("/interaction", methods=["GET","POST"])
@login_required
def interaction():
    if request.method == "GET":
        # ...
        return render_template("interaction.html", ...)

    else:
        if "submit_action" in request.form:
            # LLM call => 3 lines
            # ...
            return redirect(url_for("interaction"))

        elif "update_npc" in request.form:
            # ...
            return redirect(url_for("interaction"))

        elif "update_affection" in request.form:
            # ...
            return redirect(url_for("interaction"))

        elif "update_stage_unlocks" in request.form:
            # ...
            return redirect(url_for("interaction"))

        elif "generate_prompt" in request.form:
            # short single-line prompt
            prompt = generate_image_prompt_from_interpret_input()
            session["scene_image_prompt"] = prompt
            log_message(f"Generated image prompt: {prompt}")
            flash("Short image prompt generated from current context. You can now edit it if needed.", "info")
            return redirect(url_for("interaction"))

        elif "generate_image" in request.form:
            # user can pick model from a form field "model_type" = "flux" or "urpm"
            user_supplied_prompt = request.form.get("scene_image_prompt", "").strip()
            if not user_supplied_prompt:
                flash("No image prompt provided.", "danger")
                return redirect(url_for("interaction"))

            chosen_model = request.form.get("model_type", "flux")  # default to "flux"
            handle_image_generation_from_prompt(user_supplied_prompt, force_new_seed=False, model_type=chosen_model)
            flash(f"Image generated successfully using model => {chosen_model}.", "success")
            return redirect(url_for("interaction"))

        elif "new_seed" in request.form:
            # same logic => user can pick "model_type"
            user_supplied_prompt = request.form.get("scene_image_prompt", "").strip()
            if not user_supplied_prompt:
                flash("No image prompt provided.", "danger")
                return redirect(url_for("interaction"))

            chosen_model = request.form.get("model_type", "flux")
            handle_image_generation_from_prompt(user_supplied_prompt, force_new_seed=True, model_type=chosen_model)
            flash(f"New image generated with a new seed using model => {chosen_model}.", "success")
            return redirect(url_for("interaction"))

        else:
            return "Invalid submission in /interaction", 400

# --------------------------------------------------------------------------
# View Image
# --------------------------------------------------------------------------
@app.route("/view_image")
@login_required
def view_image():
    return send_file(GENERATED_IMAGE_PATH, mimetype="image/jpeg")

# --------------------------------------------------------------------------
# Full Story, Erotica, Stage Unlocks
# --------------------------------------------------------------------------
@app.route("/full_story")
@login_required
def full_story():
    # ...
    return render_template("full_story.html", ...)

@app.route("/continue_erotica", methods=["POST"])
@login_required
def continue_erotica():
    # ...
    return render_template("erotica_story.html", erotica_text=full_text, title="Generated Erotica")

@app.route("/generate_erotica", methods=["POST"])
@login_required
def generate_erotica():
    # ...
    return render_template("erotica_story.html", erotica_text=erotica_text, title="Generated Erotica")

@app.route("/stage_unlocks", methods=["GET","POST"])
@login_required
def stage_unlocks():
    # ...
    return render_template("stage_unlocks.html", ...)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)