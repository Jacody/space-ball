# Space Game

An innovative space game that combines hand gesture control with AI-powered opponents.

## Project Description

This project is an interactive space game that uniquely combines modern technologies:

- **Hand Gesture Control**: Control your spaceship through intuitive hand movements
- **AI Opponent**: Compete against a reinforcement learning-trained AI opponent
- **Real-time Interaction**: Dynamic gameplay with immediate response to your movements

## Technical Highlights

- Implementation of Computer Vision for hand gesture recognition
- Integration of Reinforcement Learning for AI opponents
- Real-time game mechanics with precise controls

<img src="https://github.com/user-attachments/assets/dbe4abf4-5a49-4b9c-99e7-39613f4cfbcb" alt="Game View 1" width="400">

<img src="https://github.com/user-attachments/assets/cf2b5453-7bc7-4d67-b7ef-3c292bff5084" alt="Game View 2" width="400">

## System Requirements

- Python 3.8 or higher
- Webcam for hand gesture recognition
- Minimum 4GB RAM
- GPU recommended for optimal performance

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/username/space-game.git
   cd space-game
   ```

2. Create and activate a virtual environment (recommended):
   ```
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Start single-player mode with hand gesture control:
   ```
   python single_player_camera_control.py
   ```

2. Start two-player mode with hand gesture control:
   ```
   python 2_player_camera_control.py
   ```

3. Play against an AI opponent:
   ```
   python play_trained_agent.py
   ```

4. Train your own AI agent:
   ```
   python train_agent.py
   ```

## Controls

- **Rotation**: Show your open hand to the camera to rotate the spaceship
- **Forward Movement**: Make a fist to propel your spaceship forward
- **Direction Control**: The position of your hand determines the direction of movement

## License

MIT License - See LICENSE file for details.
