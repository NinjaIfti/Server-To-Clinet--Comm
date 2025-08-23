import socket
import time

def test_connection(ip, port, timeout=5):
    """Test connection to server"""
    print(f"Testing connection to {ip}:{port}...")
    
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # Try to connect
        start_time = time.time()
        result = sock.connect_ex((ip, port))
        end_time = time.time()
        
        if result == 0:
            print(f"✅ SUCCESS: Connected to {ip}:{port} in {end_time - start_time:.2f} seconds")
            
            # Try to send a test message
            try:
                sock.send(b"TEST_CONNECTION\n")
                print("✅ SUCCESS: Test message sent successfully")
            except Exception as e:
                print(f"⚠️  WARNING: Could not send test message: {e}")
            
            sock.close()
            return True
        else:
            print(f"❌ FAILED: Connection failed with error code {result}")
            return False
            
    except socket.timeout:
        print(f"❌ FAILED: Connection timed out after {timeout} seconds")
        return False
    except Exception as e:
        print(f"❌ FAILED: Connection error: {e}")
        return False

def main():
    print("Network Connection Test Tool")
    print("=" * 40)
    
    # Test common VM IP addresses
    vm_ips = [
        "172.20.10.7",       # Your VM on mobile hotspot (from ifconfig)
        "192.168.56.1",      # VirtualBox/Hyper-V default
        "192.168.1.100",     # Common home network
        "10.0.2.15",         # VirtualBox NAT
        "172.20.10.6",       # Your Windows machine on mobile hotspot
        "localhost",          # Local connection
        "127.0.0.1"          # Loopback
    ]
    
    port = 12345
    
    print(f"Testing port: {port}")
    print()
    
    successful_connections = []
    
    for ip in vm_ips:
        if test_connection(ip, port):
            successful_connections.append(ip)
        print()
    
    print("=" * 40)
    if successful_connections:
        print("✅ SUCCESSFUL CONNECTIONS:")
        for ip in successful_connections:
            print(f"   • {ip}:{port}")
        print()
        print("Use one of these IP addresses in your client!")
    else:
        print("❌ NO SUCCESSFUL CONNECTIONS")
        print()
        print("Troubleshooting tips:")
        print("1. Make sure the server is running")
        print("2. Check if port 12345 is not blocked by firewall")
        print("3. For mobile hotspot: disable 'Client Isolation'")
        print("4. Ensure both devices are on the same network")
    
    print()
    print("Press Enter to exit...")
    input()

if __name__ == "__main__":
    main()
