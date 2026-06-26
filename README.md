# Introduction

This project is a web interface for Active Directory made using `Flask` and
`python-ldap`, focusing on ease of use and simplicity.

It's using the connecting user's credentials to connect to the
directory and allow a variety of operations.

The goal is to be able to do most common directory operations directly
through this web interface rather than have to rely on command tools or
Windows interfaces.

It's compatible with both Windows Active Directory and Samba4 domain controllers.

# History

This project started as a fork of samba4-manager, created by Stéphane Graber
and the Edubuntu community.
Was used internally at Havana's Technology University in 2017, and since it has
received numerous updates, additions, and changes.
We decided to release our version publicly since the original project was not being
regularly updated, until being archived. It has grown since to a much more capable application.

This fork is now maintained by [hadisfr](https://github.com/hadisfr)

# Install and run

Note: all code has only been tested and it's supported to run on Linux and FreeBSD
systems, contributions regarding compatibility with other platforms is welcomed.

## Local config

* Create the `.env` file in the project root directory
  * Set `CSRF\_SECRET\_KEY` to a random string, e.g. using `openssl rand -base64 60 | tr -d '\n'`
  * Set `LDAP\_DOMAIN` to your Directory domain
  * Set `SEARCH\_DN` to your Directory LDAP search base, in a form like `DC=samba,DC=example,DC=com`
  * Set `LDAP\_SERVER` to your Domain Controller IP
  * Use `DEBUG = True` if you want the test server to immediately reload after changes
  * Set `USE_LOGGING = True` if you want to log to files and console, false logs to console only
  * Set `ADMIN\_GROUP` to the security group with read/write permission (default should be `Domain Admins`)
  * Optionally, set `TREE\_WHITELIST` to filter entities, in a form like `DC=samba,DC=example,DC=com`
* Modify `settings.py` to configure some other properties
  * ADD to `TREE\_BLACKLIST `the containers you want to hide in the root directory
  * Add attribute pairs to `SEARCH\_ATTRS` and `TREE\_ATTRIBUTES` to customize the tree view

### Setup Environment

Copy the [`env`](env) file to `.env` and update the settings to match your environment.

```sh
cp .env.example .env
```

## Installing dependencies

You can install the dependencies using `pip` and the supplied [`requirements.txt`](requirements.txt). Especial
consideration to the `python-ldap` dependency, which depends on native C libraries and as such needs
native compilers and tooling to be installed ([check `python-ldap` docs here](https://www.python-ldap.org/en/python-ldap-3.4.0/installing.html#build-prerequisites)).

### For Ubuntu 20.04 or Debian 11

 **Note**: We assume you are running those commands with in the project root directory.

```sh
apt update
apt install python3-venv python3-pip
apt install build-essential python3-dev libldap2-dev libsasl2-dev ldap-utils tox lcov valgrind
python3 -m venv ./venv
source ./venv/bin/activate
pip install -r requirements.txt
```

### For FreeBSD

```sh
pkg install net/py-AD-webmanager
```

## Running

### In local

```sh
python3 ADwebmanager.py
```

### With Docker

```sh
docker build -t <image name> .
# after image succsessfully built
docker run -d -p 8080:8080 <image name>
```

You may then connect through [http://localhost:8080](http://localhost:8080)

# Contributing

Contributions are always appreciated!

The project is under the MIT license.
