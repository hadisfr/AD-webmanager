import argparse
import glob
import importlib
import logging
import os
import sys
from datetime import date
from flask import Flask, g
from waitress import serve

from libs.common import ReverseProxied
from libs.common import iri_for as url_for
from settings import Settings


if Settings.USE_LOGGING:
    import logging
    import sys

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', 
                                  '%Y-%m-%d %H:%M:%S')

    stdout_handler = logging.StreamHandler(sys.stderr)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(f'./logs/{date.today()}-v3.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)


def get_app_prefix():
    # Check if running from bzr
    for path in ['libs', 'plugins', 'static', 'templates']:
        if not os.path.exists(path):
            app_prefix = "/opt/samba4-manager-master/"
            break
    else:
        app_prefix = "."

    if not os.path.exists(app_prefix):
        raise Exception("Missing app dir: %s" % app_prefix)

    sys.path.append(app_prefix)
    return app_prefix


def load_plugins(app_prefix: str):
    for plugin_file in glob.glob("%s/plugins/*.py" % app_prefix):
        plugin_name = os.path.basename(plugin_file).replace('.py', '')
        if plugin_name == "__init__":
            continue
        plugin = importlib.import_module("plugins.%s" % plugin_name)
        plugin.init(app)


parser = argparse.ArgumentParser(description="Samba4 Gestor Web")
args = parser.parse_args()

# Prepare the web server
app_prefix = get_app_prefix()
app = Flask(__name__,
            static_folder=os.path.join(app_prefix, "static"),
            template_folder=os.path.join(app_prefix, "templates"))
app.config.from_object(Settings)
app.jinja_env.globals['url_for'] = url_for

if 'URL_PREFIX' in app.config:
    app.wsgi_app = ReverseProxied(app.wsgi_app, app.config['URL_PREFIX'])

load_plugins(app_prefix)


@app.before_request
def pre_request():
    """
        Setup any of the global variables before the request is processed.
    """
    g.menu = [
        (url_for("core_index"), "My Account"),
        (url_for("tree_base"), u"Directory"),
        (url_for("core_logout"), "Log out"),
    ]

    # LDAP connection settings
    g.ldap = {'domain': app.config['LDAP_DOMAIN'], 'dn': app.config['LDAP_DN'], 'server': app.config['LDAP_SERVER'],
              'search_dn': app.config['SEARCH_DN']}

    # The various caches
    g.ldap_cache = {}
    g.app_version = "v1.0.1"


if __name__ == '__main__':
    if app.config['DEV']:
        app.run(host='0.0.0.0', port=8080)
    else:
        serve(app, host="0.0.0.0", port=8080)
