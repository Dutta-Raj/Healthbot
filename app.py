import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

# Initialize Flask app
app = Flask(__name__)

# --- Database Configuration ---
# Use an environment variable for the database path
db_path = os.environ.get("DATABASE_URL", "sqlite:///site.db")
app.config['SQLALCHEMY_DATABASE_URI'] = db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Model ---
# Defines the structure of the 'User' table
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

# --- Routes ---
# Home page: Displays a list of users and a form to add a new one
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Create a new user from form data
        username = request.form['username']
        email = request.form['email']
        new_user = User(username=username, email=email)
        try:
            # Add new user to the database
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('index'))
        except:
            return 'There was an issue adding the user.'
    
    # Retrieve all users from the database for display
    users = User.query.all()
    return render_template('index.html', users=users)

# --- Main entry point ---
if __name__ == '__main__':
    with app.app_context():
        # Create the database and tables if they don't exist
        db.create_all()
    app.run(debug=True)
