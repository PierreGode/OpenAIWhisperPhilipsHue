# OpenAIWhisperPhilipsHue
Voice GPT4o OpenAIWhisperPhilipsHue

[![CodeQL](https://github.com/PierreGode/OpenAIWhisperPhilipsHue/actions/workflows/codeql.yml/badge.svg)](https://github.com/PierreGode/OpenAIWhisperPhilipsHue/actions/workflows/codeql.yml)

Work in Progress

Clone repo to Windows machine
```
  git clone https://github.com/PierreGode/OpenAIWhisperPhilipsHue.git
```
```
cd OpenAIWhisperPhilipsHue
```
```
pip install -r requirements.txt
```
Set API key in Enviroment
``` 

$env:OPENAI_API_KEY="sk-proj-"

$env:OPENAI_API_KEY="sk-"
$env:HUE_BRIDGE_IP="192.168.0.XX"
$env:MODEL="gpt-3.5-turbo"
$env:WHISPER_MODEL="whisper-1"

```

# Set preferred language for fallback on line 40
```
preferred_language = 'en'  # Change this to 'en' or any other supported lang
```

# Execution

```
python openaiwhisperphilipshue\nova_assistant.py
```
