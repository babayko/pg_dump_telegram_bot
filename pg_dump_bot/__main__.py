# coding: utf-8
import ConfigParser
import getpass
import sys


from .api import ConstantineIII

config = ConfigParser.ConfigParser()
config.read('config.conf')

token = config.get('main', 'bot_token')
database_url = config.get('main', 'database_url')
database_user = config.get('main', 'database_user')
database_password = config.get('main', 'database_password')
dumps_folder = config.get('main', 'dumps_folder')
jobs_names = dict(config._sections['jobs'])

if len(sys.argv) == 5:
    _, database_url, database_user, database_password, dumps_folder = sys.argv
else:
    database_url = input('database url:')
    database_user = input('database user:')
    database_password = getpass.getpass(prompt='database password:')
    dumps_folder = input('dumps folder:')

monsieur = ConstantineIII(
    token, database_url, database_user, database_password, jobs_names,
    dumps_folder)
monsieur.wake_up()