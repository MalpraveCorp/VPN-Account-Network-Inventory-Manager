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
    if args["json"]:
        print(json.dumps(rows, indent=4))
    else:
        for row in rows:
            print(row)

def dict_factory(cur, row):
    d = {}
    for idx, col in enumerate(cur.description):
        d[col[0]] = row[idx]
    return d

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

# generate /20 IP Pool in provided subnet
def get_pools(subnet, name):
    subnet = int(subnet)
    ret = []
    for thirdOctete in range(subnet, subnet+16):
        # each client needs 4 ips - must be divisible by 4
        for forthOctete in get_chunks(range(1, 253), 4):
            # Allows for 0.0/20 0.16/20 0.32/20
            network = DEFAULT_NETWORK + str(thirdOctete)
            ret.append([network + '.0', name, forthOctete[0], forthOctete[1], network + '.255', 0])
    return ret

def get_accounts():
    sql = 'SELECT * FROM accounts'
    cur.execute(sql)
    return cur.fetchall()

def get_accounts_full():
    sql = 'SELECT * FROM accounts LEFT JOIN ippools on accounts.ippool_id = ippools.id'
    cur.execute(sql)
    return cur.fetchall()

def get_ippools():
    sql = 'SELECT * FROM ippools'
    cur.execute(sql)
    return cur.fetchall()

def get_database():
    conn = sqlite3.connect('vpnaccount.db')
    conn.row_factory = dict_factory
    return conn

def database_initialized():
    return True

def create_tables(conn):
    sql = """CREATE TABLE IF NOT EXISTS accounts
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL,
                status INTEGER,
                ippool_id INTEGER,
                CONSTRAINT username_unique UNIQUE (username)
                )"""
    conn.cursor().execute(sql)
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

    conn.cursor().execute(sql)
    conn.commit()

def get_available_ip(conn):
    c = conn.cursor()
    c.execute('SELECT * FROM ippools WHERE status = 0')
    return c.fetchone()

def get_ippool_id(conn, first_ip, last_ip, network, subnet):
    c = conn.cursor()
    c.execute('SELECT * FROM ippools WHERE network = ? AND first_ip = ? AND last_ip = ? and subnet LIKE ?', [network, first_ip, last_ip, subnet])
    return c.fetchone()

def create_ippools(conn, subnet=DEFAULT_SUBNET, name=DEFAULT_GROUP):
    conn.cursor().executemany('INSERT INTO ippools(network, subnet, first_ip, last_ip, broadcast, status) VALUES (?,?,?,?,?,?)', get_pools(subnet, name))
    conn.commit()

def create_user(email):
    ip_address_id = get_available_ip(conn)['id']
    conn.cursor().execute('UPDATE ippools SET status = 1 WHERE id = ?', (ip_address_id,))
    conn.cursor().execute('INSERT INTO accounts(username, email, status, ippool_id) VALUES (?,?,?,?)', [email, email, 1, ip_address_id])
    conn.commit()

def create_user_hardcoded(email, first_ip, last_ip, subnet):
    network = DEFAULT_NETWORK + get_octets(first_ip)[2] + '.0'
    first_ip = get_octets(first_ip)[3]
    last_ip = get_octets(last_ip)[3]
    print(first_ip, last_ip, network, subnet)
    ip_address_id = get_ippool_id(conn, first_ip, last_ip, network, subnet)['id']
    conn.cursor().execute('UPDATE ippools SET status = 1 WHERE id = ?', (ip_address_id,))
    conn.cursor().execute('INSERT INTO accounts(username, email, status, ippool_id) VALUES (?,?,?,?)', [email, email, 1, ip_address_id])
    conn.commit()

def revoke_user(email):
    c = conn.cursor()
    c.execute('SELECT * FROM accounts WHERE username LIKE ?', (email,))
    account = c.fetchone()
    c.execute('UPDATE accounts SET status = 0 WHERE id = ?', (int(account['id']), )) # also remove ippool_id?
    c.execute('UPDATE ippools SET status = 0 WHERE id = ?', (int(account['ippool_id']), ))
    conn.commit()

def handler_create_pool(args):
    if len(args) == 2:
        print('Creating subnet with provided name and range.')
        create_ippools(conn, args[0], args[1])
    elif len(args) == 1:
        print('You should provide no arguments for defaults or subnet and group name e.g. --create-pool 16 prod')
    else:
        print('Creating default subnet.')
        create_ippools(conn)

def handler_create_user_hardcoded():
    if len(args) == 4:
        create_user_hardcoded(conn, args[0], args[2], args[1], args[3])
    else:
        print(get_last_octet(args[2]))
        print('You need to specify 4 params: EMAIL FISTIP LASTIP SUBNET')


#
# main
#

conn = get_database()

# if not database_initialized:
create_tables(conn)

cur = conn.cursor()
args = get_arguments()

if args["show_accounts"]:
    printer(get_accounts())

if args["show_accounts_full"]:
    printer(get_accounts_full())

if args["show_pools"]:
    printer(get_ippools())

if args["create_account"] is not None:
    create_user(args["create_account"])

if args["create_account_hardcoded"] is not None:
    handler_create_user_hardcoded(args["create_account_hardcoded"])

if args["revoke_account"] is not None:
    revoke_user(args["revoke_account"])

if args["create_pool"] is not None:
    handler_create_pool(args["create_pool"])


conn.close()
