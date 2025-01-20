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
# 1) DROPDOWN LISTS (Unchanged)
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
# 2) UPDATED STAGE DATA (Removing 'Intimate' & Setting Limits)
############################################################################

STAGE_INFO = {
    1: {
        "label": "Strangers",
        "desc": (
            "They've just met and know almost nothing about each other. Likely won't share personal info "
            "or phone numbers. Conversation remains polite but cautious."
        )
    },
    2: {
        "label": "Friendly Acquaintances",
        "desc": (
            "They're comfortable with casual chatting, might exchange social media handles. "
            "Still keep big personal boundaries. Not ready for deep personal topics."
        )
    },
    3: {
        "label": "Comfortable",
        "desc": (
            "They trust each other enough to share personal stories or minor struggles. "
            "They might plan casual dates and exchange phone numbers. "
            "Not ready for big commitments like living together."
        )
    },
    4: {
        "label": "Close",
        "desc": (
            "Emotional trust built, frequent contact. They feel safe spending time alone together. "
            "Could discuss future possibilities but not firmly making big life decisions yet."
        )
    },
    5: {
        "label": "Serious Potential",
        "desc": (
            "Deep connection, openly affectionate, discussing possible plans for the future. "
            "They rely on each other for emotional support. Might consider living together soon."
        )
    },
    6: {
        "label": "Committed Relationship",
        "desc": (
            "They see each other as life partners, with strong devotion and shared long-term goals. "
            "Marriage or full partnership is openly on the table."
        )
    }
}

STAGE_REQUIREMENTS = {
    1: 0,
    2: 5,
    3: 10,
    4: 15,
    5: 20,
    6: 25
}

############################################################################
# 3) Flask & Session Config
############################################################################

app = Flask(__name__)
app.config["SECRET_KEY"] = "destined_encounters_2024_secure"
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
# 4) Build Personalization String
############################################################################

def build_personalization_string():
    user_part = f"""
    USER:
      Name: {session.get('user_name','?')}
      Age: {session.get('user_age','?')}
      Personality: {session.get('user_personality','?')}
      Background: {session.get('user_background','?')}
    """

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

    return user_part + "\n" + npc_part + "\n" + env_part

############################################################################
# 5) interpret_npc_state (Now includes trust)
############################################################################

