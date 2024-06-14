from setuptools import setup, find_packages

setup(
    name="OpenAIWhisperPhilipsHue",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "openai",
        "pygame",
        "PyAudio",
        "phue",
        "fuzzywuzzy",
        "langdetect",
        "setuptools",
        "SpeechRecognition",
        "python-Levenshtein"
    ],
    entry_points={
        "console_scripts": [
            "openaiwhisperphilipshue=openaiwhisperphilipshue.main:main",
        ],
    },
    author="PierreGode",
    description="Control Philips Hue lights with voice commands using OpenAI Whisper and GPT-4",
    url="https://github.com/PierreGode/OpenAIWhisperPhilipsHue",
)
