#!/usr/bin/env python3
import os
import time
import pyaudio
import wave
import threading
import tempfile
import keyboard
import pyperclip
import openai
import signal
import platform
from pynput.keyboard import Controller, Key, Listener
from dotenv import load_dotenv
import numpy as np

# Load environment variables from .env file
print("Loading environment variables...")
load_dotenv(verbose=True)

# Get OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print(f"API Key loaded: {OPENAI_API_KEY[:5]}..." if OPENAI_API_KEY else "No API key found!")

if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
    raise ValueError("OpenAI API key not found or using placeholder value. Please set it correctly in the .env file.")

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Audio recording parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

# Get max recording time from environment variables (default: 60 seconds)
try:
    MAX_RECORD_SECONDS = int(os.getenv("MAX_RECORD_SECONDS", "60"))
except:
    MAX_RECORD_SECONDS = 60
print(f"Максимальная длительность записи: {MAX_RECORD_SECONDS} секунд")

# Global variables
recording = False
keyboard_controller = Controller()
running = True
shift_pressed = False  # Track shift key state
space_pressed = False  # Track space key state
record_thread = None   # Reference to recording thread

def play_sound(frequency=440, duration=0.3, volume=0.5):
    """Play a simple tone to indicate events."""
    try:
        # This is a hacky way to play a simple sound without external libraries
        # It's not ideal but works for basic notification
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paFloat32,
                        channels=1,
                        rate=RATE,
                        output=True)
        
        # Generate a simple sine wave
        samples = (volume * np.sin(2 * np.pi * np.arange(RATE * duration) * frequency / RATE)).astype(np.float32)
        
        # Play the sound
        stream.write(samples.tobytes())
        
        # Close the stream
        stream.stop_stream()
        stream.close()
        p.terminate()
    except Exception as e:
        # Silently fail if sound can't be played
        print(f"Note: Sound notification not available ({e})")

