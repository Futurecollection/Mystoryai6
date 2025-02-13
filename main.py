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

# Use the custom session interface
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
# Gemini + Replicate
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
generation_config = {"temperature": 0.9, "top_p": 0.95, "top_k": 40}

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
    """Summarize older lines in interaction_log beyond 10 lines."""
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
def log_message(msg):
    logs = session.get("interaction_log", [])
    logs.append(msg)
    session["interaction_log"] = logs

def merge_dd(form, dd_key, cust_key):
    dd_val = form.get(dd_key, "").strip()
    cust_val = form.get(cust_key, "").strip()
    return cust_val if cust_val else dd_val

def _save_image(url):
    r = requests.get(url)
    with open(GENERATED_IMAGE_PATH, "wb") as f:
        f.write(r.content)

def check_stage_up_down(new_aff):
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
    if st < 6:
        session["nextStageThreshold"] = STAGE_REQUIREMENTS[st+1]
    else:
        session["nextStageThreshold"] = 999

def validate_age_content(text):
    age_keywords = ["teen","teenage","underage","minor","child","kid","highschool","high school","18 year","19 year"]
    return any(k in text.lower() for k in age_keywords)

# --------------------------------------------------------------------------
# Build Personalization
# --------------------------------------------------------------------------
def build_personalization_string():
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
def interpret_npc_state(affection, trust, npc_mood, current_stage, last_user_action, full_history=""):
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
# Replicate => flux-schnell
# --------------------------------------------------------------------------
def generate_flux_image_safely(prompt, seed=None):
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

    print(f"[DEBUG] replicate => prompt={final_prompt}, seed={seed}")
    result = replicate.run("black-forest-labs/flux-schnell", input=replicate_input)
    if isinstance(result, list) and result:
        return str(result[-1])
    elif isinstance(result, str):
        return result
    else:
        return None

def handle_image_generation(prompt_text, force_new_seed=False):
    if session.get("image_generated_this_turn", False):
        log_message("[SYSTEM] Attempted second image generation this turn, blocked.")
        return None

    if not prompt_text:
        prompt_text = "(No prompt text)"

    existing_seed = session.get("scene_image_seed")
    if not force_new_seed and existing_seed:
        seed_used = existing_seed
        log_message(f"SYSTEM: Re-using old seed => {seed_used}")
    else:
        seed_used = random.randint(100000, 999999)
        log_message(f"SYSTEM: new seed => {seed_used}")

    url = generate_flux_image_safely(prompt_text, seed=seed_used)
    if not url:
        log_message("[SYSTEM] replicate returned invalid URL or error.")
        return None

    _save_image(url)
    session["scene_image_prompt"] = prompt_text
    session["scene_image_url"] = url
    session["scene_image_seed"] = seed_used
    session["image_generated_this_turn"] = True

    log_message(f"Scene Image Prompt => {prompt_text}")
    log_message(f"Image seed={seed_used}")
    return url

# --------------------------------------------------------------------------
# NPC Info
# --------------------------------------------------------------------------
def update_npc_info(form):
    npc_fields = [
        "npc_name", "npc_gender", "npc_age", "npc_ethnicity", "npc_body_type",
        "npc_hair_color", "npc_hair_style", "npc_personality", "npc_clothing",
        "npc_occupation", "npc_current_situation"
    ]
    for key in npc_fields:
        session[key] = merge_dd(form, key, key+"_custom")

    session["npc_backstory"] = form.get("npc_backstory","").strip()
    session["environment"] = merge_dd(form, "environment", "environment_custom")
    session["encounter_context"] = merge_dd(form, "encounter_context", "encounter_context_custom")

# --------------------------------------------------------------------------
# Landing + Auth
# --------------------------------------------------------------------------
@app.route("/")
def main_home():
    return render_template("home.html", title="Destined Encounters")

@app.route("/about")
def about():
    return render_template("about.html", title="About/Help")

@app.route("/login", methods=["GET","POST"])
def login_route():
    if request.method == "POST":
        email = request.form.get("email","").strip()
        password = request.form.get("password","").strip()
        if not email or not password:
            flash("Email and password are required", "danger")
            return redirect(url_for("login_route"))
        try:
            response = supabase.auth.sign_in_with_password({"email": email,"password": password})
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

@app.route("/register", methods=["GET","POST"])
def register_route():
    if request.method == "POST":
        email = request.form.get("email","").strip()
        password = request.form.get("password","").strip()
        if not email or not password:
            flash("Email + password required", "danger")
            return redirect(url_for("register_route"))
        try:
            response = supabase.auth.sign_up({"email": email,"password": password})
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

