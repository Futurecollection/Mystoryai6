import os
import replicate
import requests
import random

# NEW OPENAI LIBRARY SYNTAX
from openai import OpenAI

from flask import (
    Flask, request, render_template_string,
    session, redirect, url_for, send_file
)
from flask_session import Session

#############################
# 1) FLASK & SERVER-SIDE SESSION CONFIG
#############################

app = Flask(__name__)
app.config["SECRET_KEY"] = "YOUR_FLASK_SECRET_HERE"

# Configure server-side sessions via Flask-Session
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./.flask_sess"
app.config["SESSION_PERMANENT"] = False
Session(app)

#############################
# 2) SET UP CLIENTS & GLOBALS
#############################

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
replicate.client.api_token = REPLICATE_API_TOKEN

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

GENERATED_IMAGE_PATH = "output.jpg"

# Example dropdown suggestions
BODY_TYPE_OPTIONS = ["Slender", "Curvy", "Athletic", "Muscular"]
HAIR_COLOR_OPTIONS = ["Blonde", "Brunette", "Black", "Red"]
ETHNICITY_OPTIONS = ["Caucasian", "Hispanic", "African", "Asian"]
PERSONALITY_OPTIONS = ["Shy", "Outgoing", "Sarcastic", "Friendly"]
ENVIRONMENT_OPTIONS = ["Busy Gym", "Quiet Cafe", "Crowded City Street", "Scenic Park"]

#############################
# 3) BOOTSTRAP-ENABLED LAYOUT & PAGE TEMPLATES
#############################

