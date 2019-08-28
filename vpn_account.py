#!/usr/bin/env python2.7
# VPN account/network inventory

import argparse
import sqlite3
import json
from signal import signal, SIGPIPE, SIG_DFL

signal(SIGPIPE, SIG_DFL)

DEFAULT_GROUP = 'prod'
DEFAULT_SUBNET = '0'
DEFAULT_NETWORK = '10.10.'

def get_chunks(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def get_octets(address):
    return str(address).split(".")

def printer(rows):
    if ARGS["json"]:
        print(json.dumps(rows, indent=4))
    else:
        for row in rows:
            print(row)

def dict_factory(cursor, row):
    dic = {}
    for idx, col in enumerate(cursor.description):
        dic[col[0]] = row[idx]
    return dic

# def get_ippools_usage(conn):
#     return {
#         '.0.1':   0.40,
#         '.0.4':   0.00
#     }

def get_arguments():
    parser = argparse.ArgumentParser(description='VPN account/network inventory.')

    # User Actions
    parser.add_argument('--create-account', help='Create a new VPN account.')
    parser.add_argument('--create-account-hardcoded', help='Create a new VPN account with pre defined parameters.', nargs='*')
    parser.add_argument('--revoke-account', help='Revoke an existing VPN account.')
    # parser.add_argument('--modify', help='Modify an existing VPN account, e.g. move to another group or change details.')
    # parser.add_argument('--password-reset', help='Reset a VPN account password.')

    # Pool Actions
    parser.add_argument('--create-pool', help='Create a new IP pool with provided subnet.', nargs='*')

    # Usage View
    parser.add_argument('--show-accounts', help='Shows accounts.', action='store_true')
    parser.add_argument('--show-accounts-full', help='Shows accounts with respective IP pool info.', action='store_true')
    parser.add_argument('--show-pools', help='Shows IP Pools.', action='store_true')
    parser.add_argument('--show-pool-usage', help='Shows IP Pool usage.', action='store_true')
    parser.add_argument('--show-subnet-usage', help='Shows subnet usage.', action='store_true')

    # View format
    parser.add_argument('--json', help='Prints data in JSON format.', action='store_true')

    parsed_args = parser.parse_args()
    # parser.print_help()
    return vars(parsed_args)

def get_pools(subnet, name):
    """ Generates list of IP pairs on a /20 available for the given subnet."""
    subnet = int(subnet)
    ret = []
    for third_octete in range(subnet, subnet+16):
        # each client needs 4 ips - must be divisible by 4
        for forth_octete in get_chunks(range(1, 253), 4):
            # Allows for 0.0/20 0.16/20 0.32/20
            network = DEFAULT_NETWORK + str(third_octete)
            ret.append([network + '.0', name, forth_octete[0], forth_octete[1], network + '.255', 0])
    return ret

def get_accounts():
    """ Get all user accounts """
    sql = 'SELECT * FROM accounts'
    CUR.execute(sql)
    return CUR.fetchall()

def get_accounts_full():
    """ Get all user accounts along with respective ip addresses assigned """
    sql = 'SELECT * FROM accounts LEFT JOIN ippools on accounts.ippool_id = ippools.id'
    CUR.execute(sql)
    return CUR.fetchall()

def get_ippools():
    """ Get all IP pools"""
    sql = 'SELECT * FROM ippools'
    CUR.execute(sql)
    return CUR.fetchall()

def get_database():
    """ Return instance of database connection"""
    connection = sqlite3.connect('vpnaccount.db')
    connection.row_factory = dict_factory
    return connection

def create_tables():
    """ Initialize database with new tables """
    sql = """CREATE TABLE IF NOT EXISTS accounts
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL,
                status INTEGER,
                ippool_id INTEGER,
                CONSTRAINT username_unique UNIQUE (username)
                )"""
    CONN.cursor().execute(sql)
    sql = """CREATE TABLE IF NOT EXISTS ippools
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                network VARCHAR(100) NOT NULL,
                subnet VARCHAR(100) NOT NULL,
                first_ip VARCHAR(100) NOT NULL,
                last_ip VARCHAR(100) NOT NULL,
                broadcast VARCHAR(100) NOT NULL,
                status INTEGER,
                CONSTRAINT network_address UNIQUE (network, first_ip, last_ip)
                )"""

    CONN.cursor().execute(sql)
    CONN.commit()

def get_available_ip():
    """ Returns the first IP pair available """
    cur = CONN.cursor()
    cur.execute('SELECT * FROM ippools WHERE status = 0')
    return cur.fetchone()

def get_ippool_id(first_ip, last_ip, network, subnet):
    """ Returns IP pool id for given input parameters"""
    cur = CONN.cursor()
    cur.execute('SELECT * FROM ippools WHERE network = ? AND first_ip = ? AND last_ip = ? and subnet LIKE ?', [network, first_ip, last_ip, subnet])
    return cur.fetchone()

def create_ippools(subnet=DEFAULT_SUBNET, name=DEFAULT_GROUP):
    """ Populates IP pools database """
    CONN.cursor().executemany('INSERT INTO ippools(network, subnet, first_ip, last_ip, broadcast, status) VALUES (?,?,?,?,?,?)', get_pools(subnet, name))
    CONN.commit()

def create_user(email):
    """ Create a new user and assign it an IP pair """
    ip_address_id = get_available_ip()['id']
    CONN.cursor().execute('UPDATE ippools SET status = 1 WHERE id = ?', (ip_address_id,))
    CONN.cursor().execute('INSERT INTO accounts(username, email, status, ippool_id) VALUES (?,?,?,?)', [email, email, 1, ip_address_id])
    CONN.commit()

def create_user_hardcoded(email, first_ip, last_ip, subnet):
    """ Create a new user from existing system, preserving ip pairs """
    network = DEFAULT_NETWORK + get_octets(first_ip)[2] + '.0'
    first_ip = get_octets(first_ip)[3]
    last_ip = get_octets(last_ip)[3]
    print(first_ip, last_ip, network, subnet)
    ip_address_id = get_ippool_id(first_ip, last_ip, network, subnet)['id']
    CONN.cursor().execute('UPDATE ippools SET status = 1 WHERE id = ?', (ip_address_id,))
    CONN.cursor().execute('INSERT INTO accounts(username, email, status, ippool_id) VALUES (?,?,?,?)', [email, email, 1, ip_address_id])
    CONN.commit()

def revoke_user(email):
    """ Disable user and free its IP pair """
    cur = CONN.cursor()
    cur.execute('SELECT * FROM accounts WHERE username LIKE ?', (email,))
    account = cur.fetchone()
    cur.execute('UPDATE accounts SET status = 0 WHERE id = ?', (int(account['id']), )) # also remove ippool_id?
    cur.execute('UPDATE ippools SET status = 0 WHERE id = ?', (int(account['ippool_id']), ))
    CONN.commit()

def handler_create_pool(arguments):
    if len(arguments) == 2:
        print('Creating subnet with provided name and range.')
        create_ippools(arguments[0], arguments[1])
    elif len(arguments) == 1:
        print('You should provide no arguments for defaults or subnet and group name e.g. --create-pool 16 prod')
    else:
        print('Creating default subnet.')
        create_ippools()

def handler_create_user_hardcoded(arguments):
    if len(arguments) != 4:
        print('You need to specify 4 params: EMAIL FISTIP LASTIP SUBNET')
        return

    email = arguments[0]
    first_ip = arguments[1]
    last_ip = arguments[2]
    subnet = arguments[3]

    create_user_hardcoded(email, first_ip, last_ip, subnet)


#
# main
#

CONN = get_database()

# if not database_initialized:
create_tables()

CUR = CONN.cursor()
ARGS = get_arguments()

if ARGS["show_accounts"]:
    printer(get_accounts())

if ARGS["show_accounts_full"]:
    printer(get_accounts_full())

if ARGS["show_pools"]:
    printer(get_ippools())

if ARGS["create_account"] is not None:
    create_user(ARGS["create_account"])

if ARGS["create_account_hardcoded"] is not None:
    handler_create_user_hardcoded(ARGS["create_account_hardcoded"])

if ARGS["revoke_account"] is not None:
    revoke_user(ARGS["revoke_account"])

if ARGS["create_pool"] is not None:
    handler_create_pool(ARGS["create_pool"])


CONN.close()
