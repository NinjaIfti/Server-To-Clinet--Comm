import socket
import time

s = socket.socket()
s.connect(('192.168.0.106', 12345))
print("Connected!")

while True:
    try:
        data = s.recv(1024).decode('utf-8')
        if data:
            print(f"Received: '{data}'")
    except:
        time.sleep(0.1)