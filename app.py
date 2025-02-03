from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///calendar.db'
app.secret_key = os.getenv('SECRET_KEY', 'fallback-secret-key')
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    attendees = db.Column(db.String(250), nullable=True)
    creator = db.Column(db.String(50), nullable=False)
    

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class SMTPConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    smtp_server = db.Column(db.String(100), nullable=False)
    smtp_port = db.Column(db.String(10), nullable=False)
    smtp_username = db.Column(db.String(100), nullable=False)
    smtp_password = db.Column(db.String(100), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)

def send_notification_email(session):
    smtp_config = SMTPConfig.query.first()
    if not smtp_config:
        print("SMTP configuration is not set.")
        return

    subject = "Någon vill panga HS!"
    body = (f"Be there or be a fyrkant!!!\n\n"
            f"Spel: {session.name}\n"
            f"Datum: {session.date}\n"
            f"Tid: {session.time}\n"
            f"HerreSkapare: {session.creator}\n")

    sender_name = "HSGeneralen"
    sender_email = smtp_config.smtp_username

    recipient_emails = [user.email for user in User.query.filter(User.email.isnot(None)).all()]

    try:
        with smtplib.SMTP(smtp_config.smtp_server, int(smtp_config.smtp_port)) as server:
            server.starttls()
            server.login(smtp_config.smtp_username, smtp_config.smtp_password)

            for recipient in recipient_emails:
                msg = MIMEText(body)
                msg["Subject"] = subject
                msg["From"] = f"{sender_name} <{sender_email}>"
                msg["To"] = recipient  # Skickar individuellt

                server.sendmail(sender_email, recipient, msg.as_string())

        print("Notification emails sent successfully.")
    except Exception as e:
        print(f"Failed to send emails: {e}")


@app.route('/')
@login_required
def index():
    sessions = Session.query.filter(Session.date >= datetime.now().date()).order_by(Session.date.asc()).all()
    return render_template('index.html', sessions=sessions, user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(name=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            return "Invalid credentials", 401
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if not User.query.filter_by(name=username).first():
            is_admin = User.query.count() == 0  # First user becomes admin
            new_user = User(name=username, email=email, is_admin=is_admin)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        else:
            return "User already exists", 400
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add', methods=['POST'])
@login_required
def add():
    date = datetime.strptime(request.form['date'], '%Y-%m-%d')
    time = request.form['time']
    name = request.form['name']
    creator = current_user.name

    new_session = Session(date=date, time=time, name=name, attendees=creator+'', creator=creator)
    db.session.add(new_session)
    db.session.commit()

    # Send notification email
    send_notification_email(new_session)

    return redirect(url_for('index'))

@app.route('/delete_session/<int:id>', methods=['POST'])
@login_required
def delete_session(id):
    session = db.session.get(Session, id)
    if session:
        db.session.delete(session)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/attend/<int:id>')
@login_required
def attend(id):
    session = db.session.get(Session, id)
    attendees = session.attendees.split(',') if session.attendees else []
    if current_user.name not in attendees:
        attendees.append(current_user.name)
    else:
        attendees.remove(current_user.name)
    session.attendees = ','.join(attendees)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    if not current_user.is_admin:
        return "Access denied", 403

    smtp_config = SMTPConfig.query.first()

    if request.method == 'POST':
        smtp_server = request.form['smtp_server']
        smtp_port = request.form['smtp_port']
        smtp_username = request.form['smtp_username']
        smtp_password = request.form['smtp_password']

        if not smtp_config:
            smtp_config = SMTPConfig(smtp_server=smtp_server, smtp_port=smtp_port, smtp_username=smtp_username, smtp_password=smtp_password)
            db.session.add(smtp_config)
        else:
            smtp_config.smtp_server = smtp_server
            smtp_config.smtp_port = smtp_port
            smtp_config.smtp_username = smtp_username
            smtp_config.smtp_password = smtp_password
        db.session.commit()
        return "SMTP Uppdaterad!"

    return render_template('config.html', smtp_config=smtp_config)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8000)
