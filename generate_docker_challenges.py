"""
Generates standalone Docker build contexts in challenges/<challenge_id>/ for all 18 challenges.
"""
import os
import shutil
from challenges_registry import CHALLENGES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHALLENGES_DIR = os.path.join(BASE_DIR, "challenges")


def main():
    os.makedirs(CHALLENGES_DIR, exist_ok=True)
    for cid, meta in CHALLENGES.items():
        cdir = os.path.join(CHALLENGES_DIR, cid)
        os.makedirs(cdir, exist_ok=True)

        # Copy engine and registry so each challenge folder is a self-contained Docker build context
        shutil.copy2(os.path.join(BASE_DIR, "challenges_registry.py"), os.path.join(cdir, "challenges_registry.py"))
        shutil.copy2(os.path.join(BASE_DIR, "challenge_engine.py"), os.path.join(cdir, "challenge_engine.py"))

        with open(os.path.join(cdir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("flask>=3.0.0\n")

        with open(os.path.join(cdir, "app.py"), "w", encoding="utf-8") as f:
            f.write(
                f'import os\n'
                f'from challenge_engine import create_challenge_app\n\n'
                f'app = create_challenge_app("{cid}")\n\n'
                f'if __name__ == "__main__":\n'
                f'    port = int(os.environ.get("PORT", "5000"))\n'
                f'    app.run(host="0.0.0.0", port=port)\n'
            )

        with open(os.path.join(cdir, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write(
                f"# Auto-generated Dockerfile for CyberArena Shared Challenge: {meta['title']}\n"
                f"FROM python:3.11-slim\n"
                f"WORKDIR /app\n"
                f"COPY requirements.txt .\n"
                f"RUN pip install --no-cache-dir -r requirements.txt\n"
                f"COPY . .\n"
                f"ENV CHALLENGE_ID={cid}\n"
                f"ENV PORT=5000\n"
                f"EXPOSE 5000\n"
                f'CMD ["python", "app.py"]\n'
            )

    print(f"Generated {len(CHALLENGES)} Docker challenge contexts in {CHALLENGES_DIR}")


if __name__ == "__main__":
    main()
