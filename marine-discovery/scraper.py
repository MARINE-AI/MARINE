import os
import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from urllib.parse import urljoin
import yt_dlp

router = APIRouter()

def download_video_with_yt_dlp(url: str, output_format: str = "mp4") -> str:
    """
    Download a video using yt-dlp. This is suited for YouTube and other supported sites.
    
    Args:
        url (str): The video URL.
        output_format (str): The desired output format (e.g., 'mp4').
    
    Returns:
        str: The filename of the downloaded (and possibly converted) video.
    
    Raises:
        Exception: If downloading or conversion fails.
    """
    temp_dir = os.path.join(os.getcwd(), "temp_videos")
    os.makedirs(temp_dir, exist_ok=True)
    outtmpl = os.path.join(temp_dir, "%(id)s.%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': outtmpl,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': output_format,
        }],
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            base_filename = ydl.prepare_filename(info_dict)
            if not base_filename.endswith(f".{output_format}"):
                base_filename = base_filename.rsplit('.', 1)[0] + f".{output_format}"
            if not os.path.exists(base_filename):
                raise Exception("File was not downloaded.")
            return base_filename
    except Exception as e:
        raise Exception(f"yt-dlp failed: {e}")


def download_video_generic(video_url: str) -> bytes:
    """
    Download a video file from a direct URL.
    
    Args:
        video_url (str): The URL of the video.
        
    Returns:
        bytes: The content of the video file.
    
    Raises:
        Exception: If download fails.
    """
    try:
        response = requests.get(video_url, stream=True, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        raise Exception(f"Failed to download video from {video_url}: {e}")


def send_video_to_ai(video_bytes: bytes, video_name: str, ai_url: str) -> dict:
    """
    Send the video data to the AI microservice.
    
    Args:
        video_bytes (bytes): Video file content.
        video_name (str): The filename for the video.
        ai_url (str): The AI microservice endpoint.
    
    Returns:
        dict: The JSON response from the AI service.
    
    Raises:
        Exception: If the HTTP request fails.
    """
    files = {'file': (video_name, video_bytes, 'video/mp4')}
    try:
        response = requests.post(ai_url, files=files, timeout=60)   
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Failed to send video to AI microservice: {e}")

@router.get("/scrape-videos")
async def scrape_videos_endpoint(url: str, ai_service_url: str):
    """
    Scrape a given URL for videos and forward them to an AI microservice.
    
    The endpoint attempts the following:
      1. If the URL is from a supported site (like YouTube), use yt-dlp to download.
      2. Otherwise, fall back to scraping the HTML for <video> tags.
    
    Query Parameters:
      - url (str): The target webpage or video URL.
      - ai_service_url (str): The AI microservice endpoint for video analysis.
    
    Returns:
      JSON containing the results from the AI microservice.
    """
    results = {}
    try:
        try:
            downloaded_filename = download_video_with_yt_dlp(url)
            with open(downloaded_filename, "rb") as f:
                video_bytes = f.read()
            video_name = os.path.basename(downloaded_filename)
            ai_response = send_video_to_ai(video_bytes, video_name, ai_service_url)
            results["method"] = "yt-dlp"
            results["video"] = {
                "source_url": url,
                "downloaded_file": video_name,
                "ai_response": ai_response
            }
            os.remove(downloaded_filename)
            return results
        except Exception as yt_error:
            results["yt_dlp_error"] = str(yt_error)
        
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        video_tags = soup.find_all("video")
        video_results = []
        
        for video in video_tags:
            src = video.get("src")
            if not src:
                source_tag = video.find("source")
                if source_tag:
                    src = source_tag.get("src")
            if src:
                video_url = urljoin(url, src)
                try:
                    video_bytes = download_video_generic(video_url)
                    video_name = video_url.split("/")[-1] or "video.mp4"
                    ai_response = send_video_to_ai(video_bytes, video_name, ai_service_url)
                    video_results.append({
                        "video_url": video_url,
                        "downloaded_as": video_name,
                        "ai_response": ai_response
                    })
                except Exception as e:
                    video_results.append({
                        "video_url": video_url,
                        "error": str(e)
                    })
        if video_results:
            results["method"] = "scraping"
            results["videos"] = video_results
        else:
            results["message"] = "No videos found using either method."
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
