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
# 1) DROPDOWN LISTS
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
# 2) STAGE DATA => [0,2,5,7,10,15]
############################################################################

STAGE_INFO = {
    1: {"label": "Strangers", "desc": "They barely know each other."},
    2: {"label": "Casual Acquaintances", "desc": "Some superficial chatting, no real depth yet."},
    3: {"label": "Comfortable", "desc": "Can share moderate personal info, plan small outings."},
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

############################################################################
# 3) Flask & Session Config (SECRET_KEY set first)
############################################################################

app = Flask(__name__)
app.config["SECRET_KEY"] = "abc123supersecret"  # fix session usage
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
# 5) interpret_npc_state => SPOKEN_DIALOGUE
############################################################################

def interpret_npc_state(affection, trust, npc_mood, current_stage, last_user_action):
    stage_label = STAGE_INFO[current_stage]["label"]
    stage_desc = STAGE_INFO[current_stage]["desc"]
    personalization = build_personalization_string()

    system_msg = f"""
    You are the NPC's internal mind.
    Relationship Stage={current_stage} ({stage_label})
    {stage_desc}

    Current Affection={affection}, Trust={trust}, npcMood={npc_mood}.
    The user just performed: {last_user_action}.

    Provide an internal monologue, then lines:
      SPOKEN_DIALOGUE: (NPC's outward speech or empty)
      AFFECT_CHANGE: -1..+1
      TRUST_CHANGE: -1..+1
      EMOTIONAL_STATE: ...
      BEHAVIOUR: ...
    (Do not speak for the user.)
    """
    user_msg = f"PERSONALIZATION:\n{personalization}\nReturn your internal monologue + lines exactly."

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"developer","content":system_msg},
            {"role":"user","content":user_msg}
        ],
        temperature=0.7
    )
    return resp.choices[0].message.content.strip()

############################################################################
# 6) generate_story_snippet => no user speech unless typed
############################################################################

def generate_story_snippet(affection, trust, npc_mood, current_stage,
                           last_user_action, spoken_dialogue, full_history,
                           is_intro=False):
    """
    'Never invent user speech or actions that weren't typed.'
    """
    stage_label = STAGE_INFO[current_stage]["label"]
    stage_desc = STAGE_INFO[current_stage]["desc"]
    personalization = build_personalization_string()

    if is_intro:
        sys_content = f"""
        You are a romance story narrator, from the user's POV. 
        This is an introductory scene focusing on environment, user, NPC meeting. ~200 words.
        End with: "What does the user do next?"
        The user is passive except for typed actions. 
        Do not invent user speech beyond the user’s typed lines.
        Relationship stage=1 (Strangers).
        {personalization}
        """
    else:
        sys_content = f"""
        You are a romance story narrator in third-person from the user's POV.

        Relationship Stage={current_stage} ({stage_label})
        {stage_desc}

        {personalization}

        End with: "What does the user do next?" (~200 words).
        If the NPC has no big action, show minimal idle from them.
        Never invent user speech or actions that weren't typed. 
        The user is passive except for typed actions.
        """

    user_content = (
        f"FULL_HISTORY:\n{full_history}\n\n"
        f"USER's LAST ACTION: {last_user_action}\n"
        f"NPC SPOKEN_DIALOGUE: {spoken_dialogue}\n"
        "Continue the snippet from the user's POV, referencing that spoken dialogue if relevant. "
        "Again, do NOT invent any user speech or actions that weren't typed."
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"developer","content": sys_content},
            {"role":"user","content": user_content}
        ],
        temperature=0.7
    )
    return resp.choices[0].message.content.strip()

############################################################################
# 7) scene image
############################################################################

def gpt_scene_image_prompt(full_history):
    npc_age = session.get("npc_age","?")
    npc_eth = session.get("npc_ethnicity","?")
    env_loc = session.get("environment","?")
    sys_content = f"""
    Generate a single-sentence iPhone portrait style prompt focusing on the NPC (age={npc_age}, ethnicity={npc_eth}).
    If environment={env_loc}, reference it. No user mention.
    """
    user_content = f"STORY CONTEXT:\n{full_history}\nOne line describing the NPC in environment."

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"developer","content":sys_content},
            {"role":"user","content":user_content}
        ],
        temperature=0.7
    )
    return resp.choices[0].message.content.strip()

