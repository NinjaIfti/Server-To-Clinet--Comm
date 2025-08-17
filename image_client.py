import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog, ttk
import base64
import os
import json
from datetime import datetime
from PIL import Image, ImageTk

class ImageClient:
    def __init__(self):
        self.client_socket = None
        self.connected = False
        self.running = False
        self.received_images_dir = "client_received_images"
        self.setup_directories()
        self.setup_gui()
        
    def setup_directories(self):
        """Create directory for storing received images"""
        os.makedirs(self.received_images_dir, exist_ok=True)
        
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("Image Transfer Client")
        self.root.geometry("800x700")
        
        # Connection frame
        conn_frame = tk.Frame(self.root)
        conn_frame.pack(pady=10, fill='x', padx=10)
        
        tk.Label(conn_frame, text="Server IP:").pack(side='left')
        self.ip_entry = tk.Entry(conn_frame, width=15)
        self.ip_entry.pack(side='left', padx=5)
        self.ip_entry.insert(0, "192.168.0.106")
        
        tk.Label(conn_frame, text="Port:").pack(side='left', padx=(10,0))
        self.port_entry = tk.Entry(conn_frame, width=8)
        self.port_entry.pack(side='left', padx=5)
        self.port_entry.insert(0, "12346")
        
        self.connect_btn = tk.Button(conn_frame, text="Connect", command=self.connect_to_server)
        self.connect_btn.pack(side='left', padx=10)
        
        self.status_label = tk.Label(conn_frame, text="Disconnected", fg="red")
        self.status_label.pack(side='right')
        
        # Main content frame with notebook for tabs
        main_frame = tk.Frame(self.root)
        main_frame.pack(pady=10, fill='both', expand=True, padx=10)
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # Send Image Tab
        self.send_frame = tk.Frame(self.notebook)
        self.notebook.add(self.send_frame, text="Send Images")
        self.setup_send_tab()
        
        # Receive Images Tab
        self.receive_frame = tk.Frame(self.notebook)
        self.notebook.add(self.receive_frame, text="Received Images")
        self.setup_receive_tab()
        
        # Server Images Tab
        self.server_frame = tk.Frame(self.notebook)
        self.notebook.add(self.server_frame, text="Server Images")
        self.setup_server_tab()
        
        # Control buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10, fill='x', padx=10)
        
        self.disconnect_btn = tk.Button(btn_frame, text="Disconnect", 
                                      command=self.disconnect_from_server, state='disabled')
        self.disconnect_btn.pack(side='left')
        
        tk.Button(btn_frame, text="Exit", command=self.on_closing).pack(side='right')
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_send_tab(self):
        # Image selection frame
        select_frame = tk.Frame(self.send_frame)
        select_frame.pack(pady=10, fill='x')
        
        tk.Button(select_frame, text="Select Image", command=self.select_image).pack(side='left')
        self.selected_file_label = tk.Label(select_frame, text="No image selected", fg="gray")
        self.selected_file_label.pack(side='left', padx=10)
        
        self.send_image_btn = tk.Button(select_frame, text="Send Image", 
                                       command=self.send_image, state='disabled')
        self.send_image_btn.pack(side='right')
        
        # Image preview frame
        preview_frame = tk.Frame(self.send_frame)
        preview_frame.pack(pady=10, fill='both', expand=True)
        
        tk.Label(preview_frame, text="Image Preview:", font=('Arial', 12, 'bold')).pack(anchor='w')
        
        self.preview_label = tk.Label(preview_frame, text="No image selected", 
                                    bg='lightgray', width=40, height=15)
        self.preview_label.pack(pady=5)
        
        self.selected_image_path = None
    
    def setup_receive_tab(self):
        # Received images list
        list_frame = tk.Frame(self.receive_frame)
        list_frame.pack(pady=10, fill='both', expand=True)
        
        tk.Label(list_frame, text="Received Images:", font=('Arial', 12, 'bold')).pack(anchor='w')
        
        # Listbox with scrollbar
        listbox_frame = tk.Frame(list_frame)
        listbox_frame.pack(fill='both', expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.received_listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set)
        self.received_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.received_listbox.yview)
        
        self.received_listbox.bind('<Double-Button-1>', self.view_received_image)
        
        # Buttons for received images
        recv_btn_frame = tk.Frame(list_frame)
        recv_btn_frame.pack(fill='x', pady=5)
        
        tk.Button(recv_btn_frame, text="View Selected", command=self.view_received_image).pack(side='left')
        tk.Button(recv_btn_frame, text="Refresh List", command=self.refresh_received_list).pack(side='left', padx=10)
        tk.Button(recv_btn_frame, text="Open Folder", command=self.open_received_folder).pack(side='right')
    
    def setup_server_tab(self):
        # Server images list
        server_list_frame = tk.Frame(self.server_frame)
        server_list_frame.pack(pady=10, fill='both', expand=True)
        
        tk.Label(server_list_frame, text="Server Images:", font=('Arial', 12, 'bold')).pack(anchor='w')
        
        # Listbox with scrollbar for server images
        server_listbox_frame = tk.Frame(server_list_frame)
        server_listbox_frame.pack(fill='both', expand=True, pady=5)
        
        server_scrollbar = tk.Scrollbar(server_listbox_frame)
        server_scrollbar.pack(side='right', fill='y')
        
        self.server_listbox = tk.Listbox(server_listbox_frame, yscrollcommand=server_scrollbar.set)
        self.server_listbox.pack(side='left', fill='both', expand=True)
        server_scrollbar.config(command=self.server_listbox.yview)
        
        # Buttons for server images
        server_btn_frame = tk.Frame(server_list_frame)
        server_btn_frame.pack(fill='x', pady=5)
        
        tk.Button(server_btn_frame, text="Request List", command=self.request_server_images).pack(side='left')
        tk.Button(server_btn_frame, text="Download Selected", 
                 command=self.download_server_image).pack(side='left', padx=10)
        
        # Activity log
        log_frame = tk.Frame(self.server_frame)
        log_frame.pack(pady=10, fill='x')
        
        tk.Label(log_frame, text="Activity Log:", font=('Arial', 10, 'bold')).pack(anchor='w')
        self.activity_log = scrolledtext.ScrolledText(log_frame, height=8, font=('Consolas', 9))
        self.activity_log.pack(fill='x', pady=5)
    
    def connect_to_server(self):
        if self.connected:
            return
            
        try:
            server_ip = self.ip_entry.get().strip()
            port = int(self.port_entry.get().strip())
            
            self.log_activity("Connecting to server...")
            
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(10)
            self.client_socket.connect((server_ip, port))
            self.client_socket.settimeout(1.0)
            
            self.connected = True
            self.running = True
            
            self.status_label.config(text="Connected", fg="green")
            self.connect_btn.config(state='disabled')
            self.disconnect_btn.config(state='normal')
            self.ip_entry.config(state='disabled')
            self.port_entry.config(state='disabled')
            self.send_image_btn.config(state='normal' if self.selected_image_path else 'disabled')
            
            self.log_activity(f"Connected to server at {server_ip}:{port}")
            
            # Start receiving thread
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            # Request server images list
            self.request_server_images()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.cleanup_connection()
    
    def receive_messages(self):
        buffer = b""
        while self.running and self.connected:
            try:
                data = self.client_socket.recv(8192)
                if not data:
                    break
                
                buffer += data
                
                # Process complete messages
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    if line:
                        self.process_server_message(line.decode('utf-8'))
                        
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.root.after(0, lambda: self.log_activity(f"Connection error: {e}"))
                break
        
        if self.running:
            self.root.after(0, lambda: self.log_activity("Connection lost to server"))
            self.root.after(0, self.cleanup_connection)
    
    def process_server_message(self, message):
        try:
            if message.startswith('SERVER_IMAGE:'):
                # Handle server image
                data = message[13:]  # Remove 'SERVER_IMAGE:' prefix
                self.handle_received_image(data, "server")
                
            elif message.startswith('IMAGE_RECEIVED:'):
                # Handle notification of image from another client
                data = message[15:]  # Remove 'IMAGE_RECEIVED:' prefix
                sender_ip, filename = data.split('|', 1)
                self.root.after(0, lambda: self.log_activity(f"Image received from {sender_ip}: {filename}"))
                
            elif message.startswith('IMAGE_LIST:'):
                # Handle server images list
                data = message[11:]  # Remove 'IMAGE_LIST:' prefix
                image_list = json.loads(data)
                self.root.after(0, lambda: self.update_server_images_list(image_list))
                
            elif message.startswith('IMAGE_ERROR:'):
                # Handle image error
                error = message[12:]  # Remove 'IMAGE_ERROR:' prefix
                self.root.after(0, lambda: self.log_activity(f"Error: {error}"))
                
        except Exception as e:
            self.root.after(0, lambda: self.log_activity(f"Error processing message: {e}"))
    
    def handle_received_image(self, image_data, source):
        try:
            # Parse image data (format: filename|base64_data)
            parts = image_data.split('|', 1)
            if len(parts) != 2:
                self.log_activity("Invalid image data received")
                return
                
            filename, base64_data = parts
            
            # Decode base64 image data
            image_bytes = base64.b64decode(base64_data)
            
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_filename = f"{timestamp}_{source}_{filename}"
            filepath = os.path.join(self.received_images_dir, saved_filename)
            
            # Save image to file
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            self.root.after(0, lambda: self.log_activity(f"Image saved: {saved_filename}"))
            self.root.after(0, self.refresh_received_list)
            
        except Exception as e:
            self.root.after(0, lambda: self.log_activity(f"Error saving image: {e}"))
    
    def select_image(self):
        filetypes = [
            ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
            ("PNG files", "*.png"),
            ("JPEG files", "*.jpg *.jpeg"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Image",
            filetypes=filetypes
        )
        
        if filename:
            self.selected_image_path = filename
            self.selected_file_label.config(text=os.path.basename(filename), fg="black")
            self.send_image_btn.config(state='normal' if self.connected else 'disabled')
            self.show_image_preview(filename)
    
    def show_image_preview(self, image_path):
        try:
            # Open and resize image for preview
            image = Image.open(image_path)
            image.thumbnail((300, 300), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo  # Keep reference
            
        except Exception as e:
            self.preview_label.config(image="", text=f"Preview error: {e}")
    
    def send_image(self):
        if not (self.connected and self.selected_image_path):
            return
            
        try:
            # Read image file
            with open(self.selected_image_path, 'rb') as f:
                image_data = f.read()
            
            # Encode image as base64
            base64_data = base64.b64encode(image_data).decode('utf-8')
            filename = os.path.basename(self.selected_image_path)
            
            # Send image to server
            message = f"IMAGE:{filename}|{base64_data}\n"
            self.client_socket.send(message.encode('utf-8'))
            
            self.log_activity(f"Image sent: {filename}")
            
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send image: {e}")
            self.log_activity(f"Send error: {e}")
    
    def request_server_images(self):
        if not self.connected:
            return
            
        try:
            message = "REQUEST_LIST\n"
            self.client_socket.send(message.encode('utf-8'))
            self.log_activity("Requested server images list")
            
        except Exception as e:
            self.log_activity(f"Error requesting images: {e}")
    
    def update_server_images_list(self, image_list):
        self.server_listbox.delete(0, tk.END)
        for image in image_list:
            self.server_listbox.insert(tk.END, image)
        self.log_activity(f"Server images list updated ({len(image_list)} images)")
    
    def download_server_image(self):
        if not self.connected:
            return
            
        selection = self.server_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection", "Please select an image to download")
            return
            
        filename = self.server_listbox.get(selection[0])
        
        try:
            message = f"REQUEST_IMAGE:{filename}\n"
            self.client_socket.send(message.encode('utf-8'))
            self.log_activity(f"Requested image: {filename}")
            
        except Exception as e:
            self.log_activity(f"Error requesting image: {e}")
    
    def refresh_received_list(self):
        self.received_listbox.delete(0, tk.END)
        
        if os.path.exists(self.received_images_dir):
            images = [f for f in os.listdir(self.received_images_dir) 
                     if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
            images.sort(reverse=True)  # Newest first
            
            for image in images:
                self.received_listbox.insert(tk.END, image)
    
    def view_received_image(self, event=None):
        selection = self.received_listbox.curselection()
        if not selection:
            return
            
        filename = self.received_listbox.get(selection[0])
        filepath = os.path.join(self.received_images_dir, filename)
        
        if os.path.exists(filepath):
            try:
                # Open image with default system viewer
                os.startfile(filepath)
            except:
                messagebox.showerror("Error", "Could not open image")
    
    def open_received_folder(self):
        try:
            os.startfile(self.received_images_dir)
        except:
            messagebox.showerror("Error", "Could not open folder")
    
    def log_activity(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.activity_log.insert(tk.END, log_entry)
        self.activity_log.see(tk.END)
    
    def disconnect_from_server(self):
        self.running = False
        self.cleanup_connection()
        self.log_activity("Disconnected from server")
    
    def cleanup_connection(self):
        self.connected = False
        self.running = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        self.status_label.config(text="Disconnected", fg="red")
        self.connect_btn.config(state='normal')
        self.disconnect_btn.config(state='disabled')
        self.ip_entry.config(state='normal')
        self.port_entry.config(state='normal')
        self.send_image_btn.config(state='disabled')
    
    def on_closing(self):
        self.disconnect_from_server()
        self.root.destroy()
    
    def run(self):
        # Refresh received images list on startup
        self.refresh_received_list()
        self.root.mainloop()

def main():
    try:
        client = ImageClient()
        client.run()
    except Exception as e:
        print(f"Error starting client: {e}")

if __name__ == "__main__":
    main()
