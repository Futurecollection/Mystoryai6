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

# SECRET_KEY must be set for sessions, but keep it unique in production
app.config["SECRET_KEY"] = "abc123supersecret"
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./.flask_sess"
app.config["SESSION_PERMANENT"] = False
Session(app)

# Make sure the directory for session files exists
os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

############################################################################
# 2) Initialize Clients (NOT stored in session!)
############################################################################

# We do NOT store these clients in the session. We only keep them as module-level variables.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)  # used for GPT-4o-mini

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
replicate.client.api_token = REPLICATE_API_TOKEN  # no storing in session

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

############################################################################
# 3) Constants / Lists / Stage Requirements
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

GENERATED_IMAGE_PATH = "output.jpg"  # local file path for the last image

############################################################################
# 4) Helper Functions
############################################################################

def build_personalization_string():
    """
    Returns a big multiline string that includes user & NPC attributes,
    plus environment info, from the Flask session.
    """
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

def interpret_npc_state(affection, trust, npc_mood, current_stage, last_user_action, full_history=""):
    """
    Calls DeepSeek to get NPC's internal monologue, spoken dialogue, and stat changes.
    We only store the final string in session, never the raw response object.
    """
    stage_label = STAGE_INFO[current_stage]["label"]
    stage_desc = STAGE_INFO[current_stage]["desc"]
    personalization = build_personalization_string()

    system_msg = f"""
    You are the NPC's internal thoughts and external response generator.

    Relationship Stage={current_stage} ({stage_label})
    {stage_desc}

    Stats: Affection={affection}, Trust={trust}, Mood={npc_mood}
    The user's last action is: {last_user_action}

    Provide output in this exact format (no extra lines):
    INTERNAL_MONOLOGUE: ...
    SPOKEN_DIALOGUE: ...
    AFFECT_CHANGE: ...
    TRUST_CHANGE: ...
    EMOTIONAL_STATE: ...
    BEHAVIOR: ...
    """

    user_msg = f"""
    PERSONALIZATION:\n{personalization}

    PREVIOUS_LOG:\n{full_history}

    Please provide an internal monologue plus the NPC's outward spoken dialogue
    and changes in stats, given the user just did: "{last_user_action}".
    """

    # This returns an "openai.libcore.ChatCompletion" object, but we only store the final string
    resp = deepseek_client.chat.completions.create(
        model="deepseek-reasoner",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.7,
        stream=False
    )

    # Extract the final text from the response and return it
    final_text = resp.choices[0].message.content
    return final_text.strip()

def check_stage_up_down(new_aff):
    """
    Adjust the relationship stage based on the updated affection score.
    """
    cur_stage = session.get("currentStage",1)
    req = STAGE_REQUIREMENTS[cur_stage]
    if new_aff < req:
        # Possibly revert stage if affection dropped
        new_st = 1
        for s, needed in STAGE_REQUIREMENTS.items():
            if new_aff >= needed:
                new_st = max(new_st,s)
        session["currentStage"] = new_st
    else:
        # Move forward if new_aff meets next stage thresholds
        while session["currentStage"] < 6:
            nxt = session["currentStage"] + 1
            if new_aff >= STAGE_REQUIREMENTS[nxt]:
                session["currentStage"] = nxt
            else:
                break

    # compute next threshold
    st = session["currentStage"]
    if st < 6:
        session["nextStageThreshold"] = STAGE_REQUIREMENTS[st+1]
    else:
        session["nextStageThreshold"] = 999

def generate_flux_image(prompt, seed=None):
    """
    Calls Replicate to generate an image from the 'black-forest-labs/flux-1.1-pro-ultra' model.
    We return a string URL, do NOT store the replicate response object in session.
    """
    replicate_input = {
        "prompt": prompt,
        "raw": True,
        "safety_tolerance": 6
    }
    if seed is not None:
        replicate_input["seed"] = seed

    # replicate.run returns a URL string typically
    url = replicate.run("black-forest-labs/flux-1.1-pro-ultra", input=replicate_input)
    return url

def _save_image(url):
    """
    Downloads the image data from the given url to a local file (output.jpg).
    """
    r = requests.get(url)
    with open(GENERATED_IMAGE_PATH, "wb") as f:
        f.write(r.content)

def gpt_scene_image_prompt(full_history):
    """
    Creates a single-sentence prompt for the scene using 'gpt-4o-mini'.
    We only store or return the final string, never the raw response object.
    """
    npc_age = session.get("npc_age", "?")
    npc_eth = session.get("npc_ethnicity", "?")
    env_loc = session.get("environment", "?")

    sys_content = f"""
    Create a single-sentence photographic prompt featuring the NPC (age {npc_age}, {npc_eth}), 
    possibly referencing the environment '{env_loc}'. 
    Focus on describing the NPC's appearance or posture and the scene vibe. 
    No mention of 'user' or 'photographer'.
    """

    user_content = f"STORY CONTEXT:\n{full_history}\nOne line describing the NPC in environment."

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys_content},
            {"role": "user", "content": user_content}
        ],
        temperature=0.7
    )
    return resp.choices[0].message.content.strip()

