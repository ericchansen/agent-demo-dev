---
sidebar_position: 1
title: Facilitator Guide
---

# Facilitator Guide

This page is for people running this workshop with a group. It covers pacing, what to demo vs. hands-on, and how to adapt the material to different time slots.

## The journey structure

The workshop follows a progressive narrative. Each chapter builds on the previous one:

| Chapter | Core concept | Suggested time |
|---|---|---|
| [From Chat to Agent](../journey/from-chat-to-agent) | Why agents need connections | 15 min (lecture) |
| [Ground It in Data](../journey/ground-it-in-data) | Connect Fabric Data Agent | 30-45 min (hands-on) |
| [Give It Context](../journey/give-it-context) | Connect WorkIQ | 20-30 min (demo + discussion) |
| [Arm It with Tools](../journey/arm-it-with-tools) | Report generation, real output | 30-45 min (hands-on) |
| [Build Reusable Skills](../journey/build-reusable-skills) | Compose into workflows | 20-30 min (hands-on) |
| [Ship It](../journey/ship-it) | CLI → Foundry → M365 | 30-45 min (demo + discussion) |

**Total: 2.5 – 4 hours** depending on hands-on depth.

## Pacing options

### Half-day workshop (3 hours)
All six chapters. Chapters 1, 3, and 6 as demos/lectures. Chapters 2, 4, and 5 as guided hands-on.

### Full-day workshop (6 hours)
All chapters with deep hands-on. Add time for participants to build their own skills and experiment with different queries. Include the architecture section as a midday deep-dive.

### 90-minute overview
Chapters 1, 2, and 6 only. Focus on the narrative arc: why agents need data connections → show it working → show it deployed. Skip skills and tools — reference them as "what comes next."

### Multi-session series
One chapter per session (weekly or biweekly). Participants have homework between sessions to extend what they built.

## What to demo vs. hands-on

| Chapter | Recommendation |
|---|---|
| From Chat to Agent | **Lecture/demo** — set the narrative, show the problem |
| Ground It in Data | **Hands-on** — participants connect their own Data Agent |
| Give It Context | **Demo** (if mock data) or **Hands-on** (if real WorkIQ access) |
| Arm It with Tools | **Hands-on** — run the report generator, see real output |
| Build Reusable Skills | **Hands-on** — participants write their own skill |
| Ship It | **Demo** — show Foundry deployment, M365 chat |

## Prerequisites for participants

See [Setup Guide](./setup) for full details. At minimum:
- GitHub Copilot CLI installed and authenticated
- Python 3.11+ with the repo cloned and dependencies installed
- Access to a Fabric workspace (shared or individual)

## Tips

- **Start with the "why"** — Chapter 1 sets up the entire narrative. Don't skip it.
- **Use the demo script** — the [NCR Voyix QBR scenario](./demo-script) gives a concrete use case
- **Show the mermaid diagrams** — architecture visuals help non-technical audiences
- **Let people break things** — wrong queries, missing data, auth errors are all learning moments
- **End with "Ship It"** — showing M365 deployment makes the journey feel complete
