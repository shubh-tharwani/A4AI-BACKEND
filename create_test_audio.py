#!/usr/bin/env python3
"""
Create Test Audio File for Voice Assistant API
This script creates a simple WAV file for testing purposes.
"""

import wave
import struct
import math

def create_test_audio():
    """Create a simple test audio file with beeps that simulate speech patterns"""
    
    # Audio parameters
    sample_rate = 16000  # 16 kHz (standard for speech recognition)
    duration = 2.0  # 2 seconds
    channels = 1  # Mono
    bits_per_sample = 16
    
    # Calculate number of samples
    num_samples = int(sample_rate * duration)
    
    # Create audio data with multiple tones (simulating speech-like patterns)
    audio_data = []
    
    for i in range(num_samples):
        t = float(i) / sample_rate
        
        # Create a pattern that changes over time (like speech)
        if t < 0.5:
            # First part: 440 Hz (A note)
            frequency = 440
        elif t < 1.0:
            # Second part: 523 Hz (C note) 
            frequency = 523
        elif t < 1.5:
            # Third part: 659 Hz (E note)
            frequency = 659
        else:
            # Final part: back to 440 Hz
            frequency = 440
            
        # Generate sine wave
        amplitude = 0.3  # Moderate volume
        sample = amplitude * math.sin(2 * math.pi * frequency * t)
        
        # Add envelope to make it more speech-like
        envelope = math.sin(t * math.pi * 4) * 0.5 + 0.5
        sample = sample * envelope
        
        # Convert to 16-bit integer
        audio_data.append(int(sample * 32767))
    
    # Save as WAV file
    filename = "generated_test_audio.wav"
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(bits_per_sample // 8)
        wav_file.setframerate(sample_rate)
        
        # Write audio data
        for sample in audio_data:
            wav_file.writeframesraw(struct.pack('<h', sample))
    
    print(f"✅ Created test audio file: {filename}")
    print(f"   Duration: {duration} seconds")
    print(f"   Sample rate: {sample_rate} Hz")
    print(f"   Channels: {channels} (mono)")
    print(f"   Bit depth: {bits_per_sample} bits")
    print(f"   File size: ~{len(audio_data) * 2} bytes")
    print(f"\n📝 NOTE: This is just test tones, not actual speech.")
    print(f"   For better testing, record your own voice saying:")
    print(f"   'Hello, this is a test for the voice assistant'")

if __name__ == "__main__":
    create_test_audio()
