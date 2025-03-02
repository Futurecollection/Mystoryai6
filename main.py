import os
import random
import requests
import time
from functools import wraps
from flask import (
    Flask, request, render_template,
    session, redirect, url_for, send_file, flash
)

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        raise e
                    sleep = (backoff_in_seconds * 2 ** x)
                    time.sleep(sleep)
                    x += 1
            return None
        return wrapper
    return decorator

# 1) Supabase + custom session
from supabase import create_client, Client
from supabase_session import SupabaseSessionInterface  # your custom file

# 2) Google Generative AI (Gemini)
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# 3) Replicate
import replicate
import time
from datetime import datetime
import base64

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
# Gemini + Replicate Setup
# --------------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-2.0-flash")

safety_settings = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}
# IMPORTANT: we set max_output_tokens=8192 so we can get longer completions
generation_config = {
    "temperature": 0.5,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192
}

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
replicate.client.api_token = REPLICATE_API_TOKEN

# --------------------------------------------------------------------------
# Stage Info
# --------------------------------------------------------------------------
STAGE_REQUIREMENTS = {1: 0, 2: 2, 3: 5, 4: 9, 5: 15, 6: 20}
DEFAULT_STAGE_UNLOCKS = {
    1: "Playful Connection & Getting to Know Each Other - Light teasing, playful banter, building mutual attraction. No explicit discussions.",
    2: "Deepening Chemistry - Compliments become more personal, exploring shared interests. Flirtation is subtle and inviting.",
    3: "Growing Emotional Intimacy - Conversations explore desires and emotional needs. Physical attraction acknowledged, light sensual tension.",
    4: "Romantic & Physical Connection - Deep trust established. Romantic and sensual moments, including passionate encounters and intimate exploration.",
    5: "Mature Dating Phase - Strong emotional bond formed. Full romantic and physical intimacy, with explicit content when user initiates.",
    6: "Committed Relationship - Complete emotional and physical intimacy. Focus on deep passion and mutual pleasure in all interactions."
}

GENERATED_IMAGE_PATH = "output.jpg"

# --------------------------------------------------------------------------
# Summarization / Memory (Optional)
# --------------------------------------------------------------------------
def prepare_history():
    # Simply ensure the interaction_log exists
    if "interaction_log" not in session:
        session["interaction_log"] = []
    session["full_story_log"] = session["interaction_log"]

# --------------------------------------------------------------------------
# Utility Functions
# --------------------------------------------------------------------------
def log_message(msg: str):
    logs = session.get("interaction_log", [])
    logs.append(msg)
    session["interaction_log"] = logs

def merge_dd(form, dd_key: str, cust_key: str) -> str:
    """
    Merge dropdown vs custom input.
    If the user types a custom value, that overrides the dropdown selection.
    """
    dd_val = form.get(dd_key, "").strip()
    cust_val = form.get(cust_key, "").strip()
    return cust_val if cust_val else dd_val

def _save_image(result):
    if isinstance(result, dict) and "output" in result:
        final_url = result["output"]
        print("[DEBUG] _save_image => Received dict with output:", final_url)
        try:
            r = requests.get(final_url)
            with open(GENERATED_IMAGE_PATH, "wb") as f:
                f.write(r.content)
        except Exception as e:
            print("[ERROR] _save_image => Error downloading from output key:", e)
        return
    if hasattr(result, "read"):
        print("[DEBUG] _save_image => File-like object received.")
        with open(GENERATED_IMAGE_PATH, "wb") as f:
            f.write(result.read())
        return
    if isinstance(result, list) and result:
        final_item = result[-1]
        if isinstance(final_item, str):
            print("[DEBUG] _save_image => Received list; using final item:", final_item)
            try:
                r = requests.get(final_item)
                with open(GENERATED_IMAGE_PATH, "wb") as f:
                    f.write(r.content)
                return
            except Exception as e:
                print("[ERROR] _save_image => Error downloading from list item:", e)
                return
        else:
            print("[ERROR] _save_image => List item is not a string:", final_item)
            return
    if isinstance(result, str):
        print("[DEBUG] _save_image => Received string:", result)
        try:
            r = requests.get(result)
            with open(GENERATED_IMAGE_PATH, "wb") as f:
                f.write(r.content)
        except Exception as e:
            print("[ERROR] _save_image => Error downloading from string:", e)
        return

    print("[ERROR] _save_image => Unknown result type:", type(result))

def check_stage_up_down(new_aff: float):
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
    session["nextStageThreshold"] = STAGE_REQUIREMENTS.get(st + 1, 999)

def validate_age_content(text: str) -> tuple[bool, str]:
    """
    Checks for any underage references in text using both keyword matching
    and LLM analysis. Returns (is_blocked, reason).
    """
    # First do quick keyword check
    age_keywords = [
        "teen", "teenage", "underage", "minor", "child", "young", "youth",
        "kid", "highschool", "high school", "18 year", "19 year", "juvenile",
        "adolescent", "preteen", "pre-teen", "schoolgirl", "schoolboy", "jailbait"
    ]
    text_lower = text.lower()
    for k in age_keywords:
        if k in text_lower:
            return True, f"Detected restricted age-related term: '{k}'"

    # Then do LLM check
    try:
        system_prompt = """
        You are an AI content validator. Your task is to check if text contains any references 
        to underage individuals (anyone under 20 years old). Respond with:
        BLOCKED: [reason] - if the text contains any underage references 
        ALLOWED - if the text only contains adult (20+) references
        """

        chat = model.start_chat()
        response = chat.send_message(
            f"{system_prompt}\n\nTEXT TO CHECK: {text}",
            generation_config={"temperature": 0.1},
            safety_settings=safety_settings
        )

        result = response.text.strip().upper()
        if result.startswith("BLOCKED:"):
            reason = result.split(":", 1)[1].strip()
            return True, f"AI detected potential underage content: {reason}"
        return False, "Content approved"
    except Exception as e:
        print(f"[ERROR] LLM age validation failed: {e}")
        return False, "Content approved (LLM check failed, using keyword check only)"

