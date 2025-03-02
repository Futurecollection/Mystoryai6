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

def deduplicate_text_sections(text: str, section_marker: str = "###", max_sections: int = 5) -> str:
    """
    Prevents excessive repetition in text by keeping only a limited number of sections.
    Args:
        text: The text containing multiple sections
        section_marker: String that marks the beginning of each section
        max_sections: Maximum number of sections to keep
    Returns:
        Deduplicated text with only the most recent sections
    """
    sections = text.split(section_marker)
    
    # If we have a header section without the marker (first item), keep it
    if sections and not sections[0].strip():
        sections.pop(0)  # Remove empty first section if present
        
    # If we don't have more sections than max, just return the original
    if len(sections) <= max_sections:
        return text
        
    # Keep the header (if there is one) and the most recent sections
    if sections[0].strip() and not any(marker in sections[0] for marker in ["###", "##", "#"]):
        # First section is a header without markers
        header = sections[0]
        retained_sections = [header] + [section_marker + s for s in sections[-(max_sections-1):]]
    else:
        # No special header, just keep the most recent sections
        retained_sections = [section_marker + s for s in sections[-max_sections:]]
        
    return "".join(retained_sections)

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
    """Construct a detailed biography for the NPC using all available personalization data.
    If limited information is available, use the LLM to generate additional details."""
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
    
    # Check if we have enough basic information or need LLM to fill in missing details
    missing_key_fields = (
        name == 'Unknown' or gender == '?' or age == '?' or 
        personality == '?' or occupation == '?' or 
        hair_color == '?' or clothing == '?'
    )
    
    # If missing key fields, use LLM to generate a complete biography
    if missing_key_fields and GEMINI_API_KEY:
        try:
            return generate_llm_biography(
                name, gender, age, ethnicity, orientation, relationship_goal,
                personality, body_type, hair_color, hair_style, clothing,
                occupation, current_situation, backstory, environment,
                encounter_context, user_name
            )
        except Exception as e:
            print(f"[ERROR] LLM biography generation failed: {e}")
            # Fall back to narrative approach if LLM fails
    
    # Format a narrative-style biography without rigid section structure
    biography = f"# {name}'s Biography\n\n"
    
    # Opening paragraph with core details
    biography += f"{name} is a {age}-year-old {ethnicity} {gender} with {hair_color.lower() if hair_color != '?' else ''} {hair_style.lower() if hair_style != '?' else 'hair'} and a {body_type.lower() if body_type != '?' else 'distinctive'} physique. "
    biography += f"Working as a {occupation}, their {personality.lower() if personality != '?' else 'unique'} personality shines through in how they approach both their professional and personal life. "
    
    # Current life situation
    if current_situation and current_situation != '?':
        if "broke up" in current_situation.lower():
            biography += f"Having recently ended a relationship, {name} is navigating the complex emotions that come with moving on. The breakup left some unresolved feelings, but also opened up possibilities for new connections. "
        elif "divorce" in current_situation.lower():
            biography += f"Still processing a recent divorce, {name} is rediscovering who they are as an individual again. The experience changed their perspective on relationships, making them more thoughtful about what they truly want. "
        elif "single" in current_situation.lower():
            biography += f"Currently single, {name} has been focused on personal growth and self-discovery. While comfortable with independence, there's a natural desire for meaningful connection that brings them to social settings. "
        elif "new in town" in current_situation.lower():
            biography += f"New to the area, {name} is still finding their footing. The excitement of new beginnings mixes with occasional homesickness, creating a unique openness to new experiences and connections. "
        else:
            biography += f"Currently {current_situation.lower()}, {name} is in a transitional period that has them reflecting on their priorities and desires. "
    else:
        biography += f"At this point in their life, {name} is navigating a period of personal growth and change. "
    
    # Appearance and style
    if clothing and clothing != '?':
        biography += f"Today they're wearing {clothing.lower()}, which reflects their personal style and the image they want to project. The way they present themselves—confident yet approachable—draws attention in subtle ways. "
    else:
        biography += f"Their style is distinctive and carefully considered, reflecting both practicality and a subtle flair that makes them memorable. "
    
    # Relationship approach and orientation
    if orientation != '?' and relationship_goal != '?':
        biography += f"\n\n{name} identifies as {orientation.lower()} and is looking for {relationship_goal.lower()}. "
        if "casual" in relationship_goal.lower():
            biography += f"They value their independence and prefer relationships that allow for spontaneity without heavy expectations. Past experiences have taught them that forced commitment often leads to disappointment, so they approach connections with honesty about their intentions. "
        elif "serious" in relationship_goal.lower():
            biography += f"Having experienced enough surface-level connections, they're seeking something with genuine depth and potential for growth. They believe in taking the time to build trust before fully investing emotionally. "
        else:
            biography += f"Their approach to dating is straightforward and authentic—they believe in being clear about intentions while remaining open to how connections naturally evolve. "
    else:
        biography += f"\n\n{name}'s approach to relationships balances caution with genuine openness. Past experiences have shaped their expectations, making them value authenticity above all else in potential partners. "
    
    # Background/history
    if backstory:
        biography += f"\n\n{backstory}\n"
    else:
        biography += f"\n\n{name} was raised in a {random.choice(['coastal town with stunning ocean views', 'bustling metropolitan area', 'close-knit suburban community', 'rural setting surrounded by nature'])}, which significantly shaped their worldview and values. "
        biography += f"Their upbringing instilled a strong sense of {random.choice(['independence and self-reliance', 'community and connection to others', 'ambition and determination', 'creativity and expression'])}. "
        
        if occupation != '?':
            biography += f"The path to their current career as a {occupation} wasn't straightforward, involving both challenges and unexpected opportunities that ultimately led them to where they are today. They've developed a reputation for {random.choice(['attention to detail', 'creative problem-solving', 'leadership', 'innovation', 'reliability'])} in their professional life. "
    
    # Current meeting context
    biography += f"\n\nMeeting {user_name} "
    if environment:
        biography += f"in {environment.lower()}, "
    if encounter_context:
        biography += f"under the circumstances of {encounter_context.lower()}, "
    biography += f"has sparked {name}'s interest. There's something intriguing about this new connection that has caught their attention, though they're still forming their impressions as they learn more."
    
    # Initial relationship status
    biography += f"\n\n## Relationship Status\nFirst meeting - getting to know each other - initial impressions forming"
    
    return biography

