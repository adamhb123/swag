# [Swag](https://Swag.csh.rit.edu)

Swag is a database you can use to see the physical resources available to you in Computer Science House. You can see what we have available, who is/has been using it, and link to any relevant documentation or projects.

## Setup
**Requires Python & MongoDB**

### Python Dependencies
Use `pip install -r requirements.txt` to install the required python dependencies. Using virtualenv is recommeded when installing packages for python.

### Environment Variables
`Swag` requires access to OIDC and s3 to operate properly. This is done by obtaining a client id and secret for each service.

Set these variables before attempting to start `Swag`
* `SWAG_IMAGE_URL` - URL where game thumbnails are hosted
* `SWAG_MONGODB_DATABASE` - Set to whatever `Swag` database will be called
* `SWAG_SECRET_KEY` - Set to anything, but keep it a secret
* `SWAG_SERVER_NAME` - Set to localhost:5000 for use with CSH auth
* `SWAG_URL_SCHEME` - Set to `http` for CSH auth

For OIDC information contact a maintainer of `Swag`
* `SWAG_OIDC_CLIENT_ID`
* `SWAG_OIDC_CLIENT_SECRET`
* `SWAG_OIDC_ISSUER`
* `SWAG_OIDC_REDIRECT_URI`

For s3 credentials contact a maintainer of `Swag`
* `SWAG_S3_BUCKET`
* `SWAG_S3_KEY`
* `SWAG_S3_SECRET`
* `SWAG_S3_ENDPOINT`

## Running `Swag`
Start `Swag` by using `python wsgi.py` in the projects root directory

The project should be running at localhost:5000

