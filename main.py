from flask import Flask
from flask import request
from flask import render_template
from flask import make_response
from flask import send_file
from flask import send_from_directory
from datetime import datetime, date
from werkzeug import secure_filename
import sha
import os
import tarfile
import zipfile
import subprocess
import glob
import shutil
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

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
		return render_template('index.html')

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


if __name__ == '__main__':
#	app.debug = True
#	app.run(host='127.0.0.1', port=3444)
	app.run(host='0.0.0.0', port=80)
