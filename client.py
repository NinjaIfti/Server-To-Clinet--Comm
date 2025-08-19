import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import time
import base64
import os
import json
from datetime import datetime
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import torch
    import numpy as np
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

class WindowsClient:
    def __init__(self):
        self.client_socket = None
        self.connected = False
        self.running = False
        self.local_ip = None
        self.received_images_dir = "client_received_images"
        self.processed_images_dir = "processed_images"
        self.selected_image_path = None
        self.yolo_model = None
        self.setup_directories()
        self.setup_yolo()
        self.setup_gui()
        
    def setup_directories(self):
        """Create directories for storing images"""
        os.makedirs(self.received_images_dir, exist_ok=True)
        os.makedirs(self.processed_images_dir, exist_ok=True)
    
    def setup_yolo(self):
        """Initialize YOLOv5 model"""
        if not YOLO_AVAILABLE:
            print("YOLO not available - install torch and numpy")
            return
            
        try:
            # Try to load YOLOv5 model
            model_path = "yolov5s.pt"
            
            # Check if YOLO model file exists
            if os.path.exists(model_path):
                # Load YOLOv5 model
                self.yolo_model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path)
                self.yolo_model.eval()  # Set to evaluation mode
                print("YOLOv5 model loaded successfully!")
            else:
                print("YOLOv5 model file not found. Download yolov5s.pt")
                print("Auto-detection will be disabled.")
                self.yolo_model = None
                
        except Exception as e:
            print(f"Failed to load YOLOv5 model: {e}")
            self.yolo_model = None
    
    def detect_objects(self, image_path):
        """Run YOLOv5 object detection on image"""
        if not self.yolo_model:
            return None, "YOLOv5 model not available"
            
        try:
            print(f"🔍 YOLOv5: Starting object detection on {os.path.basename(image_path)}")
            
            # Run YOLOv5 inference
            results = self.yolo_model(image_path)
            
            # Debug: Show all detections found (even low confidence ones)
            all_detections = results.xyxy[0].cpu().numpy()
            print(f"🔍 YOLOv5: Found {len(all_detections)} total detections")
            
            # Parse results
            detections = []
            for *box, conf, cls in all_detections:
                print(f"   Detection: {self.yolo_model.names[int(cls)]} confidence={conf:.3f}")
                if conf > 0.1:  # Lowered confidence threshold
                    x1, y1, x2, y2 = map(int, box)
                    label = self.yolo_model.names[int(cls)]
                    detections.append({
                        'label': label,
                        'confidence': float(conf),
                        'box': [x1, y1, x2 - x1, y2 - y1]  # Convert to x, y, w, h format
                    })
            
            print(f"🎯 YOLOv5: Detected {len(detections)} objects")
            for det in detections:
                print(f"   - {det['label']}: {det['confidence']:.2f}")
            
            # Draw detections on image
            processed_image_path = self.draw_detections_pil(image_path, detections)
            
            return processed_image_path, f"Detected {len(detections)} objects"
            
        except Exception as e:
            print(f"❌ YOLOv5: Detection failed: {e}")
            return None, f"Detection failed: {e}"
    
    def draw_detections_pil(self, original_path, detections):
        """Draw bounding boxes and labels on image using PIL"""
        try:
            # Open image with PIL
            image = Image.open(original_path)
            draw = ImageDraw.Draw(image)
            
            # Generate colors for different classes
            colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'brown']
            
            for i, detection in enumerate(detections):
                x, y, w, h = detection['box']
                label = detection['label']
                confidence = detection['confidence']
                
                # Get color for this detection
                color = colors[i % len(colors)]
                
                # Draw bounding box
                draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
                
                # Draw label with confidence
                label_text = f"{label}: {confidence:.2f}"
                
                try:
                    # Try to use a default font
                    font = ImageFont.load_default()
                except:
                    font = None
                
                # Draw label background
                bbox = draw.textbbox((x, y - 20), label_text, font=font)
                draw.rectangle(bbox, fill=color)
                
                # Draw label text
                draw.text((x, y - 20), label_text, fill='white', font=font)
            
            # Save processed image
            base_name = os.path.splitext(os.path.basename(original_path))[0]
            processed_name = f"{base_name}_detected.jpg"
            processed_path = os.path.join(self.processed_images_dir, processed_name)
            
            image.save(processed_path)
            print(f"💾 YOLOv5: Processed image saved: {processed_name}")
            
            return processed_path
            
        except Exception as e:
            print(f"❌ YOLOv5: Failed to draw detections: {e}")
            return None
        
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("VM-Windows Communication Client")
        self.root.geometry("700x600")
        
        conn_frame = tk.Frame(self.root)
        conn_frame.pack(pady=10, fill='x', padx=10)
        
        tk.Label(conn_frame, text="VM IP Address:").pack(side='left')
        self.ip_entry = tk.Entry(conn_frame, width=20)
        self.ip_entry.pack(side='left', padx=5)
        self.ip_entry.insert(0, "192.168.0.106")
        
        tk.Label(conn_frame, text="Port:").pack(side='left', padx=(10,0))
        self.port_entry = tk.Entry(conn_frame, width=8)
        self.port_entry.pack(side='left', padx=5)
        self.port_entry.insert(0, "12345")
        
        self.connect_btn = tk.Button(conn_frame, text="Connect", command=self.connect_to_server)
        self.connect_btn.pack(side='left', padx=10)
        
        self.status_label = tk.Label(conn_frame, text="Disconnected", fg="red")
        self.status_label.pack(side='right')
        
        msg_frame = tk.Frame(self.root)
        msg_frame.pack(pady=10, fill='both', expand=True, padx=10)
        
        tk.Label(msg_frame, text="Messages from VM:", font=('Arial', 12, 'bold')).pack(anchor='w')
        
        self.message_area = scrolledtext.ScrolledText(
            msg_frame, wrap=tk.WORD, height=20, font=('Consolas', 11),
            bg='#f0f0f0'
        )
        self.message_area.pack(fill='both', expand=True, pady=5)

        # Image controls frame
        image_frame = tk.Frame(self.root)
        image_frame.pack(pady=5, fill='x', padx=10)
        
        tk.Label(image_frame, text="Image:", font=('Arial', 10, 'bold')).pack(side='left')
        self.select_image_btn = tk.Button(image_frame, text="Select Image", command=self.select_image, state='disabled')
        self.select_image_btn.pack(side='left', padx=5)
        
        self.selected_file_label = tk.Label(image_frame, text="No image selected", fg="gray")
        self.selected_file_label.pack(side='left', padx=5)
        
        self.send_image_btn = tk.Button(image_frame, text="Send Image", command=self.send_image, state='disabled')
        self.send_image_btn.pack(side='right')
        
        self.view_images_btn = tk.Button(image_frame, text="View Received", command=self.view_received_images, state='disabled')
        self.view_images_btn.pack(side='right', padx=5)
        
        self.view_processed_btn = tk.Button(image_frame, text="View Detected", command=self.view_processed_images, state='disabled')
        self.view_processed_btn.pack(side='right', padx=5)
        
        # Input area for sending text messages
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=5, fill='x', padx=10)
        
        tk.Label(input_frame, text="Message:", font=('Arial', 10, 'bold')).pack(side='left')
        self.input_entry = tk.Entry(input_frame)
        self.input_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.input_entry.config(state='disabled')
        self.input_entry.bind('<Return>', lambda _: self.send_message())
        self.send_btn = tk.Button(input_frame, text="Send Text", command=self.send_message, state='disabled')
        self.send_btn.pack(side='left', padx=5)
        
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10, fill='x', padx=10)
        
        self.disconnect_btn = tk.Button(btn_frame, text="Disconnect", command=self.disconnect_from_server, state='disabled')
        self.disconnect_btn.pack(side='left')
        
        self.clear_btn = tk.Button(btn_frame, text="Clear Messages", command=self.clear_messages)
        self.clear_btn.pack(side='left', padx=10)
        
        if not PIL_AVAILABLE:
            self.pil_warning_btn = tk.Button(btn_frame, text="⚠️ Install Pillow for Images", 
                                           command=self.show_pillow_warning, fg="orange")
            self.pil_warning_btn.pack(side='left', padx=10)
            
        if not YOLO_AVAILABLE:
            self.yolo_warning_btn = tk.Button(btn_frame, text="🔍 Install OpenCV for YOLO", 
                                            command=self.show_yolo_warning, fg="blue")
            self.yolo_warning_btn.pack(side='left', padx=10)
        
        tk.Button(btn_frame, text="Exit", command=self.on_closing).pack(side='right')
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def connect_to_server(self):
        if self.connected:
            return
            
        try:
            vm_ip = self.ip_entry.get().strip()
            port = int(self.port_entry.get().strip())
            
            self.add_message("Connecting to server...", "system")
            
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(10)
            self.client_socket.connect((vm_ip, port))
            # After connecting, use a short timeout for recv loop responsiveness
            self.client_socket.settimeout(1.0)
            # Capture local IP to distinguish our own messages when echoed back
            try:
                self.local_ip = self.client_socket.getsockname()[0]
            except Exception:
                self.local_ip = None
            
            self.connected = True
            self.running = True
            
            self.status_label.config(text="Connected", fg="green")
            self.connect_btn.config(state='disabled')
            self.disconnect_btn.config(state='normal')
            self.ip_entry.config(state='disabled')
            self.port_entry.config(state='disabled')
            self.input_entry.config(state='normal')
            self.send_btn.config(state='normal')
            self.select_image_btn.config(state='normal')
            self.view_images_btn.config(state='normal')
            self.view_processed_btn.config(state='normal')
            if self.selected_image_path:
                self.send_image_btn.config(state='normal')
            
            self.add_message(f"Connected to VM at {vm_ip}:{port}", "system")
            
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.cleanup_connection()
    
    def receive_messages(self):
        # Use bytes buffer for better handling of large messages
        buffer = b""
        while self.running and self.connected:
            try:
                data_bytes = self.client_socket.recv(65536)
                if not data_bytes:
                    break

                buffer += data_bytes
                # Only show progress for large transfers
                if len(data_bytes) > 10000 or len(buffer) > 100000:
                    print(f"Received {len(data_bytes)} bytes, buffer size now: {len(buffer)}")

                # Process complete frames from buffer (ending with \n)
                while b'\n' in buffer:
                    line_bytes, buffer = buffer.split(b'\n', 1)
                    try:
                        line = line_bytes.decode('utf-8').strip()
                    except UnicodeDecodeError:
                        line = line_bytes.decode('utf-8', errors='ignore').strip()
                    
                    if not line or line == 'ping':  # Skip empty lines and pings
                        continue
                        
                    # Only show debug for image messages
                    if line.startswith('SERVER_IMAGE:'):
                        print(f"Processing SERVER_IMAGE message: {len(line)} bytes")
                        
                    if line.startswith('MESSAGE:'):
                        payload = line[8:].strip()  # Remove 'MESSAGE:' prefix
                        self.process_text_message(payload)
                        
                    elif line.startswith('SERVER_IMAGE:'):
                        # Handle server image
                        image_data = line[13:]  # Remove 'SERVER_IMAGE:' prefix
                        print(f"Client received SERVER_IMAGE (size: {len(line)} bytes)")
                        # Fix lambda capture issue by creating a proper closure
                        def handle_image(data):
                            self.handle_received_image(data, "server")
                        self.root.after(0, lambda: handle_image(image_data))
                        
                    elif line.startswith('IMAGE_LIST:'):
                        # Handle server images list (for future use)
                        data = line[11:]  # Remove 'IMAGE_LIST:' prefix
                        try:
                            image_list = json.loads(data)
                            self.root.after(0, lambda lst=image_list: self.add_message(f"Server has {len(lst)} images available", "system"))
                        except:
                            pass
                            
                    elif line.startswith('IMAGE_ERROR:'):
                        # Handle image error
                        error = line[12:]  # Remove 'IMAGE_ERROR:' prefix
                        self.root.after(0, lambda err=error: self.add_message(f"Image Error: {err}", "error"))
                
                # Only trim buffer if no complete message is waiting (to avoid breaking large images)
                if len(buffer) > 3145728 and b'\n' not in buffer:  # 3MB and no complete message
                    buffer = buffer[-1048576:]  # Keep last 1MB
                    print(f"Trimmed buffer to {len(buffer)} bytes")

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Receive error: {e}")
                    err_text = f"Connection error: {e}"
                    self.root.after(0, lambda msg=err_text: self.add_message(msg, "error"))
                break

        if self.running:
            self.root.after(0, lambda: self.add_message("Connection lost to VM server", "error"))
            self.root.after(0, self.cleanup_connection)
    
    def process_text_message(self, payload):
        """Process text message from server"""
        if payload:
            # Check for image notification first
            if payload.startswith('IMAGE_RECEIVED:'):
                data = payload[15:]  # Remove 'IMAGE_RECEIVED:' prefix
                if '|' in data:
                    sender_ip, filename = data.split('|', 1)
                    self.root.after(0, lambda: self.add_message(f"📷 Image received from {sender_ip}: {filename}", "system"))
                return
            
            # Process regular text messages
            sender = "VM"
            text = payload
            has_sender = False
            
            if ' | ' in payload:
                sender, text = payload.split(' | ', 1)
                has_sender = True
            elif ': ' in payload:
                sender, text = payload.split(': ', 1)
                has_sender = True

            if has_sender:
                # Identify if this message is ours
                if self.local_ip and sender == self.local_ip:
                    self.root.after(0, lambda msg=text: self.add_message(msg, "you"))
                else:
                    display_sender = sender if sender else "Peer"
                    self.root.after(0, lambda snd=display_sender, msg=text: self.add_message(f"{snd}: {msg}", "peer"))
            else:
                # Treat entire payload as plain VM text
                self.root.after(0, lambda msg=payload: self.add_message(msg, "vm"))
    
    def handle_received_image(self, image_data, source):
        """Handle received image data"""
        try:
            print(f"Processing image data from {source}, length: {len(image_data)}")
            
            # Parse image data (format: filename|base64_data)
            if '|' not in image_data:
                print(f"Invalid image data format - no separator found")
                self.add_message("Invalid image data received - missing separator", "error")
                return
                
            parts = image_data.split('|', 1)
            if len(parts) != 2:
                print(f"Invalid image data format - wrong number of parts: {len(parts)}")
                self.add_message("Invalid image data received", "error")
                return
                
            filename, base64_data = parts
            print(f"Filename: {filename}, Base64 length: {len(base64_data)}")
            
            # Validate base64 data
            if not base64_data:
                print("Empty base64 data")
                self.add_message("Empty image data received", "error")
                return
            
            # Decode base64 image data
            try:
                image_bytes = base64.b64decode(base64_data)
                print(f"Decoded image bytes length: {len(image_bytes)}")
            except Exception as decode_error:
                print(f"Base64 decode error: {decode_error}")
                self.add_message(f"Image decode error: {decode_error}", "error")
                return
            
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_filename = f"{timestamp}_{source}_{filename}"
            filepath = os.path.join(self.received_images_dir, saved_filename)
            
            print(f"Saving image to: {filepath}")
            
            # Save image to file
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            # Verify file was created
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                print(f"Image successfully saved: {saved_filename} ({file_size} bytes)")
                self.add_message(f"📷 Image saved: {saved_filename} ({file_size} bytes)", "system")
                
                # Automatically run YOLO detection on received image
                if self.yolo_model:
                    self.add_message("🔍 Running YOLO object detection...", "system")
                    processed_path, result_msg = self.detect_objects(filepath)
                    if processed_path:
                        self.add_message(f"🎯 YOLO: {result_msg}", "system")
                        self.add_message(f"💾 Processed image saved", "system")
                    else:
                        self.add_message(f"❌ YOLO: {result_msg}", "error")
                else:
                    self.add_message("🔍 YOLO model not available for detection", "system")
            else:
                print(f"Failed to create file: {filepath}")
                self.add_message("Failed to save image file", "error")
            
        except Exception as e:
            print(f"Error in handle_received_image: {e}")
            import traceback
            traceback.print_exc()
            self.add_message(f"Error saving image: {e}", "error")
    
    def add_message(self, message, msg_type="vm"):
        timestamp = time.strftime("%H:%M:%S")
        
        if msg_type == "vm":
            formatted_msg = f"[{timestamp}] VM: {message}\n"
        elif msg_type == "you":
            formatted_msg = f"[{timestamp}] You: {message}\n"
        elif msg_type == "peer":
            formatted_msg = f"[{timestamp}] {message}\n"
        elif msg_type == "system":
            formatted_msg = f"[{timestamp}] SYSTEM: {message}\n"
        elif msg_type == "error":
            formatted_msg = f"[{timestamp}] ERROR: {message}\n"
        else:
            formatted_msg = f"[{timestamp}] {message}\n"
        
        self.message_area.insert(tk.END, formatted_msg)
        self.message_area.see(tk.END)
        print(f"GUI Updated: {formatted_msg.strip()}")

    def send_message(self):
        if not (self.connected and self.client_socket):
            return
        text = self.input_entry.get().strip()
        if not text:
            return
        try:
            frame = f"CLIENT:{text}\n".encode('utf-8')
            self.client_socket.sendall(frame)
            self.input_entry.delete(0, tk.END)
        except Exception as e:
            self.add_message(f"Send failed: {e}", "error")
    
    def select_image(self):
        """Select an image file to send"""
        if not PIL_AVAILABLE:
            self.show_pillow_warning()
            return
            
        filetypes = [
            ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
            ("PNG files", "*.png"),
            ("JPEG files", "*.jpg *.jpeg"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Image to Send",
            filetypes=filetypes
        )
        
        if filename:
            self.selected_image_path = filename
            basename = os.path.basename(filename)
            self.selected_file_label.config(text=basename, fg="black")
            if self.connected:
                self.send_image_btn.config(state='normal')
            self.add_message(f"📷 Selected image: {basename}", "system")
    
    def send_image(self):
        """Send selected image to server"""
        if not (self.connected and self.selected_image_path):
            return
            
        if not PIL_AVAILABLE:
            self.show_pillow_warning()
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
            
            self.add_message(f"📷 Image sent: {filename}", "you")
            
            # Clear selection
            self.selected_image_path = None
            self.selected_file_label.config(text="No image selected", fg="gray")
            self.send_image_btn.config(state='disabled')
            
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send image: {e}")
            self.add_message(f"Image send failed: {e}", "error")
    
    def view_received_images(self):
        """Open the received images folder"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(self.received_images_dir)
            else:  # Linux/Mac
                os.system(f'xdg-open "{self.received_images_dir}"')
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")
    
    def view_processed_images(self):
        """Open the processed images folder"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(self.processed_images_dir)
            else:  # Linux/Mac
                os.system(f'xdg-open "{self.processed_images_dir}"')
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")
    
    def show_pillow_warning(self):
        """Show warning about missing Pillow library"""
        messagebox.showwarning(
            "Pillow Required", 
            "Image functionality requires the Pillow library.\n\n"
            "Install it with: pip install Pillow\n\n"
            "Then restart the application."
        )
    
    def show_yolo_warning(self):
        """Show warning about missing YOLO dependencies"""
        messagebox.showinfo(
            "YOLOv5 Object Detection", 
            "YOLOv5 object detection requires:\n\n"
            "1. Install dependencies:\n"
            "   pip install torch torchvision numpy\n\n"
            "2. Download YOLOv5 model:\n"
            "   wget https://github.com/ultralytics/yolov5/releases/download/v5.0/yolov5s.pt\n\n"
            "Place yolov5s.pt in the same folder as client.py\n\n"
            "Then restart the application."
        )
    
    def disconnect_from_server(self):
        self.running = False
        self.cleanup_connection()
        self.add_message("Disconnected from VM server", "system")
    
    def cleanup_connection(self):
        self.connected = False
        self.running = False
        
        if self.client_socket:
            try:
                try:
                    self.client_socket.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        self.status_label.config(text="Disconnected", fg="red")
        self.connect_btn.config(state='normal')
        self.disconnect_btn.config(state='disabled')
        self.ip_entry.config(state='normal')
        self.port_entry.config(state='normal')
        self.input_entry.config(state='disabled')
        self.send_btn.config(state='disabled')
        self.select_image_btn.config(state='disabled')
        self.send_image_btn.config(state='disabled')
        self.view_images_btn.config(state='disabled')
        self.view_processed_btn.config(state='disabled')
    
    def clear_messages(self):
        self.message_area.delete(1.0, tk.END)
    
    def on_closing(self):
        self.disconnect_from_server()
        self.root.destroy()
    
    def run(self):
        self.root.mainloop()

def main():
    client = WindowsClient()
    client.run()

if __name__ == "__main__":
    main()