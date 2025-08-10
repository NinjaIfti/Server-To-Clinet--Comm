import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import time

class WindowsClient:
    def __init__(self):
        self.client_socket = None
        self.connected = False
        self.running = False
        self.local_ip = None
        self.setup_gui()
        
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("VM-Windows Communication Client")
        self.root.geometry("600x500")
        
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

        # Input area for sending messages
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=5, fill='x', padx=10)
        self.input_entry = tk.Entry(input_frame)
        self.input_entry.pack(side='left', fill='x', expand=True)
        self.input_entry.config(state='disabled')
        self.input_entry.bind('<Return>', lambda _: self.send_message())
        self.send_btn = tk.Button(input_frame, text="Send", command=self.send_message, state='disabled')
        self.send_btn.pack(side='left', padx=(8, 0))
        
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10, fill='x', padx=10)
        
        self.disconnect_btn = tk.Button(btn_frame, text="Disconnect", command=self.disconnect_from_server, state='disabled')
        self.disconnect_btn.pack(side='left')
        
        self.clear_btn = tk.Button(btn_frame, text="Clear Messages", command=self.clear_messages)
        self.clear_btn.pack(side='left', padx=10)
        
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
            
            self.add_message(f"Connected to VM at {vm_ip}:{port}", "system")
            
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.cleanup_connection()
    
    def receive_messages(self):
        # Accumulate text data and extract MESSAGE:...\n frames robustly, even if other
        # noise (e.g., pings without newlines) is interleaved or concatenated.
        buffer = ""
        while self.running and self.connected:
            try:
                data_bytes = self.client_socket.recv(1024)
                if not data_bytes:
                    break

                try:
                    data = data_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    # Fallback: ignore undecodable bytes (unlikely for ASCII messages)
                    data = data_bytes.decode('utf-8', errors='ignore')

                buffer += data

                # Extract complete MESSAGE frames regardless of preceding noise
                while True:
                    start_idx = buffer.find('MESSAGE:')
                    if start_idx == -1:
                        # No message start yet; to avoid unbounded growth due to noise like 'ping',
                        # trim buffer if it gets too large.
                        if len(buffer) > 8192:
                            buffer = buffer[-4096:]
                        break

                    end_idx = buffer.find('\n', start_idx)
                    if end_idx == -1:
                        # Partial message; keep only from 'MESSAGE:' onwards
                        buffer = buffer[start_idx:]
                        break

                    payload = buffer[start_idx + len('MESSAGE:'):end_idx].strip()
                    if payload:
                        # Prefer normalized separator " | ", then fallback to ": "
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
                                print(f"Received self message: {text}")
                            else:
                                display_sender = sender if sender else "Peer"
                                self.root.after(0, lambda snd=display_sender, msg=text: self.add_message(f"{snd}: {msg}", "peer"))
                                print(f"Received message from {sender}: {text}")
                        else:
                            # Treat entire payload as plain VM text
                            self.root.after(0, lambda msg=payload: self.add_message(msg, "vm"))
                            print(f"Received message: {payload}")

                    # Drop everything up to and including the newline we just processed
                    buffer = buffer[end_idx + 1:]

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