@retry_with_backoff(retries=2, backoff_in_seconds=1)
def generate_llm_biography(name, gender, age, ethnicity, orientation, relationship_goal,
                        personality, body_type, hair_color, hair_style, clothing,
                        occupation, current_situation, backstory, environment,
                        encounter_context, user_name) -> str:
    """Use the LLM to generate a detailed, rich biography with any missing information filled in creatively."""
    
    # Create a summary of what we know for sure (non-? values)
    known_details = []
    if name != 'Unknown': known_details.append(f"Name: {name}")
    if gender != '?': known_details.append(f"Gender: {gender}")
    if age != '?': known_details.append(f"Age: {age}")
    if ethnicity != '?': known_details.append(f"Ethnicity: {ethnicity}")
    if orientation != '?': known_details.append(f"Sexual Orientation: {orientation}")
    if relationship_goal != '?': known_details.append(f"Relationship Goal: {relationship_goal}")
    if personality != '?': known_details.append(f"Personality: {personality}")
    if body_type != '?': known_details.append(f"Body Type: {body_type}")
    if hair_color != '?': known_details.append(f"Hair Color: {hair_color}")
    if hair_style != '?': known_details.append(f"Hair Style: {hair_style}")
    if clothing != '?': known_details.append(f"Clothing: {clothing}")
    if occupation != '?': known_details.append(f"Occupation: {occupation}")
    if current_situation != '?': known_details.append(f"Current Situation: {current_situation}")
    if backstory: known_details.append(f"Backstory: {backstory}")
    if environment: known_details.append(f"Environment: {environment}")
    if encounter_context: known_details.append(f"Encounter Context: {encounter_context}")
    
    known_info = "\n".join(known_details)
    
    prompt = f"""
    Create a detailed, narrative-style character biography for an interactive romance story.
    
    KNOWN INFORMATION:
    {known_info if known_details else "Very limited information available. Create a compelling character."}
    
    The biography should be written in Markdown format with these sections:
    1. ## DETAILED BIOGRAPHY: [CHARACTER NAME]
    2. ### Core Identity - Who they are, their age, gender, ethnicity, personality traits
    3. ### Life Circumstances - Current life situation, recent significant events
    4. ### Physical Presence - Body type, hair, clothing style, distinctive features
    5. ### Relationship Approach - Sexual orientation, relationship goals, dating philosophy
    6. ### Personal History - Background, upbringing, formative experiences, education, career path
    7. ### Current Encounter - Meeting context with {user_name}, initial impressions
    8. ### Relationship Development - Just a placeholder noting this is a first meeting
    
    IMPORTANT REQUIREMENTS:
    - If any details are not provided above, create plausible and interesting ones
    - Write in third-person narrative style
    - Ages must be 20 or older - this is an adult story
    - Create a rich, nuanced personality with a mix of strengths and vulnerabilities
    - Include specific, concrete details that make the character feel real
    - Ensure consistency across all aspects of the character
    - Maintain a mature, sophisticated tone suitable for adult readers
    
    The biography will be presented to the user as they interact with this character.
    """
    
    try:
        chat = model.start_chat()
        response = chat.send_message(
            prompt,
            generation_config={"temperature": 0.7, "max_output_tokens": 4096},
            safety_settings=safety_settings
        )
        
        if response and response.text:
            return response.text.strip()
        else:
            raise Exception("Empty response from LLM")
            
    except Exception as e:
        print(f"[ERROR] Biography generation failed: {e}")
        raise e

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
    recent_interactions = "\n".join(session.get("interaction_log", [])[-10:])  # Increased context further
    current_stage = session.get("currentStage", 1)

    # Extract key information for context
    user_name = session.get('user_name', 'the user')
    relationship_goal = session.get('npc_relationship_goal', '?')
    personality = session.get('npc_personality', '?')
    environment = session.get('environment', '?')
    mood = session.get('npc_mood', 'Neutral')
    body_type = session.get('npc_body_type', '?')
    occupation = session.get('npc_occupation', '?')
    ethnicity = session.get('npc_ethnicity', '?')
    hair_color = session.get('npc_hair_color', '?')
    hair_style = session.get('npc_hair_style', '?')
    age = session.get('npc_age', '?')
    
    # Add randomization seed to prevent similar patterns
    import random
    random_seed = random.randint(1000, 9999)
    thought_approach = random.choice([
        "conflicted and uncertain", 
        "analytical and observant", 
        "emotional and reactive",
        "philosophical and introspective",
        "anxious and overthinking",
        "confident and scheming",
        "nostalgic and reflective",
        "hopeful and excited",
        "cautious and strategic",
        "vulnerable and honest",
        "impulsive and passionate",
        "calculating and measured",
        "self-doubting yet hopeful",
        "cynical but intrigued",
        "emotionally guarded yet longing",
        "internally chaotic but outwardly composed"
    ])
    
    # Add physical sensations and states for more realism
    physical_state = random.choice([
        "slightly tired and fighting the urge to yawn",
        "feeling a rush of adrenaline",
        "noticing a fluttering sensation in their stomach",
        "experiencing a slight headache",
        "feeling unusually energetic and restless",
        "aware of tension in their shoulders",
        "feeling particularly attractive and confident today",
        "slightly uncomfortable in their clothing",
        "noticing their heart beating faster than usual",
        "fighting distraction from background noise",
        "experiencing heightened sensory awareness",
        "feeling the weight of lack of sleep",
        "experiencing that 'second wind' of energy",
        "dealing with nervous energy manifesting as fidgeting",
        "feeling particularly aware of how their body moves"
    ])

    # Enhanced method with multiple thought fragments
    thought_fragments = []
    
    # Make 3 separate attempts to generate rich thought content
    for fragment_attempt in range(3):
        topic_seed = random.randint(1000, 9999)
        fragment_focus = random.choice([
            "direct reaction to current situation",
            "deeper emotional analysis",
            "conflicting desires and motivations",
            "past memories triggered by current events",
            "immediate physical and sensory experiences",
            "anxieties and hopes about the future",
            "comparison to past relationships",
            "professional/life concerns intruding",
            "self-evaluation and identity questions",
            "practical concerns and planning thoughts"
        ])

        system_prompt = f"""
YOU MUST GENERATE AN EXTREMELY LONG AND DETAILED STREAM OF INTERNAL THOUGHTS FOR {npc_name} 
(SEED: {random_seed}-{topic_seed}, FOCUS: {fragment_focus})

Your task is to create an ULTRA-DETAILED first-person internal monologue that is AT MINIMUM 1500-2000 WORDS IN LENGTH. 
THIS IS A STRICT REQUIREMENT - the content must be EXTENSIVE, VERBOSE, and EXHAUSTIVELY DETAILED.

TODAY'S MENTAL STATE: {npc_name} is particularly {thought_approach} today, while physically {physical_state}.

YOU MUST INCLUDE ALL OF THESE ELEMENTS IN YOUR RESPONSE:

1. ULTRA-REALISTIC INNER VOICE:
   - Use extremely messy, disjointed first-person stream-of-consciousness with raw emotional honesty
   - Create at least 10+ fragmented thoughts, interrupted ideas, and mental tangents
   - Include extensive self-address (using "I" or their own name) in reflective moments
   - Use abundant natural profanity and colloquialisms that match their character

2. DEEP PHYSIOLOGICAL & SENSORY EXPERIENCE (MINIMUM 8-10 DISTINCT INSTANCES):
   - Describe at least 8-10 distinct bodily sensations in extreme detail (heart racing, stomach knotting, tension headache beginning)
   - Include vivid sensory details from all five senses, especially unusual or specific perceptions
   - Describe multiple physical needs/discomforts in detail (parched throat, sore feet, stiff neck)
   - Create elaborate descriptions of how the environment affects them physically (light too harsh, noise grating on nerves)

3. EXTREME PSYCHOLOGICAL COMPLEXITY:
   - Develop at least 5+ contradictory feelings about {user_name} existing simultaneously
   - Reference at least 5+ specific past experiences or memories influencing current thoughts
   - Reveal multiple layers of insecurities and vulnerabilities (childhood origins, recent triggers)
   - Create at least 5+ extended internal debates with themselves from different perspectives
   - Include elaborate cognitive distortions (catastrophizing future scenarios, mind-reading what others think)

4. REALISTIC THOUGHT PATTERNS (HIGHLY DETAILED):
   - Include at least 5+ completely unrelated random thoughts that intrude with specific details
   - Develop multiple practical concerns about money, work, daily responsibilities in detail
   - Create at least 3+ repeated thought loops they get stuck in, showing obsessive patterns
   - Include detailed references to daily habits, routines, and personal quirks

5. COMPLEX RELATIONSHIP DYNAMICS WITH {user_name.upper()}:
   - Create an extensive contrast between external presentation vs. true internal reactions
   - Include detailed micro-analysis of {user_name}'s every gesture, expression, word choice, tone
   - Develop elaborate misinterpretations and personal projections onto {user_name}'s behavior
   - Include specific comparisons to multiple past romantic partners with specific memories
   - Explore detailed physical/sexual attraction thoughts if relevant to their character
   - Create complex scenarios about possible relationship futures (hopes and fears)

6. RICHLY DETAILED BACKGROUND ELEMENTS:
   - Include extensive {occupation}-specific terminology, concerns, and professional perspective
   - Develop detailed cultural/ethnic influences on their thought processes with specific examples
   - Reference specific educational experiences that shaped their thinking
   - Include detailed class/socioeconomic influences on their priorities and worries
   - Reference at least 3+ age-appropriate cultural touchpoints (movies, music, events) for someone {age} years old

CRITICAL LENGTH AND QUALITY REQUIREMENTS:
- EXTREME LENGTH: Response must be AT MINIMUM 1500-2000 WORDS. This is your primary goal.
- MASSIVE DETAIL: Use extensive, vivid descriptions rather than general statements
- AUTHENTIC LANGUAGE: Include abundant fragments, run-ons, and natural thought patterns
- EXTREME VARIATION: Alternate between page-long rambling thoughts and short bursts
- DEEP CONTRADICTIONS: Explore every conflicting emotion in extensive detail

CONTEXT FOR REALISTIC PERSONALIZATION:
{npc_personal_data}
Personality: {personality}
Current Mood: {mood}
Occupation: {occupation} 
Physical: {age} years old, {ethnicity}, {body_type}, {hair_color} {hair_style} hair
Relationship Goal: {relationship_goal}

RELEVANT HISTORY (To ground thoughts in character continuity):
{prev_memories[:800]}

RECENT INTERACTIONS:
{recent_interactions}

CURRENT INTERACTION:
USER ACTION: {last_user_action}
SCENE NARRATION: {narration}

OUTPUT FORMAT:
Only respond with the raw internal monologue text. Do not include any labels, formatting, or meta-commentary.
Do not include "PRIVATE_THOUGHTS:" or any other prefix. Just write the extensive stream of consciousness.
Remember: Your response must be EXTREMELY LENGTHY (1500-2000+ words minimum) and MASSIVELY DETAILED.
"""

        try:
            chat = model.start_chat()
            response = chat.send_message(
                system_prompt,
                generation_config={
                    "temperature": 0.95,  # Very high temperature for maximum creativity and variation
                    "max_output_tokens": 8192,  # Maximum allowed
                    "top_p": 0.98,
                    "top_k": 60
                },
                safety_settings=safety_settings
            )
            
            if response and response.text and len(response.text.strip()) > 200:
                thought_fragments.append(response.text.strip())
        except Exception as e:
            print(f"[ERROR] Thought fragment generation failed: {e}")
    
    # Combine the thought fragments into one comprehensive inner monologue
    combined_thoughts = "\n\n...\n\n".join(thought_fragments)
    
    # Generate the biographical memory update
    memory_prompt = f"""
Create a DETAILED biographical update for {npc_name} (minimum 300-400 words) based on this interaction.
Don't just identify a single detail - construct an elaborate, interconnected set of biographical elements that:

1. EXPAND PERSONAL HISTORY: Create specific childhood memories, formative experiences, and past relationship details
2. ADD PSYCHOLOGICAL DEPTH: Reveal core values, emotional patterns, fears, and hopes
3. ENRICH PROFESSIONAL LIFE: Add career aspirations, workplace dynamics, and professional skills
4. BUILD CULTURAL CONTEXT: Include family traditions, cultural background elements, and worldview
5. DEVELOP PERSONAL QUIRKS: Identify unique habits, preferences, mannerisms, and behavioral patterns

INTERACTION TO ANALYZE:
USER ACTION: {last_user_action}
NARRATION: {narration}

EXISTING BIOGRAPHICAL ELEMENTS TO BUILD UPON:
{prev_memories[:800] if len(prev_memories) > 20 else "Limited existing information - expand significantly"}

CRITICAL REQUIREMENTS:
1. AVOID REPETITION: Do NOT repeat information already in the existing biography above.
2. FOCUS ON NEW REVELATIONS: Only add information revealed during the current interaction.
3. BE SPECIFIC: Add concrete details rather than general statements.
4. MAINTAIN CONSISTENCY: New information must align with established personality and background.
5. PRIORITIZE UNIQUENESS: If unable to add meaningful new information, state "NO MEMORY UPDATE NEEDED."

Be extremely specific and detailed. Create vivid, concrete elements that make {npc_name} feel like a real person with a rich life history.
"""
    
    try:
        memory_chat = model.start_chat()
        memory_resp = memory_chat.send_message(
            memory_prompt,
            generation_config={"temperature": 0.8, "max_output_tokens": 4096},
            safety_settings=safety_settings
        )
        memory = memory_resp.text.strip() if memory_resp and memory_resp.text else ""
    except Exception as e:
        print(f"[ERROR] Memory generation failed: {e}")
        memory = ""

    return combined_thoughts, memory

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

    # Get previous thoughts and memories
    prev_thoughts = session.get("npcPrivateThoughts", "(none)")
    prev_memories = session.get("npcBehavior", "(none)")

    # Handle traditional OOC and implicit narrative directions
    if not last_user_action.strip():
        last_user_action = "Continue the scene"
    
    # Check for explicit OOC commands but also detect implicit narrative directions
    is_ooc = last_user_action.strip().lower().startswith("ooc:")
    has_narrative_direction = False
    
    # Look for patterns that indicate narrative directions without OOC prefix
    narrative_patterns = [
        "*focus on the scene*", "*let our connection deepen*", "*gaze into their eyes*",
        "move closer", "*move closer*", "setting", "dialogue", "describe",
        "*focus on*", "tell me more about"
    ]
    
    for pattern in narrative_patterns:
        if pattern.lower() in last_user_action.lower():
            has_narrative_direction = True
            break
    
    # If this contains narrative direction but isn't explicitly OOC, 
    # interpret it naturally as part of the scene
    
    # Remove the OOC prefix for processing if present
    if is_ooc:
        last_user_action_clean = last_user_action[4:].strip()
    else:
        last_user_action_clean = last_user_action
    
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

