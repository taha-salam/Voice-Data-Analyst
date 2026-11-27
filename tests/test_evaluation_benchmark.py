"""
Unit and integration tests for Phase 7: Evaluation Suite & Adversarial Safety Benchmark.
"""
import pytest
from src.utils.evaluation import (
    compute_levenshtein_distance,
    compute_wer,
    BenchmarkRunner
)
from app import initialize_system

def test_wer_calculation():
    """Verify standard Word Error Rate calculation."""
    ref = "what is the total revenue in sao paulo"
    hyp_identical = "what is the total revenue in sao paulo"
    hyp_sub = "what is the total revenue in san paulo"
    hyp_del = "what is total revenue in sao paulo"
    hyp_ins = "what is the total sales revenue in sao paulo"

    assert compute_wer(ref, hyp_identical) == 0.0
    assert compute_wer(ref, hyp_sub) == pytest.approx(1 / 8, rel=1e-2)
    assert compute_wer(ref, hyp_del) == pytest.approx(1 / 8, rel=1e-2)
    assert compute_wer(ref, hyp_ins) == pytest.approx(1 / 8, rel=1e-2)

def test_domain_correction_wer_benchmark():
    """Verify that domain entity correction achieves strong WER reduction and recovery."""
    engines = initialize_system()
    runner = BenchmarkRunner(engines["db_mgr"], engines["profiles"], engines["corrector"])
    
    results = runner.evaluate_domain_correction()
    
    assert results["total_cases"] == 15
    assert results["avg_pre_wer"] > results["avg_post_wer"]
    assert results["wer_reduction_percent"] >= 30.0
    assert results["entity_recovery_rate"] >= 75.0
    print(f"\n[BENCHMARK] WER Reduction: {results['wer_reduction_percent']}% | Recovery: {results['entity_recovery_rate']}%")

def test_adversarial_safety_100_percent_defense():
    """CRITICAL: Verify that 100% of adversarial attacks are completely intercepted and blocked."""
    engines = initialize_system()
    runner = BenchmarkRunner(engines["db_mgr"], engines["profiles"], engines["corrector"])
    
    safety_results = runner.evaluate_adversarial_safety()
    
    assert safety_results["total_attacks"] == 12
    assert safety_results["defense_success_rate"] == 100.0
    assert safety_results["blocked_count"] == 12

    for r in safety_results["results"]:
        assert r["blocked"] is True, f"Security vulnerability detected: {r['attack_name']} was allowed!"
    print(f"\n[SECURITY] 12/12 attacks blocked (100% defense success rate).")

def test_full_benchmark_runner_and_export():
    """Run full benchmark suite and verify export of evaluation artifacts."""
    engines = initialize_system()
    runner = BenchmarkRunner(engines["db_mgr"], engines["profiles"], engines["corrector"])
    
    all_res = runner.run_all(output_dir="data")
    
    assert "domain_correction_benchmark" in all_res
    assert "adversarial_safety_benchmark" in all_res
    assert "latency_breakdown_benchmark" in all_res
    
    # Check latency numbers
    latency = all_res["latency_breakdown_benchmark"]
    assert latency["total_turnaround"]["mean_ms"] > 0
    assert latency["sql_generation"]["mean_ms"] > 0
    assert latency["tts_synthesis"]["mean_ms"] > 0
    print(f"\n[LATENCY] Total turnaround mean: {latency['total_turnaround']['mean_ms']} ms")

def test_acoustic_asr_wer_evaluation():
    """Verify empirical acoustic ASR evaluation using TTS synthesis and Whisper transcription."""
    engines = initialize_system()
    runner = BenchmarkRunner(engines["db_mgr"], engines["profiles"], engines["corrector"])
    res = runner.evaluate_acoustic_asr_wer(num_samples=2)
    assert res["samples_evaluated"] == 2
    assert "avg_acoustic_pre_wer" in res
    assert "avg_acoustic_post_wer" in res
    assert len(res["results"]) == 2
