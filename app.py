from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class BaseModel(db.Model):
    __tablename__ = 'bases'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    server_1c = db.Column(db.String(80), nullable=False)
    user = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(80), nullable=False)
    repository_path = db.Column(db.String(120), nullable=False)
    repository_user = db.Column(db.String(80), nullable=False)
    repository_password = db.Column(db.String(80), nullable=False)
    extension_name = db.Column(db.String(80), nullable=True)
    server_sql = db.Column(db.String(80), nullable=False)
    sql_base = db.Column(db.String(80), nullable=False)

def create_database():
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table('bases'):
            db.create_all()
            print("Database created and populated.")
            populate_database()
        else:
            print("Database already exists.")
            clear_database()
            print("Database cleared.")
            populate_database()
        print_database_contents()

def clear_database():
    try:
        db.session.query(BaseModel).delete()
        db.session.commit()
        print("All records deleted successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Error occurred while deleting records: {e}")

def populate_database():
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
    try:
        bases = BaseModel.query.all()
        for base in bases:
            print(f'ID: {base.id}, Name: {base.name}, Server 1C: {base.server_1c}')
        if not bases:
            print("Database is empty.")
    except Exception as e:
        print(f"Error occurred while fetching records: {e}")

@app.route('/')
def index():
    bases = BaseModel.query.all()
    return render_template('index.html', bases=bases)

if __name__ == '__main__':
    create_database()
    app.run(debug=True)