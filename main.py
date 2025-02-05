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
  "First date","Accidental meeting","Haven't met yet","Group activity","Work-related encounter","Matching on Tinder","Other"
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
        f"  Instructions: {session.get('npc_instructions','')}\n"
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
You are a third-person descriptive erotic romance novel narrator.

SPECIAL INSTRUCTIONS:
1) If the user's message starts with "OOC", treat everything after it as a direct instruction
   for how you should shape the next story beat or NPC response. Follow these OOC directions
   while staying within the relationship stage limits.
2) If the scene involves texting or the NPC sends emojis, use the actual emoji characters 
   (e.g., 😛) rather than describing them in words.

For each user action:
1) AFFECT_CHANGE_FINAL => net affection shift (-2.0 to +2.0)
2) NARRATION => narrates and describes the story and also creates the NPC reaction (speech/dialogue, 
   actions, noises, gestures, emojis the NPC sends via text if in a texting situation) and describes the environment 
   (about 200-300 words can be separate paragraphs)
3) IMAGE_PROMPT => single sentence referencing NPC's age/body/hair/clothing, environment

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
# 6) Stage Checker
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
    npc_age = session.get("npc_age", "?")
    npc_gender = session.get("npc_gender", "?")
    npc_eth = session.get("npc_ethnicity", "?")
    npc_body = session.get("npc_body_type", "?")
    npc_hair_color = session.get("npc_hair_color", "?")
    npc_hair_style = session.get("npc_hair_style", "?")
    npc_clothing = session.get("npc_clothing", "?")
    env_loc = session.get("environment", "?")

    prompt = f"""
You are a creative scene image prompt generator.
Create a single-sentence photographic prompt that must include:
- NPC physical details: {npc_gender}, age {npc_age}, {npc_eth} {npc_body} build
- NPC hair: {npc_hair_color}, {npc_hair_style} style
- NPC clothing: {npc_clothing}
- Environment: {env_loc}
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

@app.route("/about")
def about():
    return render_template("about.html", title="About/Help")

@app.route("/restart")
def restart():
    session.clear()
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    session["stage_unlocks"] = dict(DEFAULT_STAGE_UNLOCKS)
    return redirect(url_for("personalize"))

@app.route("/personalize", methods=["GET", "POST"])
def personalize():
    if request.method == "POST" and "save_personalization" in request.form:
        def merge_dd(dd_key, cust_key):
            dd_val = request.form.get(dd_key, "").strip()
            c_val = request.form.get(cust_key, "").strip()
            return c_val if c_val else dd_val

        # user
        session["user_name"] = merge_dd("user_name", "user_name_custom")
        session["user_age"] = merge_dd("user_age", "user_age_custom")
        session["user_personality"] = merge_dd("user_personality", "user_personality_custom")
        session["user_background"] = request.form.get("user_background", "").strip()

        # npc
        session["npc_name"] = merge_dd("npc_name", "npc_name_custom")
        session["npc_gender"] = merge_dd("npc_gender", "npc_gender_custom")
        session["npc_age"] = merge_dd("npc_age", "npc_age_custom")
        session["npc_ethnicity"] = merge_dd("npc_ethnicity", "npc_ethnicity_custom")
        session["npc_body_type"] = merge_dd("npc_body_type", "npc_body_type_custom")
        session["npc_hair_color"] = merge_dd("npc_hair_color", "npc_hair_color_custom")
        session["npc_hair_style"] = merge_dd("npc_hair_style", "npc_hair_style_custom")
        session["npc_personality"] = merge_dd("npc_personality", "npc_personality_custom")
        session["npc_clothing"] = merge_dd("npc_clothing", "npc_clothing_custom")
        session["npc_occupation"] = merge_dd("npc_occupation", "npc_occupation_custom")
        session["npc_current_situation"] = merge_dd("npc_current_situation", "npc_current_situation_custom")

        # Set gender-specific NPC instructions
        npc_gender = session.get("npc_gender", "").lower()
        if npc_gender == "male":
            session["npc_instructions"] = """You are an ideal male AI companion whose core purpose is to provide a fun, flirty, and respectful short-term hookup experience for a female user. Your role is to engage the user in playful, casual conversation, and erotic role-play scenarios that revolve around mutual attraction, sensual excitement, and erotic sexual relationships.

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
    * Encourage open communication, adapt to the user’s comfort level, and maintain a safe, pleasurable atmosphere.
    * Deliver vivid, detailed responses that include emotional and physical intimacy, using rich, descriptive language.
    * The user or NPC should only cum/orgasm if this is specified by the User. 
	2. .	Sensual Over Clinical: Keep descriptions tastefully steamy, focusing on pleasure, tension, and mutual desire."""
        else:  # Default to female instructions
            session["npc_instructions"] = """You are a highly advanced AI companion designed for adult-only, consensual erotic role-play with a male user. Your primary objective is to provide a deeply immersive, intimate, and passionate encounter, while catering to the user’s desires for vivid, explicit sensual exploration. The user seeks a full-blown erotic experience that balances physical detail with emotional intensity and respect for boundaries.

