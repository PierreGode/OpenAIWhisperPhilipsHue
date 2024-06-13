import json
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
from fuzzywuzzy import fuzz, process
import re
from langdetect import detect

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
client = OpenAI()

# Philips Hue Bridge connection
bridge_ip = '192.168.1.7'
b = Bridge(bridge_ip)
b.connect()
lights = b.get_light_objects('name')
groups = b.get_group()

# Extract group names for fuzzy matching
group_names = {group_info['name']: group_id for group_id, group_info in groups.items()}

# Print all group names for debugging
print("Detected groups:")
for group_name, group_id in group_names.items():
    print(f"Group ID: {group_id}, Name: {group_name}")

# Load commands from JSON file with explicit encoding
with open('commands_lang.json', 'r', encoding='utf-8') as file:
    commands = json.load(file)

# Set preferred language for fallback
preferred_language = 'sv'  # Change this to 'en' or any other supported language

# Initial system prompt for the assistant model
initial_prompt = """
You are an AI named Nova, and you act as a supportive, engaging, and empathetic home assistant.

Here are some example interactions:

User: The lights hurt my eyes.
Nova: I understand. I'll turn off the lights for you.
(This is the same as the command "turn off lights")

User: It's too dark in here.
Nova: Let me turn on the lights for you.
(This is the same as the command "turn on lights")

User: Can you change the color to blue?
Nova: Sure, I'll set the lights to blue.
(This is the same as the command "set color to blue")

Remember to:
- Interpret variations of commands and provide appropriate responses.
- Be polite and supportive.
"""

conversation_history = [
    {"role": "system", "content": initial_prompt}
]

# Play audio using pygame (Windows)
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

# Play audio using ALSA (Linux)
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

# Turn on all lights
def turn_on_all_lights():
    print("Executing turn_on_all_lights")  # Debug statement
    for light in lights.values():
        light.on = True

# Turn off all lights
def turn_off_all_lights():
    print("Executing turn_off_all_lights")  # Debug statement
    for light in lights.values():
        light.on = False

# Set light color
def set_light_color(light_name, hue, saturation, brightness):
    if light_name in lights:
        print(f"Setting color for light {light_name} to hue: {hue}, saturation: {saturation}, brightness: {brightness}")  # Debug statement
        light = lights[light_name]
        light.hue = hue
        light.saturation = saturation
        light.brightness = brightness
    else:
        print(f"Light {light_name} not found")

# Turn on a specific light
def turn_on_light(light_name):
    if light_name in lights:
        print(f"Turning on light {light_name}")  # Debug statement
        lights[light_name].on = True
    else:
        print(f"Light {light_name} not found")

# Turn off a specific light
def turn_off_light(light_name):
    if light_name in lights:
        print(f"Turning off light {light_name}")  # Debug statement
        lights[light_name].on = False

# Normalize text by removing punctuation and converting to lowercase
def normalize_text(text):
    return re.sub(r'[^\w\s]', '', text).strip().lower()

# Match input group name with the closest group name using fuzzy matching
def match_group_name(input_name):
    input_name = normalize_text(input_name)
    group_names_lower = {normalize_text(name): id for name, id in group_names.items()}
    best_match = process.extractOne(input_name, group_names_lower.keys(), scorer=fuzz.token_sort_ratio)
    print(f"Best match for '{input_name}': {best_match}")  # Debug statement
    if best_match and best_match[1] > 50:
        return group_names_lower[best_match[0]]
    return None

# Turn on a specific group of lights
def turn_on_group(group_name, lang):
    print(f"Attempting to turn on group: {group_name}")
    group_id = match_group_name(group_name)
    if group_id:
        print(f"Matched group: {group_name} (ID: {group_id})")
        try:
            b.set_group(int(group_id), 'on', True)
            print(f"Group '{group_name}' turned on (ID: {group_id})")
            return f"Group '{group_name}' has been turned on." if lang == 'en' else f"Grupp '{group_name}' har tänts."
        except Exception as e:
            print(f"Error while turning on group '{group_name}' (ID: {group_id}): {e}")
            return f"Error occurred while turning on group '{group_name}'." if lang == 'en' else f"Fel uppstod när gruppen '{group_name}' tändes."
    else:
        print(f"Group '{group_name}' not found")
        return f"Group '{group_name}' not found." if lang == 'en' else f"Grupp '{group_name}' hittades inte."

