# Space Game

Ein innovatives Weltraumspiel mit Handgestenerkennung und KI-gesteuerten Gegnern.

## Projektbeschreibung

Dieses Projekt ist ein interaktives Weltraumspiel, das moderne Technologien auf einzigartige Weise kombiniert:

- **Handgestenerkennung**: Steuere dein Raumschiff durch intuitive Handbewegungen
- **KI-Gegner**: Tritt gegen einen mit Reinforcement Learning trainierten KI-Gegner an
- **Echtzeit-Interaktion**: Dynamisches Spielerlebnis mit sofortiger Reaktion auf deine Bewegungen

## Technische Highlights

- Implementierung von Computer Vision für die Handgestenerkennung
- Integration von Reinforcement Learning für KI-Gegner
- Echtzeit-Spielmechanik mit präziser Steuerung

## Systemvoraussetzungen

- Python 3.8 oder höher
- Webcam für die Handgestenerkennung
- Mindestens 4GB RAM
- GPU wird für optimale Leistung empfohlen

## Installation

1. Repository klonen:
   ```
   git clone https://github.com/username/space-game.git
   cd space-game
   ```

2. Virtuelle Umgebung erstellen und aktivieren (empfohlen):
   ```
   python -m venv venv
   
   # Unter Windows:
   venv\Scripts\activate
   
   # Unter macOS/Linux:
   source venv/bin/activate
   ```

3. Abhängigkeiten installieren:
   ```
   pip install -r requirements.txt
   ```

## Verwendung

1. Einzelspieler-Modus mit Handgestenerkennung starten:
   ```
   python single_player_camera_control.py
   ```

2. Zweispieler-Modus mit Handgestenerkennung starten:
   ```
   python 2_player_camera_control.py
   ```

3. Spiel gegen KI-Gegner starten:
   ```
   python play_trained_agent.py
   ```

4. Eigenen KI-Agenten trainieren:
   ```
   python train_agent.py
   ```

## Steuerung

- **Handgestenerkennung**: Zeige deine offene Hand in die Kamera, um dein Raumschiff zu steuern
- **Bewegung**: Bewege deine Hand in die Richtung, in die sich dein Raumschiff bewegen soll
- **Schießen**: Schließe deine Hand zur Faust, um zu schießen

## Screenshots

![Spielansicht 1](https://github.com/user-attachments/assets/dbe4abf4-5a49-4b9c-99e7-39613f4cfbcb)

![Spielansicht 2](https://github.com/user-attachments/assets/cf2b5453-7bc7-4d67-b7ef-3c292bff5084)

## Fehlerbehebung

Sollten Probleme mit der Handgestenerkennung auftreten:
- Stelle sicher, dass deine Webcam korrekt angeschlossen ist
- Verbessere die Beleuchtung in deinem Raum
- Halte deine Hand deutlich sichtbar vor die Kamera

## Lizenz

MIT-Lizenz - Siehe LICENSE-Datei für Details.
