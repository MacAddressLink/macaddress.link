#!/usr/bin/env python

import bottle

import json
import requests

import iptools

import pymongo
import settings

cloudflare_api_endpoint = 'https://www.cloudflare.com/api_json.html'

INTERNAL_IPS = iptools.IpRangeList(
    iptools.ipv4.LOOPBACK,
    iptools.ipv4.LINK_LOCAL,
    iptools.ipv4.PRIVATE_NETWORK_10,
    iptools.ipv4.PRIVATE_NETWORK_172_16,
    iptools.ipv4.PRIVATE_NETWORK_192_168,
    iptools.ipv4.MULTICAST,
    iptools.ipv6.LOOPBACK,
    iptools.ipv6.LINK_LOCAL,
    iptools.ipv6.PRIVATE_NETWORK,
    iptools.ipv6.MULTICAST,
    iptools.ipv6.IPV4_MAPPED
)

RECORD_FAMILY_TYPES = {
    'ipv4': 'A',
    'ipv6': 'AAAA',
}

db = pymongo.MongoClient().macaddresslink

def cloudflare_rec_upsert(record_name=None, record_type=None, record_address=None, record_proxy=False):

    if record_type in ('A', 'AAAA'):
        doc = db.records.find_one({
            'display_name': record_name,
            'type': record_type,
        })
    else:
        doc = db.records.find_one({
            'display_name': record_name,
            'type': record_type,
            'content': record_address
        })

    record_service_mode = '1' if record_proxy else '0'

    if doc:

        print(repr(doc['content']), repr(record_address), repr(doc['service_mode']), repr(record_service_mode))

        if doc['content'] == record_address and doc['service_mode'] == record_service_mode:
            return #No need to update
        print('Im gonna update youuuu')

        payload = {
            'a': 'rec_edit',
            'tkn': settings.cloudflare_api_key,
            'email': settings.cloudflare_api_email,
            'z': settings.cloudflare_domain,
            'name': record_name,
            'ttl': 1,
            'type': record_type,
            'content': record_address,
            'service_mode': record_service_mode,
            'id': doc['rec_id'],
        }

        r = requests.post(cloudflare_api_endpoint, data=payload)
        if r.json()['result'] == 'success':
            db.records.update({'_id': doc['_id']}, r.json()['response']['rec']['obj'])
            print(r.json())

    else:
        payload = {
            'a': 'rec_new',
            'tkn': settings.cloudflare_api_key,
            'email': settings.cloudflare_api_email,
            'z': settings.cloudflare_domain,
            'name': record_name,
            'ttl': 1,
            'type': record_type,
            'content': record_address,
        }
        
        r = requests.post(cloudflare_api_endpoint, data=payload)
        
        if r.json()['result'] == 'success':
            doc = db.records.insert(r.json()['response']['rec']['obj'])

        if(record_proxy):
            cloudflare_rec_upsert(record_name, record_type, record_address, record_proxy)


@bottle.post('/')
def update():

    request_data = json.loads(bottle.request.body.read().decode('utf-8'))

    record_set = {}

    for record_name, record_data in request_data.items():
        try:
            record_name = record_name.replace(':', '')
            int(record_name.replace(':', ''), 16) #innacurate validity test
        except:
            continue

        for record_family, record_address_list in record_data.items():
            record_type = RECORD_FAMILY_TYPES.get(record_family)

            if not record_type:
                continue

            for record_priority, record_address in enumerate(record_address_list):

                raw_record_address = record_address

                record_address = record_address.split('%')[0] #Remove IPv6 Interface

                if record_priority == 0:

                    cloudflare_rec_upsert(record_name, record_type, record_address, record_proxy=record_address not in INTERNAL_IPS)
                    record_set.setdefault(record_type, []).append(record_name + '.' + settings.cloudflare_domain)

                    cloudflare_rec_upsert(record_name + '.direct', record_type, record_address, record_proxy=False)
                    record_set.setdefault(record_type, []).append(record_name + '.direct' + '.' + settings.cloudflare_domain)

                    cloudflare_rec_upsert(record_name + '_' + record_family, record_type, record_address, record_proxy=record_address not in INTERNAL_IPS)
                    record_set.setdefault(record_type, []).append(record_name + '_' + record_family + '.' + settings.cloudflare_domain)

                    cloudflare_rec_upsert(record_name + '_' + record_family + '.direct', record_type, record_address, record_proxy=False)
                    record_set.setdefault(record_type, []).append(record_name + '_' + record_family + '.direct' + '.' + settings.cloudflare_domain)

                cloudflare_rec_upsert(record_name, 'TXT', raw_record_address)
        
    #bottle.response.status = 500
    #return {'status': 500, 'message': 'something did not go right'}

    return {'status': 200, 'message': 'ok', 'records': record_set}

app = bottle.default_app()

def application(environ, start_response):
    return app.wsgi(environ, start_response) 

if __name__ == "__main__":
    bottle.debug(True)
    bottle.run(app, host='0.0.0.0', port='8088', reloader=True)

