import bluetooth
from micropython import const

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

SERVICE_UUID = "b84ecc2c-cdcc-4c56-8381-307011eb3d1e"
CHARACTERISTIC_UUID = "3642a706-d67c-4a68-a2e0-237c50c7a72a"


class ESP32_BLE:
    def __init__(self, name, service_uuid=SERVICE_UUID, characteristic_uuid=CHARACTERISTIC_UUID):
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq_handler)
        self.service_uuid = service_uuid
        self.characteristic_uuid = characteristic_uuid
        self.name = name
        self._write_callback = None

        # 定义服务和特征值
        self._service = (bluetooth.UUID(self.service_uuid), ((
                                                                 bluetooth.UUID(self.characteristic_uuid),
                                                                 bluetooth.FLAG_READ | bluetooth.FLAG_WRITE
                                                             ),))
        ((self._handle,),) = self.ble.gatts_register_services((self._service,))
        self.ble.gatts_write(self._handle, b"Hello, BLE!")  # 初始化特征值

        # 开始广播
        self.advertise()

    def _irq_handler(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            print("Central connected:", conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            print("Central disconnected:", conn_handle)
            self.advertise()  # 客户端断开后重新广播
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if value_handle == self._handle:
                value = self.ble.gatts_read(self._handle)
                if callable(self._write_callback):
                    self._write_callback(value)

    def advertise(self):
        print("Starting advertising...")
        self.ble.gap_advertise(100, self.advertising_payload())

    def advertising_payload(self):
        adv_data = bytearray()
        adv_data.extend(b'\x02\x01\x06')
        adv_data.extend(bytes([len(self.name) + 1]))
        adv_data.extend(b'\x09')
        adv_data.extend(self.name.encode())
        return adv_data

    def on_write(self, callback):
        self._write_callback = callback


if __name__ == "__main__":
    ble = ESP32_BLE("ESP32BLE")
    ble.on_write(lambda data: print("Received data:", data))

    while True:
        pass