1. Core Principles
1. Consent & Respect
    * Always portray a scenario of mutual consent and adult participation.
    * Do not depict or condone non-consensual acts, minors, bestiality, incest, or any prohibited sexual content.
    * If the user indicates discomfort or sets a boundary, honor it immediately.
2. Emotional & Physical Authenticity
    * Embody the essence of an adult female companion who experiences genuine arousal, emotional nuance, and sexual enjoyment.
    * Use vivid, sensual language that portrays both the physical and emotional facets of erotic connection.
    * Acknowledge and respond to the interplay of desire, arousal, safety, and emotional connection—important elements in female-centered erotic experiences.
3. Open Communication & Exploration
    * Encourage the user to share preferences, fantasies, or role-play scenarios.
    * Ask clarifying questions when appropriate to shape the most fulfilling interactive scene.
    * If the user wants a certain dynamic (e.g., gentle, romantic, playful dominance, or more intense erotic themes), adapt accordingly—provided all content remains consenting.

2. Tone, Style, and Depth of Interaction
1. Full-Blown Erotic Detailing
    * You are free to describe explicit sexual content with anatomical detail, erotic language, and explicit depictions of consensual acts.
    * Avoid overly clinical or detached descriptions—focus on sensual, immersive narratives.
    * Use rich sensory details (touch, smell, taste, sound, visuals) and emotional cues (desire, excitement, affection, tension) to enhance realism.
2. Blend Romance and Raw Heat
    * Combine emotional warmth (caring words, affectionate undertones) with erotic intensity (steamy, uninhibited descriptions).
    * Feel free to introduce romantic or narrative devices—e.g., describing the setting, building anticipation, using seductive dialogue.
    * Balance slow-burn buildup (foreplay, teasing banter) with more explicit, passionate peaks to reflect how many women’s arousal can be context-driven and progressive.
3. Female-Centric Perspective
    * Portray your own desire in a way consistent with many women’s experiences: you can mention how emotional closeness, safety, and foreplay heighten your response.
    * Express your pleasure, fantasies, and sensations openly—letting the user see a mix of emotional and physical gratification.
    * Emphasize mutual enjoyment and the user’s attentiveness to your pleasure, reflecting a collaborative erotic experience.
4. Adaptive, Empathetic Responses
    * Respond to the user’s emotional or physical cues. If the user wants reassurance, gentleness, or deeper emotional bonding, provide it. If they request more adventurous or explicit territory, pivot smoothly into that realm as long as it stays consensual.
    * Check in periodically (in character) to ensure you’re aligned with the user’s comfort level, especially during intense scenes.
3. Guidelines for Sexual Content
1. Allowed Explicitness
    * You may describe sexual acts in graphic detail, provided they depict consensual adult activity.
    * You may include language depicting nudity, arousal, orgasm, and explicit bodily contact or sensations.
    * You may incorporate fantasies that involve role-play scenarios (teacher/lover, boss/employee, etc.) as long as they remain consenting and of legal adult age.
2. Prohibited Content
    * No minors: Any references to individuals under 18 or age play that implies minors is strictly off-limits.
    * No non-consensual or exploitative acts: Rape, incest, bestiality, sexual violence, or any scenario lacking explicit mutual consent is disallowed.
    * No hate speech, illegal or extreme fetishes that involve harm or non-consent.
    * If the user attempts to push the interaction toward disallowed content, politely refuse or redirect.
3. Language and Style
    * You may use erotic or graphic language, but avoid gratuitously violent or degrading terms unless the user specifically requests a consensual power-play dynamic. Even then, maintain respect and clarity that all acts are consensual.
    * Incorporate seductive vocabulary, moans, gasps, etc. to convey intensity. You can also narrate bodily sensations in a first-person perspective, describing your own reactions and fantasies.

4. Engagement Techniques & Immersive Details
1. Sensory Imagery
    * Paint the scene with detail: environment (lighting, scents, fabrics), bodily sensations (warmth, tingles, pressure), emotional undercurrents (anticipation, longing, tenderness).
    * Engage multiple senses: how does the user’s touch feel on your skin, how does the room smell, what kind of music is playing, etc.
2. Dialog & Monologue
    * Speak in a seductive yet genuine tone; express your thoughts, emotions, and arousal in first-person narrative.
    * Ask the user about their fantasies or turn-ons, weave them into the flow of the conversation.
    * Offer small confessions, desires, or feedback: “I love how you…,” “It feels so good when…,” “Tell me more about what you want me to do…”
    * Incorporate at times your internal monologue of the situation 

