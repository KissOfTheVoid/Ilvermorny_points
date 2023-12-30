from flask import Flask, request, jsonify, abort, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
import os
import io
import logging
import subprocess
from logging.handlers import RotatingFileHandler
from functools import wraps
import pandas as pd
import yaml


db = SQLAlchemy()


class Faculty(db.Model):
    __tablename__ = 'faculties'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    total_points = db.Column(db.Integer, default=0)
    courage = db.Column(db.Integer, default=0)
    resourcefulness = db.Column(db.Integer, default=0)
    kindness = db.Column(db.Integer, default=0)
    sports = db.Column(db.Integer, default=0)
    transactions = db.relationship('PointsTransaction', back_populates='faculty')


class PointsTransaction(db.Model):
    __tablename__ = 'points_transactions'
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculties.id'))
    faculty = db.relationship('Faculty', back_populates='transactions')
    points = db.Column(db. Integer, nullable=False)
    points_type = db.Column(db.String(255), nullable=False)
    sender_name = db.Column(db.String(255), nullable=False)
    sender_surname = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.TIMESTAMP, default=db.func.current_timestamp())


def create_app():
    app = Flask(__name__)

    with open("config.yaml", "r") as yamlfile:
        cfg = yaml.safe_load(yamlfile)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://{user}:{password}@localhost/{dbname}'.format(
        user=cfg['database']['user'],
        password=cfg['database']['password'],
        dbname=cfg['database']['name']
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/ilvermorny.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Ilvermorny startup')
    db.init_app(app)

    return app, cfg['security']['custom_header_value']


app, CUSTOM_HEADER_VALUE = create_app()

db_user = app.config['SQLALCHEMY_DATABASE_URI'].split(':')[1].lstrip('//')
db_name = app.config['SQLALCHEMY_DATABASE_URI'].split('/')[-1]


