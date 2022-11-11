from ast import Return
from datetime import datetime
from pprint import pprint
from re import compile, escape, I
from typing import Any, Dict, List, Mapping, Union
from pymongo import InsertOne, ReplaceOne, MongoClient, UpdateOne, ReturnDocument
from pymongo.command_cursor import CommandCursor
from os import environ
from uuid import uuid4
from functools import wraps
from bson.objectid import ObjectId


_sub_regex = compile('(A|(An)|(The)) ')
try:
    _database = MongoClient(
        f'mongodb://{environ["SWAG_MONGODB_USER"]}:{environ["SWAG_MONGODB_PASSWORD"]}@{environ.get("SWAG_MONGODB_HOST", "localhost")}/{environ["SWAG_MONGODB_DATABASE"]}',
        tls=environ.get('SWAG_MONGODB_SSL', 'False').lower() in (
            'true', '1', 't')
    )[environ['SWAG_MONGODB_DATABASE']]
except:
    _database = MongoClient()[environ['SWAG_MONGODB_DATABASE']]
#_api_keys = _database.api_keys
_deletedItems = _database.deletedItems
_deletedPurchases = _database.deletedPurchases
_managers = _database.managers
_items = _database.items
_purchases = _database.purchases


"""def api_key_exists(key):
    return _api_keys.count_documents({'key': key})"""


def _create_filters(arguments, **kwargs):
    filters = {}
    max_players = arguments.get('max_players')
    if max_players:
        try:
            filters['max_players'] = int(max_players)
        except:
            filters['max_players'] = -1
    min_players = arguments.get('min_players')
    if min_players:
        try:
            filters['min_players'] = int(min_players)
        except:
            filters['min_players'] = -1
    name = arguments.get('name')
    if name:
        try:
            filters['name'] = compile(name, I)
        except:
            filters['name'] = compile(escape(name), I)
    seller = arguments.get('seller')
    if seller:
        filters['seller'] = seller
    players = arguments.get('players')
    if players:
        try:
            players = int(players)
            filters['$and'] = [
                {'min_players': {'$lte': players}},
                {'max_players': {'$gte': players}}
            ]
        except:
            filters['$and'] = [
                {'min_players': {'$lte': -1}},
                {'max_players': {'$gte': -1}}
            ]
    seller = arguments.get('seller')
    if seller:
        filters['seller'] = seller

    return dict(filters, **kwargs)


def _create_sort(arguments, **kwargs):
    try:
        return dict(
            {arguments['sort']: -1 if 'descending' in arguments else 1},
            **kwargs
        )
    except:
        return kwargs


def delete_item(item_id: Union[str,ObjectId], requester):
    if type(item_id) == str:
        item_id = ObjectId(item_id)
    _purchase = _items.find_one({'_id': item_id})
    print(_purchase)
    if not _purchase or not (is_manager(requester) or requester == _purchase['seller']):
        return False
    _deletedItems.insert_one(_purchase)
    _items.delete_one({'_id': item_id})
    try:
        id = list(_items.find().sort([('_id', -1)]).limit(10))[-1]['_id']
        _items.update_many({'_id': {'$gte': id}}, {'$set': {'new': True}})
    except:
        pass
    return True


def item_exists(name):
    return _items.count_documents({'name': compile(f'^{escape(name)}$', I)})


'''def generate_api_key():
    uuid = str(uuid4())
    _api_keys.insert_one({'key': uuid})
    return uuid


def get_api_keys():
    return _api_keys.find()'''


def get_count(arguments):
    return _items.count_documents(_create_filters(arguments))


def get_item(name):
    return _items.find_one({'name': name})


def get_item_by_id(id: Union[str, ObjectId]):
    if type(id) == str:
        if not ObjectId.is_valid(id):
            return None
    item = _items.find_one({'_id': ObjectId(id) if type(id) == str else id})
    return item


def get_item_names(expansion=None):
    return (item['name'] for item in _items.find(
        {'expansion': expansion} if expansion else {},
        {'_id': False, 'name': True}
    ).sort([('sort_name', 1)]))


def get_items(arguments):
    return _items.aggregate([
        {'$match': _create_filters(arguments)},
        {'$sort': _create_sort(arguments, sort_name=1)},
    ])


def get_newest_items(arguments):
    return _items.aggregate([
        {'$match': _create_filters(arguments, new=True)},
        {'$sort': _create_sort(arguments, _id=-1)},
    ])


def get_players():
    try:
        return next(_items.aggregate([
            {'$group': {'_id': False, 'max': {'$max': '$max_players'},
                        'min': {'$min': '$min_players'}}}
        ]))
    except:
        return None


def get_random_items(arguments, sample_size):
    return _items.aggregate([
        {'$match': _create_filters(arguments)},
        {'$sample': {'size': sample_size}}, {'$project': {'_id': False}}
    ])


def get_items_from_seller(arguments, seller):
    print(_items.aggregate([
        {'$match': _create_filters(arguments, seller=seller)},
        {'$sort': _create_sort(arguments, sort_name=1)},
    ]))
    return _items.aggregate([
        {'$match': _create_filters(arguments, seller=seller)},
        {'$sort': _create_sort(arguments, sort_name=1)},
    ])


