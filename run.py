import os
from app import create_app, db
from init_db import seed_database

app = create_app()

if __name__ == '__main__':
    # Initialize the database and seed it automatically on startup
    # This makes the app immediately runnable out-of-the-box!
    seed_database(app)
    
    # Run the Flask development server
    # Host is set to 0.0.0.0 to enable access from docker or external devices if needed
    # Port defaults to 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
