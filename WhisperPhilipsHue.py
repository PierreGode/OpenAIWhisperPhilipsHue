from openai import OpenAI
from utils import record_audio, play_audio
import warnings
import os
import time
import pygame
import uuid
import platform
from threading import Thread
from phue import Bridge

warnings.filterwarnings("ignore", category=DeprecationWarning)
client = OpenAI()

# Philips Hue Bridge connection
bridge_ip = '192.168.1.7'
b = Bridge(bridge_ip)
b.connect()
lights = b.get_light_objects('name')

conversation_history = [
    {"role": "system", "content": "You are my assistant. Please answer in short sentences."}
]

def play_audio_with_pygame(file_path):
    pygame.mixer.init()
    time.sleep(0.5)
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.set_volume(1.0)
    time.sleep(0.5)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(1)
    pygame.mixer.quit()

def play_audio_with_alsa(file_path):
    try:
        import alsaaudio
        import wave

        wf = wave.open(file_path, 'rb')
        device = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK)
        device.setchannels(wf.getnchannels())
        device.setrate(wf.getframerate())
        device.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        device.setperiodsize(320)
        data = wf.readframes(320)
        audio_data = []
        while data:
            audio_data.append(data)
            data = wf.readframes(320)
        time.sleep(0.5)
        for chunk in audio_data:
            device.write(chunk)
        wf.close()
    except Exception as e:
        print(f"Error playing audio with ALSA: {e}")

is_windows = platform.system() == "Windows"

def turn_on_all_lights():
    for light in lights.values():
        light.on = True

def turn_off_all_lights():
    for light in lights.values():
        light.on = False

def set_light_color(light_name, hue, saturation, brightness):
    light = lights[light_name]
    light.hue = hue
    light.saturation = saturation
    light.brightness = brightness

def load_commands(filename):
    commands = {}
    current_key = None
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if line.startswith('#'):
                current_key = line[1:].strip()
                commands[current_key] = []
            elif current_key:
                commands[current_key].append(line.lower())
    return commands

def match_command(transcription, commands):
    transcription = transcription.lower()
    for command, phrases in commands.items():
        for phrase in phrases:
            if phrase in transcription:
                return command
    return None

def process_audio():
    record_audio('test.wav')
    audio_file = open('test.wav', "rb")
    transcription = client.audio.transcriptions.create(
        model='whisper-1',
        file=audio_file
    )
    print(transcription.text)

    commands = load_commands('commands.txt')
    matched_command = match_command(transcription.text, commands)

    command_executed = False
    if matched_command == "turn on all lights":
        turn_on_all_lights()
        command_executed = True
    elif matched_command == "turn off all lights":
        turn_off_all_lights()
        command_executed = True
    elif matched_command == "set color of Vardagsrum 6 to hue 50000 saturation 254 brightness 200":
        parts = transcription.text.lower().split()
        try:
            light_name = ' '.join(parts[3:5])
            hue = int(parts[-3])
            saturation = int(parts[-2])
            brightness = int(parts[-1])
            set_light_color(light_name, hue, saturation, brightness)
            command_executed = True
        except Exception as e:
            print(f"Error setting light color: {e}")
    elif "turn on" in transcription.text.lower():
        parts = transcription.text.lower().split()
        light_name = ' '.join(parts[2:])
        if light_name in lights:
            lights[light_name].on = True
            command_executed = True
        else:
            print(f"Light {light_name} not found")
    elif "turn off" in transcription.text.lower():
        parts = transcription.text.lower().split()
        light_name = ' '.join(parts[2:])
        if light_name in lights:
            lights[light_name].on = False
            command_executed = True
        else:
            print(f"Light {light_name} not found")

    if command_executed:
        response_text = "Command executed successfully."
    else:
        conversation_history.append({"role": "user", "content": transcription.text})
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=conversation_history
        )
        assistant_message = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": assistant_message})
        response_text = assistant_message

    print(response_text)

    speech_response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=response_text
    )
    speech_filename = f"speech_{uuid.uuid4()}.mp3"
    speech_response.stream_to_file(speech_filename)
    if is_windows:
        play_audio_with_pygame(speech_filename)
    else:
        play_audio_with_alsa(speech_filename)
    audio_file.close()
    os.remove(speech_filename)

while True:
    thread = Thread(target=process_audio)
    thread.start()
    thread.join()
