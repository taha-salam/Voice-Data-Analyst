"""
Fine-grained latency tracking and benchmarking utility.
Measures timing across all pipeline stages from spoken input to spoken output.
"""
import time
from typing import Dict, Any, List

class LatencyTracker:
    """Tracks latency breakdown across all pipeline modules."""
    
    def __init__(self):
        self.timings: Dict[str, float] = {}
        self.stage_starts: Dict[str, float] = {}
        self.overall_start: float = time.time()

    def start_stage(self, stage_name: str):
        self.stage_starts[stage_name] = time.time()

    def end_stage(self, stage_name: str) -> float:
        if stage_name in self.stage_starts:
            duration = time.time() - self.stage_starts[stage_name]
            self.timings[stage_name] = round(duration, 4)
            return self.timings[stage_name]
        return 0.0

    def record_stage(self, stage_name: str, duration: float):
        self.timings[stage_name] = round(duration, 4)

    def total_latency(self) -> float:
        return round(sum(self.timings.values()), 4)

    def get_breakdown(self) -> Dict[str, Any]:
        return {
            "stages": dict(self.timings),
            "total_latency_seconds": self.total_latency()
        }

    def format_summary_table(self) -> str:
        lines = ["| Stage | Latency (seconds) | Share (%) |", "|---|---|---|"]
        total = self.total_latency()
        for stage, duration in self.timings.items():
            share = (duration / total * 100.0) if total > 0 else 0.0
            lines.append(f"| {stage.replace('_', ' ').title()} | {duration:.3f}s | {share:.1f}% |")
        lines.append(f"| **Total End-to-End** | **{total:.3f}s** | **100.0%** |")
        return "\n".join(lines)
