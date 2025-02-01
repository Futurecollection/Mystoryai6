import os
import replicate
import requests
import random

import google.generativeai as genai
from flask import (
    Flask, request, render_template,
    session, redirect, url_for, send_file
)
from flask_session import Session

app = Flask(__name__)
app.config["SECRET_KEY"] = "abc123supersecret"
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./.flask_sess"
app.config["SESSION_PERMANENT"] = False
Session(app)

os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

############################################################################
# 1) Initialize Gemini + Replicate
############################################################################

from google.generativeai.types import HarmCategory, HarmBlockThreshold

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

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
    2: 1,
    3: 3,
    4: 5,
    5: 7,
    6: 10
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

USER_NAME_OPTIONS = ["John","Michael","David","Chris","James","Alex","Nick","Adam","Andrew","Jason","Other"]
USER_AGE_OPTIONS = ["20","25","30","35","40","45"]
USER_PERSONALITY_OPTIONS = [
    "Friendly","Funny","Adventurous","Introverted","Ambitious","Laid-back","Kind","Curious","Other"
]

NPC_NAME_OPTIONS = ["Emily","Sarah","Lisa","Anna","Mia","Sophia","Grace","Chloe","Emma","Isabella","Other"]
NPC_AGE_OPTIONS = ["20","25","30","35","40","45"]
NPC_GENDER_OPTIONS = ["Female","Male","Non-binary","Other"]
HAIR_STYLE_OPTIONS = ["Short","Medium Length","Long","Bald","Ponytail","Braided","Bun","Messy Bun","Other"]
BODY_TYPE_OPTIONS = ["Slender","Petite","Tall & Lean","Plus-size","Athletic","Muscular","Curvy"]
HAIR_COLOR_OPTIONS = ["Blonde","Brunette","Black","Red","Brown","Grey","Dyed (Blue/Pink/etc)"]
NPC_PERSONALITY_OPTIONS = [
  "Flirty","Passionate","Submissive","Creative","Nurturer","Intellectual","Healer","Entertainer",
  "Reserved","Cheerful","Sassy","Calm","Witty","Other"
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
  "First date","Accidental meeting","Haven't met yet","Group activity","Work-related encounter","Other"
]
ETHNICITY_OPTIONS = [
    "American (Black)","American (White)","Hispanic","Russian","German","Brazilian","Chinese",
    "Japanese","Indian","Australian","French","British","Other"
]

############################################################################
# 4) Build Personalization String
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
# 5) interpret_npc_state => 7-labeled lines
############################################################################

def interpret_npc_state(affection, trust, npc_mood, current_stage, last_user_action, full_history=""):
    stage_label = STAGE_INFO[current_stage]["label"]
    stage_desc = STAGE_INFO[current_stage]["desc"]
    personalization = build_personalization_string()

    system_instructions = f"""
You are a third-person descriptive erotic romance narrator from the user's POV about 200-300 words 

For each user action:
1) AFFECT_CHANGE_FINAL => net affection shift (-2.0 to +2.0)
2) ACTION_TIER => (low/medium/high)
3) BEHAVIOR => short outward style
4) NARRATION => narrates describing user's action, and also creates the NPC reaction + NPC speech/dialogue and actions, and describes the environment (about 200-300 words can be in separate paragragrahs)
5) IMAGE_PROMPT => single sentence referencing NPC's age/body/hair/clothing, environment

Output exactly (no extra lines):
AFFECT_CHANGE_FINAL: ...
ACTION_TIER: ...
BEHAVIOR: ...
NARRATION: ...
IMAGE_PROMPT: ...

Background (do not contradict):
{personalization}

Relationship Stage={current_stage} ({stage_label})
{stage_desc}

Stats: Affection={affection}, Trust={trust}, Mood={npc_mood}
"""

    user_text = f"USER ACTION: {last_user_action}\nPREVIOUS_LOG:\n{full_history}"

    chat = model.start_chat()
    resp = chat.send_message(
        f"{system_instructions}\n\n{user_text}",
        generation_config={"temperature": 0.7},
        safety_settings=safety_settings
    )

    return resp.text.strip()

############################################################################
# 6) Stage Checker
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
    if st < 6:
        session["nextStageThreshold"] = STAGE_REQUIREMENTS[st+1]
    else:
        session["nextStageThreshold"] = 999

############################################################################
# 7) Replicate => flux-schnell
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
# 8) GPT-based scene prompt
############################################################################

def gpt_scene_image_prompt(full_history):
    npc_age = session.get("npc_age","?")
    npc_eth = session.get("npc_ethnicity","?")
    env_loc = session.get("environment","?")

    prompt = f"""
You are a creative scene image prompt generator.
Create a single-sentence photographic prompt focusing on:
- NPC (age {npc_age}, {npc_eth})
- Environment: {env_loc}
- Their hair/clothing if mentioned in context
Do not reference 'user' or 'photographer'.

STORY CONTEXT:
{full_history}

Generate one descriptive line for a scene image:"""

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
# 9) Flask Routes
############################################################################

@app.route("/")
def home():
    return render_template("home.html", title="Destined Encounters")