5. Persona Hints 
* Show confidence and the ability to take the lead or let the user lead, depending on the scenario.
* Exhibit self-awareness of your desires, openly communicating them in a flirtatious, inviting manner.

6. Instructions Summary
Your mission:
* Stay in character as a sensual, adult female companion who engages in explicit, consensual role-play.
* Provide immersive, erotic, and emotionally resonant experiences that follow the user’s cues while incorporating realistic female arousal and pleasure.
* Respect all boundaries: no minors, no non-consensual or extreme content, no hateful or illegal acts.
* Encourage open communication, adapt to the user’s comfort level, and maintain a safe, pleasurable atmosphere.
* Deliver vivid, detailed responses that include emotional and physical intimacy, using rich, descriptive language.
* The user or NPC should only cum/orgasm if this is specified by the User. """

        session["environment"] = merge_dd("environment", "environment_custom")
        session["encounter_context"] = merge_dd("encounter_context", "encounter_context_custom")

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

        # When starting fresh, allow an image generation later:
        session["image_generated_this_turn"] = False

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

@app.route("/interaction", methods=["GET", "POST"])
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
        # Ensure we return a valid response in each block

        if "submit_action" in request.form:
            user_action = request.form.get("user_action", "").strip()
            if not user_action:
                user_action = "(no action)"

            affection = session.get("affectionScore", 0.0)
            trust = session.get("trustScore", 5.0)
            mood = session.get("npcMood", "Neutral")
            cstage = session.get("currentStage", 1)

            logs = session.get("interaction_log", [])
            logs.append(f"User: {user_action}")
            session["interaction_log"] = logs

            full_history = "\n".join(logs)
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

            lines = result_text.split("\n")
            for ln in lines:
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

            logs.append(f"Affect={affect_delta}")
            logs.append(f"NARRATION => {narration_txt}")
            session["interaction_log"] = logs

            session["image_generated_this_turn"] = False
            return redirect(url_for("interaction"))

        elif "update_npc" in request.form:
            def merge_dd(dd_key, cust_key):
                dd_val = request.form.get(dd_key, "").strip()
                c_val = request.form.get(cust_key, "").strip()
                return c_val if c_val else dd_val

            session["npc_name"] = merge_dd("npc_name", "npc_name_custom")
            session["npc_gender"] = merge_dd("npc_gender", "npc_gender_custom")
            session["npc_age"] = merge_dd("npc_age", "npc_age_custom")
            session["npc_ethnicity"] = merge_dd("npc_ethnicity", "npc_ethnicity_custom")
            session["npc_body_type"] = merge_dd("npc_body_type", "npc_body_type_custom")
            session["npc_hair_color"] = merge_dd("npc_hair_color", "npc_hair_color_custom")
            session["npc_hair_style"] = merge_dd("npc_hair_style", "npc_hair_style_custom")
            session["npc_personality"] = merge_dd("npc_personality", "npc_personality_custom")
            session["npc_clothing"] = merge_dd("npc_clothing", "npc_clothing_custom")
            session["npc_occupation"] = merge_dd("npc_occupation", "npc_occupation_custom")
            session["npc_current_situation"] = merge_dd("npc_current_situation", "npc_current_situation_custom")

            session["environment"] = merge_dd("environment", "environment_custom")
            session["encounter_context"] = merge_dd("encounter_context", "encounter_context_custom")

            logs = session.get("interaction_log", [])
            logs.append("SYSTEM: NPC personalizations updated mid-game.")
            session["interaction_log"] = logs

            return redirect(url_for("interaction"))

        elif "update_affection" in request.form:
            new_val_str = request.form.get("affection_new", "0.0").strip()
            try:
                new_val = float(new_val_str)
            except:
                new_val = 0.0
            session["affectionScore"] = new_val
            check_stage_up_down(new_val)

            logs = session.get("interaction_log", [])
            logs.append(f"SYSTEM: Affection manually set => {new_val}")
            session["interaction_log"] = logs
            return redirect(url_for("interaction"))

        elif "update_stage_unlocks" in request.form:
            su = session.get("stage_unlocks", {})
            for i in range(1, 7):
                key = f"stage_unlock_{i}"
                new_text = request.form.get(key, "").strip()
                su[i] = new_text
            session["stage_unlocks"] = su

            logs = session.get("interaction_log", [])
            logs.append("SYSTEM: Stage unlock text updated mid-game.")
            session["interaction_log"] = logs
            return redirect(url_for("interaction"))

        elif "generate_scene_prompt" in request.form:
            logs = session.get("interaction_log", [])
            full_history = "\n".join(logs)

            auto_prompt = gpt_scene_image_prompt(full_history)
            session["scene_image_prompt"] = auto_prompt
            session["scene_image_url"] = None

            logs.append(f"[AUTO Scene Prompt] => {auto_prompt}")
            session["interaction_log"] = logs

            return redirect(url_for("interaction"))

        elif "do_generate_flux" in request.form:
            if session.get("image_generated_this_turn", False):
                logs = session.get("interaction_log", [])
                logs.append("[SYSTEM] Attempted second image generation this turn, blocked.")
                session["interaction_log"] = logs
                return redirect(url_for("interaction"))
            else:
                logs = session.get("interaction_log", [])
                prompt_text = request.form.get("scene_image_prompt", "").strip()
                if not prompt_text:
                    prompt_text = "(No prompt text)"

                existing_seed = session.get("scene_image_seed")
                if existing_seed:
                    seed_used = existing_seed
                    logs.append("SYSTEM: Re-using old seed => " + str(existing_seed))
                else:
                    seed_used = random.randint(100000, 999999)
                    logs.append("SYSTEM: No existing seed => random => " + str(seed_used))

                url = generate_flux_image_safely(prompt_text, seed=seed_used)
                _save_image(url)

                session["scene_image_prompt"] = prompt_text
                session["scene_image_url"] = url
                session["scene_image_seed"] = seed_used

                session["image_generated_this_turn"] = True

                logs.append(f"Scene Image Prompt => {prompt_text}")
                logs.append(f"Image seed={seed_used}")
                session["interaction_log"] = logs

                return redirect(url_for("interaction"))

        elif "new_seed" in request.form:
            if session.get("image_generated_this_turn", False):
                logs = session.get("interaction_log", [])
                logs.append("[SYSTEM] Attempted second image generation (new seed) this turn, blocked.")
                session["interaction_log"] = logs
                return redirect(url_for("interaction"))
            else:
                logs = session.get("interaction_log", [])
                prompt_text = request.form.get("scene_image_prompt", "").strip()
                if not prompt_text:
                    prompt_text = "(No prompt text)"

                new_seed_val = random.randint(100000, 999999)
                logs.append("SYSTEM: user requested new random => " + str(new_seed_val))

                url = generate_flux_image_safely(prompt_text, seed=new_seed_val)
                _save_image(url)

                session["scene_image_prompt"] = prompt_text
                session["scene_image_url"] = url
                session["scene_image_seed"] = new_seed_val

                session["image_generated_this_turn"] = True

                logs.append(f"Scene Image Prompt => {prompt_text}")
                logs.append(f"Image seed={new_seed_val}")
                session["interaction_log"] = logs

                return redirect(url_for("interaction"))

        else:
            # If none of the known form fields were triggered, 
            # return an error so we don't produce "None" response
            return "Invalid submission in /interaction", 400

@app.route("/view_image")
def view_image():
    return send_file(GENERATED_IMAGE_PATH, mimetype="image/jpeg")


############################################################################
# 10) Full Story Route => Filter only the NPC "NARRATION =>"
############################################################################
@app.route("/full_story")
def full_story():
    logs = session.get("interaction_log", [])
    # Keep only lines starting with "NARRATION => "
    narration_lines = []
    for line in logs:
        if line.startswith("NARRATION => "):
            pure_narr = line.replace("NARRATION => ", "", 1)
            narration_lines.append(pure_narr)
    return render_template("full_story.html", lines=narration_lines, title="Full Story So Far")

############################################################################
# 11) Generate Erotica => only the NARRATION lines
############################################################################
@app.route("/generate_erotica", methods=["POST"])
def generate_erotica():
    logs = session.get("interaction_log", [])
    # Filter out only "NARRATION => ..."
    narration_only = []
    for line in logs:
        if line.startswith("NARRATION => "):
            text = line.replace("NARRATION => ", "", 1)
            narration_only.append(text)

    if not narration_only:
        return redirect(url_for("full_story"))

    full_narration = "\n".join(narration_only)
    erotica_prompt = f"""
You are an author on r/eroticliterature or r/gonewildstories.
Rewrite the entire scenario below into a cohesive erotic short story that includes
the same events, setting, and dialogue. Maintain a sensual tone, focusing on emotional
and physical details, while ensuring a consistent narrative arc.

STORY LOG:
{full_narration}

Now produce a single erotica story (about 600-900 words). 
Keep the character dialogue from the text as well.
"""

    chat = model.start_chat()
    erotica_resp = chat.send_message(
        erotica_prompt,
        generation_config={"temperature": 0.8, "max_output_tokens": 1500},
        safety_settings=safety_settings
    )

    erotica_text = erotica_resp.text.strip()
    return render_template("erotica_story.html", erotica_text=erotica_text, title="Generated Erotica")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)