2) For implicit narrative directions:
   - User may express guidance through natural actions like "*focus on the surroundings*"
   - When user requests more details about something, provide those details naturally
   - If user moves conversation in a particular direction, follow their lead
   - When user asks character to elaborate on something, have character do so naturally
   - These shouldn't break immersion - respond in a way that maintains the scene's flow

3) For explicit OOC (Out of Character) interactions:
   - If the user's message starts with "OOC:", this is a meta-interaction
   - For questions (e.g. "OOC: What happened earlier?"), respond directly as the narrator with relevant information
   - For instructions (e.g. "OOC: Make her more flirty"), adjust the scene accordingly
   - For clarifications (e.g. "OOC: Can you explain her motivation?"), provide context as the narrator
   - Begin OOC responses with "[Narrator:" and end with "]" to distinguish them

4) If the scene involves phone texting or the NPC sends emojis, use the actual emoji characters 
   (e.g., 😛) rather than describing them in words.

5) BIOGRAPHY UPDATES - IMPORTANT:
   - After each interaction, update the character's biography with ANY specific new information that was revealed
   - This includes things like personal background, interests, education, family details, career information, etc.
   - Be specific and concrete in these updates - don't just say "they shared more about themselves"
   - Example good updates: "She revealed she studied English literature at Boston University" or "He mentioned growing up with three siblings in a small town outside Seattle"