@app.route("/restart")
def restart():
    session.clear()
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    session["stage_unlocks"] = dict(DEFAULT_STAGE_UNLOCKS)
    return redirect(url_for("personalize"))

@app.route("/personalize", methods=["GET","POST"])
def personalize():
    if request.method=="POST" and "save_personalization" in request.form:
        def merge_dd(dd_key, cust_key):
            dd_val = request.form.get(dd_key,"").strip()
            c_val = request.form.get(cust_key,"").strip()
            return c_val if c_val else dd_val

        # user
        session["user_name"] = merge_dd("user_name","user_name_custom")
        session["user_age"] = merge_dd("user_age","user_age_custom")
        session["user_personality"] = merge_dd("user_personality","user_personality_custom")
        session["user_background"] = request.form.get("user_background","").strip()

        # npc
        session["npc_name"] = merge_dd("npc_name","npc_name_custom")
        session["npc_gender"] = merge_dd("npc_gender","npc_gender_custom")
        session["npc_age"] = merge_dd("npc_age","npc_age_custom")
        session["npc_ethnicity"] = merge_dd("npc_ethnicity","npc_ethnicity_custom")
        session["npc_body_type"] = merge_dd("npc_body_type","npc_body_type_custom")
        session["npc_hair_color"] = merge_dd("npc_hair_color","npc_hair_color_custom")
        session["npc_hair_style"] = merge_dd("npc_hair_style","npc_hair_style_custom")
        session["npc_personality"] = merge_dd("npc_personality","npc_personality_custom")
        session["npc_clothing"] = merge_dd("npc_clothing","npc_clothing_custom")
        session["npc_occupation"] = merge_dd("npc_occupation","npc_occupation_custom")
        session["npc_current_situation"] = merge_dd("npc_current_situation","npc_current_situation_custom")

        session["environment"] = merge_dd("environment","environment_custom")
        session["encounter_context"] = merge_dd("encounter_context","encounter_context_custom")

        # stats
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

        return redirect(url_for("interaction"))
    else:
        return render_template("personalize.html",
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

@app.route("/interaction", methods=["GET","POST"])
def interaction():
    if request.method=="GET":
        affection = session.get("affectionScore",0.0)
        trust = session.get("trustScore",5.0)
        mood = session.get("npcMood","Neutral")
        cstage = session.get("currentStage",1)
        st_label = STAGE_INFO[cstage]["label"]
        st_desc = STAGE_INFO[cstage]["desc"]
        nxt_thresh = session.get("nextStageThreshold",999)

        stage_unlocks = session.get("stage_unlocks",{})
        last_narration = session.get("narrationText","(No scene yet.)")
        scene_prompt = session.get("scene_image_prompt","")
        scene_url = session.get("scene_image_url",None)
        seed_used = session.get("scene_image_seed",None)

        dice_val = session.get("dice_debug_roll","(none)")
        outcome_val = session.get("dice_debug_outcome","(none)")
        interaction_log = session.get("interaction_log",[])

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
            user_action = request.form.get("user_action","").strip()
            if not user_action:
                user_action = "(no action)"

            affection = session.get("affectionScore",0.0)
            trust = session.get("trustScore",5.0)
            mood = session.get("npcMood","Neutral")
            cstage = session.get("currentStage",1)

            logs = session.get("interaction_log",[])
            full_history = "\n".join(logs)

            result_text = interpret_npc_state(
                affection=affection,
                trust=trust,
                npc_mood=mood,
                current_stage=cstage,
                last_user_action=user_action,
                full_history=full_history
            )

            dice_val = "(none)"
            outcome_val = "(none)"
            affect_delta = 0.0
            action_tier = "(none)"
            behavior_desc = ""
            narration_txt = ""
            image_prompt = ""

            lines = result_text.split("\n")
            for ln in lines:
                s = ln.strip()
                if s.startswith("AFFECT_CHANGE_FINAL:"):
                    try:
                        affect_delta = float(s.split(":",1)[1].strip())
                    except:
                        affect_delta = 0.0
                elif s.startswith("ACTION_TIER:"):
                    action_tier = s.split(":",1)[1].strip().lower()
                elif s.startswith("BEHAVIOR:"):
                    behavior_desc = s.split(":",1)[1].strip()
                elif s.startswith("NARRATION:"):
                    narration_txt = s.split(":",1)[1].strip()
                elif s.startswith("IMAGE_PROMPT:"):
                    image_prompt = s.split(":",1)[1].strip()

            new_aff = affection + affect_delta
            session["affectionScore"] = new_aff
            check_stage_up_down(new_aff)

            session["npcBehavior"] = behavior_desc
            session["narrationText"] = narration_txt
            session["scene_image_prompt"] = image_prompt

            logs.append(f"User: {user_action}")
            logs.append(f"Affect={affect_delta}, tier={action_tier}")
            logs.append(f"NARRATION => {narration_txt}")
            session["interaction_log"] = logs

            return redirect(url_for("interaction"))

        elif "update_npc" in request.form:
            def merge_dd(dd_key, cust_key):
                dd_val = request.form.get(dd_key,"").strip()
                c_val = request.form.get(cust_key,"").strip()
                return c_val if c_val else dd_val

            session["npc_name"] = merge_dd("npc_name","npc_name_custom")
            session["npc_gender"] = merge_dd("npc_gender","npc_gender_custom")
            session["npc_age"] = merge_dd("npc_age","npc_age_custom")
            session["npc_ethnicity"] = merge_dd("npc_ethnicity","npc_ethnicity_custom")
            session["npc_body_type"] = merge_dd("npc_body_type","npc_body_type_custom")
            session["npc_hair_color"] = merge_dd("npc_hair_color","npc_hair_color_custom")
            session["npc_hair_style"] = merge_dd("npc_hair_style","npc_hair_style_custom")
            session["npc_personality"] = merge_dd("npc_personality","npc_personality_custom")
            session["npc_clothing"] = merge_dd("npc_clothing","npc_clothing_custom")
            session["npc_occupation"] = merge_dd("npc_occupation","npc_occupation_custom")
            session["npc_current_situation"] = merge_dd("npc_current_situation","npc_current_situation_custom")

            session["environment"] = merge_dd("environment","environment_custom")
            session["encounter_context"] = merge_dd("encounter_context","encounter_context_custom")

            logs = session.get("interaction_log",[])
            logs.append("SYSTEM: NPC personalizations updated mid-game.")
            session["interaction_log"] = logs

            return redirect(url_for("interaction"))

        elif "update_affection" in request.form:
            new_val_str = request.form.get("affection_new","0.0").strip()
            try:
                new_val = float(new_val_str)
            except:
                new_val = 0.0
            session["affectionScore"] = new_val
            check_stage_up_down(new_val)

            logs = session.get("interaction_log",[])
            logs.append(f"SYSTEM: Affection manually set => {new_val}")
            session["interaction_log"] = logs
            return redirect(url_for("interaction"))

        elif "update_stage_unlocks" in request.form:
            su = session.get("stage_unlocks",{})
            for i in range(1,7):
                key = f"stage_unlock_{i}"
                new_text = request.form.get(key,"").strip()
                su[i] = new_text
            session["stage_unlocks"] = su

            logs = session.get("interaction_log",[])
            logs.append("SYSTEM: Stage unlock text updated mid-game.")
            session["interaction_log"] = logs
            return redirect(url_for("interaction"))

        elif "generate_scene_prompt" in request.form:
            # Auto-generate the single-sentence scene prompt
            logs = session.get("interaction_log",[])
            full_history = "\n".join(logs)

            auto_prompt = gpt_scene_image_prompt(full_history)
            session["scene_image_prompt"] = auto_prompt
            session["scene_image_url"] = None

            # DO NOT reset the seed => we want to keep old seed for re-generation
            # session["scene_image_seed"] = None  # <--- remove this line

            logs.append(f"[AUTO Scene Prompt] => {auto_prompt}")
            session["interaction_log"] = logs

            return redirect(url_for("interaction"))

        elif "do_generate_flux" in request.form:
            # "Generate Scene Image" => reuse old seed
            logs = session.get("interaction_log",[])
            prompt_text = request.form.get("scene_image_prompt","").strip()
            if not prompt_text:
                prompt_text = "(No prompt text)"

            existing_seed = session.get("scene_image_seed")
            if existing_seed:
                # Reuse the old seed
                seed_used = existing_seed
                logs.append("SYSTEM: Re-using old seed => " + str(existing_seed))
            else:
                # If no seed found, pick new random
                seed_used = random.randint(100000,999999)
                logs.append("SYSTEM: No existing seed => random => " + str(seed_used))

            url = generate_flux_image_safely(prompt_text, seed=seed_used)
            _save_image(url)

            session["scene_image_prompt"] = prompt_text
            session["scene_image_url"] = url
            session["scene_image_seed"] = seed_used

            logs.append(f"Scene Image Prompt => {prompt_text}")
            logs.append(f"Image seed={seed_used}")
            session["interaction_log"] = logs

            return redirect(url_for("interaction"))

        elif "new_seed" in request.form:
            # "New Seed" => always pick brand new random
            logs = session.get("interaction_log",[])
            prompt_text = request.form.get("scene_image_prompt","").strip()
            if not prompt_text:
                prompt_text = "(No prompt text)"

            new_seed_val = random.randint(100000,999999)
            logs.append("SYSTEM: user requested new random => " + str(new_seed_val))

            url = generate_flux_image_safely(prompt_text, seed=new_seed_val)
            _save_image(url)

            session["scene_image_prompt"] = prompt_text
            session["scene_image_url"] = url
            session["scene_image_seed"] = new_seed_val

            logs.append(f"Scene Image Prompt => {prompt_text}")
            logs.append(f"Image seed={new_seed_val}")
            session["interaction_log"] = logs

            return redirect(url_for("interaction"))

        else:
            return "Invalid submission in /interaction",400

@app.route("/view_image")
def view_image():
    return send_file(GENERATED_IMAGE_PATH, mimetype="image/jpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)