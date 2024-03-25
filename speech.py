import speech_recognition as sr
import langid


def recognize_speech(audio_file, language="en-US"):
    recognizer = sr.Recognizer()
    audio_file = sr.AudioFile(audio_file)

    try:
        with audio_file as source:
            audio_data = recognizer.record(source)
            detected_language = langid.classify(recognizer.recognize_google(audio_data, language=language))[0]
            if detected_language != language[:2].lower():
                return None
            transcript = recognizer.recognize_google(audio_data, language=language)
            return transcript
    except sr.UnknownValueError:
        return None
