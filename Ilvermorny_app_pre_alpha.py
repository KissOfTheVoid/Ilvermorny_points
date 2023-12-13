import yaml
import io
import psycopg2
from psycopg2 import sql, Error
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file
import logging
from logging.handlers import RotatingFileHandler
import subprocess
import os

app = Flask(__name__)

# Настройка логирования с использованием RotatingFileHandler
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/ilvermorny.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)

# Установка уровня логирования для приложения
app.logger.setLevel(logging.INFO)
app.logger.info('Ilvermorny startup')

# Загрузка конфигурации из YAML файла
with open("config.yaml", "r") as yamlfile:
    cfg = yaml.safe_load(yamlfile)

DB_NAME = cfg['database']['name']
DB_USER = cfg['database']['user']
DB_PASSWORD = cfg['database']['password']


def create_tables():
    try:
        conn_string = f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faculties (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                total_points INT DEFAULT 0
            );
        """)

        # Создание таблицы points_transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS points_transactions (
                id SERIAL PRIMARY KEY,
                faculty_id INT REFERENCES faculties(id),
                points INT NOT NULL,
                sender_name VARCHAR(255) NOT NULL,
                sender_surname VARCHAR(255) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Факультеты для добавления
        faculties = ['Вампус', 'Пакваджи', 'Птица Гром', 'Рогатый змей']
        for faculty in faculties:
            # Проверяем, существует ли уже факультет
            cursor.execute("SELECT * FROM faculties WHERE name = %s", (faculty,))
            if cursor.fetchone() is None:
                # Добавляем факультет, если он не существует
                cursor.execute("INSERT INTO faculties (name) VALUES (%s)", (faculty,))

        conn.commit()
        cursor.close()
        conn.close()
        app.logger.info("Таблицы успешно созданы")
    except Error as e:
        app.logger.error(f"Ошибка при создании таблиц: {e}")


def check_or_create_database():
    try:
        conn_string = f"dbname=postgres user={DB_USER} password={DB_PASSWORD}"
        conn = psycopg2.connect(conn_string)
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,))
        exists = cursor.fetchone()
        if not exists:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            conn.commit()
            cursor.close()
            conn.close()
            create_tables()
        else:
            cursor.close()
            conn.close()
        app.logger.info("База данных проверена или успешно создана")
    except Error as e:
        app.logger.error(f"Ошибка при проверке/создании базы данных: {e}")


def create_db_dump():
    check_or_create_database()

    try:
        subprocess.run(["pg_dump", "-U", DB_USER, "--data-only", "-f", "db_dump.sql", DB_NAME])
        app.logger.info("Дамп базы данных создан успешно")
    except Error as e:
        app.logger.error("Ошибка при создании дампа базы данных: %s", e)


def restore_db_from_dump():
    if os.path.exists('db_dump.sql'):
        try:
            subprocess.run(["psql", "-U", DB_USER, "-d", DB_NAME, "-f", "db_dump.sql"])
            app.logger.info("База данных восстановлена из дампа")
        except Error as e:
            app.logger.error("Ошибка при восстановлении базы данных из дампа: %s", e)


@app.route('/points', methods=['POST'])
def add_points():
    try:
        data = request.json
        faculty_id = data['faculty_id']  # Убедитесь, что здесь используется 'faculty_id'
        points = data['points']
        sender_name = data['sender_name'].strip()
        sender_surname = data['sender_surname'].strip()
        operation = data.get('operation', 'add')
        faculties = ['Вампус', 'Пакваджи', 'Птица Гром', 'Рогатый змей']
        conn = psycopg2.connect(f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}")
        cursor = conn.cursor()

        if operation == 'subtract':
            cursor.execute("UPDATE faculties SET total_points = total_points - %s WHERE id = %s",
                           (points, faculty_id))
        else:
            cursor.execute("UPDATE faculties SET total_points = total_points + %s WHERE id = %s", (points, faculty_id))

        # Добавление записи транзакции
        cursor.execute(
            "INSERT INTO points_transactions (faculty_id, points, sender_name, sender_surname) VALUES (%s, %s, %s, %s)",
            (faculty_id, points, sender_name, sender_surname))
        cursor.execute("SELECT total_points FROM faculties WHERE id = %s", (faculty_id,))
        updated_points = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        app.logger.info("Points added successfully: %s points by %s %s to %s", points, sender_name, sender_surname,
                     faculties[int(faculty_id) - 1])
        # Логгирование обновленного количества баллов факультета
        app.logger.info("Updated points for faculty_id %s: %s", faculties[int(faculty_id) - 1], updated_points)
        return jsonify({'status': 'success'}), 200
    except Error as e:
        app.logger.error("Ошибка при добавлении/вычитании баллов: %s", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/faculties', methods=['GET'])
def get_faculties():
    try:
        conn = psycopg2.connect(f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}")
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM faculties")
        faculties = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([{"id": id, "name": name} for id, name in faculties]), 200
    except Error as e:
        app.logger.error("Ошибка при получении списка факультетов: %s", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/get_transactions', methods=['GET'])
def get_transactions():
    try:
        conn = psycopg2.connect(f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM points_transactions")
        transactions = cursor.fetchall()

        conn.close()

        # Форматирование данных транзакций для JSON-ответа
        transactions_data = []
        for trans in transactions:
            trans_dict = {
                "id": trans[0],
                "faculty_id": trans[1],
                "points": trans[2],
                "sender_name": trans[3],
                "sender_surname": trans[4],
                "timestamp": trans[5].strftime("%Y-%m-%d %H:%M:%S")
            }
            transactions_data.append(trans_dict)
        app.logger.info("Transactions retrieved successfully")
        return jsonify(transactions_data), 200
    except Error as e:
        app.logger.error("Ошибка при получении транзакций: %s", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/get_faculty_points', methods=['GET'])
def get_faculty_points():
    try:
        conn = psycopg2.connect(f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}")
        cursor = conn.cursor()

        cursor.execute("SELECT name, total_points FROM faculties")
        faculty_points = cursor.fetchall()

        conn.close()

        # Форматирование данных баллов факультетов для JSON-ответа
        points_data = {name: points for name, points in faculty_points}

        return jsonify(points_data), 200
    except Error as e:
        app.logger.error("Ошибка при получении баллов факультетов: %s", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/get_transactions_by_wizard')
def get_transactions_by_wizard():
    name = request.args.get('name', '').strip()
    surname = request.args.get('surname', '').strip()

    try:
        conn = psycopg2.connect(f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}")
        cursor = conn.cursor()

        # Проверка существования волшебника в таблице transactions
        cursor.execute("SELECT * FROM points_transactions WHERE sender_name = %s AND sender_surname = %s", (name, surname))
        if cursor.fetchone() is None:
            cursor.close()
            conn.close()
            app.logger.info(f"Волшебник {name} {surname} не найден")
            return jsonify({'status': 'error', 'message': 'Волшебник не найден'}), 404

        # Выполнение запроса для получения транзакций
        cursor.execute("""
            SELECT pt.timestamp, f.name, pt.points, pt.sender_name, pt.sender_surname
            FROM points_transactions pt
            JOIN faculties f ON pt.faculty_id = f.id
            WHERE pt.sender_name = %s AND pt.sender_surname = %s
        """, (name, surname))
        transactions = cursor.fetchall()
        cursor.close()
        conn.close()

        transactions_data = [{
            'timestamp': trans[0].strftime("%Y-%m-%d %H:%M:%S"),
            'faculty_name': trans[1],
            'points': trans[2],
            'sender_name': trans[3],
            'sender_surname': trans[4]
        } for trans in transactions]

        return jsonify(transactions_data)
    except Error as e:
        app.logger.error(f"Ошибка при получении транзакций для {name} {surname}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/export_transactions')
def export_transactions():
    name = request.args.get('name', '').strip()
    surname = request.args.get('surname', '').strip()

    try:
        conn = psycopg2.connect(f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}")
        cursor = conn.cursor()

        # Выполнение запроса к базе данных
        query = """
        SELECT pt.timestamp, f.name, pt.points, pt.sender_name, pt.sender_surname
        FROM points_transactions pt
        JOIN faculties f ON pt.faculty_id = f.id
        WHERE pt.sender_name = %s AND pt.sender_surname = %s
        """
        cursor.execute(query, (name, surname))
        transactions = cursor.fetchall()

        # Проверка на наличие данных
        if not transactions:
            cursor.close()
            conn.close()
            app.logger.info(f"Волшебник {name} {surname} не найден")
            return jsonify({'status': 'error', 'message': 'Волшебник не найден'}), 404

        # Преобразование в DataFrame и сохранение в XLSX
        df = pd.DataFrame(transactions, columns=['timestamp', 'faculty_name', 'points', 'sender_name', 'sender_surname'])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)

        output.seek(0)
        cursor.close()
        conn.close()
        return send_file(output,
                         as_attachment=True,
                         download_name=f'transactions_{name}_{surname}.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Error as e:
        app.logger.error(f"Ошибка при экспорте транзакций: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/')
def index():
    return render_template('Ilvermorny_front_pre_alpha.html')


@app.route('/staff_actions')
def staff_actions():
    return render_template('staff_actions_pre_alfa.html')


if __name__ == '__main__':
    restore_db_from_dump()

    try:
        app.run(debug=True)
    finally:
        create_db_dump()
