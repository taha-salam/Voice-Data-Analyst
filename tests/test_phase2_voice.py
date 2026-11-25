"""
Unit tests for Phase 2: Local Offline Voice Engine (STT & TTS) + Latency Tracker.
"""
import pytest
import os
from pathlib import Path
from src.voice.stt import LocalSTT
from src.voice.tts import LocalTTS
from src.utils.latency_tracker import LatencyTracker
from src.config import Config

@pytest.fixture(scope="session")
def tts_engine():
    Config.ensure_directories()
    return LocalTTS(voice_speed=180)

@pytest.fixture(scope="session")
def stt_engine():
    # Use tiny.en for quick unit testing
    return LocalSTT(model_size="tiny.en", device="cpu", compute_type="int8")

def test_local_tts_synthesis(tts_engine):
    """Test offline TTS creates a valid WAV audio file with low latency."""
    text = "Sales in Sao Paulo peaked in March, approximately twenty percent above average."
    output_path, latency = tts_engine.synthesize_to_file(text)
    
    assert os.path.exists(output_path), "Synthesized WAV file does not exist"
    assert os.path.getsize(output_path) > 1000, "Synthesized WAV file should be non-empty"
    assert latency > 0.0, "TTS latency should be recorded"
    assert latency < 10.0, f"Offline TTS took {latency:.2f}s"
    
    # Second run should be even faster (< 4.0s) once initialized
    _, second_latency = tts_engine.synthesize_to_file("Second call test.")
    assert second_latency < 4.0, f"Warm TTS should take under 4.0s, took {second_latency:.2f}s"
    
    # Clean up
    if os.path.exists(output_path):
        os.remove(output_path)

def test_local_stt_transcription(tts_engine, stt_engine):
    """Test full loop: synthesize spoken audio and transcribe it back using local faster-whisper."""
    test_phrase = "Which products brought in the highest revenue last quarter?"
    audio_file, _ = tts_engine.synthesize_to_file(test_phrase)
    
    assert os.path.exists(audio_file)
    
    try:
        result = stt_engine.transcribe_file(audio_file, language="en")
        transcribed_text = result["text"].lower()
        
        # Verify key domain keywords are recognized
        assert len(transcribed_text) > 0
        assert "product" in transcribed_text or "revenue" in transcribed_text
        assert result["latency"] > 0.0
    finally:
        if os.path.exists(audio_file):
            os.remove(audio_file)

def test_latency_tracker():
    """Test fine-grained stage latency measurement and table output."""
    tracker = LatencyTracker()
    tracker.record_stage("speech_to_text", 0.420)
    tracker.record_stage("domain_correction", 0.015)
    tracker.record_stage("schema_pruning", 0.035)
    tracker.record_stage("sql_generation", 0.850)
    tracker.record_stage("db_execution", 0.012)
    tracker.record_stage("insight_generation", 0.650)
    tracker.record_stage("text_to_speech", 0.180)
    
    total = tracker.total_latency()
    assert round(total, 3) == 2.162
    
    breakdown = tracker.get_breakdown()
    assert "stages" in breakdown
    assert breakdown["total_latency_seconds"] == 2.162
    
    table = tracker.format_summary_table()
    assert "| Speech To Text | 0.420s |" in table
    assert "**Total End-to-End**" in table
