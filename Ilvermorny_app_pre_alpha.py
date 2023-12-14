import io
import logging
import os
import subprocess
from logging.handlers import RotatingFileHandler

import pandas as pd
import psycopg2
import yaml
from flask import Flask, request, jsonify, render_template, send_file
from psycopg2 import sql, Error

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
                total_points INT DEFAULT 0,
                courage INT DEFAULT 0,
                resourcefulness INT DEFAULT 0,
                kindness INT DEFAULT 0,
                sports INT DEFAULT 0
            );
        """)

        # Создание таблицы points_transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS points_transactions (
                id SERIAL PRIMARY KEY,
                faculty_id INT REFERENCES faculties(id),
                points INT NOT NULL,
                points_type VARCHAR(255) NOT NULL,
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
        # Подключение к системной базе данных для проверки существования целевой базы данных
        conn = psycopg2.connect(dbname="postgres", user=DB_USER, password=DB_PASSWORD)
        conn.autocommit = True
        cursor = conn.cursor()

        # Проверка существования базы данных Ильверморни
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if not cursor.fetchone():
            # Создание базы данных, если она не существует
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            conn.commit()
            app.logger.info(f"База данных {DB_NAME} создана.")
        else:
            app.logger.info(f"База данных {DB_NAME} уже существует.")

        cursor.close()
        conn.close()

        # Подключение к только что созданной или существующей базе данных
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
        conn.autocommit = True
        cursor = conn.cursor()

        # Создание таблиц
        create_tables()  # Предполагается, что функция create_tables определена

        cursor.close()
        conn.close()
    except Error as e:
        app.logger.error(f"Ошибка при проверке или создании базы данных {DB_NAME}: {e}")


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
    else:
        check_or_create_database()  # Создание базы данных и таблиц, если дампа нет


@app.route('/points', methods=['POST'])
def add_points():
    try:
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

        conn = psycopg2.connect(f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}")
        cursor = conn.cursor()

        update_query = "UPDATE faculties SET {} = {} + %s, total_points = total_points + %s WHERE id = %s"
        if operation == 'subtract':
            update_query = "UPDATE faculties SET {} = {} - %s, total_points = total_points - %s WHERE id = %s"
            points = points * (-1)
        cursor.execute(update_query.format(points_type, points_type), (points, points, faculty_id))

        app.logger.info(
            "Баллы успешно %s: %s баллов для %s",
            'добавлены' if operation == 'add' else 'вычтены',
            points, points_type
        )

        transaction_query = """
            INSERT INTO points_transactions (faculty_id, points, points_type, sender_name, sender_surname)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(transaction_query, (faculty_id, points, points_type, sender_name, sender_surname))
        app.logger.info(
            "Транзакция сохранена: %s баллов %s для %s от %s %s",
            points, 'добавлено' if operation == 'add' else 'вычтено', points_type, sender_name, sender_surname
        )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success'}), 200
    except Exception as e:
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
                'points_type': trans[3],
                "sender_name": trans[4],
                "sender_surname": trans[5],
                "timestamp": trans[6].strftime("%Y-%m-%d %H:%M:%S")
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
        cursor.execute("SELECT * FROM points_transactions WHERE sender_name = %s AND sender_surname = %s",
                       (name, surname))
        if cursor.fetchone() is None:
            cursor.close()
            conn.close()
            app.logger.info(f"Волшебник {name} {surname} не найден")
            return jsonify({'status': 'error', 'message': 'Волшебник не найден'}), 404

        # Выполнение запроса для получения транзакций с учетом типа баллов
        cursor.execute("""
            SELECT pt.timestamp, f.name, pt.points, pt.points_type, pt.sender_name, pt.sender_surname
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
            'points_type': trans[3],  # Добавление типа баллов в данные
            'sender_name': trans[4],
            'sender_surname': trans[5]
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

        # Обновление запроса к базе данных для включения типа баллов
        query = """
        SELECT pt.timestamp, f.name, pt.points, pt.points_type, pt.sender_name, pt.sender_surname
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

        # Преобразование в DataFrame и сохранение в XLSX с учетом типа баллов
        df = pd.DataFrame(transactions, columns=['timestamp', 'faculty_name', 'points', 'points_type', 'sender_name',
                                                 'sender_surname'])
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