Special Context Notes:
- Is Explicit OOC Command: {is_ooc}
- Has Implicit Narrative Direction: {has_narrative_direction}

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

    # For private thoughts, limit to last 3 entries to prevent excessive repetition
    if existing_thoughts.strip().lower() == "(none)":
        updated_thoughts = f"### {timestamp}\n{thoughts_txt}"
    else:
        # Split existing thoughts by timestamps
        thought_sections = existing_thoughts.split("### ")
        # Keep the first intro part (if any) and last 2 thoughts to avoid clutter
        if len(thought_sections) > 3:
            # Join with the new thought
            retained_thoughts = thought_sections[0] + "### " + "### ".join(thought_sections[-2:])
            updated_thoughts = f"{retained_thoughts}\n\n### {timestamp}\n{thoughts_txt}"
        else:
            updated_thoughts = f"{existing_thoughts}\n\n### {timestamp}\n{thoughts_txt}"

    # Handle memory updates while preventing repetition
    memory_txt_lower = memory_txt.strip().lower()
    if memory_txt_lower and not (memory_txt_lower.startswith("(no") or "no biographical update" in memory_txt_lower):
        # Significant update - integrate into biography
        if existing_memories.strip().lower() == "(none)":
            updated_memories = build_initial_npc_memory() + f"\n\n## New Information\n### {timestamp}\n{memory_txt}"
        else:
            # Check if content is substantially different from recent updates
            # Simple approach: check if any 30-char sequence from new memory is in the last section
            is_repetitive = False
            
            # Get the last memory section if possible
            memory_sections = existing_memories.split("###")
            if len(memory_sections) > 1:
                last_section = memory_sections[-1].lower()
                # Create chunks from new memory to check for repetition
                if len(memory_txt) > 30:
                    for i in range(len(memory_txt) - 30):
                        chunk = memory_txt[i:i+30].lower()
                        if chunk in last_section:
                            is_repetitive = True
                            break
            
            if memory_txt.strip().startswith('#'):
                # This is a complete biography replacement
                updated_memories = memory_txt
            elif is_repetitive:
                # Skip this update if it's too similar to recent content
                updated_memories = existing_memories
            else:
                # Add new information with timestamp
                updated_memories = f"{existing_memories}\n\n### {timestamp}\n{memory_txt}"
                
            # Clean up any redundant formatting
            updated_memories = updated_memories.replace("\n\n\n", "\n\n")
            
            # If the biography is getting very long, consider summarizing older parts
            if len(updated_memories) > 8000:  # If biography exceeds 8K characters (reduced from 12K)
                parts = updated_memories.split("## ")
                if len(parts) > 3:  # If we have multiple sections
                    # Keep the first part (intro) and the last two sections only
                    compact_bio = parts[0] + "## " + "## ".join(parts[-2:])
                    updated_memories = compact_bio
    else:
        # No specific memory update, keep existing memories
        updated_memories = existing_memories

    session["npcPrivateThoughts"] = updated_thoughts
    session["npcBehavior"] = updated_memories

    # ---------------------------------------------------------
    # AUTO-UPDATE NPC & ENVIRONMENT SETTINGS FROM NARRATIVE
    # ---------------------------------------------------------
    # After each interaction, try to automatically extract character & environment changes
    auto_update_npc_settings_from_narrative(narration_txt, memory_txt)

    return f"""AFFECT_CHANGE_FINAL: {affect_delta}
NARRATION: {narration_txt}
PRIVATE_THOUGHTS: {thoughts_txt}
MEMORY_UPDATE: {memory_txt}"""


