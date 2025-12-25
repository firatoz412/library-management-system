from flask import Blueprint, request, jsonify,render_template,redirect,url_for,session,flash
from mysql.connector import Error
from config.database import getDatabase
import smtplib,os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

book_bp = Blueprint("books", __name__)

#kitap listeleme
@book_bp.route("/books", methods=["GET"])
def list_books():
        
    connection = getDatabase()
    if connection is None:
        error_msg = "Veri tabanı bağlantısı kurulamadı."
        if request.headers.get('Accept') == 'application/json':
            return jsonify({"error": error_msg}), 500
        return render_template("index.html", error=error_msg)
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM book")
        books = cursor.fetchall()
        
        if not books:
            message = "Kayıtlı kitap bulunamadı"
            if request.headers.get('Accept') == 'application/json':
                return jsonify({"message": message, "books": []}), 200
            return render_template("books.html", books=[], message=message)
        
        if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({"books": books}), 200
        
        return render_template("books.html", books=books)
    
    except Error as e:
        print(f"Hata oluştu: {e}")
        error_msg = "Kitaplar listelenirken bir hata oluştu."
        if request.headers.get('Accept') == 'application/json':
            return jsonify({"error": error_msg}), 500
        return render_template("books.html", error=error_msg)
    
    finally:
        cursor.close()
        connection.close()


#Kitap ekleme
@book_bp.route("/addBook", methods=['GET','POST'])
def addBook():
    
    if "user_id" not in session:
        if request.is_json:
            return jsonify({"error": "Bu sayfaya erişmek için giriş yapmalısınız."}), 401
        flash("Bu sayfaya erişmek için giriş yapmalısınız.", "warning")
        return redirect(url_for("auth.login"))

    if session.get('role') != 'admin':
        flash('Bu sayfaya erişim yetkiniz yok!', 'danger')
        print("bu sayfaya sadece adminler giriş yapabilir")
        return redirect(url_for('index'))
        
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            title = data.get("title")
            author_name = data.get("author_name")
            category_name = data.get("category_name")
            isbn = data.get("isbn")
            publish_year = data.get("publish_year")
            description = data.get("description")
            if not description:
                description = "açıklama yok"
        
        else:
            title = request.form["title"]
            author_name = request.form["author_name"]
            category_name = request.form["category_name"]
            isbn = request.form["isbn"]
            publish_year = request.form["publish_year"]
            description = request.form.get("description", "").strip() or "açıklama yok"
        
        
        if not all([title, author_name, category_name, isbn, publish_year]):
            message = "Lütfen tüm zorunlu alanları doldurun."
            if request.is_json:
                return jsonify({"error": message}), 400
            else:
                return render_template("addBook.html", 
                                 message=message,
                                 form_data=request.form)
    
        connection = getDatabase()
        if connection is None:
            error_msg = "Veri tabanı bağlantısı kurulamadı."
            if request.is_json:
                return jsonify({"error": error_msg}), 500
            return render_template("addBook.html", error=error_msg)
        
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM book WHERE isbn = %s", (isbn,))
            isbn_control = cursor.fetchone()
            
            if isbn_control:
                message = "Bu ISBN numarası başka bir kitaba aittir."
                if request.is_json:
                    return jsonify({"error": message}), 409
                else:
                    return render_template("addBook.html", message=message)
            
            cursor.execute("INSERT INTO book (title, author_name, category_name, isbn, publish_year, description) VALUES (%s, %s, %s, %s, %s, %s)",
                      (title, author_name, category_name, isbn, publish_year, description))
            connection.commit()
            
            cursor.execute("SELECT * FROM book WHERE isbn = %s", (isbn,))
            inserted_book = cursor.fetchone()
            
            if request.is_json:
                return jsonify({
                    "message": "Kitap başarıyla eklendi!",
                    "book": inserted_book
                }), 201
            else:
                flash(f"'{title}' başlıklı kitap başarıyla eklendi.", "success")
                return redirect(url_for("books.list_books"))
                
        except Error as e:
            connection.rollback()
            print(f"Hata oluştu: {e}")
            error_msg = "Kitap eklenirken bir hata oluştu."
            if request.is_json:
                return jsonify({"error": error_msg}), 500
            return render_template("addBook.html", error=error_msg)
        finally:
            cursor.close()
            connection.close()
            
    return render_template("addBook.html")


