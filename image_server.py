import socket
import threading
import time
import base64
import os
import json
from datetime import datetime

class ImageServer:
    def __init__(self, host='0.0.0.0', port=12346):
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
            
            print(f"Image Server started on {self.host}:{self.port}")
            print("Waiting for connections...")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    print(f"Image client connected: {client_address}")
                    with self.clients_lock:
                        self.clients.append({
                            'socket': client_socket,
                            'address': client_address
                        })
                    
                    # Handle client in separate thread
                    threading.Thread(
                        target=self.handle_client, 
                        args=(client_socket, client_address), 
                        daemon=True
                    ).start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"Error accepting connection: {e}")
                        
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.cleanup()
    
    def handle_client(self, client_socket, client_address):
        buffer = b""
        try:
            while self.running:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    
                    buffer += data
                    
                    # Process complete messages
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        if line:
                            self.process_message(line, client_socket, client_address)
                            
                except socket.error:
                    break
                    
        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
        finally:
            self.remove_client(client_socket)
            try:
                client_socket.close()
            except:
                pass
            print(f"Client {client_address} disconnected")
    
    def process_message(self, message_bytes, sender_socket, sender_address):
        try:
            message_str = message_bytes.decode('utf-8')
            
            if message_str.startswith('IMAGE:'):
                # Handle image data
                image_data = message_str[6:]  # Remove 'IMAGE:' prefix
                self.handle_received_image(image_data, sender_address)
                
            elif message_str.startswith('REQUEST_LIST'):
                # Send list of available server images
                self.send_image_list(sender_socket)
                
            elif message_str.startswith('REQUEST_IMAGE:'):
                # Send specific image to client
                filename = message_str[14:]  # Remove 'REQUEST_IMAGE:' prefix
                self.send_image_to_client(filename, sender_socket)
                
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def handle_received_image(self, image_data_str, sender_address):
        try:
            # Parse image data (format: filename|base64_data)
            parts = image_data_str.split('|', 1)
            if len(parts) != 2:
                print("Invalid image data format")
                return
                
            original_filename, base64_data = parts
            
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
            
            # Broadcast to other clients
            self.broadcast_image_notification(filename, sender_address)
            
        except Exception as e:
            print(f"Error handling received image: {e}")
    
    def broadcast_image_notification(self, filename, sender_address):
        """Notify all clients about new image"""
        notification = f"IMAGE_RECEIVED:{sender_address[0]}|{filename}\n"
        
        with self.clients_lock:
            clients_copy = list(self.clients)
        
        for client_info in clients_copy:
            if client_info['address'] != sender_address:  # Don't send back to sender
                try:
                    client_info['socket'].send(notification.encode('utf-8'))
                except:
                    self.remove_client(client_info['socket'])
    
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
            with open(filepath, 'rb') as f:
                image_data = f.read()
            
            base64_data = base64.b64encode(image_data).decode('utf-8')
            message = f"SERVER_IMAGE:{filename}|{base64_data}\n"
            
            with self.clients_lock:
                clients_copy = list(self.clients)
            
            sent_count = 0
            for client_info in clients_copy:
                try:
                    client_info['socket'].send(message.encode('utf-8'))
                    sent_count += 1
                except:
                    self.remove_client(client_info['socket'])
            
            print(f"Server image '{filename}' sent to {sent_count} clients")
            
        except Exception as e:
            print(f"Error sending server image: {e}")
    
    def remove_client(self, client_socket):
        """Remove client from active clients list"""
        with self.clients_lock:
            self.clients = [c for c in self.clients if c['socket'] != client_socket]
    
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
        print("\nImage Server Commands:")
        print("- 'list' - Show available server images")
        print("- 'send <filename>' - Send image to all clients")
        print("- 'clients' - Show connected clients")
        print("- 'quit' - Stop server\n")
        
        while self.running:
            try:
                user_input = input("ImageServer> ").strip()
                
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
                                print(f"{i}. {client['address']}")
                        else:
                            print("No clients connected")
                            
                elif user_input.lower().startswith('send '):
                    filename = user_input[5:].strip()
                    if filename:
                        self.send_server_image(filename)
                    else:
                        print("Please specify a filename")
                        
                elif user_input:
                    print("Unknown command. Type 'quit' to exit.")
                    
            except KeyboardInterrupt:
                self.running = False
                break
    
    def cleanup(self):
        print("\nShutting down image server...")
        self.running = False
        
        with self.clients_lock:
            clients_copy = list(self.clients)
            self.clients.clear()
        
        for client_info in clients_copy:
            try:
                client_info['socket'].close()
            except:
                pass
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("Image server shut down complete")

def main():
    server = ImageServer()
    
    # Start server in separate thread
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
