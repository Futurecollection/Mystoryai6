import os
import replicate
import requests
import random
import datetime

import google.generativeai as genai
from flask import (
    Flask, request, render_template,
    session, redirect, url_for, send_file, flash
)
from flask_session import Session
from functools import wraps
from supabase import create_client, Client

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "abc123supersecret")  # Change this in production!
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./.flask_sess"
app.config["SESSION_PERMANENT"] = False
Session(app)

os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

############################################################################
# Initialize Supabase Client for Authentication
############################################################################
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

############################################################################
# Login Required Decorator
############################################################################
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login_route"))
        return f(*args, **kwargs)
    return decorated_function

############################################################################
# 1) Initialize Gemini + Replicate
############################################################################

from google.generativeai.types import HarmCategory, HarmBlockThreshold

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-2.0-flash-exp')

safety_settings = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
replicate.client.api_token = REPLICATE_API_TOKEN

############################################################################
# 2) Stage Info & Requirements
############################################################################

STAGE_INFO = {
    1: {"label": "Strangers", "desc": "They barely know each other."},
    2: {"label": "Casual Acquaintances", "desc": "Superficial chatting, no real depth yet."},
    3: {"label": "Comfortable", "desc": "Sharing moderate personal info, plan small outings."},
    4: {"label": "Close", "desc": "Frequent contact, emotional trust, safe time alone together."},
    5: {"label": "Serious Potential", "desc": "Openly affectionate, discussing future possibilities."},
    6: {"label": "Committed Relationship", "desc": "Life partners with strong devotion, shared long-term goals, can be sexually intimate."}
}

STAGE_REQUIREMENTS = {
    1: 0,
    2: 2,
    3: 5,
    4: 9,
    5: 15,
    6: 20
}

DEFAULT_STAGE_UNLOCKS = {
    1: "Basic intros, no perks",
    2: "Casual jokes, mild flirting possible,",
    3: "Comfortable enough to ask personal questions",
    4: "Deeper trust, hugging/cuddling possible",
    5: "Serious romance, discussing future plans",
    6: "Fully committed, sharing a life together, will be sexually intimate, NPC can initiate sexual intimacy "
}

GENERATED_IMAGE_PATH = "output.jpg"

############################################################################
# 3) Dropdown Options
############################################################################

USER_NAME_OPTIONS = ["John","Michael","David","Chris","James","Alex","Nick","Adam","Andrew","Jason","Emma","Sarah","Jessica","Emily","Sophie","Anna","Rachel","Lisa","Maria","Ashley","Other"]
USER_AGE_OPTIONS = ["20","25","30","35","40","45"]

NPC_NAME_OPTIONS = ["Emily","Sarah","Lisa","Anna","Mia","Sophia","Grace","Chloe","Emma","Isabella","James","Michael","William","Alexander","Daniel","David","Joseph","Thomas","Christopher","Matthew","Other"]
NPC_AGE_OPTIONS = ["20","25","30","35","40","45"]
NPC_GENDER_OPTIONS = ["Female","Male","Non-binary","Other"]
HAIR_STYLE_OPTIONS = ["Short","Medium Length","Long","Bald","Ponytail","Braided","Bun","Messy Bun","Fade Cut","Crew Cut","Slicked Back","Undercut","Quiff","Textured Crop","Side Part","Messy Spikes","Other"]
BODY_TYPE_OPTIONS = ["Athletic","Muscular","Tall & Broad","Lean & Toned","Average Build","Rugby Build","Swimmer's Build","Basketball Build","Other"]
HAIR_COLOR_OPTIONS = ["Blonde","Brunette","Black","Red","Brown","Grey","Dyed (Blue/Pink/etc)"]
NPC_PERSONALITY_OPTIONS = [
  "Flirty","Passionate","Confident","Protective","Intellectual","Charming","Ambitious","Professional",
  "Playful","Mysterious","Gentle","Athletic","Dominant","Reserved","Witty","Supportive","Other"
]
CLOTHING_OPTIONS = [
  "Red Summer Dress","Blue T-shirt & Jeans","Black Evening Gown",
  "Green Hoodie & Leggings","White Blouse & Dark Skirt","Business Attire",
  "Grey Sweater & Jeans","Pink Casual Dress","Suit & Tie","Leather Jacket & Dark Jeans",
  "Button-up Shirt & Chinos","Tank Top & Shorts","Polo & Khakis","Athletic Wear",
  "Blazer & Fitted Pants","Denim Jacket & White Tee","Other"
]
OCCUPATION_OPTIONS = [
  "College Student","School Teacher","Librarian","Office Worker","Freelance Artist","Bartender",
  "Travel Blogger","Ex-Military","Nurse","Startup Founder","CEO","Investment Banker",
  "Professional Athlete","Doctor","Firefighter","Police Detective","Personal Trainer",
  "Musician","Chef","Architect","Tech Executive","Business Consultant","Other"
]
CURRENT_SITUATION_OPTIONS = [
  "Recently Broke Up","Recovering from Divorce","Single & Looking",
  "New in Town","Trying Online Dating","Hobby Enthusiast","Other"
]
ENVIRONMENT_OPTIONS = [
  "Cafe","Library","Gym","Beach","Park","Nightclub","Airport Lounge",
  "Music Festival","Restaurant","Mountain Resort"
]
ENCOUNTER_CONTEXT_OPTIONS = [
  "First date","Accidental meeting","Haven't met yet","Group activity","Work-related encounter","Matching on Tinder","Other"
]
ETHNICITY_OPTIONS = [
    "American (Black)","American (White)","Hispanic","Australian",
    "British","Irish","Scottish","Welsh",
    "French","German","Dutch","Danish","Norwegian","Swedish",
    "Italian","Greek","Spanish","Portuguese",
    "Russian","Ukrainian","Polish","Czech","Slovak","Croatian","Serbian",
    "Chinese","Japanese","Korean","Vietnamese","Thai",
    "Indian","Pakistani","Filipino",
    "Brazilian","Turkish","Middle Eastern","Other"
]

