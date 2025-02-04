import requests
import json
import os
import cv2

def extract_keyframes(video_path, output_dir, frame_interval=30):
    """
    Extracts keyframes from the given video at a specified interval.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"Failed to open video file: {video_path}")

    frame_count = 0
    keyframe_paths = []

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        if frame_count % frame_interval == 0:
            keyframe_path = os.path.join(output_dir, f"keyframe_{frame_count}.jpg")
            cv2.imwrite(keyframe_path, frame)
            keyframe_paths.append(keyframe_path)

        frame_count += 1

    cap.release()
    return keyframe_paths

def analyze_keyframes_with_gemini(keyframe_paths, gemini_api_url, gemini_api_key, initial_description):
    """
    Sends extracted keyframes to the Gemini API for metadata analysis.
    """
    prompt = (
        "You are a content analyser. Analyze the provided keyframes and generate useful metadata and context "
        "for the video. The output should be in JSON format. The user has provided an initial description: "
        f"'{initial_description}'. Use this information to enhance the metadata generation."
    )

    headers = {
        "Authorization": f"Bearer {gemini_api_key}",
        "Content-Type": "application/json"
    }

    metadata_list = []

    for keyframe_path in keyframe_paths:
        with open(keyframe_path, "rb") as image_file:
            files = {
                "image_file": image_file,
                "metadata": (None, json.dumps({"prompt": prompt}), "application/json")
            }

            response = requests.post(gemini_api_url, headers=headers, files=files)
            if response.status_code == 200:
                metadata = response.json()
                metadata_list.append(metadata)
            else:
                print(f"Failed to analyze keyframe {keyframe_path}: {response.status_code} - {response.text}")

    return metadata_list

def submit_parsed_metadata(submit_api_url, metadata):
    """
    Submits the parsed metadata to the '/submit' endpoint.
    """
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(submit_api_url, headers=headers, json=metadata)
    if response.status_code == 200:
        print("Metadata successfully submitted!")
        return response.json()
    else:
        raise Exception(f"Submission failed: {response.status_code} - {response.text}")

def main():
    """
    Main function to test the entire flow.
    """
    # Local variables
    local_video_path = "path/to/your/local_video.mp4"  # Update with the actual video path
    output_dir = "keyframes_output"
    gemini_api_url = "https://api.gemini.com/analyze"
    gemini_api_key = "your_gemini_api_key_here"
    submit_api_url = "https://your.api/submit"
    initial_description = input("Enter the initial description for the video: ")

    # Step 1: Extract keyframes
    try:
        keyframe_paths = extract_keyframes(local_video_path, output_dir)
        print(f"Extracted {len(keyframe_paths)} keyframes.")
    except Exception as e:
        print(f"Error during keyframe extraction: {e}")
        return

    # Step 2: Analyze keyframes with Gemini API
    try:
        gemini_metadata = analyze_keyframes_with_gemini(keyframe_paths, gemini_api_url, gemini_api_key, initial_description)
        print("Gemini API Metadata:")
        print(json.dumps(gemini_metadata, indent=4))
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        return

    # Step 3: Submit the parsed metadata
    try:
        response = submit_parsed_metadata(submit_api_url, gemini_metadata)
        print("Submit API Response:")
        print(json.dumps(response, indent=4))
    except Exception as e:
        print(f"Error during metadata submission: {e}")

if __name__ == "__main__":
    main()
