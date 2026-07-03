from flask import Flask
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Import routes
from routes import api_routes

@app.route('/')
def index():
    return {'message': 'Welcome to Scrum API'}

if __name__ == '__main__':
    app.run(debug=True)
