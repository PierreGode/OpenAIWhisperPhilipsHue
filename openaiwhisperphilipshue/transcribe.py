import os
import argparse
from openai import OpenAI


client = OpenAI()


def transcribe_audio_to_english(file_path: str, output_file_path: str):
    with open(file_path, "rb") as audio_file:
        translation = client.audio.translations.create(
            model=os.getenv("WHISPER_MODEL", "whisper-1"),
            file=audio_file
        )
        print(f"{translation.text = }")
    with open(output_file_path, "w") as output_file:
        output_file.write(translation.text)


def transcribe_audio(file_path: str, output_file_path: str):
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model=os.getenv("WHISPER_MODEL", "whisper-1"),
            file=audio_file
        )
        print(f"{transcription.text = }")
    with open(output_file_path, "w") as output_file:
        output_file.write(transcription.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio to English")
    parser.add_argument("input_audio_file_path",
                        type=str, help="The path to the input audio file")
    parser.add_argument("output_file_path",
                        type=str, help="The path to the output file")
    args = parser.parse_args()
    transcribe_audio_to_english(
        args.input_audio_file_path,
        args.output_file_path)
