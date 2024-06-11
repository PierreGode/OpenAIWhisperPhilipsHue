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
    if light_name in lights:
        light = lights[light_name]
        light.hue = hue
        light.saturation = saturation
        light.brightness = brightness
    else:
        print(f"Light {light_name} not found")

def turn_on_light(light_name):
    if light_name in lights:
        lights[light_name].on = True
    else:
        print(f"Light {light_name} not found")

def turn_off_light(light_name):
    if light_name in lights:
        lights[light_name].on = False
    else:
        print(f"Light {light_name} not found")

def normalize_text(text):
    return re.sub(r'[^\w\s]', '', text).strip()

def match_group_name(input_name):
    input_name = normalize_text(input_name).lower()
    group_names_lower = {name.lower(): id for name, id in group_names.items()}
    best_match = process.extractOne(input_name, group_names_lower.keys(), scorer=fuzz.token_sort_ratio)
    if best_match and best_match[1] > 50:
        return group_names_lower[best_match[0]]
    return None

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

def process_audio():
    record_audio('test.wav')
    audio_file = open('test.wav', "rb")
    transcription = client.audio.transcriptions.create(
        model='whisper-1',
        file=audio_file
    )
    print(transcription.text)

    text = transcription.text.strip().lower()
    text = normalize_text(text)
    lang = detect(text)
    
    response_text = ""
    command_executed = False

    # Specific commands
    if "tänd i" in text:
        parts = text.split()
        item_name = ' '.join(parts[2:]).strip()
        if item_name in lights:
            turn_on_light(item_name)
            response_text = f"Light '{item_name}' has been turned on." if lang == 'en' else f"Lampa '{item_name}' har tänts."
        else:
            response_text = turn_on_group(item_name, lang)
        command_executed = True
    elif "släck i" in text:
        parts = text.split()
        item_name = ' '.join(parts[2:]).strip()
        if item_name in lights:
            turn_off_light(item_name)
            response_text = f"Light '{item_name}' has been turned off." if lang == 'en' else f"Lampa '{item_name}' har släckts."
        else:
            response_text = turn_off_group(item_name, lang)
        command_executed = True
    
    # General commands
    elif "turn on all lights" in text or "tänd alla lampor" in text or "turn on the lights" in text or "it's too dark" in text or "it's dark" in text or "kan du tända" in text or "tänd" in text:
        turn_on_all_lights()
        response_text = "All lights have been turned on." if lang == 'en' else "Alla lampor har tänts."
        command_executed = True
    elif "turn off all lights" in text or "släck alla lampor" in text or "the lights hurt my eyes" in text or "the lights are too bright" in text or "att du släcker" in text or "släck" in text:
        turn_off_all_lights()
        response_text = "All lights have been turned off." if lang == 'en' else "Alla lampor har släckts."
        command_executed = True
    elif "set color" in text or "ställ in färgen" in text:
        parts = text.split()
        try:
            light_name = ' '.join(parts[3:5])
            hue = int(parts[-3])
            saturation = int(parts[-2])
            brightness = int(parts[-1])
            set_light_color(light_name, hue, saturation, brightness)
            response_text = f"Set color for light '{light_name}'." if lang == 'en' else f"Ställ in färgen för ljuset '{light_name}'."
            command_executed = True
        except Exception as e:
            print(f"Error setting light color: {e}")
            response_text = "Error occurred while setting the light color." if lang == 'en' else "Fel uppstod när färgen ställdes in."

    if not command_executed:
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
    try:
        thread = Thread(target=process_audio)
        thread.start()
        thread.join()
    except KeyboardInterrupt:
        print("Interrupted by user")
        break
    except Exception as e:
        print(f"An error occurred: {e}")
