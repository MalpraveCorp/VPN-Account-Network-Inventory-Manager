
# VPN Account/Network Manager


VPN Account and network inventory manager

##  Usage Examples

Help flag
```
./vpn_account.py -h
usage: vpn_account.py [-h] [--create-account CREATE_ACCOUNT]
                      [--create-account-hardcoded [CREATE_ACCOUNT_HARDCODED [CREATE_ACCOUNT_HARDCODED ...]]]
                      [--revoke-account REVOKE_ACCOUNT]
                      [--create-pool [CREATE_POOL [CREATE_POOL ...]]]
                      [--show-accounts] [--show-accounts-full] [--show-pools]
                      [--show-pool-usage] [--show-subnet-usage] [--json]

Manage VPN accounts.

optional arguments:
  -h, --help            show this help message and exit
  --create-account CREATE_ACCOUNT
                        Create a new VPN account
  --create-account-hardcoded [CREATE_ACCOUNT_HARDCODED [CREATE_ACCOUNT_HARDCODED ...]]
                        Create a new VPN account with pre defined parameters.
  --revoke-account REVOKE_ACCOUNT
                        Revoke an existing VPN account.
  --create-pool [CREATE_POOL [CREATE_POOL ...]]
                        Create a new IP pool with provided subnet.
  --show-accounts       Shows accounts.
  --show-accounts-full  Shows accounts with respective IP pool info.
  --show-pools          Shows IP Pools.
  --show-pool-usage     Shows IP Pool usage.
  --show-subnet-usage   Shows subnet usage.
  --json                Prints data in JSON format.
  ```

### Subnets
Create default subnet 10.10.0.0/20 named prod.
```
./vpn_account.py --create-pool
Creating default subnet
```


Create subnet 10.10.16.0/20 named acc.
```
./vpn_account.py --create-pool 16 acc
Creating default subnet
```

View IP pairs
```
./vpn_account.py --show-pools
{'status': 1, 'subnet': u'prod', 'network': u'10.10.0.0', 'last_ip': u'1', 'broadcast': u'10.10.0.255', 'first_ip': u'0', 'id': 1}
{'status': 0, 'subnet': u'prod', 'network': u'10.10.0.0', 'last_ip': u'5', 'broadcast': u'10.10.0.255', 'first_ip': u'4', 'id': 2}
{'status': 0, 'subnet': u'prod', 'network': u'10.10.0.0', 'last_ip': u'9', 'broadcast': u'10.10.0.255', 'first_ip': u'8', 'id': 3}
(...)
```

### Accounts
Create Account
```
./vpn_account.py --create-account myname@here.com
```

Import accounts (keep the same ip pairs)

```
./vpn_account.py --create-account-hardcoded myname@host.eu 10.10.1.6 10.10.1.5 prod;
```

or run this on existing VPN server

```
cd /etc/openvpn/ccd/;  for file in *; do echo -n "./vpn_account.py --create-account-hardcoded $file "; grep ifconfig-push $file | sed 's/:ifconfig-push//g' | tr -d '\n'; echo ' prod;' ; done
```

And run the output

Show Accounts
```
./vpn_account.py --show-accounts
{'username': u'myname@here.com', 'status': 1, 'id': 1, 'ippool_id': 1, 'email': u'myname@here.com'}
```

Revoke Account (Free IP)
```
./vpn_account.py --revoke-account myname@here.com
```

### TODO
Error validation
Usage stats

### Maintainer
Pedro Gomes

### License
MIT