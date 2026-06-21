from flask import Flask
from backend.api.routes import api_bp
from config import Config
import os

def create_app(config=Config):
    app = Flask(
        __name__,
        template_folder="frontend/templates",
        static_folder="frontend/static"
    )
    app.config.from_object(config)

    # Ensure temp dirs exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)

    app.register_blueprint(api_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
