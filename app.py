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
from wtforms.validators import Email
from werkzeug.utils import secure_filename
from flask import make_response
from flask import render_template, make_response
from xhtml2pdf import pisa
from io import BytesIO
from flask import Response
from flask import send_file
from fpdf import FPDF
import io
from flask import send_file
import smtplib  # or use Flask-Mail
from email.message import EmailMessage
from io import BytesIO
from flask_login import login_required
from flask_login import LoginManager, current_user
import google.generativeai as genai
from flask_mail import Mail, Message
from wtforms.validators import DataRequired, Email










app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production

# Configure PostgreSQL or fallback to SQLite
app.config['MAIL_DEFAULT_SENDER'] = 'starbridgeconsultancy@gmail.com'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://myapp_r6n3_user:H6R5XiPx4EL8gevrbW4ySEjZIhf72U3y@dpg-d1i13dodl3ps73b1ktc0-a.oregon-postgres.render.com/myapp_r6n3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
API_KEY = "AIzaSyA_84rmTgnFdvzjpFdB8p3xYoziCVbcEic"  # Be cautious with hardcoded keys
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'starbridgeconsultancy@gmail.com'        # Use your real email
app.config['MAIL_PASSWORD'] = 'gooh wfay uxur yhsa'           # Your app-specific password

# ✅ Then: Initialize Flask-Mail
mail = Mail(app)

app.config["UPLOAD_FOLDER"] = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "txt"}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Gemini setup
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")
chat = model.start_chat()

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # or your actual login route

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # assuming you're using SQLAlchemy

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
    email = db.Column(db.String(255))  # <--- NEW FIELD
    description = db.Column(db.Text)
    posted_date = db.Column(db.DateTime, default=datetime.utcnow)
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
    email = StringField('Application Email', validators=[Optional(), Email()])
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

class CVPDF(FPDF):
    def header(self):
        # Header with user name and contact
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, self.name, ln=True)

        self.set_font("Helvetica", "", 10)
        self.set_text_color(0)
        if self.location:
            self.cell(0, 6, self.location, ln=True)
        if self.phone:
            self.cell(0, 6, f"Phone: {self.phone}", ln=True)
        if self.email:
            self.cell(0, 6, f"Email: {self.email}", ln=True, link=f"mailto:{self.email}")
        if self.linkedin:
            self.set_text_color(0, 102, 204)
            self.cell(0, 6, f"LinkedIn: {self.linkedin}", ln=True, link=self.linkedin)
        self.set_text_color(0)
        self.ln(5)

    def section_title(self, title):
        self.set_fill_color(224, 224, 224)
        self.set_text_color(0, 51, 102)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, f"  {title}", ln=True, fill=True)
        self.set_text_color(0)
        self.set_font("Helvetica", "", 10)

    def section_body(self, text):
        if text:
            self.multi_cell(0, 6, text.strip())
            self.ln(2)

        
    def generate_email_body(user, job):
     return f"""Dear {job.company_name or 'Hiring Manager'},

I am excited to apply for the {job.title} position listed by your company.

My background in {user.profession or 'relevant field'} and experience in similar roles make me a great candidate for this opportunity. I have attached my CV for your review.

Thank you for your time and consideration. I look forward to the possibility of working with your team.

Sincerely,
{user.full_name}
Email: {user.email}
"""
           