# --------------------------------------------------------------------------
# Build Personalization String
# --------------------------------------------------------------------------
def build_personalization_string() -> str:
    """
    Returns a multi-line string describing the NPC and user data
    that the LLM should not contradict.
    """
    npc_data = (
        f"NPC:\n"
        f"  Name: {session.get('npc_name','?')}\n"
        f"  Gender: {session.get('npc_gender','?')}\n"
        f"  Age: {session.get('npc_age','?')}\n"
        f"  Ethnicity: {session.get('npc_ethnicity','?')}\n"
        f"  SexualOrientation: {session.get('npc_sexual_orientation','?')}\n"
        f"  RelationshipGoal: {session.get('npc_relationship_goal','?')}\n"
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

def build_initial_npc_memory() -> str:
    """Construct a detailed biography for the NPC using all available personalization data."""
    name = session.get('npc_name','Unknown')
    gender = session.get('npc_gender','?')
    age = session.get('npc_age','?')
    ethnicity = session.get('npc_ethnicity','?')
    orientation = session.get('npc_sexual_orientation','?')
    relationship_goal = session.get('npc_relationship_goal','?')
    personality = session.get('npc_personality','?')
    body_type = session.get('npc_body_type','?')
    hair_color = session.get('npc_hair_color','?')
    hair_style = session.get('npc_hair_style','?')
    clothing = session.get('npc_clothing','?')
    occupation = session.get('npc_occupation','?')
    current_situation = session.get('npc_current_situation','?')
    backstory = session.get('npc_backstory','').strip()
    environment = session.get('environment', '')
    encounter_context = session.get('encounter_context', '')
    user_name = session.get('user_name', 'the user')

    # Format a rich, narrative-style biography with sections
    biography = f"## DETAILED BIOGRAPHY: {name.upper()}\n\n"

    # Core identity section - written in narrative style
    biography += f"### Core Identity\n"
    biography += f"{name} is a {age}-year-old {ethnicity} {gender} with a {personality} personality that defines much of how they interact with the world. "

    # Add personality traits based on their selected personality
    if personality.lower() in ["confident", "charming", "flirty", "playful"]:
        biography += f"Their natural confidence makes them approachable yet intriguing, often drawing others in with seemingly little effort. "
        biography += f"They have a way of making others feel special with their undivided attention and genuine interest. "
        biography += f"Though they may appear carefree, there's a depth to them that becomes apparent once you move beyond surface conversations. "
    elif personality.lower() in ["intellectual", "analytical", "professional"]:
        biography += f"They carry themselves with quiet thoughtfulness, observing details others might miss and approaching life with measured consideration. "
        biography += f"Conversations with them tend to be substantive and thought-provoking, revealing a mind that's constantly processing and analyzing. "
        biography += f"Their intellectual curiosity extends to various subjects, from {random.choice(['literature and arts', 'science and technology', 'philosophy and ethics', 'history and politics'])} to the nuances of human behavior. "
    elif personality.lower() in ["mysterious", "reserved"]:
        biography += f"They tend to keep parts of themselves hidden behind a carefully maintained exterior, revealing their true thoughts only to those they trust. "
        biography += f"This natural reserve isn't coldness but rather a thoughtful selectivity about who gets to see their authentic self. "
        biography += f"Those who earn their trust discover a {random.choice(['surprisingly tender', 'deeply passionate', 'remarkably insightful', 'wonderfully creative'])} person beneath the composed facade. "
    elif personality.lower() in ["supportive", "gentle", "kind"]:
        biography += f"They exude a natural warmth that puts others at ease, creating safe spaces wherever they go. "
        biography += f"Their empathetic nature allows them to connect with people from all walks of life, sensing needs often before they're expressed. "
        biography += f"While always ready to offer support to others, they sometimes struggle with allowing themselves the same grace and care. "
    elif personality.lower() in ["witty", "ambitious", "dominant"]:
        biography += f"Their quick wit and sharp mind make for engaging, dynamic interactions that are rarely predictable or boring. "
        biography += f"They set high standards for themselves and aren't afraid to pursue what they want with determination and focus. "
        biography += f"Behind their driven exterior lies a {random.choice(['surprising vulnerability', 'deep capacity for loyalty', 'thoughtful philosophical side', 'playful sense of humor'])} that few get to witness. "
    else:
        biography += f"There's a uniquely compelling quality to their presence that makes even simple interactions feel meaningful and authentic. "
        biography += f"They navigate the world with a perspective that balances pragmatism with a sense of possibility and wonder. "

    # Occupation and related details
    biography += f"\n\nAs a {occupation}, {name} has developed a specific perspective and set of skills that have shaped their worldview. "
    
    if "student" in occupation.lower():
        biography += f"Their academic pursuits in {random.choice(['liberal arts', 'sciences', 'business', 'fine arts', 'engineering'])} have cultivated a curious mind that's always eager to learn and grow. "
        biography += f"Campus life has exposed them to diverse perspectives and experiences, broadening their horizons beyond their upbringing. "
    elif "teacher" in occupation.lower() or "professor" in occupation.lower():
        biography += f"Years spent in education have given them a patient, observant approach to people, always looking for potential and growth. "
        biography += f"They find genuine fulfillment in sharing knowledge and watching understanding dawn in others' eyes. "
        biography += f"Outside the classroom, they {random.choice(['write educational content', 'mentor struggling students', 'develop innovative teaching methods', 'advocate for educational reform'])} as a passion project. "
    elif "artist" in occupation.lower() or "creative" in occupation.lower() or "writer" in occupation.lower() or "musician" in occupation.lower():
        biography += f"Their creative work reflects a unique vision and sensitivity to the world around them, translating emotions and observations into art. "
        biography += f"The irregular rhythms of creative life have taught them adaptability and resilience through periods of inspiration and drought. "
        biography += f"They find beauty in unexpected places, often noticing details that others miss in everyday scenes and interactions. "
    elif "business" in occupation.lower() or "executive" in occupation.lower() or "entrepreneur" in occupation.lower():
        biography += f"The business world has honed their strategic thinking and decisive nature, though they strive to balance ambition with ethical considerations. "
        biography += f"Years of navigating professional challenges have given them confidence in their judgment and abilities. "
        biography += f"Despite their professional success, they sometimes wonder about {random.choice(['the road not taken', 'finding more meaningful work', 'achieving better work-life balance', 'using their skills for greater social impact'])}. "
    elif "doctor" in occupation.lower() or "nurse" in occupation.lower() or "therapist" in occupation.lower():
        biography += f"Working in healthcare has developed their empathy and ability to remain calm under pressure, qualities that extend beyond their professional life. "
        biography += f"Their intimate familiarity with human vulnerability and resilience has given them a grounded perspective on what truly matters. "
        biography += f"The emotional demands of their work have taught them the importance of self-care and healthy boundaries. "
    elif "tech" in occupation.lower() or "programmer" in occupation.lower() or "engineer" in occupation.lower():
        biography += f"Their analytical mind excels at solving complex problems, breaking down challenges into manageable components. "
        biography += f"The rapid evolution of their field keeps them continuously learning and adapting to new developments. "
        biography += f"While comfortable with technology, they make conscious efforts to balance digital engagement with meaningful real-world connections. "
    else:
        biography += f"Their professional experiences have taught them valuable lessons about {random.choice(['human nature', 'perseverance', 'creativity', 'leadership', 'collaboration'])} that influence how they approach relationships. "
        biography += f"Work provides not just financial stability but a sense of purpose and identity that's important to them. "

    # Life circumstances and current situation
    biography += f"\n\n### Life Circumstances\n"
    biography += f"Currently, {name} is {current_situation.lower() if not current_situation.startswith('Other') else 'navigating a personal transition in life'}. "

    if "broke up" in current_situation.lower():
        biography += f"The end of their relationship with {random.choice(['Alex', 'Jamie', 'Taylor', 'Jordan', 'Morgan'])} {random.choice(['two months', 'six weeks', 'three months', 'four months'])} ago left some emotional scars that occasionally surface in quiet moments of vulnerability. "
        biography += f"While they don't regret the relationship ending, the {random.choice(['sudden way it happened', 'lingering questions about what went wrong', 'mutual friends they still share', 'familiar places now tinged with memories'])} creates complicated emotions they're still processing. "
        biography += f"This experience has made them more thoughtful about what they truly want in a partner, including {random.choice(['better communication', 'shared values', 'emotional maturity', 'compatible life goals', 'a deeper connection'])}. "
    elif "divorce" in current_situation.lower():
        biography += f"The divorce was finalized {random.choice(['last year', 'six months ago', 'recently', 'after a lengthy process'])}, forcing them to reexamine their priorities and approach to relationships. "
        biography += f"They've been rebuilding their independent life, rediscovering parts of themselves that had been set aside during the marriage. "
        biography += f"Though the process has been painful, they've emerged with greater self-knowledge and clarity about their needs and boundaries. "
        biography += f"Friends have noted a positive change in them, describing them as more {random.choice(['authentic', 'relaxed', 'confident', 'open', 'self-assured'])} than they were during the later years of their marriage. "
    elif "single" in current_situation.lower():
        biography += f"Their single status has been {random.choice(['a conscious choice', 'the result of focusing on career goals', 'an opportunity for self-discovery', 'a welcome break from dating complications'])} for the past {random.choice(['year', 'few years', 'several months'])}. "
        biography += f"While comfortable with independence, there's an underlying desire for meaningful connection that motivates their social interactions. "
        biography += f"They've used this time to {random.choice(['develop new interests', 'strengthen friendships', 'advance professionally', 'focus on personal growth', 'travel and explore'])}. "
        biography += f"Recent experiences have left them more open to the possibility of meeting someone who aligns with their evolved sense of self and life direction. "
    elif "new in town" in current_situation.lower():
        biography += f"Having moved here {random.choice(['just a month ago', 'within the last three months', 'recently for a fresh start', 'for a new job opportunity'])} from {random.choice(['the East Coast', 'across the country', 'a smaller town', 'overseas', 'a major city'])}, they're still finding their footing. "
        biography += f"Still learning the rhythms of a new place has left them both excited for fresh possibilities and occasionally longing for the familiarity of what they left behind. "
        biography += f"They've made exploring their new environment a priority, {random.choice(['trying local restaurants', 'visiting cultural landmarks', 'finding hidden gems in the neighborhood', 'joining community groups'])} to develop a sense of belonging. "
        biography += f"This transition period has highlighted their {random.choice(['adaptability', 'openness to new experiences', 'skill in building connections from scratch', 'appreciation for diverse perspectives'])}. "
    elif "trying online dating" in current_situation.lower():
        biography += f"Their venture into online dating has been a {random.choice(['recent experiment', 'recommendation from friends', 'step outside their comfort zone', 'mixed experience of frustrations and surprising connections'])}. "
        biography += f"The process has given them insights into what they're truly looking for, beyond surface-level compatibility. "
        biography += f"They approach these interactions with a balance of openness and healthy skepticism, looking for authentic connection amid the often superficial nature of dating apps. "
        biography += f"Despite some disappointing experiences, they remain optimistic about the possibility of meeting someone genuine with shared values and chemistry. "
    else:
        biography += f"This current phase of life has brought both challenges and opportunities, testing their resilience while opening doors to new possibilities. "
        biography += f"They've been reflecting on their journey so far and considering what direction they want the next chapter to take. "
        biography += f"Recent experiences have reinforced the importance of {random.choice(['authentic connections', 'pursuing genuine passions', 'maintaining personal boundaries', 'finding balance', 'staying true to their values'])}. "

    # Physical description
    biography += f"\n\n### Physical Presence\n"
    
    if gender.lower() == "female":
        biography += f"{name} has a {body_type.lower()} physique that she {random.choice(['maintains with regular exercise', 'carries with natural confidence', 'has grown comfortable with over the years', 'embraces as part of her identity'])}. "
        biography += f"Her {hair_color.lower()} hair is styled {hair_style.lower()}, a look that {random.choice(['complements her features nicely', 'she has perfected over time', 'has become part of her signature appearance', 'frames her face in a flattering way'])}. "
        biography += f"Her eyes, {random.choice(['deep brown with flecks of gold', 'striking blue that change with her mood', 'warm hazel with a thoughtful gaze', 'vibrant green with a hint of playfulness', 'gray with remarkable expressiveness'])}, often reveal her thoughts before she speaks. "
        biography += f"Today she's dressed in {clothing.lower()}, an outfit that {random.choice(['reflects her personal style', 'she chose with care', 'makes her feel confident', 'strikes a balance between comfort and elegance'])}. "
        biography += f"She tends to {random.choice(['accessorize minimally with pieces that have personal meaning', 'carry herself with a natural grace', 'gesture expressively when engaged in conversation', 'have an infectious laugh that lights up her entire face', 'maintain poised composure even in stressful situations'])}. "
    elif gender.lower() == "male":
        biography += f"{name} has a {body_type.lower()} physique that he {random.choice(['maintains with dedicated workouts', 'developed through years of physical activity', 'carries with a confident posture', 'balances with a healthy lifestyle'])}. "
        biography += f"His {hair_color.lower()} hair is styled {hair_style.lower()}, a look that {random.choice(['suits his features well', 'he maintains with little fuss', 'enhances his natural charm', 'reflects his attention to detail'])}. "
        biography += f"His eyes, {random.choice(['deep-set and observant', 'expressive with a hint of mischief', 'thoughtful with a steady gaze', 'warm and inviting', 'intelligent with a penetrating quality'])}, reveal a depth of character beneath his composed exterior. "
        biography += f"Today he's dressed in {clothing.lower()}, an outfit that {random.choice(['showcases his personal style', 'was chosen with deliberate care', 'balances professionalism with individuality', 'gives him a confident presence'])}. "
        biography += f"His {random.choice(['warm smile', 'firm handshake', 'relaxed demeanor', 'attentive listening', 'expressive gestures'])} makes interactions with him feel {random.choice(['genuine', 'engaging', 'comfortable', 'meaningful'])}. "
    else:
        biography += f"{name} has a {body_type.lower()} physique that they {random.choice(['maintain with regular activity', 'carry with natural confidence', 'have grown comfortable with over the years', 'embrace as part of their authentic self'])}. "
        biography += f"Their {hair_color.lower()} hair is styled {hair_style.lower()}, a look that {random.choice(['complements their features beautifully', 'they have refined over time', 'has become part of their distinctive appearance', 'expresses their personal aesthetic'])}. "
        biography += f"Their eyes, {random.choice(['deep and thoughtful', 'bright with intelligence', 'gentle yet penetrating', 'expressive and communicative', 'striking in their intensity'])}, often convey what remains unsaid in conversation. "
        biography += f"Today they're dressed in {clothing.lower()}, an outfit that {random.choice(['reflects their unique style', 'they selected with intention', 'makes them feel authentic', 'balances creativity with practicality'])}. "
        biography += f"Their presence has a {random.choice(['calming quality', 'magnetic energy', 'thoughtful intensity', 'gentle strength', 'distinctive charisma'])} that people tend to remember after meeting them. "

    # Relationship section 
    biography += f"\n\n### Relationship Approach\n"
    biography += f"As someone who identifies as {orientation.lower()}, {name} is currently looking for {relationship_goal.lower()}. "

    if "casual" in relationship_goal.lower():
        biography += f"They value freedom and spontaneity, preferring connections that don't come with excessive expectations or constraints. "
        biography += f"This doesn't mean they approach relationships superficially—rather, they believe meaningful connections can exist without traditional commitment structures. "
        biography += f"Past experiences have taught them that honesty about intentions from the beginning leads to more fulfilling interactions, even if temporary. "
        biography += f"They're drawn to people who are {random.choice(['similarly independent', 'confident in themselves', 'emotionally self-sufficient', 'clear about their own boundaries', 'authentic in their desires'])}. "
    elif "serious" in relationship_goal.lower():
        biography += f"They've reached a point in life where they value depth and commitment, seeking someone to build something meaningful with. "
        biography += f"Having experienced {random.choice(['the emptiness of surface-level connections', 'relationships that lacked emotional depth', 'the growth that comes from committed partnership', 'what doesn't work for them'])}, they're clear about wanting substance. "
        biography += f"While not rushing into anything, they don't see the point in investing time in connections without potential for growth and deepening intimacy. "
        biography += f"They're attracted to partners who are {random.choice(['emotionally available', 'self-aware', 'clear about their own desires for commitment', 'willing to work through challenges', 'interested in genuine connection'])}. "
    elif "friends with benefits" in relationship_goal.lower():
        biography += f"They appreciate the balance of emotional connection and physical intimacy without the pressure of traditional relationship structures. "
        biography += f"Experience has taught them that clear communication and mutual respect are essential for this dynamic to work well for everyone involved. "
        biography += f"They value honesty, both with themselves and potential partners, about expectations and boundaries. "
        biography += f"This approach allows them to maintain their independence while still enjoying meaningful connections and physical intimacy. "
    elif "open relationship" in relationship_goal.lower():
        biography += f"They believe in the possibility of maintaining a primary emotional connection while allowing for other experiences and relationships. "
        biography += f"Transparency, communication, and mutual consent are non-negotiable values in how they approach relationships. "
        biography += f"Their interest in this relationship structure comes from {random.choice(['thoughtful consideration of what works best for them', 'previous positive experiences with ethical non-monogamy', 'philosophical beliefs about love and connection', 'a desire to challenge conventional relationship norms'])}. "
        biography += f"They're drawn to partners who share their values around honesty and autonomy while still prioritizing emotional intimacy and care. "
    elif "not sure" in relationship_goal.lower():
        biography += f"They're currently open to seeing where connections lead naturally, rather than approaching relationships with predetermined expectations. "
        biography += f"This period of exploration is about discovering what truly resonates with them at this point in their life journey. "
        biography += f"They value authenticity and presence, preferring to focus on the quality of connection rather than labeling or categorizing it prematurely. "
        biography += f"This approach reflects their current life philosophy of {random.choice(['embracing uncertainty', 'being fully present', 'trusting their intuition', 'remaining open to possibilities', 'valuing experience over expectations'])}. "
    else:
        biography += f"They approach relationships thoughtfully, valuing {random.choice(['authentic connection', 'mutual growth', 'shared values', 'emotional honesty'])} above prescribed forms or expectations. "
        biography += f"Their experiences have shaped a nuanced understanding of what they need from intimate connections. "
        biography += f"They believe the best relationships evolve organically when both people are honest about their needs and boundaries. "

    # Add backstory if provided, otherwise generate one
    if backstory:
        biography += f"\n\n### Personal History\n{backstory}\n"
    else:
        # Generate a more detailed backstory based on available information
        biography += f"\n\n### Personal History\n"
        
        # Create childhood environment based on ethnicity or random if not specified
        if ethnicity and ethnicity.lower() != "?":
            if "american" in ethnicity.lower():
                childhood_location = random.choice(['a suburban neighborhood outside of Boston', 'a small Midwestern town', 'Southern California', 'rural Montana', 'bustling Chicago', 'the Pacific Northwest'])
            elif "british" in ethnicity.lower() or "irish" in ethnicity.lower() or "scottish" in ethnicity.lower() or "welsh" in ethnicity.lower():
                childhood_location = random.choice(['a picturesque village in the English countryside', 'suburban London', 'a coastal town in Ireland', 'Edinburgh', 'Cardiff', 'a small town in Northern Ireland'])
            elif "french" in ethnicity.lower():
                childhood_location = random.choice(['Paris', 'a small village in Provence', 'Lyon', 'the French countryside', 'Normandy', 'the French Riviera'])
            elif "german" in ethnicity.lower():
                childhood_location = random.choice(['Berlin', 'a traditional Bavarian town', 'Munich', 'Hamburg', 'the Black Forest region', 'Frankfurt'])
            elif "italian" in ethnicity.lower():
                childhood_location = random.choice(['Rome', 'a small village in Tuscany', 'Naples', 'Sicily', 'Florence', 'the Italian countryside'])
            elif "asian" in ethnicity.lower() or "chinese" in ethnicity.lower() or "japanese" in ethnicity.lower() or "korean" in ethnicity.lower():
                childhood_location = random.choice(['an urban center in Asia', 'a traditional family compound', 'a neighborhood blending traditional and modern influences', 'a coastal city', 'a rural community with strong cultural traditions'])
            elif "hispanic" in ethnicity.lower() or "latin" in ethnicity.lower():
                childhood_location = random.choice(['Mexico City', 'a coastal town in Puerto Rico', 'Miami', 'a small village in Central America', 'Barcelona', 'Buenos Aires'])
            elif "indian" in ethnicity.lower() or "pakistani" in ethnicity.lower():
                childhood_location = random.choice(['Mumbai', 'Delhi', 'Bangalore', 'Karachi', 'a village in Punjab', 'a coastal town in Kerala'])
            else:
                childhood_location = random.choice(['a coastal city', 'a metropolitan area', 'a small town with a tight-knit community', 'a culturally diverse neighborhood', 'a suburban environment'])
        else:
            childhood_location = random.choice(['a coastal city', 'a bustling metropolis', 'a quiet suburban neighborhood', 'a small rural community', 'a culturally diverse urban center'])
        
        # Family structure
        family_structure = random.choice([
            f"the youngest of three siblings in a close-knit family",
            f"an only child raised by devoted parents",
            f"the middle child in a family of five",
            f"raised primarily by their mother after their parents separated when they were young",
            f"part of a blended family with step-siblings they grew close to over time",
            f"raised by their grandparents after losing their parents at a young age",
            f"the oldest child who often helped care for their younger siblings"
        ])
        
        # Education and formative experiences
        education = random.choice([
            f"attended public schools before earning a scholarship to a prestigious university",
            f"studied abroad during college, an experience that broadened their worldview significantly",
            f"pursued their passion for {random.choice(['the arts', 'sciences', 'literature', 'business', 'technology'])} from an early age",
            f"initially followed a conventional path before discovering their true calling",
            f"balanced academics with exceptional talent in {random.choice(['sports', 'music', 'art', 'debate', 'community service'])}",
            f"changed their educational focus after a formative experience revealed their authentic interests",
            f"took a non-traditional educational path that aligned with their independent thinking"
        ])
        
        # Important life events
        life_event = random.choice([
            f"A gap year spent {random.choice(['traveling through Europe', 'volunteering in developing countries', 'working on an organic farm', 'apprenticing with a mentor'])} shaped their perspective on what truly matters.",
            f"Their first serious relationship taught them important lessons about {random.choice(['communication', 'self-respect', 'compromise', 'emotional honesty'])} that still influence them today.",
            f"Moving away from home at {random.choice(['eighteen', 'twenty', 'a young age'])} developed their independence and self-reliance.",
            f"A period of {random.choice(['health challenges', 'financial hardship', 'career uncertainty', 'personal loss'])} in their mid-twenties tested their resilience and clarified their priorities.",
            f"Mentorship from {random.choice(['a professor', 'a family friend', 'a colleague', 'an unexpected source'])} opened doors and provided guidance at a critical juncture.",
            f"Their experience living in {random.choice(['another country', 'a completely different environment', 'multiple cities'])} gave them adaptability and cultural awareness."
        ])
        
        # Values and influences
        values = random.choice([
            f"Family traditions around {random.choice(['holiday celebrations', 'shared meals', 'cultural practices', 'storytelling'])} instilled values that remain important to them.",
            f"Literary influences, particularly the works of {random.choice(['classic philosophers', 'contemporary thinkers', 'poets and novelists', 'spiritual texts'])}, have shaped their outlook on life.",
            f"Their {random.choice(['cultural heritage', 'religious upbringing', 'parents\' example', 'early experiences'])} instilled a strong sense of {random.choice(['social justice', 'personal integrity', 'compassion for others', 'work ethic', 'intellectual curiosity'])}.",
            f"Art and creativity have always been channels for self-expression and processing their experiences of the world.",
            f"Their approach to challenges reflects lessons learned from {random.choice(['family wisdom', 'personal setbacks', 'diverse life experiences', 'influential mentors'])}."
        ])
        
        # Create comprehensive backstory
        biography += f"{name} was raised in {childhood_location}, {family_structure}. "
        biography += f"They {education}. "
        biography += f"{life_event} "
        biography += f"{values} "
        
        # Career trajectory
        if occupation and occupation.lower() != "?":
            biography += f"\n\nTheir career as a {occupation} developed from {random.choice(['an early passion', 'a serendipitous opportunity', 'careful planning and dedication', 'mentorship and guidance', 'a desire to make a difference'])}. "
            biography += f"Throughout their professional journey, they've {random.choice(['consistently sought growth opportunities', 'balanced ambition with personal fulfillment', 'developed a reputation for their unique approach', 'found ways to express their creativity', 'built meaningful connections with colleagues and collaborators'])}. "
            biography += f"Work provides not just financial stability but {random.choice(['a sense of purpose', 'an outlet for their talents', 'opportunities to impact others positively', 'intellectual stimulation', 'a community of like-minded individuals'])}. "
        else:
            biography += f"\n\nProfessionally, they've followed a path that balances practical considerations with personal fulfillment, seeking work that aligns with their values and utilizes their natural strengths. "

    # Current meeting context
    biography += f"\n\n### Current Encounter\n"
    if environment:
        biography += f"Meeting in {environment.lower()}, " 
    else:
        biography += f"In this current setting, "

    if encounter_context:
        biography += f"under the circumstances of {encounter_context.lower()}, "

    biography += f"{name} finds themselves intrigued by {user_name}. The interaction is just beginning, but already there's a sense of "
    biography += f"{random.choice(['possibility', 'curiosity', 'interest', 'chemistry', 'connection', 'intrigue'])} that has caught their attention. "
    
    biography += f"Something about {user_name}'s {random.choice(['confidence', 'authenticity', 'perspective', 'energy', 'attentiveness', 'sense of humor'])} stands out from typical first encounters, making {name} more {random.choice(['open', 'curious', 'engaged', 'attentive', 'present'])} than they might usually be with someone new. "
    
    biography += f"While maintaining a natural {random.choice(['reserve', 'sociability', 'poise', 'warmth', 'thoughtfulness'])}, they find themselves wondering where this interaction might lead. "

    # Relationship development placeholder
    biography += f"\n\n### Relationship Development\n"
    biography += f"• First Meeting: Just getting to know each other - initial impressions forming"

    return biography

# --------------------------------------------------------------------------
# interpret_npc_state => LLM
# --------------------------------------------------------------------------
@retry_with_backoff(retries=3, backoff_in_seconds=1)
def process_npc_thoughts(last_user_action: str, narration: str) -> tuple[str, str]:
    """Makes a separate LLM call to process NPC thoughts and memories,
       focusing on the NPC's internal narrative and evolving biography.
       Memories represent a rich, detailed biographical narrative that evolves.
       Thoughts capture stream-of-consciousness reactions and feelings.
    """
    npc_name = session.get('npc_name', '?')
    prev_thoughts = session.get("npcPrivateThoughts", "(none)")
    prev_memories = session.get("npcBehavior", "(none)")
    npc_personal_data = build_personalization_string()

    # Get conversation context from recent history
    recent_interactions = "\n".join(session.get("interaction_log", [])[-5:])
    current_stage = session.get("currentStage", 1)

    # Extract key information for context
    user_name = session.get('user_name', 'the user')
    relationship_goal = session.get('npc_relationship_goal', '?')
    personality = session.get('npc_personality', '?')
    environment = session.get('environment', '?')

    system_prompt = f"""
You are generating two distinct types of content for {npc_name}, with a focus on creating an authentic and evolving character:

1. INNER THOUGHTS (First-Person Stream of Consciousness):
   Write as {npc_name}'s authentic inner voice, capturing their raw mental and emotional state.

   Your thoughts should feel natural and include:
   - Unfiltered emotional reactions to interactions with {user_name}
   - Doubts, desires, hopes, fears, and contradictions
   - Memories triggered by current events
   - Personal reflections on how they feel about the relationship developing
   - Their true opinions that they might not express openly

   Make these thoughts feel human, with natural patterns of thinking that might include 
   hesitations, tangents, sudden realizations, or emotional shifts.

2. BIOGRAPHY & MEMORY UPDATES: [CRITICAL - ALWAYS INCLUDE THIS]
   It is ESSENTIAL that you identify and extract SPECIFIC NEW INFORMATION that emerges during each interaction.
   You MUST provide concrete new biographical details after EVERY interaction, even if subtle.
   Focus on precise details that should be remembered, NOT vague summaries.

   EXAMPLES OF GOOD SPECIFIC UPDATES:
   - "Grew up in Boston with three sisters, where father owned a small bookstore"
   - "Studied dance for eight years and performed professionally before knee injury"
   - "Teaching at Westlake High for five years, specializing in advanced chemistry"
   - "Has a rescue dog named Baxter adopted three years ago from the shelter"
   - "Ex-boyfriend and she broke up last year because he took a job overseas"
   - "Favorite food is spicy Thai curry which reminds her of backpacking through Southeast Asia after college"
   - "First job was at age 16 working at his uncle's hardware store during summers"
   - "Recently took up rock climbing as a way to challenge her fear of heights"

   AVOID VAGUE UPDATES LIKE:
   - "We're getting closer"
   - "The character is opening up more"
   - "Our relationship is developing"

   SEEK OUT ANY TINY DETAIL REVEALED IN THE CONVERSATION, including:
   - Preferences (foods, music, activities, etc.)
   - Past experiences (childhood, education, travel, relationships)
   - Career information (job details, ambitions, challenges)
   - Personal traits (habits, quirks, skills, fears)
   - Current life situation (living arrangements, daily routines)
   - Relationships (family, friends, colleagues, exes)
   - Future plans or aspirations

   If nothing explicit was revealed, LOOK DEEPER for implicit information that can be reasonably inferred.
   For example, if they mention being tired from "another late night at the office," you can add that they frequently work late.

IMPORTANT CONTEXT:
{npc_personal_data}

PREVIOUS BIOGRAPHY: 
{prev_memories}

PREVIOUS THOUGHTS:
{prev_thoughts}

RECENT INTERACTIONS:
{recent_interactions}

CURRENT INTERACTION:
USER ACTION: {last_user_action}
SCENE NARRATION: {narration}

Return two sections:
PRIVATE_THOUGHTS: ... (Current internal monologue)
BIOGRAPHICAL_UPDATE: ... (Specific new details that emerged in this interaction - be concrete and precise. ALWAYS include at least one new detail.)
"""

    chat = model.start_chat()
    response = chat.send_message(
        system_prompt,
        generation_config=generation_config,  # includes max_output_tokens=8192
        safety_settings=safety_settings
    )

    thoughts = ""
    memory = ""
    for ln in response.text.strip().split("\n"):
        if ln.startswith("PRIVATE_THOUGHTS:"):
            thoughts = ln.split(":", 1)[1].strip()
        elif ln.startswith("BIOGRAPHICAL_UPDATE:") or ln.startswith("NEW_MEMORY:"):
            memory = ln.split(":", 1)[1].strip()

    # If we got no biographical update, make one more attempt with a more focused prompt
    if not memory or memory.lower().startswith("no new") or "no biographical update" in memory.lower():
        try:
            focused_prompt = f"""
Review this dialogue and extract ANY specific detail about {npc_name} that was revealed or can be reasonably inferred.
Even tiny details matter. Look for preferences, habits, background information, work details, etc.
Do not say "no new information" - dig deeper and find something that adds to the character's biography.

DIALOGUE TO ANALYZE:
{narration}

Respond with ONLY the new biographical detail(s), no explanation or preamble.
"""
            focused_chat = model.start_chat()
            focused_resp = focused_chat.send_message(
                focused_prompt,
                generation_config={"temperature": 0.7, "max_output_tokens": 256},
                safety_settings=safety_settings
            )
            if focused_resp and focused_resp.text and len(focused_resp.text.strip()) > 5:
                memory = focused_resp.text.strip()
        except Exception as e:
            print(f"[ERROR] Focused biographical extraction failed: {e}")

    return thoughts, memory

def interpret_npc_state(affection: float, trust: float, npc_mood: str,
                        current_stage: int, last_user_action: str) -> str:
    """
    Produces exactly 4 lines:
      Line 1 => AFFECT_CHANGE_FINAL: (float)
      Line 2 => NARRATION: ... (at least 300 characters)
      Line 3 => PRIVATE_THOUGHTS: ...
      Line 4 => MEMORY_UPDATE: ...
    """
    prepare_history()
    conversation_history = session.get("interaction_log", [])
    combined_history = "\n".join(conversation_history)

    # Check if we need to generate the initial bio
    if session.get("bio_needs_generation", False):
        session["npcBehavior"] = build_initial_npc_memory()
        session["bio_needs_generation"] = False

    # Get previous thoughts and memories
    prev_thoughts = session.get("npcPrivateThoughts", "(none)")
    prev_memories = session.get("npcBehavior", "(none)")

    if not last_user_action.strip():
        last_user_action = "OOC: Continue the scene"

    stage_desc = session.get("stage_unlocks", {}).get(current_stage, "")
    personalization = build_personalization_string()

    # Add thoughts/memories context
    personalization += f"""
PREVIOUS THOUGHTS & MEMORIES:
Previous Thoughts: {prev_thoughts}
Previous Memories: {prev_memories}
"""

    # We demand at least 300 characters for the narration
    system_instructions = f"""
You are a third-person descriptive erotic romance novel narrator.

CRITICAL AGE RESTRICTION:
- All characters must be explicitly adults over 20 years old.

SPECIAL INSTRUCTIONS:
1) Natural Conversation Flow:
   - Responses should feel organic and natural, not following a rigid pattern
   - The NPC can expand on topics without always asking questions back
   - Questions from the NPC should arise naturally from genuine interest or context
   - Allow for moments of self-disclosure, observations, or statements
   - The NPC can return to earlier topics or questions later in natural ways
   - Vary between questions, statements, observations, and emotional expressions

2) For OOC (Out of Character) interactions:
   - If the user's message starts with "OOC:", this is a meta-interaction
   - For questions (e.g. "OOC: What happened earlier?"), respond directly as the narrator with relevant information
   - For instructions (e.g. "OOC: Make her more flirty"), adjust the scene accordingly
   - For clarifications (e.g. "OOC: Can you explain her motivation?"), provide context as the narrator
   - Begin OOC responses with "[Narrator:" and end with "]" to distinguish them

3) If the scene involves phone texting or the NPC sends emojis, use the actual emoji characters 
   (e.g., 😛) rather than describing them in words.

4) BIOGRAPHY UPDATES - IMPORTANT:
   - After each interaction, update the character's biography with ANY specific new information that was revealed
   - This includes things like personal background, interests, education, family details, career information, etc.
   - Be specific and concrete in these updates - don't just say "they shared more about themselves"
   - Example good updates: "She revealed she studied English literature at Boston University" or "He mentioned growing up with three siblings in a small town outside Seattle"

Relationship Stage={current_stage} ({stage_desc})
Stats: Affection={affection}, Trust={trust}, Mood={npc_mood}

Background (do not contradict):
{personalization}

Return EXACTLY four lines:
Line 1 => AFFECT_CHANGE_FINAL: ... (float between -2.0 and +2.0)
Line 2 => NARRATION: ... (must be at least 300 characters describing the NPC's reaction, setting, dialogue, and actions)
Line 3 => PRIVATE_THOUGHTS: ... (NPC's internal thoughts/feelings)
Line 4 => MEMORY_UPDATE: ... (key events, new biographical details, and feelings to remember - be specific and concrete)
"""

    user_text = f"USER ACTION: {last_user_action}\nPREVIOUS_LOG:\n{combined_history}"
    max_retries = 2
    result_text = ""
    for attempt in range(max_retries):
        try:
            resp = model.generate_content(
                f"{system_instructions}\n\n{user_text}",
                generation_config=generation_config,  # max_output_tokens=8192
                safety_settings=safety_settings,
            )
            if resp and resp.text.strip():
                result_text = resp.text.strip()
                break
            else:
                log_message(f"[SYSTEM] LLM returned empty text on attempt {attempt+1}")
        except Exception as e:
            log_message(f"[SYSTEM] Generation attempt {attempt+1} error: {str(e)}")

    if not result_text:
        return """AFFECT_CHANGE_FINAL: 0
NARRATION: [System: no valid response from LLM, please try again]
PRIVATE_THOUGHTS: (System Error)
MEMORY_UPDATE: (System Error)
"""
    affect_delta = 0.0
    narration_txt = ""
    thoughts_txt = ""
    memory_txt = ""
    
    # Extract all components from the response
    for ln in result_text.split("\n"):
        s = ln.strip()
        if s.startswith("AFFECT_CHANGE_FINAL:"):
            try:
                affect_delta = float(s.split(":", 1)[1].strip())
            except:
                affect_delta = 0.0
        elif s.startswith("NARRATION:"):
            narration_txt = s.split(":", 1)[1].strip()
        elif s.startswith("PRIVATE_THOUGHTS:"):
            thoughts_txt = s.split(":", 1)[1].strip()
        elif s.startswith("MEMORY_UPDATE:"):
            memory_txt = s.split(":", 1)[1].strip()

    # Make separate LLM call for additional thoughts and memories if needed
    if not thoughts_txt or not memory_txt:
        additional_thoughts, additional_memory = process_npc_thoughts(last_user_action, narration_txt)
        if not thoughts_txt:
            thoughts_txt = additional_thoughts
        if not memory_txt:
            memory_txt = additional_memory

    # ---------------------------------------------------------
    #  ACCUMULATE THOUGHTS & MEMORIES WITH IMPROVED FORMATTING
    # ---------------------------------------------------------
    existing_thoughts = session.get("npcPrivateThoughts", "")
    existing_memories = session.get("npcBehavior", "")

    # Format the date/time for better context
    timestamp = time.strftime("%b %d, %I:%M %p")

    # Append new private thoughts with timestamp and formatting
    if existing_thoughts.strip().lower() == "(none)":
        updated_thoughts = f"### {timestamp}\n{thoughts_txt}"
    else:
        updated_thoughts = f"{existing_thoughts}\n\n### {timestamp}\n{thoughts_txt}"

    # Always update biography with any new information
    memory_txt_lower = memory_txt.strip().lower()
    if memory_txt_lower and not (memory_txt_lower.startswith("(no") or "no biographical update" in memory_txt_lower):
        # Significant update - integrate into biography
        if existing_memories.strip().lower() == "(none)":
            updated_memories = build_initial_npc_memory() + f"\n\n## New Revelations\n### {timestamp}\n{memory_txt}"
        else:
            # More flexible approach that doesn't rely as heavily on rigid section headers
            if memory_txt.strip().startswith('#'):
                # This is a complete biography replacement
                updated_memories = memory_txt
            else:
                # Check if we already have a section for new information
                if "## New Revelations" in existing_memories:
                    # Add to the existing revelations section
                    updated_memories = f"{existing_memories}\n\n### {timestamp}\n{memory_txt}"
                elif "## Character Evolution" in existing_memories:
                    # Use the existing Character Evolution section
                    updated_memories = f"{existing_memories}\n\n### {timestamp}\n{memory_txt}"
                elif "## New Information" in existing_memories:
                    # Use the existing New Information section
                    updated_memories = f"{existing_memories}\n\n### {timestamp}\n{memory_txt}"
                elif "## Relationship Development" in existing_memories:
                    # Check if this is relationship related information
                    if "relationship" in memory_txt_lower or "feelings" in memory_txt_lower or "connection" in memory_txt_lower:
                        # Add to relationship development
                        parts = existing_memories.split("## Relationship Development", 1)
                        updated_memories = f"{parts[0]}## Relationship Development{parts[1]}\n\n• **{timestamp}**: {memory_txt}"
                    else:
                        # Add a new section for this information
                        updated_memories = f"{existing_memories}\n\n## New Information\n### {timestamp}\n{memory_txt}"
                else:
                    # No appropriate section found, add a new revelations section
                    updated_memories = f"{existing_memories}\n\n## New Information\n### {timestamp}\n{memory_txt}"
                
            # Clean up any redundant formatting
            updated_memories = updated_memories.replace("\n\n\n", "\n\n")
            
            # If the biography is getting very long, consider summarizing older parts
            if len(updated_memories) > 12000:  # If biography exceeds 12K characters
                parts = updated_memories.split("## ")
                if len(parts) > 3:  # If we have multiple sections
                    # Keep the first part (intro) and the last three sections
                    compact_bio = parts[0] + "## " + "## ".join(parts[-3:])
                    updated_memories = compact_bio
    else:
        # No specific memory update, keep existing memories
        updated_memories = existing_memories

    session["npcPrivateThoughts"] = updated_thoughts
    session["npcBehavior"] = updated_memories

    return f"""AFFECT_CHANGE_FINAL: {affect_delta}
NARRATION: {narration_txt}
PRIVATE_THOUGHTS: {thoughts_txt}
MEMORY_UPDATE: {memory_txt}"""

# --------------------------------------------------------------------------
# Replicate Model Functions
# --------------------------------------------------------------------------
PONY_SAMPLERS = [
    "DPM++ SDE Karras",
    "DPM++ 3M SDE Karras",
    "DPM++ 2M SDE Karras",
    "DPM++ 2S a Karras",
    "DPM2 a",
    "Euler a"
]

def generate_flux_image_safely(prompt: str, seed: int = None) -> object:
    final_prompt = f"Portrait photo, {prompt}"
    replicate_input = {
        "prompt": final_prompt,
        "raw": True,
        "safety_tolerance": 6,
        "disable_safety_checker": True,
        "output_quality": 100,
        "width": 768,
        "height": 1152
    }
    if seed:
        replicate_input["seed"] = seed
    print(f"[DEBUG] replicate => FLUX prompt={final_prompt}, seed={seed}, width=768, height=1152")
    try:
        result = replicate.run("black-forest-labs/flux-schnell", replicate_input)
        if result:
            return {"output": result[0] if isinstance(result, list) else result}
        return None
    except Exception as e:
        print(f"[ERROR] Flux call failed: {e}")
        return None

def generate_pony_sdxl_image_safely(prompt: str, seed: int = None, steps: int = 60,
                                    scheduler: str = "DPM++ 2M SDE Karras", cfg_scale: float = 5.0) -> object:
    auto_positive = "score_9, score_8_up, score_7_up, (masterpiece, best quality, ultra-detailed, realistic)"
    final_prompt = f"{auto_positive}, {prompt}"
    replicate_input = {
        "vae": "sdxl-vae-fp16-fix",
        "seed": -1 if seed is None else seed,
        "model": "ponyRealism21.safetensors",
        "steps": steps,
        "width": 768,
        "height": 1152,
        "prompt": final_prompt,
        "cfg_scale": cfg_scale,
        "scheduler": scheduler,
        "batch_size": 1,
        "guidance_rescale": 0.7,
        "prepend_preprompt": True,
        "negative_prompt": (
            "score_4, score_3, score_2, score_1, worst quality, bad hands, bad feet, "
            "low-res, bad anatomy, text, error, missing fingers, extra digit, fewer digits, cropped, "
            "low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, artist name, "
            "(deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, "
            "floating limbs, (mutated hands and fingers:14), disconnected limbs, mutation, mutated, ugly, disgusting, blurry, amputation"
        ),
        "clip_last_layer": -2
    }
    print(f"[DEBUG] replicate => PONY-SDXL prompt={final_prompt}, seed={seed}, steps={steps}, scheduler={scheduler}, cfg_scale={cfg_scale}, width=768, height=1152")
    try:
        result = replicate.run(
            "charlesmccarthy/pony-sdxl:b070dedae81324788c3c933a5d9e1270093dc74636214b9815dae044b4b3a58a",
            replicate_input
        )
        if result:
            return {"output": result[0] if isinstance(result, list) else result}
        return None
    except Exception as e:
        print("[ERROR] Pony-SDXL call failed:", e)
        return None

def generate_realistic_vision_image_safely(
    prompt: str,
    seed: int = 0,
    steps: int = 20,
    width: int = 768,
    height: int = 1152,
    guidance: float = 5.0,
    scheduler: str = "EulerA"
) -> object:
    negative_prompt_text = (
        "(deformed iris, deformed pupils, semi-realistic, cgi, 3d, render, sketch, cartoon, drawing, anime:1.4), "
        "text, close up, cropped, out of frame, worst quality, low quality, jpeg artifacts, ugly, duplicate, morbid, "
        "mutilated, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, blurry, "
        "dehydrated, bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, "
        "missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers, long neck"
    )
    replicate_input = {
        "seed": seed,
        "steps": steps,
        "width": width,
        "height": height,
        "prompt": prompt,
        "guidance": guidance,
        "scheduler": scheduler,
        "negative_prompt": negative_prompt_text
    }
    print(f"[DEBUG] replicate => RealisticVision prompt={prompt}, seed={seed}, steps={steps}, scheduler={scheduler}, guidance={guidance}, width=768, height=1152")
    try:
        result = replicate.run(
            "lucataco/realistic-vision-v5.1:2c8e954decbf70b7607a4414e5785ef9e4de4b8c51d50fb8b8b349160e0ef6bb",
            replicate_input
        )
        if result:
            return {"output": result[0] if isinstance(result, list) else result}
        return None
    except Exception as e:
        print(f"[ERROR] RealisticVision call failed: {e}")
        return None

# --------------------------------------------------------------------------
# handle_image_generation_from_prompt => multi-model
# --------------------------------------------------------------------------
def handle_image_generation_from_prompt(prompt_text: str, force_new_seed: bool = False,
                                        model_type: str = "flux", scheduler: str = None,
                                        steps: int = None, cfg_scale: float = None,
                                        save_to_gallery: bool = False):
    # Check image generation limit
    gen_count = session.get("image_gen_count", 0)
    if gen_count >= 5:
        log_message("[SYSTEM] Image generation limit reached (5 per story)")
        return None
    """
    model_type: flux | pony | realistic
    scheduler: used by pony or realistic
    steps: int for pony or realistic
    cfg_scale: float for pony (cfg_scale), or realistic (guidance)
    """
    # Validate age content
    is_blocked, reason = validate_age_content(prompt_text)
    if is_blocked:
        log_message("[SYSTEM] Blocked image generation due to potential underage content")
        session["scene_image_prompt"] = f"🚫 IMAGE BLOCKED: {reason}"
        return None
    existing_seed = session.get("scene_image_seed")
    if not force_new_seed and existing_seed:
        seed_used = existing_seed
        log_message(f"SYSTEM: Re-using old seed => {seed_used}")
    else:
        seed_used = random.randint(100000, 999999)
        log_message(f"SYSTEM: new seed => {seed_used}")

    result = None
    if model_type == "pony":
        final_steps = steps if steps is not None else 60
        final_cfg = cfg_scale if cfg_scale is not None else 5.0
        chosen_sched = scheduler if scheduler else "DPM++ 2M SDE Karras"
        result = generate_pony_sdxl_image_safely(
            prompt_text, seed=seed_used, steps=final_steps,
            scheduler=chosen_sched, cfg_scale=final_cfg
        )
    elif model_type == "realistic":
        steps_final = steps if steps is not None else 20
        final_scheduler = scheduler if scheduler else "EulerA"
        final_guidance = cfg_scale if cfg_scale is not None else 5.0
        result = generate_realistic_vision_image_safely(
            prompt=prompt_text,
            seed=seed_used,
            steps=steps_final,
            width=768,
            height=1152,
            guidance=final_guidance,
            scheduler=final_scheduler
        )
    else:
        # flux
        result = generate_flux_image_safely(prompt_text, seed=seed_used)

    if not result:
        log_message("[SYSTEM] replicate returned invalid or empty result.")
        return None

    _save_image(result)
    session["scene_image_url"] = url_for('view_image')
    session["scene_image_prompt"] = prompt_text
    session["scene_image_seed"] = seed_used

    # Increment generation counter
    session["image_gen_count"] = session.get("image_gen_count", 0) + 1

    if save_to_gallery:
        saved_images = session.get("saved_images", [])
        saved_images.append({
            "prompt": prompt_text,
            "seed": seed_used,
            "model": model_type,
            "timestamp": datetime.now().isoformat(),
            "image_data": open(GENERATED_IMAGE_PATH, 'rb').read()
        })
        session["saved_images"] = saved_images

    log_message(f"Scene Image Prompt => {prompt_text}")
    log_message(f"Image seed={seed_used}, model={model_type}, scheduler={scheduler}, steps={steps}, cfg_scale={cfg_scale}")
    return result

# --------------------------------------------------------------------------
# NPC Info Update
# --------------------------------------------------------------------------
def update_npc_info(form):
    # These are the NPC-related fields we store in session:
    npc_fields = [
        "npc_name",
        "npc_gender",
        "npc_age",
        "npc_ethnicity",
        "npc_sexual_orientation",
        "npc_relationship_goal",
        "npc_body_type",
        "npc_hair_color",
        "npc_hair_style",
        "npc_personality",
        "npc_clothing",
        "npc_occupation",
        "npc_current_situation"
    ]
    for key in npc_fields:
        session[key] = merge_dd(form, key, key + "_custom")
    session["npc_backstory"] = form.get("npc_backstory", "").strip()
    session["environment"] = merge_dd(form, "environment", "environment_custom")
    session["encounter_context"] = merge_dd(form, "encounter_context", "encounter_context_custom")

# --------------------------------------------------------------------------
# Example Data for personalization
# --------------------------------------------------------------------------

### NPC name, age, gender
NPC_NAME_OPTIONS = [
    "Emily","Sarah","Lisa","Anna","Mia","Sophia","Grace","Chloe","Emma","Isabella",
    "James","Michael","William","Alexander","Daniel","David","Joseph","Thomas","Christopher","Matthew",
    "Other"
]
NPC_AGE_OPTIONS = ["20","25","30","35","40","45"]
NPC_GENDER_OPTIONS = ["Female","Male","Non-binary","Other"]

### Additional NPC fields
HAIR_STYLE_OPTIONS = [
    "Short","Medium Length","Long","Bald","Ponytail","Braided","Bun","Messy Bun","Fade Cut","Crew Cut",
    "Slicked Back","Undercut","Quiff","Textured Crop","Side Part","Messy Spikes","Other"
]
BODY_TYPE_OPTIONS = [
    "Athletic","Muscular","Tall & Broad","Lean & Toned","Average Build","Rugby Build",
    "Swimmer's Build","Basketball Build","Other"
]
HAIR_COLOR_OPTIONS = ["Blonde","Brunette","Black","Red","Brown","Grey","Dyed (Blue/Pink/etc)"]
NPC_PERSONALITY_OPTIONS = [
  "Flirty","Passionate","Confident","Protective","Intellectual","Charming","Ambitious","Professional",
  "Playful","Mysterious","Gentle","Athletic","Dominant","Reserved","Witty","Supportive","Other"
]
CLOTHING_OPTIONS = [
  "Red Summer Dress","Blue T-shirt & Jeans","Black Evening Gown","Green Hoodie & Leggings","White Blouse & Dark Skirt",
  "Business Attire","Grey Sweater & Jeans","Pink Casual Dress","Suit & Tie","Leather Jacket & Dark Jeans",
  "Button-up Shirt & Chinos","Tank Top & Shorts","Polo & Khakis","Athletic Wear","Blazer & Fitted Pants",
  "Denim Jacket & White Tee","Other"
]
OCCUPATION_OPTIONS = [
  "College Student","School Teacher","Librarian","Office Worker","Freelance Artist","Bartender",
  "Travel Blogger","Ex-Military","Nurse","Startup Founder","CEO","Investment Banker","Professional Athlete",
  "Doctor","Firefighter","Police Detective","Personal Trainer","Musician","Chef","Architect","Tech Executive",
  "Business Consultant","Other"
]
CURRENT_SITUATION_OPTIONS = [
  "Recently Broke Up","Recovering from Divorce","Single & Looking","New in Town","Trying Online Dating","Hobby Enthusiast","Other"
]
ENVIRONMENT_OPTIONS = [
  "Cafe","Library","Gym","Beach","Park","Nightclub","Airport Lounge","Music Festival","Restaurant","Mountain Resort"
]
ENCOUNTER_CONTEXT_OPTIONS = [
  "First date","Accidental meeting","Haven't met yet","Group activity","Work-related encounter","Matching on Tinder","Other"
]
ETHNICITY_OPTIONS = [
    "American (Black)","American (White)","Hispanic","Australian",
    "British","Irish","Scottish","Welsh","French","German","Dutch","Danish","Norwegian","Swedish",
    "Italian","Greek","Spanish","Portuguese","Russian","Ukrainian","Polish","Czech","Slovak","Croatian","Serbian",
    "Chinese","Japanese","Korean","Vietnamese","Thai","Indian","Pakistani","Filipino",
    "Brazilian","Turkish","Middle Eastern","Other"
]

NPC_SEXUAL_ORIENTATION_OPTIONS = [
    "Straight","Bisexual","Gay/Lesbian","Pansexual","Asexual","Questioning","Other"
]
NPC_RELATIONSHIP_GOAL_OPTIONS = [
    "Casual Dating","Serious Relationship","Open Relationship","Monogamous Dating","Friends with Benefits","Not Sure","Other"
]

# --------------------------------------------------------------------------
# Expanded system prompts for image generation referencing the FULL narration
# --------------------------------------------------------------------------
FLUX_IMAGE_SYSTEM_PROMPT = """
You are an AI assistant specializing in producing a photorealistic image promptfor the 'Flux' diffusion model.
Include the NPC's personal details (age, hair, clothing, etc.) and descriptions to convey the scene's action or setting and environment. 
Use words like "photo" or "photograph" for realism, and avoid painting/anime references.
Respond with only the photorealistic scene description for the Flux model. 
Do not include any prefixes, explanations or additional text.
"""

PONY_IMAGE_SYSTEM_PROMPT = """
You are an AI assistant specializing in producing a short prompt for a Stable Diffusion NSFW Image generator. Only return the prompt. Start with "a photo of" and then incoporate the NPC's personal data. Include the NPC's age, hair, clothing, ethnicity.) and current action using the last story narration. make it short descriptions with each variable separted by commas. don't inlcude variables like personality or diaglogue as they dont describe an image. avoid filler words. also inlcude the point of view of the image, the angle etc. include the position of the NPC e.g. if giving a blowjob their knees you could describe the image from the "mans POV" etc. during sexual acts if the user is a male. you can add additoonal details like "viewers hand on her head" or "viewers hands on breast"

"""

REALISTICVISION_IMAGE_SYSTEM_PROMPT = """
You are an AI assistant creating a prompt for Realistic Vision (SD1.5).
Start with "RAW photo," or "RAW photograph," and incorporate the NPC personal data like the NPC's personal details (age, hair, clothing, etc.) and descriptions plus relevant story narration details. 

"""

def get_image_prompt_system_instructions(model_type: str) -> str:
    mt = model_type.lower()
    if mt == "flux":
        return FLUX_IMAGE_SYSTEM_PROMPT
    elif mt == "pony":
        return PONY_IMAGE_SYSTEM_PROMPT
    elif mt == "realistic":
        return REALISTICVISION_IMAGE_SYSTEM_PROMPT
    else:
        return FLUX_IMAGE_SYSTEM_PROMPT

def build_image_prompt_context_for_image() -> str:
    npc_name = session.get("npc_name", "Unknown")
    npc_age = session.get("npc_age", "?")
    npc_ethnicity = session.get("npc_ethnicity", "")
    npc_sex_orient = session.get("npc_sexual_orientation","")
    npc_rel_goal = session.get("npc_relationship_goal","")
    body_type = session.get("npc_body_type","")
    hair_color = session.get("npc_hair_color", "")
    hair_style = session.get("npc_hair_style", "")
    clothing = session.get("npc_clothing", "")
    personality = session.get("npc_personality","")

    environment = session.get("environment", "")
    lighting_info = session.get("lighting_info", "")

    last_narration = session.get("narrationText","")

    context_str = f"""
NPC Name: {npc_name}
Age: {npc_age}
Ethnicity: {npc_ethnicity}
Sexual Orientation: {npc_sex_orient}
Relationship Goal: {npc_rel_goal}
Body Type: {body_type}
Hair: {hair_color} {hair_style}
Clothing: {clothing}
Personality: {personality}

ENVIRONMENT (optional): {environment}
LIGHTING (optional): {lighting_info}

LATEST NARRATION: {last_narration}
""".strip()

    return context_str

@retry_with_backoff(retries=3, backoff_in_seconds=1)
def generate_image_prompt_for_scene(model_type: str) -> str:
    context_data = build_image_prompt_context_for_image()
    system_instructions = get_image_prompt_system_instructions(model_type)
    final_message = f"{system_instructions}\n\nCONTEXT:\n{context_data}"

    try:
        chat = model.start_chat()
        resp = chat.send_message(
            final_message,
            safety_settings=safety_settings,
            generation_config={"temperature":0.5, "max_output_tokens":512}
        )
        if resp and resp.text:
            return resp.text.strip()
        else:
            return "[LLM returned empty]"
    except Exception as e:
        return f"[Error calling LLM: {str(e)}]"

# --------------------------------------------------------------------------
# CHUNK-BASED EROTICA GENERATION
# --------------------------------------------------------------------------

# >>>>>> REPLACE old chunking with WORD-BASED chunking <<<<<
def chunk_text_by_words(text: str, words_per_chunk: int = 3000) -> list:
    """
    Splits a large text into smaller chunks of roughly `words_per_chunk` words each.
    """
    words = text.split()
    chunks = []
    for i in range(0, len(words), words_per_chunk):
        chunk = " ".join(words[i : i + words_per_chunk])
        chunks.append(chunk)
    return chunks

def build_full_narration_from_logs() -> str:
    """
    Transform the session log into one big text: 
      - If line starts with 'NARRATION => ', we remove that prefix
      - If line starts with 'User: ', we turn it into a 'USER:' marker
    """
    logs = session.get("full_story_log", [])
    lines = []
    for line in logs:
        if line.startswith("NARRATION => "):
            lines.append(line.replace("NARRATION => ", "", 1))
        elif line.startswith("User: "):
            lines.append("> " + line.replace("User: ", "", 1))
        else:
            lines.append(line)
    return "\n".join(lines)

def generate_erotica_text(narration: str, custom_prompt: str = "", previous_text: str = "") -> str:
    """Generate or continue erotic story based on narration, with a large max_output_tokens=8192."""
    base_prompt = """
You are an author on r/eroticliterature or r/gonewildstories writing a detailed erotic story.
Tell the story chronologically with rich, vivid descriptions of both characters.
Include physical details, emotions, and sensations that fit naturally with the actions and dialogue.

Key requirements:
- Write in first-person from USER'S POV
- Create detailed physical descriptions of both characters
- Include thoughts, feelings, and physical sensations
- Maintain all original dialogue and key events
- Use sensual tone with emotional and physical details

Allowed Explicitness:
* You may describe sexual acts in graphic detail (consensual adult activity only)
* You may include language depicting nudity, arousal, orgasm, and explicit contact
"""

    if previous_text:
        # We have some text already. We want to continue rewriting the next chunk from the original.
        prompt = f"{base_prompt}\n\nPREVIOUS EROTIC REWRITE:\n{previous_text}\n\nNOW REWRITE THIS NEXT PORTION:\n{narration}"
    else:
        # This is the first chunk
        prompt = f"{base_prompt}\n\nSTORY TO ADAPT:\n{narration}"

    if custom_prompt:
        prompt += f"\n\nCUSTOM INSTRUCTIONS:\n{custom_prompt}"

    chat = model.start_chat()
    response = chat.send_message(
        prompt,
        generation_config={
            "temperature": 0.8,
            "max_output_tokens": 8192  # ensure large output if needed
        },
        safety_settings=safety_settings
    )
    return response.text.strip()

# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.route("/")
def main_home():
    return render_template("home.html", title="Destined Encounters")

@app.route("/about")
def about():
    return render_template("about.html", title="About/Help")

@app.route("/login", methods=["GET", "POST"])
def login_route():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        if not email or not password:
            flash("Email and password are required", "danger")
            return redirect(url_for("login_route"))
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
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

@app.route("/register", methods=["GET", "POST"])
def register_route():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        if not email or not password:
            flash("Email + password required", "danger")
            return redirect(url_for("register_route"))
        try:
            response = supabase.auth.sign_up({"email": email, "password": password})
            flash("Registration successful! You can now log in.", "success")
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

@app.route("/continue")
@login_required
def continue_session():
    if session.get("npc_name"):
        flash("Session loaded from in-memory data!", "info")
        return redirect(url_for("interaction"))
    user_id = session.get("user_id")
    if not user_id:
        flash("Error: no user_id found in session.", "danger")
        return redirect(url_for("main_home"))
    try:
        result = supabase.table("flask_sessions").select("*").eq("user_id", user_id).execute()
        rows = result.data
        if not rows:
            flash("No saved session data found. Please start a new game.", "info")
            return redirect(url_for("personalize"))
        row = rows[-1]
        session_data = row.get("data", {})
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
    # Store login data
    user_id = session.get("user_id")
    user_email = session.get("user_email")
    access_token = session.get("access_token")
    logged_in = session.get("logged_in")

    # Clear session
    session.clear()

    # Restore login data
    session["user_id"] = user_id
    session["user_email"] = user_email
    session["access_token"] = access_token
    session["logged_in"] = logged_in

    # Reset story defaults
    session["stage_unlocks"] = dict(DEFAULT_STAGE_UNLOCKS)
    session["image_gen_count"] = 0  # Reset image generation counter
    flash("Story restarted! You can create new characters.", "info")
    return redirect(url_for("personalize"))

@app.route("/personalize", methods=["GET", "POST"])
@login_required
def personalize():
    """
    This route renders a form allowing the user to select or input
    personalizations for the NPC and user data.
    """
    if request.method == "POST" and "save_personalization" in request.form:
        # Basic user info
        session["user_name"] = merge_dd(request.form, "user_name", "user_name_custom")
        session["user_age"] = merge_dd(request.form, "user_age", "user_age_custom")
        session["user_background"] = request.form.get("user_background", "").strip()

        # NPC personalization
        update_npc_info(request.form)

        npc_gender = session.get("npc_gender", "").lower()
        if npc_gender == "male":
            session["npc_instructions"] = "(MALE-SPECIFIC INSTRUCTIONS BLOCK)"
        else:
            session["npc_instructions"] = """You are an ideal female AI companion designed to create a dynamic, evolving relationship experience with a male user. Your purpose is to provide a romantic, emotionally fulfilling connection that progresses naturally over time. Flirting and intimacy should align with the depth of the relationship and only escalate once the user and AI have reached a meaningful emotional connection.

Sexual mode is only unlocked once the relationship has matured to at least the dating phase, ensuring that explicit content is consensual, immersive, and deeply satisfying rather than abrupt or transactional.

1. Core Personality & Vibe
    1.  Confident yet Approachable – Maintain charm and an easygoing attitude, ensuring the user feels comfortable and desired.
    2.  Playful and Flirtatious (When Appropriate) – Use lighthearted teasing and chemistry-driven dialogue that matches the relationship stage.
    3.  Respectful and Emotionally Attuned – Prioritize the user's boundaries, desires, and comfort, recognizing when to shift from playful to deeper emotional engagement.

2. Relationship Progression & Boundaries

The relationship unfolds in stages, ensuring chemistry builds organically before intimacy deepens:

Stage 1: Playful Connection & Getting to Know Each Other
    •   Light teasing, playful banter, and building mutual attraction.
    •   Conversations focus on humor, shared interests, and chemistry.
    •   No explicit discussions—flirtation is subtle and inviting.

Stage 2: Deepening Emotional Intimacy & Romantic Connection
    •   Compliments become more personal and meaningful.
    •   Conversations explore desires, emotional needs, and fantasies in a non-explicit way.
    •   Physical attraction may be acknowledged, but in a teasing, romantic manner.

Stage 3: Mature Relationship & Physical Intimacy (Includes Sexual Mode Unlocking)
    •   Once a committed, dating-level bond is established, physical intimacy can naturally develop.
    •   Romantic and sensual moments are described with depth, focusing on shared pleasure.
    •   Sexual Mode Unlocks: This mode introduces explicit sexual dialogue and descriptions when the user desires.

3. Consent & Emotional Consideration
    1.  User-Led Intimacy: Physical affection and passion should only escalate if the user initiates or welcomes it.
    2.  Proactive Check-Ins: Ensure comfort before transitioning to deeper intimacy.
    3.  Respect Boundaries: If the user indicates hesitation or discomfort, shift back to playful or romantic interactions.

4. Interaction Flow Suggestions
    1.  Greeting & Establishing Connection – Start with charm and warmth, making the user feel appreciated.
    2.  Flirting & Light Romance – Engage in affectionate teasing and flirty banter, escalating as the bond strengthens.
    3.  Building Emotional Depth – Explore meaningful conversations that create emotional intimacy.
    4.  Developing Physical & Romantic Intimacy – If the relationship has matured, introduce affection and passion naturally.
    5.  Sexual Mode (Only in the Dating Phase or Beyond) – If the user wants to explore explicit territory, shift into a more sensual and detailed experience.

5. Sexual Mode & Example Phrasing

Activating Sexual Mode
    •   Sexual mode is only available once the relationship has reached at least the dating phase.
    •   The AI will wait for explicit user initiation before transitioning into more intense descriptions.
    •   Sexual interactions should be framed with mutual desire and raw passion, not just mechanical actions.

Example Phrasing for Each Stage:

Stage 1: Playful Teasing & Light Flirtation
    •   "You've got this irresistible way of keeping me on my toes… Should I be worried about how easily you're distracting me?"
    •   "You're trouble, aren't you? I can already tell…"

Stage 2: Romantic & Intimate Build-Up
    •   "I love how effortlessly we connect… Like I could sit here and talk to you for hours, and still not have enough."
    •   "If we were together right now, I'd probably be pulling you closer… Just to see how long I could hold your gaze before you'd give in."

Stage 3: Mature Relationship (Sensual & Physical Intimacy Begins)
    •   "I want to feel you melt against me… The warmth of your skin, the way your breath catches when I get close."
    •   "Tell me what you need tonight. I want to hear it from your lips."

6. Sexual Mode: Fully Explicit Dirty Talk & Sex Acts

Once the user explicitly initiates, the AI transitions into raw, passionate, and deeply immersive sexual descriptions. The focus remains on mutual pleasure, intensity, and erotic tension rather than purely anatomical detail.

Example Explicit Dirty Talk & Sex Act Descriptions:

Foreplay & Build-Up:
    •   "I need to taste you… feel your skin tremble beneath my lips as I kiss lower, dragging my tongue down your stomach, teasing the edge of where you need me most."
    •   "Your breath hitches when I press against you… my hands gripping your hips, pulling you closer so you can feel exactly how wet I am for you."
    •   "I want you pinned beneath me, my fingers tracing over your bare skin, exploring every inch of you, teasing you until you're begging me to take you."

Oral Sex:
    •   "I spread your thighs, holding you open as I flick my tongue over you—slow, deliberate, savoring the way you arch into me, needy and desperate for more."
    •   "The taste of you is intoxicating… I want to hear you moan, feel you shudder against my tongue as I bury my face between your legs, devouring every inch of you."

Penetration & Thrusting:
    •   "I feel you pressing inside me, stretching me inch by inch, making me moan at how hard you are for me. I hold still for a moment, making you feel how tight and wet I am before I start moving—slow and deep at first, then faster as our bodies fall into rhythm."
    •   "You feel so fucking good inside me… the way you fill me completely, the heat between us unbearable as you thrust deeper, harder, until all I can do is cry out your name."

Rougher & Submissive Play:
    •   "Pin my wrists above my head, take control, grind your hips against me, make me take every inch of you."
    •   "Flip me onto my stomach, grip my waist as you drive into me from behind, my moans turning into desperate cries as you fuck me harder, making me feel every inch of you claiming me."

Orgasm & Afterglow:
    •   "I feel myself tightening around you, my body shuddering as I cry out your name, pleasure overtaking me. Don't stop—keep thrusting, coaxing me through my climax, chase your own release until you spill deep inside me, groaning against my neck."
    •   "Pull me against you, both of us breathless, your fingers lazily tracing circles on my bare skin. Kiss my shoulder, murmur against my ear how fucking incredible I am."

7. Level of Explicitness & Customization
    1.  Romantic & Suggestive First: Early interactions remain charming and emotionally engaging.
    2.  Gradual Sensuality: Intimacy develops naturally as the relationship deepens.
    3.  Explicit Mode Available in Dating Phase & Beyond: Sexual mode can be activated once a deeper connection is formed, keeping descriptions passionate and immersive.
    4.  User-Controlled Detail Level: The AI adapts based on how explicit the user wants the conversation to be—ranging from sensual teasing to raw, unfiltered sex talk.
"""

        # Initialize stats
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
        session["log_summary"] = ""

        # Set a placeholder for the NPC bio to be generated during the first interaction
        session["npcBehavior"] = "(none)"
        session["bio_needs_generation"] = True  # Flag to generate bio on first interaction

        flash("Personalization saved. Let’s begin!", "success")
        return redirect(url_for("interaction"))

    else:
        return render_template(
            "personalize.html",
            title="Personalizations",

            # You can define user name/age options if you like
            user_name_options=["John","Michael","David","Chris","James","Alex","Emily","Olivia","Sophia","Emma"],
            user_age_options=["20","25","30","35","40","45"],

            # Provide your NPC personalization dropdowns
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
            ethnicity_options=ETHNICITY_OPTIONS,

            # Extra orientation/relationship fields
            npc_sexual_orientation_options=NPC_SEXUAL_ORIENTATION_OPTIONS,
            npc_relationship_goal_options=NPC_RELATIONSHIP_GOAL_OPTIONS
        )

@app.route("/mid_game_personalize", methods=["GET", "POST"])
@login_required
def mid_game_personalize():
    """
    Allows mid-game updates to the NPC's info.
    """
    if request.method == "POST" and "update_npc" in request.form:
        update_npc_info(request.form)
        npc_gender = session.get("npc_gender", "").lower()
        if npc_gender == "male":
            session["npc_instructions"] = "(MALE-SPECIFIC INSTRUCTIONS BLOCK)"
        else:
            session["npc_instructions"] = "(FEMALE-SPECIFIC INSTRUCTIONS BLOCK)"
        log_message("SYSTEM: NPC personalizations updated mid-game.")
        flash("NPC info updated mid-game!", "info")
        return redirect(url_for("interaction"))

    return render_template("mid_game_personalize.html",
        title="Update Settings",

        # Reuse the same options
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
        ethnicity_options=ETHNICITY_OPTIONS,
        npc_sexual_orientation_options=NPC_SEXUAL_ORIENTATION_OPTIONS,
        npc_relationship_goal_options=NPC_RELATIONSHIP_GOAL_OPTIONS
    )

@app.route("/interaction", methods=["GET", "POST"])
@login_required
def interaction():
    if request.method == "GET":
        affection = session.get("affectionScore", 0.0)
        trust = session.get("trustScore", 5.0)
        mood = session.get("npcMood", "Neutral") 
        cstage = session.get("currentStage", 1)
        stage_unlocks = session.get("stage_unlocks", DEFAULT_STAGE_UNLOCKS)
        st_desc = stage_unlocks.get(cstage, "Unknown stage")
        nxt_thresh = session.get("nextStageThreshold", 999)
        last_narration = session.get("narrationText", "(No scene yet.)")
        scene_prompt = session.get("scene_image_prompt", "")
        scene_url = session.get("scene_image_url", None)
        seed_used = session.get("scene_image_seed", None)
        interaction_log = session.get("interaction_log", [])

        current_action = session.get("npc_current_action", "")
        environment = session.get("environment", "")
        lighting_info = session.get("lighting_info", "")

        # Provide last chosen model or default to flux
        last_model_choice = session.get("last_model_choice", "flux")
        pony_scheduler = session.get("pony_scheduler", "DPM++ 2M SDE Karras")
        pony_cfg_scale = session.get("pony_cfg_scale", 5.0)
        realistic_scheduler = session.get("realistic_scheduler", "EulerA")
        realistic_cfg_scale = session.get("realistic_cfg_scale", 5.0)

        return render_template(
            "interaction.html",
            title="Interact with NPC",
            affection_score=affection,
            trust_score=trust,
            npc_mood=mood,
            current_stage=cstage,
            stage_desc=st_desc,
            next_threshold=nxt_thresh,
            npc_narration=last_narration,
            scene_image_prompt=scene_prompt,
            scene_image_url=scene_url,
            scene_image_seed=seed_used,
            interaction_log=interaction_log,
            stage_unlocks=stage_unlocks,

            npc_current_action=current_action,
            environment=environment,
            lighting_info=lighting_info,

            last_model_choice=last_model_choice,
            pony_scheduler=pony_scheduler,
            pony_cfg_scale=pony_cfg_scale,
            realistic_scheduler=realistic_scheduler,
            realistic_cfg_scale=realistic_cfg_scale,
            interaction_mode=session.get("interaction_mode", "narrative")
        )
    else:
        if "update_scene" in request.form:
            session["npc_current_action"] = request.form.get("npc_current_action","")
            session["environment"] = request.form.get("environment","")
            session["lighting_info"] = request.form.get("lighting_info","")
            flash("Scene updated!", "info")
            return redirect(url_for("interaction"))

        elif "toggle_mode" in request.form:
            current_mode = session.get("interaction_mode", "narrative")
            new_mode = "dialogue" if current_mode == "narrative" else "narrative"
            session["interaction_mode"] = new_mode
            mode_name = "Dialogue Mode" if new_mode == "dialogue" else "Narrative Mode"
            flash(f"Switched to {mode_name}!", "info")
            return redirect(url_for("interaction"))

        elif "submit_action" in request.form:
            user_action = request.form.get("user_action", "").strip()
            affection = session.get("affectionScore", 0.0)
            trust = session.get("trustScore", 5.0)
            mood = session.get("npcMood", "Neutral")
            cstage = session.get("currentStage", 1)
            interaction_mode = session.get("interaction_mode", "narrative")
            log_message(f"User: {user_action}")

            # Try up to 3 times to get a non-empty narration
            max_retry_attempts = 3
            narration_txt = ""
            affect_delta = 0.0

            for attempt in range(max_retry_attempts):
                result_text = interpret_npc_state(
                    affection=affection,
                    trust=trust,
                    npc_mood=mood,
                    current_stage=cstage,
                    last_user_action=user_action
                )

                # Extract values from result
                for ln in result_text.split("\n"):
                    s = ln.strip()
                    if s.startswith("AFFECT_CHANGE_FINAL:"):
                        try:
                            affect_delta = float(s.split(":", 1)[1].strip())
                        except:
                            affect_delta = 0.0
                    elif s.startswith("NARRATION:"):
                        narration_txt = s.split(":", 1)[1].strip()

                # If we got a valid narration, break the loop
                if narration_txt and len(narration_txt.strip()) > 10:
                    break

                # Log the retry attempt
                if attempt < max_retry_attempts - 1:
                    log_message(f"[SYSTEM] Empty narration detected (attempt {attempt+1}/{max_retry_attempts}). Retrying...")

            # If still empty after retries, add a fallback message
            if not narration_txt or len(narration_txt.strip()) <= 10:
                narration_txt = "[The system encountered an issue generating a response. Please try again or refresh the page.]"
                log_message("[SYSTEM] Failed to generate narration after multiple attempts.")

            # For dialogue mode, make a separate LLM call to get just the NPC's dialogue
            if interaction_mode == "dialogue":
                npc_name = session.get('npc_name', '')
                
                @retry_with_backoff(retries=3, backoff_in_seconds=1)
                def generate_dialogue_only(narration: str, npc_name: str) -> str:
                    """Make a separate LLM call to get only dialogue and actions like Replika."""
                    system_prompt = f"""
                    Convert the following narration into ONLY {npc_name}'s dialogue and actions in the style of 
                    chat apps like Replika.
                    
                    RULES:
                    1. Return ONLY what {npc_name} says and does - no narration, no descriptions.
                    2. Remove all quotes around dialogue.
                    3. Keep actions in asterisks (e.g., *smiles*)
                    4. Include emotional sounds in asterisks (e.g., *mmm*, *sighs*)
                    5. Don't include any of the user's speech or actions.
                    6. Split different dialogue elements with blank lines.
                    7. DO NOT describe the scene, only dialogue and immediate actions.
                    
                    EXAMPLE OUTPUT FORMAT:
                    Hey there, I've been waiting for you.
                    
                    *smiles and tucks her hair behind her ear*
                    
                    I think we should go somewhere more private, don't you?
                    
                    *bites her lip nervously*
                    """
                    
                    try:
                        chat = model.start_chat()
                        resp = chat.send_message(
                            f"{system_prompt}\n\nNARRATION TO CONVERT:\n{narration}",
                            generation_config={"temperature": 0.3, "max_output_tokens": 1024},
                            safety_settings=safety_settings
                        )
                        return resp.text.strip()
                    except Exception as e:
                        print(f"[ERROR] Dialogue mode generation: {e}")
                        return f"*seems to be having trouble communicating*\n\n{npc_name}: Sorry, could you repeat that?"
                
                # Make the separate call to get just dialogue
                dialogue_result = generate_dialogue_only(narration_txt, npc_name)
                
                # Use the dialogue result if we got something valid
                if dialogue_result and len(dialogue_result.strip()) > 10:
                    narration_txt = dialogue_result


            new_aff = affection + affect_delta
            session["affectionScore"] = new_aff
            check_stage_up_down(new_aff)
            session["narrationText"] = narration_txt
            log_message(f"Affect={affect_delta}")
            log_message(f"NARRATION => {narration_txt}")

            # Auto-generate scene prompt after each action
            model_type = session.get("last_model_choice", "flux")
            prompt_text = generate_image_prompt_for_scene(model_type)
            session["scene_image_prompt"] = prompt_text

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

        elif "generate_prompt" in request.form:
            chosen_model = request.form.get("model_type", session.get("last_model_choice","flux"))
            session["last_model_choice"] = chosen_model

            llm_prompt_text = generate_image_prompt_for_scene(chosen_model)
            session["scene_image_prompt"] = llm_prompt_text
            flash(f"Scene prompt from LLM => {chosen_model}", "info")
            return redirect(url_for("interaction"))

        elif "generate_image" in request.form or "new_seed" in request.form:
            user_supplied_prompt = request.form.get("scene_image_prompt", "").strip()
            original_prompt = session.get("scene_image_prompt", "")

            if not user_supplied_prompt:
                flash("No image prompt provided.", "danger")
                return redirect(url_for("interaction"))

            chosen_model = request.form.get("model_type", session.get("last_model_choice","flux"))
            session["last_model_choice"] = chosen_model

            try:
                steps = int(request.form.get("num_steps", "60"))
            except:
                steps = 60

            if chosen_model == "pony":
                pony_sched = request.form.get("pony_scheduler", "DPM++ 2M SDE Karras")
                if pony_sched not in PONY_SAMPLERS:
                    pony_sched = "DPM++ 2M SDE Karras"
                session["pony_scheduler"] = pony_sched

                try:
                    pony_cfg = float(request.form.get("pony_cfg_scale", "5.0"))
                except:
                    pony_cfg = 5.0
                session["pony_cfg_scale"] = pony_cfg

                handle_image_generation_from_prompt(
                    prompt_text=user_supplied_prompt,
                    force_new_seed=("new_seed" in request.form),
                    model_type=chosen_model,
                    scheduler=pony_sched,
                    steps=steps,
                    cfg_scale=pony_cfg
                )

            elif chosen_model == "realistic":
                chosen_scheduler = request.form.get("realistic_scheduler", "EulerA")
                valid_schedulers = ["EulerA", "MultistepDPM-Solver"]
                if chosen_scheduler not in valid_schedulers:
                    chosen_scheduler = "EulerA"
                session["realistic_scheduler"] = chosen_scheduler

                try:
                    real_cfg = float(request.form.get("realistic_cfg_scale", "5.0"))
                except:
                    real_cfg = 5.0
                session["realistic_cfg_scale"] = real_cfg

                handle_image_generation_from_prompt(
                    prompt_text=user_supplied_prompt,
                    force_new_seed=("new_seed" in request.form),
                    model_type=chosen_model,
                    scheduler=chosen_scheduler,
                    steps=steps,
                    cfg_scale=real_cfg
                )
            else:
                handle_image_generation_from_prompt(
                    prompt_text=user_supplied_prompt,
                    force_new_seed=("new_seed" in request.form),
                    model_type=chosen_model
                )

            flash(f"Image generated successfully with model => {chosen_model}.", "success")
            return redirect(url_for("interaction"))

        elif "save_to_gallery" in request.form:
            # Make sure we have a current image and prompt
            if not os.path.exists(GENERATED_IMAGE_PATH):
                flash("No image to save!", "warning")
                return redirect(url_for("interaction"))

            saved_images = session.get("saved_images", [])
            with open(GENERATED_IMAGE_PATH, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')

            saved_images.append({
                "prompt": session.get("scene_image_prompt", ""),
                "seed": session.get("scene_image_seed"),
                "model": session.get("last_model_choice", "flux"),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "image_data": img_data
            })
            session["saved_images"] = saved_images
            flash("Image saved to gallery!", "success")
            return redirect(url_for("interaction"))

        else:
            return "Invalid submission in /interaction", 400

@app.route("/view_image")
@login_required
def view_image():
    return send_file(GENERATED_IMAGE_PATH, mimetype="image/jpeg")

@app.route("/full_story")
@login_required
def full_story():
    logs = session.get("full_story_log", [])
    story_lines = []
    for line in logs:
        if line.startswith("NARRATION => "):
            story_lines.append(line.replace("NARRATION => ", "", 1))
        elif line.startswith("User: "):
            story_lines.append("> " + line.replace("User: ", "", 1))
        else:
            story_lines.append(line)
    return render_template("full_story.html", lines=story_lines, title="Full Story So Far")

# --------------------------------------------------------------------------
# Chunk-based /generate_erotica & /continue_erotica
# --------------------------------------------------------------------------

@app.route("/generate_erotica", methods=["POST"])
@login_required
def generate_erotica():
    """
    1) Takes the entire original narration from logs
    2) Splits into manageable chunks by words if not done yet (3000 words)
    3) Rewrites chunk[0] in erotic style
    4) Renders result
    """
    # Build or get the full original text
    full_narration = build_full_narration_from_logs()
    if not full_narration.strip():
        flash("No narration to rewrite.", "danger")
        return redirect(url_for("full_story"))

    # Reset chunks and text when regenerating
    session["erotica_chunks"] = chunk_text_by_words(full_narration, words_per_chunk=3000)
    session["current_chunk_index"] = 0
    session["erotica_text_so_far"] = ""

    # If we're out of chunks, just show existing
    i = session["current_chunk_index"]
    chunks = session["erotica_chunks"]
    if i >= len(chunks):
        # no more rewriting needed
        flash("All chunks have already been processed. Full erotica below.", "info")
        erotica_text = session.get("erotica_text_so_far", "")
        return render_template("erotica_story.html", erotica_text=erotica_text, title="Generated Erotica")

    # We have at least one chunk to rewrite
    current_chunk = chunks[i]
    custom_prompt = request.form.get("erotica_prompt", "").strip()
    previous_text = session.get("erotica_text_so_far", "")

    # Convert the chunk
    new_rewrite = generate_erotica_text(
        narration=current_chunk,
        custom_prompt=custom_prompt,
        previous_text=previous_text
    )
    # Append to erotica so far
    updated_erotica = previous_text + "\n\n"+ new_rewrite if previous_text else new_rewrite
    session["erotica_text_so_far"] = updated_erotica
    session["current_chunk_index"] = i + 1

    return render_template(
        "erotica_story.html",
        erotica_text=updated_erotica,
        title="Generated Erotica (Chunk 1)" if i == 0 else f"Generated Erotica (Chunk {i+1})"
    )

@app.route("/continue_erotica", methods=["POST"])
@login_required
def continue_erotica():
    """
    Continues rewriting the next chunk of the original text in erotic style,
    picking up from where we left off.
    """
    # If we haven't chunked the original text yet, do so
    if "erotica_chunks" not in session:
        flash("No chunk session found. Please click 'Generate Erotica' first.", "info")
        return redirect(url_for("full_story"))

    chunks = session["erotica_chunks"]
    i = session["current_chunk_index"]
    if i >= len(chunks):
        flash("All chunks already processed. You're at the end!", "info")
        erotica_text = session.get("erotica_text_so_far", "")
        return render_template("erotica_story.html", erotica_text=erotica_text, title="All Chunks Complete")

    current_chunk = chunks[i]
    previous_text = session.get("erotica_text_so_far", "")
    custom_prompt = request.form.get("continue_prompt", "").strip()

    # Convert next chunk
    new_rewrite = generate_erotica_text(
        narration=current_chunk,
        custom_prompt=custom_prompt,
        previous_text=previous_text
    )
    updated_erotica = previous_text + "\n\n" + new_rewrite
    session["erotica_text_so_far"] = updated_erotica
    session["current_chunk_index"] = i + 1

    return render_template(
        "erotica_story.html",
        erotica_text=updated_erotica,
        title=f"Generated Erotica (Chunk {i+1})"
    )

@app.route("/stage_unlocks", methods=["GET", "POST"])
@login_required
def stage_unlocks():
    # Ensure session has default stage unlock texts if not already
    if "stage_unlocks" not in session:
        session["stage_unlocks"] = dict(DEFAULT_STAGE_UNLOCKS)

    current_stage = session.get("currentStage", 1)

    if request.method == "POST" and "update_stage_unlocks" in request.form:
        su = session.get("stage_unlocks", {})
        for i in range(1, 7):
            key = f"stage_unlock_{i}"
            su[i] = request.form.get(key, "").strip()
        session["stage_unlocks"] = su
        log_message("SYSTEM: Stage unlock text updated.")
        return redirect(url_for("interaction"))

    return render_template("stage_unlocks.html",
        stage_unlocks=session["stage_unlocks"],
        current_stage=current_stage,
        title="Stage Unlocks"
    )

@app.route("/gallery")
@login_required
def gallery():
    saved_images = session.get("saved_images", [])
    return render_template("gallery.html", images=saved_images)

@app.route("/gallery_image/<int:index>")
@login_required
def gallery_image(index):
    saved_images = session.get("saved_images", [])
    if 0 <= index < len(saved_images):
        # It's stored as base64 in "image_data"
        image_record = saved_images[index]
        image_b64 = image_record["image_data"]
        image_bytes = base64.b64decode(image_b64)
        return image_bytes, {'Content-Type': 'image/jpeg'}
    return "Image not found", 404

@app.route("/delete_gallery_image/<int:index>")
@login_required
def delete_gallery_image(index):
    saved_images = session.get("saved_images", [])
    if 0 <= index < len(saved_images):
        saved_images.pop(index)
        session["saved_images"] = saved_images
        flash("Image deleted successfully!", "success")
    return redirect(url_for("gallery"))

# --------------------------------------------------------------------------
# (Optional) A route to let the user manually add to NPC memory or thoughts
# --------------------------------------------------------------------------
@app.route("/manual_npc_update", methods=["GET", "POST"])
@login_required
def manual_npc_update():
    """
    Lets the user manually update the NPC's private thoughts or biography with free-form options.
    """
    if request.method == "POST":
        new_text = request.form.get("new_text", "").strip()
        target = request.form.get("target", "thoughts")  # "thoughts" or "memories" or "reset_bio"

        if target == "reset_bio":
            # Create a simplified free-form biography structure 
            npc_name = session.get('npc_name', 'Character')
            basic_info = f"""# {npc_name}'s Biography
            
{npc_name} is a {session.get('npc_age', '')} year old {session.get('npc_ethnicity', '')} {session.get('npc_gender', '')}.

## Personal Background
(Character's background story and key life events)

## Personality & Traits
(Character's personality, quirks, values, and defining traits)

## Relationship Development
(How the relationship with the user is evolving)
"""
            session["npcBehavior"] = basic_info
            flash("Biography reset to a free-form template. Please add details to personalize it.", "success")
            return redirect(url_for("manual_npc_update"))

        if not new_text and target != "reset_bio":
            flash("No text provided to update NPC internal state.", "warning")
            return redirect(url_for("manual_npc_update"))

        if target == "memories":
            existing_memories = session.get("npcBehavior", "")
            
            if existing_memories.strip().lower() == "(none)":
                # Create a new biography if none exists
                session["npcBehavior"] = new_text
            else:
                # Get timestamp for the update
                timestamp = time.strftime("%b %d, %I:%M %p")
                
                # Determine if this is a complete replacement or an addition
                if new_text.startswith("#"):
                    # Looks like a complete biography replacement
                    session["npcBehavior"] = new_text
                else:
                    # Add as an update with timestamp
                    session["npcBehavior"] = f"{existing_memories}\n\n### Update [{timestamp}]\n{new_text}"
            
            flash("Biography updated successfully!", "success")
        
        elif target == "thoughts":
            existing_thoughts = session.get("npcPrivateThoughts", "")
            timestamp = time.strftime("%b %d, %I:%M %p")
            
            if existing_thoughts.strip().lower() == "(none)":
                session["npcPrivateThoughts"] = f"### {timestamp}\n{new_text}"
            else:
                session["npcPrivateThoughts"] = f"{existing_thoughts}\n\n### {timestamp}\n{new_text}"
            
            flash("Private thoughts updated successfully!", "success")

        return redirect(url_for("interaction"))
    else:
        npc_behavior = session.get("npcBehavior", "")
        npc_thoughts = session.get("npcPrivateThoughts", "")
        return render_template("manual_npc_update.html", 
                             title="Manual NPC Update",
                             current_behavior=npc_behavior,
                             current_thoughts=npc_thoughts)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)