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
# 1) CONFIG + Session Setup
############################################################################

app = Flask(__name__)
app.config["SECRET_KEY"] = "abc123supersecret"
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./.flask_sess"
app.config["SESSION_PERMANENT"] = False
Session(app)

os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

############################################################################
# 2) Initialize Clients (NOT stored in session!)
############################################################################

# Example approach:
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
deepseek_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)  # If you use GPT-4, etc.

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
replicate.client.api_token = REPLICATE_API_TOKEN

############################################################################
# 3) Constants / Stage Requirements / Etc.
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
USER_PERSONALITY_OPTIONS = [
    "Friendly","Funny","Adventurous","Introverted","Ambitious","Laid-back","Kind","Curious","Other"
]

STAGE_INFO = {
    1: {"label": "Strangers", "desc": "They barely know each other."},
    2: {"label": "Casual Acquaintances", "desc": "Some superficial chatting, no real depth yet."},
    3: {"label": "Comfortable", "desc": "Can share moderate personal info, might plan small outings."},
    4: {"label": "Close", "desc": "Frequent contact, emotional trust, safe time alone together."},
    5: {"label": "Serious Potential", "desc": "Openly affectionate, discussing future possibilities."},
    6: {"label": "Committed Relationship", "desc": "Life partners with strong devotion and shared long-term goals."}
}

STAGE_REQUIREMENTS = {
    1: 0,
    2: 2,
    3: 5,
    4: 7,
    5: 10,
    6: 15
}

GENERATED_IMAGE_PATH = "output.jpg"

############################################################################
# 4) Build Personalization
############################################################################

def build_personalization_string():
    user_data = (
        f"USER:\n"
        f"  Name: {session.get('user_name','?')}\n"
        f"  Age: {session.get('user_age','?')}\n"
        f"  Personality: {session.get('user_personality','?')}\n"
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
    )
    env_data = (
        f"ENVIRONMENT:\n"
        f"  Location: {session.get('environment','?')}\n"
        f"  EncounterContext: {session.get('encounter_context','?')}\n"
    )
    return user_data + npc_data + env_data

############################################################################
# 5) Single-Pass LLM with "assistant prefix" + "user" for deepseek-reasoner
############################################################################

def interpret_npc_state(affection, trust, npc_mood, current_stage, last_user_action, full_history=""):
    """
    We'll create two messages for deepseek-reasoner:
      1) assistant with prefix=True = "system-like" instructions about dice logic
      2) user = the user content (the last action, plus conversation log)
    The model returns a single answer with lines (DICE_ROLL, OUTCOME, AFFECT_CHANGE_FINAL, etc.)
    """
    stage_label = STAGE_INFO[current_stage]["label"]
    stage_desc = STAGE_INFO[current_stage]["desc"]
    personalization = build_personalization_string()

    prefix_instructions = f"""
You are both the conversation generator and the dice-based logic engine for a romance RPG.

For each user action:
1) Identify ACTION_TIER = low|medium|high|bad.
2) Generate a random integer DICE_ROLL (1..100). (Simulate fairly, do not cheat.)
3) Compare DICE_ROLL to these probabilities (based on ACTION_TIER):
   - low:    60% success, 40% neutral, 0% regression
   - medium: 50% success, 30% neutral, 20% regression
   - high:   35% success, 50% neutral, 15% regression
   - bad:    0% success,  30% neutral, 70% regression
4) Decide final shift in affection as AFFECT_CHANGE_FINAL:
   - If success => your recommended shift
   - If neutral => 0
   - If regression => invert sign (if 0, fallback to -2)
5) Produce these lines EXACTLY (no extra lines):
   DICE_ROLL: ...
   OUTCOME: success|neutral|regression
   AFFECT_CHANGE_FINAL: ...
   SPOKEN_DIALOGUE: ...
   INTERNAL_MONOLOGUE: ...

Background (do not contradict):
{personalization}

Relationship Stage={current_stage} ({stage_label})
{stage_desc}

Stats: Affection={affection}, Trust={trust}, Mood={npc_mood}
    """

    user_msg = f"""
User's last action: {last_user_action}

PREVIOUS_LOG:
{full_history}
"""

    messages = [
        {
            "role": "assistant",
            "content": prefix_instructions,
            "prefix": True
        },
        {
            "role": "user",
            "content": user_msg
        }
    ]

    response = deepseek_client.chat.completions.create(
        model="deepseek-reasoner",
        messages=messages,
        temperature=0.5
    )

    final_text = response.choices[0].message.content.strip()
    return final_text

