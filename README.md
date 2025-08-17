# Server-To-Client Communication

A Python-based client-server communication system designed for VM-to-Windows messaging with integrated text and image transfer capabilities.

## Overview

This project provides a unified real-time messaging and image transfer system that allows communication between a VM server and Windows clients. Both text messages and images are handled in the same conversation interface, providing seamless multimedia communication.

## Features

### Unified Communication System (server.py / client.py)
- **Multi-client Support**: Server can handle multiple simultaneous client connections
- **Real-time Messaging**: Instant text message broadcasting between server and clients
- **Image Transfer**: Send and receive images in the same conversation
- **Unified GUI**: Single Windows client interface for both text and images
- **Bidirectional Communication**: Both server-to-client and client-to-server messaging
- **Connection Management**: Automatic connection handling with keepalive pings
- **Message History**: Scrollable display with timestamps for both text and image notifications
- **Thread-safe Operations**: Proper handling of concurrent connections
- **Automatic Image Saving**: Images are saved with timestamps and source identification
- **Multiple Image Formats**: Support for PNG, JPG, JPEG, GIF, BMP formats
- **Server Image Library**: VM can maintain and share a collection of images
- **Visual Indicators**: Emoji indicators for image-related activities

## Files

### Main System (Unified Text + Image)
- `server.py` - VM server with integrated text messaging and image transfer
- `client.py` - Windows GUI client with unified text and image interface
- `test_client.py` - Simple test client for basic connection testing
- `requirements.txt` - Python dependencies (includes Pillow for images)

### Legacy Separate System (Optional)
- `image_server.py` - Standalone image server (for reference)
- `image_client.py` - Standalone image client (for reference)

## Requirements

### For the Unified System
- **Python 3.6+**
- **tkinter** (usually included with Python)
- **Pillow (PIL)** - Required for image functionality: `pip install Pillow`
- **Standard libraries**: socket, threading, base64, json, os, datetime, time

**Note**: Both VM (server) and Windows (client) systems need Pillow installed for full image functionality.

## Setup and Usage

### Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

Or install Pillow directly:
```bash
pip install Pillow
```

### Unified Communication System

#### Running the Server (VM Side)
1. Run the unified server on your VM:
```bash
python server.py
```
2. The server will start on `0.0.0.0:12345` by default
3. Server automatically creates two directories:
   - `received_images/` - stores images received from clients
   - `server_images/` - place images here to share with clients
4. Available server commands:
   - Type regular messages to broadcast to all clients
   - `list` - Show available server images
   - `send <filename>` - Send image from server_images/ to all clients
   - `clients` - Show connected clients
   - `quit` - Stop server

#### Running the Client (Windows Side)
1. Run the unified client application:
```bash
python client.py
```
2. Enter the VM's IP address (default: 192.168.0.106)
3. Enter the port number (default: 12345)
4. Click "Connect" to establish connection
5. **Text Messages**: Type in the message field and click "Send Text"
6. **Images**: Click "Select Image", choose a file, then click "Send Image"
7. **View Received Images**: Click "View Received" to open the images folder
8. All communication (text and image notifications) appears in the same conversation area

### Testing Connection

Use the simple test client to verify basic connectivity:
```bash
python test_client.py
```

## Configuration

### Server Configuration
The unified server can be configured by modifying the `VMServer` class initialization:
- `host`: IP address to bind to (default: '0.0.0.0')
- `port`: Port number to listen on (default: 12345)
- `received_images_dir`: Directory for received images (default: 'received_images')
- `server_images_dir`: Directory for server images (default: 'server_images')

### Client Configuration
The GUI client allows runtime configuration of:
- VM IP address
- Port number
- Received images directory (default: 'client_received_images')

## Message Protocols

The unified system uses a single protocol that handles both text and image data:

### Client to Server
- Text Messages: `CLIENT:<content>\n`
- Image Upload: `IMAGE:<filename>|<base64_encoded_data>\n`
- Request Image List: `REQUEST_LIST\n`
- Request Specific Image: `REQUEST_IMAGE:<filename>\n`

