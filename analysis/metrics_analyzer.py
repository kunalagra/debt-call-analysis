import logging
import pandas as pd
from typing import Tuple
from collections import defaultdict
import numpy as np # For handling potential infinities

def calculate_call_metrics(call_df: pd.DataFrame) -> Tuple[float, float, float]:
    if call_df is None or call_df.empty:
        return 0.0, 0.0, 0.0
    call_df = call_df.sort_values(by="stime").reset_index(drop=True)
    call_df = call_df.dropna(subset=["stime", "etime"])
    call_df = call_df[pd.to_numeric(call_df["stime"], errors="coerce").notna()]
    call_df = call_df[pd.to_numeric(call_df["etime"], errors="coerce").notna()]
    call_df["stime"] = call_df["stime"].astype(float)
    call_df["etime"] = call_df["etime"].astype(float)
    call_df = call_df[call_df["etime"] >= call_df["stime"]]
    if call_df.empty:
        return 0.0, 0.0, 0.0
    min_start_time = call_df["stime"].min()
    max_end_time = call_df["etime"].max()
    total_duration = max_end_time - min_start_time
    if total_duration <= 0:
        is_silent = (call_df["etime"] - call_df["stime"]).sum() == 0
        return 0.0, 100.0 if is_silent else 0.0, 0.0
    intervals = sorted([(row["stime"], row["etime"]) for _, row in call_df.iterrows()])
    timeline = defaultdict(int)
    for start, end in intervals:
        start = max(min_start_time, start)
        end = min(max_end_time, end)
        if end > start:
            timeline[start] += 1
            timeline[end] -= 1
    active_speakers = 0
    last_time = min_start_time
    merged_speech_duration = 0.0
    overlap_duration = 0.0
    sorted_times = sorted(timeline.keys())
    for t in sorted_times:
        if t < last_time:
            continue
        segment_duration = t - last_time
        if active_speakers > 0:
            merged_speech_duration += segment_duration
            if active_speakers > 1:
                overlap_duration += segment_duration
        active_speakers += timeline[t]
        last_time = t
        if active_speakers < 0:
            active_speakers = 0  # Safety reset
    overtalk_pct = (
        (overlap_duration / total_duration) * 100 if total_duration > 0 else 0.0
    )
    silence_duration = max(0, total_duration - merged_speech_duration)
    silence_pct = (
        (silence_duration / total_duration) * 100 if total_duration > 0 else 0.0
    )
    overtalk_pct = max(0.0, min(100.0, overtalk_pct))
    silence_pct = max(0.0, min(100.0, silence_pct))
    return overtalk_pct, silence_pct, total_duration
