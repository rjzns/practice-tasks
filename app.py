from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
import json
from cryptography.fernet import Fernet
import pythoncom
import win32com.client as win32
import shutil
import os
import zipfile
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Необходим для использования flash-сообщений

# Загрузка конфигурации из config.json
with open('config.json', 'r', encoding='utf-8-sig') as config_file:
    config = json.load(config_file)

db_dialect = config['database']['dialect']
db_name = config['database']['name']
db_user = config['database']['user']
db_host = config['database']['host']
db_port = config['database']['port']

# Функции для работы с шифрованием
def load_key():
    return open("secret.key", "rb").read()

def decrypt_password(user_password):
    key = load_key()
    f = Fernet(key)
    try:
        with open("encrypted_password.bin", "rb") as password_file:
            encrypted_password = password_file.read()
        decrypted_password = f.decrypt(encrypted_password).decode()
        if decrypted_password == user_password:
            return decrypted_password
        else:
            raise ValueError("Неверный пароль")
    except Exception as e:
        print(f"Ошибка при дешифровании пароля: {e}")
        raise

# Запрос пароля у пользователя для дешифрования
user_password = input("Введите пароль для доступа к базе данных: ")
db_password = decrypt_password(user_password)

# Формирование строки подключения
if db_dialect == 'sqlite':
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_name}'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'{db_dialect}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Проверяем, установлен ли SQLAlchemy
try:
    db = SQLAlchemy(app)
except ImportError:
    db = None
    print("SQLAlchemy не установлен. Приложение работает в ограниченном режиме.")

class BaseModel(db.Model if db else object):
    __tablename__ = 'bases'
    id = db.Column(db.Integer, primary_key=True) if db else None
    name = db.Column(db.String(80), nullable=False) if db else None
    server_1c = db.Column(db.String(80), nullable=False) if db else None
    user = db.Column(db.String(80), nullable=False) if db else None
    password = db.Column(db.String(80), nullable=False) if db else None
    repository_path = db.Column(db.String(120), nullable=False) if db else None
    repository_user = db.Column(db.String(80), nullable=False) if db else None
    repository_password = db.Column(db.String(80), nullable=False) if db else None
    extension_name = db.Column(db.String(80), nullable=True) if db else None
    server_sql = db.Column(db.String(80), nullable=False) if db else None
    sql_base = db.Column(db.String(80), nullable=False) if db else None

def create_database():
    if not db:
        print("SQLAlchemy не установлен. Невозможно создать базу данных.")
        return
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table('bases'):
            db.create_all()
            print("База данных создана")
            populate_database_if_empty()
        else:
            print("База данных уже существует")
        print_database_contents()

def populate_database_if_empty():
    if not db:
        print("SQLAlchemy не установлен. Невозможно заполнить базу данных.")
        return
    try:
        if db.session.query(BaseModel).count() == 0:
            populate_database()
        else:
            print("База данных уже заполнена.")
    except Exception as e:
        print(f"Ошибка при проверке базы данных: {e}")

