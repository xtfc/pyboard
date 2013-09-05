# Flask imports
from flask import Flask, redirect, session
from flask import make_response
from flask import render_template
from flask import request
from flask import send_file
from flask import send_from_directory
from werkzeug import secure_filename

# Python imports
from datetime import datetime, date
import glob
import os
import random
import re
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

@app.route('/', methods=['GET', 'POST'])
def upload():
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
			pass
		full_path = upload_dir + filename
		ufile.save(full_path)

		verification_code = sha.new(name+'_'+assignment).hexdigest()
		msg = MIMEText("Your submission for assignment `" + assignment + "' was received.\n\nYour confirmation code is " + verification_code)
		me = 'submission@leiyu5.cs.binghamton.edu'
		you = name + '@binghamton.edu'
		msg['Subject'] = 'Submission received'
		msg['From'] = me
		msg['To'] = you
		s = smtplib.SMTP('localhost')
		s.sendmail(me, [you], msg.as_string())
		s.quit()

		output = handle_file(full_path)
		return render_template('upload.html', name=name,
						      filename=filename,
						      section=section,
						      assignment=assignment,
						      output=output)
	else:
		assignments = re.split('\n', subprocess.check_output("tac assignments", shell=True).rstrip())
		return render_template('index.html', assignments=assignments)

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

@app.route('/download/<section>/<assignment>', methods=['GET', 'POST'])
def download(section, assignment):
	if request.method == 'GET':
		return "<form method=\"POST\" action=/download/"+section+"/"+assignment+"><input type=\"password\" name=\"pw\" /></form>"
	else:
		if sha.new(request.form['pw']).hexdigest() == '3c580cd7d19aeb7f8b70b53fd15fe7b9371c1598':
			file_name = get_submissions(section, assignment)
			if file_name is None:
				return "Error, sorry"
			return send_file(file_name, as_attachment=True)
		else:
			return "wrong password"

@app.route('/emails/')
def email():
	users = sorted(os.listdir('emails'))
	emails = [open('emails/' + user).readline().strip() for user in users]
	return render_template('emails.html', users=zip(users, emails))

@app.route('/emails/edit/<name>', methods=['GET', 'POST'])
def edit(name):
	if request.method == 'GET':
		return "<form method=\"POST\" action=\"/emails/edit/"+name+"\"><label for=\"email\">new email:</label><input type=\"text\" name=\"email\" /><input type=\"submit\" /></form>- a confirmation email will be sent to your old email address after submission"
	if request.method == 'POST':
		requested_email = request.form['email']
		old_email = subprocess.check_output("head -n 2 emails/" + name, shell=True).rstrip()
		subprocess.call("echo \"" + old_email + "\n" + requested_email + "\" > emails/" + name, shell=True)

		# send an email confirmation
		verification_code = sha.new(str(random.randint(0, 1000000))).hexdigest()
		subprocess.call("echo " + verification_code + " >> emails/"+name, shell=True)
		msg = MIMEText(name +", your request to change your email address to " + requested_email + " was received.\n\nFollow this link to confirm this action http://leiyu5.cs.binghamton.edu/emails/edit/"+name+"/" + verification_code)
		me = 'emailchange@leiyu5.cs.binghamton.edu'
		you = old_email
		msg['Subject'] = 'Email Change Verification'
		msg['From'] = me
		msg['To'] = you
		s = smtplib.SMTP('localhost')
		s.sendmail(me, [you], msg.as_string())
		s.quit()

		return redirect("/emails")

@app.route('/emails/edit/<name>/<code>')
def confirm(name, code):
	lines = re.split('\n', subprocess.check_output("cat emails/" + name, shell=True).rstrip())
	try:
		if lines[3] == code:
			subprocess.call("echo \"" + lines[2] + "\n" + lines[1] + "\" > emails/" + name, shell=True)
			return redirect("/emails")
	except: pass
	return "no"

@app.route('/emails/to/<to>', methods=['GET', 'POST'])
def email_to(to):
	if request.method == 'GET':
		return "<form method=\"POST\" action=\"/emails/to/"+to+"\"><label for=\"from\">from</label><input type=\"text\" name=\"from\" /><br /><label for=\"subject\">subject</label><input type=\"text\" name=\"subject\" size=50 /><br /><label for=\"body\" style=\"float:left\">body</label><textarea name=\"body\" style=\"width: 80%\" rows=20></textarea><br /><input type=\"submit\" /></form>"
	else:
		msg = MIMEText(request.form['body'])
		me = request.form['from']
		yous = []
		output = subprocess.check_output("ls emails", shell=True).rstrip()
		userids = re.split('\n', output)
		for id in userids:
			lines = re.split('\n', subprocess.check_output("head -n 2 emails/" + id, shell=True).rstrip())
			email = lines[0]
			section = lines[1]
			if to == 'a0' or to == section:
				yous.append(email)
		msg['Subject'] = request.form['subject']
		msg['From'] = me
		msg['To'] = ", ".join(yous)
		s = smtplib.SMTP('localhost')
		s.sendmail(me, yous, msg.as_string())
		s.quit()
		return "message sent successfully"

@app.route('/grades/', methods=['GET', 'POST'])
def grades_login():
	if request.method == 'GET':
		return "<form method=\"POST\" action=\"/grades/\"><label for=\"username\">pods id</label><input type=\"text\" name=\"username\" /><br /><label for=\"pw\">password</label><input type=\"password\" name=\"pw\" /><br /><input type=\"submit\" /></form>"
	else:
		username = request.form['username']
		pw = request.form['pw']
		server = serverconfig.ldap_server
		con = ldap.initialize(server)
		dn = serverconfig.make_dn(username)
		rv = con.simple_bind(dn, pw)
		try:
			r = con.result(rv)
			if r[0] == 97:
				session['username'] = username
				return redirect("/grades/"+username)
		except: pass
		return "nopenope"

@app.route('/grades/<user>')
def grades_show(user):
	if 'username' not in session:
		return "nope"
	logged_in_as = session['username']
	if logged_in_as != user:
		return "nope"
	grades = re.split('\n', subprocess.check_output("cat grades/"+user, shell=True).rstrip())
	html = "<table border=\"1\">"
	html += "<tr><td>Assignment</td><td>Grade</td></tr>"
	for g in grades:
		formatted = re.split('\t', g)
		html += "<tr>"
		html += "<td>" + formatted[0] + "</td><td>" + formatted[1] + "</td>"
		html += "</tr>"
	html += "</table>"
	return html

@app.route('/grades/logout')
def grades_logout():
	session.pop('username', None)
	return redirect("/grades")

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True)
