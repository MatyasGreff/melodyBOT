#importing modules
import secrets
from melodyBOT.forms import RegistrationForm, LoginForm, GenerationForm, UpdateAccountForm, RequestResetForm, ResetPasswordForm, MIDIPlayer
from flask import render_template, url_for, flash, redirect, request, send_file
from melodyBOT.models import User
from melodyBOT import app, db, bcrypt, mail
from flask_login import login_user
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
import os
import subprocess

#defining route for / and /home
@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')

#defining route for /about
@app.route("/about")
def about():
    return render_template('about.html', title='About')


#function for Midi Player, this will be called from the MIDI_Player route
#the uploaded files are renamed to random generated name, to avoid matching filenames
def load_midi_player(form_melody):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_melody.filename)
    melody_fn = random_hex + f_ext
    melody_path = os.path.join(app.root_path, 'static/MIDIPlayer_melodies', melody_fn)
    form_melody.save(melody_path)

    return melody_fn
#melody renamed, saved, and filename with extension is returned



#same idea as the previous function, this is for melody generation from a primer melody
#this function will be called from the app_values route
def save_primer(form_primer):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_primer.filename)
    primer_fn = random_hex + f_ext
    primer_path = os.path.join(app.root_path, 'static/primer_melodies', primer_fn)
    form_primer.save(primer_path)

    return primer_path

#this function is responsible for fetching the most recently generated melody for a user
def get_generated_path(output_folder):
    file_gen_string = 'ls -lrt melodyBOT/static/outputs/{0} | tail -n 1; exit 0'.format(current_user.output_folder)
    generated_fname = subprocess.check_output(file_gen_string, stderr=subprocess.STDOUT, shell=True)
    generated_fname = str(generated_fname[-25:-1])  #this type of formatting works, as every generated melody has the same length filename
    generated_fname = generated_fname[3:-1]
    generated_fname = "{0}/{1}".format(output_folder, generated_fname)

    return generated_fname
#this function is called from app_values, the returned path will be turned into an URL, so it is callable from HTML
#the argument this function gets is coming from the database(output_folder)


#this can be considered the main route, as this is where the melody generation takes place
@app.route("/app_values", methods=['GET', 'POST'])
@login_required  #this, we will see later as well - self explanatory
def app_values():
    form = GenerationForm()     #this is coming from forms.py, it is also imported at the top of this file
    if form.validate_on_submit(): #error checking, will proceed further only if all the imputs are valid
        if form.primer_melody.data:
            primer_file = save_primer(form.primer_melody.data)
            current_user.primer_melody = primer_file
            midiormelody = "midi"
        else:
            current_user.primer_melody = '"[60]"'
            midiormelody = "melody"
        #the if-else statement above defines if the generation will be based on a primer melody or a single note
        generate_string = "melody_rnn_generate --config={0} --bundle_file={0}.mag --output_dir=melodyBOT/static/outputs/{1} --num_outputs=1 --num_steps={2} --primer_{3}={4}".format(form.model.data, current_user.output_folder, form.num_steps.data, midiormelody, current_user.primer_melody)
        #the generate_string variable is a string that will be fed into the generation variable, this is where the actual MIDI generation happens
        generation = os.system(generate_string)
        flash(f'Melody is generated', 'success')
        generated_fname = get_generated_path(current_user.output_folder) #calls the function stated above
        generated_fname = url_for('static', filename='outputs/' + generated_fname) #makes the most recently generated melody a callable URL
        return render_template('app_values.html', title='App_values', form=form, generated_fname=generated_fname, generation=generation)
    return render_template('app_values.html', title='App_values', form=form) #returning template, form and variables


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('app_values')) #if the user is already logged in, will be redirected to generation page
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password, output_folder=form.username.data)
        db.session.add(user) #User is a database model defined in models.py
        db.session.commit()  #If the form validates, new user is added
        flash(f'Account created for {form.username.data}!', 'success')
        make_folder = "mkdir melodyBOT/static/outputs/{0}".format(form.username.data)
        make_saved_folder = "mkdir melodyBOT/static/outputs/{0}/saved".format(form.username.data)
        os.system(make_folder)
        os.system(make_saved_folder) #user output folder is also created
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

#route for Login
@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('app_values'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('app_values'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

#route for Logout
@app.route("/logout", methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect(url_for('home'))

#account route, user can change name/email here
@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pic/profile_pic.jpg')
    return render_template('account.html', title='Account', image_file=image_file, form=form)

#in case of a forgotten password, this function takes care of the password reset email
#this function will be called from the reset_password route
def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request', sender='matyas.greff1991@gmail.com', recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)

#reset password route
@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('app_values'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)

#After following the link from the password reset email, this is the route the user will get

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('app_values'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash(f'Your password has been updated.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)

#Some devices are not able to play .mid and .midi files by default, I made an in-browser MIDI player available for all users
@app.route("/MIDI_player", methods=['GET', 'POST'])
def Play_MIDI():
    form = MIDIPlayer()
    if form.validate_on_submit():
        melody_file = load_midi_player(form.melody.data)
        saved_melody = url_for('static', filename='MIDIPlayer_melodies/' + melody_file)
        return render_template('MIDI_player.html', title='MIDI Player', form=form, saved_melody=saved_melody)
    return render_template('MIDI_player.html', title='MIDI Player', form=form)

#Random generated 45 sample MIDI files using Magenta, this is the route for those files
@app.route("/samples", methods=['GET', 'POST'])
def Samples():
    samples_list = []
    directory = "melodyBOT/static/samples"
    for sample in os.listdir(directory):
        temp = url_for('static', filename='samples/' + sample)
        samples_list.append(temp)
        #populate the list with callable URLs, a for loop will display the files in samples.html
    return render_template('samples.html', title='Samples', samples_list=samples_list)

@app.route('/my-link/')
def my_link():
    file_to_be_saved = get_generated_path(current_user.output_folder)
    move_file = "cp melodyBOT/static/outputs/{0} melodyBOT/static/outputs/{1}/saved".format(file_to_be_saved, current_user.output_folder)
    os.system(move_file)
    flash(f'Melody is saved in your online library', 'info')

    return redirect(url_for('app_values'))

@app.route("/saved_melodies", methods=['GET', 'POST'])
def saved_melodies():
    saved_melodies_list = []
    directory = "melodyBOT/static/outputs/{0}/saved".format(current_user.output_folder)
    for melody in os.listdir(directory):
        temp = url_for('static', filename='outputs/' + current_user.output_folder + '/saved/' + melody)
        saved_melodies_list.append(temp)
    number_of_files = len(saved_melodies_list)
    return render_template('saved_melodies.html', title='Saved Melodies', saved_melodies_list=saved_melodies_list, number_of_files=number_of_files)


@app.route('/delete_melody', methods=['POST'])
def delete_melody():
    melody_to_delete = request.form['del_mel']
    delete_string = "rm melodyBOT/{0}".format(melody_to_delete)
    os.system(delete_string)
    return redirect(url_for('saved_melodies'))

