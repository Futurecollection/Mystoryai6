import os
import replicate
import requests
import random

from openai import OpenAI
from flask import (
    Flask, request, render_template,
    session, redirect, url_for, send_file
)
from flask_session import Session

############################################################################
# A) DROPDOWN LISTS
############################################################################

USER_NAME_OPTIONS = ["John","Michael","David","Chris","James","Alex","Nick","Adam","Andrew","Jason","Other"]
USER_AGE_OPTIONS = [str(a) for a in range(20,50,5)]

NPC_NAME_OPTIONS = ["Emily","Sarah","Lisa","Anna","Mia","Sophia","Grace","Chloe","Emma","Isabella","Other"]
NPC_AGE_OPTIONS = [str(a) for a in range(20,50,5)]
NPC_GENDER_OPTIONS = ["Female", "Male", "Non-binary", "Other"]
HAIR_STYLE_OPTIONS = ["Short","Medium Length","Long","Bald","Ponytail","Braided","Bun","Messy Bun","Other"]
BODY_TYPE_OPTIONS = ["Slender","Petite","Tall & Lean","Plus-size","Athletic","Muscular","Curvy"]
HAIR_COLOR_OPTIONS = ["Blonde","Brunette","Black","Red","Brown","Grey","Dyed (Blue/Pink/etc)"]
NPC_PERSONALITY_OPTIONS = [
  "Flirty","Passionate","Submissive","Creative","Nurturer",
  "Intellectual","Healer","Entertainer","Reserved","Cheerful",
  "Sassy","Calm","Witty","Other"
]
CLOTHING_OPTIONS = [
  "Red Summer Dress","Blue T-shirt & Jeans","Black Evening Gown",
  "Green Hoodie & Leggings","White Blouse & Dark Skirt","Business Attire",
  "Grey Sweater & Jeans","Pink Casual Dress","Other"
]
OCCUPATION_OPTIONS = [
  "College Student","School Teacher","Librarian","Office Worker","Freelance Artist","Bartender",
  "Travel Blogger","Ex-Military","Nurse","Startup Founder","Other"
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
  "First date","Accidental meeting","Haven't met yet","Happened to be in the same location",
  "Group activity or event","Work-related encounter","Other"
]
ETHNICITY_OPTIONS = [
  "American (Black)","American (White)","American (Hispanic)","Russian","German","Nigerian","Brazilian","Chinese",
  "Japanese","Indian","Australian","Canadian","British","French","Norwegian","Korean","Egyptian","Pakistani","Other"
]

############################################################################
# B) SIMPLE STAGE DATA (optional)
############################################################################

STAGE_INFO = {
    1: {"label": "Strangers", "desc": "Barely know each other."},
    2: {"label": "Friendly Acquaintances","desc":"Casual chatting, not deep."},
    3: {"label": "Comfortable","desc":"Trusting, some personal stories."},
    4: {"label": "Close","desc":"Frequent contact, emotional trust."},
    5: {"label": "Serious Potential","desc":"Openly affectionate, deeper plans."},
    6: {"label": "Committed Relationship","desc":"Life partners, strong devotion."}
}

# Requirements: 2,3,5,7,10
STAGE_REQUIREMENTS = {
    1: 0,
    2: 2,
    3: 3,
    4: 5,
    5: 7,
    6: 10
}

############################################################################
# C) Flask & Session Config
############################################################################

app = Flask(__name__)
app.config["SECRET_KEY"] = "abc123supersecret"
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./.flask_sess"
app.config["SESSION_PERMANENT"] = False
Session(app)

os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
replicate.client.api_token = REPLICATE_API_TOKEN

GENERATED_IMAGE_PATH = "output.jpg"

############################################################################
# D) build_npc_env_personalization (NPC only, no user)
############################################################################

def build_npc_env_personalization():
    npc_part = f"""
    NPC:
      Name: {session.get('npc_name','?')}
      Gender: {session.get('npc_gender','?')}
      Age: {session.get('npc_age','?')}
      Ethnicity: {session.get('npc_ethnicity','?')}
      BodyType: {session.get('npc_body_type','?')}
      HairColor: {session.get('npc_hair_color','?')}
      HairStyle: {session.get('npc_hair_style','?')}
      Clothing: {session.get('npc_clothing','?')}
      Personality: {session.get('npc_personality','?')}
      Occupation: {session.get('npc_occupation','?')}
      CurrentSituation: {session.get('npc_current_situation','?')}
    """

    env_part = f"""
    ENVIRONMENT:
      Location: {session.get('environment','?')}
      EncounterContext: {session.get('encounter_context','?')}
    """

    return npc_part + "\n" + env_part

