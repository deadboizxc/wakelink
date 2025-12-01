/**
 * @file tcp_handler.h
 * @brief TCP server handler for local WakeLink communication.
 * 
 * Provides local network communication via TCP on port 99.
 * Handles encrypted protocol v1.0 packets from Python CLI
 * and other local clients.
 * 
 * Protocol:
 * - Each connection handles one packet (terminated by newline)
 * - Packet is decrypted, command executed, response encrypted
 * - Connection closed after response sent
 * 
 * Packet Format:
 * - Outer JSON: {device_id, payload, signature, version}
 * - Payload: hex-encoded encrypted inner JSON
 * - Signature: HMAC-SHA256 of payload
 * 
 * @note Timeout: 5 seconds per connection.
 * 
 * @author deadboizxc
 * @version 1.0
 */

#pragma once
#include "platform.h"
#include "packet.h"
#include "config.h"

/**
 * @brief TCP server handler class.
 * 
 * Wraps WiFiServer to handle encrypted WakeLink protocol packets.
 * Each connection is processed synchronously: receive, decrypt,
 * execute command, encrypt response, send, close.
 */
class TCPHandler {
private:
    WiFiServer server;           ///< Underlying WiFi TCP server
    PacketManager* packetManager; ///< Packet encryption/decryption manager

    /**
     * @brief Process received packet and send response.
     * 
     * Decrypts packet, extracts command, executes via CommandManager,
     * encrypts response, and sends back to client.
     * 
     * @param client Connected client socket.
     * @param packetData Raw packet string (trimmed, without newline).
     */
    void processClient(WiFiClient& client, const String& packetData);

    /**
     * @brief Accept next pending client connection.
     * 
     * Platform abstraction: uses server.available() on ESP8266,
     * server.accept() on ESP32.
     * 
     * @return WiFiClient object (check with if(client) for validity).
     */
    WiFiClient getClient();

public:
    /**
     * @brief Construct TCP handler.
     * 
     * @param port TCP port to listen on (default: 99).
     * @param pm Pointer to PacketManager for encryption.
     */
    TCPHandler(int port, PacketManager* pm)
        : server(port), packetManager(pm) {}

    /**
     * @brief Start TCP server.
     * 
     * Begins listening for incoming connections.
     * Call once during setup() after WiFi connected.
     */
    void begin();

    /**
     * @brief Handle pending TCP clients.
     * 
     * Checks for new connections, reads packet data,
     * and processes one client per call.
     * 
     * @note Call from loop() every iteration.
     */
    void handle();
};