import sys
sys.path.append(r"C:\Users\Hp\Downloads\GlobalSpeak-main\GlobalSpeak-main\env\Lib\site-packages")


import threading

import os
from flask import Flask, render_template, request, jsonify, redirect
from moviepy.editor import *
from pydub import AudioSegment
from pydub.silence import split_on_silence

import speech_recognition as sr
from googletrans import Translator
from gtts import gTTS

import json


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

languages = {
    "afrikaans": "af", "albanian": "sq", "amharic": "am", "arabic": "ar", "armenian": "hy", "azerbaijani": "az",
    "basque": "eu", "belarusian": "be", "bengali": "bn", "bosnian": "bs", "bulgarian": "bg",
    "catalan": "ca", "cebuano": "ceb", "chichewa": "ny", "chinese (simplified)": "zh-cn", "chinese (traditional)": "zh-tw",
    "corsican": "co", "croatian": "hr", "czech": "cs", "danish": "da", "dutch": "nl",
    "english": "en", "esperanto": "eo", "estonian": "et", "filipino": "tl", "finnish": "fi",
    "french": "fr", "frisian": "fy", "galician": "gl", "georgian": "ka", "german": "de",
    "greek": "el", "gujarati": "gu", "haitian creole": "ht", "hausa": "ha", "hawaiian": "haw",
    "hebrew": "he", "hindi": "hi", "hmong": "hmn", "hungarian": "hu", "icelandic": "is",
    "igbo": "ig", "indonesian": "id", "irish": "ga", "italian": "it", "japanese": "ja",
    "javanese": "jw", "kannada": "kn", "kazakh": "kk", "khmer": "km", "korean": "ko",
    "kurdish (kurmanji)": "ku", "kyrgyz": "ky", "lao": "lo", "latin": "la", "latvian": "lv",
    "lithuanian": "lt", "luxembourgish": "lb", "macedonian": "mk", "malagasy": "mg", "malay": "ms",
    "malayalam": "ml", "maltese": "mt", "maori": "mi", "marathi": "mr", "mongolian": "mn",
    "myanmar (burmese)": "my", "nepali": "ne", "norwegian": "no", "odia": "or", "pashto": "ps",
    "persian": "fa", "polish": "pl", "portuguese": "pt", "punjabi": "pa", "romanian": "ro",
    "russian": "ru", "samoan": "sm", "scots gaelic": "gd", "serbian": "sr", "sesotho": "st",
    "shona": "sn", "sindhi": "sd", "sinhala": "si", "slovak": "sk", "slovenian": "sl",
    "somali": "so", "spanish": "es", "sundanese": "su", "swahili": "sw", "swedish": "sv",
    "tajik": "tg", "tamil": "ta", "telugu": "te", "thai": "th", "turkish": "tr",
    "ukrainian": "uk", "urdu": "ur", "uyghur": "ug", "uzbek": "uz", "vietnamese": "vi",
    "welsh": "cy", "xhosa": "xh", "yiddish": "yi", "yoruba": "yo", "zulu": "zu"
}

@app.route('/text_translate', methods=['GET', 'POST'])
def translate_text():
    """ Translate text from source language to target language

    Keyword arguments:
    Return: translated text in .json format which is later fetched by connector.js
    """
    print("inside translate_text")
    text = request.form.get('user_text')
    target = request.form.get('target_language')

    print(text, target)
    unicodeData = text_translator(text, target)
    data = {'text': unicodeData}
    encodedUnicode = json.dumps(data, ensure_ascii=False)
    return encodedUnicode