@app.route("/styled-cv")
def styled_cv():
    if 'user_id' not in session:
        return redirect('/login')
    
    user = db.session.get(User, session['user_id'])

    if not user:
        flash("User not found", "error")
        return redirect('/dashboard')

    pdf = CVPDF()
    pdf.name = user.full_name or ""
    pdf.location = f"{user.city}, {user.country}" if user.city and user.country else ""
    pdf.phone = user.phone or ""
    pdf.email = user.email or ""
    pdf.linkedin = ""  # Optional: Add user.linkedin if you store it

    pdf.add_page()

    # Professional Summary (use experience field or separate summary if you add one later)
    if user.experience:
        pdf.section_title("Professional Summary")
        pdf.section_body(user.experience)

    # Left Column Data (skills, preferred industries, etc.)
    if user.skills:
        pdf.section_title("Skills")
        pdf.section_body(user.skills)

    if user.preferred_industries:
        pdf.section_title("Preferred Industries")
        pdf.section_body(user.preferred_industries)

    if user.preferred_job_type:
        pdf.section_title("Preferred Job Type")
        pdf.section_body(user.preferred_job_type)

    # Right Column Data (Education & Experience)
    if user.education:
        pdf.section_title("Education")
        pdf.section_body(user.education)

    # Save to buffer
    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{user.full_name or 'cv'}_CV.pdf"
    )



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
        notify_users_about_new_job(job)
        flash('Job added and users notified!', 'success')
    
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

    user = db.session.get(User, session['user_id'])

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
        user = db.session.get(User, session['user_id'])

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
    user = db.session.get(User, session['user_id'])

    return render_template('dashboard.html', user=user)

# ----------------------------
# Jobs Page (Replaces Chat)
# ----------------------------
@app.route('/jobs', methods=['GET', 'POST'])
def jobs():
    if 'user_id' not in session:
        return redirect('/login')

    user = db.session.get(User, session['user_id'])

    if not user:
        flash("User not found.", "error")
        return redirect('/login')

    # Get jobs the user has already applied to
    applied_job_ids = [app.job_id for app in user.applications]

    # User preferences
    user_skills = set(map(str.strip, user.skills.lower().split(','))) if user.skills else set()
    user_industries = set(map(str.strip, user.preferred_industries.lower().split(','))) if user.preferred_industries else set()
    user_country = user.country.lower() if user.country else ""

    # Get all jobs the user hasn't applied to
    available_jobs = Job.query.filter(~Job.id.in_(applied_job_ids)).all()

    def match_job(job):
        job_industry = (job.industry or '').strip().lower()
        job_location_type = (job.location_type or '').strip().lower()
        job_country = (job.country or '').strip().lower()

        # 1. Job must match user's preferred industries
        if job_industry not in user_industries:
            return False

        # 2. Show remote or international jobs to everyone
        if job_location_type in ['remote', 'international']:
            return True

        # 3. Show local jobs (same country)
        if job_country == user_country:
            return True

        # 4. Otherwise, don't show job
        return False

    # Apply filter
    filtered_jobs = [job for job in available_jobs if match_job(job)]

    # Get jobs the user already applied to
    applied_jobs = Job.query.filter(Job.id.in_(applied_job_ids)).all()

    return render_template(
        'jobs.html',
        user=user,
        applied_jobs=applied_jobs,
        available_jobs=filtered_jobs,
        is_subscribed=user.is_subscribed
    )

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect('/login')

    user = db.session.get(User, session['user_id'])

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

@app.route('/chatbot-ui')
@login_required
def chatbot_ui():
    user = db.session.get(User, session['user_id'])
    if not user or not user.is_subscribed:
        return "Access Denied", 403
    return render_template('chatbot.html', user=user)