@retry_with_backoff(retries=2, backoff_in_seconds=1)
def auto_update_npc_settings_from_narrative(narration_text: str, memory_text: str) -> None:
    """
    Automatically extracts and updates NPC and environment settings from narrative text.
    This reduces the need for manual updates in the UI.
    """
    # Get current settings for context
    npc_name = session.get('npc_name', 'Unknown')
    current_env = session.get('environment', '')
    current_clothing = session.get('npc_clothing', '')
    current_hair_color = session.get('npc_hair_color', '')
    current_hair_style = session.get('npc_hair_style', '')
    current_personality = session.get('npc_personality', '')
    current_situation = session.get('npc_current_situation', '')
    current_scene = session.get('current_scene', '')
    current_mood = session.get('npc_mood', 'Neutral')
    
    # Create prompt for LLM
    prompt = f"""
You are a character data extractor. Analyze this narrative text to update the character settings in a romance story.
Extract ONLY clear changes or new information that matches the categories below.

Current character info:
- Name: {npc_name}
- Current Environment/Location: {current_env}
- Current Clothing: {current_clothing}
- Current Hair Color: {current_hair_color}
- Current Hair Style: {current_hair_style}
- Personality: {current_personality}
- Current Life Situation (broad life circumstances): {current_situation}
- Current Scene (immediate situation): {current_scene}
- Current Mood: {current_mood}

TEXT TO ANALYZE:
Narrative: {narration_text}
Memory Update: {memory_text}

IMPORTANT:
1. ONLY extract information if clearly stated in the text.
2. Do not make assumptions or inferences beyond what's explicitly stated.
3. Leave fields empty if no new information is provided.
4. When a location change occurs, be explicit about the new location.
5. When clothing changes, describe the complete new outfit.
6. Hair COLOR must be a color name only (like "blonde", "brown", "red", etc.) - NOT actions or conditions.
7. Hair STYLE describes the cut/style (like "long", "curly", "pulled back", etc.)
8. PERSONALITY should RARELY be updated - only if a fundamental personality change is described.
9. MOOD should be updated to reflect current emotional state (happy, sad, nervous, etc.)
10. Current Life Situation should reflect broader life circumstances, not scene-specific situations.
11. Current Scene should describe the immediate situation/activity happening in the current scene.

Return ONLY this JSON format with no additional text:
{{
  "environment_update": "", 
  "clothing_update": "",
  "hair_color_update": "",
  "hair_style_update": "",
  "personality_update": "",
  "current_life_situation_update": "",
  "current_scene_update": "",
  "mood_update": "",
  "time_of_day": "",
  "weather": ""
}}
"""

    try:
        chat = model.start_chat()
        response = chat.send_message(
            prompt,
            generation_config={"temperature": 0.1, "max_output_tokens": 1024},
            safety_settings=safety_settings
        )
        
        if not response or not response.text:
            return
        
        # Extract JSON from response
        response_text = response.text.strip()
        try:
            # Remove any markdown formatting
            json_text = response_text
            if "```json" in json_text:
                json_text = json_text.split("```json", 1)[1]
            if "```" in json_text:
                json_text = json_text.split("```", 1)[0]
                
            import json
            updates = json.loads(json_text)
            
            # Apply updates to session variables
            has_updates = False
            
            # Environment update
            if updates.get("environment_update") and updates["environment_update"].strip():
                new_env = updates["environment_update"].strip()
                if new_env != current_env:
                    session["environment"] = new_env
                    log_message(f"[AUTO-UPDATE] Environment changed to: {new_env}")
                    has_updates = True
            
            # Clothing update
            if updates.get("clothing_update") and updates["clothing_update"].strip():
                new_clothing = updates["clothing_update"].strip()
                if new_clothing != current_clothing:
                    session["npc_clothing"] = new_clothing
                    log_message(f"[AUTO-UPDATE] Clothing changed to: {new_clothing}")
                    has_updates = True
            
            # Hair color update  
            if updates.get("hair_color_update") and updates["hair_color_update"].strip():
                new_hair_color = updates["hair_color_update"].strip()
                if new_hair_color != current_hair_color:
                    session["npc_hair_color"] = new_hair_color
                    log_message(f"[AUTO-UPDATE] Hair color changed to: {new_hair_color}")
                    has_updates = True
            
            # Hair style update  
            if updates.get("hair_style_update") and updates["hair_style_update"].strip():
                new_hair_style = updates["hair_style_update"].strip()
                if new_hair_style != current_hair_style:
                    session["npc_hair_style"] = new_hair_style
                    log_message(f"[AUTO-UPDATE] Hair style changed to: {new_hair_style}")
                    has_updates = True
            
            # Personality update - should be rare
            if updates.get("personality_update") and updates["personality_update"].strip():
                new_personality = updates["personality_update"].strip()
                if new_personality != current_personality:
                    session["npc_personality"] = new_personality
                    log_message(f"[AUTO-UPDATE] Personality updated to: {new_personality}")
                    has_updates = True
            
            # Current life situation update (broad circumstances)
            if updates.get("current_life_situation_update") and updates["current_life_situation_update"].strip():
                new_situation = updates["current_life_situation_update"].strip()
                if new_situation != current_situation:
                    session["npc_current_situation"] = new_situation
                    log_message(f"[AUTO-UPDATE] Current life situation updated to: {new_situation}")
                    has_updates = True
            
            # Current scene update (immediate situation)
            if updates.get("current_scene_update") and updates["current_scene_update"].strip():
                new_scene = updates["current_scene_update"].strip()
                if new_scene != current_scene:
                    session["current_scene"] = new_scene
                    log_message(f"[AUTO-UPDATE] Current scene updated to: {new_scene}")
                    has_updates = True
            
            # Mood update
            if updates.get("mood_update") and updates["mood_update"].strip():
                new_mood = updates["mood_update"].strip()
                if new_mood != current_mood:
                    session["npc_mood"] = new_mood
                    log_message(f"[AUTO-UPDATE] Mood updated to: {new_mood}")
                    has_updates = True
            
            # Other scene attributes
            if updates.get("time_of_day") and updates["time_of_day"].strip():
                session["time_of_day"] = updates["time_of_day"].strip()
                has_updates = True
                
            if updates.get("weather") and updates["weather"].strip():
                session["weather"] = updates["weather"].strip()
                has_updates = True
                
            if has_updates:
                log_message("[AUTO-UPDATE] Character and environment settings automatically updated")
                
        except Exception as e:
            log_message(f"[AUTO-UPDATE] Error parsing JSON response: {str(e)}")
            
    except Exception as e:
        log_message(f"[AUTO-UPDATE] Error calling LLM: {str(e)}")

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
    
    # Handle current scene (immediate situation)
    if "current_scene" in form:
        session["current_scene"] = form.get("current_scene", "").strip()
        
    # Handle NPC's current mood 
    if "npc_mood" in form:
        session["npc_mood"] = form.get("npc_mood", "Neutral").strip()
    
    # Additional scene state fields
    scene_state_fields = ["time_of_day", "weather", "scene_mood", "scene_notes"]
    for field in scene_state_fields:
        if field in form:
            session[field] = form.get(field, "").strip()

