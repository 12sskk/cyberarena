# CyberArena ⚡

> **A self-hosted, lightweight Capture-The-Flag (CTF) platform built for labs, workshops, and friendly hacker duels.**
> Featuring on-demand Dockerized challenges, a shared-container architecture, live presence telemetry, and a dark CRT/terminal vibe.

---

## Why we built this

Most self-hosted CTF setups usually fall into two traps:
1. **They eat up all your system RAM:** If 15 people in a classroom or workshop click "Start Challenge", a traditional platform spawns 15 separate Docker containers of the exact same challenge on 15 random ports. Your host laptop or small VPS immediately chokes.
2. **Or they are entirely static:** Challenges don't actually run real services, leaving players clicking through mock screens instead of inspecting real HTTP headers, cookies, query strings, and processes.

**CyberArena fixes this with shared on-demand challenge instances.**

When the first player opens a challenge, CyberArena builds and spins up a single Docker container for that challenge. When other players jump into that same challenge, they are routed to the **exact same running container**. They share the live environment, see other active operators in real time, and can cooperatively solve (or race for First Blood!) without thrashing the host's memory.

---

## Features

- 🐳 **On-Demand Shared Docker Engine:** Containers stay idle until someone actually wants to play them. Once started, all players working on that challenge share the instance.
- 🔄 **Graceful Hybrid Fallback:** If you're developing locally on a laptop without the Docker daemon running, CyberArena automatically falls back to an isolated shared background process so you can test all 18 challenges without friction.
- 🎯 **18 Handcrafted Challenges:** Replaced the old static archive dumps with 18 distinct, interactive challenges covering web logic, API exploration, cache poisoning, cryptography, forensics, reverse engineering, and protocol desyncs.
- 📺 **CRT / Cyber Terminal UI:** Styled with phosphor green `#39ff88`, scanline overlays, glitch typography, and clean terminal panels inspired by classic hacking consoles.
- 🩸 **First Blood & Live Standings:** Tracks real-time solves, bonus points for first bloods, and an interactive leaderboard with a live fleet event feed.
- 🛡️ **Zero Pre-Filled Answers:** Every challenge is a real multi-route mini-site where players have to inspect elements, read cookies, trace diffs, and construct inputs themselves.

---

## The 18 Challenges

| # | Challenge Name | Category | Difficulty | Target Port | Concept / Core Mechanic |
|---|----------------|----------|------------|-------------|-------------------------|
| 01 | **Chrono-Vault Sync** | Timing & Logic | Easy | `:5101` | Clock synchronization & diagnostic header inspection |
| 02 | **Quantum Ledger** | Financial Logic | Easy | `:5102` | Handling unexpected transfer inputs to acquire credits |
| 03 | **Sentinel Core Directives** | Guardrails & Logic | Easy | `:5103` | Inspecting DOM parameters & auditing override directives |
| 04 | **Astral Passports** | Auth & Encoding | Easy | `:5104` | Session cookie decoding and clearance privilege editing |
| 05 | **Schema Introspection Lab** | API Architecture | Medium | `:5105` | GraphQL introspection & unearthing hidden schema fields |
| 06 | **Virtual Manifest Resolver** | Path Traversal | Medium | `:5106` | Bypassing single-pass string sanitization filters |
| 07 | **Edge Cache Mirage** | Web Caching | Medium | `:5107` | Unkeyed header handling and shared edge cache poisoning |
| 08 | **Bitwise Reactor Gates** | Reverse Engineering | Medium | `:5108` | C firmware analysis, bit shifts, and register constraints |
| 09 | **Telemetry Batch Parser** | Protocol Parsing | Medium | `:5109` | Front-end validator vs back-end batch execution desync |
| 10 | **Subnet Relay Loopback** | Network / SSRF | Medium | `:5110` | Alternate loopback IP representations (`127.0.0.2`, `0.0.0.0`) |
| 11 | **YAML/JSON Config Duel** | Parser Differentials | Medium | `:5111` | Regex linter vs native parser duplicate-key precedence |
| 12 | **Deep Space LFSR Stream** | Cryptography | Medium | `:5112` | Known-plaintext XOR recovery from stream radio headers |
| 13 | **Concurrency Escrow** | State & Concurrency | Hard | `:5113` | Dual-key pulse synchronization within a shared time window |
| 14 | **Formula Evaluator AST** | Code Analysis | Hard | `:5114` | Abstract Syntax Tree evaluation and object attribute access |
| 15 | **Commit History Forensics** | Forensics | Easy | `:5115` | Exploring historical git commit diffs for leaked secrets |
| 16 | **Bytecode Matrix Verifier** | Reverse Engineering | Hard | `:5116` | Stack-machine instruction disassembly and arithmetic trace |
| 17 | **Event-Sourced State Replay**| Distributed Systems | Hard | `:5117` | Sequence ID ordering in append-only event projection streams |
| 18 | **Modular Arithmetic Graph** | Applied Math & Crypto| Hard | `:5118` | Modular multiplicative inverse calculations |