############################################################################
# 6) Stage Up/Down Checker
############################################################################

def check_stage_up_down(new_aff):
    cur_stage = session.get("currentStage",1)
    req = STAGE_REQUIREMENTS[cur_stage]
    if new_aff < req:
        new_st = 1
        for s, needed in STAGE_REQUIREMENTS.items():
            if new_aff >= needed:
                new_st = max(new_st,s)
        session["currentStage"] = new_st
    else:
        while session["currentStage"] < 6:
            nxt = session["currentStage"] + 1
            if new_aff >= STAGE_REQUIREMENTS[nxt]:
                session["currentStage"] = nxt
            else:
                break

    st = session["currentStage"]
    session["nextStageThreshold"] = STAGE_REQUIREMENTS[st+1] if st < 6 else 999

############################################################################
# 7) Image Generation
############################################################################

def generate_flux_image_safely(prompt, seed=None):
    replicate_input = {
        "prompt": prompt,
        "raw": True,
        "safety_tolerance": 6
    }
    if seed is not None:
        replicate_input["seed"] = seed

    result = replicate.run("black-forest-labs/flux-1.1-pro-ultra", input=replicate_input)
    if isinstance(result, list):
        if result:
            return str(result[-1])
        else:
            return "No URL returned??"
    else:
        return str(result)

def _save_image(url):
    r = requests.get(url)
    with open(GENERATED_IMAGE_PATH, "wb") as f:
        f.write(r.content)

