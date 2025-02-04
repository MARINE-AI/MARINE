import os
import subprocess
import json
import tempfile
from flask import Flask, request, jsonify
import google.generativeai as genai

# Suppress gRPC logging messages (set before any library is imported)
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GRPC_TRACE"] = ""

# Configure the API key (Ensure you have set up your Google AI credentials)
genai.configure(api_key="AIzaSyDhgn_kEp1gHyizJvmGlMWOGnq56aAhGjU")

app = Flask(__name__)

def extract_keyframes(video_path: str, output_dir: str, frame_interval: int = 30) -> list:
    """
    Uses FFmpeg to extract keyframes from the provided video at the specified interval.
    
    :param video_path: Path to the video file.
    :param output_dir: Directory where keyframes will be stored.
    :param frame_interval: The interval between frames to extract.
    :return: A list of file paths to the extracted keyframes.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Construct the FFmpeg command to extract keyframes
    command = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"select='not(mod(n\\,{frame_interval}))'",
        "-vsync", "vfr",
        os.path.join(output_dir, "keyframe_%04d.jpg")
    ]
    
    # Run the FFmpeg command
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Collect the paths of the extracted keyframes
    keyframe_paths = []
    for file in sorted(os.listdir(output_dir)):
        if file.endswith(".jpg"):
            keyframe_paths.append(os.path.join(output_dir, file))
    return keyframe_paths

def clean_output(raw_text: str) -> str:
    """
    Cleans the output text by removing markdown code block formatting if present.
    """
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().endswith("```"):
            lines = lines[:-1]
        raw_text = "\n".join(lines).strip()
    return raw_text

def analyze_image_for_dork(image_path: str, description: str) -> list:
    """
    Uploads an image (keyframe) and generates a JSON array containing Google dork queries.
    The output is strictly a JSON array of query strings.
    
    :param image_path: Path to the image file.
    :param description: Additional context for refining the AI's analysis.
    :return: A list of Google dork query strings.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Upload the image file
    myfile = genai.upload_file(image_path)

    # Prompt instructs the model to return only a JSON array of query strings
    prompt = f"""
You are an advanced image analysis engine. Your task is to analyze the provided image (a keyframe extracted from a video)
and deduce the context, theme, and visual cues that could be used to locate related content on the web.
Based on your analysis, generate Google dork queries using specific keywords and search operators (such as site:, intext:, intitle:, etc.).

Instructions:
1. Analyze the image and extract key visual and contextual elements.
2. Construct one or more detailed Google dork query strings that incorporate these elements.
3. Return only a JSON array containing the Google dork query strings. Each element of the array must be a string.
4. Do not include any additional text, commentary, or extra fields.

Additional Context: {description}

Return only the JSON array.
"""

    model = genai.GenerativeModel("gemini-1.5-flash")
    result = model.generate_content([myfile, "\n\n", prompt])

    # Clean the model output to remove any markdown formatting
    cleaned_text = clean_output(result.text)
    
    try:
        output_array = json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from model output: {cleaned_text}") from e

    if not isinstance(output_array, list):
        raise ValueError("The model output is not a JSON array as expected.")

    return output_array

@app.route("/discover", methods=["POST"])
def discover():
    """
    The /discover endpoint accepts a multipart POST request with the following fields:
      - file: the video file
      - name: the video's name
      - description: additional context/description for analysis
    It extracts keyframes from the video, sends each keyframe to the Gemini API for analysis,
    and returns a JSON array of unique Google dork queries.
    """
    # Validate that the file exists in the request
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    name = request.form.get("name", "")
    description = request.form.get("description", "")

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Save the video file to a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, file.filename)
        file.save(video_path)
        keyframes_output_dir = os.path.join(tmpdir, "keyframes")
        
        try:
            # Extract keyframes from the video
            keyframe_paths = extract_keyframes(video_path, keyframes_output_dir, frame_interval=30)
            all_dork_queries = []

            # Send each extracted keyframe to the Gemini API for analysis
            for keyframe in keyframe_paths:
                queries = analyze_image_for_dork(keyframe, description)
                all_dork_queries.extend(queries)
            
            # Remove duplicate queries if any
            unique_dork_queries = list(set(all_dork_queries))
            
            # Return strictly the JSON array of Google dork queries
            return jsonify(unique_dork_queries)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Run the Flask app on port 8002
    app.run(port=8002)