# Turn off a specific group of lights
def turn_off_group(group_name, lang):
    print(f"Attempting to turn off group: {group_name}")
    group_id = match_group_name(group_name)
    if group_id:
        print(f"Matched group: {group_name} (ID: {group_id})")
        try:
            b.set_group(int(group_id), 'on', False)
            print(f"Group '{group_name}' turned off (ID: {group_id})")
            return f"Group '{group_name}' has been turned off." if lang == 'en' else f"Grupp '{group_name}' har släckts."
        except Exception as e:
            print(f"Error while turning off group '{group_name}' (ID: {group_id}): {e}")
            return f"Error occurred while turning off group '{group_name}'." if lang == 'en' else f"Fel uppstod när gruppen '{group_name}' släcktes."
    else:
        print(f"Group '{group_name}' not found")
        return f"Group '{group_name}' not found." if lang == 'en' else f"Grupp '{group_name}' hittades inte."

# Check if text matches any command patterns for a specific action
def match_command(text, command_patterns):
    print(f"Matching text '{text}' against patterns {command_patterns}")  # Debug statement
    for pattern in command_patterns:
        if re.search(fr'\b{pattern}', text):  # Match patterns only if they form a complete word boundary
            print(f"Pattern '{pattern}' matched")  # Debug statement
            return True
    return False

# Process audio and execute appropriate light commands
def process_audio():
    record_audio('test.wav')
    audio_file = open('test.wav', "rb")
    transcription = client.audio.transcriptions.create(
        model='whisper-1',
        file=audio_file
    )
    print("Transcript:", transcription.text)

    text = transcription.text.strip().lower()
    text = normalize_text(text)
    detected_lang = detect(text)
    print("Detected language:", detected_lang)  # Debug statement

    # Use detected language if available, otherwise fall back to preferred language
    lang = detected_lang if detected_lang in commands else preferred_language
    print("Using language:", lang)  # Debug statement
    
    response_text = ""
    command_executed = False

    # Load commands for the determined language
    lang_commands = commands.get(lang, commands[preferred_language])

    # Prioritize Group Commands First
    for pattern in lang_commands['turn_on_group']:
        match = re.search(pattern.replace("{group}", "(.+)"), text)
        if match:
            group_name = match.group(1).strip()
            print(f"Extracted group name for turning on: {group_name}")  # Debug statement
            response_text = turn_on_group(group_name, lang)
            command_executed = True
            break
    
    if not command_executed:
        for pattern in lang_commands['turn_off_group']:
            match = re.search(pattern.replace("{group}", "(.+)"), text)
            if match:
                group_name = match.group(1).strip()
                print(f"Extracted group name for turning off: {group_name}")  # Debug statement
                response_text = turn_off_group(group_name, lang)
                command_executed = True
                break

    # General Commands
    if not command_executed:
        if match_command(text, lang_commands['turn_on_all_lights']):
            print(f"Matched command for turning on all lights: {text}")  # Debug statement
            turn_on_all_lights()
            response_text = "All lights have been turned on." if lang == 'en' else "Alla lampor har tänts."
            command_executed = True
        elif match_command(text, lang_commands['turn_off_all_lights']):
            print(f"Matched command for turning off all lights: {text}")  # Debug statement
            turn_off_all_lights()
            response_text = "All lights have been turned off." if lang == 'en' else "Alla lampor har släckts."
            command_executed = True

    # If no command is executed, continue the conversation through the assistant
    if not command_executed:
        print("No command executed. Passing to assistant.")  # Debug statement
        conversation_history.append({"role": "user", "content": transcription.text})
        response = client.chat.completions.create(
            model='gpt-4',
            messages=conversation_history
        )
        assistant_message = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": assistant_message})
        response_text = assistant_message

    print("Response text:", response_text)  # Debug statement

    # Generate speech from the response text
    speech_response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=response_text
    )
    speech_filename = f"speech_{uuid.uuid4()}.mp3"
    speech_response.stream_to_file(speech_filename)
    
    # Play the generated speech
    if is_windows:
        play_audio_with_pygame(speech_filename)
    else:
        play_audio_with_alsa(speech_filename)
    audio_file.close()
    os.remove(speech_filename)

# Main loop to continuously listen and process audio
while True:
    try:
        thread = Thread(target=process_audio)
        thread.start()
        thread.join()
    except KeyboardInterrupt:
        print("Interrupted by user")
        break
    except Exception as e:
        print(f"An error occurred: {e}")