############################################################################
# 8) Flask Routes
############################################################################

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
    if request.method=="POST" and "save_personalization" in request.form:
        def merge_dropdown(dd_key, custom_key):
            dd_val = request.form.get(dd_key,"").strip()
            custom_val = request.form.get(custom_key,"").strip()
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

        session["environment"] = merge_dropdown("environment","environment_custom")
        session["encounter_context"] = merge_dropdown("encounter_context","encounter_context_custom")

        use_single_seed = (request.form.get("use_single_seed","")=="yes")
        session["use_single_seed"] = use_single_seed
        if use_single_seed:
            session["global_seed"] = random.randint(100000,999999)

        # stats
        session["affectionScore"] = 0.0
        session["trustScore"] = 5.0
        session["npcMood"] = "Neutral"
        session["currentStage"] = 1
        session["npcPrivateThoughts"] = "(none)"
        session["nextStageThreshold"] = STAGE_REQUIREMENTS[2]

        # debug
        session["dice_debug_roll"] = "(none)"
        session["dice_debug_outcome"] = "(none)"

        session["interaction_log"] = []
        session["scene_image_prompt"] = ""
        session["scene_image_url"] = None
        session["scene_image_seed"] = None

        return redirect(url_for("npc_image"))

    else:
        # Render your existing personalization form
        return render_template(
            "personalize.html",
            title="Personalizations",
            user_name_options=USER_NAME_OPTIONS,
            user_age_options=USER_AGE_OPTIONS,
            user_personality_options=USER_PERSONALITY_OPTIONS,
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

@app.route("/npc_image", methods=["GET","POST"])
def npc_image():
    if request.method=="GET":
        prompt = (
            f"Portrait of {session.get('npc_name','?')}, age {session.get('npc_age','?')}, "
            f"ethnicity {session.get('npc_ethnicity','?')} wearing {session.get('npc_clothing','?')}. "
            "Photo-realistic style."
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
        url = generate_flux_image_safely(prompt, seed=seed_used)
        _save_image(url)
        session["last_image_seed"] = seed_used
        return render_template(
            "npc_image.html",
            title="NPC Portrait",
            npc_image_prompt=prompt,
            npc_image_url=url,
            seed_used=seed_used
        )

    if "regenerate_same_seed" in request.form:
        seed_used = session.get("last_image_seed", None)
        if not seed_used:
            seed_used = session["global_seed"] if use_single_seed else random.randint(100000,999999)
        url = generate_flux_image_safely(prompt, seed=seed_used)
        _save_image(url)
        session["last_image_seed"] = seed_used
        return render_template(
            "npc_image.html",
            title="NPC Portrait",
            npc_image_prompt=prompt,
            npc_image_url=url,
            seed_used=seed_used
        )

    if "regenerate_new_seed" in request.form:
        seed_used = random.randint(100000,999999)
        url = generate_flux_image_safely(prompt, seed=seed_used)
        _save_image(url)
        session["last_image_seed"] = seed_used
        return render_template(
            "npc_image.html",
            title="NPC Portrait",
            npc_image_prompt=prompt,
            npc_image_url=url,
            seed_used=seed_used
        )

    return "Invalid request in npc_image", 400

@app.route("/interaction", methods=["GET","POST"])
def interaction():
    """
    Main user action route. Single pass call to deepseek-reasoner using interpret_npc_state.
    Then parse the model's lines (DICE_ROLL, OUTCOME, AFFECT_CHANGE_FINAL, etc.).
    """
    if request.method == "GET":
        affection = session.get("affectionScore", 0.0)
        trust = session.get("trustScore", 5.0)
        mood = session.get("npcMood", "Neutral")
        cstage = session.get("currentStage", 1)
        st_label = STAGE_INFO[cstage]["label"]
        st_desc = STAGE_INFO[cstage]["desc"]
        nxt_thresh = session.get("nextStageThreshold", 999)

        last_npc_private = session.get("npcPrivateThoughts", "(none)")
        last_spoken = session.get("npcSpokenDialogue", "No dialogue yet.")

        scene_prompt = session.get("scene_image_prompt", "")
        scene_url = session.get("scene_image_url", None)
        seed_used = session.get("scene_image_seed", None)

        dice_roll_dbg = session.get("dice_debug_roll","(none)")
        dice_outcome_dbg = session.get("dice_debug_outcome","(none)")

        return render_template(
            "interaction.html",
            title="Interact with NPC",
            affection_score=affection,
            trust_score=trust,
            npc_mood=mood,
            current_stage=cstage,
            stage_label=st_label,
            stage_desc=st_desc,
            next_threshold=nxt_thresh,
            npc_private_thoughts=last_npc_private,
            npc_spoken_dialogue=last_spoken,
            scene_image_prompt=scene_prompt,
            scene_image_url=scene_url,
            scene_image_seed=seed_used,
            environment_options=ENVIRONMENT_OPTIONS,
            clothing_options=CLOTHING_OPTIONS,
            interaction_log=session.get("interaction_log", []),
            dice_roll_dbg=dice_roll_dbg,
            dice_outcome_dbg=dice_outcome_dbg
        )

    else:
        if "submit_action" in request.form:
            user_action = request.form.get("user_action", "").strip()
            if not user_action:
                user_action = "(no action)"

            affection = session.get("affectionScore", 0.0)
            trust = session.get("trustScore", 5.0)
            mood = session.get("npcMood", "Neutral")
            cstage = session.get("currentStage", 1)

            log_entries = session.get("interaction_log", [])
            full_history = "\n".join(log_entries)

            # Single pass to deepseek-reasoner
            result_text = interpret_npc_state(
                affection=affection,
                trust=trust,
                npc_mood=mood,
                current_stage=cstage,
                last_user_action=user_action,
                full_history=full_history
            )

            # parse them
            dice_roll_val = "(none)"
            outcome_val = "(none)"
            final_affect = 0.0
            spoken_dialogue = ""
            internal_monologue = ""

            lines = result_text.split("\n")
            for ln in lines:
                s = ln.strip()
                if s.startswith("DICE_ROLL:"):
                    dice_roll_val = s.split(":",1)[1].strip()
                elif s.startswith("OUTCOME:"):
                    outcome_val = s.split(":",1)[1].strip()
                elif s.startswith("AFFECT_CHANGE_FINAL:"):
                    try:
                        final_affect = float(s.split(":",1)[1].strip())
                    except:
                        final_affect = 0.0
                elif s.startswith("SPOKEN_DIALOGUE:"):
                    spoken_dialogue = s.split(":",1)[1].strip()
                elif s.startswith("INTERNAL_MONOLOGUE:"):
                    internal_monologue = s.split(":",1)[1].strip()

            new_aff = affection + final_affect
            session["affectionScore"] = new_aff

            session["dice_debug_roll"] = dice_roll_val
            session["dice_debug_outcome"] = outcome_val

            session["npcMood"] = mood
            session["npcPrivateThoughts"] = result_text
            session["npcSpokenDialogue"] = spoken_dialogue

            check_stage_up_down(new_aff)

            log_entries.append(f"User: {user_action}")
            log_entries.append(
                f"NPC: {spoken_dialogue} [DiceRoll={dice_roll_val}, Outcome={outcome_val}, FinalAffect={final_affect}]"
            )
            session["interaction_log"] = log_entries

            return redirect(url_for("interaction"))

        elif "update_mutable" in request.form:
            new_env = request.form.get("new_environment", "").strip()
            new_clothing = request.form.get("new_clothing", "").strip()

            log_entries = session.get("interaction_log", [])
            changed_something = False

            if new_env:
                session["environment"] = new_env
                log_entries.append(f"SYSTEM: Environment changed to '{new_env}'.")
                changed_something = True

            if new_clothing:
                session["npc_clothing"] = new_clothing
                log_entries.append(f"SYSTEM: NPC clothing changed to '{new_clothing}'.")
                changed_something = True

            if changed_something:
                session["interaction_log"] = log_entries

            return redirect(url_for("interaction"))

        elif "generate_scene_image" in request.form:
            log_entries = session.get("interaction_log", [])
            full_history = "\n".join(log_entries)
            prompt = f"A scene featuring the NPC, referencing the environment.\n\nHistory:\n{full_history}"
            session["scene_image_prompt"] = prompt
            session["scene_image_url"] = None
            session["scene_image_seed"] = None
            return redirect(url_for("interaction"))

        elif "do_generate_flux" in request.form or "same_seed" in request.form or "new_seed" in request.form:
            prompt_text = request.form.get("scene_image_prompt","").strip()
            if not prompt_text:
                prompt_text = "(No prompt text?)"

            use_single_seed = session.get("use_single_seed", False)
            seed_used = session.get("scene_image_seed", None)

            if "same_seed" in request.form:
                if not seed_used:
                    seed_used = session.get("global_seed", None) or random.randint(100000,999999)
            elif "new_seed" in request.form:
                seed_used = random.randint(100000,999999)
            else:
                if use_single_seed:
                    if not seed_used:
                        seed_used = session.get("global_seed", None) or random.randint(100000,999999)
                else:
                    seed_used = random.randint(100000,999999)

            url = generate_flux_image_safely(prompt_text, seed=seed_used)
            _save_image(url)
            session["scene_image_prompt"] = prompt_text
            session["scene_image_url"] = url
            session["scene_image_seed"] = seed_used

            return redirect(url_for("interaction"))

        return "Invalid form submission in /interaction", 400

@app.route("/view_image")
def view_image():
    return send_file(GENERATED_IMAGE_PATH, mimetype="image/jpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)