############################################################################
# 8) Stage Up/Down => nextStageThreshold
############################################################################

def check_stage_up_down(new_aff):
    cur_st = session.get("currentStage",1)
    req = STAGE_REQUIREMENTS[cur_st]
    if new_aff < req:
        new_stage = 1
        for s, needed in STAGE_REQUIREMENTS.items():
            if new_aff >= needed:
                new_stage = max(new_stage,s)
        session["currentStage"] = new_stage
    else:
        while session["currentStage"]<6:
            nxt = session["currentStage"]+1
            if new_aff>=STAGE_REQUIREMENTS[nxt]:
                session["currentStage"] = nxt
            else:
                break

    # compute next threshold
    st = session["currentStage"]
    if st<6:
        session["nextStageThreshold"] = STAGE_REQUIREMENTS[st+1]
    else:
        session["nextStageThreshold"] = 999

############################################################################
# 9) Image Gen & Scene Stack
############################################################################

def generate_flux_image(prompt, seed=None):
    replicate_input = {
        "prompt": prompt,
        "raw": True,
        "safety_tolerance": 6
    }
    if seed is not None:
        replicate_input["seed"] = seed
    return replicate.run("black-forest-labs/flux-1.1-pro-ultra", input=replicate_input)

def _save_image(url):
    r = requests.get(url)
    with open("output.jpg","wb") as f:
        f.write(r.content)

def store_scene(scene_text, user_action=""):
    st = session.setdefault("scene_stack",[])
    st.append({
        "scene_text": scene_text,
        "user_action": user_action
    })
    session["scene_stack"] = st

def pop_scene():
    st = session.get("scene_stack",[])
    if len(st)>1:
        st.pop()
    session["scene_stack"] = st

def current_scene():
    st = session.get("scene_stack",[])
    if st:
        return st[-1]
    return {"scene_text":"","user_action":""}

def full_story_text():
    lines=[]
    for s in session.get("scene_stack",[]):
        if s["user_action"]:
            lines.append(f"User: {s['user_action']}")
        lines.append(s["scene_text"])
    return "\n\n".join(lines)

############################################################################
# 10) Flask Routes
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
            c_val = request.form.get(custom_key,"").strip()
            return c_val if c_val else dd_val

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
        session["nextStageThreshold"] = STAGE_REQUIREMENTS[2]  # from stage1 => next=2 =>2

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
    if request.method=="GET":
        prompt = (
            f"Portrait of {session.get('npc_name','?')}, age {session.get('npc_age','?')}, "
            f"ethnicity {session.get('npc_ethnicity','?')} wearing {session.get('npc_clothing','?')}. "
            "Photo-realistic style."
        )
        session["npc_image_prompt"] = prompt
        return render_template("npc_image.html",
                               title="NPC Portrait",
                               npc_image_prompt=prompt,
                               npc_image_url=None,
                               seed_used=None)

    prompt = request.form.get("npc_image_prompt","")
    session["npc_image_prompt"] = prompt
    use_single_seed = session.get("use_single_seed", False)

    if "generate_npc_image" in request.form:
        seed_used = session["global_seed"] if use_single_seed else random.randint(100000,999999)
        url = generate_flux_image(prompt, seed=seed_used)
        _save_image(url)
        session["last_image_seed"] = seed_used
        return render_template("npc_image.html",
                               title="NPC Portrait",
                               npc_image_prompt=prompt,
                               npc_image_url=url,
                               seed_used=seed_used)
    if "regenerate_same_seed" in request.form:
        seed_used = session.get("last_image_seed",None)
        if not seed_used:
            seed_used = session["global_seed"] if use_single_seed else random.randint(100000,999999)
        url = generate_flux_image(prompt, seed=seed_used)
        _save_image(url)
        session["last_image_seed"] = seed_used
        return render_template("npc_image.html",
                               title="NPC Portrait",
                               npc_image_prompt=prompt,
                               npc_image_url=url,
                               seed_used=seed_used)
    if "regenerate_new_seed" in request.form:
        seed_used = random.randint(100000,999999)
        url = generate_flux_image(prompt, seed=seed_used)
        _save_image(url)
        session["last_image_seed"] = seed_used
        return render_template("npc_image.html",
                               title="NPC Portrait",
                               npc_image_prompt=prompt,
                               npc_image_url=url,
                               seed_used=seed_used)

    return "Invalid request in npc_image", 400

