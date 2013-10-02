pyboard
====

Installation
----

Install dependencies (through `virtualenv` or with `sudo`):

```bash
$ pip install -U -r requirements.txt
```

Create skeleton files:

```bash
$ ./install.sh
```

If you want to use LDAP authentication (currently the only supported method),
you will have to install the `python-ldap` package.

Running
----

Included is a sample config.py file for running with [gunicorn](http://gunicorn.org/).
You can start it as such from the pyboard directory

```bash
$ gunicorn -c config.py main:app
```

note: you will have to either run as root (not recommended) or use something
like [authbind](http://manpages.ubuntu.com/manpages/hardy/man1/authbind.1.html) to bind to port 80.

If you want to simply run the development server, use this:

```bash
$ python main.py
```