#kitap silme
@book_bp.route("/deleteBook", methods=['GET', 'POST'])
def deleteBook():

    if "user_id" not in session:
        if request.is_json:
            return jsonify({"error": "Bu sayfaya erişmek için giriş yapmalısınız."}), 401
        flash("Bu sayfaya erişmek için giriş yapmalısınız.", "warning")
        return redirect(url_for("auth.login"))
    
    if session.get('role') != 'admin':
        flash('Bu sayfaya erişim yetkiniz yok!', 'danger')
        print("bu sayfaya sadece adminler giriş yapabilir")
        return redirect(url_for('index'))
    
        
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            isbn = data.get("isbn")
        else:
            isbn = request.form.get("isbn")

        if not isbn:
            message = "Kaydı silinecek kitabın ISBN numarası girilmelidir!"
            if request.is_json:
                return jsonify({"error": message}), 400
            return render_template("deleteBook.html", Warning=message)
            
        if not isbn.isdigit():
            message = "Silinecek kitabın ISBN numarası rakamlardan oluşmalı."
            if request.is_json:
                return jsonify({"error": message}), 400
            return render_template("deleteBook.html", error=message) 

        connection = getDatabase()
        if connection is None:
            error_msg = "Veri tabanı bağlantısı kurulamadı."
            if request.is_json:
                return jsonify({"error": error_msg}), 500
            return render_template("deleteBook.html", error=error_msg)
        
        cursor = connection.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT * FROM book WHERE isbn = %s", (isbn,))
            book = cursor.fetchone()
            
            if not book:
                cursor.close()
                connection.close()
                message = "Bu ISBN numarasına sahip kitap bulunamadı!"
                if request.is_json:
                    return jsonify({"error": message}), 404
                return render_template("deleteBook.html", message=message)

            cursor.execute("DELETE FROM book WHERE isbn = %s", (isbn,))
            
            if cursor.rowcount > 0:
                connection.commit()
                if request.is_json:
                    return jsonify({
                        "message": "Kitap başarıyla silindi!",
                        "deleted_book": book
                    }), 200
                else:
                    flash(f"'{book['title']}' başlıklı kitap başarıyla silindi.", "success")
                    return redirect(url_for("books.list_books"))
            else:
                message = "Silme işlemi başarısız oldu!"
                if request.is_json:
                    return jsonify({"error": message}), 500
                return render_template("deleteBook.html", message=message)

        except Error as e:
            connection.rollback()
            print(f"Hata oluştu: {e}")
            error_msg = "Kitap silinirken hata oluştu."
            if request.is_json:
                return jsonify({"error": error_msg}), 500
            return render_template("deleteBook.html", error=error_msg)

        finally:
            cursor.close()
            connection.close()

    return render_template("deleteBook.html")


#Kitap bilgilerini gösterme(bir kitap)
@book_bp.route("/bookInfo/<int:id>")
def bookInfo(id):
         
    connection = getDatabase()
    if connection is None:
        error_msg = "Veri tabanı bağlantısı kurulamadı."
        if request.is_json or request.args.get('format') == 'json':
            return jsonify({"error": error_msg}), 500
        return render_template("bookInfo.html", error=error_msg)
    
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM book WHERE book_id = %s", (id,))
        book = cursor.fetchone()
          
        if book:
            if request.is_json or request.args.get('format') == 'json':
                return jsonify({
                    "message": "Kitap bulundu",
                    "book": book
                }), 200
            return render_template("bookInfo.html", books=book)
        else:
            message = f"ID {id} numaralı kitap bulunamadı."
            if request.is_json or request.args.get('format') == 'json':
                return jsonify({"error": message}), 404
            return render_template("bookInfo.html", message=message)
        
    except Error as e:
        print(f"Hata oluştu: {e}")
        error_msg = "Kitap bilgileri bulunamadı."
        if request.is_json or request.args.get('format') == 'json':
            return jsonify({"error": error_msg}), 500
        return render_template("bookInfo.html", error=error_msg)
    finally:
        cursor.close()
        connection.close()