# --------------------------------------------------------------------------
# Example Data for personalization
# --------------------------------------------------------------------------

### NPC name, age, gender
NPC_NAME_OPTIONS = [
    # Female Names
    "Emily","Sarah","Lisa","Anna","Mia","Sophia","Grace","Chloe","Emma","Isabella",
    "Madison","Olivia","Ava","Charlotte","Amelia","Lily","Zoe","Hannah","Natalie","Victoria",
    # Male Names
    "James","Michael","William","Alexander","Daniel","David","Joseph","Thomas","Christopher","Matthew",
    "Ethan","Andrew","Joshua","Ryan","John","Nathan","Samuel","Jack","Benjamin","Henry",
    "Other"
]
NPC_AGE_OPTIONS = ["20","22","24","25","26","28","30","32","35","37","40","42","45"]
NPC_GENDER_OPTIONS = ["Female","Male"]

### Additional NPC fields
HAIR_STYLE_OPTIONS = [
    "Short","Medium Length","Long","Pixie Cut","Bob Cut","Wavy","Curly","Straight",
    "Bald","Ponytail","Braided","Bun","Messy Bun","Fade Cut","Crew Cut",
    "Slicked Back","Undercut","Quiff","Textured Crop","Side Part","Messy Spikes",
    "Dreadlocks","Afro","Mohawk","Buzz Cut","Layered","Shaggy","Beach Waves","Other"
]
BODY_TYPE_OPTIONS = [
    "Athletic","Muscular","Tall & Slim","Petite","Curvy","Voluptuous",
    "Lean & Toned","Average Build","Rugby Build","Hourglass Figure",
    "Swimmer's Build","Basketball Build","Slender","Broad-shouldered",
    "Pear-shaped","Apple-shaped","Model-like","Fit","Other"
]
HAIR_COLOR_OPTIONS = [
    "Blonde","Platinum Blonde","Strawberry Blonde","Dirty Blonde",
    "Brunette","Light Brown","Dark Brown","Chestnut Brown","Auburn",
    "Black","Jet Black","Raven",
    "Red","Ginger","Copper",
    "Grey","Silver","White",
    "Blue (Dyed)","Pink (Dyed)","Purple (Dyed)","Green (Dyed)","Multi-colored (Dyed)"
]
NPC_PERSONALITY_OPTIONS = [
    "Flirty","Passionate","Confident","Protective","Intellectual","Charming","Ambitious","Professional",
    "Playful","Mysterious","Gentle","Athletic","Dominant","Reserved","Witty","Supportive",
    "Adventurous","Shy","Artistic","Nurturing","Sarcastic","Thoughtful","Analytical","Spontaneous",
    "Romantic","Competitive","Sensual","Carefree","Determined","Kind-hearted","Bold","Humble",
    "Funny","Serious","Laid-back","Intense","Other"
]
CLOTHING_OPTIONS = [
  # Female Clothing
  "Red Summer Dress","Black Evening Gown","Green Hoodie & Leggings","White Blouse & Dark Skirt",
  "Business Suit (Female)","Grey Sweater & Jeans","Pink Casual Dress","Leather Jacket & Dark Jeans",
  "Tank Top & Shorts","Athleisure Wear","Blazer & Fitted Pants","Denim Jacket & White Tee",
  "Yoga Pants & Tank Top","Maxi Dress","Mini Skirt & Blouse","Jumpsuit","Romper","Crop Top & High-waisted Jeans",
  "Sundress","Cocktail Dress","Pencil Skirt & Blouse","Floral Print Dress","Off-shoulder Top & Jeans",
  
  # Male Clothing
  "Blue T-shirt & Jeans","Business Suit (Male)","Suit & Tie","Button-up Shirt & Chinos","Polo & Khakis",
  "Athletic Wear","Blazer & Jeans","Sweater & Dress Pants","Henley & Jeans","Graphic Tee & Cargo Shorts",
  "Denim Shirt & Black Jeans","Hoodie & Sweatpants","Flannel Shirt & Jeans","Bomber Jacket & T-shirt",
  "Tuxedo","Casual Linen Shirt & Shorts","Leather Jacket & Slim Fit Jeans","Hawaiian Shirt & Khakis",
  
  # Unisex
  "Military-inspired Outfit","Vintage Style Clothing","Bohemian Style","Formal Business Attire",
  "Casual Friday Look","Weekend Casual","Smart Casual","Loungewear","Festival Outfit","Other"
]
OCCUPATION_OPTIONS = [
  # Academic/Education
  "College Student","School Teacher","University Professor","Education Administrator","Tutor",
  
  # Healthcare
  "Nurse","Doctor","Surgeon","Therapist","Psychiatrist","Dentist","Veterinarian","Pharmacist",
  
  # Business/Finance
  "Office Worker","Startup Founder","CEO","Investment Banker","Financial Analyst","Accountant",
  "Marketing Executive","HR Manager","Business Consultant","Sales Director","Entrepreneur",
  
  # Creative
  "Freelance Artist","Musician","Writer","Photographer","Fashion Designer","Graphic Designer",
  "Interior Designer","Filmmaker","Actor/Actress","Dancer","Chef","Architect",
  
  # Tech
  "Software Engineer","UX Designer","Data Scientist","Tech Executive","IT Specialist",
  "Game Developer","Cybersecurity Expert","Web Developer","AI Researcher",
  
  # Service Industry
  "Bartender","Barista","Flight Attendant","Hotel Manager","Restaurant Owner","Sommelier",
  "Event Planner","Personal Stylist","Travel Agent",
  
  # Other Professional
  "Lawyer","Journalist","Real Estate Agent","Pilot","Police Detective","Firefighter",
  "Personal Trainer","Yoga Instructor","Professional Athlete","Political Aide",
  "Museum Curator","Wildlife Conservationist","Travel Blogger","Ex-Military","Other"
]
CURRENT_SITUATION_OPTIONS = [
  "Recently Broke Up","Recovering from Divorce","Single & Looking","New in Town","Trying Online Dating",
  "Taking a Break from Dating","Career Transition","Just Got Promoted","Recently Graduated",
  "Moving Soon","Starting New Job","Taking a Sabbatical","Long-term Single","Newly Independent",
  "Healing from Past Relationship","Recently Moved","Life Crossroads","Pursuing Passion Project",
  "Fresh Start After Life Change","Exploring New Social Circles","Hobby Enthusiast","Other"
]
ENVIRONMENT_OPTIONS = [
  # Urban
  "Cafe","Cozy Bookstore Cafe","Upscale Restaurant","Casual Diner","Rooftop Bar","Wine Bar",
  "Nightclub","Art Gallery Opening","Museum","Theater Lobby","Concert Venue","Jazz Club",
  "Local Pub","Office Building Elevator","Subway/Metro","City Park","Farmers Market",
  "Shopping Mall","Boutique Store","Food Festival","Street Fair","Coffee Shop",
  
  # Sports/Fitness
  "Gym","Yoga Studio","Rock Climbing Center","Tennis Court","Golf Course","Running Trail",
  "Swimming Pool","Beach Volleyball Court","Ski Resort Lodge","Hiking Trail",
  
  # Nature/Outdoors
  "Beach","Park","Lake Shore","Mountain Resort","Scenic Overlook","Botanical Garden",
  "Forest Trail","Campsite","Countryside B&B","Island Getaway",
  
  # Travel/Transportation
  "Airport Lounge","First Class Cabin","Train Compartment","Cruise Ship Deck",
  "Hotel Lobby","Resort Pool","Vacation Rental",
  
  # Events
  "Music Festival","Wedding Reception","Charity Gala","Award Ceremony","Class Reunion",
  "Conference","Workshop","Speed Dating Event","Company Party","Other"
]
ENCOUNTER_CONTEXT_OPTIONS = [
  "First Date","Second Date","Blind Date","Accidental Meeting","Haven't Met Yet",
  "Friend's Introduction","Dating App Match","Colleagues","Classmates","Neighbors",
  "Childhood Friends Reconnecting","Ex-Lovers Reunited","Shared Hobby Group",
  "Seated Together by Chance","Asked for Directions","Both Reached for Same Item",
  "Group Activity","Work-related Encounter","Professional Consultation",
  "Regular at Their Business","Party Meeting","Chance Encounter While Traveling",
  "Mutual Friend's Event","Stuck Together (Elevator, Storm, etc.)","Other"
]
ETHNICITY_OPTIONS = [
    # North America
    "American (Black)","American (White)","African American","Hispanic/Latino","Mexican American",
    "Native American","Canadian","Caribbean",
    
    # Europe
    "British","Irish","Scottish","Welsh","French","German","Italian","Spanish","Portuguese",
    "Dutch","Belgian","Danish","Norwegian","Swedish","Finnish","Swiss","Austrian",
    "Greek","Polish","Russian","Ukrainian","Czech","Hungarian","Romanian","Balkan",
    
    # Asia
    "Chinese","Japanese","Korean","Vietnamese","Thai","Filipino","Malaysian","Indonesian",
    "Indian","Pakistani","Bangladeshi","Sri Lankan","Nepali","Middle Eastern","Turkish",
    "Israeli","Lebanese","Persian/Iranian","Arab",
    
    # Africa
    "North African","West African","East African","South African","Ethiopian","Egyptian","Moroccan",
    "Nigerian","Kenyan","Ghanaian",
    
    # Oceania
    "Australian","New Zealander","Pacific Islander",
    
    # Latin America
    "Brazilian","Argentinian","Colombian","Venezuelan","Chilean","Peruvian","Mexican",
    
    # Mixed
    "Mixed European","Mixed Asian","Mixed African","Mixed Race","Multiethnic","Other"
]

