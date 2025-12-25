from mysql.connector import Error
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, session
from config.database import getDatabase
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import datetime

admin_bp = Blueprint("admin", __name__)


def admin_control():
    if 'user_id' not in session:
        flash('Bu sayfayı görüntülemek için giriş yapmalısınız.', 'warning')
        return redirect(url_for('auth.login'))

    if session.get('role') != 'admin':
        flash('Bu sayfaya erişim yetkiniz yok!', 'danger')
        return redirect(url_for('index'))

    return None


@admin_bp.route("/adminIndex")
def adminIndex():
    if 'user_id' not in session:
        flash('Bu sayfayı görüntülemek için giriş yapmalısınız.', 'warning')
        return redirect(url_for('auth.login'))

    if session.get('role') != 'admin':
        flash('Bu sayfaya erişim yetkiniz yok!', 'danger')
        print("bu sayfaya sadece adminler giriş yapabilir")
        return redirect(url_for('index'))
    return render_template("adminIndex.html")



@admin_bp.route("/adminPanel")  
def adminPanel():
    if 'user_id' not in session:
        flash('Bu sayfayı görüntülemek için giriş yapmalısınız.', 'warning')
        return redirect(url_for('auth.login'))

    if session.get('role') != 'admin':
        flash('Bu sayfaya erişim yetkiniz yok!', 'danger')
        print("bu sayfaya sadece adminler giriş yapabilir")
        return redirect(url_for('index'))
    
    return render_template("adminPanel.html")




@admin_bp.route("/adminLogin", methods=['GET', 'POST'])
def adminLogin():
    if session.get('role') == 'admin':
        if request.is_json:
            return jsonify({"success": True, "message": "Zaten giriş yapılmış"}),200
        return redirect(url_for('admin.adminPanel'))

    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            user = data.get('username')
            password = data.get('password')
        else:
            user = request.form.get('username')
            password = request.form.get('password')

        connection = getDatabase()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (user,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if user and check_password_hash(user['password'], password):
            

            if user['role'] == 'admin':
                session['user_id'] = user['id']
                session['role'] = 'admin'
            
                if request.is_json:
                    return jsonify({
                        "success": True,
                        "message": "Yönetici girişi başarılı",
                        "user": {
                            "id": user['id'],
                            "username": user['username'],
                            "email": user['email'],
                            "role": user['role']
                        }
                    }),200
                
                flash("Yönetici girişi başarılı.", "success")
                return redirect(url_for('admin.adminPanel'))
            
            elif user['role'] == 'student':
                if request.is_json:
                    return jsonify({
                        "success": False,
                        "message": "Öğrenci hesabı ile admin girişi yapılamaz!"
                    }),403
         
                flash("Öğrenci hesabı ile admin girişi yapılamaz!", "danger")
                return redirect(url_for('auth.login'))
        
        else:
            if request.is_json:
                return jsonify({
                    "success": False,
                    "message": "Kullanıcı adı veya şifre hatalı!"
                }), 401
            
            flash("Kullanıcı adı veya şifre hatalı!", "danger")
            return redirect(url_for('admin.adminLogin'))
        
    return render_template("adminLogin.html")



@admin_bp.route("/adminRegister", methods=["GET", "POST"])
def adminRegister():

    is_admin_register = request.args.get("admin") == "1"

    if "user_id" in session and not is_admin_register and not request.is_json:
        return redirect(url_for("index"))

    if request.method == "POST":

        if request.is_json:
            data = request.get_json()
            name = data.get("name", "").strip()
            surename = data.get("surename", "").strip()
            username = data.get("username", "").strip()
            email = data.get("email", "").strip()
            password = data.get("password", "").strip()
            passwordConfirm = data.get("passwordConfirm", "").strip()
        else:
            name = request.form.get("name", "").strip()
            surename = request.form.get("surename", "").strip()
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()
            passwordConfirm = request.form.get("passwordConfirm", "").strip()

        if not all([name, surename, username, email, password, passwordConfirm]):
            msg = "Tüm alanları doldurunuz!"
            if request.is_json:
                return jsonify({"error": msg}), 400
            flash(msg, "danger")
            return render_template("register.html")

        if password != passwordConfirm:
            msg = "Şifreler uyuşmuyor!"
            if request.is_json:
                return jsonify({"error": msg}), 400
            flash(msg, "danger")
            return render_template("register.html")

        if len(password) < 6:
            msg = "Şifre en az 6 karakter olmalıdır!"
            if request.is_json:
                return jsonify({"error": msg}), 400
            flash(msg, "danger")
            return render_template("register.html")

        connection = getDatabase()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT id FROM users WHERE username = %s OR email = %s",
                (username, email)
            )
            if cursor.fetchone():
                msg = "Bu kullanıcı adı veya e-posta zaten kayıtlı!"
                if request.is_json:
                    return jsonify({"error": msg}), 409
                flash(msg, "danger")
                return render_template("register.html")

            hashedPassword = generate_password_hash(password)

            role = "admin" if is_admin_register else "student"

            cursor.execute("""
                INSERT INTO users (name, surename, username, email, password, role)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, surename, username, email, hashedPassword, role))

            connection.commit()

            if request.is_json:
                return jsonify({
                    "message": "Kayıt başarılı",
                    "role": role
                }), 201

            flash("Kayıt başarılı!", "success")

            if is_admin_register:
                return redirect(url_for("admin.adminPanel"))
            return redirect(url_for("admin.adminLogin"))

        except Error as e:
            connection.rollback()
            print("Register hata:", e)
            flash("Kayıt sırasında hata oluştu", "danger")

        finally:
            cursor.close()
            connection.close()

    return render_template("adminRegister.html", is_admin_register=is_admin_register)





@admin_bp.route("/userList")
def userList():
    
    connection = getDatabase()
    cursor = connection.cursor(dictionary=True)  
    
    cursor.execute("""
        SELECT id, name, surename, username, email, role, created_at 
        FROM users
    """)
    users = cursor.fetchall()
    
    cursor.close()
    connection.close()
 
    if request.headers.get('Content-Type') == 'application/json' or request.headers.get('Accept') == 'application/json':
        return jsonify({
            "success": True,
            "data": users,
            "count": len(users)
        })
    return render_template("userList.html", users=users)


@admin_bp.route("/penalties")
def list_penalties():
    connection = getDatabase()
    cursor = connection.cursor(dictionary=True)
    

    cursor.execute(
         """
            SELECT p.*, u.username, u.email, b.title 
            FROM penalties p
            JOIN users u ON p.user_id = u.id
            JOIN borrowed_books bb ON p.borrow_id = bb.id
            JOIN book b ON bb.book_id = b.book_id
            ORDER BY p.penalty_start_date DESC
        """
    )
    
    penalties = cursor.fetchall()
    
    now = datetime.now()
    
    cursor.close()
    connection.close()
    return render_template("penaltiesList.html", penalties=penalties,now=now)





