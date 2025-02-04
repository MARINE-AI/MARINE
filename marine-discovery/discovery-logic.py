import requests
import json
import os

def read_local_video(file_path):
    """
    Read the local video file to upload it to the API.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file at {file_path} does not exist.")
    return open(file_path, "rb")

def analyze_video_with_gemini(file_path, gemini_api_url, gemini_api_key, initial_description):
    """
    Use the Gemini API to analyze a local video and generate metadata, combining the user's initial description.
    """
    # Define the prompt for the Gemini API
    prompt = (
        "You are a content analyser. You have to analyse keyframes for this video "
        "in a single command and generate useful meta-data and context to the video. "
        "The output should be in a JSON format. The user has also provided an initial description: "
        f"'{initial_description}'. Use this information to enhance the metadata generation."
    )
    
    headers = {
        "Authorization": f"Bearer {gemini_api_key}",
        "Content-Type": "application/json"
    }

    # Read the local video file
    video_file = read_local_video(file_path)

    # Define the payload
    payload = {
        "prompt": prompt
    }
    
    # Attach the video file as part of the POST request
    files = {
        "video_file": video_file,
        "metadata": (None, json.dumps(payload), "application/json")
    }

    try:
        # Send a POST request to the Gemini API
        response = requests.post(gemini_api_url, headers=headers, files=files)

        # Close the video file after sending
        video_file.close()

        # Check the response status and return the JSON output
        if response.status_code == 200:
            metadata = response.json()
            # Combine Gemini API metadata with the initial user-provided description
            metadata["video_metadata"]["user_description"] = initial_description
            return metadata
        else:
            raise Exception(f"Gemini API request failed: {response.status_code} - {response.text}")
    
    except Exception as e:
        # Ensure the file is closed in case of errors
        video_file.close()
        raise e

def submit_parsed_metadata(submit_api_url, metadata):
    """
    Submit the parsed metadata to the '/submit' endpoint.
    """
    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(submit_api_url, headers=headers, json=metadata)

        if response.status_code == 200:
            print("Metadata successfully submitted!")
            return response.json()
        else:
            raise Exception(f"Submission failed: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"Error in submitting metadata: {e}")
        return None

def main():
    """
    Main function to test the entire flow.
    """
    # Local variables (update with your actual values)
    local_video_path = "path/to/your/local_video.mp4"  # Path to the local video
    gemini_api_url = "https://api.gemini.com/analyze"
    gemini_api_key = "your_gemini_api_key_here"
    submit_api_url = "https://your.api/submit"
    initial_description = input("Enter the initial description for the video: ")  # Get user input

    # Step 1: Analyze the video with the Gemini API
    try:
        gemini_metadata = analyze_video_with_gemini(local_video_path, gemini_api_url, gemini_api_key, initial_description)
        print("Gemini API Metadata:")
        print(json.dumps(gemini_metadata, indent=4))
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        return

    # Step 2: Submit the parsed metadata to the '/submit' endpoint
    try:
        response = submit_parsed_metadata(submit_api_url, gemini_metadata)
        print("Submit API Response:")
        print(json.dumps(response, indent=4))
    except Exception as e:
        print(f"Error during metadata submission: {e}")

if __name__ == "__main__":
    main()
