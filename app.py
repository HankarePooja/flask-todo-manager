from flask import Flask, render_template, request, redirect, session, url_for,flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import case
from functools import wraps
from authlib.integrations.flask_client import OAuth
from itsdangerous import URLSafeTimedSerializer
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or "temporary_secret_for_render"
app.config['GOOGLE_CLIENT_ID'] = os.getenv("GOOGLE_CLIENT_ID")
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv("GOOGLE_CLIENT_SECRET")
serializer = URLSafeTimedSerializer(app.secret_key)

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///app.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=True)

class Todo(db.Model):
    SrNo = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50),nullable=False)
    date = db.Column(db.DateTime,nullable=False)
    priority = db.Column(db.String(50),nullable=False)
    nm = db.Column(db.String(200))  
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

with app.app_context():
    db.create_all()

@app.context_processor
def inject_current_user():
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    return dict(current_user=user)


@app.route("/")
def home():
    return render_template('dashboard.html')

def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first")
            return redirect('/login')
        return view_func(*args, **kwargs)
    return wrapper

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            flash("You were successfully logged in!")
            print("USER LOGGED IN:", session.get('user_id'))
            return redirect('/task')
        else:
            flash("Invalid email or password")
    return render_template('login.html')

@app.route('/google-login')
def google_login():
    print(url_for('google_auth', _external=True))
    return google.authorize_redirect(url_for('google_auth', _external=True))

@app.route('/auth/google')
def google_auth():
    token = google.authorize_access_token()
    user_info = google.get('userinfo').json()
    email = user_info['email']
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, password_hash=None)
        db.session.add(user)
        db.session.commit()
    session['user_id'] = user.id
    flash("Logged in with Google successfully!")
    return redirect('/task')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("User already exists. Please login.")
            return redirect('/login')
        hashed_pw = generate_password_hash(password)
        user = User(email=email, password_hash=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash("Signup successful. Please login.")
        return redirect('/login')
    return render_template('signup.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            token = serializer.dumps(email, salt='reset-password')
            reset_url = url_for('reset_password', token=token, _external=True)
            print("RESET LINK:", reset_url)  
            flash("Password reset link sent to your email")
        else:
            flash("Email not found")
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(
            token,
            salt='reset-password',
            max_age=600 
        )
    except:
        flash("Reset link expired or invalid")
        return redirect('/login')
    user = User.query.filter_by(email=email).first()
    if request.method == 'POST':
        new_password = request.form['password']
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash("Password reset successful. Please login.")
        return redirect('/login')
    return render_template('reset_password.html')

@app.route('/task', methods=['GET', 'POST'])
@login_required
def task():
    if request.method == 'POST':
        nm = request.form['nm']
        task_text = request.form['task']
        status = request.form['status']
        date_str = request.form['date']
        priority = request.form['priority']
        date_obj = datetime.strptime(date_str, "%Y-%m-%dT%H:%M")
        new_todo = Todo(nm=nm,task=task_text,status=status,date=date_obj,priority=priority,user_id=session['user_id'])
        db.session.add(new_todo)
        db.session.commit()
        flash("Your task is successfully submitted!")
        return redirect('/task')
    return render_template('task.html')

@app.route('/table')
@login_required
def table():
    now = datetime.now()
    sort = request.args.get('sort')
    search_query = request.args.get('q')
    query = Todo.query.filter_by(user_id=session['user_id'])
    if search_query:
        query = query.filter(Todo.task.ilike(f"%{search_query}%"))
    if sort == 'date':
        query = query.order_by(Todo.date)
    elif sort == 'status':
        status_order = case((Todo.status == 'Not started', 1),(Todo.status == 'In progress', 2),(Todo.status == 'Done', 3))
        query = query.order_by(status_order)
    elif sort == 'priority':
        priority_order = case((Todo.priority == 'High', 1),(Todo.priority == 'Medium', 2),(Todo.priority == 'Low', 3) )
        query = query.order_by(priority_order)
    allTodo = query.all()
    nm = allTodo[0].nm if allTodo else "My Todo List"
    return render_template('table.html', allTodo=allTodo, nm=nm,now=now)

@app.route("/update/<int:SrNo>", methods=['GET', 'POST'])
@login_required
def update(SrNo):
    todo = Todo.query.filter_by(SrNo=SrNo,user_id=session['user_id']).first_or_404()
    if request.method == 'POST':
        todo.nm = request.form['nm']
        todo.task = request.form['task']
        todo.status = request.form['status']
        todo.priority = request.form['priority']
        date_str = request.form['date']
        todo.date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M")
        db.session.commit()
        flash("Task updated successfully!")
        return redirect("/table")
    return render_template('update.html', todo=todo)

@app.route("/delete/<int:SrNo>")
@login_required
def delete(SrNo):
    todo = Todo.query.filter_by(SrNo=SrNo,user_id=session['user_id']).first_or_404()
    db.session.delete(todo)
    db.session.commit()
    flash("Task deleted successfully!")
    return redirect("/table")

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have logged out successfully")
    return redirect('/')

if __name__ == '__main__':  
   app.run()
