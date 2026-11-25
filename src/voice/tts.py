"""
Local Text-to-Speech (TTS) Engine.
Runs 100% offline using native SAPI5 / pyttsx3 with output file rendering.
"""
import time
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Tuple, Optional
import pyttsx3
from src.config import Config

class LocalTTS:
    """Offline speech synthesizer for spoken explanations and spoken clarifications."""
    
    _lock = threading.Lock()

    def __init__(self, voice_speed: int = 175, volume: float = 1.0):
        self.voice_speed = voice_speed
        self.volume = volume

    @staticmethod
    def clean_spoken_text(text: str) -> str:
        """Strips markdown code blocks, asterisks, hashes, and formatting for natural spoken speech."""
        if not text:
            return ""
        # Remove code blocks
        clean = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        # Remove inline backticks
        clean = re.sub(r'`([^`]+)`', r'\1', clean)
        # Remove markdown bold/italics
        clean = re.sub(r'[*_~]', '', clean)
        # Remove markdown headers and bullet markers
        clean = re.sub(r'^#+\s*', '', clean, flags=re.MULTILINE)
        clean = re.sub(r'^\s*[-*+]\s+', '', clean, flags=re.MULTILINE)
        # Replace symbols with words
        clean = re.sub(r'\$(\d+)', r'\1 dollars', clean)
        clean = re.sub(r'(\d+)%', r'\1 percent', clean)
        # Normalize whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def synthesize_to_file(self, text: str, output_path: Optional[str] = None) -> Tuple[str, float]:
        """
        Synthesizes text into a local WAV audio file.
        Returns: (output_file_path, latency_seconds)
        """
        clean_text = self.clean_spoken_text(text)
        if not clean_text:
            return "", 0.0

        if output_path is None:
            temp_dir = Config.BASE_DIR / "temp_audio"
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir=temp_dir)
            output_path = temp_file.name
            temp_file.close()

        start_time = time.time()
        
        with self._lock:
            engine = pyttsx3.init()
            engine.setProperty("rate", self.voice_speed)
            engine.setProperty("volume", self.volume)
            
            # Select an English voice if available
            voices = engine.getProperty("voices")
            for v in voices:
                if "david" in v.name.lower() or "zira" in v.name.lower() or "english" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
                    
            engine.save_to_file(clean_text, output_path)
            engine.runAndWait()
            # Cleanly stop engine to avoid COM hang
            engine.stop()

        latency = time.time() - start_time
        return output_path, latency

    def speak(self, text: str) -> float:
        """Speaks text directly via the system speakers."""
        clean_text = self.clean_spoken_text(text)
        if not clean_text:
            return 0.0
            
        start_time = time.time()
        with self._lock:
            engine = pyttsx3.init()
            engine.setProperty("rate", self.voice_speed)
            engine.setProperty("volume", self.volume)
            engine.say(clean_text)
            engine.runAndWait()
            engine.stop()
        return time.time() - start_time