#kitap arama
@book_bp.route("/bookSearch", methods=["GET", "POST"])
def bookSearch():
    
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            isbn = data.get("isbn")
        else:   
            isbn = request.form.get("isbn")
        
        if not isbn:
            message = "Lütfen kitap ISBN numarasını giriniz."
            if request.is_json:
                return jsonify({"error": message}), 400
            return render_template("bookSearch.html", error=message)

        connection = getDatabase()
        if connection is None:
            error_msg = "Veri tabanı bağlantısı kurulamadı."
            if request.is_json:
                return jsonify({"error": error_msg}), 500
            return render_template("bookSearch.html", error=error_msg)
        
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM book WHERE isbn = %s", (isbn,))
            book = cursor.fetchone()
            
            if book:
                print(f"Bulunan kitap: {book}")
                if request.is_json:
                    return jsonify({
                        "message": "Kitap bulundu",
                        "book": book
                    }), 200
                else:
                    return render_template("bookInfo.html", books=book)
            else:
                message = f" {isbn} isbn numaralı kitap bulunamadı."
                if request.is_json:
                    return jsonify({"error": message}), 404
                return render_template("bookSearch.html", hata=message)
                
        except Error as e:
            print(f"Arama hatası: {e}")
            error_msg = "Kitap aranırken hata oluştu."
            if request.is_json:
                return jsonify({"error": error_msg}), 500
            return render_template("bookSearch.html", error=error_msg)
        finally:
            cursor.close()
            connection.close()

    return render_template("bookSearch.html")

#Kitap güncelleme
@book_bp.route("/bookUpdate/<int:id>", methods=['GET', 'POST'])
def bookUpdate(id):

    if "user_id" not in session:
        if request.is_json or request.args.get('format') == 'json':
            return jsonify({"error": "Bu sayfaya erişmek için giriş yapmalısınız."}), 401
        flash("Bu sayfaya erişmek için giriş yapmalısınız.", "warning")
        return redirect(url_for("auth.login"))
    
    if session.get('role') != 'admin':
        flash('Bu sayfaya erişim yetkiniz yok!', 'danger')
        print("bu sayfaya sadece adminler giriş yapabilir")
        return redirect(url_for('index'))
    
    connection = getDatabase()
    if connection is None:
        error_msg = "Veri tabanı bağlantısı kurulamadı."
        if request.is_json:
            return jsonify({"error": error_msg}), 500
        return render_template("bookUpdate.html", error=error_msg)
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM book WHERE book_id = %s", (id,))  
        book = cursor.fetchone()
        
        if not book:
            message = f"ID {id} numaralı kitap bulunamadı."
            if request.is_json:
                return jsonify({"error": message}), 404
            return render_template("bookUpdate.html", error=message), 404
            
    except Error as e:
        print(f"Kitap bilgileri çekilemedi: {e}")
        cursor.close()
        connection.close()
        error_msg = "Kitap bilgileri bulunamadı."
        if request.is_json:
            return jsonify({"error": error_msg}), 500
        return render_template("bookUpdate.html", error=error_msg)
    
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            title = data.get("title") or book["title"]
            author_name = data.get("author_name") or book["author_name"]
            category_name = data.get("category_name") or book["category_name"]
            publish_year = data.get("publish_year") or book["publish_year"]
            description = data.get("description") or book["description"]
        else:
            title = request.form.get("title") or book["title"]
            author_name = request.form.get("author_name") or book["author_name"]
            category_name = request.form.get("category_name") or book["category_name"]
            publish_year = request.form.get("publish_year") or book["publish_year"]
            description = request.form.get("description") or book["description"]
        
        if not description:
            description = "Açıklama Yok"
        
        try:
            cursor.execute(
                "UPDATE book SET title=%s, author_name=%s, category_name=%s, publish_year=%s, description=%s WHERE book_id=%s",
                (title, author_name, category_name, publish_year, description, id))
            connection.commit()
            
            cursor.execute("SELECT * FROM book WHERE book_id = %s", (id,))
            updated_book = cursor.fetchone()
            
            if request.is_json:
                return jsonify({
                    "message": "Kitap başarıyla güncellendi!",
                    "book": updated_book
                }), 200
            else:
                flash("Kitap başarıyla güncellendi!", "success")
                return redirect(url_for("books.bookInfo", id=id))
                
        except Error as e:
            connection.rollback()
            print(f"Kitap güncelleme hatası: {e}")
            error_msg = "Kitap güncellenemedi."
            if request.is_json:
                return jsonify({"error": error_msg}), 500
            return render_template("bookUpdate.html", books=book, error=error_msg)
            
        finally:
            cursor.close()
            connection.close()
    
    cursor.close()
    connection.close()
    return render_template("bookUpdate.html", books=book)