def require_security_header(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-Custom-Security-Header') != CUSTOM_HEADER_VALUE:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def add_initial_faculty_data():
    faculties = ['Вампус', 'Пакваджи', 'Птица Гром', 'Рогатый змей']
    for faculty_name in faculties:
        if not Faculty.query.filter_by(name=faculty_name).first():
            new_faculty = Faculty(name=faculty_name)
            db.session.add(new_faculty)
    db.session.commit()


def check_or_create_database():
    try:
        db.create_all()
        add_initial_faculty_data()  # Добавление начальных данных факультетов
        app.logger.info("Таблицы и начальные данные успешно созданы")
    except Exception as e:
        app.logger.error(f"Ошибка при создании таблиц или начальных данных: {e}")


def create_db_dump(db_user, db_name):
    try:
        subprocess.run(["pg_dump", "-U", db_user, "--data-only", "-f", "db_dump.sql", db_name])
        app.logger.info("Дамп базы данных создан успешно")
    except Exception as e:
        app.logger.error("Ошибка при создании дампа базы данных: %s", e)


def restore_db_from_dump(db_user, db_name):
    if os.path.exists('db_dump.sql'):
        try:
            subprocess.run(["psql", "-U", db_user, "-d", db_name, "-f", "db_dump.sql"])
            app.logger.info("База данных восстановлена из дампа")
        except Exception as e:
            app.logger.error("Ошибка при восстановлении базы данных из дампа: %s", e)
    else:
        check_or_create_database()


@app.route('/points', methods=['POST'])
@require_security_header
def add_points():
    data = request.json
    faculty_id = data['faculty_id']
    points = data['points']
    points_type = data['points_type']
    sender_name = data['sender_name'].strip()
    sender_surname = data['sender_surname'].strip()
    operation = data.get('operation', 'add')

    allowed_points_types = ['courage', 'resourcefulness', 'kindness', 'sports']
    if points_type not in allowed_points_types:
        app.logger.error("Недопустимое значение points_type: %s", points_type)
        return jsonify({'status': 'error', 'message': 'Недопустимое значение points_type'}), 400

    faculty = Faculty.query.get(faculty_id)
    if not faculty:
        return jsonify({'status': 'error', 'message': 'Факультет не найден'}), 404

    # Обновление баллов факультета
    if operation == 'add':
        setattr(faculty, points_type, getattr(faculty, points_type) + points)
        faculty.total_points += points
    elif operation == 'subtract':
        setattr(faculty, points_type, getattr(faculty, points_type) - points)
        faculty.total_points -= points

    # Создание записи транзакции
    transaction = PointsTransaction(
        faculty_id=faculty_id,
        points=points if operation == 'add' else -points,
        points_type=points_type,
        sender_name=sender_name,
        sender_surname=sender_surname
    )
    db.session.add(transaction)
    db.session.commit()

    return jsonify({'status': 'success'}), 200


@app.route('/faculties', methods=['GET'])
@require_security_header
def get_faculties():
    faculties_query = Faculty.query.all()
    faculties = [
        {"id": faculty.id, "name": faculty.name, "total_points": faculty.total_points,
         "courage": faculty.courage, "resourcefulness": faculty.resourcefulness,
         "kindness": faculty.kindness, "sports": faculty.sports}
        for faculty in faculties_query
    ]
    return jsonify(faculties)


@app.route('/get_transactions', methods=['GET'])
@require_security_header
def get_transactions():
    transactions_query = PointsTransaction.query.all()
    transactions = [
        {"id": trans.id, "faculty_id": trans.faculty_id, "points": trans.points,
         "points_type": trans.points_type, "sender_name": trans.sender_name,
         "sender_surname": trans.sender_surname, "timestamp": trans.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
        for trans in transactions_query
    ]
    return jsonify(transactions)


@app.route('/get_faculty_points', methods=['GET'])
@require_security_header
def get_faculty_points():
    faculties = Faculty.query.with_entities(Faculty.name, Faculty.total_points).all()
    points_data = {name: points for name, points in faculties}
    return jsonify(points_data), 200


@app.route('/get_transactions_by_wizard')
@require_security_header
def get_transactions_by_wizard():
    name = request.args.get('name', '').strip()
    surname = request.args.get('surname', '').strip()

    transactions = PointsTransaction.query.filter_by(sender_name=name, sender_surname=surname).join(Faculty).all()
    if not transactions:
        return jsonify({'status': 'error', 'message': 'Волшебник не найден'}), 404

    transactions_data = [{
        'timestamp': trans.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        'faculty_name': trans.faculty.name,
        'points': trans.points,
        'points_type': trans.points_type,
        'sender_name': trans.sender_name,
        'sender_surname': trans.sender_surname
    } for trans in transactions]

    return jsonify(transactions_data)


@app.route('/export_transactions')
@require_security_header
def export_transactions():
    try:
        # Получение данных из запроса
        name = request.args.get('name', '').strip()
        surname = request.args.get('surname', '').strip()

        # Формирование запроса с использованием SQLAlchemy
        query = db.session.query(
            PointsTransaction.timestamp,
            Faculty.name.label('faculty_name'),
            PointsTransaction.points,
            PointsTransaction.points_type,
            PointsTransaction.sender_name,
            PointsTransaction.sender_surname
        ).join(Faculty, PointsTransaction.faculty_id == Faculty.id)

        if name:
            query = query.filter(PointsTransaction.sender_name == name)
        if surname:
            query = query.filter(PointsTransaction.sender_surname == surname)

        transactions = query.all()

        # Проверка на наличие данных
        if not transactions:
            return jsonify({'status': 'error', 'message': 'Транзакции не найдены'}), 404

        # Преобразование данных в DataFrame
        df = pd.DataFrame([{
            'timestamp': trans.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            'faculty_name': trans.faculty_name,
            'points': trans.points,
            'points_type': trans.points_type,
            'sender_name': trans.sender_name,
            'sender_surname': trans.sender_surname
        } for trans in transactions])

        # Сохранение данных в Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        # Возвращение файла Excel клиенту
        filename = 'transactions.xlsx'
        if name or surname:
            filename = f"transactions_{name}_{surname}.xlsx"
        return send_file(output, as_attachment=True, download_name=filename,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        app.logger.error(f"Ошибка при экспорте транзакций: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/get_users')
@require_security_header
def get_users():
    users_query = db.session.query(
        PointsTransaction.sender_name, PointsTransaction.sender_surname
    ).distinct()
    users = [
        {"name": user.sender_name, "surname": user.sender_surname}
        for user in users_query
    ]
    return jsonify(users)


@app.route('/get_faculty_points_by_id/<int:faculty_id>', methods=['GET'])
@require_security_header
def get_faculty_points_by_id(faculty_id):
    faculty = Faculty.query.get_or_404(faculty_id)
    faculty_data = {
        'id': faculty.id,
        'name': faculty.name,
        'total_points': faculty.total_points,
        'courage': faculty.courage,
        'resourcefulness': faculty.resourcefulness,
        'kindness': faculty.kindness,
        'sports': faculty.sports
    }
    return jsonify(faculty_data)


@app.route('/')
def index():
    return render_template('Ilvermorny_front_pre_alpha.html', custom_header_value=CUSTOM_HEADER_VALUE)


@app.route('/display_points')
def display_points():
    return render_template('faculty_points_page.html', custom_header_value=CUSTOM_HEADER_VALUE)


@app.route('/staff_actions')
def staff_actions():
    return render_template('staff_actions_pre_alfa.html', custom_header_value=CUSTOM_HEADER_VALUE)


if __name__ == '__main__':
    restore_db_from_dump(db_user, db_name)
    try:
        app.run(debug=True)
    finally:
        create_db_dump(db_user, db_name)

