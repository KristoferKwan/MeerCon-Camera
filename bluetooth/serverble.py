#!/usr/bin/env python3

import logging

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
from signal import signal, SIGINT
from sys import exit

from ble import (
    Advertisement,
    Characteristic,
    Service,
    Application,
    find_adapter,
    Descriptor,
    Agent,
)

import struct
import requests
import subprocess
import array
import json
from enum import Enum

import sys

MainLoop = None
try:
    from gi.repository import GLib

    MainLoop = GLib.MainLoop
except ImportError:
    import gobject as GObject

    MainLoop = GObject.MainLoop

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logHandler = logging.StreamHandler()
filelogHandler = logging.FileHandler("logs.log")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logHandler.setFormatter(formatter)
filelogHandler.setFormatter(formatter)
logger.addHandler(filelogHandler)
logger.addHandler(logHandler)


mainloop = None

BLUEZ_SERVICE_NAME = "org.bluez"
GATT_MANAGER_IFACE = "org.bluez.GattManager1"
LE_ADVERTISEMENT_IFACE = "org.bluez.LEAdvertisement1"
LE_ADVERTISING_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"


class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.freedesktop.DBus.Error.InvalidArgs"


class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.NotSupported"


class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.NotPermitted"


class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.InvalidValueLength"


class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.Failed"


def register_app_cb():
    logger.info("GATT application registered")


def register_app_error_cb(error):
    logger.critical("Failed to register application: " + str(error))
    mainloop.quit()


class MeerConS1Service(Service):
    """
    Dummy test service that provides characteristics and descriptors that
    exercise various API functionality.
    """

    MEERCON_SVC_UUID = 'd2884631-92ad-4aa1-b362-7e1329f7d990'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.MEERCON_SVC_UUID, True)
        self.add_characteristic(WifiControlCharacteristic(bus, 0, self))
        self.add_characteristic(WifiListCharacteristic(bus, 1, self))


class WifiControlCharacteristic(Characteristic):
    uuid = "4116f8d2-9f66-4f58-a53d-fc7440e7c14e"
    description = b"Get/set wifiname and password"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.uuid, ["encrypt-read", "encrypt-write"], service,
        )

        self.value = None
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self))

    def attemptWifiChange(self, wifiname, password):
        connectWifi = subprocess.Popen(("sudo", "./changewifi.sh", wifiname, password), stdout=subprocess.PIPE)
        connectWifi.communicate()[0]
        rc = connectWifi.returncode
        res = dict()
        try:
            hostname = subprocess.check_output(['hostname', '-I']).decode('utf-8').strip()
            wifiname = subprocess.check_output(['iwgetid', '-r']).decode('utf-8').strip()
        except Exception:
            hostname = "" 
            wifiname = ""
        if rc == 1:
            res["status"] = 400
            res["hostname"] = None if hostname == "" else hostname
            res["wifiname"] = None if wifiname == "" else wifiname
            res["message"] = "error: wifiname or password was incorrect"
            return bytearray(json.dumps(res, separators=(',',':')), encoding="utf8")
        else:
            res["status"] = 200
            res["hostname"] = None if hostname == "" else hostname
            res["wifiname"] = None if wifiname == "" else wifiname
            res["message"] = "successfully changed wifi"
            return bytearray(json.dumps(res, separators=(',',':')), encoding="utf8")

    def ReadValue(self, options):
        logger.info("wifi and ip read: " + repr(self.value))
        res = None
        try:
            res = dict()
            if not self.value:
                res["status"] = 200
                res["message"] = None
            else:
                oldValue = json.loads(bytes(self.value).decode("utf-8"))
                res["status"] = oldValue["status"]
                res["message"] = oldValue["message"]
            try:
                hostname = subprocess.check_output(['hostname', '-I']).decode('utf-8').strip()
                wifiname = subprocess.check_output(['iwgetid', '-r']).decode('utf-8').strip()
            except:
                hostname = ""
                wifiname = ""
            res["hostname"] = None if hostname == "" else hostname
            res["wifiname"] = None if wifiname == "" else wifiname
            self.value = bytearray(json.dumps(res, separators=(',',':')), encoding="utf8")
        except Exception as e:
            logger.error(f"Error getting status {e}")
        return self.value

    def WriteValue(self, value, options):
        logger.info("wifi and password write: " + repr(value))
        cmd = bytes(value).decode("utf-8")
        cmdlist = cmd.split(" ")
        # write it to machine
        logger.info(f"writing {cmd} to machine")
        try:
            if len(cmdlist) == 2: 
                wifi = cmdlist[0]
                password = cmdlist[1]
                processing = dict()
                processing["status"] = "PENDING"
                processing["hostname"] = None
                processing["wifiname"] = None
                processing["message"] = None
                self.value = bytearray(json.dumps(processing, separators=(',',':')), encoding="utf8")
                res = self.attemptWifiChange(wifi, password)
            else:
                raise Exception("Incorrect number of arguments. \nUSAGE: changeWifi <WIFINAME> <PASSWORD>")
            logger.info(res)
            self.value = res
        except Exception as e:
            logger.error(f"Error updating machine state: {e}")
            raise