def record_audio(file_path):
    """Record audio while keys are held down and save it to file_path."""
    global recording, shift_pressed, space_pressed
    
    audio = pyaudio.PyAudio()
    start_time = time.time()
    
    try:
        # Get default input device info
        default_device_index = audio.get_default_input_device_info()['index']
        print(f"Using default input device: {audio.get_device_info_by_index(default_device_index)['name']}")
    except Exception as e:
        print(f"Could not get default input device info: {e}")
        print("Available audio devices:")
        for i in range(audio.get_device_count()):
            try:
                device_info = audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:  # Only show input devices
                    print(f"  [{i}] {device_info['name']}")
            except Exception:
                pass
        default_device_index = None
    
    # Open audio stream
    try:
        stream = audio.open(format=FORMAT, channels=CHANNELS,
                          rate=RATE, input=True,
                          frames_per_buffer=CHUNK,
                          input_device_index=default_device_index)
    except Exception as e:
        print(f"Error opening audio stream: {e}")
        try:
            # Try again without specifying device
            stream = audio.open(format=FORMAT, channels=CHANNELS,
                              rate=RATE, input=True,
                              frames_per_buffer=CHUNK)
            print("Successfully opened audio stream with default device.")
        except Exception as e:
            print(f"Failed to open audio stream: {e}")
            audio.terminate()
            return False
    
    print("Recording... (hold Shift+Space to continue, release to stop)")
    recording = True
    
    # Play sound to indicate recording started
    play_sound(frequency=880, duration=0.2)  # Higher pitch for start
    
    frames = []
    try:
        # Continue recording while both shift and space are pressed
        while recording and shift_pressed and space_pressed:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
            # Update recording duration every second
            current_time = time.time()
            if int(current_time) > int(start_time) and (current_time - start_time) % 1 < 0.1:
                duration = int(current_time - start_time)
                print(f"Запись: {duration} сек...", end="\r", flush=True)
                
                # Check if we've reached the maximum recording time
                if duration >= MAX_RECORD_SECONDS:
                    print(f"\nДостигнута максимальная длительность записи ({MAX_RECORD_SECONDS} сек)")
                    break
                
            time.sleep(0.01)  # Small delay to prevent high CPU usage
        
        duration = time.time() - start_time
        print(f"\nЗапись завершена. Длительность: {duration:.2f} сек.")
        
        # Play sound to indicate recording stopped
        play_sound(frequency=440, duration=0.2)  # Lower pitch for stop
    except Exception as e:
        print(f"Error during recording: {e}")
        recording = False
        stream.stop_stream()
        stream.close()
        audio.terminate()
        return False
    
    recording = False
    
    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    audio.terminate()
    
    # Save the recorded audio as a WAV file
    try:
        with wave.open(file_path, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
        
        # Only return True if we actually recorded something
        if len(frames) > 0:
            return True
        else:
            print("No audio was recorded (recording time too short)")
            return False
    except Exception as e:
        print(f"Error saving audio file: {e}")
        return False

def stop_recording():
    """Stop ongoing recording."""
    global recording
    recording = False

def transcribe_audio(file_path):
    """Transcribe audio using OpenAI's Whisper API."""
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None

def insert_text(text):
    """Insert text at the current cursor position by simulating keystrokes."""
    if not text:
        return
    
    print("\n=== РЕЗУЛЬТАТ ТРАНСКРИПЦИИ ===")
    print(text)
    print("==============================\n")
    
    # Save transcription to file for backup
    transcript_file = os.path.expanduser("~/whisperflow_transcript.txt")
    try:
        with open(transcript_file, "w") as f:
            f.write(text)
        print(f"✓ Текст сохранен в файл: {transcript_file}")
    except Exception as e:
        print(f"✗ Не удалось сохранить текст в файл: {e}")
    
    print("Вставляю текст напрямую в активное окно...")
    
    # Give the user a moment to switch to the target window if needed
    time.sleep(0.5)
    
    # Предварительная обработка текста для правильного форматирования списков
    # Разбиваем текст по строкам
    lines = text.split('\n')
    formatted_lines = []
    
    # Определяем, является ли текст списком
    contains_list = False
    for line in lines:
        line = line.strip()
        if line and line[0].isdigit() and '. ' in line[:5]:
            contains_list = True
            break
    
    # Подготавливаем каждую строку
    in_list = False
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            # Пустые строки оставляем для разделения абзацев
            formatted_lines.append("")
            continue
            
        # Проверяем, является ли строка пунктом списка
        is_list_item = line and line[0].isdigit() and '. ' in line[:5]
        
        if is_list_item:
            in_list = True
            # Добавляем пункт списка с правильным форматированием
            formatted_lines.append(line)
        else:
            # Если это не пункт списка, просто добавляем строку
            if in_list and contains_list:
                # Если мы были в списке и строка не пункт, это конец списка
                in_list = False
            formatted_lines.append(line)
    
    # Используем только AppleScript на macOS для большей надежности
    if platform.system() == "Darwin":
        try:
            script_content = '''
            tell application "System Events"
                set activeApp to name of first application process whose frontmost is true
                tell process activeApp
            '''
            
            # Добавляем каждую строку в скрипт с правильной обработкой
            for i, line in enumerate(formatted_lines):
                if not line:
                    # Пустая строка - добавляем Shift+Enter
                    script_content += '''
                    key code 36 using shift down  # Shift+Enter
                    delay 0.1
                    '''
                    continue
                    
                # Проверяем, является ли строка пунктом списка
                is_list_item = line and line[0].isdigit() and '. ' in line[:5]
                
                # Экранируем кавычки для AppleScript
                escaped_line = line.replace('"', '\\"').replace('\\', '\\\\')
                
                # Если это первая строка или предыдущая строка пустая, не добавляем Shift+Enter перед
                if i > 0 and formatted_lines[i-1]:
                    # Если это пункт списка или предыдущая строка была пунктом списка, 
                    # добавляем Shift+Enter перед
                    prev_is_list_item = formatted_lines[i-1] and formatted_lines[i-1][0].isdigit() and '. ' in formatted_lines[i-1][:5]
                    if is_list_item or prev_is_list_item:
                        script_content += '''
                        key code 36 using shift down  # Shift+Enter
                        delay 0.1
                        '''
                
                # Вводим текст строки
                script_content += '''
                keystroke "''' + escaped_line + '''"
                delay 0.1
                '''
            
            script_content += '''
                end tell
            end tell
            '''
            
            # Выполняем скрипт
            os.system(f"osascript -e '{script_content}'")
            print("✓ Текст успешно введен через AppleScript")
            return
        except Exception as e:
            print(f"✗ Ошибка при использовании AppleScript: {e}")
    else:
        # Для Windows и Linux используем прямой ввод
        try:
            # Вводим текст с правильным форматированием
            for i, line in enumerate(formatted_lines):
                if not line:
                    # Пустая строка - добавляем Shift+Enter
                    keyboard_controller.press(Key.shift)
                    keyboard_controller.press(Key.enter)
                    keyboard_controller.release(Key.enter)
                    keyboard_controller.release(Key.shift)
                    time.sleep(0.1)
                    continue
                
                # Проверяем, является ли строка пунктом списка
                is_list_item = line and line[0].isdigit() and '. ' in line[:5]
                
                # Если это первая строка или предыдущая строка пустая, не добавляем Shift+Enter перед
                if i > 0 and formatted_lines[i-1]:
                    # Если это пункт списка или предыдущая строка была пунктом списка, 
                    # добавляем Shift+Enter перед
                    prev_is_list_item = formatted_lines[i-1] and formatted_lines[i-1][0].isdigit() and '. ' in formatted_lines[i-1][:5]
                    if is_list_item or prev_is_list_item:
                        keyboard_controller.press(Key.shift)
                        keyboard_controller.press(Key.enter)
                        keyboard_controller.release(Key.enter)
                        keyboard_controller.release(Key.shift)
                        time.sleep(0.1)
                
                # Вводим текст строки
                keyboard_controller.type(line)
                time.sleep(0.1)
            
            print("✓ Текст успешно введен")
            return
        except Exception as e:
            print(f"✗ Ошибка при вводе текста: {e}")
    
    print("\n=== ИНСТРУКЦИИ ПО ВСТАВКЕ ===")
    print("Не удалось автоматически вставить текст. Вы можете:")
    print(f"1. Скопировать текст из консоли: \"{text}\"")
    print(f"2. Использовать файл с текстом: {transcript_file}")

def process_with_gpt(text):
    """Process the transcribed text through GPT-4o to improve style and structure."""
    if not text or len(text.strip()) == 0:
        return text
    
    print("\n=== ОБРАБОТКА ТЕКСТА ЧЕРЕЗ GPT-4o ===")
    print(f"Исходный текст: \"{text}\"")
    print("Отправляю на обработку...")
    
    try:
        # Составляем промпт для GPT-4o
        prompt = f"""
        Ты ассистент, который улучшает транскрибированный текст. 
        Вот текст, полученный с аудиозаписи: 

        "{text}"

        Пожалуйста, улучши этот текст:
        1. Исправь стилистические ошибки
        2. Улучши структуру текста
        3. Сделай формулировки более четкими и профессиональными
        4. Если нужно, оформи как список с пунктами
        5. Сохрани смысл и ключевые моменты оригинала
        6. Если текст содержит вопрос, оставь его как вопрос

        Верни только улучшенный текст без объяснений или комментариев.
        """
        
        # Отправляем запрос к OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",  # Используем GPT-4o
            messages=[
                {"role": "system", "content": "Ты ассистент, который улучшает стиль и структуру текста, сохраняя его основной смысл."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,  # Низкая температура для более консервативных изменений
        )
        
        # Получаем обработанный текст
        improved_text = response.choices[0].message.content.strip()
        
        print("\n=== РЕЗУЛЬТАТ ОБРАБОТКИ GPT-4o ===")
        print(improved_text)
        print("====================================")
        
        return improved_text
        
    except Exception as e:
        print(f"Ошибка при обработке текста через GPT-4o: {e}")
        print("Возвращаю оригинальный текст...")
        return text

def on_hotkey_pressed():
    """Function to execute when the hotkey is pressed."""
    global record_thread
    
    # Create a temporary file for the audio recording with unique identifier
    temp_filename = os.path.join(tempfile.gettempdir(), f"whisperflow_{int(time.time())}.wav")
    
    # Store the filename in a variable accessible to the release function
    os.environ['WHISPERFLOW_TEMP_FILE'] = temp_filename
    
    # Start recording in a separate thread
    record_thread = threading.Thread(target=record_audio, args=(temp_filename,))
    record_thread.start()

def on_hotkey_released():
    """Function to execute when the hotkey is released."""
    global record_thread
    
    if record_thread is None:
        return
    
    # Wait for the recording thread to finish
    record_thread.join()
    record_thread = None
    
    # Get the temporary file name from environment variable
    temp_filename = os.environ.get('WHISPERFLOW_TEMP_FILE')
    if not temp_filename:
        print("Не удалось найти временный файл")
        return
    
    # Check if recording was successful
    if not os.path.exists(temp_filename) or os.path.getsize(temp_filename) == 0:
        print("Запись не удалась или была прервана")
        try:
            os.unlink(temp_filename)
        except:
            pass
        return
    
    print(f"Аудио сохранено во временный файл: {temp_filename}")
    
    # Transcribe the audio
    print("Транскрибирую аудио...")
    transcribed_text = transcribe_audio(temp_filename)
    
    if transcribed_text:
        print(f"Транскрипция: {transcribed_text}")
        
        # Process the transcribed text through GPT-4o
        improved_text = process_with_gpt(transcribed_text)
        
        # Insert the improved text
        insert_text(improved_text)
        
        print("Совет: Если текст не вставляется, убедитесь что:")
        print("  - Ваш курсор находится в текстовом поле")
        print("  - Приложение разрешает ввод текста")
        print("  - Вы предоставили разрешения для мониторинга клавиатуры")
    else:
        print("Транскрипция не удалась")
    
    # Clean up the temporary file
    try:
        os.unlink(temp_filename)
        # Clear the environment variable
        os.environ['WHISPERFLOW_TEMP_FILE'] = ""
    except Exception as e:
        print(f"Ошибка при удалении временного файла: {e}")

def on_press(key):
    """Handle key press events."""
    global recording, shift_pressed, space_pressed
    
    try:
        # Check if Shift key is pressed
        if key == Key.shift:
            shift_pressed = True
            # Check if both keys are pressed to start recording
            if space_pressed and not recording:
                on_hotkey_pressed()
            # We don't return False here to allow the listener to continue
        
        # Check if Space is pressed
        elif key == Key.space:
            space_pressed = True
            # Check if both keys are pressed to start recording
            if shift_pressed:  # If Shift is already pressed
                if not recording:
                    on_hotkey_pressed()
                # We suppress the space keypress by using keyboard_controller to backspace
                # This is more reliable than trying to block the event
                try:
                    # Small delay to let the space be registered, then remove it
                    threading.Timer(0.01, lambda: keyboard_controller.press(Key.backspace) and keyboard_controller.release(Key.backspace)).start()
                except:
                    pass  # If we can't do this, just continue
            
        # Check if Escape is pressed and we are recording
        elif key == Key.esc and recording:
            print("Остановка записи по нажатию Esc...")
            stop_recording()
            # Process the recording like if keys were released
            if recording:
                on_hotkey_released()
        
        # Stop the listener if we need to exit
        if not running:
            return False
            
    except Exception as e:
        print(f"Ошибка при обработке нажатия клавиши: {e}")
    
    # We always return True to keep the listener running
    return True

def on_release(key):
    """Handle key release events."""
    global shift_pressed, space_pressed, recording
    
    try:
        # Track when Shift key is released
        if key == Key.shift:
            shift_pressed = False
            # If recording was ongoing, stop it
            if recording:
                stop_recording()
                on_hotkey_released()
        
        # Track when Space key is released
        elif key == Key.space:
            space_pressed = False
            # If recording was ongoing, stop it
            if recording:
                stop_recording()
                on_hotkey_released()
        
        # Stop the listener if we need to exit
        if not running:
            return False
            
    except Exception as e:
        print(f"Ошибка при обработке отпускания клавиши: {e}")
    
    # We always return True to keep the listener running
    return True

def signal_handler(sig, frame):
    """Handle interrupt signals."""
    global running
    print("\nExiting WhisperFlow")
    running = False
    stop_recording()

def main():
    global running
    
    print("\n" + "="*50)
    print("WhisperFlow - Транскрипция голоса в текст")
    print("="*50)
    print("ИНСТРУКЦИЯ:")
    print("1. НАЖМИТЕ И УДЕРЖИВАЙТЕ Shift+Пробел, чтобы начать запись")
    print("2. Говорите в микрофон, пока держите клавиши нажатыми")
    print("3. ОТПУСТИТЕ Shift+Пробел, чтобы завершить запись и транскрибировать")
    print("4. Текст будет вставлен в позицию курсора")
    print("5. Нажмите Ctrl+C, чтобы выйти из программы")
    
    # Display macOS-specific instructions if needed
    if platform.system() == "Darwin":  # macOS
        print("\nВАЖНО: На macOS нужно предоставить разрешения доступа")
        print("Если вы видите ошибку 'This process is not trusted!', пожалуйста:")
        print("1. Перейдите в Системные настройки > Защита и безопасность > Конфиденциальность > Универсальный доступ")
        print("2. Нажмите на значок замка, чтобы внести изменения")
        print("3. Добавьте Терминал или вашу IDE в список разрешенных приложений")
        print("4. Перезапустите программу после предоставления разрешений\n")
    
    # Register the signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create keyboard listener
    listener = Listener(on_press=on_press, on_release=on_release)
    listener.start()
    
    print("WhisperFlow запущен! Ожидаю нажатия Shift+Пробел...\n")
    
    # Keep the program running
    try:
        while running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        running = False
    finally:
        # Cleanup
        running = False
        listener.stop()

if __name__ == "__main__":
    main()
 