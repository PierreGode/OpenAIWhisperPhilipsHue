import os
import argparse
import platform
import uuid
from openai import OpenAI
import pygame
import time

client = OpenAI()
is_windows = platform.system() == "Windows"


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
        import alsaaudio  # type: ignore
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


def dictate_text(text: str):
    speech_filename = f"speech_{uuid.uuid4()}.mp3"
    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="nova",
        input=text
    ) as speech_response:
        speech_response.stream_to_file(speech_filename)
    play_audio(speech_filename)
    os.remove(speech_filename)


def play_audio(file_path):
    if is_windows:
        play_audio_with_pygame(file_path)
    else:
        play_audio_with_alsa(file_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dicatate text")
    parser.add_argument("text", type=str, help="The text to dictate")
    args = parser.parse_args()
    dictate_text(args.text)
