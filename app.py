from flask import Flask, render_template

# Create the Flask application
app = Flask(__name__)

# Home route
@app.route("/")
def home():
    return render_template("index.html")

# Optional: Add more routes if needed
@app.route("/about")
def about():
    return "<h1>About Page</h1><p>This is a sample about page.</p>"

# Entry point for Railway / local
if __name__ == "__main__":
    # Railway provides PORT as an environment variable
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
