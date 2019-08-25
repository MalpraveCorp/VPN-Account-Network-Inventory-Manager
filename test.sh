rm vpnaccount.db

echo "Creating 3 subnets with /20 default subnet."
# create pool with default subnet of 
./vpn_account.py --create-pool
./vpn_account.py --create-pool 16 sta
./vpn_account.py --create-pool 32 tst

if [ "$(./vpn_account.py --show-pools | wc -l)" -eq 3024 ];
then
  echo "Got expected number of IPs available.";
else
  echo "Did not get expected number of IP.";
  exit 1;
fi

echo "Creating 3 accounts"
./vpn_account.py --create-account meme1@here.coe
./vpn_account.py --create-account meme2@here.coe
./vpn_account.py --create-account meme3@here.coe

echo "Disabling one account"
./vpn_account.py --revoke-account meme1@here.coe

./vpn_account.py --show-accounts | grep -q "'status': 0" \
	&& echo "User was disabled." || (echo "User was not disabled" && exit 1)

./vpn_account.py --show-pools | head -n 1 | grep -q "'status': 0" \
	&& echo "IP was freed." || (echo "IP was not freed." && exit 1)

echo "Creating another account"
./vpn_account.py --create-account meme4@here.coe

if [ "$(./vpn_account.py --show-pools | grep "'status': 1"  | wc -l )" -eq 3 ];
then
  echo "IP of removed user was freed and reutilized.";
else
  echo "IP of removed user was NOT freed and reutilized.";
  exit 1;
fi
