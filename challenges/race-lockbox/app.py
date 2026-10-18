import os
from challenge_engine import create_challenge_app

app = create_challenge_app("race-lockbox")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