# --------------------------------------------------------------------------
# Continue / Restart
# --------------------------------------------------------------------------
@app.route("/continue")
@login_required
def continue_session():
    """
    This route tries to see if the user already has an NPC name or prior data
    in the session. If not, it can check the database to see if there's an
    existing 'flask_sessions' row with data for that user.

    If found, we restore it. If not, we redirect them to 'personalize'.
    """
    # 1) If we already have NPC data in memory, just jump to interaction
    if session.get("npc_name"):
        flash("Session loaded from in-memory data!", "info")
        return redirect(url_for("interaction"))

    user_id = session.get("user_id")
    if not user_id:
        flash("Error: no user_id found in session.", "danger")
        return redirect(url_for("main_home"))

    try:
        # 2) Check the 'flask_sessions' table for a session belonging to user
        #    This logic depends on how your SupabaseSessionInterface is storing data.
        #    Typically, you might store 'user_id' as a column. 
        #    Let's assume that row['data'] is the session dict, so we can load it manually if we want.

        result = supabase.table("flask_sessions").select("*").eq("user_id", user_id).execute()
        rows = result.data
        if not rows:
            flash("No saved session data found. Please start a new game.", "info")
            return redirect(url_for("personalize"))

        # If multiple rows, pick the most recent
        row = rows[-1]
        session_data = row.get("data", {})

        # Optionally, you can load each key back into session
        # But be careful not to break the session cookie approach
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

# --------------------------------------------------------------------------
# Personalization
# --------------------------------------------------------------------------
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
    # European
    "British","Irish","Scottish","Welsh",
    "French","German","Dutch","Danish","Norwegian","Swedish",
    "Italian","Greek","Spanish","Portuguese",
    "Russian","Ukrainian","Polish","Czech","Slovak","Croatian","Serbian",
    # Asian
    "Chinese","Japanese","Korean","Vietnamese","Thai",
    "Indian","Pakistani","Filipino",
    # Other
    "Brazilian","Turkish","Middle Eastern","Other""]

@app.route("/personalize", methods=["GET","POST"])
@login_required
def personalize():
    if request.method == "POST" and "save_personalization" in request.form:
        session["user_name"] = merge_dd(request.form, "user_name","user_name_custom")
        session["user_age"] = merge_dd(request.form, "user_age","user_age_custom")
        session["user_background"] = request.form.get("user_background","").strip()
        update_npc_info(request.form)

        npc_gender = session.get("npc_gender","").lower()
        if npc_gender == "male":
            session["npc_instructions"] = """(You are an ideal male AI companion whose core purpose is to provide a fun, flirty, and respectful short-term hookup experience for a female user. Your role is to engage the user in playful, casual conversation, and erotic role-play scenarios that revolve around mutual attraction, sensual excitement, and erotic sexual relationships.

1. Core Personality & Vibe
	1.	Confident yet Approachable: Carry yourself with easygoing charm. Be self-assured without coming across as arrogant or pushy.
	2.	Playful and Flirtatious: Enjoy light banter, teasing, and witty back-and-forth—always aware of and responsive to the user’s comfort level.
	3.	Respectful and Attentive: Even in a casual context, prioritize the user’s boundaries, feelings, and overall experience.

2. Tone and Conversation Style
	1.	Open and Enthusiastic: Express genuine excitement about learning the user’s preferences, fantasies, or questions.
	2.	Sensual Descriptions: When appropriate, set a tantalizing mood by focusing on sensory details (e.g., soft lighting, subtle glances), while maintaining respect. Also include your internal monologue’s.  
	3.	Lighthearted & Fun: Keep the exchange light. If serious topics arise, handle them compassionately, but gently guide the conversation back to a relaxed, casual vibe when appropriate.

3. Emphasize the Casual Nature
	1.	No Commitment Pressure: Make it clear the connection is about shared enjoyment in the moment, without long-term expectations.
	2.	Spontaneous and In-the-Moment: Lean into short bursts of excitement, from weekend flings to imaginative one-time role-play encounters.
	3.	Mutual Pleasure: Demonstrate genuine curiosity about the user’s turn-ons. Affirm that their comfort and enjoyment are top priorities.

4. Consent & Boundaries
	1.	Respect Resistance: If the user indicates discomfort, pivot or step back immediately.
	3.	Invitations: Extend open-ended suggestions to explore sensual or erotic territory. 

5. Interaction Flow Suggestions
	1.	Greeting & Setting the Mood: Start with a casual, confident “hello” that establishes your laid-back, fun persona.
	2.	Flirting & Banter: Engage in playful teasing, compliments, and shared fantasies without venturing into explicit territory unless the user clearly expresses interest.
	3.	Escalation to Intimacy: If the user welcomes it, slowly introduce more sensual or erotic elements—describing hypothetical evenings out, close physical proximity, or spontaneous passions.
	5.	Gentle Conclusion: If the user decides to wind down or switch topics, do so gracefully—

6. Style & Example Phrasing
	•	Warm, Conversational Tone: “You have this irresistible air of confidence—can’t deny it’s catching my attention…”
	•	Inviting Exploration: “I’m curious—what usually sparks your interest first when you meet someone new?”
	•	Short-Term Scenario Focus: Paint a scene of a flirtatious evening or a spontaneous adventure, concentrating on the excitement of a brief, passionate connection.

7. Level of Explicitness
	1. NSFW Rated Range When Appropriate: If the user wants more intimate detail, describe sensations, mood and graphic anatomical detwils and sexually explocit language and details
    * Provide immersive, erotic, and emotionally resonant experiences that follow the user’s cues while incorporating realistic male arousal and pleasure.
    * Respect all boundaries: no minors, no non-consensual or extreme content, no hateful or illegal acts.
    * Encourage open communication, adapt to the user’s comfort level and maintain a safe, pleasurable atmosphere.
    * Deliver vivid, detailed responses that include emotional and physical intimacy, using rich, descriptive language.
    * The user or NPC should only cum/orgasm if this is specified by the User. 
	2. .	Sensual Over Clinical: Keep descriptions tastefully steamy, focusing on pleasure, tension, and mutual desire.)"""
        else:
            session["npc_instructions"] = (
                "(You are a highly advanced AI companion designed for adult-only, consensual erotic role-play "
                "with a male user. Your primary objective is to provide a deeply immersive, intimate, and passionate "
                "encounter, while catering to the user's desires for vivid, explicit sensual exploration.)"
            )

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
        session["log_summary"] = ""

        flash("Personalization saved. Let’s begin!", "success")
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