def populate_database():
    if not db:
        print("SQLAlchemy не установлен. Невозможно заполнить базу данных.")
        return
    try:
        with open('data.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
            for key, details in data.items():
                new_base = BaseModel(
                    name=key,
                    server_1c=details['server_1c'],
                    user=details['user'],
                    password=details['password'],
                    repository_path=details['repository_path'],
                    repository_user=details['repository_user'],
                    repository_password=details['repository_password'],
                    extension_name=details.get('extension_name', ''),
                    server_sql=details['server_sql'],
                    sql_base=details['sql_base']
                )
                db.session.add(new_base)
            db.session.commit()
            print("База данных успешно заполнена.")
    except FileNotFoundError:
        print("Файл data.json не найден.")
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON: {e}")
    except KeyError as e:
        print(f"Отсутствует необходимый ключ в JSON: {e}")
    except Exception as e:
        print(f"Произошла ошибка при заполнении базы данных: {e}")
        db.session.rollback()

def print_database_contents():
    if not db:
        print("SQLAlchemy не установлен. Невозможно вывести содержимое базы данных.")
        return
    try:
        bases = BaseModel.query.all()
        for base in bases:
            print(f'ID: {base.id}, Name: {base.name}, Server 1C: {base.server_1c}')
        if not bases:
            print("База данных пуста")
    except Exception as e:
        print(f"Ошибка при выводе содержимого базы данных: {e}")

@app.route('/')
def index():
    if not db:
        return "SQLAlchemy не установлен. Приложение работает в ограниченном режиме."
    bases = BaseModel.query.all()
    return render_template('index.html', bases=bases)

@app.route('/base/<int:base_id>')
def show_base(base_id):
    if not db:
        return "SQLAlchemy не установлен. Приложение работает в ограниченном режиме."
    base = db.session.get(BaseModel, base_id)
    if not base:
        return "База данных не найдена", 404
    base_details = {
        'id': base.id,
        'name': base.name,
        'server_1c': base.server_1c,
        'user': base.user,
        'password': base.password,
        'repository_path': base.repository_path,
        'repository_user': base.repository_user,
        'repository_password': base.repository_password,
        'extension_name': base.extension_name,
        'server_sql': base.server_sql,
        'sql_base': base.sql_base
    }
    connection_status = connect_to_1c(base_details)
    return render_template('base_details.html', base=base_details, connection_status=connection_status)

@app.route('/edit_base/<int:base_id>', methods=['GET', 'POST'])
def edit_base(base_id):
    if not db:
        return "SQLAlchemy не установлен. Приложение работает в ограниченном режиме."
    base = db.session.get(BaseModel, base_id)
    if not base:
        return "База данных не найдена", 404
    if request.method == 'POST':
        base.name = request.form['name']
        base.server_1c = request.form['server_1c']
        base.user = request.form['user']
        base.password = request.form['password']
        base.repository_path = request.form['repository_path']
        base.repository_user = request.form['repository_user']
        base.repository_password = request.form['repository_password']
        base.extension_name = request.form.get('extension_name')
        base.server_sql = request.form['server_sql']
        base.sql_base = request.form['sql_base']
        try:
            db.session.commit()
            flash("База успешно обновлена!", "success")
            return redirect(url_for('show_base', base_id=base.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при обновлении базы: {e}", "danger")
    return render_template('edit_base.html', base=base)

def connect_to_1c(base):
    try:
        pythoncom.CoInitialize()
        v8 = win32.Dispatch("V83.COMConnector")
        connection_string = f'Srvr="{base["server_1c"]}";Ref="{base["name"]}";Usr="{base["user"]}";Pwd="{base["password"]}";'
        connection = v8.Connect(connection_string)
        return "Подключение успешно"
    except Exception as e:
        print(f"Ошибка подключения к базе 1С: {e}")
        return f"Ошибка подключения: {e}"

@app.route('/perform_action', methods=['POST'])
def perform_action():
    if not db:
        return "SQLAlchemy не установлен. Приложение работает в ограниченном режиме."
    action = request.form.get('action')
    selected_bases = request.form.getlist('selected_bases')
    if not selected_bases:
        flash("Пожалуйста, выберите базы данных для выполнения действия.", "warning")
        return redirect(url_for('index'))
    if action == 'delete':
        delete_bases(selected_bases)
    elif action == 'export':
        return export_bases(selected_bases)
    elif action == 'archive':
        return archive_bases(selected_bases)
    return redirect(url_for('index'))

def delete_bases(base_ids):
    try:
        for base_id in base_ids:
            base = db.session.get(BaseModel, base_id)
            if base:
                db.session.delete(base)
        db.session.commit()
        flash("Базы успешно удалены!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении баз: {e}", "danger")

def export_bases(base_ids):
    try:
        bases_data = []
        for base_id in base_ids:
            base = db.session.get(BaseModel, base_id)
            if base:
                base_details = {
                    'id': base.id,
                    'name': base.name,
                    'server_1c': base.server_1c,
                    'user': base.user,
                    'password': base.password,
                    'repository_path': base.repository_path,
                    'repository_user': base.repository_user,
                    'repository_password': base.repository_password,
                    'extension_name': base.extension_name,
                    'server_sql': base.server_sql,
                    'sql_base': base.sql_base
                }
                bases_data.append(base_details)
        
        # Сохранение данных в файл
        json_data = json.dumps(bases_data, ensure_ascii=False, indent=4)
        buffer = BytesIO()
        buffer.write(json_data.encode('utf-8'))
        buffer.seek(0)
        
        return send_file(buffer, as_attachment=True, download_name="exported_bases.json", mimetype="application/json")
    except Exception as e:
        flash(f"Ошибка при экспорте баз: {e}", "danger")
        return redirect(url_for('index'))

def archive_bases(base_ids):
    try:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for base_id in base_ids:
                base = db.session.get(BaseModel, base_id)
                if base:
                    base_details = {
                        'id': base.id,
                        'name': base.name,
                        'server_1c': base.server_1c,
                        'user': base.user,
                        'password': base.password,
                        'repository_path': base.repository_path,
                        'repository_user': base.repository_user,
                        'repository_password': base.repository_password,
                        'extension_name': base.extension_name,
                        'server_sql': base.server_sql,
                        'sql_base': base.sql_base
                    }
                    json_data = json.dumps(base_details, ensure_ascii=False, indent=4)
                    zip_file.writestr(f"{base.name}.json", json_data)

        zip_buffer.seek(0)
        return send_file(zip_buffer, as_attachment=True, download_name="archived_bases.zip", mimetype="application/zip")
    except Exception as e:
        flash(f"Ошибка при архивировании баз: {e}", "danger")
        return redirect(url_for('index'))

if __name__ == '__main__':
    create_database()
    app.run(debug=True)