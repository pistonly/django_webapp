'''
M1-3: front shootting of group1
M11-13: NG of g1
M4-6: back shootting of g1
M14-16: NG

D812: delay reset

Y0.8 blow

M37: plc online
M18: plc online

M7 on -> Y0.6

X0.0 X0.2 X0.4 X0.11 continous ON > T, warning. T = D820
M19 stop warning   <--> X0.15

M21 ON clean-light <--> Y0.9    continuous-time: D816(500ms)

==================================================
time line:

X0.0(M202) --(D850)--> M1(shoot, AI) --(D812)--> M11(NG) --(D864)--> blow(Y0.8)(D814 blow time)

X0.4(M212) --(D856)--> M4(shoot, AI) --(D812)--> M14(NG) --(D870)--> blow(Y0.8)(D814 blow time)

'''
from pymodbus.client import ModbusTcpClient
import time

#修改为plc的ip
plc_ip= "192.168.1.5"



def get_register(name:str):
    name = name.lower().strip()
    if name.startswith("d"):
        num = int(name[1:])
    elif name.startswith("x0."):
        num = int(name[3:]) + 0x6300
    elif name.startswith("y0."):
        num = int(name[3:]) + 0xA300
    elif name.startswith("m"):
        num = int(name[1:])
    else:
        print("register name error!")
        return

    return num


class plcControl(object):
    def __init__(self, ip="192.168.1.5") -> None:
        self.client = ModbusTcpClient(ip)
        # self.connect()

    def connected(self):
        self.connect()
        return self.client.connected

    def connect(self):
        return self.client.connect()

    def close(self):
        if self.client is not None:
            self.client.close()

    def set_reg(self, address="m201", value=1):
        address = address.lower()
        if address.startswith("m"):
            return self.set_M(address, value)
        else:
            return self.write_D(address, value)

    def get_reg(self, address="m201"):
        address = address.lower()
        if address.startswith("m"):
            return self.get_M(address)
        else:
            return self.read_D(address)


    def set_M(self, address="m201", value=1):
        if not self.client.connected:
            return False, "client is not connected"
        try:
            assert address.lower().startswith("m"), "address should start with 'm'"
            self.client.write_coil(get_register(address), int(value))
            return True, None
        except Exception as e:
            print("set_M failed", str(e))
            return False, str(e)


    def get_M(self, address="m201"):
        if not self.client.connected:
            return False, "client is not connected"
        try:
            assert address.lower().startswith("m"), "address should start with 'm'"
            res = self.client.read_coils(get_register(address))
            return True, int(res.getBit(0))
        except Exception as e:
            print("get M failed", str(e))
            return False, str(e)

    def write_D(self, address="d812", value=100):
        if not self.client.connected:
            return False, "client is not connected"
        try:
            assert address.lower().startswith("d"), "address should start with 'd'"
            self.client.write_registers(get_register(address), values=int(value))
            return True, None
        except Exception as e:
            print("write D failed: ", str(e))
            return False, str(e)

    def read_D(self, address="d812"):
        if not self.client.connected:
            return False, "client is not connected"
        try:
            assert address.lower().startswith("d"), "address should start with 'd'"
            res = self.client.read_holding_registers(get_register(address))
            return True, res.registers[0]
        except Exception as e:
            print("read D failed", str(e))
            return False, str(e)


if __name__ == "__main__":
    plc = plcControl()
    res = plc.connect()