def is_item_seller(seller, item):
    return _items.find_one({'_id': item['_id'], 'seller': seller})


def get_sellers(arguments=None):
    aggregation = [{'$group': {'_id': '$seller'}}, {'$sort': {'_id': 1}}]
    if arguments:
        aggregation = {'$match': _create_filters(arguments)} + aggregation
    return (item['_id'] for item in _items.aggregate(aggregation))


def replace_item(old_item, item, seller):
    #requests = [ReplaceOne({"name": update_name},  item)]
    print(item)
    if is_manager(seller) or is_item_seller(seller):
        return _items.find_one_and_replace({'_id': old_item['_id']}, item, return_document=ReturnDocument.AFTER)


def insert_item(item, seller) -> ObjectId:
    print(item)
    del item['image']
    item['new'] = True
    item['date'] = datetime.now()
    item['active'] = True if item['active'] and item['quantity'] > 0 else False
    item['sort_name'] = _sub_regex.sub('', item['name'])
    item['seller'] = seller
    print(item)
    return _items.insert_one(item).inserted_id
    '''    swag = list(_items.find().sort([('_id', -1)]).limit(10))
       if len(swag) == 10:
        requests.append(UpdateOne({'_id': swag[-1]['_id']}, {
            '$unset': {'new': 1}
        }))'''


def user_owns_item(username, item):
    return _purchases.find_one({
        'seller': username,
        'item_id': ObjectId(item['_id'])
    }) is not None


def get_all_purchases():
    return _purchases.find()


def get_purchases_with_items(arguments, username: str = None):
    return _items.aggregate([
        {'$lookup':
            {'from': 'purchases', 'localField': '_id',
                'foreignField': 'item_id', 'as': 'purchases'}
         },
        {'$unwind': '$purchases'},
        #{'$set': {'purchase':'$purchases.fulfilled'}},
        {'$set': {'purchase': '$purchases'}},
        {'$project': {'purchases': False}},
        {'$match': {'purchase.buyer': username} if username else {}},
        # Sort by fulfilled, date fulfilled, date ordered, then id, in that order
        {'$sort': {
            'purchase.fulfilled': arguments.get('sort-fulfilled', default=1, type=int),
            'purchase.dateFulfilled': arguments.get('sort-date-fulfilled', default=-1, type=int),
            'purchase.date': arguments.get('sort-date', default=-1, type=int), '_id': 1
        }},
    ])


class DuplicateData:
    def __init__(self, data, count):
        self.data = data
        self.count = count


def collapse_duplicates(collection: Union[CommandCursor, List], onField: str) -> List[DuplicateData]:
    if type(collection) == CommandCursor:
        collection = list(collection)
    collapsed = []
    for unique_member in [*set(map(lambda z: z[onField], collection))]:
        duplicates = list(
            filter(lambda i: i[onField] == unique_member, collection))
        collapsed.append(DuplicateData(duplicates[0], len(duplicates)))
        collection = list(filter(lambda i: i not in duplicates, collection))
    return collapsed


def insert_purchase(item, quantity, buyer, fulfilled=False, paymentMethod=None):
    # Insert purchase into purchases db
    purchase = {'buyer': buyer,
                'item_id': item['_id'],
                'quantity': quantity,
                'date': datetime.now(),
                'fulfilled': fulfilled,
                'paymentMethod': paymentMethod}
    _purchases.insert_one(purchase)

    # Update item quantity in items db, set active to false if none left
    item = _items.find_one_and_update({'_id': item['_id']},
                                      [{"$set":
                                        {"quantity": {"$add": ["$quantity", -quantity]},
                                         "active": {"$and": [{"$gt": ["$quantity", 0]}, {"$eq": ["$active", True]}]}}
                                        }]
                                      )
    print(item)


def fulfillment_guard(*args):
    func = args[0]
    def wrapper(*args, **kwargs):
        purchase = _purchases.find_one({'_id': args[0]})
        print("purchase fulfilled: " + str(purchase['fulfilled']))
        if not purchase['fulfilled']:
            return func(*args, **kwargs)
    return wrapper


@fulfillment_guard
def fulfill_purchase(purchase_id: ObjectId, payment_method: str):
    purchase = _purchases.find_one_and_update({'_id': purchase_id}, {'$set': {
        'fulfilled': True,
        'paymentMethod': payment_method,
        'dateFulfilled': datetime.now()
    }}, return_document=ReturnDocument.AFTER)
    return purchase


@fulfillment_guard
def delete_purchase(purchase_id, requester):
    _purchase = _purchases.find_one({'_id': purchase_id})
    if not _purchase or not (is_manager(requester) or requester == _purchase['seller']):
        return False
    print(_purchase)
    if _purchase:
        _deletedPurchases.insert_one(_purchase)
        _purchases.delete_one({'_id': purchase_id})
        # Restore quantity to item
        _items.update_one({'_id': _purchase['item_id']}, [
                          {'$set': {"quantity": {"$add": ["$quantity", _purchase['quantity']]}}}])
        try:
            id = list(_items.find().sort([('_id', -1)]).limit(10))[-1]['_id']
            _items.update_many({'_id': {'$gte': id}}, {'$set': {'new': True}})
        except:
            pass


def is_manager(username):
    return _managers.count_documents({'username': username})
