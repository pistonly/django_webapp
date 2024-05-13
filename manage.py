#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from multiprocessing import Process


def start_log_server():
    # 日志服务器代码
    import socketserver
    import logging
    import logging.handlers
    import struct

    class LogRecordStreamHandler(socketserver.StreamRequestHandler):
        def handle(self):
            while True:
                chunk = self.connection.recv(4)
                if len(chunk) < 4:
                    break
                slen = struct.unpack('>L', chunk)[0]
                record = self.connection.recv(slen)
                obj = logging.makeLogRecord(eval(record))
                logger = logging.getLogger(obj.name)
                logger.handle(obj)

    class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

        def __init__(self, host='localhost', port=logging.handlers.DEFAULT_TCP_LOGGING_PORT):
            socketserver.ThreadingTCPServer.__init__(self, (host, port), LogRecordStreamHandler)
            self.abort = 0
            self.timeout = 1
            self.logname = None

    logging.basicConfig(format='%(relativeCreated)5d %(name)-15s %(levelname)-8s %(message)s')
    tcpserver = LogRecordSocketReceiver()
    print('Starting TCP server for logging...')
    tcpserver.serve_forever()

def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    log_server_process = Process(target=start_log_server)
    log_server_process.start()  # 启动日志服务器
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