#kitap ödünç alma
@book_bp.route("/borrowBook/<int:book_id>", methods=["GET", "POST"])
def borrowBook(book_id):
    if "user_id" not in session:
        if request.is_json or request.args.get('format') == 'json':
            return jsonify({"error": "Bu sayfaya erişmek için giriş yapmalısınız."}), 401
        flash("Bu sayfaya erişmek için giriş yapmalısınız.", "warning")
        return redirect(url_for("auth.login"))

    if request.is_json:
        data = request.get_json()
        user_id = data.get("user_id")
        email = data.get("email")
        if not user_id or not email:
            return jsonify({"error": "user_id ve email gereklidir."}), 400
    else:
        user_id = session.get("user_id")
        email = session.get("email")
    
    connection = getDatabase()
    if connection is None:
        error_msg = "Veri tabanı bağlantısı kurulamadı."
        if request.is_json: return jsonify({"error": error_msg}), 500
        flash(error_msg, "error")
        return redirect(url_for("books.list_books"))
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT penalty_end_date FROM penalties 
            WHERE user_id = %s AND penalty_end_date > NOW() 
            LIMIT 1
        """, (user_id,))
        active_penalty = cursor.fetchone()

        if active_penalty:
            penalty_time = active_penalty['penalty_end_date'].strftime('%H:%M:%S')
            message = f"Cezalı olduğunuz için kitap alamazsınız! Ceza bitişi: {penalty_time}"
            if request.is_json: return jsonify({"error": message}), 403
            flash(message, "danger")
            return redirect(url_for("books.list_books"))

        cursor.execute("SELECT * FROM book WHERE book_id = %s", (book_id,))
        book = cursor.fetchone()
        if not book:
            if request.is_json: return jsonify({"error": "Kitap bulunamadı"}), 404
            flash("Kitap bulunamadı.", "error")
            return redirect(url_for("books.list_books"))
    
        cursor.execute("SELECT * FROM borrowed_books WHERE book_id = %s AND is_returned = FALSE", (book_id,))
        if cursor.fetchone():
            flash(f"'{book['title']}' kitabı şu anda ödünç alınmış durumda.", "warning")
            return redirect(url_for("books.bookInfo", id=book_id))
        
        simdikizaman = datetime.now()
        teslim_tarihi = simdikizaman + timedelta(minutes=1) 

        cursor.execute("""
            INSERT INTO borrowed_books (user_id, book_id, borrow_date, due_date, is_returned)
            VALUES (%s, %s, %s, %s, FALSE)
        """, (user_id, book_id, simdikizaman, teslim_tarihi))
        
        connection.commit()

        try:
            send_borrow_mail_odunc(email=email, book_name=book['title'])
        except Exception as e:
            print(f"E-posta gönderme hatası: {e}")
        
        if request.is_json:
            return jsonify({"message": "Kitap başarıyla ödünç alındı!", "due_date": teslim_tarihi}), 201
        else:
            flash(f"'{book['title']}' kitabı ödünç alındı! 1 dakika içinde iade etmelisiniz.", "success")
            return redirect(url_for("books.list_books"))
    
    except Exception as e: 
        connection.rollback()
        print(f"Kitap ödünç alma hatası: {e}")
        if request.is_json: return jsonify({"error": str(e)}), 500
        flash("Kitap ödünç alınırken bir hata oluştu.", "error")
        return redirect(url_for("books.list_books"))
    
    finally:
        cursor.close()
        connection.close()
        
        
@book_bp.route("/returnBook/<int:book_id>", methods=["GET", "POST"])
def returnBook(book_id):
    if "user_id" not in session:
        if request.is_json or request.args.get("format") == "json":
            return jsonify({"error": "Bu sayfaya erişmek için giriş yapmalısınız."}), 401
        flash("Bu sayfaya erişmek için giriş yapmalısınız.", "warning")
        return redirect(url_for("auth.login"))

    user_id = session.get("user_id")
    email = session.get("email")

    connection = getDatabase()
    if connection is None:
        return jsonify({"error": "Veri tabanı bağlantısı kurulamadı."})

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT bb.*, b.title 
            FROM borrowed_books bb
            JOIN book b ON bb.book_id = b.book_id
            WHERE bb.user_id = %s AND bb.book_id = %s AND bb.is_returned = FALSE
        """, (user_id, book_id))

        borrowed = cursor.fetchone()

        if not borrowed:
            if request.is_json:
                return jsonify({"message": "İade edilecek kitap bulunamadı."}), 404
            flash("İade edilecek kitap bulunamadı.", "warning")
            return redirect(url_for("books.list_books"))
        
        #trigger tetikleyici
        cursor.execute("""
            UPDATE borrowed_books
            SET is_returned = TRUE, return_date = NOW()
            WHERE id = %s
        """, (borrowed["id"],))

        connection.commit()
        
        cursor.execute("""
            SELECT penalty_end_date FROM penalties 
            WHERE borrow_id = %s LIMIT 1
        """, (borrowed["id"],))
        
        penalty_record = cursor.fetchone()

        if penalty_record:
            send_penalty_mail(email, borrowed["title"], penalty_record["penalty_end_date"])
            flash(f"Kitap geç iade edildi! {penalty_record['penalty_end_date'].strftime('%H:%M')} saatine kadar yeni kitap alamazsınız.", "danger")
        else:
            send_borrow_mail_iade(email, borrowed["title"])
            flash(f"'{borrowed['title']}' başarıyla zamanında iade edildi.", "success")

        if request.is_json or request.args.get("format") == "json":
            return jsonify({"message": "İşlem tamamlandı."})
            
        return redirect(url_for("books.list_books"))

    except Exception as e:
        connection.rollback()
        print(f"Kitap iade hatası: {e}")
        if request.is_json:
            return jsonify({"error": "Kitap iade edilemedi."}), 500
        flash("Kitap iade edilemedi.", "danger")
        return redirect(url_for("books.list_books"))

    finally:
        cursor.close()
        connection.close()
        
        
