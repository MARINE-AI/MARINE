# import os
# import subprocess
# import json
# import tempfile
# from fastapi import FastAPI, UploadFile, File, Form, HTTPException
# from pydantic import BaseModel
# import google.generativeai as genai

# os.environ["GRPC_VERBOSITY"] = "ERROR"
# os.environ["GRPC_TRACE"] = ""

# genai.configure(api_key="")

# app = FastAPI()

# def extract_keyframes(video_path: str, output_dir: str, frame_interval: int = 30) -> list:
#     """
#     Uses FFmpeg to extract keyframes from the provided video at the specified interval.

#     :param video_path: Path to the video file.
#     :param output_dir: Directory where keyframes will be stored.
#     :param frame_interval: The interval between frames to extract.
#     :return: A list of file paths to the extracted keyframes.
#     """
#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)
    
#     # Construct the FFmpeg command to extract keyframes
#     command = [
#         "ffmpeg",
#         "-i", video_path,
#         "-vf", f"select='not(mod(n\\,{frame_interval}))'",
#         "-vsync", "vfr",
#         os.path.join(output_dir, "keyframe_%04d.jpg")
#     ]
    
#     # Run the FFmpeg command
#     subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
#     # Collect the paths of the extracted keyframes
#     keyframe_paths = []
#     for file in sorted(os.listdir(output_dir)):
#         if file.endswith(".jpg"):
#             keyframe_paths.append(os.path.join(output_dir, file))
#     return keyframe_paths

# def clean_output(raw_text: str) -> str:
#     """
#     Cleans the output text by removing markdown code block formatting if present.
#     """
#     raw_text = raw_text.strip()
#     if raw_text.startswith("```"):
#         lines = raw_text.splitlines()
#         if lines[0].startswith("```"):
#             lines = lines[1:]
#         if lines and lines[-1].strip().endswith("```"):
#             lines = lines[:-1]
#         raw_text = "\n".join(lines).strip()
#     return raw_text

# def analyze_image_for_dork(image_path: str, description: str) -> list:
#     """
#     Uploads an image (keyframe) and generates a JSON array containing Google dork queries.
#     The output is strictly a JSON array of query strings.

#     :param image_path: Path to the image file.
#     :param description: Additional context for refining the AI's analysis.
#     :return: A list of Google dork query strings.
#     """
#     if not os.path.exists(image_path):
#         raise FileNotFoundError(f"Image not found: {image_path}")

#     # Upload the image file to the Gemini API
#     myfile = genai.upload_file(image_path)

#     # Instruct the model to return only a JSON array of query strings
#     prompt = f"""
# You are an advanced image analysis engine. Your task is to analyze the provided image (a keyframe extracted from a video)
# and deduce the context, theme, and visual cues that could be used to locate related content on the web.
# Based on your analysis, generate Google dork queries using specific keywords and search operators (such as site:, intext:, intitle:, etc.).

# Instructions:
# 1. Analyze the image and extract key visual and contextual elements.
# 2. Construct one or more detailed Google dork query strings that incorporate these elements.
# 3. Return only a JSON array containing the Google dork query strings. Each element of the array must be a string.
# 4. Do not include any additional text, commentary, or extra fields.

# Additional Context: {description}

# Return only the JSON array.
# """

#     model = genai.GenerativeModel("gemini-1.5-flash")
#     result = model.generate_content([myfile, "\n\n", prompt])

#     # Clean the model output to remove any markdown formatting
#     cleaned_text = clean_output(result.text)
    
#     try:
#         output_array = json.loads(cleaned_text)
#     except json.JSONDecodeError as e:
#         raise ValueError(f"Failed to parse JSON from model output: {cleaned_text}") from e

#     if not isinstance(output_array, list):
#         raise ValueError("The model output is not a JSON array as expected.")

#     return output_array

# @app.post("/discover")
# async def discover(
#     file: UploadFile = File(...),
#     name: str = Form(""),
#     description: str = Form("")
# ):
#     """
#     The /discover endpoint accepts a multipart POST request with the following fields:
#       - file: the video file
#       - name: the video's name (optional)
#       - description: additional context/description for analysis (optional)

#     It extracts keyframes from the video, sends each keyframe to the Gemini API for analysis,
#     and returns a JSON array of unique Google dork queries.
#     """
#     try:
#         with tempfile.TemporaryDirectory() as tmpdir:
#             video_path = os.path.join(tmpdir, file.filename)
#             contents = await file.read()
#             with open(video_path, "wb") as f:
#                 f.write(contents)
#             keyframes_output_dir = os.path.join(tmpdir, "keyframes")
            
#             # Extract keyframes from the video
#             keyframe_paths = extract_keyframes(video_path, keyframes_output_dir, frame_interval=30)
#             all_dork_queries = []

#             # Analyze each keyframe using the Gemini API
#             for keyframe in keyframe_paths:
#                 queries = analyze_image_for_dork(keyframe, description)
#                 all_dork_queries.extend(queries)
            
#             # Remove duplicate queries if any
#             unique_dork_queries = list(set(all_dork_queries))
            
#             return unique_dork_queries
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # Global list to store submitted URLs
# url_list = []

# class URLRequest(BaseModel):
#     url: str

# @app.post("/submit")
# async def submit_url(request: URLRequest):
#     """
#     The /submit endpoint receives a URL and adds it to the global url_list.
#     """
#     url_list.append(request.url)
#     return {"message": f"URL {request.url} submitted for crawling."}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("discovery-logic:app", host="0.0.0.0", port=8002, reload=True)