@app.route('/chatbot-api', methods=['POST'])
@login_required
def chatbot_api():
    user = db.session.get(User, session['user_id'])
    if not user or not user.is_subscribed:
        return {"reply": "You must be a subscribed user."}, 403

    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return {"reply": "Please enter a job-related question or paste a job description."}

    # Heuristic: detect pasted job descriptions
    is_job_description = any(word in user_message.lower() for word in ['requirements', 'job description', 'we are looking for', 'qualifications']) or len(user_message) > 300

    if is_job_description:
        # Generate tailored CV with Gemini
        prompt = f"""
Generate a professional CV in plain text (not markdown or LaTeX). Use the user's profile below and tailor it to this job description:

Job Description:
{user_message}

User Profile:
Name: {user.full_name}
Phone: {user.phone}
Email: {user.email}
Location: {user.city}, {user.country}
Preferred Job Type: {user.preferred_job_type}
Preferred Industries: {user.preferred_industries}
Skills: {user.skills}
Experience: {user.experience}
Education: {user.education}

Format:
- Start with contact info
- Then PROFESSIONAL SUMMARY
- Then EXPERIENCE
- Then SKILLS
- Then EDUCATION
- Use simple dashes (-) for bullet points.
"""
        try:
            response = model.generate_content(prompt)
            text_cv = response.text.strip()

            # Convert CV to PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Arial", size=12)
            for line in text_cv.split('\n'):
                pdf.multi_cell(0, 10, line)
            buffer = io.BytesIO()
            pdf.output(buffer)
            buffer.seek(0)

            # Store the CV in session or temporary ID for retrieval
            session['cv_pdf'] = buffer.read()
            return {"reply": "✅ Your tailored CV is ready. [Click here to download it](/chatbot-download-cv)"}

        except Exception as e:
            return {"reply": f"❌ Gemini failed to generate your CV: {str(e)}"}

    # Otherwise: handle general job questions
    prompt = f"""
You're a job assistant bot. Only respond to job-related questions.
User Profile:
Name: {user.full_name}
Skills: {user.skills}
Experience: {user.experience}
Education: {user.education}

User Message: {user_message}
"""
    try:
        response = model.generate_content(prompt)
        return {"reply": response.text.strip()}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}, 500


@app.route('/chatbot-download-cv')
@login_required
def chatbot_download_cv():
    pdf_data = session.get('cv_pdf')
    if not pdf_data:
        return "No CV generated yet.", 404

    return send_file(
        io.BytesIO(pdf_data),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="Tailored_CV.pdf"
    )




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

    user = db.session.get(User, session['user_id'])
    job = Job.query.get(job_id)

    if not job:
        flash("Job does not exist.", "error")
        return redirect('/jobs')

    existing_application = JobApplication.query.filter_by(user_id=user.id, job_id=job.id).first()
    if existing_application:
        flash("You have already applied to this job.", "info")
        return redirect('/jobs')

    # Save the application
    new_application = JobApplication(user_id=user.id, job_id=job.id)
    db.session.add(new_application)
    db.session.commit()
    flash("Applied successfully!", "success")

    # --- Step 1: Generate CV ---
    cv_pdf = generate_cv(user)  # should return a BytesIO object

    # --- Step 2: Generate Email Body ---
    email_body = generate_email_body(user, job)

    # --- Step 3: Send Email with Flask-Mail ---
    try:
        msg = Message(
            subject=f"Job Application for {job.title}",
            recipients=[job.email],
            body=email_body,
            reply_to=user.email  # important: so employer replies to applicant, not system
        )

        msg.attach("CV.pdf", "application/pdf", cv_pdf.getvalue())

        mail.send(msg)
        flash("Email sent to the employer!", "success")
    except Exception as e:
        print("Email sending failed:", e)
        flash("Failed to send application email.", "error")

    return redirect('/jobs')