#kitap ödünç aldığında...
def send_borrow_mail_odunc(email, book_name):
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_PASSWORD")

    subject = "Kitap Ödünç Alma Bilgilendirmesi"
    body = f"""
Merhaba,

"{book_name}" adlı kitabı başarıyla ödünç aldınız.
İyi okumalar dileriz

Kütüphane Yönetim Sistemi
"""

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Mail gönderilemedi: {type(e).__name__} - {e}")


#Kitap iade edildiğinde...
def send_borrow_mail_iade(email, book_name):
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_PASSWORD")
    
    subject = "Kitap İade Bilgilendirmesi"
    body = f"""
Merhaba,

"{book_name}" adlı kitabı başarıyla iade edildi.
sağlıklı günler dileriz.

Kütüphane Yönetim Sistemi
"""

    msg = MIMEMultipart()
    msg["From"] = sender_email#kimden gidecek
    msg["To"] = email#kime gidecek
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))#plain = düz metin

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)#mail sunucu adresi,port numarası
        server.starttls()#güvenli gönderim 
        server.login(sender_email, sender_password)#kimlik doğrulama aşaması
        server.send_message(msg)#mesaj gönder
        server.quit()#sunucudan çık
    except Exception as e:
        print(f"Mail gönderilemedi: {type(e).__name__} - {e}")
        

#ceza maili gönderme
def send_penalty_mail(email, book_name, end_date):
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_PASSWORD")
    
    subject = "Kütüphane Ceza Bildirimi"
    end_date = end_date.strftime('%H:%M:%S')
    
    body = f"""
Merhaba,

"{book_name}" adlı kitabı teslim tarihinden (1 dakika) geç iade ettiğiniz tespit edilmiştir.

Bu nedenle 1 dakika boyunca kitap ödünç alamayacaksınız.
Kısıtlama Bitiş Süresi: {end_date}

Kütüphane Yönetim Sistemi
"""
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Ceza maili gönderilemedi: {e}")

    

    
    
    


