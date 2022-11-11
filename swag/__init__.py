from flask import *
from os import environ
from flaskext.markdown import Markdown
from flask_pyoidc.provider_configuration import *
from flask_pyoidc.flask_pyoidc import OIDCAuthentication
from boto3 import client
from datetime import datetime
from swag.auth import require_manager, require_read_key
from swag.database import *
from swag.item import Item, EditItem

app = Flask(__name__)
app.config.update(
    PREFERRED_URL_SCHEME=environ.get('SWAG_URL_SCHEME', 'https'),
    SECRET_KEY=environ['SWAG_SECRET_KEY'],
    SERVER_NAME=environ['SWAG_SERVER_NAME'],
    WTF_CSRF_ENABLED=False
)

# OIDC flask config setup
app.config.update(
    # OIDC_REDIRECT_URI = f"{app.config['PREFERRED_URL_SCHEME']}://{app.config['SERVER_NAME']}/",
    OIDC_ISSUER=environ['SWAG_OIDC_ISSUER'],
    OIDC_CLIENT_ID=environ['SWAG_OIDC_CLIENT_ID'],
    OIDC_CLIENT_SECRET=environ['SWAG_OIDC_CLIENT_SECRET'],

)
app.jinja_env.add_extension('jinja2.ext.loopcontrols')
app.jinja_env.lstrip_blocks = True
app.jinja_env.trim_blocks = True
app.url_map.strict_slashes = False


Markdown(app)
_config = ProviderConfiguration(
    app.config["OIDC_ISSUER"],
    client_metadata=ClientMetadata(
        app.config['OIDC_CLIENT_ID'], app.config['OIDC_CLIENT_SECRET']
    )
)
_auth = OIDCAuthentication({'default': _config}, app)

_s3 = client(
    's3', aws_access_key_id=environ['SWAG_S3_KEY'],
    aws_secret_access_key=environ['SWAG_S3_SECRET'],
    endpoint_url=environ['SWAG_S3_ENDPOINT']
)


@app.context_processor
def utility_functions():
    def print_in_console(message):
        print(str(message))

    def format_date(date: datetime):
        return date.strftime('%m/%d/%Y')

    def format_price(price: float):
        return "{:.2f}".format(price)

    return dict(mdebug=print_in_console, format_date=format_date, format_price=format_price)


"""@app.route('/api')
@require_read_key
def api():
    return jsonify(list(get_items(request.args)))


@app.route('/api/count')
@require_read_key
def api_count():
    return jsonify(get_count(request.args))


@app.route('/api/key', methods=['GET', 'POST'])
@requiremanager
def api_key():
    return jsonify(generate_api_key())


@app.route('/api/keys')
@requiremanager
def api_keys():
    return jsonify(list(get_api_keys()))


@app.route('/api/newest')
@require_read_key
def api_newest():
    return jsonify(list(get_newest_items(request.args)))


@app.route('/api/sellers')
@require_read_key
def api_sellers():
    return jsonify(list(get_sellers(request.args)))


@app.route('/api/random')
@app.route('/api/random/<int:sample_size>')
@require_read_key
def api_random(sample_size=1):
    sample = list(get_random_items(request.args, sample_size))
    return jsonify(sample[0] if len(sample) == 1 else sample)


@app.route('/api/submitters')
@require_read_key
def api_submitters():
    return jsonify(list(get_submitters(request.args)))
"""


@app.route('/delete/<item_id>', methods=['POST'])
@_auth.oidc_auth('default')
@require_manager
def delete(item_id):
    if not delete_item(item_id, session['userinfo']['preferred_username']):
        abort(404)
    return redirect('/')


def _get_template_variables():
    return {
        'manager': is_manager(session['userinfo']['preferred_username']),
        'image_url': environ['SWAG_IMAGE_URL'],
        'sellers': get_sellers(), 'players': get_players(),
    }


@app.route('/')
@_auth.oidc_auth('default')
def index():
    return render_template(
        'index.html', items=get_items(request.args),
        **_get_template_variables()
    )


@app.route('/item/<item_id>')
@_auth.oidc_auth('default')
def item(item_id):
    i = get_item_by_id(item_id)
    if not i:
        abort(404)
    return render_template(
        'item.html', expansions=list(get_item_names(i['name'])), item=i,
        **_get_template_variables()
    )

# @app.route('/submissions')
# @_auth.oidc_auth('default')
# def submissions():
#     return render_template(
#         'submissions.html',
#         items=get_submissions(
#             request.args,
#             session['userinfo']['preferred_username']
#         ), **_get_template_variables()
#     )


