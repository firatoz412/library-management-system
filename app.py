from flask import Flask,render_template
import os 
from dotenv import load_dotenv


from routes.book import book_bp
from routes.auth import auth_bp
from routes.admin import admin_bp

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

load_dotenv()
app.secret_key = os.getenv("SECRET_KEY")

app.register_blueprint(book_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)



@app.route("/")
def index():
    return render_template("index.html")
    

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    
    