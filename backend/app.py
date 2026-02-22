import os
from flask import Flask, render_template, send_from_directory, jsonify
from flask_cors import CORS
from backend.models import db
import traceback

def create_app(test_config=None):
    # Setup paths for frontend templates and static files
    base_dir = os.path.abspath(os.path.dirname(__file__))
    project_dir = os.path.dirname(base_dir)
    template_dir = os.path.join(project_dir, 'frontend', 'templates')
    static_dir = os.path.join(project_dir, 'frontend', 'static')

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    CORS(app) # Enable CORS for development flexibility

    # Configuration
    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(base_dir, 'meal_tracker_v2.sqlite')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.from_mapping(test_config)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints/routes
    from backend.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Serve Frontend
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/<path:path>')
    def static_proxy(path):
        return send_from_directory(static_dir, path)

    # Create DB tables
    with app.app_context():
        db.create_all()

    @app.errorhandler(Exception)
    def handle_exception(e):
        print(f"!!! [CRITICAL ERROR] !!!: {str(e)}", flush=True)
        traceback.print_exc()
        return jsonify({
            "error": "Internal Server Error",
            "details": str(e),
            "trace": traceback.format_exc()
        }), 500

    return app

if __name__ == '__main__':
    app = create_app()
    # Disable reloader on Pi to prevent "GPIO busy" errors from double-initialization
    use_reloader = os.getenv("USE_REAL_HARDWARE", "false").lower() != "true"
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=use_reloader)
