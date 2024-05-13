import logging
import logging.handlers
import pickle
import struct

class PickleSocketHandler(logging.handlers.SocketHandler):
    def emit(self, record):
        # 序列化日志记录
        try:
            s = pickle.dumps(record)
            slen = struct.pack(">L", len(s))
            self.send(slen)
            self.send(s)
        except Exception as e:
            print(f"Error sending log record: {e}")
