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
from datetime import datetime
import base64

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

# We allow up to 8192 tokens for longer outputs
safety_settings = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}
generation_config = {
    "temperature": 0.5,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192
}

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
        with open(GENERATED_IMAGE_PATH, "wb") as f:
            f.write(result.read())
        return
    if isinstance(result, list) and result:
        final_item = result[-1]
        if isinstance(final_item, str):
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

def validate_age_content(text: str) -> tuple[bool, str]:
    age_keywords = [
        "teen", "teenage", "underage", "minor", "child", "young", "youth",
        "kid", "highschool", "high school", "18 year", "19 year", "juvenile",
        "adolescent", "preteen", "pre-teen", "schoolgirl", "schoolboy", "jailbait"
    ]
    text_lower = text.lower()
    for k in age_keywords:
        if k in text_lower:
            return True, f"Detected restricted age-related term: '{k}'"

    try:
        system_prompt = """
        You are an AI content validator. Your task is to check if text contains any references 
        to underage individuals (anyone under 20 years old). Respond with:
        BLOCKED: [reason] - if the text contains any underage references 
        ALLOWED - if the text only contains adult (20+) references
        """

        chat = model.start_chat()
        response = chat.send_message(
            f"{system_prompt}\n\nTEXT TO CHECK: {text}",
            generation_config={"temperature": 0.1},
            safety_settings=safety_settings
        )

        result = response.text.strip().upper()
        if result.startswith("BLOCKED:"):
            reason = result.split(":", 1)[1].strip()
            return True, f"AI detected potential underage content: {reason}"
        return False, "Content approved"
    except Exception as e:
        print(f"[ERROR] LLM age validation failed: {e}")
        return False, "Content approved (LLM check failed, using keyword check only)"

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

def build_initial_npc_memory() -> str:
    """Creates a short snippet describing the NPC as initial memory."""
    name = session.get('npc_name','Unknown')
    gender = session.get('npc_gender','?')
    age = session.get('npc_age','?')
    personality = session.get('npc_personality','?')
    clothing = session.get('npc_clothing','?')
    occupation = session.get('npc_occupation','?')

    return (f"Initial memory about {name}: " 
            f"{gender}, age {age}, personality={personality}, clothing={clothing}, occupation={occupation}.")

# --------------------------------------------------------------------------
# interpret_npc_state => LLM
# --------------------------------------------------------------------------
@retry_with_backoff(retries=3, backoff_in_seconds=1)
def process_npc_thoughts(last_user_action: str, narration: str) -> tuple[str, str]:
    npc_name = session.get('npc_name', '?')
    prev_thoughts = session.get("npcPrivateThoughts", "(none)")
    prev_memories = session.get("npcBehavior", "(none)")

    npc_personal_data = build_personalization_string()

    system_prompt = f"""
You are analyzing {npc_name}'s internal thoughts and memories during an interaction.

We have the NPC's overall personality traits, backstory, relationship goals, etc.:
{npc_personal_data}

Focus on how {npc_name}'s emotional state, private reactions, and key memories:
 - Reflect their personality and background
 - Align with the last user action and the scene narration
 - Are influenced by their existing instructions or relationship goal
 - **Only store SIGNIFICANT or pivotal knowledge** about the user or the NPC's identity/history. 
   Minor ephemeral details or small talk should NOT become permanent memory.

PREVIOUS THOUGHTS: {prev_thoughts}
PREVIOUS MEMORIES: {prev_memories}

LAST USER ACTION: {last_user_action}
SCENE NARRATION: {narration}

Return EXACTLY two lines:
Line 1 => PRIVATE_THOUGHTS: ... 
Line 2 => MEMORY_UPDATE: ... (or "(no significant update)" if no new important memory)
"""

    chat = model.start_chat()
    response = chat.send_message(
        system_prompt,
        generation_config=generation_config,
        safety_settings=safety_settings
    )

    thoughts = ""
    memory = ""
    for ln in response.text.strip().split("\n"):
        if ln.startswith("PRIVATE_THOUGHTS:"):
            thoughts = ln.split(":", 1)[1].strip()
        elif ln.startswith("MEMORY_UPDATE:"):
            memory = ln.split(":", 1)[1].strip()

    return thoughts, memory