---

## Getting Started

### Prerequisites

- Python 3.10+ (or Docker / Docker Desktop if running containerized)

---

### Option A: Running Directly with Python (Recommended for Local Dev)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/12sskk/cyberarena.git
   cd cyberarena
   ```

2. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Generate challenge contexts:**
   ```bash
   python generate_docker_challenges.py
   ```

4. **Launch the server:**
   ```bash
   python app.py
   ```

5. **Open your browser:**
   Navigate to [http://localhost:5000](http://localhost:5000)

---

### Option B: Running with Docker Compose

If you have Docker installed and want the platform itself containerized:

```bash
docker compose up --build
```

The platform mounts the host Docker socket (`/var/run/docker.sock`), allowing it to build and manage sibling challenge containers dynamically when users request them.

---

## Default Accounts

For quick local testing and trying out multi-user container sharing across different browser sessions/incognito tabs:

| Callsign | Passkey | Role |
|----------|---------|------|
| `admin`  | `admin123` | Default Operator |
| `alice`  | `alice123` | Second Operator |
| `bob`    | `bob123`   | Third Operator |

*(You can also click **Register here** on the login terminal to create any custom callsign on the spot).*

---

## How It Works Under The Hood

```
   [ Player 1 ]        [ Player 2 ]        [ Player 3 ]
        \                   |                   /
         \                  |                  /
          ▼                 ▼                 ▼
   +-------------------------------------------------+
   |              CyberArena Web Hub                 |
   |           (Flask / SQLite / REST API)           |
   +-------------------------------------------------+
                            |
               SharedDockerOrchestrator
             (Per-Challenge Lock + Registry)
                            |
                            ▼
        Does container 'cyberarena-shared-<id>' exist?
           /                                   \
      [ NO ]                                  [ YES ]
         |                                       |
  Build & Run Docker Container                   |
  Port 5101..5118                                |
         |                                       |
         +-------------------+-------------------+
                             |
                             ▼
              Attach all players to the SAME
                 shared running container!
```

1. **Locking & Thread Safety:** Every challenge ID has a dedicated mutex lock. If multiple players hit "Launch" at the exact same millisecond, only one container is provisioned.
2. **Shared Presence:** The orchestrator maintains an active registry of who is connected to which container, rendering live badges on the dashboard.
3. **Container Recycling & Control:** Operators can restart a container if they need a clean state, or terminate it when finished.

---

## Project Structure

```
CyberArena/
├── app.py                         # Main platform server & API endpoints
├── orchestrator.py                # Shared Docker orchestrator & process manager
├── challenges_registry.py         # Metadata, points, ports & flags for all 18 challenges
├── challenge_engine.py            # Microservice logic powering the challenge mini-apps
├── generate_docker_challenges.py  # Automation script generating standalone Docker contexts
├── Dockerfile                     # Root platform Dockerfile
├── docker-compose.yml             # Compose file for platform & sibling container socket
├── requirements.txt               # Platform Python dependencies
├── LICENSE                        # MIT License
├── templates/
│   ├── login.html                 # CRT Auth Terminal & animated ticker
│   └── dashboard.html             # Main dashboard, challenge selector & module views
├── static/
│   └── style.css                  # Retro-futuristic CRT scanline & terminal stylesheet
├── challenges/                    # Generated standalone Docker build contexts
│   ├── chrono-vault/
│   ├── quantum-ledger/
│   └── ... (18 challenge directories)
└── frontend/                      # Optional React frontend client (Vite)
```

---

## Contributing

Pull requests are always welcome! If you want to design a new challenge, add a category, or refine the terminal aesthetic:
1. Fork the repo.
2. Add your challenge to `challenges_registry.py` and `challenge_engine.py`.
3. Run `python generate_docker_challenges.py` to regenerate the Dockerfiles.
4. Open a PR with a description of the vulnerability and solution path.

---

## License

This project is licensed under the [MIT License](LICENSE).
Feel free to use it for university workshops, security clubs, corporate training, or personal CTF practice!
