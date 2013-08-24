pyboard
====

Installation
----

Run `$ ./install.sh`

Running
----

Included is a sample config.py file for running with [gunicorn](http://gunicorn.org/).
You can start it as such from the pyboard directory

```bash
$ gunicorn -c config.py main:app
```

note: you will have to either run as root (not recommended) or use something
like [authbind](http://manpages.ubuntu.com/manpages/hardy/man1/authbind.1.html) to bind to port 80.
