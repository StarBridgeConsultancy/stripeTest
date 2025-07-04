from flask import Blueprint, render_template, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, URL, Optional
from app import db, Job

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
# Setup a secret key for CSRF protection
app.config['SECRET_KEY'] = 'your-secret-key'  # change this in production!

class JobForm(FlaskForm):
    title = StringField('Job Title', validators=[DataRequired()])
    company = StringField('Company', validators=[DataRequired()])
    location = StringField('Location', validators=[Optional()])
    country = StringField('Country', validators=[Optional()])
    industry = StringField('Industry', validators=[Optional()])
    location_type = SelectField('Location Type', choices=[('Remote', 'Remote'), ('Onsite', 'Onsite')])
    link = StringField('Job Link', validators=[DataRequired(), URL()])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Add Job')

@app.route('/admin/add-job', methods=['GET', 'POST'])
def add_job():
    form = JobForm()
    if form.validate_on_submit():
        # Check if job already exists
        exists = Job.query.filter_by(title=form.title.data, company=form.company.data, link=form.link.data).first()
        if exists:
            flash('Job already exists!', 'warning')
        else:
            new_job = Job(
                title=form.title.data,
                company=form.company.data,
                location=form.location.data or '',
                country=form.country.data or '',
                industry=form.industry.data or '',
                location_type=form.location_type.data,
                link=form.link.data,
                description=form.description.data or ''
            )
            db.session.add(new_job)
            db.session.commit()
            flash('Job added successfully!', 'success')
            return redirect(url_for('add_job'))

    return render_template('admin_add_job.html', form=form)