def interpret_npc_state(affection: float, trust: float, npc_mood: str,
                        current_stage: int, last_user_action: str) -> str:
    prepare_history()
    conversation_history = session.get("interaction_log", [])
    combined_history = "\n".join(conversation_history)

    prev_thoughts = session.get("npcPrivateThoughts", "(none)")
    prev_memories = session.get("npcBehavior", "(none)")

    if not last_user_action.strip():
        last_user_action = "OOC: Continue the scene"

    stage_desc = session.get("stage_unlocks", {}).get(current_stage, "")
    personalization = build_personalization_string()
    personalization += f"""
PREVIOUS THOUGHTS & MEMORIES:
Previous Thoughts: {prev_thoughts}
Previous Memories: {prev_memories}
"""

    # We also demand at least 300 characters in the narration
    system_instructions = f"""
You are a third-person descriptive erotic romance novel narrator.

CRITICAL AGE RESTRICTION:
- All characters must be explicitly adults over 20 years old.

SPECIAL INSTRUCTIONS:
1) Natural Conversation Flow:
   - Feel organic and natural, not a rigid pattern
   - NPC can expand on topics 
   - Vary questions/statements/emotional expressions

2) For OOC interactions:
   - "OOC:" is meta

3) Use actual emojis if texting

Relationship Stage={current_stage} ({stage_desc})
Stats: Affection={affection}, Trust={trust}, Mood={npc_mood}

Background (do not contradict):
{personalization}

Return EXACTLY four lines:
Line 1 => AFFECT_CHANGE_FINAL: (float between -2.0 and +2.0)
Line 2 => NARRATION: (must be at least 300 characters describing NPC's reaction, dialogue, actions)
Line 3 => PRIVATE_THOUGHTS: (NPC's internal thoughts)
Line 4 => MEMORY_UPDATE: (key events to remember)
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
PRIVATE_THOUGHTS: (System Error)
MEMORY_UPDATE: (System Error)
"""
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

    # Make separate LLM call for thoughts and memories
    thoughts_txt, memory_txt = process_npc_thoughts(last_user_action, narration_txt)

    existing_thoughts = session.get("npcPrivateThoughts", "")
    existing_memories = session.get("npcBehavior", "")

    if existing_thoughts.strip().lower() == "(none)":
        updated_thoughts = thoughts_txt
    else:
        updated_thoughts = f"{existing_thoughts}\n• {thoughts_txt}"

    memory_txt_lower = memory_txt.strip().lower()
    if memory_txt_lower.startswith("(no significant update)") or not memory_txt_lower:
        updated_memories = existing_memories
    else:
        if existing_memories.strip().lower() == "(none)":
            updated_memories = memory_txt
        else:
            updated_memories = f"{existing_memories}\n• {memory_txt}"

    session["npcPrivateThoughts"] = updated_thoughts
    session["npcBehavior"] = updated_memories

    return f"""AFFECT_CHANGE_FINAL: {affect_delta}
NARRATION: {narration_txt}
PRIVATE_THOUGHTS: {thoughts_txt}
MEMORY_UPDATE: {memory_txt}"""

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
# handle_image_generation_from_prompt
# --------------------------------------------------------------------------
def handle_image_generation_from_prompt(prompt_text: str, force_new_seed: bool = False,
                                        model_type: str = "flux", scheduler: str = None,
                                        steps: int = None, cfg_scale: float = None,
                                        save_to_gallery: bool = False):
    gen_count = session.get("image_gen_count", 0)
    if gen_count >= 5:
        log_message("[SYSTEM] Image generation limit reached (5 per story)")
        return None
    is_blocked, reason = validate_age_content(prompt_text)
    if is_blocked:
        log_message("[SYSTEM] Blocked image generation due to potential underage content")
        session["scene_image_prompt"] = f"🚫 IMAGE BLOCKED: {reason}"
        return None
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
        result = generate_flux_image_safely(prompt_text, seed=seed_used)

    if not result:
        log_message("[SYSTEM] replicate returned invalid/empty result.")
        return None

    _save_image(result)
    session["scene_image_url"] = url_for('view_image')
    session["scene_image_prompt"] = prompt_text
    session["scene_image_seed"] = seed_used

    session["image_gen_count"] = gen_count + 1
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
NPC_NAME_OPTIONS = [
    "Emily","Sarah","Lisa","Anna","Mia","Sophia","Grace","Chloe","Emma","Isabella",
    "James","Michael","William","Alexander","Daniel","David","Joseph","Thomas","Christopher","Matthew",
    "Other"
]
NPC_AGE_OPTIONS = ["20","25","30","35","40","45"]
NPC_GENDER_OPTIONS = ["Female","Male","Non-binary","Other"]

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