############################################################################
# 4) Build Personalization String
############################################################################

def build_personalization_string():
    user_data = (
        f"USER:\n"
        f"  Name: {session.get('user_name','?')}\n"
        f"  Age: {session.get('user_age','?')}\n"
        f"  Background: {session.get('user_background','?')}\n"
    )
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
    return user_data + npc_data + env_data

############################################################################
# 5) Utility Helpers
############################################################################

def merge_dd(form, dd_key, cust_key):
    dd_val = form.get(dd_key, "").strip()
    cust_val = form.get(cust_key, "").strip()
    return cust_val if cust_val else dd_val

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

def log_message(msg):
    logs = session.get("interaction_log", [])
    logs.append(msg)
    session["interaction_log"] = logs

def handle_image_generation(prompt_text, force_new_seed=False):
    if session.get("image_generated_this_turn", False):
        log_message("[SYSTEM] Attempted second image generation this turn, blocked.")
        return None

    safety_prompt = f"""
Analyze this image generation prompt.
REJECT ONLY if the prompt contains:
- Characters under 20 years old
- References to minors or teenagers
- High school settings
- Age-play scenarios

NOTE: Adult sexual content and college settings are explicitly allowed for characters 20+ years old.

Prompt to check: {prompt_text}

Return only "ALLOW" or "REJECT"
"""
    chat = model.start_chat()
    validation = chat.send_message(safety_prompt, safety_settings=safety_settings)
    if validation.text.strip().upper() != "ALLOW":
        log_message("[SYSTEM] WARNING: AI detected age-restricted content. Generation blocked.")
        session["scene_image_prompt"] = "⚠️ ERROR: AI detected age-restricted content. Please edit and try again."
        return None

    if not prompt_text:
        prompt_text = "(No prompt text)"

    existing_seed = session.get("scene_image_seed")
    if not force_new_seed and existing_seed:
        seed_used = existing_seed
        log_message("SYSTEM: Re-using old seed => " + str(existing_seed))
    else:
        seed_used = random.randint(100000, 999999)
        if force_new_seed:
            log_message("SYSTEM: user requested new random => " + str(seed_used))
        else:
            log_message("SYSTEM: No existing seed => random => " + str(seed_used))

    url = generate_flux_image_safely(prompt_text, seed=seed_used)
    _save_image(url)
    session["scene_image_prompt"] = prompt_text
    session["scene_image_url"] = url
    session["scene_image_seed"] = seed_used
    session["image_generated_this_turn"] = True

    log_message(f"Scene Image Prompt => {prompt_text}")
    log_message(f"Image seed={seed_used}")
    return url

############################################################################
# 6) Interpret NPC State
############################################################################

