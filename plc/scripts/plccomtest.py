from pymodbus.client import ModbusTcpClient

#修改为plc的ip
plc_ip= "192.168.1.5"

#创建modbus客户端
client = ModbusTcpClient(plc_ip)

try:
    #链接plc
    client.connect()

    #读取寄存器d812的值
    result = client.read_holding_registers(address= 0x032C,count = 1,unit = 1)
    print("d812值为：",result.registers[0])

    #写入d850的值 复位的时间 原本是320
    client.write_registers(address= 0x0352,values=320,unit = 1)
    print("写入d850成功")
except Exception as e:
        # 捕获除ModbusException之外的所有异常
    print(f"An error occurred: {e}")
finally:
    client.close()
