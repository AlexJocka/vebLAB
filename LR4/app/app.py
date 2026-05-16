import os
import re
import sqlite3

from flask import Flask, flash, g, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
application = app
app.config['SECRET_KEY'] = 'lab4-secret-key'
app.config['DATABASE'] = os.path.join(app.root_path, 'users.sqlite3')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к этой странице необходимо войти в систему.'
login_manager.login_message_category = 'warning'

LOGIN_RE = re.compile(r'^[A-Za-z0-9]{5,}$')
PASSWORD_ALLOWED_RE = re.compile(r'^[A-Za-zА-Яа-яЁё0-9~!?@#$%^&*_\-+()\[\]{}></\\|"\'.,:;]+$')


class User(UserMixin):
    def __init__(self, user_id, login, first_name='', last_name=''):
        self.id = str(user_id)
        self.login = login
        self.first_name = first_name or ''
        self.last_name = last_name or ''


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def query_one(sql, params=()):
    return get_db().execute(sql, params).fetchone()


def query_all(sql, params=()):
    return get_db().execute(sql, params).fetchall()


def init_db():
    db = get_db()
    db.executescript(
        '''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            last_name TEXT,
            first_name TEXT NOT NULL,
            middle_name TEXT,
            role_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE SET NULL
        );
        '''
    )

    if query_one('SELECT COUNT(*) AS count FROM roles')['count'] == 0:
        db.executemany(
            'INSERT INTO roles (name, description) VALUES (?, ?)',
            [
                ('Администратор', 'Полный доступ к управлению пользователями'),
                ('Пользователь', 'Обычная учетная запись'),
            ],
        )

    db.commit()


@login_manager.user_loader
def load_user(user_id):
    user = query_one('SELECT id, login, first_name, last_name FROM users WHERE id = ?', (user_id,))
    if user is None:
        return None
    return User(user['id'], user['login'], user['first_name'], user['last_name'])


def full_name(user):
    parts = [user['last_name'], user['first_name'], user['middle_name']]
    return ' '.join(part for part in parts if part) or user['login']


@app.context_processor
def inject_helpers():
    return {'full_name': full_name}


def get_roles():
    return query_all('SELECT id, name, description FROM roles ORDER BY name')


def get_user_or_404(user_id):
    user = query_one(
        '''
        SELECT users.id, users.login, users.last_name, users.first_name, users.middle_name,
               users.role_id, users.created_at, roles.name AS role_name
        FROM users
        LEFT JOIN roles ON roles.id = users.role_id
        WHERE users.id = ?
        ''',
        (user_id,),
    )
    if user is None:
        flash('Пользователь не найден.', 'danger')
        return None
    return user


def validate_password(password):
    errors = []
    if not password:
        return ['Поле не может быть пустым.']
    if len(password) < 8:
        errors.append('Пароль должен содержать не менее 8 символов.')
    if len(password) > 128:
        errors.append('Пароль должен содержать не более 128 символов.')
    if re.search(r'\s', password):
        errors.append('Пароль не должен содержать пробелы.')
    if not PASSWORD_ALLOWED_RE.fullmatch(password):
        errors.append('Пароль содержит недопустимые символы.')
    if not any(ch.isupper() for ch in password if ch.isalpha()):
        errors.append('Пароль должен содержать хотя бы одну заглавную букву.')
    if not any(ch.islower() for ch in password if ch.isalpha()):
        errors.append('Пароль должен содержать хотя бы одну строчную букву.')
    if not any(ch in '0123456789' for ch in password):
        errors.append('Пароль должен содержать хотя бы одну цифру.')
    return errors


def validate_user_form(form, mode='create'):
    errors = {}
    login = form.get('login', '').strip()
    password = form.get('password', '')
    last_name = form.get('last_name', '').strip()
    first_name = form.get('first_name', '').strip()

    if mode == 'create':
        if not login:
            errors['login'] = ['Поле не может быть пустым.']
        elif not LOGIN_RE.fullmatch(login):
            errors['login'] = ['Логин должен состоять только из латинских букв и цифр и иметь длину не менее 5 символов.']

        password_errors = validate_password(password)
        if password_errors:
            errors['password'] = password_errors

    if not last_name:
        errors['last_name'] = ['Поле не может быть пустым.']
    if not first_name:
        errors['first_name'] = ['Поле не может быть пустым.']

    return errors


def form_data_from_request():
    role_id = request.form.get('role_id') or None
    return {
        'login': request.form.get('login', '').strip(),
        'password': request.form.get('password', ''),
        'last_name': request.form.get('last_name', '').strip(),
        'first_name': request.form.get('first_name', '').strip(),
        'middle_name': request.form.get('middle_name', '').strip(),
        'role_id': int(role_id) if role_id and role_id.isdigit() else None,
    }


