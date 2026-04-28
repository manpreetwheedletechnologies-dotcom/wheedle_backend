from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
import os
from .db import mongo
from .config import MONGO_URI

# ─────────────────────────────────────────
#  SocketIO instance (created here, used everywhere)
# ─────────────────────────────────────────
socketio = SocketIO(cors_allowed_origins="*", async_mode="threading", logger=False, engineio_logger=False)


def create_app():
    app = Flask(__name__)

    app.config["MONGO_URI"] = MONGO_URI
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "wheedle_flask_secret")
    mongo.init_app(app)

    CORS(
        app,
        supports_credentials=True,
        resources={r"/*": {"origins": "*"}},
        allow_headers=["Content-Type", "Authorization", "x-api-key", "Accept"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        expose_headers=["Content-Type", "Authorization"],
    )

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, x-api-key, Accept"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        return response

    @app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
    @app.route('/<path:path>', methods=['OPTIONS'])
    def handle_options(path):
        from flask import Response
        return Response(status=200, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, x-api-key, Accept",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
        })

    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(os.path.join(app.root_path, '../uploads'), filename)

    @app.route('/py/api/uploads/<path:filename>')
    def serve_upload_pyapi(filename):
        return send_from_directory(os.path.join(app.root_path, '../uploads'), filename)

    # ── Import blueprints ──────────────────────────────────────────────────────
    from .routes.chat_routes import chat_bp
    from .routes.live_chat_routes import live_chat_bp   # ← NEW live-chat REST
    from .routes.auth_routes import auth_bp
    from .routes.blog_routes import blog_bp
    from .routes.job_routes import job_bp
    from .routes.partner_routes import partner_bp
    from .routes.contact_routes import contact_bp
    from .routes.testimonial_routes import testimonial_bp
    from .routes.hero_routes import hero_bp
    from .routes.step_routes import steps_bp
    from .routes.profile_routes import profile_bp
    from .routes.lead_routes import leads_bp
    from .routes.formlead_routes import formleads_bp
    from .routes.dashboard_routes import dashboard_bp

    # ── Register blueprints ────────────────────────────────────────────────────
    app.register_blueprint(chat_bp,          url_prefix="/py/api")
    app.register_blueprint(live_chat_bp,     url_prefix="/py/api/live")   # ← NEW
    app.register_blueprint(auth_bp,          url_prefix="/py/api/auth")
    app.register_blueprint(blog_bp,          url_prefix="/py/api/blogs")
    app.register_blueprint(job_bp,           url_prefix="/py/api/jobs")
    app.register_blueprint(contact_bp,       url_prefix="/py/api/contact")
    app.register_blueprint(testimonial_bp,   url_prefix="/py/api/testimonial")
    app.register_blueprint(hero_bp,          url_prefix="/py/api/hero")
    app.register_blueprint(partner_bp,       url_prefix="/py/api/partner")
    app.register_blueprint(steps_bp,         url_prefix="/py/api/steps")
    app.register_blueprint(profile_bp,       url_prefix="/py/api/profile")
    app.register_blueprint(leads_bp,         url_prefix="/py/api/leads")
    app.register_blueprint(formleads_bp,     url_prefix="/py/api/formleads")
    app.register_blueprint(dashboard_bp,     url_prefix="/py/api")

    # ── Register Socket.IO event handlers ─────────────────────────────────────
    from .routes import live_chat_socket   # noqa: F401  (registers @socketio.on handlers)

    # ── Attach SocketIO to app ─────────────────────────────────────────────────
    socketio.init_app(app)

    return app
