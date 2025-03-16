# WhisperFlow

WhisperFlow is a utility that allows you to transcribe speech to text using OpenAI's Whisper model and insert it at your cursor position.

## Features

- Global hotkey (Shift+Space) to start recording audio from anywhere in your system
- Audio transcription using OpenAI's Whisper API
- Automatic insertion of transcribed text at your current cursor position
- Escape key to stop recording early

## Prerequisites

- Python 3.6 or higher
- An OpenAI API key
- macOS accessibility permissions for keyboard monitoring

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/whisper-flow.git
   cd whisper-flow
   ```

2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   Note: If you have issues with PyAudio on macOS, you may need to install PortAudio first:
   ```bash
   brew install portaudio
   ```

   Then install PyAudio directly:
   ```bash
   pip install pyaudio
   ```

4. Create a `.env` file with your OpenAI API key:
   ```bash
   cp .env.example .env
   ```
   Then edit the `.env` file to replace `your_openai_api_key_here` with your actual OpenAI API key.

## Usage

1. Run the WhisperFlow script with the virtual environment activated:
   ```bash
   source venv/bin/activate
   python whisper-flow.py
   ```

2. Press Shift+Space to start recording audio (default recording duration is 5 seconds)
3. Speak clearly into your microphone
4. Recording will automatically stop after the preset duration (or press Esc to stop early)
5. Wait for the transcription to complete
6. The transcribed text will be automatically inserted at your current cursor position

## macOS Permissions

On macOS, you need to grant accessibility permissions for keyboard monitoring:

1. Go to System Preferences > Security & Privacy > Privacy > Accessibility
2. Click the lock icon in the bottom left to make changes
3. Add your Terminal app or the app you're running the script from to the list of allowed applications
4. You may need to restart your Terminal or application after granting permissions

If you see the error message "This process is not trusted! Input event monitoring will not be possible until it is added to accessibility clients," follow the steps above to grant permissions.

## Troubleshooting

### API Key Issues

If you see errors related to the API key:
1. Make sure your `.env` file contains your actual OpenAI API key and not the placeholder text
2. The key should be in the format: `OPENAI_API_KEY=sk-...`
3. Ensure the API key is valid and has access to the Whisper API

### Keyboard Monitoring Issues

If hotkeys aren't working:
1. Make sure you've granted accessibility permissions (for macOS)
2. Try running the application with administrator privileges
3. Restart your terminal or IDE after granting permissions

### Audio Recording Issues

If audio recording isn't working:
1. Check if your microphone is properly connected and not muted
2. Try selecting a different audio input device
3. Ensure no other application is using the microphone

## Customization

You can modify the following parameters in the script:

- `RECORD_SECONDS`: Default recording duration in seconds (default: 5)
- Recording audio parameters (FORMAT, CHANNELS, RATE, CHUNK)

## License

MIT

## Note on Dependencies

You may need to install PortAudio to use PyAudio:

### macOS
```bash
brew install portaudio
```

### Linux (Debian/Ubuntu)
```bash
sudo apt-get install portaudio19-dev
```

### Windows
PyAudio wheels are available for Windows, so it should install without additional dependencies. 