@app.route("/start_story")
def start_story():
    session["scene_stack"] = []
    # produce an environment-intro snippet
    intro = generate_story_snippet(
        affection=session["affectionScore"],
        trust=session["trustScore"],
        npc_mood=session["npcMood"],
        current_stage=session["currentStage"],
        last_user_action="(none)",
        spoken_dialogue="(none)",
        full_history="",
        is_intro=True
    )
    store_scene(intro, user_action="(none)")
    return redirect(url_for("story"))

@app.route("/story", methods=["GET","POST"])
def story():
    if request.method=="GET":
        data = current_scene()
        scene_text = data["scene_text"]
        fh = full_story_text()
        scene_image_prompt = gpt_scene_image_prompt(fh)

        aff = session["affectionScore"]
        trust = session["trustScore"]
        mood = session["npcMood"]
        cstage = session["currentStage"]
        st_label = STAGE_INFO[cstage]["label"]
        st_desc = STAGE_INFO[cstage]["desc"]
        nxt_thresh = session.get("nextStageThreshold",999)
        npc_priv = session.get("npcPrivateThoughts","")

        return render_template("story.html",
                               title="Story",
                               scene_text=scene_text,
                               scene_image_prompt=scene_image_prompt,
                               scene_image_generated=False,
                               seed_used=None,
                               affection_score=aff,
                               trust_score=trust,
                               npc_mood=mood,
                               current_stage=cstage,
                               stage_label=st_label,
                               stage_desc=st_desc,
                               next_threshold=nxt_thresh,
                               npc_private_thoughts=npc_priv)

    if "go_back" in request.form:
        pop_scene()
        return redirect(url_for("story"))

    data = current_scene()
    scene_text = data["scene_text"]
    fh = full_story_text()
    scene_image_prompt = request.form.get("scene_image_prompt","")
    use_single_seed = session.get("use_single_seed", False)

    custom_action = request.form.get("user_action","").strip()
    if not custom_action:
        custom_action = "(none)"

    # 1) NPC private thoughts
    npc_result = interpret_npc_state(
        affection=session["affectionScore"],
        trust=session["trustScore"],
        npc_mood=session["npcMood"],
        current_stage=session["currentStage"],
        last_user_action=custom_action
    )
    lines = npc_result.split("\n")
    spoken_dialogue = ""
    affchg = "0.0"
    trustchg = "0.0"
    new_mood = session["npcMood"]

    for ln in lines:
        s=ln.strip()
        if s.startswith("SPOKEN_DIALOGUE:"):
            spoken_dialogue = s.split(":",1)[1].strip()
        elif s.startswith("AFFECT_CHANGE:"):
            affchg = s.split(":",1)[1].strip()
        elif s.startswith("TRUST_CHANGE:"):
            trustchg = s.split(":",1)[1].strip()
        elif s.startswith("EMOTIONAL_STATE:"):
            new_mood = s.split(":",1)[1].strip()

    # update affection/trust
    def update_stats(a_str,t_str):
        try: da=float(a_str)
        except: da=0.0
        new_a=session["affectionScore"]+da
        session["affectionScore"]=new_a
        check_stage_up_down(new_a)

        try: dt=float(t_str)
        except: dt=0.0
        new_t=session["trustScore"]+dt
        new_t=max(0.0, min(15.0,new_t))
        session["trustScore"]=new_t

    update_stats(affchg,trustchg)
    session["npcMood"]=new_mood
    session["npcPrivateThoughts"]=npc_result

    # 2) user-facing snippet => incorporate spoken dialogue
    new_snippet = generate_story_snippet(
        affection=session["affectionScore"],
        trust=session["trustScore"],
        npc_mood=session["npcMood"],
        current_stage=session["currentStage"],
        last_user_action=custom_action,
        spoken_dialogue=spoken_dialogue,
        full_history=fh,
        is_intro=False
    )

    store_scene(new_snippet, user_action=custom_action)
    return redirect(url_for("story"))

@app.route("/view_image")
def view_image():
    return send_file(GENERATED_IMAGE_PATH, mimetype="image/jpeg")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)