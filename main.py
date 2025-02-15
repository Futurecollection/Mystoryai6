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
# Utility Functions
# --------------------------------------------------------------------------
def log_message(msg: str):
    logs = session.get("interaction_log", [])
    logs.append(msg)
    session["interaction_log"] = logs

def merge_dd(form, dd_key: str, cust_key: str) -> str:
    dd_val = form.get(dd_key, "").strip()
    cust_val = form.get(cust_key, "").strip()
    return cust_val if cust_val else dd_val

def _save_image(result):
    """
    Saves the output to output.jpg. Handles file-like objects, dicts with "output", lists, or strings.
    """
    if isinstance(result, dict) and "output" in result:
        final_url = result["output"]
        print("[DEBUG] _save_image => Received dict with output:", final_url)
        try:
            r = requests.get(final_url)
            with open(GENERATED_IMAGE_PATH, "wb") as f:
                f.write(r.content)
        except Exception as e:
            print("[ERROR] _save_image => Error downloading from output key:", e)
        return

    if hasattr(result, "read"):
        print("[DEBUG] _save_image => File-like object received.")
        with open(GENERATED_IMAGE_PATH, "wb") as f:
            f.write(result.read())
        return

    if isinstance(result, list) and result:
        final_item = result[-1]
        if isinstance(final_item, str):
            print("[DEBUG] _save_image => Received list; using final item:", final_item)
            try:
                r = requests.get(final_item)
                with open(GENERATED_IMAGE_PATH, "wb") as f:
                    f.write(r.content)
                return
            except Exception as e:
                print("[ERROR] _save_image => Error downloading from list item:", e)
                return
        else:
            print("[ERROR] _save_image => List item is not a string:", final_item)
            return

    if isinstance(result, str):
        print("[DEBUG] _save_image => Received string:", result)
        try:
            r = requests.get(result)
            with open(GENERATED_IMAGE_PATH, "wb") as f:
                f.write(r.content)
        except Exception as e:
            print("[ERROR] _save_image => Error downloading from string:", e)
        return

    print("[ERROR] _save_image => Unknown result type:", type(result))

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
    age_keywords = [
        "teen", "teenage", "underage", "minor", "child",
        "kid", "highschool", "high school", "18 year", "19 year"
    ]
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
1) If the user's message starts with "OOC", treat everything after it as direct instructions.
2) The story must remain consenting and adult-only.

