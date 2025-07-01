from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import stripe
from flask_migrate import Migrate

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure value in production

# Configure PostgreSQL or fallback to SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_subscribed = db.Column(db.Boolean, default=False)

# --- ROUTES ---

# Landing page (always shown first)
@app.route('/')
def index():
    return render_template('index.html')

# Register
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

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.id
            # Redirect based on subscription status
            return redirect('/chat') if user.is_subscribed else redirect('/subscribe')
        return "Invalid credentials"
    return render_template('login.html')


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Stripe checkout
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

# Stripe success
@app.route('/payment-success')
def payment_success():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user.is_subscribed = True
        db.session.commit()
    return redirect('/chat')

# Stripe cancel
@app.route('/payment-cancel')
def payment_cancel():
    return "Payment was cancelled. <a href='/'>Go back</a>"

# Protected dashboard (optional)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

# Subscriber-only chat page
@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    if not user or not user.is_subscribed:
        return redirect('/subscribe')

    return render_template('chat.html', user=user)

# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
