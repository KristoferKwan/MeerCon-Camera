create_backup () {
    echo "creating backup"
    touch ./wpa_supplicant_old.conf
    cat /etc/wpa_supplicant/wpa_supplicant.conf  >> ./wpa_supplicant_old.conf
}

reset () {
    echo "reset"
    sudo rm ./wpa_supplicant_old.conf
}

rollback () {
    echo "rollback"
    sudo su -c "cat ./wpa_supplicant_old.conf > /etc/wpa_supplicant/wpa_supplicant.conf"
    sudo wpa_cli -i wlan0 reconfigure
    reset
}

create_backup
sudo su -c 'cat ./wpa_header.conf > /etc/wpa_supplicant/wpa_supplicant.conf' 

wifi=$1
password=$2

passwordLength=$(expr length "$password" )

echo "${passwordLength}"

if [ "$passwordLength" -lt 8 ] || [ "${passwordLength}" -gt 63 ]
then
    echo "ERROR: password needs to be between 8 and 63 chars in length"
    exit 1
fi

sudo su -c "wpa_passphrase ${wifi} ${password} | tee -a /etc/wpa_supplicant/wpa_supplicant.conf" 

sudo wpa_cli -i wlan0 reconfigure

duration=0
while true; do
    # testing...
    duration=$(( duration + 1 ))
    wpa_cli -i wlan0 status | grep "wpa_state=COMPLETED"
    wpa_status=$?

    if [ $wpa_status -eq 0 ]; then
        ifconfig wlan0 | grep 'inet '
        config_status=$?
        if [ $config_status -eq 0 ]; then
            break    
        fi
        sleep 1
    elif [ $duration -gt 30 ]; then
        echo "Connection not established... exiting"
        rollback
        exit 1
    else
        # not connected, sleeping for a second
        echo "$duration seconds have elapsed" 
        sleep 1
    fi
done

exit 0
