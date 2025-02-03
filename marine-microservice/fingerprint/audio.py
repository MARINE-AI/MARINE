# app/fingerprinting/audio.py

import subprocess
import librosa
import numpy as np

def extract_audio(video_path: str, output_audio: str = "temp_audio.wav") -> str:
    """
    Extracts audio from a video using ffmpeg.
    """
    command = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        output_audio
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_audio
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        return None

def generate_audio_fingerprint(audio_file: str, n_mfcc: int = 20) -> np.ndarray:
    """
    Generates an audio fingerprint using MFCC features.
    """
    try:
        y, sr = librosa.load(audio_file, sr=None)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
        return np.mean(mfcc, axis=1)
    except Exception as e:
        print(f"Error generating audio fingerprint: {e}")
        return None
