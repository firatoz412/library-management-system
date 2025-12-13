from flask import Flask,render_template,flash,redirect,session,url_for
import os 
from dotenv import load_dotenv


from routes.book import book_bp
from routes.auth import auth_bp


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

load_dotenv()
app.secret_key = os.getenv("SECRET_KEY")

app.register_blueprint(book_bp)
app.register_blueprint(auth_bp)



@app.route("/")
def index():
    if "user_id" not in session:
            flash("Bu sayfaya erişmek için giriş yapmalısınız.", "warning")
            return redirect(url_for("auth.login"))
    return render_template("index.html")
    


if __name__ == '__main__':
    app.run(debug=True, port=5000)