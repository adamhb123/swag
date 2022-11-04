from swag import app as application
from os import getenv

if __name__ == '__main__':
    debug = True if getenv(
        "SWAG_DEBUG", "false").lower().strip() == "true" else False
    application.run(debug=debug)
