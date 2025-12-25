from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import Error
from config.database import getDatabase

auth_bp = Blueprint("auth", __name__)


#kayıt olma
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    
    if "user_id" in session:
        if request.is_json:
            return jsonify({"success": False, "message": "Zaten giriş yapmışsınız."}), 400
        return redirect(url_for("index"))
    
    if request.method == "POST":
        if request.is_json:
            try:
                data = request.get_json()
                if data is None:
                    return jsonify({"success": False, "message": "Geçersiz JSON formatı"}), 400
            except Exception as e:
                return jsonify({"success": False, "message": f"JSON parse hatası: {str(e)}"}), 400
            
            name = data.get("name", "").strip() if data.get("name") else ""
            surename = data.get("surename", "").strip() if data.get("surename") else ""
            username = data.get("username", "").strip() if data.get("username") else ""
            email = data.get("email", "").strip() if data.get("email") else ""
            password = data.get("password", "").strip() if data.get("password") else ""
            passwordConfirm = data.get("passwordConfirm", "").strip() if data.get("passwordConfirm") else ""
            is_json_request = True
        else:
            name = request.form.get("name", "").strip()
            surename = request.form.get("surename", "").strip()
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()
            passwordConfirm = request.form.get("passwordConfirm", "").strip()
            is_json_request = False


        if not all([name, surename, username, email, password, passwordConfirm]):
            if is_json_request:
                missing_fields = []
                if not name: missing_fields.append("name")
                if not surename: missing_fields.append("surename")
                if not username: missing_fields.append("username")
                if not email: missing_fields.append("email")
                if not password: missing_fields.append("password")
                if not passwordConfirm: missing_fields.append("passwordConfirm")
                return jsonify({
                    "success": False, 
                    "message": "Tüm zorunlu alanları doldurunuz!",
                    "missing_fields": missing_fields
                }), 400
            flash("Tüm zorunlu alanları doldurunuz!", "error")
            return render_template("register.html")

        if password != passwordConfirm:
            if is_json_request:
                return jsonify({"success": False, "message": "Şifre alanları eşleşmiyor."}), 400
            flash("Şifre alanları eşleşmiyor.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            if is_json_request:
                return jsonify({"success": False, "message": "Şifre en az 6 karakter olmalıdır!"}), 400
            flash("Şifre en az 6 karakter olmalıdır!", "danger")
            return render_template("register.html")

        connection = getDatabase()
        if connection is None:
            if is_json_request:
                return jsonify({"success": False, "message": "Veri tabanı bağlantısı kurulamadı."}), 500
            flash("Veri tabanı bağlantısı kurulamadı.", "error")
            return render_template("register.html")
        
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
            user = cursor.fetchone()

            if user:
                if is_json_request:
                    return jsonify({"success": False, "message": "Bu E-posta veya kullanıcı adı daha önce alınmış!"}), 409
                flash("Bu E-posta veya kullanıcı adı daha önce alınmış!", "danger")
                return render_template("register.html")

            hashedPassword = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (name, surename, username, email, password, role) VALUES (%s, %s, %s, %s, %s, %s)",
                (name, surename, username, email, hashedPassword, "student")
            )
            connection.commit()
            
            if is_json_request:
                return jsonify({
                    "success": True, 
                    "message": "Kayıt başarılı.",
                    "data": {
                        "username": username,
                        "email": email,
                        "name": name,
                        "surename": surename
                    }
                }), 201
            
            flash("Kayıt Başarılı.", "success")
            return redirect(url_for("auth.login"))

        except Error as e:
            print(f"Kayıt Olunamadı: {e}")
            if is_json_request:
                return jsonify({"success": False, "message": "Kayıt olunamadı. Lütfen tekrar deneyin."}), 500
            flash("Kayıt Olunamadı.", "danger")
            return render_template("egister.html")
        finally:
            cursor.close()
            connection.close()

    return render_template("register.html")

# giriş
@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    is_admin_login = request.args.get("admin") == "1"  

    if request.method == "POST":

        if request.is_json:
            data = request.get_json()
            username = data.get("username", "").strip()
            password = data.get("password", "").strip()
        else:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

        if not username or not password:
            message = "Kullanıcı adınızı ve şifrenizi girmelisiniz!"
            if request.is_json:
                return jsonify({"error": message}), 400
            flash(message, "warning")
            return redirect(url_for("auth.login"))

        connection = getDatabase()
        if connection is None:
            error_msg = "Veritabanı bağlantı hatası."
            if request.is_json:
                return jsonify({"error": error_msg}), 500
            flash(error_msg, "danger")
            return redirect(url_for("auth.login"))

        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            if user and check_password_hash(user["password"], password):

                if is_admin_login and user["role"] != "admin":
                    message = "Bu giriş yalnızca adminler içindir."
                    if request.is_json:
                        return jsonify({"error": message}), 403
                    flash(message, "danger")
                    return redirect(url_for("auth.login"))

            
                session["user_id"] = user["id"]
                session["email"] = user["email"]
                session["user"] = user["username"]
                session["name"] = user["name"]
                session["surename"] = user["surename"]
                session["role"] = user["role"]

                
                if request.is_json:
                    return jsonify({
                        "message": "Giriş başarılı!",
                        "user": {
                            "id": user["id"],
                            "username": user["username"],
                            "email": user["email"],
                            "name": user["name"],
                            "surename": user["surename"],
                            "role": user["role"]
                        }
                    }), 200

            
                if is_admin_login and user["role"] == "admin":
                    return redirect(url_for("admin.adminPanel"))

                return redirect(url_for("index"))

            else:
                message = "Kullanıcı adı veya şifre hatalı!"
                if request.is_json:
                    return jsonify({"error": message}), 401
                flash(message, "danger")

        except Error as e:
            print("Giriş hatası:", e)
            error_msg = "Giriş yapılamadı!"
            if request.is_json:
                return jsonify({"error": error_msg}), 500
            flash(error_msg, "danger")

        finally:
            cursor.close()
            connection.close()

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Çıkış yapıldı.", "success")
    return redirect(url_for("index"))