@app.route('/generate-cv')
def generate_cv():
    if 'user_id' not in session:
        return redirect('/login')

    user = db.session.get(User, session['user_id'])

    if not user:
        flash("User not found", "error")
        return redirect('/dashboard')

    # Gemini prompt
    prompt = f"""
Create a clean, modern, ATS-friendly CV in plain text only — no markdown, no asterisks, and no LaTeX. 
Use uppercase section headers (e.g., PROFESSIONAL SUMMARY), simple bullet points (like hyphens), and consistent spacing.

Format and organize it as follows:

Full Name: {user.full_name}
Phone: {user.phone}
Email: {user.email}
Address: {user.address}, {user.city}, {user.country}

Professional Summary:
Write a concise 2–3 sentence summary that highlights the user's experience, goals, and key strengths.

Career Preferences:
Job Type: {user.preferred_job_type}
Industries: {user.preferred_industries}

Experience:
{user.experience}

Skills:
{user.skills}

Education:
{user.education}

Avoid symbols like asterisks, hashtags, or markdown-style headers. The CV should be ATS-parsable.
"""

    try:
        response = model.generate_content(prompt)
        import re

        # Clean raw text
        cv_text = response.text.strip()

        # Remove any repeated personal details
        personal_lines = [
            user.full_name or "",
            user.phone or "",
            user.email or "",
            f"{user.address}, {user.city}, {user.country}"
        ]
        for line in personal_lines:
            cv_text = re.sub(re.escape(line), '', cv_text, flags=re.IGNORECASE)

        # Remove markdown formatting
        cv_text = re.sub(r'\*+|\#+', '', cv_text)

        # PDF class with formatting
        class CVPDF(FPDF):
            def header(self):
                self.set_font("Helvetica", "B", 18)
                self.set_text_color(0, 51, 102)
                self.cell(0, 10, user.full_name or "CV", ln=True)

                self.set_font("Helvetica", "", 10)
                self.set_text_color(0)
                location = f"{user.city}, {user.country}" if user.city and user.country else ""
                if location:
                    self.cell(0, 6, location, ln=True)
                if user.phone:
                    self.cell(0, 6, f"Phone: {user.phone}", ln=True)
                if user.email:
                    self.cell(0, 6, f"Email: {user.email}", ln=True, link=f"mailto:{user.email}")
                self.ln(5)

            def section_title(self, title):
                self.set_fill_color(224, 224, 224)
                self.set_text_color(0, 51, 102)
                self.set_font("Helvetica", "B", 11)
                self.cell(0, 8, f"  {title}", ln=True, fill=True)
                self.set_text_color(0)
                self.set_font("Helvetica", "", 10)

            def section_body(self, text):
                if text:
                    self.multi_cell(0, 6, text.strip())
                    self.ln(2)

        pdf = CVPDF()
        pdf.add_page()

        # Try to split by sections like "PROFESSIONAL SUMMARY:"
        section_titles = re.findall(r'([A-Z][A-Z ]+):', cv_text)
        sections = re.split(r'[A-Z][A-Z ]+:\s*\n?', cv_text)

        if section_titles and len(sections) > 1:
            for title, body in zip(section_titles, sections[1:]):
                pdf.section_title(title.strip())
                pdf.section_body(body.strip())
        else:
            # fallback: render all
            pdf.section_body(cv_text)

        # Output to memory
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        buffer = io.BytesIO(pdf_bytes)

        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{user.full_name or 'CV'}_Gemini_Styled.pdf"
        )

    except Exception as e:
        return f"Error generating CV with Gemini: {e}"
    

def generate_email_body(user, job):
    return f"""
Dear {job.company} Hiring Team,

I hope this message finds you well.

My name is {user.full_name}, and I am writing to express my strong interest in the position of {job.title} at your esteemed organization. I believe my skills and experience make me a great fit for this opportunity.

Please find my CV attached for your consideration. I look forward to the opportunity to contribute to your team.

Sincerely,  
{user.full_name}  
{user.email}
"""


def notify_users_about_new_job(job):
    """Sends an email to all users about a new job posting."""
    from flask import current_app

    users = User.query.all()
    subject = f"New Job Posted: {job.title} at {job.company}"
    for user in users:
        if user.email:  # ensure email exists
            msg = Message(subject, recipients=[user.email])
            msg.body = f"""
Hi {user.full_name},

A new job has just been posted on the platform:

Title: {job.title}
Company: {job.company}
Location: {job.location}, {job.country}
Industry: {job.industry}
Type: {job.location_type}
Link: {job.link}

Description:
{job.description}

Log in to your dashboard to apply or view more jobs.

Best regards,
GoGetJobs Team
"""
            try:
                mail.send(msg)
            except Exception as e:
                print(f"Error sending to {user.email}: {e}")





if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        cleanup_expired_jobs()
    app.run(debug=True)
    

