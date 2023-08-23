import os
import time
import subprocess
import sys
import dbus, dbus.mainloop.glib
from gi.repository import GLib
from example_advertisement import Advertisement
from example_advertisement import register_ad_cb, register_ad_error_cb
from example_gatt_server import Service, Characteristic
from example_gatt_server import register_app_cb, register_app_error_cb

BLUEZ_SERVICE_NAME =           'org.bluez'
DBUS_OM_IFACE =                'org.freedesktop.DBus.ObjectManager'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
GATT_MANAGER_IFACE =           'org.bluez.GattManager1'
GATT_CHRC_IFACE =              'org.bluez.GattCharacteristic1'
UART_SERVICE_UUID =                 '6e400001-b5a3-f393-e0a9-e50e24dcca9e'
UART_TX_CHARACTERISTIC_UUID =       '6e400003-b5a3-f393-e0a9-e50e24dcca9e'
UART_RX_CHARACTERISTIC_UUID =       '6e400002-b5a3-f393-e0a9-e50e24dcca9e'
UART_RX_CHARACTERISTIC_NEW_UUID =   '6e400004-b5a3-f393-e0a9-e50e24dcca9e'

LOCAL_NAME =                   'rpi-gatt-server'
mainloop = None

class TxCharacteristic(Characteristic):
    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, UART_TX_CHARACTERISTIC_UUID,
                                ['notify'], service)
        self.notifying = False
        GLib.io_add_watch(sys.stdin, GLib.IO_IN, self.on_console_input)

    def on_console_input(self, fd, condition):
        s = fd.readline()
        if s.isspace():
            pass
        else:
            self.send_tx(s)
        return True

    def send_tx(self, s):
        if not self.notifying:
            return
        value = []
        for c in s:
            value.append(dbus.Byte(c.encode()))
        self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': value}, [])

    def StartNotify(self):
        if self.notifying:
            return
        self.notifying = True

    def StopNotify(self):
        if not self.notifying:
            return
        self.notifying = False

class RxCharacteristic(Characteristic):
    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, UART_RX_CHARACTERISTIC_UUID,
                                ['read','write'], service)

    def WriteValue(self, value, options):
        print('entering write value'.format(bytearray(value).decode()))
        byte_array = bytearray(value)

        # Convert the received byte array to a string
        data_str = byte_array.decode('utf-8')

        # Store the received string in the "rgb_text.txt" file
        file_path = '/home/admin/rpi-rgb-led-matrix/examples-api-use/rgb_text.txt'
        with open(file_path, 'wb') as f:
            f.write(data_str.encode('utf-8'))
            print('writing')
        f.close()
        # Print the received data for debugging
        print('writing completed : {}'.format(data_str))
        
        kill_text_example()
        time.sleep(3)
        run_text_example()

class RxCharacteristic_new(Characteristic):
    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, UART_RX_CHARACTERISTIC_NEW_UUID,
                                ['read','write'], service)

    def WriteValue(self, value, options):
        print('entering write value_new'.format(bytearray(value).decode()))
        byte_array = bytearray(value)

        # Convert the received byte array to a string
        data_str = byte_array.decode('utf-8')

        # Store the received string in the "rgb_text.txt" file
        file_path = '/home/admin/rpi-rgb-led-matrix/examples-api-use/color_text.txt'
        with open(file_path, 'wb') as f:
            f.write(data_str.encode('utf-8'))
            print('writing_color')
        f.close()
        # Print the received data for debugging
        print('writing completed : {}'.format(data_str))
        
        kill_text_example()
        time.sleep(3)
        run_text_example()


class UartService(Service):
    def __init__(self, bus, index):
        Service.__init__(self, bus, index, UART_SERVICE_UUID, True)
        self.add_characteristic(TxCharacteristic(bus, 0, self))
        self.add_characteristic(RxCharacteristic(bus, 1, self))
        self.add_characteristic(RxCharacteristic_new(bus, 2, self))

class Application(dbus.service.Object):
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
        return response

class UartApplication(Application):
    def __init__(self, bus):
        Application.__init__(self, bus)
        self.add_service(UartService(bus, 0))

class UartAdvertisement(Advertisement):
    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.add_service_uuid(UART_SERVICE_UUID)
        self.add_local_name(LOCAL_NAME)
        self.include_tx_power = True

def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                               DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    for o, props in objects.items():
        if LE_ADVERTISING_MANAGER_IFACE in props and GATT_MANAGER_IFACE in props:
            return o
        print('Skip adapter:', o)
    return None
    
def kill_text_example():
    # os.system("sudo pkill -f 'text-example'")
    # print("clear screen.")
    with open("/home/admin/rpi-rgb-led-matrix/examples-api-use/switch.txt", 'w') as f:
        f.write("stop")
    print('RGB-OFF')
    os.system("pkill -f 'testscript'")
    print('killed testscript.')
    return
    
def run_text_example():
    print("calling run_text_example ")
    
    #os.system("python /home/admin/rpi-rgb-led-matrix/examples-api-use/testscript.py")
    subprocess.Popen(['python','/home/admin/rpi-rgb-led-matrix/examples-api-use/testscript.py'])
    print("testscript called")
    #os.system("pkill -f 'testscript'")
    #print("testscript killed")
    
    #print("kill-tesrscript()")

    
    #print("testscript-kill")
    # print("start_testscript")
    # os.chdir("/home/admin/rpi-rgb-led-matrix/examples-api-use")
    # command = "sudo ./text-example --led-no-hardware-pulse --led-cols=64 --led-rows=64 --led-gpio-mapping=adafruit-hat-pwm"
    # os.system(command)
    # try:
        # with open("/home/admin/rpi-rgb-led-matrix/examples-api-use/switch.txt", 'w') as f:
            # f.write("start.")
        # print('RGB-ON')
    # except Exception as e:
        # print('Error:testscript1: {}'.format(e))
    # command = "sudo /home/admin/rpi-rgb-led-matrix/examples-api-use/text-example --led-no-hardware-pulse --led-cols=64 --led-rows=64 --led-gpio-mapping=adafruit-hat-pwm"
    # os.system(command)

    return
    
def main():
    global mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    adapter = find_adapter(bus)
    if not adapter:
        print('BLE adapter not found')
        return

    service_manager = dbus.Interface(
                                bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                GATT_MANAGER_IFACE)
    ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                LE_ADVERTISING_MANAGER_IFACE)

    app = UartApplication(bus)
    adv = UartAdvertisement(bus, 0)

    mainloop = GLib.MainLoop()

    service_manager.RegisterApplication(app.get_path(), {},
                                        reply_handler=register_app_cb,
                                        error_handler=register_app_error_cb)
    ad_manager.RegisterAdvertisement(adv.get_path(), {},
                                     reply_handler=register_ad_cb,
                                     error_handler=register_ad_error_cb)
    try:
        mainloop.run()
    except KeyboardInterrupt:
        adv.Release()
        mainloop.quit()

if __name__ == '__main__':
    main()
