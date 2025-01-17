import os
import replicate
import requests
import openai

from flask import Flask, request, render_template_string, send_file

app = Flask(__name__)

# ========== 1) SET CREDENTIALS & GLOBALS ==========
# Replicate API token stored as a Replit secret
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
replicate.client.api_token = REPLICATE_API_TOKEN

# OpenAI API key stored as a Replit secret
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Where we'll store the downloaded image
GENERATED_IMAGE_PATH = "output.jpg"

# ========== 2) HTML TEMPLATE WITH TWO STEPS ==========
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
  <head>
    <title>Meta-Prompt Image Generator</title>
  </head>
  <body>
    <h1>Meta-Prompt Image Generator (Flux + GPT-4o-mini)</h1>

    <!-- Step 1: Gather user attributes to build an image prompt with GPT-4o-mini -->
    <form method="POST">
      <h2>Step 1: Describe Your Scene</h2>
      <label for="age">Age:</label>
      <input type="text" id="age" name="age" value="{{ age or '' }}"><br>

      <label for="gender">Gender:</label>
      <input type="text" id="gender" name="gender" value="{{ gender or '' }}"><br>

      <label for="ethnicity">Ethnicity:</label>
      <input type="text" id="ethnicity" name="ethnicity" value="{{ ethnicity or '' }}"><br>

      <label for="body_build">Body Build:</label>
      <input type="text" id="body_build" name="body_build" value="{{ body_build or '' }}"><br>

      <label for="outfit">Outfit / Style:</label>
      <input type="text" id="outfit" name="outfit" value="{{ outfit or '' }}"><br>

      <label for="background">Background / Activity:</label>
      <input type="text" id="background" name="background" value="{{ background or '' }}"><br><br>

      <button type="submit" name="generate_prompt" value="true">Generate Prompt</button>
    </form>

    <!-- Step 2: Show recommended prompt, let user edit and generate the final image -->
    {% if recommended_prompt %}
      <hr>
      <h2>Step 2: Review / Edit Prompt</h2>
      <form method="POST">
        <label for="final_prompt">LLM-Generated Prompt:</label><br>
        <textarea id="final_prompt" name="final_prompt" rows="5" cols="60">{{ recommended_prompt }}</textarea><br><br>

        <!-- carry the user attribute fields forward in hidden fields if needed -->
        <input type="hidden" name="age" value="{{ age }}">
        <input type="hidden" name="gender" value="{{ gender }}">
        <input type="hidden" name="ethnicity" value="{{ ethnicity }}">
        <input type="hidden" name="body_build" value="{{ body_build }}">
        <input type="hidden" name="outfit" value="{{ outfit }}">
        <input type="hidden" name="background" value="{{ background }}">

        <!-- Optional extra model settings -->
        <label for="aspect_ratio">Aspect Ratio:</label>
        <select id="aspect_ratio" name="aspect_ratio">
          <option value="1:1" selected>1:1</option>
          <option value="16:9">16:9</option>
          <option value="9:16">9:16</option>
        </select>
        <br><br>

        <button type="submit" name="generate_image" value="true">Generate Image</button>
      </form>
    {% endif %}

    {% if image_generated %}
      <hr>
      <h2>Generated Image</h2>
      <img src="/view_image" alt="Generated Image" style="max-width: 70%;">
    {% endif %}
  </body>
</html>
"""

# ========== 3) HELPER: CALL GPT-4o-mini ==========
def call_llm(age, gender, ethnicity, body_build, outfit, background):
    """
    Calls GPT-4o-mini to create a descriptive prompt from user attributes.
    """
    system_prompt = "You are a helpful AI that creates descriptive image prompts from user attributes."
    user_content = f"""
The user wants an image with these attributes:
- Age: {age}
- Gender: {gender}
- Ethnicity: {ethnicity}
- Body Build: {body_build}
- Outfit/Style: {outfit}
- Background/Activity: {background}

Please return a single text prompt describing an image suitable for an AI image generator.
Keep it short and succinct, but descriptive.
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # <--- using GPT-4o-mini
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
    )
    return response["choices"][0]["message"]["content"].strip()

# ========== 4) FLASK ROUTE ==========
@app.route("/", methods=["GET", "POST"])
def meta_prompt_generator():
    image_generated = False
    recommended_prompt = None

    # Retrieve user attributes (if any)
    age = request.form.get("age", "")
    gender = request.form.get("gender", "")
    ethnicity = request.form.get("ethnicity", "")
    body_build = request.form.get("body_build", "")
    outfit = request.form.get("outfit", "")
    background = request.form.get("background", "")

    # Step 1: Generate recommended prompt from GPT-4o-mini
    if request.method == "POST" and "generate_prompt" in request.form:
        recommended_prompt = call_llm(age, gender, ethnicity, body_build, outfit, background)

    # Step 2: User finalizes prompt and we generate the image using replicate
    if request.method == "POST" and "generate_image" in request.form:
        final_prompt = request.form.get("final_prompt", "")
        aspect_ratio = request.form.get("aspect_ratio", "1:1")

        # Construct replicate input
        replicate_input = {
            "prompt": final_prompt,
            "aspect_ratio": aspect_ratio,
        }

        # Call the black-forest-labs/flux-1.1-pro-ultra model
        output_url = replicate.run(
            "black-forest-labs/flux-1.1-pro-ultra",
            input=replicate_input
        )

        # Download the generated image to output.jpg
        r = requests.get(output_url)
        with open(GENERATED_IMAGE_PATH, "wb") as f:
            f.write(r.content)

        image_generated = True
        recommended_prompt = final_prompt  # So we can still see it in the text field if you want

    # Render the template with the relevant variables
    return render_template_string(
        HTML_TEMPLATE,
        recommended_prompt=recommended_prompt,
        image_generated=image_generated,
        age=age,
        gender=gender,
        ethnicity=ethnicity,
        body_build=body_build,
        outfit=outfit,
        background=background,
    )

# A simple route to serve the generated image
@app.route("/view_image")
def view_image():
    return send_file(GENERATED_IMAGE_PATH, mimetype="image/jpeg")

# For Replit, run on 0.0.0.0:8080
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)