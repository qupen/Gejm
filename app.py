from flask import Flask, render_template, request, redirect, url_for, session as login_session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///calendar.db'
app.secret_key = 'supersecretkey'
db = SQLAlchemy(app)

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    attendees = db.Column(db.String(250), nullable=True)
    creator = db.Column(db.String(50), nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

@app.route('/')
def index():
    sessions = Session.query.filter(Session.date >= datetime.now().date()).order_by(Session.date.asc()).all()
    for session in sessions:
        session.days_left = (session.date - datetime.now().date()).days
    return render_template('index.html', sessions=sessions, user=login_session.get('user'))

@app.route('/select_user', methods=['GET', 'POST'])
def select_user():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            username = request.form['username']
            if not User.query.filter_by(name=username).first():
                new_user = User(name=username)
                db.session.add(new_user)
                db.session.commit()
        elif action == 'edit':
            user_id = request.form['user_id']
            username = request.form['username']
            user = User.query.get(user_id)
            if user:
                user.name = username
                db.session.commit()
        elif action == 'delete':
            user_id = request.form['user_id']
            user = User.query.get(user_id)
            if user:
                db.session.delete(user)
                db.session.commit()
        elif action == 'select':
            username = request.form['username']
            login_session['user'] = username
            return redirect(url_for('index'))
    users = User.query.all()
    return render_template('select_user.html', users=users)


@app.route('/logout')
def logout():
    login_session.pop('user', None)
    return redirect(url_for('select_user'))

@app.route('/add', methods=['POST'])
def add():
    if 'user' not in login_session:
        return redirect(url_for('select_user'))
    
    date = datetime.strptime(request.form['date'], '%Y-%m-%d')
    time = request.form['time']
    name = request.form['name']
    creator = login_session['user']

    new_session = Session(date=date, time=time, name=name, attendees=creator+'', creator=creator)
    db.session.add(new_session)
    db.session.commit()
    return redirect(url_for('index'))



@app.route('/delete_session/<int:id>', methods=['POST'])
def delete_session(id):
    session = db.session.get(Session, id)
    if session:
        db.session.delete(session)
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/attend/<int:id>')
def attend(id):
    if 'user' not in login_session:
        return redirect(url_for('select_user'))
    session = db.session.get(Session, id)
    attendees = session.attendees.split(',') if session.attendees else []
    if login_session['user'] not in attendees:
        attendees.append(login_session['user'])
    else:
        attendees.remove(login_session['user'])
    session.attendees = ','.join(attendees)
    db.session.commit()
    return redirect(url_for('index'))



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8000)