For each user action, produce exactly 3 lines (no extra lines):
Line 1 => AFFECT_CHANGE_FINAL: ... (net affection shift between -2.0 and +2.0)
Line 2 => NARRATION: ... (200-300 words describing the NPC's reaction, setting, dialogue, and actions)
Line 3 => IMAGE_PROMPT: ... (a customized, structured image prompt)

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
# generate_image_prompt_from_interpret_input => LLM
# --------------------------------------------------------------------------
def generate_image_prompt_from_interpret_input() -> str:
    prepare_history()
    memory_summary = session.get("log_summary", "")
    recent_lines = session.get("interaction_log", [])
    combined_history = memory_summary + "\n" + "\n".join(recent_lines)
    personalization = build_personalization_string()

    system_instructions = f"""
You are an assistant specialized in generating concise, ultrarealistic image prompts for an AI image generator.
Use the context below (the NPC's personal details and recent story) to produce a single-sentence image prompt referencing
the NPC's physical appearance, environment, and any relevant current actions or mood.

CONTEXT:
{personalization}

RECENT_LOG:
{combined_history}

Output only the final prompt (1-2 sentences, no extra commentary).
"""
    try:
        chat = model.start_chat()
        resp = chat.send_message(
            system_instructions,
            generation_config={"temperature": 0.3, "max_output_tokens": 100},
            safety_settings=safety_settings
        )
        if resp and resp.text.strip():
            return resp.text.strip()
        else:
            return "Ultrarealistic photo of the NPC in the current environment."
    except Exception as e:
        log_message(f"[SYSTEM] generate_image_prompt_from_interpret_input error: {str(e)}")
        return "Ultrarealistic photo of the NPC in the current environment."

# --------------------------------------------------------------------------
# Replicate Model Functions
# --------------------------------------------------------------------------
def generate_flux_image_safely(prompt: str, seed: int = None) -> object:
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
    try:
        result = replicate.run("black-forest-labs/flux-schnell", replicate_input)
        # Return in consistent format for _save_image
        if result:
            return {"output": result[0] if isinstance(result, list) else result}
        return None
    except Exception as e:
        print(f"[ERROR] Flux call failed: {e}")
        return None

def generate_pony_sdxl_image_safely(prompt: str, seed: int = None, steps: int = 60) -> object:
    auto_positive = "score_9, score_8_up, score_7_up, (masterpiece, best quality, ultra-detailed, realistic)"
    final_prompt = f"{auto_positive}, {prompt}"
    replicate_input = {
        "vae": "sdxl-vae-fp16-fix",
        "seed": -1,
        "model": "ponyRealism21.safetensors",
        "steps": steps,
        "width": 1184,
        "height": 864,
        "prompt": final_prompt,
        "cfg_scale": 5,
        "scheduler": "DPM++ 2M SDE Karras",
        "batch_size": 1,
        "guidance_rescale": 0.7,
        "prepend_preprompt": True,
        "negative_prompt": (
            "low-res, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, "
            "worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, artist name, "
            "(deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, "
            "floating limbs, (mutated hands and fingers:1.4), disconnected limbs, mutation, mutated, ugly, disgusting, blurry, amputation"
        ),
        "clip_last_layer": -2
    }
    if seed:
        replicate_input["seed"] = seed
    print(f"[DEBUG] replicate => PONY-SDXL prompt={final_prompt}, seed={seed}, steps={steps}")
    try:
        result = replicate.run(
            "charlesmccarthy/pony-sdxl:b070dedae81324788c3c933a5d9e1270093dc74636214b9815dae044b4b3a58a",
            replicate_input
        )
        # Return in consistent format for _save_image
        if result:
            return {"output": result[0] if isinstance(result, list) else result}
        return None
    except Exception as e:
        print("[ERROR] Pony-SDXL call failed:", e)
        return None

def generate_cyberrealisticpony_image_safely(prompt: str, seed: int = None, scheduler: str = "K_EULER", steps: int = 50) -> object:
    auto_positive = "score_9, score_8_up, score_7_up, (masterpiece, best quality, ultra-detailed, realistic)"
    final_prompt = f"{auto_positive}, {prompt}"
    negative_prompt_text = (
        "score_6, score_5, score_4, simplified, abstract, unrealistic, impressionistic, "
        "low resolution, lowres, bad anatomy, bad hands, missing fingers, worst quality, "
        "low quality, normal quality, cartoon, anime, drawing, sketch, illustration, "
        "artificial, poor quality"
    )
    replicate_input = {
        "width": 1024,
        "height": 1024,
        "prompt": final_prompt,
        "negative_prompt": negative_prompt_text,
        "scheduler": scheduler,   # either "K_EULER" or "KarrasDPM"
        "num_inference_steps": steps,
        "guidance_scale": 5,
        "clip_skip": 2,
        "refine": "no_refiner",
        "lora_scale": 0.6,
        "num_outputs": 1,
        "apply_watermark": True,
        "high_noise_frac": 0.8,
        "prompt_strength": 0.8
    }
    if seed:
        replicate_input["seed"] = seed
    print(f"[DEBUG] replicate => CyberRealisticPony prompt={final_prompt}, seed={seed}, scheduler={scheduler}, steps={steps}")
    try:
        result = replicate.run(
            "charlesmccarthy/cyberrealisticpony_v40:7dc5ff926d5948d6d85869ce8016e8f1ebe72377f7f67aecb3c9d9b9cfacf665",
            replicate_input
        )
        # Return in consistent format for _save_image
        if result:
            return {"output": result[0] if isinstance(result, list) else result}
        return None
    except Exception as e:
        print("[ERROR] CyberRealisticPony call failed:", e)
        return None

def generate_realistic_vision_image_safely(
    prompt: str,
    seed: int = 0,
    steps: int = 20,
    width: int = 512,
    height: int = 728,
    guidance: float = 5.0,
    scheduler: str = "EulerA"
) -> object:
    negative_prompt_text = (
        "(deformed iris, deformed pupils, semi-realistic, cgi, 3d, render, sketch, cartoon, drawing, anime:1.4), "
        "text, close up, cropped, out of frame, worst quality, low quality, jpeg artifacts, ugly, duplicate, morbid, "
        "mutilated, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, blurry, "
        "dehydrated, bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, "
        "missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers, long neck"
    )
    replicate_input = {
        "seed": seed,
        "steps": steps,
        "width": width,
        "height": height,
        "prompt": prompt,
        "guidance": guidance,
        "scheduler": scheduler,
        "negative_prompt": negative_prompt_text
    }
    print(f"[DEBUG] replicate => RealisticVision prompt={prompt}, seed={seed}, steps={steps}, scheduler={scheduler}, width={width}, height={height}")
    try:
        result = replicate.run(
            "lucataco/realistic-vision-v5.1:2c8e954decbf70b7607a4414e5785ef9e4de4b8c51d50fb8b8b349160e0ef6bb",
            replicate_input
        )
        # Check if result is a dict with an "output" key.
        # Return full result object to let _save_image handle it
        if result:
            return {"output": result[0] if isinstance(result, list) else result}
        return None
    except Exception as e:
        print(f"[ERROR] RealisticVision call failed: {e}")
        return None

# --------------------------------------------------------------------------
# handle_image_generation_from_prompt => multi-model selection
# --------------------------------------------------------------------------
def handle_image_generation_from_prompt(prompt_text: str, force_new_seed: bool = False,
                                        model_type: str = "flux", scheduler: str = None, steps: int = None):
    existing_seed = session.get("scene_image_seed")
    if not force_new_seed and existing_seed:
        seed_used = existing_seed
        log_message(f"SYSTEM: Re-using old seed => {seed_used}")
    else:
        seed_used = random.randint(100000, 999999)
        log_message(f"SYSTEM: new seed => {seed_used}")

    if model_type == "pony":
        steps = steps if steps is not None else 60
        result = generate_pony_sdxl_image_safely(prompt_text, seed=seed_used, steps=steps)
    elif model_type == "cyberpony":
        steps = steps if steps is not None else 50
        valid_schedulers = ["K_EULER", "KarrasDPM"]
        chosen_sched = scheduler if scheduler in valid_schedulers else "K_EULER"
        result = generate_cyberrealisticpony_image_safely(
            prompt=prompt_text,
            seed=seed_used,
            scheduler=chosen_sched,
            steps=steps
        )
    elif model_type == "realistic":
        steps_final = steps if steps is not None else 20
        valid_schedulers = ["EulerA", "MultistepDPM-Solver"]
        chosen_sched = scheduler if scheduler in valid_schedulers else "EulerA"
        result = generate_realistic_vision_image_safely(
            prompt=prompt_text,
            seed=seed_used,
            steps=steps_final,
            width=512,
            height=728,
            guidance=5.0,
            scheduler=chosen_sched
        )
    else:
        result = generate_flux_image_safely(prompt_text, seed=seed_used)

    if not result:
        log_message("[SYSTEM] replicate returned invalid or empty result.")
        return None

    _save_image(result)

    # Save URL to session after successful save
    session["scene_image_url"] = url_for('view_image')

    session["scene_image_prompt"] = prompt_text
    session["scene_image_seed"] = seed_used

    log_message(f"Scene Image Prompt => {prompt_text}")
    log_message(f"Image seed={seed_used}, model={model_type}, scheduler={scheduler}, steps={steps}")
    return result

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
# Expanded Dropdown Lists
# --------------------------------------------------------------------------
USER_NAME_OPTIONS = [
    "John", "Michael", "David", "Chris", "James", "Alex",
    "Emily", "Olivia", "Sophia", "Emma", "Ava", "Isabella",
    "Liam", "Noah", "Ethan", "Mason", "Lucas", "Logan"
]
NPC_NAME_OPTIONS = [
    "Lucy", "Emily", "Sarah", "Lisa", "Anna", "Mia", "Sophia",
    "Olivia", "Chloe", "Isabella", "Grace", "Lily", "Ella", "Zoe", "Emma",
    "Victoria", "Madison", "Natalie", "Jasmine", "Aurora", "Ruby", "Scarlett",
    "Hazel", "Ivy", "Luna", "Penelope", "Stella"
]
HAIR_STYLE_OPTIONS = [
    "Short", "Medium", "Long", "Bald", "Pixie", "Bob",
    "Curly", "Wavy", "Braided", "Updo", "Ponytail", "Messy bun",
    "Side-swept bangs", "Fishtail braid", "Sleek straight", "Layered",
    "Curls", "Tousled", "Wavy bob", "Half-up half-down"
]
BODY_TYPE_OPTIONS = [
    "Athletic", "Muscular", "Average", "Tall", "Slim",
    "Curvy", "Petite", "Voluptuous", "Fit", "Lithe", "Hourglass",
    "Elegant", "Graceful"
]
CLOTHING_OPTIONS = [
    "Red Dress", "T-shirt & Jeans", "Black Gown", "Green Hoodie",
    "Elegant Evening Gown", "Casual Blouse & Skirt", "Office Suit",
    "Summer dress", "Black mini skirt and white blouse",
    "Leather Jacket and Shorts", "Vintage Outfit",
    "High-waisted trousers with a crop top", "Lace lingerie set",
    "Silk robe", "Intimate chemise", "Bodysuit",
    "Off-shoulder top with skirt", "Corset and thigh-high stockings"
]
ETHNICITY_OPTIONS = [
    "British", "French", "German", "Italian", "Spanish", "Portuguese",
    "Greek", "Dutch", "Swedish", "Norwegian", "Finnish", "Danish",
    "Polish", "Russian", "Ukrainian", "Austrian", "Swiss", "Belgian",
    "Czech", "Slovak", "Hungarian", "Romanian", "Bulgarian", "Serbian",
    "Croatian", "Slovenian", "Bosnian", "Australian", "New Zealander",
    "Maori", "Chinese", "Japanese", "Korean", "Indian", "Pakistani",
    "Bangladeshi", "Indonesian", "Filipino", "Thai", "Vietnamese",
    "Malaysian", "Singaporean", "American (Black)", "American (White)",
    "Hispanic", "Latino", "Middle Eastern", "African", "Other"
]
NPC_PERSONALITY_OPTIONS = [
    "Flirty", "Passionate", "Confident", "Playful", "Gentle",
    "Seductive", "Sensual", "Provocative", "Lascivious", "Romantic",
    "Erotic", "Alluring", "Mysterious", "Intense", "Charming", "Warm",
    "Feminine", "Nurturing"
]
HAIR_COLOR_OPTIONS = [
    "Blonde", "Brunette", "Black", "Red", "Auburn", "Platinum Blonde",
    "Jet Black", "Chestnut", "Strawberry Blonde", "Honey Blonde",
    "Caramel", "Golden"
]
CURRENT_SITUATION_OPTIONS = [
    "Recently Broke Up", "Single & Looking", "On Vacation",
    "Working", "In a Relationship", "Divorced", "Exploring new desires",
    "Feeling liberated"
]
ENVIRONMENT_OPTIONS = [
    "Cafe", "Library", "Gym", "Beach", "Park", "Nightclub", "Bar",
    "Studio", "Loft", "Garden", "Rooftop", "Boutique hotel", "Luxury spa",
    "Chic restaurant"
]
ENCOUNTER_CONTEXT_OPTIONS = [
    "First Date", "Accidental Meeting", "Group Activity", "Work Event",
    "Online Match", "Blind Date", "Unexpected Reunion", "Romantic Getaway",
    "After-Party", "Private Dinner", "Secret Meeting", "Intimate Gathering",
    "Spontaneous Encounter", "Cozy Evening"
]

# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.route("/")
def main_home():
    return render_template("home.html", title="Destined Encounters")

@app.route("/about")
def about():
    return render_template("about.html", title="About/Help")

@app.route("/login", methods=["GET", "POST"])
def login_route():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        if not email or not password:
            flash("Email and password are required", "danger")
            return redirect(url_for("login_route"))
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if not response or not response.user:
                flash("Invalid credentials", "danger")
                return redirect(url_for("login_route"))
            user = response.user
            user_id = user.id
            session.update({
                "logged_in": True,
                "user_id": user_id,
                "user_email": user.email,
                "access_token": response.session.access_token
            })
            flash("Logged in successfully!", "success")
            return redirect(url_for("main_home"))
        except Exception as e:
            flash(f"Login failed: {e}", "danger")
            return redirect(url_for("login_route"))
    return render_template("login.html", title="Login")

@app.route("/register", methods=["GET", "POST"])
def register_route():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        if not email or not password:
            flash("Email + password required", "danger")
            return redirect(url_for("register_route"))
        try:
            response = supabase.auth.sign_up({"email": email, "password": password})
            flash("Registration success! Check your email, then log in.", "success")
            return redirect(url_for("login_route"))
        except Exception as e:
            flash(f"Registration failed: {e}", "danger")
            return redirectreturn redirect(url_for("register_route"))
    return render_template("register.html", title="Register")

@app.route("/logout")
def logout_route():
    for key in ["logged_in", "user_id", "user_email", "access_token"]:
        session.pop(key, None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("main_home"))

@app.route("/continue")
@login_required
def continue_session():
    if session.get("npc_name"):
        flash("Session loaded from in-memory data!", "info")
        return redirect(url_for("interaction"))
    user_id = session.get("user_id")
    if not user_id:
        flash("Error: no user_id found in session.", "danger")
        return redirect(url_for("main_home"))
    try:
        result = supabase.table("flask_sessions").select("*").eq("user_id", user_id).execute()
        rows = result.data
        if not rows:
            flash("No saved session data found. Please start a new game.", "info")
            return redirect(url_for("personalize"))
        row = rows[-1]
        session_data = row.get("data", {})
        for k, v in session_data.items():
            session[k] = v
        flash("Saved session loaded from database!", "success")
        return redirect(url_for("interaction"))
    except Exception as e:
        flash(f"Error loading session: {e}", "danger")
        return redirect(url_for("personalize"))

@app.route("/restart")
@login_required
def restart():
    session.clear()
    session["stage_unlocks"] = dict(DEFAULT_STAGE_UNLOCKS)
    flash("Session restarted (NPC data cleared).", "info")
    return redirect(url_for("personalize"))

@app.route("/personalize", methods=["GET", "POST"])
@login_required
def personalize():
    if request.method == "POST" and "save_personalization" in request.form:
        session["user_name"] = merge_dd(request.form, "user_name", "user_name_custom")
        session["user_age"] = merge_dd(request.form, "user_age", "user_age_custom")
        session["user_background"] = request.form.get("user_background", "").strip()
        update_npc_info(request.form)
        npc_gender = session.get("npc_gender", "").lower()
        if npc_gender == "male":
            session["npc_instructions"] = "(MALE-SPECIFIC INSTRUCTIONS BLOCK)"
        else:
            session["npc_instructions"] = "(FEMALE-SPECIFIC INSTRUCTIONS BLOCK)"
        session["affectionScore"] = 0.0
        session["trustScore"] = 5.0
        session["npcMood"] = "Neutral"
        session["currentStage"] = 1
        session["npcPrivateThoughts"] = "(none)"
        session["npcBehavior"] = "(none)"
        session["nextStageThreshold"] = STAGE_REQUIREMENTS[2]
        session["interaction_log"] = []
        session["scene_image_prompt"] = ""
        session["scene_image_url"] = None
        session["scene_image_seed"] = None
        session["log_summary"] = ""
        flash("Personalization saved. Let’s begin!", "success")
        return redirect(url_for("interaction"))
    else:
        return render_template("personalize.html",
            title="Personalizations",
            user_name_options=USER_NAME_OPTIONS,
            user_age_options=["20", "25", "30", "35", "40", "45"],
            npc_name_options=NPC_NAME_OPTIONS,
            npc_age_options=["20", "25", "30", "35", "40", "45"],
            npc_gender_options=["Female", "Male", "Non-binary", "Other"],
            hair_style_options=HAIR_STYLE_OPTIONS,
            body_type_options=BODY_TYPE_OPTIONS,
            hair_color_options=HAIR_COLOR_OPTIONS,
            npc_personality_options=NPC_PERSONALITY_OPTIONS,
            clothing_options=CLOTHING_OPTIONS,
            occupation_options=["College Student", "Teacher", "Artist", "Doctor", "Chef", "Engineer"],
            current_situation_options=["Recently Broke Up", "Single & Looking", "On Vacation", "Working", "In a Relationship", "Divorced"],
            environment_options=["Cafe", "Library", "Gym", "Beach", "Park"],
            encounter_context_options=["First date", "Accidental meeting", "Group activity", "Work event", "Online Match"],
            ethnicity_options=ETHNICITY_OPTIONS
        )

@app.route("/mid_game_personalize", methods=["GET", "POST"])
@login_required
def mid_game_personalize():
    if request.method == "POST" and "update_npc" in request.form:
        update_npc_info(request.form)
        npc_gender = session.get("npc_gender", "").lower()
        if npc_gender == "male":
            session["npc_instructions"] = "(MALE-SPECIFIC INSTRUCTIONS BLOCK)"
        else:
            session["npc_instructions"] = "(FEMALE-SPECIFIC INSTRUCTIONS BLOCK)"
        log_message("SYSTEM: NPC personalizations updated mid-game.")
        flash("NPC info updated mid-game!", "info")
        return redirect(url_for("interaction"))
    return render_template("mid_game_personalize.html",
        title="Update Settings",
        npc_name_options=NPC_NAME_OPTIONS,
        npc_age_options=["20", "25", "30", "35", "40", "45"],
        npc_gender_options=["Female", "Male", "Non-binary", "Other"],
        hair_style_options=HAIR_STYLE_OPTIONS,
        body_type_options=BODY_TYPE_OPTIONS,
        hair_color_options=HAIR_COLOR_OPTIONS,
        npc_personality_options=NPC_PERSONALITY_OPTIONS,
        clothing_options=CLOTHING_OPTIONS,
        occupation_options=["College Student", "Teacher", "Artist", "Doctor", "Chef", "Engineer"],
        current_situation_options=["Recently Broke Up", "Single & Looking", "On Vacation", "Working", "In a Relationship", "Divorced"],
        environment_options=["Cafe", "Library", "Gym", "Beach", "Park"],
        encounter_context_options=["First date", "Accidental meeting", "Group activity", "Work event", "Online Match"],
        ethnicity_options=ETHNICITY_OPTIONS
    )

@app.route("/interaction", methods=["GET", "POST"])
@login_required
def interaction():
    if request.method == "GET":
        affection = session.get("affectionScore", 0.0)
        trust = session.get("trustScore", 5.0)
        mood = session.get("npcMood", "Neutral")
        cstage = session.get("currentStage", 1)
        st_label = STAGE_INFO[cstage]["label"]
        st_desc = STAGE_INFO[cstage]["desc"]
        nxt_thresh = session.get("nextStageThreshold", 999)
        stage_unlocks = session.get("stage_unlocks", {})
        last_narration = session.get("narrationText", "(No scene yet.)")
        scene_prompt = session.get("scene_image_prompt", "")
        scene_url = session.get("scene_image_url", None)
        seed_used = session.get("scene_image_seed", None)
        interaction_log = session.get("interaction_log", [])

        return render_template("interaction.html",
            title="Interact with NPC",
            affection_score=affection,
            trust_score=trust,
            npc_mood=mood,
            current_stage=cstage,
            stage_label=st_label,
            stage_desc=st_desc,
            next_threshold=nxt_thresh,
            npc_narration=last_narration,
            scene_image_prompt=scene_prompt,
            scene_image_url=scene_url,
            scene_image_seed=seed_used,
            interaction_log=interaction_log,
            stage_unlocks=stage_unlocks,
            npc_name_options=NPC_NAME_OPTIONS,
            npc_age_options=["20", "25", "30", "35", "40", "45"],
            npc_gender_options=["Female", "Male", "Non-binary", "Other"],
            hair_style_options=HAIR_STYLE_OPTIONS,
            body_type_options=BODY_TYPE_OPTIONS,
            hair_color_options=HAIR_COLOR_OPTIONS,
            npc_personality_options=NPC_PERSONALITY_OPTIONS,
            clothing_options=CLOTHING_OPTIONS,
            occupation_options=["College Student", "Teacher", "Artist", "Doctor", "Chef", "Engineer"],
            current_situation_options=["Recently Broke Up", "Single & Looking", "On Vacation", "Working", "In a Relationship", "Divorced"],
            environment_options=["Cafe", "Library", "Gym", "Beach", "Park"],
            encounter_context_options=["First date", "Accidental meeting", "Group activity", "Work event", "Online Match"],
            ethnicity_options=ETHNICITY_OPTIONS
        )
    else:
        if "submit_action" in request.form:
            user_action = request.form.get("user_action", "").strip()
            affection = session.get("affectionScore", 0.0)
            trust = session.get("trustScore", 5.0)
            mood = session.get("npcMood", "Neutral")
            cstage = session.get("currentStage", 1)
            log_message(f"User: {user_action}")

            # Clear previous image URL to avoid stale data
            session["scene_image_url"] = None

            result_text = interpret_npc_state(
                affection=affection,
                trust=trust,
                npc_mood=mood,
                current_stage=cstage,
                last_user_action=user_action
            )

            affect_delta = 0.0
            narration_txt = ""
            image_prompt = ""
            for ln in result_text.split("\n"):
                s = ln.strip()
                if s.startswith("AFFECT_CHANGE_FINAL:"):
                    try:
                        affect_delta = float(s.split(":", 1)[1].strip())
                    except:
                        affect_delta = 0.0
                elif s.startswith("NARRATION:"):
                    narration_txt = s.split(":", 1)[1].strip()
                elif s.startswith("IMAGE_PROMPT:"):
                    image_prompt = s.split(":", 1)[1].strip()

            new_aff = affection + affect_delta
            session["affectionScore"] = new_aff
            check_stage_up_down(new_aff)
            session["narrationText"] = narration_txt
            session["scene_image_prompt"] = image_prompt
            log_message(f"Affect={affect_delta}")
            log_message(f"NARRATION => {narration_txt}")
            return redirect(url_for("interaction"))

        elif "update_npc" in request.form:
            update_npc_info(request.form)
            log_message("SYSTEM: NPC personalizations updated mid-game.")
            return redirect(url_for("interaction"))

        elif "update_affection" in request.form:
            try:
                new_val = float(request.form.get("affection_new", "0.0").strip())
            except:
                new_val = 0.0
            session["affectionScore"] = new_val
            check_stage_up_down(new_val)
            log_message(f"SYSTEM: Affection manually set => {new_val}")
            return redirect(url_for("interaction"))

        elif "update_stage_unlocks" in request.form:
            su = session.get("stage_unlocks", {})
            for i in range(1, 7):
                key = f"stage_unlock_{i}"
                su[i] = request.form.get(key, "").strip()
            session["stage_unlocks"] = su
            log_message("SYSTEM: Stage unlock text updated mid-game.")
            return redirect(url_for("interaction"))

        elif "generate_prompt" in request.form:
            prompt = generate_image_prompt_from_interpret_input()
            session["scene_image_prompt"] = prompt
            log_message(f"Generated image prompt: {prompt}")
            flash("Short image prompt generated from current context. You can now edit it if needed.", "info")
            return redirect(url_for("interaction"))

        elif "generate_image" in request.form:
            user_supplied_prompt = request.form.get("scene_image_prompt", "").strip()
            if not user_supplied_prompt:
                flash("No image prompt provided.", "danger")
                return redirect(url_for("interaction"))
            chosen_model = request.form.get("model_type", "flux")
            if chosen_model == "cyberpony":
                chosen_scheduler = request.form.get("cyber_scheduler", "K_EULER")
            elif chosen_model == "realistic":
                chosen_scheduler = request.form.get("realistic_scheduler", "EulerA")
            else:
                chosen_scheduler = None
            try:
                steps = int(request.form.get("num_steps", "60"))
            except:
                steps = 60
            handle_image_generation_from_prompt(
                prompt_text=user_supplied_prompt,
                force_new_seed=False,
                model_type=chosen_model,
                scheduler=chosen_scheduler,
                steps=steps
            )
            flash(f"Image generated successfully with model => {chosen_model}.", "success")
            return redirect(url_for("interaction"))

        elif "new_seed" in request.form:
            user_supplied_prompt = request.form.get("scene_image_prompt", "").strip()
            if not user_supplied_prompt:
                flash("No image prompt provided.", "danger")
                return redirect(url_for("interaction"))
            chosen_model = request.form.get("model_type", "flux")
            if chosen_model == "cyberpony":
                chosen_scheduler = request.form.get("cyber_scheduler", "K_EULER")
            elif chosen_model == "realistic":
                chosen_scheduler = request.form.get("realistic_scheduler", "EulerA")
            else:
                chosen_scheduler = None
            try:
                steps = int(request.form.get("num_steps", "60"))
            except:
                steps = 60
            handle_image_generation_from_prompt(
                prompt_text=user_supplied_prompt,
                force_new_seed=True,
                model_type=chosen_model,
                scheduler=chosen_scheduler,
                steps=steps
            )
            flash(f"New image generated with a new seed using model => {chosen_model}.", "success")
            return redirect(url_for("interaction"))
        else:
            return "Invalid submission in /interaction", 400

@app.route("/view_image")
@login_required
def view_image():
    return send_file(GENERATED_IMAGE_PATH, mimetype="image/jpeg")

@app.route("/full_story")
@login_required
def full_story():
    logs = session.get("interaction_log", [])
    story_lines = []
    for line in logs:
        if line.startswith("NARRATION => "):
            story_lines.append(line.replace("NARRATION => ", "", 1))
        elif line.startswith("User: "):
            story_lines.append("> " + line.replace("User: ", "", 1))
    return render_template("full_story.html", lines=story_lines, title="Full Story So Far")

@app.route("/continue_erotica", methods=["POST"])
@login_required
def continue_erotica():
    previous_text = request.form.get("previous_text", "").strip()
    continue_prompt = f"""
You are continuing an erotic story.
Pick up exactly where this left off and continue
the scene for another 600-900 words.

PREVIOUS TEXT:
{previous_text}

Now continue the story:
"""
    chat = model.start_chat()
    continuation = chat.send_message(
        continue_prompt,
        generation_config={"temperature": 0.8, "max_output_tokens": 1500},
        safety_settings=safety_settings
    )
    full_text = f"{previous_text}\n\n{continuation.text.strip()}"
    return render_template("erotica_story.html", erotica_text=full_text, title="Generated Erotica")

@app.route("/generate_erotica", methods=["POST"])
@login_required
def generate_erotica():
    logs = session.get("interaction_log", [])
    story_parts = []
    for line in logs:
        if line.startswith("NARRATION => "):
            story_parts.append(line.replace("NARRATION => ", "", 1))
        elif line.startswith("User: "):
            story_parts.append(line.replace("User: ", "", 1))
    if not story_parts:
        return redirect(url_for("full_story"))
    full_narration = "\n".join(story_parts)
    erotica_prompt = f"""
You are an author on an adult erotica forum.
Rewrite the scenario below into a detailed erotic short story from the user's perspective.

STORY LOG:
{full_narration}

Now produce a single narrative (600-900 words), focusing on emotional + physical details.
"""
    chat = model.start_chat()
    erotica_resp = chat.send_message(
        erotica_prompt,
        generation_config={"temperature": 0.8, "max_output_tokens": 1500},
        safety_settings=safety_settings
    )
    erotica_text = erotica_resp.text.strip()
    return render_template("erotica_story.html", erotica_text=erotica_text, title="Generated Erotica")

@app.route("/stage_unlocks", methods=["GET", "POST"])
@login_required
def stage_unlocks():
    if request.method == "POST" and "update_stage_unlocks" in request.form:
        su = session.get("stage_unlocks", {})
        for i in range(1, 7):
            key = f"stage_unlock_{i}"
            su[i] = request.form.get(key, "").strip()
        session["stage_unlocks"] = su
        log_message("SYSTEM: Stage unlock text updated.")
        return redirect(url_for("interaction"))
    return render_template("stage_unlocks.html",
        stage_unlocks=session.get("stage_unlocks", {}),
        title="Stage Unlocks"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)