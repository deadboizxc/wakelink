#include "tcp_handler.h"
#include "command.h"
#include "platform.h"

/**
 * @brief Start the TCP server and log its listening port.
 */
void TCPHandler::begin() {
    server.begin();
    Serial.printf("TCP server started on port %d\n", TCP_PORT);
}

/**
 * @brief Retrieve the next pending client connection, if available.
 *
 * @return WiFiClient object representing the accepted connection or
 *         an empty client if none are accepting.
 */
WiFiClient TCPHandler::getClient() {
    return getServerClient(server);
}

/**
 * @brief Read a single packet from the client and forward it for processing.
 *
 * The handler waits until a newline or timeout, assembles the packet string,
 * and invokes `processClient`. The client is disconnected afterwards.
 */
void TCPHandler::handle() {
    WiFiClient client = getClient();
    if (!client) return;

    char buffer[1024];
    size_t len = 0;
    unsigned long timeout = millis();

    while (client.connected() && millis() - timeout < 5000) {
        if (client.available()) {
            int c = client.read();
            if (c < 0) break;
            if (len < sizeof(buffer) - 1) {
                buffer[len++] = (char)c;
            } else {
                Serial.println("Packet too big, dropping");
                break;
            }
            if ((char)c == '\n') break;
        }
    }

    if (len == 0) {
        client.stop();
        return;
    }

    buffer[len] = '\0';
    String packetData = String(buffer);
    packetData.trim();
    Serial.printf("RX %u bytes\n", packetData.length());

    processClient(client, packetData);
}

/**
 * @brief Validate and dispatch an incoming packet from the TCP client.
 *
 * This method decrypts/validates the packet, executes the associated command,
 * and replies with either the command result or an error packet. The connection
 * is closed after replying.
 *
 * @param client Connected client socket.
 * @param packetData Raw packet string received from the client.
 */
void TCPHandler::processClient(WiFiClient& client, const String& packetData) {
    String response;
    
    JsonDocument incoming = packetManager->processIncomingPacket(packetData);
    
    if (incoming["status"] == "success") {
        const char* command = incoming["command"];
        String requestId = incoming["request_id"] | "unknown";
        
        if (command && strlen(command) > 0) {
            JsonObject data = incoming["data"].as<JsonObject>();
            JsonDocument result = CommandManager::executeCommand(String(command), data);
            result["request_id"] = requestId;
            response = packetManager->createResponsePacket(result);
        } else {
            JsonDocument error;
            error["status"] = "error";
            error["error"] = "NO_COMMAND_IN_JSON";
            error["request_id"] = requestId;
            response = packetManager->createResponsePacket(error);
        }
    } else {
        const char* err = incoming["error"] | "PACKET_ERROR";
        JsonDocument errorResp;
        errorResp["status"] = "error";
        errorResp["error"] = err;
        errorResp["request_id"] = incoming["request_id"];
        response = packetManager->createResponsePacket(errorResp);
    }

    if (client.connected()) {
        client.print(response + "\n");
    }
    client.stop();
}