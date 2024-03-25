from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Email, ValidationError
from models import User, mail
from flask import url_for
from flask_mail import Message


class RequestResetForm(FlaskForm):
    email = StringField("email", validators=[DataRequired(), Email()])
    submit = SubmitField("Сбросить пароль")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError("Нет аккаунта с такой электронной почтой. Вы должны сначала зарегистрироваться.")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("Пароль", validators=[DataRequired()])
    confirm_password = PasswordField("Подтвердите пароль", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Сбросить пароль")


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message("Запрос на смену пароля",
                  sender="textifyaudio@gmail.com",
                  recipients=[user.email])
    msg.body = f"""
    Чтобы сбросить ваш пароль, перейдите по этой ссылке:
    {url_for('reset_token', token=token, _external=True)}

    Если вы не делали данный запрос, просто проигнорируйте это письмо!
    Никаких изменений произведено не будет!

    Отвечать на данное письмо не нужно так как оно сгенерировано автоматически.
    """
    mail.send(msg)
