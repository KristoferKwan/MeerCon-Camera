"""
A simple Python script to receive messages from a client over
Bluetooth using PyBluez (with Python 2).
"""

import bluetooth
import os
import threading
import subprocess
import json
import uuid


class Client:
    def __init__(self, clientname, client, thread=None):
        self.clientname = clientname
        self.client = client
        self.thread = thread

    def __gt__(self, other):
        return self.clientname > other.clientname

    def __eq__(self, other):
        return self.clientname == other.clientname

    def __str__(self):
        return f"clientname: {self.clientname}, client: {self.client}, thread: {self.thread}"  

class BluetoothSocketService:
    def __init__(self, uuid, name, port, socket=None):
        self.uuid = uuid
        self.name = name
        self.port = port
        self.socket = socket
        self.peer = dict() 
    
    def run_service(self):
        self.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self.socket.bind(("", self.port))
        self.socket.listen(5)


        bluetooth.advertise_service(self.socket, self.name, service_id=self.uuid,
                            service_classes=[self.uuid, bluetooth.SERIAL_PORT_CLASS],
                            profiles=[bluetooth.SERIAL_PORT_PROFILE],
                            # protocols=[bluetooth.OBEX_UUID]
                            )
        
        port = self.socket.getsockname()[1]
        addr = self.socket.getsockname()[0]
        print(f"Service running at {addr} on port {port}")
        
        while True:
            client, clientInfo = self.socket.accept()
            print("Accepted request:", clientInfo)
            clientname = self.get_unique_clientname(clientInfo[0])
            clientThread = threading.Thread(target=self.connection, args=(client, clientname, ))
            clientThread.start()
            self.add_client(client, clientname, clientThread)
            print(self.peer)

    def get_unique_clientname(self, rawclientname):
        i = 1
        clientname = rawclientname
        while clientname in self.peer:
            clientname = rawclientname + str(i)
            i += 1
        return clientname 

    def add_client(self, client, clientname, thread):
        newClient = Client(clientname, client, thread)
        self.peer[clientname] = newClient
        return clientname

    def attemptWifiChange(self, wifiname, password):
        connectWifi = subprocess.Popen(("sudo", "./changewifi.sh", wifiname, password), stdout=subprocess.PIPE)
        connectWifi.communicate()[0]
        rc = connectWifi.returncode
        if rc == 1:
            return "error: wifiname or password was incorrect"
        else:
            hostname = subprocess.check_output(['hostname', '-I']).decode('utf-8').strip()
            return hostname
 
    def getAvailableWifiList(self):
        wifiinfo = subprocess.Popen(("sudo", "iwlist", "wlan0", "scan"), stdout=subprocess.PIPE)
        result_raw = subprocess.check_output(("grep", "ESSID"), stdin=wifiinfo.stdout)
        wifiinfo.wait()
        result_str = result_raw.decode('utf-8')
        essid_list = result_str.split("\n")
        seen = set()
        for essid_entry in essid_list:
            essid = essid_entry.strip()[7:-1]
            if essid != "":
                seen.add(essid)
        response = json.dumps(list(seen), separators=(',', ':'))
        return response

    def connection(self, client, clientname):
        size = 1024

        try:
            client.send("ACK. please provide a command")
            while 1:
                command = client.recv(size).decode("utf-8").strip()
                print(command)
                commandlist = command.split(" ")
                if command == "getAvailableWifiList":
                    response = self.getAvailableWifiList()
                    client.send(response)
                elif command and commandlist[0] == "changeWifi":
                    if len(commandlist) == 3: 
                        wifi = commandlist[1]
                        password = commandlist[2]
                        response = self.attemptWifiChange(wifi, password)
                        client.send(response)
                    else:
                        client.send("Incorrect number of arguments. \nUSAGE: changeWifi <WIFINAME> <PASSWORD>") 
                elif command == "quit":
                    self.disconnect_peer(clientname)
                    client.send("quit")
                    return
                else:
                    print("Invalid command")
                    client.send("Invalid command")
        except Exception as e:	
            print(e)
            print("Closing client connection")
            self.disconnect_peer(clientname)
        
    def disconnect_peer(self, clientip):
        client = self.peer[clientip]
        client.client.close()
        del self.peer[clientip]


    def close_service(self):
        self.socket.close()
        for clientip in self.peer:
            self.disconnect_peer(clientip) 


def createSocketConn(port):
    generalService = BluetoothSocketService(uuid="94f39d29-7d6d-437d-973b-fba39e49d4ee", port=port, name="connection")
    generalService.run_service()


for i in range(2,7):
    sock = threading.Thread(target=createSocketConn, args=(i, ))
    sock.start()