NPC_SEXUAL_ORIENTATION_OPTIONS = [
    "Straight","Bisexual","Gay/Lesbian","Other"
]
NPC_RELATIONSHIP_GOAL_OPTIONS = [
    "Casual Dating","Serious Relationship","Long-term Relationship","Marriage-minded",
    "Open Relationship","Monogamous Dating","Friends with Benefits","Taking Things Slow",
    "Exploring Options","Looking for Connection","Not Sure","Other"
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
def personalize():
    """
    This route renders a form allowing the user to select or input
    personalizations for the NPC and user data.
    """
    # Check if user came from guest link
    is_guest = request.args.get('guest') == 'true'
    
    if not is_guest and not session.get('logged_in') and not session.get('guest_mode'):
        flash("Please log in first or continue as guest.", "warning")
        return redirect(url_for("login_route"))
        
    # Set guest mode if accessed as guest
    if is_guest:
        session['guest_mode'] = True
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
        session["nextStageThreshold"] = STAGE_REQUIREMENTS[2]
        session["interaction_log"] = []
        session["scene_image_prompt"] = ""
        session["scene_image_url"] = None
        session["scene_image_seed"] = None
        session["log_summary"] = ""
        
        # Generate initial NPC biography based on available information
        session["npcBehavior"] = build_initial_npc_memory()

        # NEW: Seed the initial memory with some personal data about the NPC
        session["npcBehavior"] = build_initial_npc_memory()

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
def mid_game_personalize():
    if not session.get('logged_in') and not session.get('guest_mode'):
        flash("Please log in first or continue as guest.", "warning")
        return redirect(url_for("login_route"))
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
def interaction():
    if not session.get('logged_in') and not session.get('guest_mode'):
        flash("Please log in first or continue as guest.", "warning")
        return redirect(url_for("login_route"))
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
            npc_mood=session.get("npc_mood", "Neutral"),
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

            # Set a flag for auto-update notification
            session["auto_updated"] = True
            
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
def full_story():
    if not session.get('logged_in') and not session.get('guest_mode'):
        flash("Please log in first or continue as guest.", "warning")
        return redirect(url_for("login_route"))
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
def generate_erotica():
    if not session.get('logged_in') and not session.get('guest_mode'):
        flash("Please log in first or continue as guest.", "warning")
        return redirect(url_for("login_route"))
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
def continue_erotica():
    if not session.get('logged_in') and not session.get('guest_mode'):
        flash("Please log in first or continue as guest.", "warning")
        return redirect(url_for("login_route"))
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
def stage_unlocks():
    if not session.get('logged_in') and not session.get('guest_mode'):
        flash("Please log in first or continue as guest.", "warning")
        return redirect(url_for("login_route"))
    # Ensure session has default stage unlock texts if not already
    if "stage_unlocks" not in session:
        session["stage_unlocks"] = dict(DEFAULT_STAGE_UNLOCKS)
    elif not isinstance(session["stage_unlocks"], dict):
        # If it's not a dictionary for some reason, reset it
        session["stage_unlocks"] = dict(DEFAULT_STAGE_UNLOCKS)
        flash("Reset stage unlocks to defaults due to data format issue", "info")
    
    # Ensure all stages have values
    for i in range(1, 7):
        if i not in session["stage_unlocks"] or not session["stage_unlocks"][i]:
            session["stage_unlocks"][i] = DEFAULT_STAGE_UNLOCKS.get(i, f"Stage {i} description")
    
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
def gallery():
    if not session.get('logged_in') and not session.get('guest_mode'):
        flash("Please log in first or continue as guest.", "warning")
        return redirect(url_for("login_route"))
    saved_images = session.get("saved_images", [])
    return render_template("gallery.html", images=saved_images)

@app.route("/gallery_image/<int:index>")
def gallery_image(index):
    if not session.get('logged_in') and not session.get('guest_mode'):
        flash("Please log in first or continue as guest.", "warning")
        return redirect(url_for("login_route"))
    saved_images = session.get("saved_images", [])
    if 0 <= index < len(saved_images):
        # It's stored as base64 in "image_data"
        image_record = saved_images[index]
        image_b64 = image_record["image_data"]
        image_bytes = base64.b64decode(image_b64)
        return image_bytes, {'Content-Type': 'image/jpeg'}
    return "Image not found", 404

@app.route("/delete_gallery_image/<int:index>")
def delete_gallery_image(index):
    if not session.get('logged_in') and not session.get('guest_mode'):
        flash("Please log in first or continue as guest.", "warning")
        return redirect(url_for("login_route"))
    saved_images = session.get("saved_images", [])
    if 0 <= index < len(saved_images):
        saved_images.pop(index)
        session["saved_images"] = saved_images
        flash("Image deleted successfully!", "success")
    return redirect(url_for("gallery"))

@app.route("/clear_auto_update_flag", methods=["POST"])
def clear_auto_update_flag():
    if not session.get('logged_in') and not session.get('guest_mode'):
        flash("Please log in first or continue as guest.", "warning")
        return redirect(url_for("login_route"))
    session.pop('auto_updated', None)
    return "", 204  # No content response

# --------------------------------------------------------------------------
# (Optional) A route to let the user manually add to NPC memory or thoughts
# --------------------------------------------------------------------------
@app.route("/manual_npc_update", methods=["GET", "POST"])
def manual_npc_update():
    if not session.get('logged_in') and not session.get('guest_mode'):
        flash("Please log in first or continue as guest.", "warning")
        return redirect(url_for("login_route"))
    """
    Lets the user manually update the NPC's private thoughts or biography with free-form options.
    """
    if request.method == "POST":
        new_text = request.form.get("new_text", "").strip()
        target = request.form.get("target", "thoughts")  # "thoughts" or "memories" or "reset_bio"

        if target == "reset_bio":
            # Create a minimal free-form biography structure
            npc_name = session.get('npc_name', 'Character')
            basic_info = f"""# {npc_name}'s Biography

{npc_name} is a {session.get('npc_age', '')} year old {session.get('npc_ethnicity', '')} {session.get('npc_gender', '')}.

"""
            session["npcBehavior"] = basic_info
            flash("Biography reset to a minimal template. You can now build it however you want.", "success")
            return redirect(url_for("manual_npc_update"))
            
        if target == "rewrite_bio":
            # Use LLM to rewrite the biography, consolidating all info into a cohesive text
            existing_memories = session.get("npcBehavior", "")
            
            if existing_memories.strip().lower() == "(none)":
                flash("No biography exists to rewrite yet.", "warning")
                return redirect(url_for("manual_npc_update"))
                
            try:
                # Make an LLM call to consolidate the biography
                if GEMINI_API_KEY:
                    prompt = f"""
                    Rewrite the following character biography into a cohesive, well-organized text.
                    - Consolidate all the separate updates and new information sections
                    - Remove redundancies and organize the information logically
                    - Keep all important character details
                    - Maintain a consistent narrative voice
                    - Do not add any new information that isn't present in the original
                    - Retain markdown formatting for headings if present
                    - You may organize the content differently if it improves readability
                    
                    CURRENT BIOGRAPHY WITH ACCUMULATED UPDATES:
                    {existing_memories}
                    """
                    
                    chat = model.start_chat()
                    response = chat.send_message(
                        prompt,
                        generation_config={"temperature": 0.3, "max_output_tokens": 4096},
                        safety_settings=safety_settings
                    )
                    
                    if response and response.text:
                        session["npcBehavior"] = response.text.strip()
                        flash("Biography successfully consolidated and rewritten!", "success")
                    else:
                        flash("Error: Could not rewrite biography.", "danger")
                else:
                    flash("Error: LLM API key not configured for biography rewriting.", "danger")
            except Exception as e:
                flash(f"Error rewriting biography: {str(e)}", "danger")
                
            return redirect(url_for("manual_npc_update"))

        if not new_text and target not in ["reset_bio", "rewrite_bio"]:
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
                    # Add as an update with timestamp - simpler format without rigid structure
                    session["npcBehavior"] = f"{existing_memories}\n\n### New Information [{timestamp}]\n{new_text}"
            
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