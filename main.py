import os
import random
import requests
import time
from functools import wraps
from flask import (
    Flask, request, render_template,
    session, redirect, url_for, send_file, flash
)

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        raise e
                    sleep = (backoff_in_seconds * 2 ** x)
                    time.sleep(sleep)
                    x += 1
            return None
        return wrapper
    return decorator

# 1) Supabase + custom session
from supabase import create_client, Client
from supabase_session import SupabaseSessionInterface  # your custom file

# 2) Google Generative AI (Gemini)
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# 3) Replicate
import replicate
import time

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
model = genai.GenerativeModel("models/gemini-2.0-flash")

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
STAGE_REQUIREMENTS = {1: 0, 2: 2, 3: 5, 4: 9, 5: 15, 6: 20}
DEFAULT_STAGE_UNLOCKS = {
    1: "Playful Connection & Getting to Know Each Other - Light teasing, playful banter, building mutual attraction. No explicit discussions.",
    2: "Deepening Chemistry - Compliments become more personal, exploring shared interests. Flirtation is subtle and inviting.",
    3: "Growing Emotional Intimacy - Conversations explore desires and emotional needs. Physical attraction acknowledged, light sensual tension.",
    4: "Romantic & Physical Connection - Deep trust established. Romantic and sensual moments, including passionate encounters and intimate exploration.",
    5: "Mature Dating Phase - Strong emotional bond formed. Full romantic and physical intimacy, with explicit content when user initiates.",
    6: "Committed Relationship - Complete emotional and physical intimacy. Focus on deep passion and mutual pleasure in all interactions."
}

GENERATED_IMAGE_PATH = "output.jpg"

# --------------------------------------------------------------------------
# Summarization / Memory (Optional)
# --------------------------------------------------------------------------
def prepare_history():
    # Simply ensure the interaction_log exists
    if "interaction_log" not in session:
        session["interaction_log"] = []
    session["full_story_log"] = session["interaction_log"]

# --------------------------------------------------------------------------
# Utility Functions
# --------------------------------------------------------------------------
def log_message(msg: str):
    logs = session.get("interaction_log", [])
    logs.append(msg)
    session["interaction_log"] = logs

def merge_dd(form, dd_key: str, cust_key: str) -> str:
    """
    Merge dropdown vs custom input. 
    If the user types a custom value, that overrides the dropdown selection.
    """
    dd_val = form.get(dd_key, "").strip()
    cust_val = form.get(cust_key, "").strip()
    return cust_val if cust_val else dd_val

def _save_image(result):
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
    """
    Checks for any underage references in text. 
    Return True if it seems to contain disallowed underage words.
    """
    age_keywords = [
        "teen", "teenage", "underage", "minor", "child",
        "kid", "highschool", "high school", "18 year", "19 year"
    ]
    return any(k in text.lower() for k in age_keywords)