def interpret_npc_state(affection, trust, npc_mood, current_stage, last_user_action, full_history=""):
    stage_label = STAGE_INFO[current_stage]["label"]
    stage_desc = STAGE_INFO[current_stage]["desc"]
    personalization = build_personalization_string()

    age_keywords = ["teen", "teenage", "underage", "minor", "child", "kid", "highschool", "high school", "18 year"]
    if any(keyword in last_user_action.lower() for keyword in age_keywords):
        return """AFFECT_CHANGE_FINAL: -5.0
NARRATION: ⚠️ WARNING: This system does not allow any content involving minors or characters under 20 years old. Please ensure all characters are explicitly adults over 20.
IMAGE_PROMPT: Portrait photo of a warning sign"""

    system_instructions = f"""
You are a third-person descriptive erotic romance novel narrator.

CRITICAL AGE RESTRICTION:
- All characters must be explicitly adults over 20 years old

SPECIAL INSTRUCTIONS:
1) If the user's message starts with "OOC", treat everything after it as a direct instruction
   for how you should shape the next story beat or NPC response. Follow these OOC directions
   while staying within the relationship stage limits.
2) If the scene involves phone texting or the NPC sends emojis, use the actual emoji characters 
   (e.g., 😛) rather than describing them in words.

For each user action:
1) AFFECT_CHANGE_FINAL => net affection shift (-2.0 to +2.0)
2) NARRATION => narrates and describes the story and also creates the NPC reaction (speech/dialogue, 
   actions, noises, gestures) and describes the environment 
   (about 200-300 words can be separate paragraphs)
3) IMAGE_PROMPT => single sentence referencing the NPC's age/ethnicity/bodytype/hair colour/style, outfit, environment

Output exactly (no extra lines):
AFFECT_CHANGE_FINAL: ...
NARRATION: ...
IMAGE_PROMPT: ...

Background (do not contradict):
{personalization}

Relationship Stage={current_stage} ({stage_label})
{stage_desc}

Stats: Affection={affection}, Trust={trust}, Mood={npc_mood}
"""

    user_text = f"USER ACTION: {last_user_action}\nPREVIOUS_LOG:\n{full_history}"

    resp = model.generate_content(
        f"{system_instructions}\n\n{user_text}",
        generation_config={"temperature": 0.9},
        safety_settings=safety_settings
    )

    return resp.text.strip()

############################################################################
# 7) Stage Checker
############################################################################

def check_stage_up_down(new_aff):
    cur_stage = session.get("currentStage", 1)
    req = STAGE_REQUIREMENTS[cur_stage]
    if new_aff < req:
        new_st = 1
        for s, needed in STAGE_REQUIREMENTS.items():
            if new_aff >= needed:
                new_st = max(new_st, s)
        session["currentStage"] = new_st
    else:
        while session["currentStage"] < 6:
            nxt = session["currentStage"] + 1
            if new_aff >= STAGE_REQUIREMENTS[nxt]:
                session["currentStage"] = nxt
            else:
                break

    st = session["currentStage"]
    if st < 6:
        session["nextStageThreshold"] = STAGE_REQUIREMENTS[st+1]
    else:
        session["nextStageThreshold"] = 999

############################################################################
# 8) Replicate / Image Functions
############################################################################

def _save_image(url):
    r = requests.get(url)
    with open(GENERATED_IMAGE_PATH, "wb") as f:
        f.write(r.content)

def generate_flux_image_safely(prompt, seed=None):
    final_prompt = f"Portrait photo, {prompt}"
    replicate_input = {
        "prompt": final_prompt,
        "raw": True,
        "safety_tolerance": 6,
        "disable_safety_checker": True,
        "output_quality": 100
    }
    if seed is not None:
        replicate_input["seed"] = seed

    print(f"[DEBUG] replicate => prompt={final_prompt}, seed={seed}")
    result = replicate.run("black-forest-labs/flux-schnell", input=replicate_input)
    if isinstance(result, list):
        if result:
            return str(result[-1])
        else:
            return "No URL returned??"
    else:
        return str(result)

############################################################################
# 9) GPT-based Scene Prompt
############################################################################

