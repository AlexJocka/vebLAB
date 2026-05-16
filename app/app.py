import random
import re
from flask import Flask, render_template, request
from faker import Faker

fake = Faker()

app = Flask(__name__)
application = app

images_ids = ['7d4e9175-95ea-4c5f-8be5-92a6b708bb3c',
              '2d2ab7df-cdbc-48a8-a936-35bba702def5',
              '6e12f3de-d5fd-4ebb-855b-8cbc485278b7',
              'afc2cfe7-5cac-4b80-9b9a-d5c65ef0c728',
              'cab5b7f2-774e-4884-a200-0c0180fa777f']

def generate_comments(replies=True):
    comments = []
    for i in range(random.randint(1, 3)):
        comment = { 'author': fake.name(), 'text': fake.text() }
        if replies:
            comment['replies'] = generate_comments(replies=False)
        comments.append(comment)
    return comments

def generate_post(i):
    return {
        'title': 'Заголовок поста',
        'text': fake.paragraph(nb_sentences=100),
        'author': fake.name(),
        'date': fake.date_time_between(start_date='-2y', end_date='now'),
        'image_id': f'{images_ids[i]}.jpg',
        'comments': generate_comments()
    }

posts_list = sorted([generate_post(i) for i in range(5)], key=lambda p: p['date'], reverse=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/posts')
def posts():
    return render_template('posts.html', title='Посты', posts=posts_list)

@app.route('/posts/<int:index>')
def post(index):
    p = posts_list[index]
    return render_template('post.html', title=p['title'], post=p)

@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')


@app.route('/request-data')
def request_data():
    return render_template('request_data.html', title='Данные запроса')


@app.route('/request-data/url-params')
def request_url_params():
    return render_template(
        'request_url_params.html',
        title='Параметры URL',
        url_params=request.args
    )


@app.route('/request-data/headers')
def request_headers():
    return render_template(
        'request_headers.html',
        title='Заголовки запроса',
        headers=request.headers
    )


@app.route('/request-data/cookies')
def request_cookies():
    return render_template(
        'request_cookies.html',
        title='Cookie',
        cookies=request.cookies
    )


@app.route('/request-data/form', methods=['GET', 'POST'])
def request_form():
    auth_data = None
    if request.method == 'POST':
        auth_data = {
            'login': request.form.get('login', ''),
            'password': request.form.get('password', '')
        }

    return render_template(
        'request_form.html',
        title='Параметры формы',
        auth_data=auth_data
    )


def validate_phone_number(raw_phone):
    phone = raw_phone.strip()

    if re.search(r"[^0-9\s().+-]", phone):
        return None, 'Недопустимый ввод. В номере телефона встречаются недопустимые символы.'

    digits = re.sub(r"\D", "", phone)
    needs_eleven = phone.startswith('+7') or phone.startswith('8')
    required_length = 11 if needs_eleven else 10

    if len(digits) != required_length:
        return None, 'Недопустимый ввод. Неверное количество цифр.'

    if required_length == 11:
        if phone.startswith('+7'):
            digits = '8' + digits[1:]
        elif phone.startswith('8'):
            digits = '8' + digits[1:]
        else:
            return None, 'Недопустимый ввод. Неверное количество цифр.'
    else:
        digits = '8' + digits

    formatted = f"{digits[0]}-{digits[1:4]}-{digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    return formatted, None


@app.route('/phone-check', methods=['GET', 'POST'])
def phone_check():
    phone = ''
    formatted_phone = None
    error = None

    if request.method == 'POST':
        phone = request.form.get('phone', '')
        formatted_phone, error = validate_phone_number(phone)

    return render_template(
        'phone_check.html',
        title='Проверка телефона',
        phone=phone,
        formatted_phone=formatted_phone,
        error=error
    )


if __name__ == '__main__':
    app.run(debug=True)
