# Server-To-Client Communication

A Python-based client-server communication system designed for VM-to-Windows messaging with a GUI client interface.

## Overview

This project provides a real-time messaging system that allows communication between a VM server and Windows clients. The server can broadcast messages to multiple connected clients, and clients can send messages back to the server and other connected clients.

## Features

- **Multi-client Support**: Server can handle multiple simultaneous client connections
- **Real-time Messaging**: Instant message broadcasting between server and clients
- **GUI Client**: User-friendly Windows client with tkinter interface
- **Bidirectional Communication**: Both server-to-client and client-to-server messaging
- **Connection Management**: Automatic connection handling with keepalive pings
- **Message History**: Scrollable message display with timestamps
- **Thread-safe Operations**: Proper handling of concurrent connections

## Files

- `server.py` - VM server that accepts connections and broadcasts messages
- `client.py` - Windows GUI client for connecting to the server
- `test_client.py` - Simple test client for basic connection testing

## Requirements

- Python 3.6+
- tkinter (usually included with Python)
- socket (standard library)
- threading (standard library)

## Setup and Usage

### Running the Server (VM Side)

1. Run the server on your VM:
```bash
python server.py
```

2. The server will start on `0.0.0.0:12345` by default
3. You can type messages in the server console to broadcast to all connected clients
4. Type 'quit' to stop the server

### Running the GUI Client (Windows Side)

1. Run the client application:
```bash
python client.py
```

2. Enter the VM's IP address (default: 192.168.0.106)
3. Enter the port number (default: 12345)
4. Click "Connect" to establish connection
5. Use the input field at the bottom to send messages
6. View received messages in the main text area

### Testing Connection

Use the simple test client to verify basic connectivity:
```bash
python test_client.py
```

## Configuration

### Server Configuration
The server can be configured by modifying the `VMServer` class initialization:
- `host`: IP address to bind to (default: '0.0.0.0')
- `port`: Port number to listen on (default: 12345)

### Client Configuration
The GUI client allows runtime configuration of:
- VM IP address
- Port number

## Message Protocol

The system uses a simple text-based protocol:

### Server to Client
- Keepalive: `ping\n`
- Messages: `MESSAGE:<sender> | <content>\n`

### Client to Server
- Messages: `CLIENT:<content>\n`

## Architecture

### Server (`VMServer`)
- **Connection Handling**: Accepts multiple client connections
- **Threading**: Uses separate threads for each client (reader/writer pairs)
- **Message Broadcasting**: Sends messages to all connected clients
- **Cleanup**: Proper connection cleanup on shutdown

### GUI Client (`WindowsClient`)
- **tkinter Interface**: Modern GUI with connection controls and message display
- **Message Parsing**: Handles different message types (VM, peer, system, error)
- **Threading**: Separate thread for receiving messages
- **Connection Management**: Connect/disconnect functionality

## Network Communication

- **Protocol**: TCP sockets
- **Encoding**: UTF-8 text encoding
- **Timeout Handling**: 1-second timeouts for responsive operation
- **Error Recovery**: Graceful handling of connection failures

## Usage Examples

### Server Console Commands
```
VM> Hello all clients!        # Broadcast message
VM> quit                      # Stop server
```

### Client Operations
1. Connect to server using IP and port
2. Send messages using the input field
3. View all messages in the scrollable area
4. Disconnect cleanly using the Disconnect button

## Troubleshooting

### Connection Issues
- Verify the VM IP address is correct
- Check firewall settings on both VM and Windows machines
- Ensure the port (12345) is not blocked
- Confirm the server is running before connecting clients

### Message Display Issues
- Messages are timestamped and categorized by sender
- Your own messages appear as "You:"
- Other client messages show the sender's IP
- System messages indicate connection status

## Development

The code is structured for easy modification and extension:
- Server logic is contained in the `VMServer` class
- Client GUI is in the `WindowsClient` class
- Protocol handling is centralized for easy updates
- Threading is properly managed for stability

## License

This project is provided as-is for educational and development purposes.
