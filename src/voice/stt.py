"""
Local Speech-to-Text (ASR) Engine using faster-whisper.
Runs 100% offline with int8 quantization on CPU.
"""
import time
import os
import io
import tempfile
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from faster_whisper import WhisperModel
from src.config import Config

class LocalSTT:
    """Offline speech recognition using quantized Whisper models."""
    
    _instance = None
    _model = None

    def __init__(self, model_size: Optional[str] = None, device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size or Config.WHISPER_MODEL_SIZE
        self.device = device
        self.compute_type = compute_type
        self.model = None

    def load_model(self):
        """Loads Whisper model weights lazily or on startup."""
        if self.model is None:
            # print(f"Loading local Whisper model: {self.model_size} ({self.device}, {self.compute_type})...")
            models_dir = Config.BASE_DIR / "models" / "whisper"
            models_dir.mkdir(parents=True, exist_ok=True)
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=str(models_dir)
            )
        return self.model

    def transcribe_file(self, audio_path: str, language: str = "en") -> Dict[str, Any]:
        """
        Transcribes an audio file on disk.
        Returns dict with 'text', 'latency_seconds', 'language', and 'segments'.
        """
        model = self.load_model()
        start_time = time.time()
        
        segments, info = model.transcribe(
            audio_path,
            beam_size=5,
            language=language,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        segment_texts = []
        for segment in segments:
            segment_texts.append(segment.text.strip())
            
        full_text = " ".join(segment_texts).strip()
        latency = time.time() - start_time
        
        return {
            "text": full_text,
            "latency": latency,
            "language": info.language,
            "probability": info.language_probability
        }

    def transcribe_audio_bytes(self, audio_bytes: bytes, suffix: str = ".wav") -> Dict[str, Any]:
        """Transcribes raw audio bytes (e.g. from Streamlit audio recorder)."""
        temp_dir = Config.BASE_DIR / "temp_audio"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=temp_dir) as temp_file:
            temp_path = temp_file.name
            temp_file.write(audio_bytes)
            
        try:
            result = self.transcribe_file(temp_path)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
                    
        return result
