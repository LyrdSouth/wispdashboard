from flask import Flask, session
from dashboard.routes import dashboard
import os

app = Flask(__name__)

# Set up Flask secret key from environment variable
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

# Register blueprints
app.register_blueprint(dashboard, url_prefix='/dashboard')

if __name__ == '__main__':
    app.run(debug=True) 