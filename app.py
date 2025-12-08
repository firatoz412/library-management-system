from flask import Flask,render_template
#import os

from routes.book import book_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'busecretkeycokgizli'

app.register_blueprint(book_bp)



@app.route("/")
def index():
    return render_template("index.html")
    



if __name__ == '__main__':
    app.run(debug=True, port=5000)