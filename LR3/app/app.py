from urllib.parse import urljoin, urlparse

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)

app = Flask(__name__)
application = app
app.config['SECRET_KEY'] = 'lab3-secret-key'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к запрашиваемой странице необходимо пройти процедуру аутентификации.'
login_manager.login_message_category = 'warning'


class User(UserMixin):
    def __init__(self, user_id, login):
        self.id = user_id
        self.login = login


USERS = {
    'user': {
        'id': '1',
        'password': 'qwerty',
    }
}


@login_manager.user_loader
def load_user(user_id):
    for login, data in USERS.items():
        if data['id'] == user_id:
            return User(user_id=data['id'], login=login)
    return None


def is_safe_redirect_url(target):
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ('http', 'https') and host_url.netloc == redirect_url.netloc


@app.route('/')
def index():
    return render_template('index.html', title='Главная')


@app.route('/counter')
def counter():
    visit_count = session.get('counter_visits', 0) + 1
    session['counter_visits'] = visit_count
    return render_template('counter.html', title='Счётчик посещений', visit_count=visit_count)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        user_data = USERS.get(username)
        if user_data and user_data['password'] == password:
            user = User(user_id=user_data['id'], login=username)
            login_user(user, remember=remember)
            flash('Успешный вход в систему.', 'success')

            next_page = request.args.get('next')
            if next_page and is_safe_redirect_url(next_page):
                return redirect(next_page)
            return redirect(url_for('index'))

        flash('Неверный логин или пароль.', 'danger')
        return render_template('login.html', title='Вход', username=username)

    return render_template('login.html', title='Вход')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))


@app.route('/secret')
@login_required
def secret():
    return render_template('secret.html', title='Секретная страница')


if __name__ == '__main__':
    app.run(debug=True)