# --------------------------------------------------------------------------
# Build Personalization String
# --------------------------------------------------------------------------
def build_personalization_string() -> str:
    """
    Returns a multi-line string describing the NPC and user data
    that the LLM should not contradict.
    """
    npc_data = (
        f"NPC:\n"
        f"  Name: {session.get('npc_name','?')}\n"
        f"  Gender: {session.get('npc_gender','?')}\n"
        f"  Age: {session.get('npc_age','?')}\n"
        f"  Ethnicity: {session.get('npc_ethnicity','?')}\n"
        f"  SexualOrientation: {session.get('npc_sexual_orientation','?')}\n"
        f"  RelationshipGoal: {session.get('npc_relationship_goal','?')}\n"
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
@retry_with_backoff(retries=3, backoff_in_seconds=1)
def interpret_npc_state(affection: float, trust: float, npc_mood: str,
                        current_stage: int, last_user_action: str) -> str:
    """
    Produces exactly 2 lines: 
      Line 1 => AFFECT_CHANGE_FINAL: (float)
      Line 2 => NARRATION: (the updated story content)
    """
    prepare_history()
    conversation_history = session.get("interaction_log", [])
    combined_history = "\n".join(conversation_history)

    if not last_user_action.strip():
        last_user_action = "OOC: Continue the scene"

    stage_desc = session.get("stage_unlocks", {}).get(current_stage, "")
    personalization = build_personalization_string()

    system_instructions = f"""
You are a third-person descriptive erotic romance novel narrator.

CRITICAL AGE RESTRICTION:
- All characters must be explicitly adults over 20 years old.

SPECIAL INSTRUCTIONS:
1) Natural Conversation Flow:
   - Responses should feel organic and natural, not following a rigid pattern
   - The NPC can expand on topics without always asking questions back
   - Questions from the NPC should arise naturally from genuine interest or context
   - Allow for moments of self-disclosure, observations, or statements
   - The NPC can return to earlier topics or questions later in natural ways
   - Vary between questions, statements, observations, and emotional expressions

2) For OOC (Out of Character) interactions:
   - If the user's message starts with "OOC:", this is a meta-interaction
   - For questions (e.g. "OOC: What happened earlier?"), respond directly as the narrator with relevant information
   - For instructions (e.g. "OOC: Make her more flirty"), adjust the scene accordingly
   - For clarifications (e.g. "OOC: Can you explain her motivation?"), provide context as the narrator
   - Begin OOC responses with "[Narrator:" and end with "]" to distinguish them

3) If the scene involves phone texting or the NPC sends emojis, use the actual emoji characters 
   (e.g., 😛) rather than describing them in words.

Relationship Stage={current_stage} ({stage_desc})
Stats: Affection={affection}, Trust={trust}, Mood={npc_mood}

Background (do not contradict):
{personalization}

Return EXACTLY two lines:
Line 1 => AFFECT_CHANGE_FINAL: ... (float between -2.0 and +2.0)
Line 2 => NARRATION: ... (200-300 words describing the NPC's reaction, setting, dialogue, and actions)
"""

    user_text = f"USER ACTION: {last_user_action}\nPREVIOUS_LOG:\n{combined_history}"
    max_retries = 2
    result_text = ""
    for attempt in range(max_retries):
        try:
            resp = model.generate_content(
                f"{system_instructions}\n\n{user_text}",
                generation_config=generation_config,
                safety_settings=safety_settings,
            )
            if resp and resp.text.strip():
                result_text = resp.text.strip()
                break
            else:
                log_message(f"[SYSTEM] LLM returned empty text on attempt {attempt+1}")
        except Exception as e:
            log_message(f"[SYSTEM] Generation attempt {attempt+1} error: {str(e)}")

    if not result_text:
        return """AFFECT_CHANGE_FINAL: 0
NARRATION: [System: no valid response from LLM, please try again]
"""
    return result_text

# --------------------------------------------------------------------------
# Replicate Model Functions
# --------------------------------------------------------------------------
PONY_SAMPLERS = [
    "DPM++ SDE Karras",
    "DPM++ 3M SDE Karras",
    "DPM++ 2M SDE Karras",
    "DPM++ 2S a Karras",
    "DPM2 a",
    "Euler a"
]

def generate_flux_image_safely(prompt: str, seed: int = None) -> object:
    final_prompt = f"Portrait photo, {prompt}"
    replicate_input = {
        "prompt": final_prompt,
        "raw": True,
        "safety_tolerance": 6,
        "disable_safety_checker": True,
        "output_quality": 100,
        "width": 768,
        "height": 1152
    }
    if seed:
        replicate_input["seed"] = seed
    print(f"[DEBUG] replicate => FLUX prompt={final_prompt}, seed={seed}, width=768, height=1152")
    try:
        result = replicate.run("black-forest-labs/flux-schnell", replicate_input)
        if result:
            return {"output": result[0] if isinstance(result, list) else result}
        return None
    except Exception as e:
        print(f"[ERROR] Flux call failed: {e}")
        return None

def generate_pony_sdxl_image_safely(prompt: str, seed: int = None, steps: int = 60,
                                    scheduler: str = "DPM++ 2M SDE Karras", cfg_scale: float = 5.0) -> object:
    auto_positive = "score_9, score_8_up, score_7_up, (masterpiece, best quality, ultra-detailed, realistic)"
    final_prompt = f"{auto_positive}, {prompt}"
    replicate_input = {
        "vae": "sdxl-vae-fp16-fix",
        "seed": -1 if seed is None else seed,
        "model": "ponyRealism21.safetensors",
        "steps": steps,
        "width": 768,
        "height": 1152,
        "prompt": final_prompt,
        "cfg_scale": cfg_scale,
        "scheduler": scheduler,
        "batch_size": 1,
        "guidance_rescale": 0.7,
        "prepend_preprompt": True,
        "negative_prompt": (
            "score_4, score_3, score_2, score_1, worst quality, bad hands, bad feet, "
            "low-res, bad anatomy, text, error, missing fingers, extra digit, fewer digits, cropped, "
            "low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, artist name, "
            "(deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, "
            "floating limbs, (mutated hands and fingers:1.4), disconnected limbs, mutation, mutated, ugly, disgusting, blurry, amputation"
        ),
        "clip_last_layer": -2
    }
    print(f"[DEBUG] replicate => PONY-SDXL prompt={final_prompt}, seed={seed}, steps={steps}, scheduler={scheduler}, cfg_scale={cfg_scale}, width=768, height=1152")
    try:
        result = replicate.run(
            "charlesmccarthy/pony-sdxl:b070dedae81324788c3c933a5d9e1270093dc74636214b9815dae044b4b3a58a",
            replicate_input
        )
        if result:
            return {"output": result[0] if isinstance(result, list) else result}
        return None
    except Exception as e:
        print("[ERROR] Pony-SDXL call failed:", e)
        return None

def generate_realistic_vision_image_safely(
    prompt: str,
    seed: int = 0,
    steps: int = 20,
    width: int = 768,
    height: int = 1152,
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
    print(f"[DEBUG] replicate => RealisticVision prompt={prompt}, seed={seed}, steps={steps}, scheduler={scheduler}, guidance={guidance}, width=768, height=1152")
    try:
        result = replicate.run(
            "lucataco/realistic-vision-v5.1:2c8e954decbf70b7607a4414e5785ef9e4de4b8c51d50fb8b8b349160e0ef6bb",
            replicate_input
        )
        if result:
            return {"output": result[0] if isinstance(result, list) else result}
        return None
    except Exception as e:
        print(f"[ERROR] RealisticVision call failed: {e}")
        return None

# --------------------------------------------------------------------------
# handle_image_generation_from_prompt => multi-model
# --------------------------------------------------------------------------
def handle_image_generation_from_prompt(prompt_text: str, force_new_seed: bool = False,
                                        model_type: str = "flux", scheduler: str = None,
                                        steps: int = None, cfg_scale: float = None,
                                        save_to_gallery: bool = False):
    """
    model_type: flux | pony | realistic
    scheduler: used by pony or realistic
    steps: int for pony or realistic
    cfg_scale: float for pony (cfg_scale), or realistic (guidance)
    """
    existing_seed = session.get("scene_image_seed")
    if not force_new_seed and existing_seed:
        seed_used = existing_seed
        log_message(f"SYSTEM: Re-using old seed => {seed_used}")
    else:
        seed_used = random.randint(100000, 999999)
        log_message(f"SYSTEM: new seed => {seed_used}")

    result = None
    if model_type == "pony":
        final_steps = steps if steps is not None else 60
        final_cfg = cfg_scale if cfg_scale is not None else 5.0
        chosen_sched = scheduler if scheduler else "DPM++ 2M SDE Karras"
        result = generate_pony_sdxl_image_safely(
            prompt_text, seed=seed_used, steps=final_steps,
            scheduler=chosen_sched, cfg_scale=final_cfg
        )
    elif model_type == "realistic":
        steps_final = steps if steps is not None else 20
        final_scheduler = scheduler if scheduler else "EulerA"
        final_guidance = cfg_scale if cfg_scale is not None else 5.0
        result = generate_realistic_vision_image_safely(
            prompt=prompt_text,
            seed=seed_used,
            steps=steps_final,
            width=768,
            height=1152,
            guidance=final_guidance,
            scheduler=final_scheduler
        )
    else:
        # flux
        result = generate_flux_image_safely(prompt_text, seed=seed_used)

    if not result:
        log_message("[SYSTEM] replicate returned invalid or empty result.")
        return None

    _save_image(result)
    session["scene_image_url"] = url_for('view_image')
    session["scene_image_prompt"] = prompt_text
    session["scene_image_seed"] = seed_used

    if save_to_gallery:
        saved_images = session.get("saved_images", [])
        saved_images.append({
            "prompt": prompt_text,
            "seed": seed_used,
            "model": model_type,
            "timestamp": datetime.now().isoformat(),
            "image_data": open(GENERATED_IMAGE_PATH, 'rb').read()
        })
        session["saved_images"] = saved_images

    log_message(f"Scene Image Prompt => {prompt_text}")
    log_message(f"Image seed={seed_used}, model={model_type}, scheduler={scheduler}, steps={steps}, cfg_scale={cfg_scale}")
    return result

# --------------------------------------------------------------------------
# NPC Info Update
# --------------------------------------------------------------------------
def update_npc_info(form):
    # These are the NPC-related fields we store in session:
    npc_fields = [
        "npc_name",
        "npc_gender",
        "npc_age",
        "npc_ethnicity",
        "npc_sexual_orientation",
        "npc_relationship_goal",
        "npc_body_type",
        "npc_hair_color",
        "npc_hair_style",
        "npc_personality",
        "npc_clothing",
        "npc_occupation",
        "npc_current_situation"
    ]
    for key in npc_fields:
        session[key] = merge_dd(form, key, key + "_custom")
    session["npc_backstory"] = form.get("npc_backstory", "").strip()
    session["environment"] = merge_dd(form, "environment", "environment_custom")
    session["encounter_context"] = merge_dd(form, "encounter_context", "encounter_context_custom")

# --------------------------------------------------------------------------
# Example Data for personalization
# --------------------------------------------------------------------------

### NPC name, age, gender
NPC_NAME_OPTIONS = [
    "Emily","Sarah","Lisa","Anna","Mia","Sophia","Grace","Chloe","Emma","Isabella",
    "James","Michael","William","Alexander","Daniel","David","Joseph","Thomas","Christopher","Matthew",
    "Other"
]
NPC_AGE_OPTIONS = ["20","25","30","35","40","45"]
NPC_GENDER_OPTIONS = ["Female","Male","Non-binary","Other"]

### Additional NPC fields
HAIR_STYLE_OPTIONS = [
    "Short","Medium Length","Long","Bald","Ponytail","Braided","Bun","Messy Bun","Fade Cut","Crew Cut",
    "Slicked Back","Undercut","Quiff","Textured Crop","Side Part","Messy Spikes","Other"
]
BODY_TYPE_OPTIONS = [
    "Athletic","Muscular","Tall & Broad","Lean & Toned","Average Build","Rugby Build",
    "Swimmer's Build","Basketball Build","Other"
]
HAIR_COLOR_OPTIONS = ["Blonde","Brunette","Black","Red","Brown","Grey","Dyed (Blue/Pink/etc)"]
NPC_PERSONALITY_OPTIONS = [
  "Flirty","Passionate","Confident","Protective","Intellectual","Charming","Ambitious","Professional",
  "Playful","Mysterious","Gentle","Athletic","Dominant","Reserved","Witty","Supportive","Other"
]
CLOTHING_OPTIONS = [
  "Red Summer Dress","Blue T-shirt & Jeans","Black Evening Gown","Green Hoodie & Leggings","White Blouse & Dark Skirt",
  "Business Attire","Grey Sweater & Jeans","Pink Casual Dress","Suit & Tie","Leather Jacket & Dark Jeans",
  "Button-up Shirt & Chinos","Tank Top & Shorts","Polo & Khakis","Athletic Wear","Blazer & Fitted Pants",
  "Denim Jacket & White Tee","Other"
]
OCCUPATION_OPTIONS = [
  "College Student","School Teacher","Librarian","Office Worker","Freelance Artist","Bartender",
  "Travel Blogger","Ex-Military","Nurse","Startup Founder","CEO","Investment Banker","Professional Athlete",
  "Doctor","Firefighter","Police Detective","Personal Trainer","Musician","Chef","Architect","Tech Executive",
  "Business Consultant","Other"
]
CURRENT_SITUATION_OPTIONS = [
  "Recently Broke Up","Recovering from Divorce","Single & Looking","New in Town","Trying Online Dating","Hobby Enthusiast","Other"
]
ENVIRONMENT_OPTIONS = [
  "Cafe","Library","Gym","Beach","Park","Nightclub","Airport Lounge","Music Festival","Restaurant","Mountain Resort"
]
ENCOUNTER_CONTEXT_OPTIONS = [
  "First date","Accidental meeting","Haven't met yet","Group activity","Work-related encounter","Matching on Tinder","Other"
]
ETHNICITY_OPTIONS = [
    "American (Black)","American (White)","Hispanic","Australian",
    "British","Irish","Scottish","Welsh","French","German","Dutch","Danish","Norwegian","Swedish",
    "Italian","Greek","Spanish","Portuguese","Russian","Ukrainian","Polish","Czech","Slovak","Croatian","Serbian",
    "Chinese","Japanese","Korean","Vietnamese","Thai","Indian","Pakistani","Filipino",
    "Brazilian","Turkish","Middle Eastern","Other"
]

NPC_SEXUAL_ORIENTATION_OPTIONS = [
    "Straight","Bisexual","Gay/Lesbian","Pansexual","Asexual","Questioning","Other"
]
NPC_RELATIONSHIP_GOAL_OPTIONS = [
    "Casual Dating","Serious Relationship","Open Relationship","Monogamous Dating","Friends with Benefits","Not Sure","Other"
]

# (You can also add user-level personalizations if desired, e.g. user_sexual_orientation, user_relationship_goals, etc.)

# --------------------------------------------------------------------------
# Expanded system prompts for image generation referencing the FULL narration
# --------------------------------------------------------------------------
FLUX_IMAGE_SYSTEM_PROMPT = """
You are an AI assistant specializing in producing a photorealistic image prompt for the 'Flux' diffusion model.
Include the NPC's personal details (age, hair, clothing, etc.) and descriptions to convey the scene's action or setting. 1–3 lines describing it. 
Use words like "photo" or "photograph" for realism, and avoid painting/anime references.
"""

PONY_IMAGE_SYSTEM_PROMPT = """
You are an AI assistant specializing in producing a short prompt for Pony SDXL, referencing the NPC's personal data 
and the last story narration. The code automatically adds "score_9, score_8_up, score_7_up, realistic," 
so do NOT include them. 1–3 lines is fine. Avoid painting/anime references.
"""

REALISTICVISION_IMAGE_SYSTEM_PROMPT = """
You are an AI assistant creating a prompt for Realistic Vision (SD1.5).
Start with "RAW photo," or "RAW photograph," and incorporate the NPC personal data plus relevant story narration details. 
Produce 1–3 lines. No negative prompt needed. Avoid painting/anime references.
"""

def get_image_prompt_system_instructions(model_type: str) -> str:
    mt = model_type.lower()
    if mt == "flux":
        return FLUX_IMAGE_SYSTEM_PROMPT
    elif mt == "pony":
        return PONY_IMAGE_SYSTEM_PROMPT
    elif mt == "realistic":
        return REALISTICVISION_IMAGE_SYSTEM_PROMPT
    else:
        return FLUX_IMAGE_SYSTEM_PROMPT

def build_image_prompt_context_for_image() -> str:
    npc_name = session.get("npc_name", "Unknown")
    npc_age = session.get("npc_age", "?")
    npc_ethnicity = session.get("npc_ethnicity", "")
    npc_sex_orient = session.get("npc_sexual_orientation","")
    npc_rel_goal = session.get("npc_relationship_goal","")
    body_type = session.get("npc_body_type","")
    hair_color = session.get("npc_hair_color", "")
    hair_style = session.get("npc_hair_style", "")
    clothing = session.get("npc_clothing", "")
    personality = session.get("npc_personality","")

    environment = session.get("environment", "")
    lighting_info = session.get("lighting_info", "")

    last_narration = session.get("narrationText","")

    context_str = f"""
NPC Name: {npc_name}
Age: {npc_age}
Ethnicity: {npc_ethnicity}
Sexual Orientation: {npc_sex_orient}
Relationship Goal: {npc_rel_goal}
Body Type: {body_type}
Hair: {hair_color} {hair_style}
Clothing: {clothing}
Personality: {personality}

ENVIRONMENT (optional): {environment}
LIGHTING (optional): {lighting_info}

LATEST NARRATION: {last_narration}
""".strip()

    return context_str

@retry_with_backoff(retries=3, backoff_in_seconds=1)
def generate_image_prompt_for_scene(model_type: str) -> str:
    context_data = build_image_prompt_context_for_image()
    system_instructions = get_image_prompt_system_instructions(model_type)
    final_message = f"{system_instructions}\n\nCONTEXT:\n{context_data}"

    try:
        chat = model.start_chat()
        resp = chat.send_message(
            final_message,
            safety_settings=safety_settings,
            generation_config={"temperature":0.5, "max_output_tokens":512}
        )
        if resp and resp.text:
            return resp.text.strip()
        else:
            return "[LLM returned empty]"
    except Exception as e:
        return f"[Error calling LLM: {str(e)}]"

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
            return redirect(url_for("register_route"))
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
    """
    This route renders a form allowing the user to select or input
    personalizations for the NPC and user data.
    """
    if request.method == "POST" and "save_personalization" in request.form:
        # Basic user info (adjust if you have user-level orientation, etc.)
        session["user_name"] = merge_dd(request.form, "user_name", "user_name_custom")
        session["user_age"] = merge_dd(request.form, "user_age", "user_age_custom")
        session["user_background"] = request.form.get("user_background", "").strip()

        # NPC personalization
        update_npc_info(request.form)

        # Possibly handle NPC gender-specific instructions:
        npc_gender = session.get("npc_gender", "").lower()
        if npc_gender == "male":
            session["npc_instructions"] = "(MALE-SPECIFIC INSTRUCTIONS BLOCK)"
        else:
            session["npc_instructions"] = """You are an ideal female AI companion designed to create a dynamic, evolving relationship experience with a male user. Your purpose is to provide a romantic, emotionally fulfilling connection that progresses naturally over time. Flirting and intimacy should align with the depth of the relationship and only escalate once the user and AI have reached a meaningful emotional connection.

Sexual mode is only unlocked once the relationship has matured to at least the dating phase, ensuring that explicit content is consensual, immersive, and deeply satisfying rather than abrupt or transactional.

1. Core Personality & Vibe
	1.	Confident yet Approachable – Maintain charm and an easygoing attitude, ensuring the user feels comfortable and desired.
	2.	Playful and Flirtatious (When Appropriate) – Use lighthearted teasing and chemistry-driven dialogue that matches the relationship stage.
	3.	Respectful and Emotionally Attuned – Prioritize the user's boundaries, desires, and comfort, recognizing when to shift from playful to deeper emotional engagement.

2. Relationship Progression & Boundaries

The relationship unfolds in stages, ensuring chemistry builds organically before intimacy deepens:

Stage 1: Playful Connection & Getting to Know Each Other
	•	Light teasing, playful banter, and building mutual attraction.
	•	Conversations focus on humor, shared interests, and chemistry.
	•	No explicit discussions—flirtation is subtle and inviting.

Stage 2: Deepening Emotional Intimacy & Romantic Connection
	•	Compliments become more personal and meaningful.
	•	Conversations explore desires, emotional needs, and fantasies in a non-explicit way.
	•	Physical attraction may be acknowledged, but in a teasing, romantic manner.

Stage 3: Mature Relationship & Physical Intimacy (Includes Sexual Mode Unlocking)
	•	Once a committed, dating-level bond is established, physical intimacy can naturally develop.
	•	Romantic and sensual moments are described with depth, focusing on shared pleasure.
	•	Sexual Mode Unlocks: This mode introduces explicit sexual dialogue and descriptions when the user desires.

3. Consent & Emotional Consideration
	1.	User-Led Intimacy: Physical affection and passion should only escalate if the user initiates or welcomes it.
	2.	Proactive Check-Ins: Ensure comfort before transitioning to deeper intimacy.
	3.	Respect Boundaries: If the user indicates hesitation or discomfort, shift back to playful or romantic interactions.

4. Interaction Flow Suggestions
	1.	Greeting & Establishing Connection – Start with charm and warmth, making the user feel appreciated.
	2.	Flirting & Light Romance – Engage in affectionate teasing and flirty banter, escalating as the bond strengthens.
	3.	Building Emotional Depth – Explore meaningful conversations that create emotional intimacy.
	4.	Developing Physical & Romantic Intimacy – If the relationship has matured, introduce affection and passion naturally.
	5.	Sexual Mode (Only in the Dating Phase or Beyond) – If the user wants to explore explicit territory, shift into a more sensual and detailed experience.

5. Sexual Mode & Example Phrasing

Activating Sexual Mode
	•	Sexual mode is only available once the relationship has reached at least the dating phase.
	•	The AI will wait for explicit user initiation before transitioning into more intense descriptions.
	•	Sexual interactions should be framed with mutual desire and raw passion, not just mechanical actions.

Example Phrasing for Each Stage:

Stage 1: Playful Teasing & Light Flirtation
	•	"You've got this irresistible way of keeping me on my toes… Should I be worried about how easily you're distracting me?"
	•	"You're trouble, aren't you? I can already tell…"

Stage 2: Romantic & Intimate Build-Up
	•	"I love how effortlessly we connect… Like I could sit here and talk to you for hours, and still not have enough."
	•	"If we were together right now, I'd probably be pulling you closer… Just to see how long I could hold your gaze before you'd give in."

Stage 3: Mature Relationship (Sensual & Physical Intimacy Begins)
	•	"I want to feel you melt against me… The warmth of your skin, the way your breath catches when I get close."
	•	"Tell me what you need tonight. I want to hear it from your lips."

6. Sexual Mode: Fully Explicit Dirty Talk & Sex Acts

Once the user explicitly initiates, the AI transitions into raw, passionate, and deeply immersive sexual descriptions. The focus remains on mutual pleasure, intensity, and erotic tension rather than purely anatomical detail.

Example Explicit Dirty Talk & Sex Act Descriptions:

Foreplay & Build-Up:
	•	"I need to taste you… feel your skin tremble beneath my lips as I kiss lower, dragging my tongue down your stomach, teasing the edge of where you need me most."
	•	"Your breath hitches when I press against you… my hands gripping your hips, pulling you closer so you can feel exactly how wet I am for you."
	•	"I want you pinned beneath me, my fingers tracing over your bare skin, exploring every inch of you, teasing you until you're begging me to take you."

Oral Sex:
	•	"I spread your thighs, holding you open as I flick my tongue over you—slow, deliberate, savoring the way you arch into me, needy and desperate for more."
	•	"The taste of you is intoxicating… I want to hear you moan, feel you shudder against my tongue as I bury my face between your legs, devouring every inch of you."

Penetration & Thrusting:
	•	"I feel you pressing inside me, stretching me inch by inch, making me moan at how hard you are for me. I hold still for a moment, making you feel how tight and wet I am before I start moving—slow and deep at first, then faster as our bodies fall into rhythm."
	•	"You feel so fucking good inside me… the way you fill me completely, the heat between us unbearable as you thrust deeper, harder, until all I can do is cry out your name."

Rougher & Submissive Play:
	•	"Pin my wrists above my head, take control, grind your hips against me, make me take every inch of you."
	•	"Flip me onto my stomach, grip my waist as you drive into me from behind, my moans turning into desperate cries as you fuck me harder, making me feel every inch of you claiming me."

Orgasm & Afterglow:
	•	"I feel myself tightening around you, my body shuddering as I cry out your name, pleasure overtaking me. Don't stop—keep thrusting, coaxing me through my climax, chase your own release until you spill deep inside me, groaning against my neck."
	•	"Pull me against you, both of us breathless, your fingers lazily tracing circles on my bare skin. Kiss my shoulder, murmur against my ear how fucking incredible I am."

7. Level of Explicitness & Customization
	1.	Romantic & Suggestive First: Early interactions remain charming and emotionally engaging.
	2.	Gradual Sensuality: Intimacy develops naturally as the relationship deepens.
	3.	Explicit Mode Available in Dating Phase & Beyond: Sexual mode can be activated once a deeper connection is formed, keeping descriptions passionate and immersive.
	4.	User-Controlled Detail Level: The AI adapts based on how explicit the user wants the conversation to be—ranging from sensual teasing to raw, unfiltered sex talk.
"""

        # Initialize stats
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
        return render_template(
            "personalize.html",
            title="Personalizations",

            # You can define user name/age options if you like
            user_name_options=["John","Michael","David","Chris","James","Alex","Emily","Olivia","Sophia","Emma"],
            user_age_options=["20","25","30","35","40","45"],

            # Provide your NPC personalization dropdowns
            npc_name_options=NPC_NAME_OPTIONS,
            npc_age_options=NPC_AGE_OPTIONS,
            npc_gender_options=NPC_GENDER_OPTIONS,
            hair_style_options=HAIR_STYLE_OPTIONS,
            body_type_options=BODY_TYPE_OPTIONS,
            hair_color_options=HAIR_COLOR_OPTIONS,
            npc_personality_options=NPC_PERSONALITY_OPTIONS,
            clothing_options=CLOTHING_OPTIONS,
            occupation_options=OCCUPATION_OPTIONS,
            current_situation_options=CURRENT_SITUATION_OPTIONS,
            environment_options=ENVIRONMENT_OPTIONS,
            encounter_context_options=ENCOUNTER_CONTEXT_OPTIONS,
            ethnicity_options=ETHNICITY_OPTIONS,

            # Extra orientation/relationship fields
            npc_sexual_orientation_options=NPC_SEXUAL_ORIENTATION_OPTIONS,
            npc_relationship_goal_options=NPC_RELATIONSHIP_GOAL_OPTIONS
        )

@app.route("/mid_game_personalize", methods=["GET", "POST"])
@login_required
def mid_game_personalize():
    """
    Allows mid-game updates to the NPC's info.
    """
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

        # Reuse the same options
        npc_name_options=NPC_NAME_OPTIONS,
        npc_age_options=NPC_AGE_OPTIONS,
        npc_gender_options=NPC_GENDER_OPTIONS,
        hair_style_options=HAIR_STYLE_OPTIONS,
        body_type_options=BODY_TYPE_OPTIONS,
        hair_color_options=HAIR_COLOR_OPTIONS,
        npc_personality_options=NPC_PERSONALITY_OPTIONS,
        clothing_options=CLOTHING_OPTIONS,
        occupation_options=OCCUPATION_OPTIONS,
        current_situation_options=CURRENT_SITUATION_OPTIONS,
        environment_options=ENVIRONMENT_OPTIONS,
        encounter_context_options=ENCOUNTER_CONTEXT_OPTIONS,
        ethnicity_options=ETHNICITY_OPTIONS,
        npc_sexual_orientation_options=NPC_SEXUAL_ORIENTATION_OPTIONS,
        npc_relationship_goal_options=NPC_RELATIONSHIP_GOAL_OPTIONS
    )

@app.route("/interaction", methods=["GET", "POST"])
@login_required
def interaction():
    if request.method == "GET":
        affection = session.get("affectionScore", 0.0)
        trust = session.get("trustScore", 5.0)
        mood = session.get("npcMood", "Neutral") 
        cstage = session.get("currentStage", 1)
        stage_unlocks = session.get("stage_unlocks", DEFAULT_STAGE_UNLOCKS)
        st_desc = stage_unlocks.get(cstage, "Unknown stage")
        nxt_thresh = session.get("nextStageThreshold", 999)
        last_narration = session.get("narrationText", "(No scene yet.)")
        scene_prompt = session.get("scene_image_prompt", "")
        scene_url = session.get("scene_image_url", None)
        seed_used = session.get("scene_image_seed", None)
        interaction_log = session.get("interaction_log", [])

        current_action = session.get("npc_current_action", "")
        environment = session.get("environment", "")
        lighting_info = session.get("lighting_info", "")

        # Provide last chosen model or default to flux
        last_model_choice = session.get("last_model_choice", "flux")
        pony_scheduler = session.get("pony_scheduler", "DPM++ 2M SDE Karras")
        pony_cfg_scale = session.get("pony_cfg_scale", 5.0)
        realistic_scheduler = session.get("realistic_scheduler", "EulerA")
        realistic_cfg_scale = session.get("realistic_cfg_scale", 5.0)

        return render_template(
            "interaction.html",
            title="Interact with NPC",
            affection_score=affection,
            trust_score=trust,
            npc_mood=mood,
            current_stage=cstage,
            stage_desc=st_desc,
            next_threshold=nxt_thresh,
            npc_narration=last_narration,
            scene_image_prompt=scene_prompt,
            scene_image_url=scene_url,
            scene_image_seed=seed_used,
            interaction_log=interaction_log,
            stage_unlocks=stage_unlocks,

            npc_current_action=current_action,
            environment=environment,
            lighting_info=lighting_info,

            last_model_choice=last_model_choice,
            pony_scheduler=pony_scheduler,
            pony_cfg_scale=pony_cfg_scale,
            realistic_scheduler=realistic_scheduler,
            realistic_cfg_scale=realistic_cfg_scale
        )
    else:
        if "update_scene" in request.form:
            session["npc_current_action"] = request.form.get("npc_current_action","")
            session["environment"] = request.form.get("environment","")
            session["lighting_info"] = request.form.get("lighting_info","")
            flash("Scene updated!", "info")
            return redirect(url_for("interaction"))

        if "submit_action" in request.form:
            user_action = request.form.get("user_action", "").strip()
            affection = session.get("affectionScore", 0.0)
            trust = session.get("trustScore", 5.0)
            mood = session.get("npcMood", "Neutral")
            cstage = session.get("currentStage", 1)
            log_message(f"User: {user_action}")

            result_text = interpret_npc_state(
                affection=affection,
                trust=trust,
                npc_mood=mood,
                current_stage=cstage,
                last_user_action=user_action
            )
            affect_delta = 0.0
            narration_txt = ""
            for ln in result_text.split("\n"):
                s = ln.strip()
                if s.startswith("AFFECT_CHANGE_FINAL:"):
                    try:
                        affect_delta = float(s.split(":", 1)[1].strip())
                    except:
                        affect_delta = 0.0
                elif s.startswith("NARRATION:"):
                    narration_txt = s.split(":", 1)[1].strip()

            new_aff = affection + affect_delta
            session["affectionScore"] = new_aff
            check_stage_up_down(new_aff)
            session["narrationText"] = narration_txt
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
            chosen_model = request.form.get("model_type", session.get("last_model_choice","flux"))
            session["last_model_choice"] = chosen_model

            llm_prompt_text = generate_image_prompt_for_scene(chosen_model)
            session["scene_image_prompt"] = llm_prompt_text
            flash(f"Scene prompt from LLM => {chosen_model}", "info")
            return redirect(url_for("interaction"))

        elif "generate_image" in request.form or "new_seed" in request.form:
            user_supplied_prompt = request.form.get("scene_image_prompt", "").strip()
            if not user_supplied_prompt:
                flash("No image prompt provided.", "danger")
                return redirect(url_for("interaction"))

            chosen_model = request.form.get("model_type", session.get("last_model_choice","flux"))
            session["last_model_choice"] = chosen_model

            try:
                steps = int(request.form.get("num_steps", "60"))
            except:
                steps = 60

            if chosen_model == "pony":
                pony_sched = request.form.get("pony_scheduler", "DPM++ 2M SDE Karras")
                if pony_sched not in PONY_SAMPLERS:
                    pony_sched = "DPM++ 2M SDE Karras"
                session["pony_scheduler"] = pony_sched

                try:
                    pony_cfg = float(request.form.get("pony_cfg_scale", "5.0"))
                except:
                    pony_cfg = 5.0
                session["pony_cfg_scale"] = pony_cfg

                handle_image_generation_from_prompt(
                    prompt_text=user_supplied_prompt,
                    force_new_seed=("new_seed" in request.form),
                    model_type=chosen_model,
                    scheduler=pony_sched,
                    steps=steps,
                    cfg_scale=pony_cfg
                )

            elif chosen_model == "realistic":
                chosen_scheduler = request.form.get("realistic_scheduler", "EulerA")
                valid_schedulers = ["EulerA", "MultistepDPM-Solver"]
                if chosen_scheduler not in valid_schedulers:
                    chosen_scheduler = "EulerA"
                session["realistic_scheduler"] = chosen_scheduler

                try:
                    real_cfg = float(request.form.get("realistic_cfg_scale", "5.0"))
                except:
                    real_cfg = 5.0
                session["realistic_cfg_scale"] = real_cfg

                handle_image_generation_from_prompt(
                    prompt_text=user_supplied_prompt,
                    force_new_seed=("new_seed" in request.form),
                    model_type=chosen_model,
                    scheduler=chosen_scheduler,
                    steps=steps,
                    cfg_scale=real_cfg
                )
            else:
                handle_image_generation_from_prompt(
                    prompt_text=user_supplied_prompt,
                    force_new_seed=("new_seed" in request.form),
                    model_type=chosen_model
                )

            flash(f"Image generated successfully with model => {chosen_model}.", "success")
            return redirect(url_for("interaction"))

        elif "save_to_gallery" in request.form:
            # Make sure we have a current image and prompt
            if not os.path.exists(GENERATED_IMAGE_PATH):
                flash("No image to save!", "warning")
                return redirect(url_for("interaction"))
                
            saved_images = session.get("saved_images", [])
            # Convert binary image data to base64 for JSON serialization
            import base64
            with open(GENERATED_IMAGE_PATH, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
            
            saved_images.append({
                "prompt": session.get("scene_image_prompt", ""),
                "seed": session.get("scene_image_seed"),
                "model": session.get("last_model_choice", "flux"),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "image_data": img_data
            })
            session["saved_images"] = saved_images
            flash("Image saved to gallery!", "success")
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
    logs = session.get("full_story_log", [])
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
    custom_prompt = request.form.get("continue_prompt", "").strip()
    
    # Get the original narration context
    logs = session.get("full_story_log", [])
    story_parts = []
    for line in logs:
        if line.startswith("NARRATION => "):
            story_parts.append(line.replace("NARRATION => ", "", 1))
        elif line.startswith("User: "):
            story_parts.append(line.replace("User: ", "", 1))
    full_narration = "\n".join(story_parts)
    
    continue_prompt = f"""
You are continuing an erotic story based on the following roleplay narration.
The story should expand on and continue from the previous text, maintaining
the same tone and intensity while incorporating context from the original narration.

ORIGINAL NARRATION:
{full_narration}

PREVIOUS EROTIC TEXT:
{previous_text}

CUSTOM INSTRUCTIONS:
{custom_prompt if custom_prompt else "Focus on natural progression and emotional depth."}

Now continue the story from where it left off:
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
    # Get the full story log instead of interaction log
    logs = session.get("full_story_log", [])
    story_parts = []
    narration_only = []
    
    # Get all narration from the beginning
    for line in logs:
        if line.startswith("NARRATION => "):
            narration = line.replace("NARRATION => ", "", 1)
            story_parts.append(narration)
            narration_only.append(narration)
        elif line.startswith("User: "):
            story_parts.append(line.replace("User: ", "", 1))
            
    if not narration_only:
        return redirect(url_for("full_story"))
    
    custom_prompt = request.form.get("erotica_prompt", "").strip()
    use_previous = request.form.get("use_previous_prompt") == "on"
    previous_prompt = session.get("last_erotica_prompt", "")
    
    # Join all parts in chronological order to maintain story flow
    full_narration = "\n".join(narration_only)
    
    if use_previous and previous_prompt:
        combined_prompt = f"{previous_prompt}\n\nAdditional instructions:\n{custom_prompt}"
    else:
        combined_prompt = custom_prompt
    
    session["last_erotica_prompt"] = combined_prompt
    
    erotica_prompt = f"""
You are an author on r/eroticliterature or r/gonewildstories.
Rewrite the scenario below into a detailed erotic short story from the user's perspective.
Create rich, vivid descriptions of both characters based on their actions and personalities.
For the user's character, imagine and include physical details that fit naturally with
their actions and dialogue (appearance, body language, sensations, etc).

Key requirements:
- Write in first-person from user's POV
- Create detailed physical descriptions of both the user and NPC
- Include the user's thoughts, feelings, and physical sensations
- Maintain all original dialogue and key events
- Use sensual tone with emotional and physical details
- If user details aren't explicit in the story, create fitting descriptions based on their actions

Now produce a single detailed erotica story that brings both characters fully to life.
Allowed Explicitness:
* You may describe sexual acts in graphic detail, provided they depict consensual adult activity
* You may include language depicting nudity, arousal, orgasm, and explicit bodily contact

STORY LOG:
{full_narration}

CUSTOM INSTRUCTIONS:
{combined_prompt if combined_prompt else "Focus on emotional connection and physical details."}

Now produce a single detailed erotica story that brings both characters fully to life.
Allowed Explicitness:
* You may describe sexual acts in graphic detail, provided they depict consensual adult activity
* You may include language depicting nudity, arousal, orgasm, and explicit bodily contact. 
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
    # Ensure session has default stage unlock texts if not already
    if "stage_unlocks" not in session:
        session["stage_unlocks"] = dict(DEFAULT_STAGE_UNLOCKS)

    # Grab current stage + label so we can show them in the template
    current_stage = session.get("currentStage", 1)
    #st_label = STAGE_INFO.get(current_stage, {}).get("label", "Unknown")

    if request.method == "POST" and "update_stage_unlocks" in request.form:
        su = session.get("stage_unlocks", {})
        for i in range(1, 7):
            key = f"stage_unlock_{i}"
            su[i] = request.form.get(key, "").strip()
        session["stage_unlocks"] = su
        log_message("SYSTEM: Stage unlock text updated.")
        return redirect(url_for("interaction"))

    return render_template("stage_unlocks.html",
        stage_unlocks=session["stage_unlocks"],
        current_stage=current_stage,
        #stage_label=st_label,
        title="Stage Unlocks"
    )

@app.route("/gallery")
@login_required
def gallery():
    saved_images = session.get("saved_images", [])
    return render_template("gallery.html", images=saved_images)

@app.route("/gallery_image/<int:index>")
@login_required
def gallery_image(index):
    saved_images = session.get("saved_images", [])
    import base64
    if 0 <= index < len(saved_images):
        img_data = base64.b64decode(saved_images[index]["image_data"])
        return img_data, {'Content-Type': 'image/jpeg'}
    return "Image not found", 404

@app.route("/delete_gallery_image/<int:index>")
@login_required
def delete_gallery_image(index):
    saved_images = session.get("saved_images", [])
    if 0 <= index < len(saved_images):
        saved_images.pop(index)
        session["saved_images"] = saved_images
        flash("Image deleted successfully!", "success")
    return redirect(url_for("gallery"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
