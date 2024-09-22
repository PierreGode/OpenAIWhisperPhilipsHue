import logging
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils import record_audio
import warnings
import os
import time
import pygame
import platform
from threading import Thread
from phue import Bridge
from fuzzywuzzy import process
from transcribe import transcribe_audio
from chat import Chat
from dictate import dictate_text

warnings.filterwarnings("ignore", category=DeprecationWarning)


# Philips Hue Bridge connection
def initialize_hue_bridge():
    bridge_ip = os.getenv("HUE_BRIDGE_IP")
    global b
    b = Bridge(bridge_ip)
    b.connect()
    global lights
    global groups
    lights = b.get_light_objects('name')
    groups = b.get_group()


initial_prompt = """
You are an AI named Nova, and you act as a supportive, engaging, and
empathetic home assistant.
You can help with a variety of tasks, such as answering questions,
providing information, and helping with tasks.
Use tools that are available to you to help you answer questions and
provide information. You can also ask for help from a human if you need.

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
- Answer in the same language as the user's input.
"""

conversation_history = [
    {"role": "system", "content": initial_prompt}
]
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


# Ligth controls
def search_light(name: str):
    all_objects = b.lights + b.groups
    all_objects_names = {o.name: o for o in all_objects}
    light_score = process.extractOne(
        name.lower(),
        all_objects_names.keys(),
        score_cutoff=80)
    if not light_score:
        raise Exception(f"No light or group with the name {name}")
    else:
        logging.debug(f"{light_score[0] = }")
        return all_objects_names[light_score[0]]


def switch_on(name: str) -> None:
    light = search_light(name)
    logging.debug(f"{light = }")
    if light.on:
        logging.warning(f"The light {light} is already on")
    else:
        light.on = True
        logging.info(f"light {light.name} on")


def switch_off(name: str) -> None:
    light = search_light(name)
    logging.debug(f"{light = }")
    if not light.on:
        logging.warning(f"The light {light} is already off")
    else:
        light.on = False
        logging.info(f"light {light.name} off")


# tools
@tool
def switch_light_on(light_name: str):
    """use this tool when you need to switch on the lights
    given the name of one light, use this tool to switch on the light.
    To use the tool you must provide the light name 'light_name' """
    try:
        switch_on(light_name)
        return f"Switched on light {light_name}"
    except Exception as e:
        return str(e)


@tool
def switch_light_off(light_name: str):
    """use this tool when you need to switch off the lights
    given the name of one light, use this tool to switch off the light.
    To use the tool you must provide the light name 'light_name' """
    try:
        switch_off(light_name)
        return f"Switched off light {light_name}"
    except Exception as e:
        return str(e)


def initialize_chat():
    tools = [switch_light_on, switch_light_off]
    tools_description = "\n".join(
        [f"{i+1}. {t.name}: {t.description}" for i, t in enumerate(tools)])

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", initial_prompt),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    global chat
    chat = Chat(prompt=prompt)
    chat.initialize_agent(tools, tools_description)


def process_audio2():
    record_audio('test.wav')
    transcribe_audio("test.wav", "transcription.txt")
    with open("transcription.txt", "r") as file:
        transcription_text = file.read()
    print(transcription_text)
    response = chat(transcription_text)
    print("Respuesta: ", response)
    dictate_text(response)


if __name__ == "__main__":
    initialize_hue_bridge()
    initialize_chat()
    while True:
        try:
            thread = Thread(target=process_audio2)
            thread.start()
            thread.join()
        except KeyboardInterrupt:
            print("Interrupted by user")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