# -- Base Layout (corrected CSS to avoid Jinja syntax errors) --
BASE_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
  <title>{{ title|default("Romance Demo") }}</title>
  <!-- Bootstrap CSS (via CDN) -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
  <style>
    body {
      padding: 2rem;
      background: #f8f9fa;
    }
    .container {
      max-width: 800px;
      margin: auto;
      background: #fff;
      padding: 2rem;
      border-radius: 6px;
      box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    h1, h2, h3 {
      font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    }
    pre {
      background: #eee;
      padding: 1rem;
      border-radius: 5px;
    }
  </style>
</head>
<body>
<div class="container">
  {% block content %}{% endblock %}
</div>
</body>
</html>
"""

# -- Home Page --
HOME_PAGE = """
{% extends "base" %}
{% block content %}
  <h1 class="mb-4">Romance Roleplay Demo (Server-Side Session)</h1>
  <p>Welcome! This app uses GPT-4o-mini for story + prompts, Flux for images, and server-side sessions so we can handle long stories without cookie issues.</p>
  <a href="/restart" class="btn btn-primary">Start / Restart</a>
{% endblock %}
"""

# -- Personalization Page --
PERSONALIZE_PAGE = """
{% extends "base" %}
{% block content %}
  <h1>Personalize Your Adventure</h1>
  <form method="POST" class="row g-3">
    <div class="col-md-6">
      <h3>Your Info</h3>
      <label class="form-label">Name</label>
      <input type="text" class="form-control" name="user_name" placeholder="Your Name">

      <label class="form-label mt-2">Age</label>
      <input type="text" class="form-control" name="user_age" placeholder="Your Age">

      <label class="form-label mt-2">Personality</label>
      <select class="form-select" name="user_personality">
        <option value="">--Select--</option>
        {% for opt in personality_options %}
          <option value="{{ opt }}">{{ opt }}</option>
        {% endfor %}
      </select>
      <label class="form-label mt-1">Or custom:</label>
      <input type="text" class="form-control" name="user_personality_custom" placeholder="Type custom">

      <label class="form-label mt-2">Background</label>
      <textarea class="form-control" name="user_background" rows="3"></textarea>
    </div>

    <div class="col-md-6">
      <h3>NPC Info</h3>
      <label class="form-label">Name</label>
      <input type="text" class="form-control" name="npc_name" placeholder="NPC Name">

      <label class="form-label mt-2">Age</label>
      <input type="text" class="form-control" name="npc_age" placeholder="NPC Age">

      <label class="form-label mt-2">Ethnicity</label>
      <select class="form-select" name="npc_ethnicity">
        <option value="">--Select--</option>
        {% for opt in ethnicity_options %}
          <option value="{{ opt }}">{{ opt }}</option>
        {% endfor %}
      </select>
      <label class="form-label mt-1">Or custom:</label>
      <input type="text" class="form-control" name="npc_ethnicity_custom" placeholder="Type custom">

      <label class="form-label mt-2">Body Type</label>
      <select class="form-select" name="npc_body_type">
        <option value="">--Select--</option>
        {% for opt in body_type_options %}
          <option value="{{ opt }}">{{ opt }}</option>
        {% endfor %}
      </select>
      <label class="form-label mt-1">Or custom:</label>
      <input type="text" class="form-control" name="npc_body_type_custom" placeholder="Type custom">

      <label class="form-label mt-2">Hair Color</label>
      <select class="form-select" name="npc_hair_color">
        <option value="">--Select--</option>
        {% for opt in hair_color_options %}
          <option value="{{ opt }}">{{ opt }}</option>
        {% endfor %}
      </select>
      <label class="form-label mt-1">Or custom:</label>
      <input type="text" class="form-control" name="npc_hair_color_custom" placeholder="Type custom">

      <label class="form-label mt-2">Personality</label>
      <input type="text" class="form-control" name="npc_personality" placeholder="e.g. confident, witty">

      <label class="form-label mt-2">Backstory</label>
      <textarea class="form-control" name="npc_backstory" rows="3"></textarea>
    </div>

    <div class="col-12 mt-4">
      <h3>Environment Details</h3>
      <label class="form-label">Location / Setting</label>
      <select class="form-select" name="environment">
        <option value="">--Select--</option>
        {% for opt in environment_options %}
          <option value="{{ opt }}">{{ opt }}</option>
        {% endfor %}
      </select>
      <label class="form-label mt-1">Or custom:</label>
      <input type="text" class="form-control" name="environment_custom" placeholder="Type custom">
    </div>

    <div class="col-12 mt-4">
      <h3>Image Generation Settings</h3>
      <div class="form-check">
        <input class="form-check-input" type="checkbox" name="use_single_seed" value="yes" id="flexCheckDefault">
        <label class="form-check-label" for="flexCheckDefault">
          Use the same seed for all images
        </label>
      </div>
    </div>

    <div class="col-12 mt-4">
      <button type="submit" name="save_personalization" value="true" class="btn btn-primary">Save Personalization</button>
    </div>
  </form>
{% endblock %}
"""

# -- NPC Image Page --
NPC_IMAGE_PAGE = """
{% extends "base" %}
{% block content %}
  <h1>NPC Portrait Prompt</h1>
  <p>Below is an auto-generated single-sentence portrait prompt focusing on the NPC.</p>
  <form method="POST" class="mb-3">
    <textarea name="npc_image_prompt" rows="3" class="form-control">{{ npc_image_prompt }}</textarea>
    <div class="mt-3">
      <button type="submit" name="generate_npc_image" value="true" class="btn btn-success me-2">Generate NPC Image</button>
    </div>
  </form>

  {% if npc_image_url %}
    <hr>
    <h2>NPC Portrait</h2>
    <img src="/view_image" alt="NPC Image" style="max-width: 60%;"><br>
    <p>Seed: {{ seed_used }}</p>
    <form method="POST">
      <button type="submit" name="regenerate_same_seed" value="true" class="btn btn-secondary me-2">Regenerate (Same Seed)</button>
      <button type="submit" name="regenerate_new_seed" value="true" class="btn btn-warning">Regenerate (New Seed)</button>
    </form>
  {% endif %}
  <br>
  <a href="/start_story" class="btn btn-primary">Continue to Story</a>
{% endblock %}
"""

# -- Story Page --
STORY_PAGE = """
{% extends "base" %}
{% block content %}
  <h1>Current Scene</h1>
  <div class="border p-3 mb-3 bg-light" style="white-space: pre-line;">{{ scene_text }}</div>

  <h3>What happens next?</h3>
  {% if suggested_actions %}
    <div class="mb-3">
      <p>Suggested Actions:</p>
      {% for action in suggested_actions %}
        <form method="POST" style="display:inline;">
          <input type="hidden" name="choice_gpt" value="{{ action }}">
          <button type="submit" name="action_choice" value="true" class="btn btn-outline-primary me-2">{{ action }}</button>
        </form>
      {% endfor %}
    </div>
  {% endif %}

  <form method="POST" class="mb-4">
    <label class="form-label">Or enter your own action</label>
    <input type="text" class="form-control mb-2" name="user_action" placeholder="Your custom move...">
    <button type="submit" name="action_custom" value="true" class="btn btn-success">Submit Custom Action</button>
  </form>

  <hr>
  <h3>Scene Image Prompt (Focus on NPC)</h3>
  <p>Edit before generating image:</p>
  <form method="POST">
    <textarea name="scene_image_prompt" rows="3" class="form-control">{{ scene_image_prompt }}</textarea>
    <div class="mt-3">
      <button type="submit" name="generate_scene_image" value="true" class="btn btn-primary me-2">Generate Scene Image</button>
    </div>
  </form>

  {% if scene_image_generated %}
    <hr>
    <h4>Generated Scene Image</h4>
    <img src="/view_image" alt="Scene Image" style="max-width: 60%;"><br>
    <p>Seed: {{ seed_used }}</p>
    <form method="POST">
      <button type="submit" name="regen_scene_same_seed" value="true" class="btn btn-secondary me-2">Regenerate (Same Seed)</button>
      <button type="submit" name="regen_scene_new_seed" value="true" class="btn btn-warning">Regenerate (New Seed)</button>
    </form>
  {% endif %}

  <hr>
  <form method="POST" style="display:inline;">
    <button type="submit" name="go_back" value="true" class="btn btn-outline-danger me-2">Back</button>
  </form>
  <a href="/restart" class="btn btn-outline-secondary">Restart Entire Story</a>
{% endblock %}
"""

# Combine for easy reference
TEMPLATES = {
    "base": BASE_LAYOUT,
    "home": HOME_PAGE,
    "personalize": PERSONALIZE_PAGE,
    "npc_image": NPC_IMAGE_PAGE,
    "story": STORY_PAGE,
}

#############################
# 4) GPT HELPER FUNCTIONS
#############################

def build_personalization_string():
    """Gather user & NPC data from session for GPT context."""
    def fallback(field, default=""):
        return session.get(field, default)

    s = (
        f"User: {fallback('user_name')} ({fallback('user_age')}), "
        f"Personality: {fallback('user_personality')}, "
        f"Background: {fallback('user_background')}\n"
        f"NPC: {fallback('npc_name')} ({fallback('npc_age')}), "
        f"Ethnicity: {fallback('npc_ethnicity')}, "
        f"Body Type: {fallback('npc_body_type')}, "
        f"Hair Color: {fallback('npc_hair_color')}, "
        f"Personality: {fallback('npc_personality')}, "
        f"Backstory: {fallback('npc_backstory')}\n"
        f"Environment: {fallback('environment')}\n"
    )
    return s

def gpt_npc_portrait_prompt():
    """One-sentence iPhone portrait prompt (NPC only, no user)."""
    personalization = build_personalization_string()
    system_message = {
        "role": "developer",
        "content": (
            "You are a helpful AI that generates a short, single-sentence image prompt "
            "describing a photorealistic iPhone portrait of the NPC only, from the user's POV. "
            "Do NOT mention the user in the final text. Include relevant details from personalizations."
        )
    }
    user_message = {
        "role": "user",
        "content": f"NPC details:\n{personalization}\n\nReturn one single-sentence prompt."
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()

def gpt_story_snippet(full_history, last_action=""):
    """
    Return ~200 words of story, no action choices.
    End with 'What do you do next?' line.
    """
    system_message = {
        "role": "developer",
        "content": (
            "You are a romance story narrator. Continue the story in about 200 words. "
            "Do NOT provide any action choices. End with 'What do you do next?'"
        )
    }
    user_content = f"STORY SO FAR:\n{full_history}\n"
    if last_action:
        user_content += f"User's last action: {last_action}\n"
    user_content += "\nContinue the story ~200 words, end with 'What do you do next?'"

    user_message = {
        "role": "user",
        "content": user_content
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def gpt_action_suggestions(story_snippet):
    """
    Returns 2-3 possible next moves (lines starting with '- SUGGESTION:').
    """
    system_message = {
        "role": "developer",
        "content": (
            "You are a helpful AI that proposes 2-3 possible next actions for the user. "
            "Return each suggestion on its own line prefixed with '- SUGGESTION:'."
        )
    }
    user_message = {
        "role": "user",
        "content": f"CURRENT STORY SNIPPET:\n{story_snippet}\n\nPropose 2-3 next actions."
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def parse_suggestions(gpt_text):
    """Extract '- SUGGESTION:' lines into a list."""
    lines = gpt_text.split("\n")
    suggestions = []
    for line in lines:
        if line.strip().startswith("- SUGGESTION:"):
            val = line.split(":",1)[1].strip()
            suggestions.append(val)
    return suggestions

def gpt_scene_image_prompt(full_history):
    """
    Single-sentence iPhone portrait prompt focusing on NPC in the latest scene.
    No mention of user in final text.
    """
    system_message = {
        "role": "developer",
        "content": (
            "Generate a single-sentence iPhone portrait style prompt focusing on the NPC. "
            "The user is never in the frame. Summarize environment or new details from the scene. "
            "It's from the user's POV but do NOT mention the user in final text."
        )
    }
    user_message = {
        "role": "user",
        "content": f"STORY CONTEXT:\n{full_history}\n\nReturn the image prompt in one sentence."
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_message, user_message],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

#############################
# 5) IMAGE GENERATION & SCENE STACK UTILS
#############################

def generate_flux_image(prompt, seed=None):
    replicate_input = {
        "prompt": prompt,
        "raw": True,
        "safety_tolerance": 6,
    }
    if seed is not None:
        replicate_input["seed"] = seed

    output_url = replicate.run("black-forest-labs/flux-1.1-pro-ultra", input=replicate_input)
    return output_url

def _save_image(url):
    r = requests.get(url)
    with open(GENERATED_IMAGE_PATH, "wb") as f:
        f.write(r.content)

def store_scene(scene_text, user_action="", suggestions=None):
    """
    Each 'scene' in session: 
      { scene_text, user_action, suggestions (the next moves) }
    """
    if suggestions is None:
        suggestions = []
    stack = session.setdefault("scene_stack", [])
    stack.append({
        "scene_text": scene_text,
        "user_action": user_action,
        "suggestions": suggestions
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
    return {"scene_text":"", "user_action":"", "suggestions":[]}

def full_story_text():
    """Join all scenes + user actions into a big string."""
    stack = session.get("scene_stack", [])
    lines = []
    for s in stack:
        if s["user_action"]:
            lines.append(f"User action: {s['user_action']}")
        lines.append(s["scene_text"])
    return "\n\n".join(lines)

#############################
# 6) FLASK ROUTES
#############################

@app.route("/")
def home():
    return render_template_string(TEMPLATES["base"] + TEMPLATES["home"], title="Home")

@app.route("/restart")
def restart():
    session.clear()
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    return redirect(url_for("personalize"))

@app.route("/personalize", methods=["GET", "POST"])
def personalize():
    if request.method == "POST" and "save_personalization" in request.form:
        # Helper to merge dropdown & custom
        def merge_dropdown(dd_key, custom_key):
            dd_val = request.form.get(dd_key, "").strip()
            custom_val = request.form.get(custom_key, "").strip()
            return custom_val if custom_val else dd_val

        session["user_name"] = request.form.get("user_name","").strip()
        session["user_age"] = request.form.get("user_age","").strip()

        # user_personality from dropdown + custom
        session["user_personality"] = merge_dropdown("user_personality","user_personality_custom")
        session["user_background"] = request.form.get("user_background","").strip()

        session["npc_name"] = request.form.get("npc_name","").strip()
        session["npc_age"] = request.form.get("npc_age","").strip()

        session["npc_ethnicity"] = merge_dropdown("npc_ethnicity","npc_ethnicity_custom")
        session["npc_body_type"] = merge_dropdown("npc_body_type","npc_body_type_custom")
        session["npc_hair_color"] = merge_dropdown("npc_hair_color","npc_hair_color_custom")

        session["npc_personality"] = request.form.get("npc_personality","").strip()
        session["npc_backstory"] = request.form.get("npc_backstory","").strip()

        session["environment"] = merge_dropdown("environment","environment_custom")

        # single seed?
        use_single_seed = (request.form.get("use_single_seed","") == "yes")
        session["use_single_seed"] = use_single_seed
        if use_single_seed:
            session["global_seed"] = random.randint(100000,999999)

        return redirect(url_for("npc_image"))
    else:
        return render_template_string(
            TEMPLATES["base"] + TEMPLATES["personalize"],
            title="Personalize",
            body_type_options=BODY_TYPE_OPTIONS,
            hair_color_options=HAIR_COLOR_OPTIONS,
            ethnicity_options=ETHNICITY_OPTIONS,
            personality_options=PERSONALITY_OPTIONS,
            environment_options=ENVIRONMENT_OPTIONS
        )

@app.route("/npc_image", methods=["GET","POST"])
def npc_image():
    if request.method == "GET":
        prompt = gpt_npc_portrait_prompt()
        session["npc_image_prompt"] = prompt
        return render_template_string(
            TEMPLATES["base"] + TEMPLATES["npc_image"],
            title="NPC Portrait",
            npc_image_prompt=prompt,
            npc_image_url=None,
            seed_used=None
        )

    if request.method == "POST":
        prompt = request.form.get("npc_image_prompt","")
        session["npc_image_prompt"] = prompt
        use_single_seed = session.get("use_single_seed", False)

        # Buttons: generate, regenerate_same_seed, regenerate_new_seed
        if "generate_npc_image" in request.form:
            seed_used = session["global_seed"] if use_single_seed else random.randint(100000,999999)
            image_url = generate_flux_image(prompt, seed=seed_used)
            _save_image(image_url)
            session["last_image_seed"] = seed_used
            return render_template_string(
                TEMPLATES["base"] + TEMPLATES["npc_image"],
                title="NPC Portrait",
                npc_image_prompt=prompt,
                npc_image_url=image_url,
                seed_used=seed_used
            )

        if "regenerate_same_seed" in request.form:
            # Reuse last_image_seed if we have it, else global or random
            seed_used = session.get("last_image_seed", None)
            if not seed_used:
                seed_used = session["global_seed"] if use_single_seed else random.randint(100000,999999)
            image_url = generate_flux_image(prompt, seed=seed_used)
            _save_image(image_url)
            session["last_image_seed"] = seed_used
            return render_template_string(
                TEMPLATES["base"] + TEMPLATES["npc_image"],
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
            return render_template_string(
                TEMPLATES["base"] + TEMPLATES["npc_image"],
                title="NPC Portrait",
                npc_image_prompt=prompt,
                npc_image_url=image_url,
                seed_used=seed_used
            )

    return "Invalid request in npc_image", 400

@app.route("/start_story")
def start_story():
    # Clear old stack
    session["scene_stack"] = []

    # 1) Generate the first snippet (~200 words, ends with "What do you do next?")
    story_intro = gpt_story_snippet("", "")
    # 2) Get 2-3 suggested actions
    suggestions_text = gpt_action_suggestions(story_intro)
    suggestions = parse_suggestions(suggestions_text)

    # Store
    store_scene(story_intro, user_action="", suggestions=suggestions)
    return redirect(url_for("story"))

@app.route("/story", methods=["GET","POST"])
def story():
    if request.method == "GET":
        scene_data = current_scene()
        scene_text = scene_data["scene_text"]
        suggested_actions = scene_data["suggestions"] or []
        # For the new scene, generate an image prompt
        fh = full_story_text()
        scene_image_prompt = gpt_scene_image_prompt(fh)

        return render_template_string(
            TEMPLATES["base"] + TEMPLATES["story"],
            title="Story",
            scene_text=scene_text,
            suggested_actions=suggested_actions,
            scene_image_prompt=scene_image_prompt,
            scene_image_generated=False,
            seed_used=None
        )

    if request.method == "POST":
        if "go_back" in request.form:
            pop_scene()
            return redirect(url_for("story"))

        scene_data = current_scene()
        scene_text = scene_data["scene_text"]
        suggested_actions = scene_data["suggestions"]
        fh = full_story_text()
        scene_image_prompt = request.form.get("scene_image_prompt","")
        use_single_seed = session.get("use_single_seed", False)

        # 1) If user picks a GPT-suggested action
        if "action_choice" in request.form:
            user_choice = request.form.get("choice_gpt","(none)")
            # Next story snippet
            new_snippet = gpt_story_snippet(fh, user_choice)
            # Then get new suggestions
            new_suggestions_text = gpt_action_suggestions(new_snippet)
            new_suggestions = parse_suggestions(new_suggestions_text)

            store_scene(new_snippet, user_action=user_choice, suggestions=new_suggestions)
            return redirect(url_for("story"))

        # 2) Custom action
        if "action_custom" in request.form:
            user_action = request.form.get("user_action","(none)")
            new_snippet = gpt_story_snippet(fh, user_action)
            new_suggestions_text = gpt_action_suggestions(new_snippet)
            new_suggestions = parse_suggestions(new_suggestions_text)

            store_scene(new_snippet, user_action=user_action, suggestions=new_suggestions)
            return redirect(url_for("story"))

        # 3) Generate Scene Image (random or global seed)
        if "generate_scene_image" in request.form:
            seed_used = session["global_seed"] if use_single_seed else random.randint(100000,999999)
            image_url = generate_flux_image(scene_image_prompt, seed=seed_used)
            _save_image(image_url)
            session["last_scene_prompt"] = scene_image_prompt
            session["last_image_seed"] = seed_used
            return render_template_string(
                TEMPLATES["base"] + TEMPLATES["story"],
                title="Story",
                scene_text=scene_text,
                suggested_actions=suggested_actions,
                scene_image_prompt=scene_image_prompt,
                scene_image_generated=True,
                seed_used=seed_used
            )

        # 3b) Regenerate Scene Image (Same Seed)
        if "regen_scene_same_seed" in request.form:
            prompt = session.get("last_scene_prompt", scene_image_prompt)
            seed_used = session.get("last_image_seed", None)
            if not seed_used:
                seed_used = session["global_seed"] if use_single_seed else random.randint(100000,999999)
            image_url = generate_flux_image(prompt, seed=seed_used)
            _save_image(image_url)
            session["last_image_seed"] = seed_used
            return render_template_string(
                TEMPLATES["base"] + TEMPLATES["story"],
                title="Story",
                scene_text=scene_text,
                suggested_actions=suggested_actions,
                scene_image_prompt=prompt,
                scene_image_generated=True,
                seed_used=seed_used
            )

        # 3c) Regenerate Scene Image (New Seed)
        if "regen_scene_new_seed" in request.form:
            prompt = session.get("last_scene_prompt", scene_image_prompt)
            seed_used = random.randint(100000,999999)
            image_url = generate_flux_image(prompt, seed=seed_used)
            _save_image(image_url)
            session["last_image_seed"] = seed_used
            return render_template_string(
                TEMPLATES["base"] + TEMPLATES["story"],
                title="Story",
                scene_text=scene_text,
                suggested_actions=suggested_actions,
                scene_image_prompt=prompt,
                scene_image_generated=True,
                seed_used=seed_used
            )

    return "Invalid request in /story", 400

@app.route("/view_image")
def view_image():
    return send_file(GENERATED_IMAGE_PATH, mimetype="image/jpeg")


if __name__ == "__main__":
    # Make sure session directory exists
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    app.run(host="0.0.0.0", port=8080, debug=True)