def gpt_scene_image_prompt(full_history):
    npc_age = session.get("npc_age", "?")
    npc_gender = session.get("npc_gender", "?") 
    npc_eth = session.get("npc_ethnicity", "?")
    npc_body = session.get("npc_body_type", "?")
    npc_hair_color = session.get("npc_hair_color", "?")
    npc_hair_style = session.get("npc_hair_style", "?")
    npc_clothing = session.get("npc_clothing", "?")
    env_loc = session.get("environment", "?")
    npc_mood = session.get("npcMood", "Neutral")
    current_stage = session.get("currentStage", 1)

    history_lines = full_history.split("\n")[-5:]
    recent_context = "\n".join(history_lines)

    prompt = f"""
You are a creative scene image prompt generator.
Create a vivid single-sentence photographic prompt that captures the current moment.

CHARACTER DETAILS:
- Physical: {npc_gender}, age {npc_age}, {npc_eth} with {npc_body} build
- Hair: {npc_hair_color}, {npc_hair_style} style
- Outfit: {npc_clothing}
- Current Mood: {npc_mood}

SETTING:
- Location: {env_loc}
- Relationship Stage: {current_stage}

RECENT CONTEXT:
{recent_context}

Generate one descriptive scene line that reflects the current emotional state and physical setting:"""

    chat = model.start_chat()
    resp = chat.send_message(
        prompt,
        generation_config={"temperature": 0.7},
        safety_settings=safety_settings
    )

    final_line = resp.text.strip()
    print("[DEBUG] gpt_scene_image_prompt =>", final_line)
    return final_line

############################################################################
# 10) Flask Routes
############################################################################

# --- Public Routes ---
@app.route("/")
def main_home():
    return render_template("home.html", title="Destined Encounters")

@app.route("/about")
def about():
    return render_template("about.html", title="About/Help")

# --- Authentication Routes ---
@app.route("/login", methods=["GET", "POST"])
def login_route():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            user = response.user
            user_id = user.id
            session_data = {
                "logged_in": True,
                "user_email": user.email,
                "access_token": response.session.access_token,
                "user_id": user_id
            }
            
            # Store session in Supabase
            supabase.table("user_sessions").upsert({
                "user_id": user_id,
                "session_data": session_data,
                "last_activity": datetime.datetime.utcnow().isoformat()
            }).execute()
            
            # Also store in Flask session
            session.update(session_data)
            flash("Logged in successfully!", "success")
            return redirect(url_for("personalize"))
        except Exception as e:
            error_msg = str(e)
            if not error_msg:
                error_msg = "Invalid credentials"
            flash(f"Login failed: {error_msg}", "danger")
            return redirect(url_for("login_route"))
    return render_template("login.html", title="Login")

@app.route("/register", methods=["GET", "POST"])
def register_route():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            response = supabase.auth.sign_up({"email": email, "password": password})
            error = None
        except Exception as e:
            error = {"message": str(e)}
        if error:
            flash("Registration failed: " + error["message"], "danger")
            return redirect(url_for("register_route"))
        else:
            flash("Registration successful! Check your email for confirmation, then log in.", "success")
            return redirect(url_for("login_route"))
    return render_template("register.html", title="Register")

@app.route("/logout")
def logout_route():
    if session.get("user_id"):
        try:
            # Clear Supabase session
            supabase.table("user_sessions").delete().eq("user_id", session["user_id"]).execute()
        except Exception as e:
            print("Error clearing Supabase session:", str(e))
    
    # Clear Flask session
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("main_home"))

# --- Protected Routes ---
@app.route("/restart")
@login_required
def restart():
    session.clear()
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    session["stage_unlocks"] = dict(DEFAULT_STAGE_UNLOCKS)
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
            session["npc_instructions"] = """[Male-specific instructions ...]"""
        else:
            session["npc_instructions"] = """[Female-specific instructions ...]"""
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
        session["image_generated_this_turn"] = False
        return redirect(url_for("interaction"))
    else:
        return render_template("personalize.html",
            title="Personalizations",
            user_name_options=USER_NAME_OPTIONS,
            user_age_options=USER_AGE_OPTIONS,
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
            ethnicity_options=ETHNICITY_OPTIONS
        )

