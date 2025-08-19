import socket
import threading
import time
import base64
import os
import json
from datetime import datetime

class VMServer:
    def __init__(self, host='0.0.0.0', port=12345):
        self.host = host
        self.port = port
        self.clients = []
        self.clients_lock = threading.Lock()
        self.server_socket = None
        self.running = False
        self.received_images_dir = "received_images"
        self.server_images_dir = "server_images"
        self.setup_directories()
    
    def setup_directories(self):
        """Create directories for storing images"""
        os.makedirs(self.received_images_dir, exist_ok=True)
        os.makedirs(self.server_images_dir, exist_ok=True)
    
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
        buffer = b""  # Use bytes buffer for better handling
        client_socket.settimeout(1.0)
        try:
            while self.running:
                try:
                    data = client_socket.recv(65536)  # Increased buffer size for images
                    if not data:
                        break
                    
                    buffer += data
                    
                    # Process complete messages (ending with \n)
                    while b'\n' in buffer:
                        line_bytes, buffer = buffer.split(b'\n', 1)
                        try:
                            line = line_bytes.decode('utf-8').strip()
                        except UnicodeDecodeError:
                            line = line_bytes.decode('utf-8', errors='ignore').strip()
                        
                        if not line:
                            continue
                            
                        if line.startswith('CLIENT:'):
                            msg = line[len('CLIENT:'):].strip()
                            if msg:
                                print(f"From {client_address}: {msg}")
                                self.broadcast_message(f"{client_address[0]} | {msg}")
                        elif line.startswith('IMAGE:'):
                            # Handle image data
                            image_data = line[6:]  # Remove 'IMAGE:' prefix
                            print(f"Received image from {client_address} (message size: {len(line)} bytes)")
                            self.handle_received_image(image_data, client_address)
                        elif line.startswith('REQUEST_LIST'):
                            # Send list of available server images
                            self.send_image_list(client_socket)
                        elif line.startswith('REQUEST_IMAGE:'):
                            # Send specific image to client
                            filename = line[14:]  # Remove 'REQUEST_IMAGE:' prefix
                            self.send_image_to_client(filename, client_socket)
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Error in client reader: {e}")
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
                # Only print message if it's not image data (to avoid huge base64 strings)
                if not message.startswith('SERVER_IMAGE:'):
                    print(f"Sent to client: {message}")
                else:
                    # Extract just filename for image messages
                    if '|' in message:
                        filename = message.split('|')[0].replace('SERVER_IMAGE:', '')
                        print(f"Sent image to client: {filename}")
            except Exception as e:
                print(f"Failed to send to client: {e}")
                disconnected_clients.append(client)
        
        if disconnected_clients:
            with self.clients_lock:
                for client in disconnected_clients:
                    if client in self.clients:
                        self.clients.remove(client)
    
    def handle_received_image(self, image_data_str, sender_address):
        try:
            # Parse image data (format: filename|base64_data)
            parts = image_data_str.split('|', 1)
            if len(parts) != 2:
                print(f"Invalid image data format. Parts: {len(parts)}")
                print(f"Data preview: {image_data_str[:100]}...")
                return
                
            original_filename, base64_data = parts
            print(f"Processing image: {original_filename} (size: {len(base64_data)} chars)")
            
            # Decode base64 image data
            image_bytes = base64.b64decode(base64_data)
            
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sender_ip = sender_address[0].replace('.', '_')
            filename = f"{timestamp}_{sender_ip}_{original_filename}"
            filepath = os.path.join(self.received_images_dir, filename)
            
            # Save image to file
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            print(f"Image received and saved: {filename}")
            
            # Broadcast image notification to other clients
            self.broadcast_image_notification(original_filename, sender_address)
            
        except Exception as e:
            print(f"Error handling received image: {e}")
    
    def broadcast_image_notification(self, filename, sender_address):
        """Notify all clients about new image"""
        notification = f"IMAGE_RECEIVED:{sender_address[0]}|{filename}"
        self.broadcast_message(notification)
    
    def send_image_list(self, client_socket):
        """Send list of available server images"""
        try:
            images = []
            if os.path.exists(self.server_images_dir):
                for filename in os.listdir(self.server_images_dir):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                        images.append(filename)
            
            image_list = json.dumps(images)
            message = f"IMAGE_LIST:{image_list}\n"
            client_socket.send(message.encode('utf-8'))
            
        except Exception as e:
            print(f"Error sending image list: {e}")
    
    def send_image_to_client(self, filename, client_socket):
        """Send specific image to client"""
        try:
            filepath = os.path.join(self.server_images_dir, filename)
            if not os.path.exists(filepath):
                error_msg = f"IMAGE_ERROR:File not found: {filename}\n"
                client_socket.send(error_msg.encode('utf-8'))
                return
            
            # Read and encode image
            with open(filepath, 'rb') as f:
                image_data = f.read()
            
            base64_data = base64.b64encode(image_data).decode('utf-8')
            message = f"SERVER_IMAGE:{filename}|{base64_data}\n"
            client_socket.send(message.encode('utf-8'))
            
            print(f"Sent image to client: {filename}")
            
        except Exception as e:
            print(f"Error sending image: {e}")
    
    def send_server_image(self, filename):
        """Broadcast server image to all clients"""
        filepath = os.path.join(self.server_images_dir, filename)
        if not os.path.exists(filepath):
            print(f"Image not found: {filename}")
            return
        
        try:
            print(f"Reading image file: {filepath}")
            with open(filepath, 'rb') as f:
                image_data = f.read()
            
            print(f"Image file size: {len(image_data)} bytes")
            
            base64_data = base64.b64encode(image_data).decode('utf-8')
            print(f"Base64 encoded size: {len(base64_data)} characters")
            
            # Create the message - format: SERVER_IMAGE:filename|base64_data
            message = f"SERVER_IMAGE:{filename}|{base64_data}\n"
            
            # Send image directly to clients
            with self.clients_lock:
                clients_snapshot = list(self.clients)
            
            if not clients_snapshot:
                print("No clients connected to send image to")
                return
                
            disconnected_clients = []
            sent_count = 0
            for client in clients_snapshot:
                try:
                    print(f"Sending image to client: {len(message)} bytes total")
                    client.sendall(message.encode('utf-8'))
                    sent_count += 1
                    print(f"Successfully sent to client {sent_count}")
                except Exception as e:
                    print(f"Failed to send image to client: {e}")
                    disconnected_clients.append(client)
            
            if disconnected_clients:
                with self.clients_lock:
                    for client in disconnected_clients:
                        if client in self.clients:
                            self.clients.remove(client)
            
            print(f"Server image '{filename}' sent to {sent_count} clients")
            
        except Exception as e:
            print(f"Error sending server image: {e}")
            import traceback
            traceback.print_exc()
    
    def list_server_images(self):
        """List available server images"""
        if os.path.exists(self.server_images_dir):
            images = [f for f in os.listdir(self.server_images_dir) 
                     if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
            if images:
                print("\nAvailable server images:")
                for i, img in enumerate(images, 1):
                    print(f"{i}. {img}")
                return images
            else:
                print("No images found in server_images directory")
                return []
        else:
            print("Server images directory not found")
            return []
    
    def input_handler(self):
        print("\nVM Server Commands:")
        print("- Type messages to send to clients")
        print("- 'list' - Show available server images")
        print("- 'send <filename>' - Send image to all clients")
        print("- 'clients' - Show connected clients")
        print("- 'quit' - Stop server\n")
        
        while self.running:
            try:
                user_input = input("VM> ").strip()
                
                if user_input.lower() == 'quit':
                    self.running = False
                    break
                    
                elif user_input.lower() == 'list':
                    self.list_server_images()
                    
                elif user_input.lower() == 'clients':
                    with self.clients_lock:
                        if self.clients:
                            print(f"\nConnected clients ({len(self.clients)}):")
                            for i, client in enumerate(self.clients, 1):
                                try:
                                    addr = client.getpeername()
                                    print(f"{i}. {addr}")
                                except:
                                    print(f"{i}. Unknown address")
                        else:
                            print("No clients connected")
                            
                elif user_input.lower().startswith('send '):
                    filename = user_input[5:].strip()
                    if filename:
                        self.send_server_image(filename)
                    else:
                        print("Please specify a filename")
                        
                elif user_input:
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