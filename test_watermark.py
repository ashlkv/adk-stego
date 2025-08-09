#!/usr/bin/env python3

import subprocess
import sys
import os


def add_watermark(input_file, output_file, message, strength=16):
    """Add a watermark to an audio file using audiowmark Docker container."""
    try:
        current_dir = os.getcwd()
        result = subprocess.run([
            'docker', 'run', '--rm', '-v', f'{current_dir}:/data',
            'audiowmark', 'add', '--strength', str(strength),
            f'/data/{input_file}', f'/data/{output_file}', message
        ], capture_output=True, text=True, check=True)
        print(f"Watermark added successfully to {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error adding watermark: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: docker command not found. Please install Docker first.")
        return False


def get_watermark(input_file):
    """Extract watermark from an audio file using audiowmark Docker container."""
    try:
        current_dir = os.getcwd()
        result = subprocess.run([
            'docker', 'run', '--rm', '-v', f'{current_dir}:/data',
            'audiowmark', 'get', f'/data/{input_file}'
        ], capture_output=True, text=True, check=True)
        # Parse the output to extract hex watermark
        output_lines = result.stdout.strip().split('\n')
        for line in output_lines:
            if 'pattern' in line:
                # Extract hex from pattern line: "pattern  0:00 6469736f626579000000000000000000 2.271 0.640 CLIP-A"
                parts = line.split()
                if len(parts) >= 3:
                    return parts[2]  # The hex part
        return output_lines[0] if output_lines else None
    except subprocess.CalledProcessError as e:
        print(f"Error extracting watermark: {e.stderr}")
        return None
    except FileNotFoundError:
        print("Error: docker command not found. Please install Docker first.")
        return None

def encode_message(text):
    """Encode text to hex format for watermarking."""
    hex_str = text.encode().hex()
    # Pad to 32 characters with zeros
    return hex_str.ljust(32, '0')[:32]


def decode_message(hex_str):
    """Decode hex watermark back to text."""
    try:
        return bytes.fromhex(hex_str.rstrip('0')).decode('utf-8')
    except (ValueError, UnicodeDecodeError):
        return hex_str


def main():
    
    # Example usage with predefined messages from README
    input_file = "in.wav"
    output_file = "out.wav"
    
    # Use "disobey" message from README
    message = "6469736f626579000000000000000000"
    
    if not os.path.exists(input_file):
        print(f"Input file {input_file} does not exist")
        print("Please provide a valid WAV file as input")
        return
    
    print(f"Adding watermark to {input_file}...")
    if add_watermark(input_file, output_file, message):
        print(f"Extracting watermark from {output_file}...")
        extracted = get_watermark(output_file)
        if extracted:
            print(f"Extracted hex: {extracted}")
            decoded = decode_message(extracted)
            print(f"Decoded message: '{decoded}'")


if __name__ == "__main__":
    main()