# Flask imports
from flask import Flask
from flask import abort, redirect, session, flash
from flask import render_template, url_for
from flask import request
from flask import send_file
from werkzeug import secure_filename

# Python imports
from datetime import datetime
from functools import wraps
import os
import random
import sha
import shutil
import smtplib
import subprocess
import tarfile
import zipfile
try:
	import ldap
except:
	print "ldap not loaded"
from email.mime.text import MIMEText

# Pyboard imports
import serverconfig

app = Flask(__name__)
app.secret_key = serverconfig.app_secret_key

def send_email(me = None, you = None, subject = 'Notification', body = None):
	if not me:
		me = serverconfig.email_from
	if not you or not body:
		return

	if type(you) is str or type(you) is unicode:
		you = [you]

	message = MIMEText(body)
	message['Subject'] = subject
	message['From'] = me
	message['To'] = ', '.join(you)

	s = smtplib.SMTP('localhost')
	s.sendmail(me, you, message.as_string())
	s.quit()

def requires_login(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		if 'username' not in session:
			flash('You must be logged in to view this page.')
			return render_template('login.html')

		return func(*args, **kwargs)
	return wrapper

def validate_login(username, password):
	server = serverconfig.ldap_server
	con = ldap.initialize(server)
	dn = serverconfig.make_dn(username)
	rv = con.simple_bind(dn, password)

	try:
		r = con.result(rv)
		if r[0] == 97:
			return True
	except:
		pass

	return False

def handle_file(file_path):
	return_string = ""

	dir = os.path.dirname(file_path)
	ufile = os.path.basename(file_path)

	ext = ufile.split(".")[1:]
	ext = ".".join(ext)

	pdir = os.path.abspath(os.curdir)

	os.chdir(dir)

	if ext == "tar" or ext == "tar.gz":
		return_string += "tar or tar.gz file extension found\n"
		try:
			tf = tarfile.open(ufile)
			tf.extractall()
		except:
			return_string += "ERROR: could not open tar(.gz) file " + ufile + "\n"
			os.chdir(pdir)
			return return_string
		os.remove(ufile)
	elif ext == "zip":
		return_string += "zip file extension found\n"
		try:
			zf = zipfile.ZipFile(ufile)
			zf.extractall()
		except:
			return_string += "ERROR: could not open zip file " + ufile + "\n"
			os.chdir(pdir)
			return return_string
		os.remove(ufile)
	else:
		return_string += "Can't work with " + ufile + ". Don't know how.\n"
		os.chdir(pdir)
		return return_string

	return_string += "file successfully extracted\n"

	find = subprocess.Popen('find .', shell=True, stdout=subprocess.PIPE)
	return_string += "-\n" + find.communicate()[0].strip() + "\n-\n"

	os.mkdir('bin')
	return_string += "---running javac---\n"
	java = subprocess.Popen('javac -d bin -cp .:/usr/share/java/junit.jar **/*.java', shell=True, executable="/bin/zsh", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	jout = java.communicate()
	if jout[0] or jout[1]:
		return_string += "---javac error/warning output---\n"
	else:
		return_string += "---compilation successful---\n"
	if jout[0]:
		return_string += jout[0] + "\n"
	if jout[1]:
		return_string += jout[1] + "\n"


	os.chdir(pdir)

	return return_string

def get_submissions(section, assignment):
	pdir = os.path.abspath(os.curdir)
	dir = "files/" + "/" + section + "/" + assignment + "/"
	try:
		os.chdir(dir)
	except:
		os.chdir(pdir)
		return None
	os.chdir('..')
	file_name = section + "_" + assignment + ".tar.gz"
	tar = tarfile.open(file_name, "w:gz")
	tar.add(assignment)
	tar.close()

	os.chdir(pdir)

	shutil.move(dir + '../' + file_name, "static/" + file_name)
	return "static/" + file_name

def get_user_info(username):
	return [line.strip() for line in open('emails/' + username) if line.strip()]

@app.route('/', methods=['GET', 'POST'])
@requires_login
def index():
	if request.method == 'POST':
		name = request.form['id']
		ufile = request.files['file']
		section = request.form['section']
		filename = secure_filename(ufile.filename)
		assignment = request.form['ass']
		d = datetime.now()
		time_stamp = d.strftime("%Y-%m-%d-%H-%M-%S")
		upload_dir = "files/" + "/" + section + "/" + assignment + "/" + name + "/" + time_stamp + "/"

		try:
			os.makedirs(upload_dir)
		except:
			pass # uhh wat FIXME

		full_path = upload_dir + filename
		ufile.save(full_path)

		verification_code = sha.new(name+'_'+assignment).hexdigest()
		# FIXME template
		send_email(you = name + '@binghamton.edu',
			subject = 'Submission Received',
			body = "Your submission for assignment `" + assignment + "' was received.\n\nYour confirmation code is " + verification_code)

		output = handle_file(full_path)
		return render_template('upload.html', title='Upload',
			name=name,
			filename=filename,
			section=section,
			assignment=assignment,
			output=output)
	else:
		assignments = [line.strip() for line in open('assignments') if line.strip()]
		assignments.reverse()
		sections = sorted([line.strip().split('\t') for line in open('sections') if line.strip()])
		return render_template('index.html', title='Submit',
			sections = sections,
			assignments = assignments)

@app.route('/download/<section>/<assignment>', methods=['GET', 'POST'])
def download(section, assignment):
	if request.method == 'GET':
		# FIXME #5, #7
		return "<form method=\"POST\" action=/download/"+section+"/"+assignment+"><input type=\"password\" name=\"password\" /></form>"
	else:
		if sha.new(request.form['password']).hexdigest() == '3c580cd7d19aeb7f8b70b53fd15fe7b9371c1598':
			file_name = get_submissions(section, assignment)
			if file_name is None:
				return abort(404)
			return send_file(file_name, as_attachment=True)
		else:
			return abort(403)

@app.route('/emails')
@requires_login
def emails():
	users = sorted(os.listdir('emails'))
	emails = [get_user_info(user)[0] for user in users]
	return render_template('emails.html', title='Email List', users=zip(users, emails))

@app.route('/emails/edit/<name>', methods=['GET', 'POST'])
def edit(name):
	if request.method == 'GET':
		return "<form method=\"POST\" action=\"/emails/edit/"+name+"\"><label for=\"email\">new email:</label><input type=\"text\" name=\"email\" /><input type=\"submit\" /></form>- a confirmation email will be sent to your old email address after submission"
	if request.method == 'POST':
		requested_email = request.form['email']
		verification_code = sha.new(str(random.randint(0, 1000000))).hexdigest()

		lines = get_user_info(name)[:2]
		old_email = lines[0]
		lines.append(requested_email)
		lines.append(verification_code)

		temp = open('emails/' + name, 'w')
		temp.write('\n'.join(lines))
		temp.close()

		# FIXME template and actually linkify the text
		send_email(you = old_email,
			subject = 'Email Change Verification',
			body = name + ", your request to change your email address to " + requested_email + " was received.\n\nFollow this link to confirm this action http://leiyu5.cs.binghamton.edu/emails/edit/"+name+"/" + verification_code)

		return redirect("/emails")

@app.route('/emails/edit/<name>/<code>')
def confirm(name, code):
	lines = get_user_info(name)
	try:
		if lines[3] == code:
			temp = open('emails/' + name, 'w')
			temp.write('{}\n{}\n'.format(lines[2], lines[1]))
			temp.close()

			return redirect("/emails")
	except:
		pass
	return abort(403)

@app.route('/emails/to/<to>', methods=['GET', 'POST'])
def email_to(to):
	if request.method == 'GET':
		return render_template('compose.html', to=to)
	else:
		yous = []

		users = sorted(os.listdir('emails'))
		for user in users:
			info = get_user_info(user)
			email = info[0]
			section = info[1]

			if to == 'a0' or to == section:
				yous.append(email)

		send_email(me = request.form['from'],
			you = yous,
			subject = request.form['subject'],
			body = request.form['body'])

		return "message sent successfully"

@app.route('/grades')
@requires_login
def grades():
	grades = sorted([line.strip().split('\t') for line in open('grades/' + session['username']) if line.strip()])
	return render_template('grades.html', grades=grades)

@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'GET':
		return render_template('login.html')
	else:
		if validate_login(request.form['username'], request.form['password']):
			session['username'] = request.form['username']
			return redirect(url_for('index'))

		flash('Invalid login')
		return redirect(url_for('login'))

@app.route('/logout')
def logout():
	session.pop('username', None)
	return redirect(url_for('login'))

@app.errorhandler(400)
@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(500)
def view_error(error):
	try:
		return render_template('error.html',
			error = '{} Error'.format(error.code),
			desc = error.description), error.code

	except:
		return render_template('error.html',
			error = 'Oh my',
			desc = 'Something went wrong.')

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True)