@app.route('/my-purchases')
@_auth.oidc_auth('default')
def purchases():
    return render_template(
        'my-purchases.html',
        title="Your Purchase History",
        items=list(get_purchases_with_items(
            request.args, session['userinfo']['preferred_username'])),
        **_get_template_variables()
    )


@app.route('/manage-orders')
@_auth.oidc_auth('default')
@require_manager
def manage_purchases():
    print(list(get_purchases_with_items(request.args)))
    return render_template(
        'manage.html',
        title="Order Management",
        items=list(get_purchases_with_items(request.args)),
        **_get_template_variables()
    )


@app.route('/order/<action>/<purchase_id>', methods=['POST'])
@_auth.oidc_auth('default')
@require_manager
def resolve_order(action, purchase_id):
    if is_manager(session['userinfo']['preferred_username']):
        if type(purchase_id) != ObjectId:
            purchase_id = ObjectId(purchase_id)
        if action == "fulfill":
            if fulfill_purchase(purchase_id, request.args.get('payment-method', 'Not Specified')):
                flash(
                    f'Order \'{purchase_id}\' successfully finalized', 'success')
            else:
                flash(f'Order \'{purchase_id}\' already finalized', 'warning')

        elif action == "cancel":
            delete_purchase(
                purchase_id, session['userinfo']['preferred_username'])
        else:
            flash('Invalid order action', 'danger')
    else:
        flash('Access denied, halt your tomfoolery at once!')

    return redirect('/manage-orders')


@app.route('/submit', methods=['GET', 'POST'])
@_auth.oidc_auth('default')
@require_manager
def submit():
    if request.method == 'GET':
        return render_template(
            'submit.html',
            form=Item(session['userinfo']['preferred_username']),
            item_names=get_item_names(), **_get_template_variables()
        )
    item = Item()
    if not item.validate():
        return render_template(
            'submit.html',
            error=next(iter(item.errors.values()))[0], form=item,
            item_names=get_item_names(), **_get_template_variables()
        )
    item = item.data
    raw_info = item['info']
    item = {k: v.strip() if type(v) == str else v for k, v in item.items()}
    item['info'] = raw_info
    item_image = item['image']
    item_id = insert_item(item, session['userinfo']['preferred_username'])
    _s3.upload_fileobj(
        item_image, environ['SWAG_S3_BUCKET'], str(item_id) + '.jpg',
        ExtraArgs={
            'ACL': 'public-read', 'ContentType': item_image.content_type
        }
    )
    flash('Swag successfully submitted, thanks!', 'success')
    return redirect('/')


@app.route('/edit/<item_id>', methods=['GET', 'POST'])
@_auth.oidc_auth('default')
def edit(item_id):
    old_item = get_item_by_id(item_id)
    if request.method == 'GET':
        return render_template(
            'submit.html',
            form=Item(session['userinfo']['preferred_username']),
            item_names=get_item_names(), **_get_template_variables(),
            item=old_item
        )
    item = EditItem()
    if not item.validate():
        return render_template(
            'submit.html',
            form=item,
            item_names=get_item_names(),
            **_get_template_variables(),
            item=get_item_by_id(item_id)
        )
    item = item.data
    item = {k: v.strip() if type(v) == str and k !=
            'info' else v for k, v in item.items()}
    if item['image']:
        _s3.upload_fileobj(
            item['image'], environ['SWAG_S3_BUCKET'],
            f'{old_item["_id"]}.jpg',
            ExtraArgs={
                'ACL': 'public-read', 'ContentType': item['image'].content_type
            }
        )
    del item['image']
    item['date'] = old_item['date']
    replace_item(old_item, item, session['userinfo']['preferred_username'])
    flash('Swag successfully submitted', 'successs')
    return redirect('/')


@app.route('/buy/<item_id>', methods=['GET', 'POST'])
@_auth.oidc_auth('default')
def buy(item_id):
    # Add quantities
    i = get_item_by_id(item_id)
    if request.method != 'POST':
        abort(400)
        # return render_template(
        #     'purchase.html',
        #     form=Item(session['userinfo']['preferred_username']),
        #     **_get_template_variables(),
        # )
    quantity = request.form.get("quantity", type=int)
    if not i['active']:
        flash('Order failed! Item not available for purchase...', 'danger')
    elif not (quantity and 0 < quantity <= i['quantity']):
        flash("Order failed! Invalid quantity provided...", 'danger')
    else:
        insert_purchase(i, quantity, session['userinfo']['preferred_username'])
        flash('Order successfully placed! Financial will be in touch for payment soon...', 'success')

    return redirect('/')