class WifiListCharacteristic(Characteristic):
    uuid = "322e774f-c909-49c4-bd7b-48a4003a967f"
    description = b"Get available wifi networks"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.uuid, ["secure-read"], service,
        )

        self.value = []
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self))

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

    def ReadValue(self, options):
        logger.info("getting available wifi networks read: " + repr(self.value))
        res = None
        try:
            res = self.getAvailableWifiList()
            self.value = bytearray(res, encoding='utf-8')
        except Exception as e:
            logger.error(f"Error getting status {e}")

        return self.value


class CharacteristicUserDescriptionDescriptor(Descriptor):
    """
    Writable CUD descriptor.
    """

    CUD_UUID = "2901"

    def __init__(
        self, bus, index, characteristic,
    ):

        self.value = array.array("B", characteristic.description)
        self.value = self.value.tolist()
        Descriptor.__init__(self, bus, index, self.CUD_UUID, ["read"], characteristic)

    def ReadValue(self, options):
        return self.value

    def WriteValue(self, value, options):
        if not self.writable:
            raise NotPermittedException()
        self.value = value


class MeerConAdvertisement(Advertisement):
    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, "peripheral")
        self.add_manufacturer_data(
            0xFFFF, [0x70, 0x74],
        )
        self.add_service_uuid(MeerConS1Service.MEERCON_SVC_UUID)

        self.add_local_name("MeerConCam")   
        self.include_tx_power = True


def register_ad_cb():
    logger.info("Advertisement registered")


def register_ad_error_cb(error):
    logger.critical("Failed to register advertisement: " + str(error))
    mainloop.quit()


AGENT_PATH = "/com/meercon/agent"


def main():
    def handler(signal_received, frame):
        logger.info(f"unregistering advertisement")
        ad_manager.UnregisterAdvertisement(advertisement)
        dbus.service.Object.remove_from_connection(advertisement)
        # Handle any cleanup here
        logger.info('SIGINT or CTRL-C detected. Exiting gracefully')
        exit(0)
    signal(SIGINT, handler)
    try:
        global mainloop

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        # get the system bus
        bus = dbus.SystemBus()
        # get the ble controller
        adapter = find_adapter(bus)

        if not adapter:
            logger.critical("GattManager1 interface not found")
            return

        adapter_obj = bus.get_object(BLUEZ_SERVICE_NAME, adapter)

        adapter_props = dbus.Interface(adapter_obj, "org.freedesktop.DBus.Properties")

        # powered property on the controller to on
        adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))

        # Get manager objs
        service_manager = dbus.Interface(adapter_obj, GATT_MANAGER_IFACE)
        ad_manager = dbus.Interface(adapter_obj, LE_ADVERTISING_MANAGER_IFACE)

        advertisement = MeerConAdvertisement(bus, 0)
        obj = bus.get_object(BLUEZ_SERVICE_NAME, "/org/bluez")

        agent = Agent(bus, AGENT_PATH)

        app = Application(bus)
        app.add_service(MeerConS1Service(bus, 2))

        mainloop = MainLoop()

        agent_manager = dbus.Interface(obj, "org.bluez.AgentManager1")
        agent_manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")

        ad_manager.RegisterAdvertisement(
            advertisement.get_path(),
            {},
            reply_handler=register_ad_cb,
            error_handler=register_ad_error_cb,
        )

        logger.info("Registering GATT application...")

        service_manager.RegisterApplication(
            app.get_path(),
            {},
            reply_handler=register_app_cb,
            error_handler=[register_app_error_cb],
        )

        agent_manager.RequestDefaultAgent(AGENT_PATH)

        mainloop.run()
    except Exception as e:
        logger.error(f"{e}")


if __name__ == "__main__":
    main()
    