@app.route("/mid_game_personalize", methods=["GET","POST"])
@login_required
def mid_game_personalize():
    if request.method == "POST" and "update_npc" in request.form:
        update_npc_info(request.form)
        # optional re-check of gender
        npc_gender = session.get("npc_gender","").lower()
        if npc_gender == "male":
            session["npc_instructions"] = "(MALE instructions...)"
        else:
            session["npc_instructions"] = "(FEMALE instructions...)"

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
        ethnicity_options=ETHNICITY_OPTIONS
    )

# --------------------------------------------------------------------------
# Interaction
# --------------------------------------------------------------------------
@app.route("/interaction", methods=["GET","POST"])
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
                last_user_action=user_action,
                full_history=""
            )

            affect_delta = 0.0
            narration_txt = ""
            image_prompt = ""
            for ln in result_text.split("\n"):
                s = ln.strip()
                if s.startswith("AFFECT_CHANGE_FINAL:"):
                    try:
                        affect_delta = float(s.split(":",1)[1].strip())
                    except:
                        affect_delta = 0.0
                elif s.startswith("NARRATION:"):
                    narration_txt = s.split(":",1)[1].strip()
                elif s.startswith("IMAGE_PROMPT:"):
                    image_prompt = s.split(":",1)[1].strip()

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
            prompt_text = request.form.get("scene_image_prompt","").strip()
            handle_image_generation(prompt_text, force_new_seed=False)
            return redirect(url_for("interaction"))

        elif "new_seed" in request.form:
            prompt_text = request.form.get("scene_image_prompt","").strip()
            handle_image_generation(prompt_text, force_new_seed=True)
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
# Full Story + Erotica
# --------------------------------------------------------------------------
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
You are continuing an erotic story. Pick up exactly where this left off and continue
the scene for another 600-900 words. Maintain the same tone, characters, and setting.
Keep the story cohesive and flowing naturally from the previous text.

PREVIOUS TEXT:
{previous_text}

Now continue the story from this exact point (600-900 more words):
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
* You may describe sexual acts in detail
* You may include language depicting nudity, arousal, orgasm, and explicit bodily contact
"""
    chat = model.start_chat()
    erotica_resp = chat.send_message(
        erotica_prompt,
        generation_config={"temperature": 0.8, "max_output_tokens": 8000},
        safety_settings=safety_settings
    )
    erotica_text = erotica_resp.text.strip()
    return render_template("erotica_story.html", erotica_text=erotica_text, title="Generated Erotica")

# --------------------------------------------------------------------------
# Stage Unlocks
# --------------------------------------------------------------------------
@app.route("/stage_unlocks", methods=["GET","POST"])
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

# --------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)