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
# A) Dropdown Lists
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
  "First date","Accidental meeting","Haven't met yet",
  "Happened to be in the same location","Group activity or event",
  "Work-related encounter","Other"
]
ETHNICITY_OPTIONS = [
  "American (Black)","American (White)","American (Hispanic)","Russian","German","Nigerian","Brazilian","Chinese",
  "Japanese","Indian","Australian","Canadian","British","French","Norwegian","Korean","Egyptian","Pakistani","Other"
]

############################################################################
# B) Stage Data
############################################################################

STAGE_INFO = {
    1: {
        "label": "Strangers",
        "desc": "Barely know each other; minimal personal info exchanged.",
        "privileges": "Polite small talk"
    },
    2: {
        "label": "Friendly Acquaintances",
        "desc": "Comfortable talking about casual interests.",
        "privileges": "Willing to share social media or short hangouts"
    },
    3: {
        "label": "Comfortable",
        "desc": "Sharing deeper personal stories, more trust established.",
        "privileges": "Could plan casual dates or personal meetups"
    },
    4: {
        "label": "Close",
        "desc": "Emotional trust built, frequent contact.",
        "privileges": "Potential romance or more intimate hangouts"
    },
    5: {
        "label": "Serious Potential",
        "desc": "On the verge of an official date/relationship.",
        "privileges": "Openly flirty, can plan more intimate experiences"
    },
    6: {
        "label": "In a Relationship",
        "desc": "Officially a couple with strong affection and trust.",
        "privileges": "Shared future plans, deep emotional support"
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
# C) Flask + Session Config
############################################################################

app = Flask(__name__)
app.config["SECRET_KEY"] = "YOUR_FLASK_SECRET"

# We define the session type and directory to avoid KeyError
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./.flask_sess"
app.config["SESSION_PERMANENT"] = False
Session(app)

# Ensure the session directory exists
os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
replicate.client.api_token = REPLICATE_API_TOKEN

GENERATED_IMAGE_PATH = "output.jpg"

############################################################################
# D) GPT Helpers: interpret_npc_state & generate_story_snippet
############################################################################

def interpret_npc_state(affection, trust, npc_mood, current_stage, last_user_action):
    """
    LLM Call #1: NPC's private thoughts/feelings => debug only.
    """
    system_message = {
        "role": "developer",
        "content": (
            "You are the NPC's internal mind. Summarize your hidden thoughts and feelings "
            "based on numeric stats + last user action. Then decide if you do anything, "
            "like approach or remain idle. Output ends with 'NEXT_PLAN: ...'."
        )
    }
    user_message = {
        "role": "user",
        "content": f"""
        Stats:
        affection={affection}, trust={trust}, npcMood={npc_mood}, stage={current_stage}
        Last user action: {last_user_action}

        Return a short monologue + 'NEXT_PLAN:' with your immediate plan (or 'no action').
        """
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def generate_story_snippet(affection, trust, npc_mood, current_stage,
                           last_user_action, npc_private_plan, full_history):
    """
    LLM Call #2: public user-facing snippet (3rd person from user's POV).
    """
    stage_label = STAGE_INFO[current_stage]["label"]
    stage_desc = STAGE_INFO[current_stage]["desc"]

    system_message = {
        "role": "developer",
        "content": f"""
        You are a romance story narrator in third-person from the user's POV.
        The NPC's hidden plan is: {npc_private_plan} (do not reveal internal thoughts).
        The user sees only outward behavior, body language, speech. 
        Relationship stage: {current_stage} ({stage_label}).
        {stage_desc}

        End with: "What does the user do next?" (~200 words).
        If NPC plan is 'no action', show minimal idle behavior.
        """
    }
    user_message = {
        "role": "user",
        "content": (
            f"FULL_HISTORY:\n{full_history}\n"
            f"Last user action: {last_user_action}\n"
            "Generate the next snippet from the user's POV, reflect the NPC's plan outwardly."
        )
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

############################################################################
# E) GPT for user actions & images
############################################################################

def gpt_user_actions(story_snippet):
    system_message = {
        "role": "developer",
        "content": "Provide 3 next user moves, each line '- SUGGESTION_USER:'."
    }
    user_message = {
        "role": "user",
        "content": (
            f"STORY:\n{story_snippet}\n\n"
            "Return 3 lines '- SUGGESTION_USER:' for possible user actions."
        )
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def parse_suggestions_user(gpt_text: str):
    lines = gpt_text.split("\n")
    suggestions = []
    for line in lines:
        if line.strip().startswith("- SUGGESTION_USER:"):
            val = line.split(":", 1)[1].strip()
            suggestions.append(val)
    return suggestions

def gpt_scene_image_prompt(full_history):
    system_message = {
        "role": "developer",
        "content": (
            "Generate a single-sentence iPhone portrait style prompt focusing on the NPC. "
            "No user mention. Summarize environment if relevant."
        )
    }
    user_message = {
        "role": "user",
        "content": f"STORY CONTEXT:\n{full_history}\n\nReturn a single sentence describing the NPC for a portrait."
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

############################################################################
# F) Stage Up/Down Logic
############################################################################

def check_stage_up_down(new_aff):
    current_stage = session.get("currentStage", 1)
    # if we drop below the requirement for current stage => revert
    req_for_stage = STAGE_REQUIREMENTS[current_stage]
    if new_aff < req_for_stage:
        new_stage = 1
        for s, needed in STAGE_REQUIREMENTS.items():
            if new_aff >= needed:
                new_stage = max(new_stage, s)
        session["currentStage"] = new_stage
    else:
        # possibly stage up
        while session["currentStage"] < 6:
            nxt = session["currentStage"] + 1
            if new_aff >= STAGE_REQUIREMENTS[nxt]:
                session["currentStage"] = nxt
            else:
                break

############################################################################
# G) Image Generation & Scene Stack
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
# H) Sentiment + Affection Utility
############################################################################

def gpt_sentiment_analysis(text: str) -> float:
    """
    A separate LLM call for sentiment classification, returning float in [0..1].
    """
    system_message = {
        "role": "developer",
        "content": (
            "You are a sentiment classifier. Read the user’s text and respond with a single decimal "
            "value from 0.0 to 1.0, no extra text."
        )
    }
    user_message = {
        "role": "user",
        "content": text
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.0
    )
    raw = response.choices[0].message.content.strip()
    try:
        val = float(raw)
    except ValueError:
        val = 0.5
    return max(0.0, min(val, 1.0))

def adjust_affection(positivity: float) -> float:
    """
    Partial increments/decrements:
    >=0.75 => +1
    >=0.5  => +0.5
    >=0.3  => 0
    >=0.1  => -0.5
    <0.1   => -1
    """
    if positivity >= 0.75:
        return 1.0
    elif positivity >= 0.5:
        return 0.5
    elif positivity >= 0.3:
        return 0.0
    elif positivity >= 0.1:
        return -0.5
    else:
        return -1.0

############################################################################
# I) Flask Routes
############################################################################

@app.route("/")
def home():
    return render_template("home.html", title="Destined Encounters")

@app.route("/restart")
def restart():
    session.clear()
    # ensure session file dir
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

        # init hidden stats
        session["affectionScore"] = 0.0
        session["trustScore"] = 5.0
        session["npcMood"] = "Neutral"
        session["currentStage"] = 1
        # small random threshold
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

    # no user action initially
    intro = generate_story_snippet(
        affection=session["affectionScore"],
        trust=session["trustScore"],
        npc_mood=session["npcMood"],
        current_stage=session["currentStage"],
        last_user_action="(none)",
        npc_private_plan="(none)",
        full_history=""
    )

    user_actions_text = gpt_user_actions(intro)
    user_suggestions = parse_suggestions_user(user_actions_text)

    store_scene(intro, user_action="", user_suggestions=user_suggestions)
    return redirect(url_for("story"))

@app.route("/story", methods=["GET","POST"])
def story():
    if request.method == "GET":
        data = current_scene()
        scene_text = data["scene_text"]
        user_suggestions = data["user_suggestions"]
        fh = full_story_text()
        scene_image_prompt = gpt_scene_image_prompt(fh)

        affection_score = session.get("affectionScore", 0.0)
        trust_score = session.get("trustScore", 5.0)
        npc_mood = session.get("npcMood", "Neutral")
        current_stage = session.get("currentStage", 1)
        next_threshold = session.get("nextStageThreshold", 999)
        last_positivity = session.get("lastPositivity", None)
        npc_private_thoughts = session.get("npcPrivateThoughts", "")

        stage_info = STAGE_INFO.get(current_stage, {})
        stage_label = stage_info.get("label","Unknown")
        stage_desc = stage_info.get("desc","N/A")

        return render_template(
            "story.html",
            title="Story",
            scene_text=scene_text,
            user_suggestions=user_suggestions,
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
            last_positivity=last_positivity,
            npc_private_thoughts=npc_private_thoughts
        )

    if "go_back" in request.form:
        pop_scene()
        return redirect(url_for("story"))

    data = current_scene()
    scene_text = data["scene_text"]
    user_suggestions = data["user_suggestions"]
    fh = full_story_text()
    scene_image_prompt = request.form.get("scene_image_prompt","")
    use_single_seed = session.get("use_single_seed", False)

    def update_affection_and_stage(action_text: str):
        positivity = gpt_sentiment_analysis(action_text)
        session["lastPositivity"] = positivity
        base_delta = adjust_affection(positivity)
        old_aff = session["affectionScore"]
        new_aff = old_aff + base_delta
        session["affectionScore"] = new_aff
        check_stage_up_down(new_aff)

    if "action_choice" in request.form:
        chosen_action = request.form.get("choice_gpt","(none)")
        update_affection_and_stage(chosen_action)

        # Call #1: private NPC thoughts
        npc_thoughts = interpret_npc_state(
            affection=session["affectionScore"],
            trust=session["trustScore"],
            npc_mood=session["npcMood"],
            current_stage=session["currentStage"],
            last_user_action=chosen_action
        )
        session["npcPrivateThoughts"] = npc_thoughts
        next_plan = "(none)"
        for line in npc_thoughts.split("\n"):
            if line.strip().startswith("NEXT_PLAN:"):
                next_plan = line.split(":",1)[1].strip()

        # Call #2: user-facing snippet
        new_snippet = generate_story_snippet(
            affection=session["affectionScore"],
            trust=session["trustScore"],
            npc_mood=session["npcMood"],
            current_stage=session["currentStage"],
            last_user_action=chosen_action,
            npc_private_plan=next_plan,
            full_history=fh
        )

        # new user actions
        new_user_actions_text = gpt_user_actions(new_snippet)
        new_user_suggestions = parse_suggestions_user(new_user_actions_text)

        store_scene(new_snippet, user_action=chosen_action, user_suggestions=new_user_suggestions)
        return redirect(url_for("story"))

    if "action_custom" in request.form:
        custom_action = request.form.get("user_action","(none)")
        update_affection_and_stage(custom_action)

        npc_thoughts = interpret_npc_state(
            affection=session["affectionScore"],
            trust=session["trustScore"],
            npc_mood=session["npcMood"],
            current_stage=session["currentStage"],
            last_user_action=custom_action
        )
        session["npcPrivateThoughts"] = npc_thoughts
        next_plan = "(none)"
        for line in npc_thoughts.split("\n"):
            if line.strip().startswith("NEXT_PLAN:"):
                next_plan = line.split(":",1)[1].strip()

        new_snippet = generate_story_snippet(
            affection=session["affectionScore"],
            trust=session["trustScore"],
            npc_mood=session["npcMood"],
            current_stage=session["currentStage"],
            last_user_action=custom_action,
            npc_private_plan=next_plan,
            full_history=fh
        )

        new_user_actions_text = gpt_user_actions(new_snippet)
        new_user_suggestions = parse_suggestions_user(new_user_actions_text)

        store_scene(new_snippet, user_action=custom_action, user_suggestions=new_user_suggestions)
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
            user_suggestions=user_suggestions,
            scene_image_prompt=scene_image_prompt,
            scene_image_generated=True,
            seed_used=seed_used,
            affection_score=session.get("affectionScore",0),
            trust_score=session.get("trustScore",5),
            npc_mood=session.get("npcMood","Neutral"),
            current_stage=session.get("currentStage",1),
            next_threshold=session.get("nextStageThreshold",999),
            last_positivity=session.get("lastPositivity",None),
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
            user_suggestions=user_suggestions,
            scene_image_prompt=prompt,
            scene_image_generated=True,
            seed_used=seed_used,
            affection_score=session.get("affectionScore",0),
            trust_score=session.get("trustScore",5),
            npc_mood=session.get("npcMood","Neutral"),
            current_stage=session.get("currentStage",1),
            next_threshold=session.get("nextStageThreshold",999),
            last_positivity=session.get("lastPositivity",None),
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
            user_suggestions=user_suggestions,
            scene_image_prompt=prompt,
            scene_image_generated=True,
            seed_used=seed_used,
            affection_score=session.get("affectionScore",0),
            trust_score=session.get("trustScore",5),
            npc_mood=session.get("npcMood","Neutral"),
            current_stage=session.get("currentStage",1),
            next_threshold=session.get("nextStageThreshold",999),
            last_positivity=session.get("lastPositivity",None),
            npc_private_thoughts=session.get("npcPrivateThoughts","")
        )

    return "Invalid request in /story", 400

@app.route("/view_image")
def view_image():
    return send_file(GENERATED_IMAGE_PATH, mimetype="image/jpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)