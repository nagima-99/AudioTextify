from flask import render_template, request, redirect, flash, url_for, make_response
from flask_login import LoginManager, login_user, current_user, login_required, logout_user
from models import app, db, User, Feedback
from speech import recognize_speech
from werkzeug.utils import redirect
from forms import ResetPasswordForm, RequestResetForm, send_reset_email
from docx import Document
from io import BytesIO


login_manager = LoginManager(app)
login_manager.login_view = 'login'
ALLOWED_EXTENSIONS = {'wav'}


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def index():
    transcript = ""
    error = None
    if request.method == "POST":
        if "file" not in request.files:
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            return redirect(request.url)
        if file and allowed_file(file.filename):
            language = request.form.get('language', "en-US")
            transcript = recognize_speech(file, language=language)
            if transcript is None:
                error = "Ошибка: Обнаруженный язык в аудио не соответствует выбранному вами языку для распознавания."
        else:
            error = "Ошибка: Недопустимый формат файла. Загрузите файл в формате WAV."
    return render_template('index.html', transcript=transcript, error=error)


@app.route("/download_transcript")
def download_transcript():
    if "transcript" in request.args:
        transcript = request.args["transcript"]

        format = request.args.get("format", "txt")

        if format == "txt":
            response = make_response(transcript)
            response.headers["Content-Disposition"] = "attachment; filename=transcript.txt"
            return response
        elif format == "docx":
            doc = Document()
            doc.add_paragraph(transcript)

            doc_buffer = BytesIO()
            doc.save(doc_buffer)
            doc_buffer.seek(0)

            response = make_response(doc_buffer.getvalue())
            response.headers["Content-Disposition"] = "attachment; filename=transcript.docx"
            response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            return response
        else:
            return "Ошибка: Неподдерживаемый формат файла."
    else:
        return "Ошибка: Текст для скачивания не найден."


@app.route("/instruction")
def about():
    return render_template("instruction.html", title="Инструкция")


@app.route("/faq")
def faq():
    return render_template("faq.html", title="FAQ")


@app.route("/feedback", methods=["GET", "POST"])
@login_required
def feedback():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        message = request.form["message"]

        feedback_entry = Feedback(name=name, email=email, message=message)
        db.session.add(feedback_entry)
        db.session.commit()

        flash("Ваша заявка успешно отправлена!", "success")
        return redirect(url_for("feedback"))

    return render_template("feedback.html", title="Обратная связь")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Пользователь с таким именем уже существует", "error")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Пользователь с таким email уже существует", "error")
            return redirect(url_for("register"))

        if len(password) < 4:
            flash("Пароль слишком короткий (не может быть меньше 4 символов)", "error")
            return redirect(url_for("register"))

        new_user = User(username=username, email=email, password=password)

        db.session.add(new_user)
        db.session.commit()

        flash("Вы успешно зарегистрировались!", "success")
        return redirect(url_for("login"))

    return render_template("register.html", title="Регистрация")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Вы успешно вошли в систему!", "success")
            return redirect(url_for("user_profile"))
        else:
            flash("Неверное имя пользователя или пароль", "error")
            return redirect(url_for("login"))

    return render_template("login.html", title="Вход в систему")


@app.route("/user_profile", methods=["GET", "POST"])
@login_required
def user_profile():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]

        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_new_password = request.form["confirm_new_password"]

        if current_password and not current_user.check_password(current_password):
            flash("Неверный текущий пароль", "error")
            return redirect(url_for("user_profile"))

        if new_password and new_password != confirm_new_password:
            flash("Новый пароль и его подтверждение не совпадают", "error")
            return redirect(url_for("user_profile"))

        if new_password and len(new_password) < 4:
            flash("Новый пароль слишком короткий (не может быть меньше 4 символов)", "error")
            return redirect(url_for("user_profile"))

        current_user.username = username
        current_user.email = email

        if new_password:
            current_user.set_password(new_password)

        db.session.commit()

        if new_password:
            flash("Ваш пароль успешно обновлен", "success")
        else:
            flash("Ваши личные данные успешно обновлены", "success")

        return redirect(url_for("user_profile"))
    return render_template("user_profile.html", user=current_user)


@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    db.session.delete(current_user)
    db.session.commit()
    logout_user()
    flash("Ваш аккаунт успешно удален", "success")
    return redirect(url_for("register"))


@app.route("/reset_password", methods=["GET", "POST"])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash("На указанный email были отправлены инструкции по восстановлению пароля", "info")
        return redirect(url_for("login"))
    return render_template("reset_request.html", form_reset=form, title="Сброс пароля")


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    user = User.verify_reset_token(token)
    if user is None:
        flash("Не правильный или просроченный токен", "warning")
        return redirect(url_for("reset_request"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Ваш пароль был обновлён! Вы можете войти на блог", "success")
        return redirect(url_for("login"))
    return render_template("reset_token.html", form_reset_password=form, title="Новый пароль")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы успешно вышли из системы.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        app.run(debug=True, threaded=True)
