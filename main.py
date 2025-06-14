from app import create_app
import os, logging

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s — %(message)s")

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logging.info("Starting TrendWave on port %s", port)
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
