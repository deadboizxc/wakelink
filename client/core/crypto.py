import os
import struct
import random


class Crypto:
    """Crypto engine 100% compatible with WakeLink v1.0 firmware."""

    def __init__(self, token: str):
        if len(token) < 32:
            raise ValueError("Token must be ≥32 chars")

        token_bytes = token.encode("utf-8")
        master_key = self._sha256(token_bytes)[:32]

        self.chacha_key = master_key
        self.hmac_key = master_key
        self.request_counter = 0
        self.request_limit = 1000

    # --------------------- SHA256 ---------------------
    def _sha256(self, data: bytes) -> bytes:
        """Full SHA256 implementation.

        This is a pure-Python SHA256 used to derive keys from the device token
        and to produce HMAC values. It mirrors the firmware implementation.
        """
        # Constants
        K = [
            0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
            0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
            0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
            0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
            0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
            0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
            0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
            0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
        ]
        
        # Initial hash values
        h = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
        
        # Pre-processing
        ml = len(data) * 8
        data = bytearray(data)
        data.append(0x80)
        while (len(data) * 8) % 512 != 448:
            data.append(0x00)
        data.extend(struct.pack('>Q', ml))
        
        # Process blocks
        for i in range(0, len(data), 64):
            w = [0] * 64
            block = data[i:i+64]
            
            for j in range(16):
                w[j] = struct.unpack('>I', block[j*4:j*4+4])[0]
            
            for j in range(16, 64):
                s0 = self._rotr(w[j-15], 7) ^ self._rotr(w[j-15], 18) ^ (w[j-15] >> 3)
                s1 = self._rotr(w[j-2], 17) ^ self._rotr(w[j-2], 19) ^ (w[j-2] >> 10)
                w[j] = (w[j-16] + s0 + w[j-7] + s1) & 0xFFFFFFFF
            
            a, b, c, d, e, f, g, h_temp = h
            
            for j in range(64):
                s1 = self._rotr(e, 6) ^ self._rotr(e, 11) ^ self._rotr(e, 25)
                ch = (e & f) ^ (~e & g)
                temp1 = (h_temp + s1 + ch + K[j] + w[j]) & 0xFFFFFFFF
                s0 = self._rotr(a, 2) ^ self._rotr(a, 13) ^ self._rotr(a, 22)
                maj = (a & b) ^ (a & c) ^ (b & c)
                temp2 = (s0 + maj) & 0xFFFFFFFF
                
                h_temp = g
                g = f
                f = e
                e = (d + temp1) & 0xFFFFFFFF
                d = c
                c = b
                b = a
                a = (temp1 + temp2) & 0xFFFFFFFF
            
            h = [(x + y) & 0xFFFFFFFF for x, y in zip(h, [a, b, c, d, e, f, g, h_temp])]
        
        # Build result
        return b''.join(struct.pack('>I', x) for x in h)
    
    def _rotr(self, x: int, n: int) -> int:
        return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF
    
    # --------------------- ChaCha20 ---------------------
    def _chacha20_quarter_round(self, a, b, c, d):
        a = (a + b) & 0xFFFFFFFF
        d ^= a
        d = ((d << 16) | (d >> 16)) & 0xFFFFFFFF
        c = (c + d) & 0xFFFFFFFF
        b ^= c
        b = ((b << 12) | (b >> 20)) & 0xFFFFFFFF
        a = (a + b) & 0xFFFFFFFF
        d ^= a
        d = ((d << 8) | (d >> 24)) & 0xFFFFFFFF
        c = (c + d) & 0xFFFFFFFF
        b ^= c
        b = ((b << 7) | (b >> 25)) & 0xFFFFFFFF
        return a, b, c, d
    
    def _chacha20_block(self, key: bytes, nonce: bytes, counter: int) -> bytes:
        constants = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574]
        
        # Initialize state
        state = constants.copy()
        
        # Key (8 words of 4 bytes)
        key_words = [struct.unpack('<I', key[i:i+4])[0] for i in range(0, 32, 4)]
        state.extend(key_words)
        
        # Counter
        state.append(counter)
        
        # Nonce (3 words of 4 bytes)
        nonce_words = [struct.unpack('<I', nonce[i:i+4])[0] for i in range(0, 12, 4)]
        state.extend(nonce_words)
        
        working_state = state.copy()
        
        # 20 rounds (10 double rounds)
        for _ in range(10):
            # Even rounds
            working_state[0], working_state[4], working_state[8], working_state[12] = self._chacha20_quarter_round(
                working_state[0], working_state[4], working_state[8], working_state[12])
            working_state[1], working_state[5], working_state[9], working_state[13] = self._chacha20_quarter_round(
                working_state[1], working_state[5], working_state[9], working_state[13])
            working_state[2], working_state[6], working_state[10], working_state[14] = self._chacha20_quarter_round(
                working_state[2], working_state[6], working_state[10], working_state[14])
            working_state[3], working_state[7], working_state[11], working_state[15] = self._chacha20_quarter_round(
                working_state[3], working_state[7], working_state[11], working_state[15])
            
            # Odd rounds
            working_state[0], working_state[5], working_state[10], working_state[15] = self._chacha20_quarter_round(
                working_state[0], working_state[5], working_state[10], working_state[15])
            working_state[1], working_state[6], working_state[11], working_state[12] = self._chacha20_quarter_round(
                working_state[1], working_state[6], working_state[11], working_state[12])
            working_state[2], working_state[7], working_state[8], working_state[13] = self._chacha20_quarter_round(
                working_state[2], working_state[7], working_state[8], working_state[13])
            working_state[3], working_state[4], working_state[9], working_state[14] = self._chacha20_quarter_round(
                working_state[3], working_state[4], working_state[9], working_state[14])
        
        # Add original state
        for i in range(16):
            working_state[i] = (working_state[i] + state[i]) & 0xFFFFFFFF
        
        # Convert to bytes (little-endian)
        output = bytearray(64)
        for i in range(16):
            struct.pack_into('<I', output, i * 4, working_state[i])
        
        return bytes(output)
    
    def _chacha20_encrypt(self, key: bytes, nonce: bytes, plaintext: bytes) -> bytes:
        """Encrypt/decrypt using ChaCha20 (symmetric operation).

        This mirrors the firmware ChaCha20 implementation used for packet
        encryption and decryption.
        """
        ciphertext = bytearray(len(plaintext))
        counter = 0
        
        for i in range(0, len(plaintext), 64):
            key_stream = self._chacha20_block(key, nonce, counter)
            block_len = min(64, len(plaintext) - i)
            
            for j in range(block_len):
                ciphertext[i + j] = plaintext[i + j] ^ key_stream[j]
            
            counter += 1
        
        return bytes(ciphertext)

    # --------------------- HMAC ---------------------
    def _hmac_sha256(self, key: bytes, data: bytes) -> bytes:
        if len(key) > 64:
            key = self._sha256(key)
        key = key.ljust(64, b"\x00")
        ipad = bytes(k ^ 0x36 for k in key)
        opad = bytes(k ^ 0x5C for k in key)
        return self._sha256(opad + self._sha256(ipad + data))

    def calculate_hmac(self, data: str) -> str:
        return self._hmac_sha256(self.hmac_key, data.encode("utf-8")).hex()

    def verify_hmac(self, data: str, signature: str) -> bool:
        return self.calculate_hmac(data) == signature.lower()

    def create_secure_response(self, plaintext: str) -> str:
        data = plaintext.encode("utf-8")[:500]
        full_nonce = os.urandom(16)
        nonce12 = full_nonce[:12]
        cipher = self._chacha20_encrypt(self.chacha_key, nonce12, data)
        packet = struct.pack(">H", len(data)) + cipher + full_nonce
        self.request_counter += 1
        return packet.hex()

    def process_secure_packet(self, hex_packet: str) -> str:
        try:
            p = bytes.fromhex(hex_packet)
            if len(p) < 18: 
                return "ERROR:TOO_SHORT"
            
            length = struct.unpack(">H", p[:2])[0]
            if length > 500 or len(p) < 2 + length + 16: 
                return "ERROR:INVALID_SIZE"
            
            cipher = p[2:2+length]
            full_nonce = p[-16:]
            nonce12 = full_nonce[:12]
            
            plain = self._chacha20_encrypt(self.chacha_key, nonce12, cipher)
            self.request_counter += 1
            return plain.decode("utf-8", errors="ignore")
        except Exception as e:
            return f"ERROR:DECRYPT: {str(e)}"