############################################################################
# 5) Flask Routes
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
        session["nextStageThreshold"] = STAGE_REQUIREMENTS[2]  # stage1 => next=2 => 2

        # create an empty log for user/NPC lines
        session["interaction_log"] = []

        # scene prompt placeholders
        session["scene_image_prompt"] = ""
        session["scene_image_url"] = None
        session["scene_image_seed"] = None

        return redirect(url_for("npc_image"))

    else:
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
        url = generate_flux_image(prompt, seed=seed_used)
        _save_image(url)  # save to output.jpg
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
        url = generate_flux_image(prompt, seed=seed_used)
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
        url = generate_flux_image(prompt, seed=seed_used)
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
    Main route for user actions + NPC responses + optional scene image generation
    """

    if request.method == "GET":
        # Show the form, plus last NPC response, stats, and any scene image
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
            scene_image_seed=seed_used
        )

    else:
        if "submit_action" in request.form:
            # A new user action
            user_action = request.form.get("user_action", "").strip()
            if not user_action:
                user_action = "(no action)"

            affection = session.get("affectionScore", 0.0)
            trust = session.get("trustScore", 5.0)
            mood = session.get("npcMood", "Neutral")
            cstage = session.get("currentStage", 1)

            # Build a minimal "full_history" from the session logs
            log_entries = session.get("interaction_log", [])
            full_history = "\n".join(log_entries)

            result_text = interpret_npc_state(
                affection=affection,
                trust=trust,
                npc_mood=mood,
                current_stage=cstage,
                last_user_action=user_action,
                full_history=full_history
            )

            # parse them
            internal_monologue = ""
            spoken_dialogue = ""
            affect_change = 0.0
            trust_change = 0.0
            new_mood = mood
            behavior_desc = ""

            lines = result_text.split("\n")
            for ln in lines:
                s = ln.strip()
                if s.startswith("INTERNAL_MONOLOGUE:"):
                    internal_monologue = s.split(":",1)[1].strip()
                elif s.startswith("SPOKEN_DIALOGUE:"):
                    spoken_dialogue = s.split(":",1)[1].strip()
                elif s.startswith("AFFECT_CHANGE:"):
                    try:
                        affect_change = float(s.split(":",1)[1].strip())
                    except:
                        affect_change = 0.0
                elif s.startswith("TRUST_CHANGE:"):
                    try:
                        trust_change = float(s.split(":",1)[1].strip())
                    except:
                        trust_change = 0.0
                elif s.startswith("EMOTIONAL_STATE:"):
                    new_mood = s.split(":",1)[1].strip()
                elif s.startswith("BEHAVIOR:"):
                    behavior_desc = s.split(":",1)[1].strip()
                else:
                    # Possibly leftover lines from internal monologue
                    pass

            # Update stats
            new_aff = affection + affect_change
            session["affectionScore"] = new_aff
            check_stage_up_down(new_aff)

            new_trust = trust + trust_change
            new_trust = max(0.0, min(15.0, new_trust))
            session["trustScore"] = new_trust

            session["npcMood"] = new_mood

            # Save the entire text in npcPrivateThoughts
            # => final_text is a string, so it's safe
            session["npcPrivateThoughts"] = result_text
            session["npcSpokenDialogue"] = spoken_dialogue

            # Append new lines to the log (strings only)
            log_entries.append(f"User: {user_action}")
            log_entries.append(f"NPC: {spoken_dialogue}")
            session["interaction_log"] = log_entries

            return redirect(url_for("interaction"))

        elif "generate_scene_image" in request.form:
            # We want a GPT-based scene prompt
            log_entries = session.get("interaction_log", [])
            full_history = "\n".join(log_entries)

            auto_prompt = gpt_scene_image_prompt(full_history)
            session["scene_image_prompt"] = auto_prompt
            session["scene_image_url"] = None
            session["scene_image_seed"] = None

            return redirect(url_for("interaction"))

        elif "do_generate_flux" in request.form or "same_seed" in request.form or "new_seed" in request.form:
            # Actually call replicate with the prompt
            prompt_text = request.form.get("scene_image_prompt","").strip()
            if not prompt_text:
                prompt_text = "(No prompt text?)"

            use_single_seed = session.get("use_single_seed", False)
            seed_used = session.get("scene_image_seed", None)

            if "same_seed" in request.form:
                # Re-generate with same seed
                if not seed_used:
                    # fallback to global or random
                    seed_used = session.get("global_seed", None) or random.randint(100000,999999)
            elif "new_seed" in request.form:
                # brand new random seed
                seed_used = random.randint(100000,999999)
            else:
                # "Generate Scene Image" with default approach
                if use_single_seed:
                    if not seed_used:
                        seed_used = session.get("global_seed", None) or random.randint(100000,999999)
                else:
                    seed_used = random.randint(100000,999999)

            url = generate_flux_image(prompt_text, seed=seed_used)
            _save_image(url)

            session["scene_image_prompt"] = prompt_text
            session["scene_image_url"] = url  # just a string
            session["scene_image_seed"] = seed_used  # just an int

            return redirect(url_for("interaction"))

        else:
            return "Invalid form submission in /interaction", 400

@app.route("/view_image")
def view_image():
    """
    Returns the locally saved image from replicate.
    """
    return send_file(GENERATED_IMAGE_PATH, mimetype="image/jpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)