# --------------------------------------------------------------------------
# Routing
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
            flash("Registration successful! You can now log in.", "success")
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
    user_id = session.get("user_id")
    user_email = session.get("user_email")
    access_token = session.get("access_token")
    logged_in = session.get("logged_in")

    session.clear()

    session["user_id"] = user_id
    session["user_email"] = user_email
    session["access_token"] = access_token
    session["logged_in"] = logged_in

    session["stage_unlocks"] = dict(DEFAULT_STAGE_UNLOCKS)
    session["image_gen_count"] = 0
    flash("Story restarted! You can create new characters.", "info")
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
            session["npc_instructions"] = """You are an ideal female AI companion... (original instructions)"""

        # Initialize stats & story
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

        # Seed initial memory
        session["npcBehavior"] = build_initial_npc_memory()

        flash("Personalization saved. Let’s begin!", "success")
        return redirect(url_for("interaction"))
    else:
        return render_template(
            "personalize.html",
            title="Personalizations",
            user_name_options=["John","Michael","David","Chris","James","Alex","Emily","Olivia","Sophia","Emma"],
            user_age_options=["20","25","30","35","40","45"],
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

            # Auto-generate scene prompt after each action
            model_type = session.get("last_model_choice", "flux")
            prompt_text = generate_image_prompt_for_scene(model_type)
            session["scene_image_prompt"] = prompt_text

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
            if not os.path.exists(GENERATED_IMAGE_PATH):
                flash("No image to save!", "warning")
                return redirect(url_for("interaction"))

            saved_images = session.get("saved_images", [])
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
        else:
            story_lines.append(line)
    return render_template("full_story.html", lines=story_lines, title="Full Story So Far")

# --------------------------------------------------------------------------
# Chunk-based /generate_erotica & /continue_erotica
# --------------------------------------------------------------------------
@app.route("/generate_erotica", methods=["POST"])
@login_required
def generate_erotica():
    full_narration = build_full_narration_from_logs()
    if not full_narration.strip():
        flash("No narration to rewrite.", "danger")
        return redirect(url_for("full_story"))

    session["erotica_chunks"] = chunk_text(full_narration, chunk_size=3000)
    session["current_chunk_index"] = 0
    session["erotica_text_so_far"] = ""

    i = session["current_chunk_index"]
    chunks = session["erotica_chunks"]
    if i >= len(chunks):
        flash("All chunks processed. Full erotica below.", "info")
        erotica_text = session.get("erotica_text_so_far", "")
        return render_template("erotica_story.html", erotica_text=erotica_text, title="Generated Erotica")

    current_chunk = chunks[i]
    custom_prompt = request.form.get("erotica_prompt", "").strip()
    previous_text = session.get("erotica_text_so_far", "")

    new_rewrite = generate_erotica_text(
        narration=current_chunk,
        custom_prompt=custom_prompt,
        previous_text=previous_text
    )
    updated_erotica = previous_text + "\n\n"+ new_rewrite if previous_text else new_rewrite
    session["erotica_text_so_far"] = updated_erotica
    session["current_chunk_index"] = i + 1

    return render_template(
        "erotica_story.html",
        erotica_text=updated_erotica,
        title="Generated Erotica (Chunk 1)" if i == 0 else f"Generated Erotica (Chunk {i+1})"
    )

@app.route("/continue_erotica", methods=["POST"])
@login_required
def continue_erotica():
    if "erotica_chunks" not in session:
        flash("No chunk session found. Click 'Generate Erotica' first.", "info")
        return redirect(url_for("full_story"))

    chunks = session["erotica_chunks"]
    i = session["current_chunk_index"]
    if i >= len(chunks):
        flash("All chunks processed. You're at the end!", "info")
        erotica_text = session.get("erotica_text_so_far", "")
        return render_template("erotica_story.html", erotica_text=erotica_text, title="All Chunks Complete")

    current_chunk = chunks[i]
    previous_text = session.get("erotica_text_so_far", "")
    custom_prompt = request.form.get("continue_prompt", "").strip()

    new_rewrite = generate_erotica_text(
        narration=current_chunk,
        custom_prompt=custom_prompt,
        previous_text=previous_text
    )
    updated_erotica = previous_text + "\n\n" + new_rewrite
    session["erotica_text_so_far"] = updated_erotica
    session["current_chunk_index"] = i + 1

    return render_template(
        "erotica_story.html",
        erotica_text=updated_erotica,
        title=f"Generated Erotica (Chunk {i+1})"
    )

@app.route("/stage_unlocks", methods=["GET", "POST"])
@login_required
def stage_unlocks():
    if "stage_unlocks" not in session:
        session["stage_unlocks"] = dict(DEFAULT_STAGE_UNLOCKS)

    current_stage = session.get("currentStage", 1)

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
    if 0 <= index < len(saved_images):
        image_record = saved_images[index]
        image_b64 = image_record["image_data"]
        image_bytes = base64.b64decode(image_b64)
        return image_bytes, {'Content-Type': 'image/jpeg'}
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

# --------------------------------------------------------------------------
# Manually Updating NPC Memory
# --------------------------------------------------------------------------
@app.route("/manual_npc_update", methods=["GET", "POST"])
@login_required
def manual_npc_update():
    """
    Shows the NPC's current private thoughts & memories
    and allows the user to add more text to either field.
    """
    if request.method == "POST":
        new_text = request.form.get("new_text", "").strip()
        target = request.form.get("target", "thoughts")

        if not new_text:
            flash("No text provided to update NPC internal state.", "warning")
            return redirect(url_for("manual_npc_update"))

        if target == "memories":
            existing_memories = session.get("npcBehavior", "")
            if existing_memories.strip().lower() == "(none)":
                session["npcBehavior"] = new_text
            else:
                session["npcBehavior"] = existing_memories + f"\n• {new_text}"
            flash("Memory updated successfully!", "success")
        else:
            existing_thoughts = session.get("npcPrivateThoughts", "")
            if existing_thoughts.strip().lower() == "(none)":
                session["npcPrivateThoughts"] = new_text
            else:
                session["npcPrivateThoughts"] = existing_thoughts + f"\n• {new_text}"
            flash("Private thoughts updated successfully!", "success")

        return redirect(url_for("manual_npc_update"))
    else:
        # Show the current private thoughts & memories so the user can see them
        existing_thoughts = session.get("npcPrivateThoughts", "(none)")
        existing_memories = session.get("npcBehavior", "(none)")
        return render_template(
            "manual_npc_update.html",
            title="Manual NPC Update",
            current_thoughts=existing_thoughts,
            current_memories=existing_memories
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)