@app.route('/audio_translate', methods=['GET', 'POST'])
def audio_transcript():
    """ Return translated audio from source language to target language
        and generate audio file as well as text file

    Returns:
        dict: dictionary containing translated text in json format. 
        This is later fetched by connector.js
    """
    print("inside audio_transcript")
    target = request.form.get('target_language')
    if "file" not in request.files:
        print("No file 1")
        return redirect(request.url)

    file = request.files["file"]
    if file.filename == "":
        print("No file")
        return redirect(request.url)

    target = languages[target].lower()
    print(file, target)
    transcript = ""
    if file:
        print("transcription")
        recognizer = sr.Recognizer()
        audioFile = sr.AudioFile(file)
        with audioFile as source:
            data = recognizer.record(source)
        transcript = recognizer.recognize_google(data, key=None)
    print(transcript)
    ans = text_translator(transcript, target)
    audio_translator(ans, target)
    print('printing ans')
    data = {'text': ans}
    encodedUnicode = json.dumps(data, ensure_ascii=False)
    return encodedUnicode

@app.route('/video_translate', methods=['GET', 'POST'])
def translate_video():
    print("inside video_transcript")
    target = request.form.get('target_language')
    if "file" not in request.files:
        print("No file 1")
        return redirect(request.url)

    file = request.files["file"]
    if file.filename == "":
        print("No file")
        return redirect(request.url)

    target = languages[target].lower()
    print(file, target)
    file.save(r'static/audio_from_video/original.mp4')
    print("file saved")
    videoclip = VideoFileClip(r'static/audio_from_video/original.mp4')
    videoclip.audio.write_audiofile(r"static/audio_from_video/audio.wav", codec='pcm_s16le')
    print("audio extracted")
    video_translator(r'static/audio_from_video/audio.wav', target, videoclip)
    return {'text': 'success'}



def video_translator(file, target, videoclip):
    """Translate video by extracting audio, translating, and creating a new video."""
    transcript = ""
    recognizer = sr.Recognizer()
    
    # Break the audio into chunks
    with sr.AudioFile(file) as source:
        duration = int(source.DURATION)
        chunk_size = 30  # Process audio in 30-second chunks
        chunks = [(i, min(i + chunk_size, duration)) for i in range(0, duration, chunk_size)]
    
    def process_chunk(start, end, results):
        """Transcribe a chunk of audio."""
        with sr.AudioFile(file) as source:
            audio_chunk = recognizer.record(source, offset=start, duration=(end - start))
        try:
            chunk_transcript = recognizer.recognize_google(audio_chunk)
            results.append(chunk_transcript)
        except sr.UnknownValueError:
            results.append("")

    threads = []
    results = []
    
    # Create threads for chunk processing
    for start, end in chunks:
        thread = threading.Thread(target=process_chunk, args=(start, end, results))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Join the transcript parts
    transcript = " ".join(results)
    
    translated_text = text_translator(transcript, target)
    
    # Generate translated audio
    translated_audio = gTTS(text=translated_text, lang=target, slow=False)
    translated_audio.save(r'static/audio_from_video/translated_audio.wav')
    
    audioclip = AudioFileClip(r'static/audio_from_video/translated_audio.wav')

    # Adding audio to the video clip
    new_audioclip = CompositeAudioClip([audioclip])
    videoclip.audio = new_audioclip
    videoclip.write_videofile(r"static/audio_from_video/translated_video.mp4", codec="libx264", audio_codec="aac")


def audio_translator(text, target):
    print("inside audio translate")
    """ Translate audio from source language to target language

    Args:
        text (str): transcription of audio file in source language
        target (str): target language for translation

    Returns (none): It generates audio file in target language and stores it locally
    """
    try:
        speak = gTTS(text=text, lang=target, slow=False)
        speak.save(r"static/translated_audio/captured_voice.mp3")
    except Exception as e:
        print(f"Error in audio translation: {e}")

def text_translator(text, target):
    """Translate given text to target language

    Args:
        text (str): text to be translated
        target (str): target language

    Returns:
        str: translated text
    """
    print(target)
    translator = Translator()
    translation = translator.translate(text, dest=target)
    translated_text = translation.text
    print(target)
    print(translation.text)
    return translated_text

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)
