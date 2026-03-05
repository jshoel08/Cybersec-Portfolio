# Network Latency Analysis for Multiplayer Gaming

## Overview
This project analyzes network latency during online gaming sessions to investigate whether abnormal packet behavior (such as lag switching exploits) can be detected.

## Goal
The goal was to compare normal network behavior with live multiplayer matches to determine if latency spikes, packet loss, or jitter patterns indicate network manipulation.

## Methodology

1. Collect baseline ping telemetry during normal gameplay.
2. Capture ping telemetry during online matches.
3. Parse the logs using a Python script.
4. Calculate metrics including:
   - Average latency
   - Packet loss
   - Jitter
   - Latency spikes
5. Generate graphs to visualize network behavior.

## Tools Used

- Python
- Regex log parsing
- Matplotlib
- ICMP ping telemetry

## Outputs

The project generates several outputs:

- `ping_summary.csv` — structured latency statistics
- `summary_latency.png` — comparison of latency across matches
- `summary_loss.png` — packet loss comparison
- `match_xx_graph.png` — latency timeline for each match

## Conclusion

No structured exploit patterns were detected during the recorded matches.  
However, the project demonstrates a methodology for detecting abnormal network behavior through telemetry analysis.

## Files Included

- Raw ping logs
- Python analysis script
- CSV statistics output
- Latency visualization graphs