@app.route("/mid_game_personalize", methods=["GET", "POST"])
@login_required
def mid_game_personalize():
    if request.method == "POST" and "update_npc" in request.form:
        update_npc_info(request.form)
        log_message("SYSTEM: NPC personalizations updated mid-game.")
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
        dice_val = session.get("dice_debug_roll", "(none)")
        outcome_val = session.get("dice_debug_outcome", "(none)")
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
            dice_roll_dbg=dice_val,
            dice_outcome_dbg=outcome_val,
            interaction_log=interaction_log,
            stage_unlocks=stage_unlocks,
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
            ethnicity_options=ETHNICITY_OPTIONS
        )
    else:
        if "submit_action" in request.form:
            user_action = request.form.get("user_action", "").strip() or "(no action)"
            affection = session.get("affectionScore", 0.0)
            trust = session.get("trustScore", 5.0)
            mood = session.get("npcMood", "Neutral")
            cstage = session.get("currentStage", 1)
            log_message(f"User: {user_action}")
            full_history = "\n".join(session.get("interaction_log", []))
            result_text = interpret_npc_state(
                affection=affection,
                trust=trust,
                npc_mood=mood,
                current_stage=cstage,
                last_user_action=user_action,
                full_history=full_history
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
            session["image_generated_this_turn"] = False
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
        elif "do_generate_flux" in request.form:
            prompt_text = request.form.get("scene_image_prompt", "").strip() or "(No prompt text)"
            handle_image_generation(prompt_text, force_new_seed=False)
            return redirect(url_for("interaction"))
        elif "new_seed" in request.form:
            prompt_text = request.form.get("scene_image_prompt", "").strip() or "(No prompt text)"
            handle_image_generation(prompt_text, force_new_seed=True)
            return redirect(url_for("interaction"))
        else:
            return "Invalid submission in /interaction", 400

@app.route("/view_image")
@login_required
def view_image():
    return send_file(GENERATED_IMAGE_PATH, mimetype="image/jpeg")

############################################################################
# 11) Full Story and Erotica Routes
############################################################################

@app.route("/full_story")
@login_required
def full_story():
    logs = session.get("interaction_log", [])
    story_lines = []
    for line in logs:
        if line.startswith("NARRATION => "):
            story_lines.append(line.replace("NARRATION => ", "", 1))
        elif line.startswith("User: "):
            story_lines.append(line.replace("User: ", "", 1))
    return render_template("full_story.html", lines=story_lines, title="Full Story So Far")

@app.route("/continue_erotica", methods=["POST"])
@login_required
def continue_erotica():
    previous_text = request.form.get("previous_text", "").strip()
    continue_prompt = f"""
You are continuing an erotic story. Pick up exactly where this left off and continue
the scene for another 600-900 words. Maintain the same tone, characters, and setting.
Keep the story cohesive and flowing naturally from the previous text.

PREVIOUS TEXT:
{previous_text}

Now continue the story from this exact point (600-900 more words):"""
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

STORY LOG:
{full_narration}

Now produce a single detailed erotica story (600-900 words) that brings both characters fully to life.
Allowed Explicitness:
* You may describe sexual acts in graphic detail, provided they depict consensual adult activity
* You may include language depicting nudity, arousal, orgasm, and explicit bodily contact
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
                         title="Stage Unlocks")

def validate_age_content(text):
    age_keywords = ["teen", "teenage", "underage", "minor", "child", "kid", "highschool", "high school", "18 year", "19 year"]
    return any(keyword in text.lower() for keyword in age_keywords)

@app.route("/generate_scene_prompt", methods=["POST"])
@login_required
def generate_scene_prompt():
    logs = session.get("interaction_log", [])
    full_history = "\n".join(logs)
    print("[DEBUG] Attempting to generate scene prompt")
    try:
        auto_prompt = gpt_scene_image_prompt(full_history)
        print("[DEBUG] Generated prompt:", auto_prompt)
        if not auto_prompt:
            raise ValueError("Generated prompt was empty")
        if validate_age_content(auto_prompt):
            log_message("[SYSTEM] WARNING: Generated prompt contained age-restricted content.")
            session["scene_image_prompt"] = "⚠️ ERROR: Generated prompt contained age-restricted terms. Please try again or edit manually."
            return redirect(url_for("interaction"))
        session["scene_image_prompt"] = auto_prompt
        log_message(f"[AUTO Scene Prompt] => {auto_prompt}")
    except Exception as e:
        print("[DEBUG] Error generating prompt:", str(e))
        log_message(f"[SYSTEM] Error generating scene prompt: {str(e)}")
        session["scene_image_prompt"] = "⚠️ ERROR: Failed to generate prompt. Please try again."
    return redirect(url_for("interaction"))

PREDEFINED_BIOS = {
    "Lucy": "First date with Lucy",
    "Grand Aurora Hotel Resort and Spa": "Grand Aurora Hotel Resort and Spa",
    "Fifty Shades of Grey": "Fifty Shades of Grey Roleplay"
}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)