@app.route('/')
def index():
    users = query_all(
        '''
        SELECT users.id, users.login, users.last_name, users.first_name, users.middle_name,
               roles.name AS role_name
        FROM users
        LEFT JOIN roles ON roles.id = users.role_id
        ORDER BY users.id
        '''
    )
    return render_template('index.html', title='Пользователи', users=users)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        login_value = request.form.get('login', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        user = query_one('SELECT * FROM users WHERE login = ?', (login_value,))

        if user and check_password_hash(user['password_hash'], password):
            login_user(User(user['id'], user['login'], user['first_name'], user['last_name']), remember=remember)
            flash('Вы успешно вошли в систему.', 'success')
            return redirect(url_for('index'))

        flash('Неверный логин или пароль.', 'danger')
        return render_template('login.html', title='Вход', login_value=login_value)

    return render_template('login.html', title='Вход')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))


@app.route('/users/<int:user_id>')
def user_detail(user_id):
    user = get_user_or_404(user_id)
    if user is None:
        return redirect(url_for('index'))
    return render_template('user_detail.html', title='Просмотр пользователя', user=user)


@app.route('/users/new', methods=['GET', 'POST'])
@login_required
def user_create():
    roles = get_roles()
    form_data = {}
    errors = {}

    if request.method == 'POST':
        form_data = form_data_from_request()
        errors = validate_user_form(request.form, mode='create')
        if not errors:
            try:
                db = get_db()
                db.execute(
                    '''
                    INSERT INTO users (login, password_hash, last_name, first_name, middle_name, role_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        form_data['login'],
                        generate_password_hash(form_data['password']),
                        form_data['last_name'],
                        form_data['first_name'],
                        form_data['middle_name'],
                        form_data['role_id'],
                    ),
                )
                db.commit()
                flash('Пользователь успешно создан.', 'success')
                return redirect(url_for('index'))
            except sqlite3.IntegrityError:
                errors['login'] = ['Пользователь с таким логином уже существует.']
                flash('Не удалось создать пользователя. Исправьте ошибки в форме.', 'danger')
            except sqlite3.Error:
                flash('При записи в БД произошла ошибка.', 'danger')
        else:
            flash('Исправьте ошибки в форме.', 'danger')

    return render_template('user_form_page.html', title='Создание пользователя', roles=roles, form_data=form_data, errors=errors, mode='create')


@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def user_edit(user_id):
    user = get_user_or_404(user_id)
    if user is None:
        return redirect(url_for('index'))

    roles = get_roles()
    form_data = dict(user)
    errors = {}

    if request.method == 'POST':
        form_data = form_data_from_request()
        errors = validate_user_form(request.form, mode='edit')
        if not errors:
            try:
                db = get_db()
                db.execute(
                    '''
                    UPDATE users
                    SET last_name = ?, first_name = ?, middle_name = ?, role_id = ?
                    WHERE id = ?
                    ''',
                    (
                        form_data['last_name'],
                        form_data['first_name'],
                        form_data['middle_name'],
                        form_data['role_id'],
                        user_id,
                    ),
                )
                db.commit()
                flash('Пользователь успешно обновлен.', 'success')
                return redirect(url_for('index'))
            except sqlite3.Error:
                flash('При обновлении записи произошла ошибка.', 'danger')
        else:
            flash('Исправьте ошибки в форме.', 'danger')

    return render_template('user_form_page.html', title='Редактирование пользователя', roles=roles, form_data=form_data, errors=errors, mode='edit')


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def user_delete(user_id):
    if str(user_id) == current_user.get_id():
        flash('Нельзя удалить текущего пользователя.', 'danger')
        return redirect(url_for('index'))

    try:
        db = get_db()
        db.execute('DELETE FROM users WHERE id = ?', (user_id,))
        db.commit()
        flash('Пользователь успешно удален.', 'success')
    except sqlite3.Error:
        flash('При удалении пользователя произошла ошибка.', 'danger')
    return redirect(url_for('index'))


@app.route('/password', methods=['GET', 'POST'])
@login_required
def change_password():
    errors = {}
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        repeat_password = request.form.get('repeat_password', '')
        user = query_one('SELECT * FROM users WHERE id = ?', (current_user.get_id(),))

        if not old_password:
            errors['old_password'] = ['Поле не может быть пустым.']
        elif not check_password_hash(user['password_hash'], old_password):
            errors['old_password'] = ['Старый пароль введен неверно.']

        password_errors = validate_password(new_password)
        if password_errors:
            errors['new_password'] = password_errors

        if not repeat_password:
            errors['repeat_password'] = ['Поле не может быть пустым.']
        elif new_password != repeat_password:
            errors['repeat_password'] = ['Пароли не совпадают.']

        if not errors:
            db = get_db()
            db.execute(
                'UPDATE users SET password_hash = ? WHERE id = ?',
                (generate_password_hash(new_password), current_user.get_id()),
            )
            db.commit()
            flash('Пароль успешно изменен.', 'success')
            return redirect(url_for('index'))

        flash('Исправьте ошибки в форме.', 'danger')

    return render_template('change_password.html', title='Изменить пароль', errors=errors)


with app.app_context():
    init_db()


if __name__ == '__main__':
    app.run(debug=True)
