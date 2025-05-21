## ImproTron

ImproTron is Light and Sound software for managing multiple screens, lights, and audio playback, designed primarily for ComedySportz (R) and other Improv Shows. It provides a comprehensive suite of tools to enhance live improvisational performances.

## Features
The application assumes the theater has Windows running with two additional monitors. The applications features are:
* Ability to display a scoreboard for two teams. The color and team names are configured and remembered across sessions. There are shortcut buttons to add common score updates.
* Countdown Timer: A countdown timer can be displayed at any time. A time at which the timer turns red can be set. The timer will continue to countdown when hidden.
* Two text windows whose content can be sent to either monitor. Text can be loaded from storage. The color and font can be sent to either monitor.
* Push images to either monitor. The app provides a basic search capability based on indexing the file name and file extension.
* Copy images from a browser and paste them to either monitor.
* Drag and drop images from browser pages or a file manager.
* Slide Show creation and management. Lists of images can be created by searching or navigating via a file tree. Slide Shows can be used for random selection. Supports images, animations, and movies.
* Promo Mode: Uses a directory as the source of content for a slide show. This enables a directory to be sync-ed with a cloud service like DropBox to provide remote management of content. If enabled, the slides will auto-start when the application starts.
* Playing sounds. Audio file searching is built on the same technique as image searching. In addition, WAV files can be stored as sound effect palettes. Multiple WAV files can be played simultaneously via the SoundFX features.
* Thingz: List management for a ComedySportz (R) specialty game. Support games with and without substitutions.
* Webcam integration: A webcam feed can be sent to either monitor or
* Video File player: Supports multiple video formats. Includes playing the sound.
* YouTube Playback: An embedded player can play sound and video provided the content producer enables it.
* Hotbuttons: Images can be associated with 10 buttons which will push the image immediately to the main monitor with a left click and auxiliary monitor with a right click.
* Game Slide Builder: A simple frame can be combined with a database of games to produce slides for each game. Includes a whammy function. Frames can be any of the image formats supported.
* Integration with [Touch Portal](https://www.touch-portal.com/), which is a remote macro control deck for Android, iPads, and iPhones. The server runs on the same PC as ImproTron. This enables remote control of ImproTron. Any button can be pressed, any file displayed and any sound played. Touch Panel Panel can also integrate with Spotify, OBS, and other applications.

## Installation

1.  **Prerequisites:**
    *   Ensure you have Python installed (version 3.x recommended). You can download it from [python.org](https://www.python.org/).
    *   This application uses PySide6.

2.  **Get the Code:**
    *   Clone this repository or download the source code.

3.  **Install Dependencies:**
    *   Open a terminal or command prompt in the project's root directory.
    *   Install PySide6 and TinyDB by running:
        ```bash
        pip install PySide6 tinydb
        ```

4.  **Running the Application (from source):**
    *   Once dependencies are installed, you can run ImproTron from the source code:
        ```bash
        python main.py
        ```

5.  **(Optional) Building a Standalone Executable:**
    *   The `main.py` file contains comments with commands that can be used to build a standalone executable using `pyside6-deploy` and related tools. This typically involves steps like:
        ```bash
        # First, ensure PySide6 development tools are installed
        # pip install pyside6-tools 
        # (or it might be part of the main PySide6 install)

        # Activate your virtual environment if you're using one
        # e.g., venv\Scripts\activate.bat (Windows) or source venv/bin/activate (Linux/macOS)

        # Compile resources and UI files (paths might need adjustment)
        # pyside6-rcc ImproTronIcons.qrc > ImproTronIcons.py 
        # pyside6-uic ImproTronControlBoard.ui -o ui_ImproTronControlBoard.py
        # pyside6-uic ImproTron.ui -o ui_ImproTron.py
        
        # Deploy the application using the spec file
        # pyside6-deploy ImproTron.spec 
        ```
    *   Refer to the comments in `main.py` and the [PySide6 documentation](https://doc.qt.io/qtforpython/deployment/index.html) for more details on deployment.

## Usage

To run ImproTron after installation, navigate to the project's root directory in your terminal or command prompt and execute:

```bash
python main.py
```

For detailed information on all features and how to use them, please refer to the "ImproTron User Guide.pdf". This guide is typically available on the [project's GitHub releases page](https://github.com/guywinterbotham/ImproTron/releases) or alongside the application if you have a built version.

## Dependencies

*   **Python 3.x**
*   **PySide6:** This is the core GUI framework used by ImproTron.
*   **TinyDB:** Used for database functionalities (e.g., media file indexing).

These should be installed during the [Installation](#installation) process.

### Related Software

*   **TouchPortal:** For remote control functionality, ImproTron integrates with TouchPortal. You will need to have the TouchPortal server running on the same PC as ImproTron and the TouchPortal app on your control device (Android/iOS). You can find more information at [touch-portal.com](https://www.touch-portal.com/).

## License

This project is licensed under the GNU General Public License Version 2. See the `LICENSE` file for the full license text.

## Contributing

Contributions are welcome! If you have suggestions for improvements or bug fixes, please feel free to:
1.  Open an issue to discuss the change.
2.  Fork the repository and submit a pull request with your changes.