############################################################################
# E) Minimal Rolling NPC Memory
############################################################################

def get_npc_memory():
    return session.get("npcMemory","(none)")

def set_npc_memory(new_summary:str):
    session["npcMemory"] = new_summary

############################################################################
# F) interpret_npc_state: single-turn internal mind
############################################################################

def interpret_npc_state(affection, trust, last_user_action):
    """
    LLM sees:
      - Rolling NPC memory summary
      - Affection & Trust
      - NPC + environment data
      - user action

    Returns (internal monologue) + lines:
      SPOKEN_DIALOGUE:
      GESTURES:
      AFFECT_CHANGE:
      TRUST_CHANGE:
      EMOTIONAL_STATE:
      BEHAVIOUR:
    """
    npc_memory = get_npc_memory()
    npc_env = build_npc_env_personalization()

    system_message = {
        "role": "system",
        "content": f"""
        You are the NPC's internal mind.
        Rolling memory summary: {npc_memory}

        {npc_env}

        Current Affection: {affection}
        Current Trust: {trust}

        The user just performed: {last_user_action}.

        Return:
        1) Long internal monologue (debug only)
        2) lines:
           SPOKEN_DIALOGUE: (what NPC says out loud, or empty)
           GESTURES: (body/facial expressions)
           AFFECT_CHANGE: -1..+1
           TRUST_CHANGE: -1..+1
           EMOTIONAL_STATE:
           BEHAVIOUR: (any extra outward behavior)
        """
    }
    user_message = {
        "role": "user",
        "content": "Produce your internal thoughts + the lines exactly as specified."
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

############################################################################
# G) generate_single_turn_snippet: short scene from user POV
############################################################################

def generate_single_turn_snippet(user_action, spoken_dialogue, gestures):
    """
    Minimal 3rd-person snippet. 
    No large memory. 
    Just incorporate the user action + NPC speech/gestures.
    """
    system_message = {
        "role": "system",
        "content": (
            "You are a short, third-person narrator. "
            "We have: userAction and npcSpeech/gestures. "
            "Write a single-step scene (~1-3 lines). No additional expansions."
        )
    }
    user_message = {
        "role": "user",
        "content": f"""
        userAction: {user_action}
        npcSpeech: {spoken_dialogue}
        npcGestures: {gestures}

        Return a short scene from user’s POV, describing only this moment.
        """
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

############################################################################
# H) Stage Up/Down
############################################################################

def check_stage_up_down(new_aff):
    current_stage = session.get("currentStage", 1)
    req_for_stage = STAGE_REQUIREMENTS[current_stage]
    if new_aff < req_for_stage:
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

############################################################################
# I) Image Gen & Minimal
############################################################################

def generate_flux_image(prompt, seed=None):
    replicate_input = {
        "prompt": prompt,
        "raw": True,
        "safety_tolerance": 6
    }
    if seed is not None:
        replicate_input["seed"] = seed
    output_url = replicate.run("black-forest-labs/flux-1.1-pro-ultra", input=replicate_input)
    return output_url

def _save_image(url):
    r = requests.get(url)
    with open(GENERATED_IMAGE_PATH, "wb") as f:
        f.write(r.content)

############################################################################
# J) Flask Routes
############################################################################

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("home.html", title="Destined Encounters")

@app.route("/restart")
def restart():
    session.clear()
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    return redirect(url_for("personalize"))

@app.route("/personalize", methods=["GET","POST"])
def personalize():
    if request.method == "POST" and "save_personalization" in request.form:
        def merge_dropdown(dd_key, custom_key):
            dd_val = request.form.get(dd_key, "").strip()
            custom_val = request.form.get(custom_key, "").strip()
            return custom_val if custom_val else dd_val

        # user
        session["user_name"] = merge_dropdown("user_name","user_name_custom")
        session["user_age"] = merge_dropdown("user_age","user_age_custom")
        session["user_personality"] = merge_dropdown("user_personality","user_personality_custom")
        session["user_background"] = request.form.get("user_background","").strip()

        # npc
        session["npc_name"] = merge_dropdown("npc_name","npc_name_custom")
        session["npc_gender"] = merge_dropdown("npc_gender","npc_gender_custom")
        session["npc_age"] = merge_dropdown("npc_age","npc_age_custom")
        session["npc_ethnicity"] = merge_dropdown("npc_ethnicity","npc_ethnicity_custom")
        session["npc_body_type"] = merge_dropdown("npc_body_type","npc_body_type_custom")
        session["npc_hair_color"] = merge_dropdown("npc_hair_color","npc_hair_color_custom")
        session["npc_hair_style"] = merge_dropdown("npc_hair_style","npc_hair_style_custom")
        session["npc_personality"] = merge_dropdown("npc_personality","npc_personality_custom")
        session["npc_clothing"] = merge_dropdown("npc_clothing","npc_clothing_custom")
        session["npc_occupation"] = merge_dropdown("npc_occupation","npc_occupation_custom")
        session["npc_current_situation"] = merge_dropdown("npc_current_situation","npc_current_situation_custom")

        # environment
        session["environment"] = merge_dropdown("environment","environment_custom")
        session["encounter_context"] = merge_dropdown("encounter_context","encounter_context_custom")

        use_single_seed = (request.form.get("use_single_seed","") == "yes")
        session["use_single_seed"] = use_single_seed
        if use_single_seed:
            session["global_seed"] = random.randint(100000,999999)

        # init hidden stats
        session["affectionScore"] = 0.0
        session["trustScore"] = 5.0
        session["npcMood"] = "Neutral"
        session["currentStage"] = 1

        # next stage threshold => stage 2 => 2 affection
        session["npcMemory"] = "(none)"  # rolling summary blank
        return redirect(url_for("npc_image"))

    else:
        return render_template(
            "personalize.html",
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
            encounter_options=ENCOUNTER_CONTEXT_OPTIONS,
            ethnicity_options=ETHNICITY_OPTIONS
        )

@app.route("/npc_image", methods=["GET","POST"])
def npc_image():
    if request.method == "GET":
        # minimal portrait prompt
        prompt = (
            f"A single short portrait of {session.get('npc_name','?')} wearing "
            f"{session.get('npc_clothing','?')} with {session.get('npc_hair_color','?')} hair, {session.get('npc_hair_style','?')} style. "
            f"Focus on her/his appearance. Photo-realistic style."
        )
        session["npc_image_prompt"] = prompt
        return render_template(
            "npc_image.html",
            title="NPC Portrait",
            npc_image_prompt=prompt,
            npc_image_url=None,
            seed_used=None
        )

    prompt = request.form.get("npc_image_prompt","")
    session["npc_image_prompt"] = prompt
    use_single_seed = session.get("use_single_seed", False)

    if "generate_npc_image" in request.form:
        seed_used = session["global_seed"] if use_single_seed else random.randint(100000,999999)
        image_url = generate_flux_image(prompt, seed=seed_used)
        _save_image(image_url)
        session["last_image_seed"] = seed_used
        return render_template(
            "npc_image.html",
            title="NPC Portrait",
            npc_image_prompt=prompt,
            npc_image_url=image_url,
            seed_used=seed_used
        )
    if "regenerate_same_seed" in request.form:
        seed_used = session.get("last_image_seed", None)
        if not seed_used:
            seed_used = session["global_seed"] if use_single_seed else random.randint(100000,999999)
        image_url = generate_flux_image(prompt, seed=seed_used)
        _save_image(image_url)
        session["last_image_seed"] = seed_used
        return render_template(
            "npc_image.html",
            title="NPC Portrait",
            npc_image_prompt=prompt,
            npc_image_url=image_url,
            seed_used=seed_used
        )
    if "regenerate_new_seed" in request.form:
        seed_used = random.randint(100000,999999)
        image_url = generate_flux_image(prompt, seed=seed_used)
        _save_image(image_url)
        session["last_image_seed"] = seed_used
        return render_template(
            "npc_image.html",
            title="NPC Portrait",
            npc_image_prompt=prompt,
            npc_image_url=image_url,
            seed_used=seed_used
        )

    return "Invalid request in npc_image", 400

@app.route("/start_story")
def start_story():
    # minimal snippet
    session["last_snippet"] = "The story begins..."
    return redirect(url_for("story"))

@app.route("/story", methods=["GET","POST"])
def story():
    if request.method == "GET":
        # Display the last snippet
        snippet = session.get("last_snippet","(no snippet yet)")
        affection_score = session.get("affectionScore",0.0)
        trust_score = session.get("trustScore",5.0)
        current_stage = session.get("currentStage",1)
        stage_label = STAGE_INFO[current_stage]["label"]
        stage_desc = STAGE_INFO[current_stage]["desc"]
        npc_mood = session.get("npcMood","Neutral")
        npc_memory = get_npc_memory()

        return render_template(
            "story.html",
            title="Story",
            scene_text=snippet,
            scene_image_prompt="",
            scene_image_generated=False,
            seed_used=None,
            affection_score=affection_score,
            trust_score=trust_score,
            npc_mood=npc_mood,
            current_stage=current_stage,
            stage_label=stage_label,
            stage_desc=stage_desc,
            next_threshold=0,  # we won't show next threshold unless you want
            npc_private_thoughts=npc_memory
        )

    if "go_back" in request.form:
        session["last_snippet"] = "You decide to rewind. (no real stack here, so not much to go back to)."
        return redirect(url_for("story"))

    # user typed an action
    custom_action = request.form.get("user_action","").strip()
    if not custom_action:
        custom_action = "(none)"

    # 1) interpret npc
    npc_result = interpret_npc_state(
        affection=session["affectionScore"],
        trust=session["trustScore"],
        last_user_action=custom_action
    )

    # parse the lines
    lines = npc_result.split("\n")
    monologue_lines = []
    spoken_dialogue = ""
    gestures = ""
    affect_change = "0.0"
    trust_change = "0.0"
    emotional_state = ""
    behaviour = ""

    # We'll store a short chunk of monologue in npcMemory
    short_summary = ""

    for line in lines:
        stripline = line.strip()
        # We'll try to detect the "lines" by prefix:
        if stripline.startswith("SPOKEN_DIALOGUE:"):
            spoken_dialogue = stripline.split(":",1)[1].strip()
        elif stripline.startswith("GESTURES:"):
            gestures = stripline.split(":",1)[1].strip()
        elif stripline.startswith("AFFECT_CHANGE:"):
            affect_change = stripline.split(":",1)[1].strip()
        elif stripline.startswith("TRUST_CHANGE:"):
            trust_change = stripline.split(":",1)[1].strip()
        elif stripline.startswith("EMOTIONAL_STATE:"):
            emotional_state = stripline.split(":",1)[1].strip()
        elif stripline.startswith("BEHAVIOUR:"):
            behaviour = stripline.split(":",1)[1].strip()
        else:
            # it's part of the internal monologue
            monologue_lines.append(stripline)

    # update affection/trust
    try:
        delta_a = float(affect_change)
    except ValueError:
        delta_a = 0.0

    old_aff = session["affectionScore"]
    new_aff = old_aff + delta_a
    session["affectionScore"] = new_aff
    check_stage_up_down(new_aff)

    try:
        delta_t = float(trust_change)
    except ValueError:
        delta_t = 0.0
    old_trust = session["trustScore"]
    new_trust = old_trust + delta_t
    new_trust = max(0.0, min(10.0, new_trust))
    session["trustScore"] = new_trust

    # Let's build a short summary from the internal monologue for npcMemory
    # We'll just take the first line or so from monologue
    if monologue_lines:
        short_summary = monologue_lines[0]
    else:
        short_summary = "(no new internal monologue)"

    old_memory = get_npc_memory()
    # We'll keep it short: just store the new summary
    updated_memory = f"{old_memory}\n{short_summary}"
    # If it gets too big, we could truncate
    if len(updated_memory) > 300:
        updated_memory = updated_memory[-300:]  # keep last 300 chars
    set_npc_memory(updated_memory)

    # 2) generate a single-turn snippet
    snippet = generate_single_turn_snippet(
        user_action=custom_action,
        spoken_dialogue=spoken_dialogue,
        gestures=gestures
    )

    session["last_snippet"] = snippet
    return redirect(url_for("story"))

@app.route("/view_image")
def view_image():
    return send_file(GENERATED_IMAGE_PATH, mimetype="image/jpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)