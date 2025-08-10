import socket
import threading
import time

class VMServer:
    def __init__(self, host='0.0.0.0', port=12345):
        self.host = host
        self.port = port
        self.clients = []
        self.clients_lock = threading.Lock()
        self.server_socket = None
        self.running = False
    
    def start_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"Server started on {self.host}:{self.port}")
            print("Waiting for connections...")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    print(f"Connection established with {client_address}")
                    with self.clients_lock:
                        self.clients.append(client_socket)
                    
                    # One thread for pinging/keepalive and one for reading client messages
                    threading.Thread(target=self.handle_client_writer, args=(client_socket, client_address), daemon=True).start()
                    threading.Thread(target=self.handle_client_reader, args=(client_socket, client_address), daemon=True).start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"Error accepting connection: {e}")
                        
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.cleanup()
    
    def handle_client_writer(self, client_socket, client_address):
        try:
            while self.running:
                try:
                    client_socket.sendall(b"ping\n")
                    time.sleep(1)
                except:
                    break
        except Exception as e:
            print(f"Error handling client (writer) {client_address}: {e}")
        finally:
            with self.clients_lock:
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            client_socket.close()
            print(f"Client {client_address} disconnected (writer)")

    def handle_client_reader(self, client_socket, client_address):
        buffer = ""
        client_socket.settimeout(1.0)
        try:
            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    try:
                        text = data.decode('utf-8')
                    except UnicodeDecodeError:
                        text = data.decode('utf-8', errors='ignore')
                    buffer += text
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line.startswith('CLIENT:'):
                            msg = line[len('CLIENT:'):].strip()
                            if msg:
                                print(f"From {client_address}: {msg}")
                                # Normalize broadcast as "<ip> | <msg>" to avoid ambiguous colons in IPv6
                                self.broadcast_message(f"{client_address[0]} | {msg}")
                except socket.timeout:
                    continue
                except Exception:
                    break
        finally:
            # Reader ends; writer cleanup will handle removal/close
            pass
    
    def broadcast_message(self, message):
        with self.clients_lock:
            clients_snapshot = list(self.clients)
        if not clients_snapshot:
            print("No clients connected to broadcast to")
            return
            
        disconnected_clients = []
        for client in clients_snapshot:
            try:
                full_message = f"MESSAGE:{message}\n"
                client.sendall(full_message.encode('utf-8'))
                print(f"Sent to client: {message}")
            except Exception as e:
                print(f"Failed to send to client: {e}")
                disconnected_clients.append(client)
        
        if disconnected_clients:
            with self.clients_lock:
                for client in disconnected_clients:
                    if client in self.clients:
                        self.clients.remove(client)
    
    def input_handler(self):
        print("\nYou can now type messages to send to Windows clients:")
        print("Type 'quit' to stop the server\n")
        
        while self.running:
            try:
                user_input = input("VM> ")
                if user_input.lower() == 'quit':
                    self.running = False
                    break
                elif user_input.strip():
                    self.broadcast_message(user_input)
            except KeyboardInterrupt:
                self.running = False
                break
    
    def cleanup(self):
        print("\nShutting down server...")
        self.running = False
        
        with self.clients_lock:
            clients_copy = list(self.clients)
            self.clients.clear()
        for client in clients_copy:
            try:
                try:
                    client.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                client.close()
            except:
                pass
        
        if self.server_socket:
            try:
                try:
                    self.server_socket.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                self.server_socket.close()
            except:
                pass
        
        print("Server shut down complete")

def main():
    server = VMServer()
    
    server_thread = threading.Thread(target=server.start_server)
    server_thread.daemon = True
    server_thread.start()
    
    time.sleep(1)
    
    try:
        server.input_handler()
    except KeyboardInterrupt:
        pass
    finally:
        server.cleanup()

if __name__ == "__main__":
    main()