from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import stripe
from flask_migrate import Migrate
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, URL, Optional
from flask import flash
from datetime import datetime, timezone, timedelta







app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production


# Configure PostgreSQL or fallback to SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://myapp_r6n3_user:H6R5XiPx4EL8gevrbW4ySEjZIhf72U3y@dpg-d1i13dodl3ps73b1ktc0-a.oregon-postgres.render.com/myapp_r6n3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ----------------------------
# Models
# ----------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_subscribed = db.Column(db.Boolean, default=False)

    # Profile Info
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    preferred_job_type = db.Column(db.String(50))  # Remote / Hybrid / Onsite
    preferred_industries = db.Column(db.Text)      # Eg: IT, Healthcare, Marketing
    skills = db.Column(db.Text)
    experience = db.Column(db.Text)
    education = db.Column(db.Text)

    applications = db.relationship('JobApplication', back_populates='user', lazy=True, cascade='all, delete-orphan')




class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255))
    country = db.Column(db.String(100))
    industry = db.Column(db.String(255))
    location_type = db.Column(db.String(50))
    link = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    
    posted_date = db.Column(db.DateTime, default=datetime.utcnow)  # When job was posted
    expiry_days = db.Column(db.Integer, default=30)

    applications = db.relationship(
        'JobApplication', 
        back_populates='job', 
        lazy=True, 
        cascade='all, delete-orphan'
    )


class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id', ondelete='CASCADE'), nullable=False)
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='applications')
    job = db.relationship('Job', back_populates='applications')

class JobForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    company = StringField('Company', validators=[DataRequired()])
    location = StringField('Location', validators=[Optional()])
    country = SelectField(
        'Country', 
        choices=[
            ('', 'Select Country'),
            ('United Kingdom', 'United Kingdom'),
            ('United States', 'United States'),
            ('Canada', 'Canada'),
            ('India', 'India'),
            ('Germany', 'Germany'),
            ('Australia', 'Australia'),
            # Add more countries as needed
        ], 
        validators=[Optional()]
    )
    industry = StringField('Industry', validators=[Optional()])
    location_type = SelectField('Location Type', choices=[('Remote', 'Remote'), ('Onsite', 'Onsite'), ('Hybrid', 'Hybrid')])
    link = StringField('Job Link', validators=[DataRequired(), URL()])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Add Job')





def cleanup_expired_jobs():
    now = datetime.now(timezone.utc)  # timezone-aware UTC datetime
    expired_jobs = []
    for job in Job.query.all():
        if job.posted_date is None:
            expired_jobs.append(job)
            continue
        
        expiry = job.expiry_days if job.expiry_days is not None else 30
        
        # Ensure posted_date is timezone-aware for comparison:
        posted_date = job.posted_date
        if posted_date.tzinfo is None:
            # Convert naive posted_date to aware (UTC)
            posted_date = posted_date.replace(tzinfo=timezone.utc)
        
        if posted_date + timedelta(days=expiry) < now:
            expired_jobs.append(job)

    for job in expired_jobs:
        db.session.delete(job)
    db.session.commit()

# ----------------------------
# Routes
# ----------------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/add-job', methods=['GET', 'POST'])
def add_job():
    form = JobForm()
    if form.validate_on_submit():
        job = Job(
    title=form.title.data,
    company=form.company.data,
    location=form.location.data,
    country=form.country.data,
    industry=form.industry.data,
    location_type=form.location_type.data,
    link=form.link.data,
    description=form.description.data
)

        db.session.add(job)
        db.session.commit()
        flash('Job added successfully!', 'success')
        return redirect(url_for('add_job'))
    return render_template('admin.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return "User already exists."
        new_user = User(email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect('/jobs') #if user.is_subscribed else redirect('/subscribe')
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/subscribe')
def subscribe():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])

    checkout_session = stripe.checkout.Session.create(
        customer_email=user.email,
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'unit_amount': 1000,
                'product_data': {'name': 'Monthly Access'},
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=url_for('payment_success', _external=True),
        cancel_url=url_for('payment_cancel', _external=True)
    )
    return redirect(checkout_session.url, code=303)

@app.route('/payment-success')
def payment_success():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user.is_subscribed = True
        db.session.commit()
    return redirect('/jobs')

@app.route('/payment-cancel')
def payment_cancel():
    return "Payment was cancelled. <a href='/'>Go back</a>"

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

# ----------------------------
# Jobs Page (Replaces Chat)
# ----------------------------
@app.route('/jobs', methods=['GET', 'POST'])
def jobs():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])

    # Get all job IDs the user has already applied to
    applied_job_ids = [app.job_id for app in user.applications]

    # Fetch jobs
    applied_jobs = Job.query.filter(Job.id.in_(applied_job_ids)).all()
    available_jobs = Job.query.filter(~Job.id.in_(applied_job_ids)).all()

    return render_template(
        'jobs.html',
        user=user,
        applied_jobs=applied_jobs,
        available_jobs=available_jobs,
        is_subscribed=user.is_subscribed
    )


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user.full_name = request.form.get('full_name')
        user.phone = request.form.get('phone')
        user.address = request.form.get('address')
        user.country = request.form.get('country')
        user.city = request.form.get('city')
        user.preferred_job_type = request.form.get('preferred_job_type')
        user.preferred_industries = ','.join(request.form.getlist('preferred_industries'))  # multiple checkboxes
        user.skills = request.form.get('skills')
        user.experience = request.form.get('experience')
        user.education = request.form.get('education')

        db.session.commit()
        return redirect('/dashboard')

    return render_template('profile.html', user=user)




@app.route('/admin/delete-job/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    flash('Job deleted successfully', 'success')
    return redirect(url_for('add_job'))  # Redirect back to admin page (add_job route)


@app.route('/apply', methods=['POST'])
def apply():
    if 'user_id' not in session:
        return redirect('/login')

    try:
        job_id = int(request.form['job_id'])
    except (ValueError, KeyError):
        flash("Invalid job selection.", "error")
        return redirect('/jobs')

    user = User.query.get(session['user_id'])
    job = Job.query.get(job_id)

    if not job:
        flash("Job does not exist.", "error")
        return redirect('/jobs')

    # Check if application already exists
    existing_application = JobApplication.query.filter_by(user_id=user.id, job_id=job.id).first()
    if not existing_application:
        new_application = JobApplication(user_id=user.id, job_id=job.id)
        db.session.add(new_application)
        db.session.commit()
        flash("Applied successfully!", "success")
        # Trigger any external auto-apply logic here if needed
    else:
        flash("You have already applied to this job.", "info")

    return redirect('/jobs')

# ----------------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        cleanup_expired_jobs()
    app.run(debug=True)
    