### Server to Client
- Keepalive: `ping\n`
- Text Messages: `MESSAGE:<sender> | <content>\n`
- Server Image: `SERVER_IMAGE:<filename>|<base64_encoded_data>\n`
- Image List: `IMAGE_LIST:<json_array_of_filenames>\n`
- Image Notifications: `MESSAGE:IMAGE_RECEIVED:<sender_ip>|<filename>\n`
- Error Messages: `IMAGE_ERROR:<error_description>\n`

## Architecture

### Unified Communication System

#### Server (`VMServer`)
- **Connection Handling**: Accepts multiple client connections on single port
- **Threading**: Uses separate threads for each client (reader/writer pairs)
- **Message Broadcasting**: Sends both text and image data to all connected clients
- **Image Management**: Automatic directory creation and file organization
- **Base64 Encoding**: Converts binary image data for network transmission
- **Server Library**: Maintains collection of server-side images for sharing
- **Unified Protocol**: Handles both text and binary data seamlessly

#### GUI Client (`WindowsClient`)
- **Unified Interface**: Single window for both text and image communication
- **Message Display**: Shows text messages and image notifications in same area
- **Image Controls**: Integrated image selection and sending functionality
- **File Management**: Automatic saving of received images with timestamps
- **Error Handling**: Graceful handling of missing Pillow library
- **Threading**: Separate thread for receiving all message types
- **Visual Indicators**: Emoji indicators for different message types

## Network Communication

### Unified System
- **Protocol**: TCP sockets on single port
- **Text Encoding**: UTF-8 for text messages
- **Image Encoding**: Base64 encoding for binary image data
- **Buffer Size**: 8KB for efficient data transfer
- **Timeout Handling**: 1-second timeouts for responsive operation
- **Error Recovery**: Graceful handling of connection failures
- **Port**: Default 12345 (single port for all communication)
- **File Formats**: PNG, JPG, JPEG, GIF, BMP support

## Usage Examples

### Server Console Commands
```
VM> Hello all clients!        # Broadcast text message
VM> list                      # Show available server images
VM> send photo.jpg            # Send image to all clients
VM> clients                   # Show connected clients
VM> quit                      # Stop server
```

### Client Operations
1. **Connect**: Enter VM IP and port, click "Connect"
2. **Send Text**: Type message and click "Send Text"
3. **Send Image**: Click "Select Image", choose file, click "Send Image"
4. **View Messages**: All text and image notifications appear in conversation area
5. **View Images**: Click "View Received" to open received images folder
6. **Visual Indicators**: 📷 emoji indicates image-related activities

## Troubleshooting

### Connection Issues
- Verify the VM IP address is correct
- Check firewall settings on both VM and Windows machines
- Ensure port 12345 is not blocked
- Confirm the server is running before connecting clients
- Both text and images use the same port (12345)

### Message Display Issues
- Messages are timestamped and categorized by sender
- Your own messages appear as "You:"
- Other client messages show the sender's IP
- System messages indicate connection status
- Image activities show 📷 emoji indicators

### Image Issues
- **Missing Pillow**: Install with `pip install Pillow` on both VM and Windows
- **Supported Formats**: PNG, JPG, JPEG, GIF, BMP
- **Large Images**: May take time to transfer, watch for completion messages
- **Server Images**: Place in `server_images/` directory on VM
- **Client Warning**: Orange warning button appears if Pillow not installed

### Directory Structure
The applications automatically create these directories:
```
VM Side (Server):
├── received_images/          # Images received from clients
└── server_images/           # Images to share with clients

Windows Side (Client):
└── client_received_images/   # Images received from server/clients
```

## Development

The unified system is structured for easy modification and extension:

### Code Organization
- **Server Logic**: All functionality in the `VMServer` class
- **Client GUI**: Unified interface in the `WindowsClient` class
- **Protocol Handling**: Single protocol handles both text and binary data
- **Threading**: Properly managed for stability and responsiveness

### Key Features
- **Unified Protocol**: Seamless handling of text and image data
- **Error Handling**: Graceful degradation when Pillow is missing
- **File Management**: Automatic directory creation and organization
- **Visual Feedback**: Emoji indicators and status messages
- **Thread Safety**: Proper locking for concurrent operations

### Extension Points
- Easy to add new message types to the protocol
- Image processing can be enhanced with additional Pillow features
- GUI can be extended with additional controls
- Server commands can be easily added to the input handler

## License

This project is provided as-is for educational and development purposes.
