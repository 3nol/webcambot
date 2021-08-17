from WebcamBot import WebcamBot
from db import update_database

if __name__ == '__main__':
    update_database([])
    WebcamBot().run('<bot_token>')
