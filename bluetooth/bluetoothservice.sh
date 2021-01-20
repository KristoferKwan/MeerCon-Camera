set -xe

sudo hciconfig hci0 piscan

echo 'power on\ndiscoverable on\nmenu advertise\nmanufacturer 0xffff 0x12 0x34\nname MeerCon\nback\nadvertise on\nquit' | sudo bluetoothctl

sudo python3 serverble.py