def interpret_npc_state(affection, trust, current_stage, last_user_action):
    """
    LLM call that returns a short paragraph plus lines:
      AFFECT_CHANGE: float
      TRUST_CHANGE: float
      EMOTIONAL_STATE: ...
      BEHAVIOUR: ...
      NEXT_PLAN: ...
    We incorporate both affection & trust in the system prompt.
    """
    personalization = build_personalization_string()

    stage_label = STAGE_INFO[current_stage]["label"]
    stage_desc = STAGE_INFO[current_stage]["desc"]

    system_message = {
        "role": "developer",
        "content": f"""
        You are the NPC's internal mind.

        {personalization}

        Current Affection: {affection}
        Current Trust: {trust}
        Relationship Stage: {current_stage} ({stage_label})
        {stage_desc}

        The user just performed this action: {last_user_action}

        1) Provide a short monologue on how the NPC internally feels.
        2) Then produce lines:
           AFFECT_CHANGE: -1.0..+1.0
           TRUST_CHANGE: -1.0..+1.0  (0..10 scale, so a big negative might push trust close to 0)
           EMOTIONAL_STATE: ...
           BEHAVIOUR: ...
           NEXT_PLAN: ...
        """
    }
    user_message = {
        "role": "user",
        "content": "Return your internal monologue plus those lines as described."
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

############################################################################
# 6) generate_story_snippet
############################################################################

def generate_story_snippet(affection, trust, current_stage, last_user_action, npc_private_plan, full_history):
    """
    We incorporate both affection & trust in the context if needed.
    The snippet remains from the user's POV, 3rd person.
    """
    personalization = build_personalization_string()
    stage_label = STAGE_INFO[current_stage]["label"]
    stage_desc = STAGE_INFO[current_stage]["desc"]

    system_message = {
        "role": "developer",
        "content": f"""
        You are a romance story narrator in third-person from the user's POV.

        Relationship Stage: {current_stage} ({stage_label})
        {stage_desc}

        The NPC's hidden plan is: {npc_private_plan} (do not reveal as internal monologue).
        {personalization}

        End with: 'What does the user do next?' (~200 words).
        If plan='no action', show minimal or idle behavior.
        """
    }
    user_message = {
        "role": "user",
        "content": (
            f"FULL_HISTORY:\n{full_history}\n\n"
            f"USER's LAST ACTION: {last_user_action}\n"
            "Generate the next snippet from the user's POV."
        )
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

############################################################################
# 7) GPT for NPC portrait
############################################################################

def gpt_npc_portrait_prompt():
    """
    Summarize the NPC's physical appearance in 1-2 lines
    """
    npc_gender = session.get("npc_gender","Female")
    npc_age = session.get("npc_age","25")
    npc_eth = session.get("npc_ethnicity","?")
    npc_body = session.get("npc_body_type","?")
    npc_hc = session.get("npc_hair_color","?")
    npc_hs = session.get("npc_hair_style","?")
    npc_cloth = session.get("npc_clothing","?")

    system_message = {
        "role": "developer",
        "content": (
            "Return a single short portrait prompt describing the NPC physically. "
            "No mention of user. 1-2 lines max."
        )
    }
    user_message = {
        "role": "user",
        "content": f"""
        NPC:
          Gender: {npc_gender}
          Age: {npc_age}
          Ethnicity: {npc_eth}
          Body Type: {npc_body}
          Hair Color: {npc_hc}
          Hair Style: {npc_hs}
          Clothing: {npc_cloth}
        """
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

############################################################################
# 8) gpt_scene_image_prompt
############################################################################

def gpt_scene_image_prompt(full_history):
    """
    Single-sentence iPhone portrait focusing on the NPC in the environment.
    No user mention.
    """
    system_message = {
        "role": "developer",
        "content": (
            "Generate a single-sentence iPhone portrait style prompt focusing on the NPC. "
            "No mention of user. Summarize environment if relevant."
        )
    }
    user_message = {
        "role": "user",
        "content": (
            f"STORY CONTEXT:\n{full_history}\n\n"
            "Return a single sentence describing the NPC for a portrait."
        )
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

############################################################################
# 9) Stage Up/Down
############################################################################

def check_stage_up_down(new_aff):
    current_stage = session.get("currentStage", 1)
    req_for_stage = STAGE_REQUIREMENTS[current_stage]
    if new_aff < req_for_stage:
        # revert stage
        new_stage = 1
        for s, needed in STAGE_REQUIREMENTS.items():
            if new_aff >= needed:
                new_stage = max(new_stage, s)
        session["currentStage"] = new_stage
    else:
        # maybe stage up
        while session["currentStage"] < 6:
            nxt = session["currentStage"] + 1
            if new_aff >= STAGE_REQUIREMENTS[nxt]:
                session["currentStage"] = nxt
            else:
                break

############################################################################
# 10) Image Gen & Scene
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

def store_scene(scene_text, user_action="", user_suggestions=None):
    if user_suggestions is None:
        user_suggestions = []
    stack = session.setdefault("scene_stack", [])
    stack.append({
        "scene_text": scene_text,
        "user_action": user_action,
        "user_suggestions": user_suggestions
    })
    session["scene_stack"] = stack

def pop_scene():
    stack = session.get("scene_stack", [])
    if len(stack) > 1:
        stack.pop()
    session["scene_stack"] = stack

def current_scene():
    stack = session.get("scene_stack", [])
    if stack:
        return stack[-1]
    return {
        "scene_text": "",
        "user_action": "",
        "user_suggestions": []
    }

def full_story_text():
    stack = session.get("scene_stack", [])
    lines = []
    for s in stack:
        if s["user_action"]:
            lines.append(f"User chose: {s['user_action']}")
        lines.append(s["scene_text"])
    return "\n\n".join(lines)

############################################################################
# 11) Flask Routes
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

        session["environment"] = merge_dropdown("environment","environment_custom")
        session["encounter_context"] = merge_dropdown("encounter_context","encounter_context_custom")

        use_single_seed = (request.form.get("use_single_seed","") == "yes")
        session["use_single_seed"] = use_single_seed
        if use_single_seed:
            session["global_seed"] = random.randint(100000,999999)

        # Initialize hidden stats
        session["affectionScore"] = 0.0
        session["trustScore"] = 5.0  # We start trust at 5/10
        session["npcMood"] = "Neutral"
        session["currentStage"] = 1
        session["nextStageThreshold"] = session["affectionScore"] + random.randint(2,4)
        session["npcPrivateThoughts"] = "(none)"

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
        prompt = gpt_npc_portrait_prompt()
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
    session["scene_stack"] = []

    intro = generate_story_snippet(
        affection=session["affectionScore"],
        trust=session["trustScore"],
        current_stage=session["currentStage"],
        last_user_action="(none)",
        npc_private_plan="(none)",
        full_history=""
    )

    # We no longer do user_suggestions from GPT here. We'll rely on the user custom input only.
    store_scene(intro, user_action="", user_suggestions=[])
    return redirect(url_for("story"))

@app.route("/story", methods=["GET","POST"])
def story():
    if request.method == "GET":
        data = current_scene()
        scene_text = data["scene_text"]
        fh = full_story_text()
        scene_image_prompt = gpt_scene_image_prompt(fh)

        affection_score = session.get("affectionScore", 0.0)
        trust_score = session.get("trustScore", 5.0)
        npc_mood = session.get("npcMood", "Neutral")
        current_stage = session.get("currentStage", 1)
        stage_label = STAGE_INFO[current_stage]["label"]
        stage_desc = STAGE_INFO[current_stage]["desc"]
        next_threshold = session.get("nextStageThreshold", 999)
        npc_private_thoughts = session.get("npcPrivateThoughts", "")

        return render_template(
            "story.html",
            title="Story",
            scene_text=scene_text,
            scene_image_prompt=scene_image_prompt,
            scene_image_generated=False,
            seed_used=None,
            affection_score=affection_score,
            trust_score=trust_score,
            npc_mood=npc_mood,
            current_stage=current_stage,
            stage_label=stage_label,
            stage_desc=stage_desc,
            next_threshold=next_threshold,
            npc_private_thoughts=npc_private_thoughts
        )

    # POST
    if "go_back" in request.form:
        pop_scene()
        return redirect(url_for("story"))

    data = current_scene()
    scene_text = data["scene_text"]
    fh = full_story_text()
    scene_image_prompt = request.form.get("scene_image_prompt","")
    use_single_seed = session.get("use_single_seed", False)

    def update_stats(affect_str, trust_str):
        # parse the two lines
        try:
            affect_val = float(affect_str)
        except ValueError:
            affect_val = 0.0
        try:
            trust_val = float(trust_str)
        except ValueError:
            trust_val = 0.0

        old_aff = session["affectionScore"]
        new_aff = old_aff + affect_val
        session["affectionScore"] = new_aff
        check_stage_up_down(new_aff)

        # update trust
        # clamp trust in [0..10]
        old_trust = session["trustScore"]
        new_trust = old_trust + trust_val
        new_trust = max(0.0, min(10.0, new_trust))
        session["trustScore"] = new_trust

    if "action_custom" in request.form:
        custom_action = request.form.get("user_action","").strip()
        if not custom_action:
            # interpret as "(none)"
            custom_action = "(none)"

        # interpret npc state
        npc_thoughts = interpret_npc_state(
            affection=session["affectionScore"],
            trust=session["trustScore"],
            current_stage=session["currentStage"],
            last_user_action=custom_action
        )

        # parse lines
        lines = npc_thoughts.split("\n")
        affect_change = "0.0"
        trust_change = "0.0"
        npc_mood = session.get("npcMood","Neutral")
        npc_behaviour = ""
        next_plan = "no action"
        stripped_paragraph = []

        for line in lines:
            stripline = line.strip()
            if stripline.startswith("AFFECT_CHANGE:"):
                affect_change = stripline.split(":",1)[1].strip()
            elif stripline.startswith("TRUST_CHANGE:"):
                trust_change = stripline.split(":",1)[1].strip()
            elif stripline.startswith("EMOTIONAL_STATE:"):
                npc_mood = stripline.split(":",1)[1].strip()
            elif stripline.startswith("BEHAVIOUR:"):
                npc_behaviour = stripline.split(":",1)[1].strip()
            elif stripline.startswith("NEXT_PLAN:"):
                next_plan = stripline.split(":",1)[1].strip()
            else:
                stripped_paragraph.append(stripline)

        # update affection & trust
        update_stats(affect_change, trust_change)
        session["npcMood"] = npc_mood

        final_private_thoughts = (
            "\n".join(stripped_paragraph)
            + f"\n\nAFFECT_CHANGE: {affect_change}"
            + f"\nTRUST_CHANGE: {trust_change}"
            + f"\nEMOTIONAL_STATE: {npc_mood}"
            + f"\nBEHAVIOUR: {npc_behaviour}"
            + f"\nNEXT_PLAN: {next_plan}"
        )
        session["npcPrivateThoughts"] = final_private_thoughts

        # generate new snippet
        new_snippet = generate_story_snippet(
            affection=session["affectionScore"],
            trust=session["trustScore"],
            current_stage=session["currentStage"],
            last_user_action=custom_action,
            npc_private_plan=next_plan,
            full_history=fh
        )

        store_scene(new_snippet, user_action=custom_action, user_suggestions=[])
        return redirect(url_for("story"))

    if "generate_scene_image" in request.form:
        seed_used = session["global_seed"] if use_single_seed else random.randint(100000,999999)
        image_url = generate_flux_image(scene_image_prompt, seed=seed_used)
        _save_image(image_url)
        session["last_scene_prompt"] = scene_image_prompt
        session["last_image_seed"] = seed_used

        return render_template(
            "story.html",
            title="Story",
            scene_text=scene_text,
            scene_image_prompt=scene_image_prompt,
            scene_image_generated=True,
            seed_used=seed_used,
            affection_score=session.get("affectionScore",0),
            trust_score=session.get("trustScore",5.0),
            npc_mood=session.get("npcMood","Neutral"),
            current_stage=session.get("currentStage",1),
            stage_label=STAGE_INFO[session.get("currentStage",1)]["label"],
            stage_desc=STAGE_INFO[session.get("currentStage",1)]["desc"],
            next_threshold=session.get("nextStageThreshold",999),
            npc_private_thoughts=session.get("npcPrivateThoughts","")
        )

    if "regen_scene_same_seed" in request.form:
        prompt = session.get("last_scene_prompt", scene_image_prompt)
        seed_used = session.get("last_image_seed", None)
        if not seed_used:
            seed_used = session["global_seed"] if use_single_seed else random.randint(100000,999999)
        image_url = generate_flux_image(prompt, seed=seed_used)
        _save_image(image_url)
        session["last_image_seed"] = seed_used

        return render_template(
            "story.html",
            title="Story",
            scene_text=scene_text,
            scene_image_prompt=prompt,
            scene_image_generated=True,
            seed_used=seed_used,
            affection_score=session.get("affectionScore",0),
            trust_score=session.get("trustScore",5.0),
            npc_mood=session.get("npcMood","Neutral"),
            current_stage=session.get("currentStage",1),
            stage_label=STAGE_INFO[session.get("currentStage",1)]["label"],
            stage_desc=STAGE_INFO[session.get("currentStage",1)]["desc"],
            next_threshold=session.get("nextStageThreshold",999),
            npc_private_thoughts=session.get("npcPrivateThoughts","")
        )

    if "regen_scene_new_seed" in request.form:
        prompt = session.get("last_scene_prompt", scene_image_prompt)
        seed_used = random.randint(100000,999999)
        image_url = generate_flux_image(prompt, seed=seed_used)
        _save_image(image_url)
        session["last_image_seed"] = seed_used

        return render_template(
            "story.html",
            title="Story",
            scene_text=scene_text,
            scene_image_prompt=prompt,
            scene_image_generated=True,
            seed_used=seed_used,
            affection_score=session.get("affectionScore",0),
            trust_score=session.get("trustScore",5.0),
            npc_mood=session.get("npcMood","Neutral"),
            current_stage=session.get("currentStage",1),
            stage_label=STAGE_INFO[session.get("currentStage",1)]["label"],
            stage_desc=STAGE_INFO[session.get("currentStage",1)]["desc"],
            next_threshold=session.get("nextStageThreshold",999),
            npc_private_thoughts=session.get("npcPrivateThoughts","")
        )

    return "Invalid request in /story", 400

@app.route("/view_image")
def view_image():
    return send_file(GENERATED_IMAGE_PATH, mimetype="image/jpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)