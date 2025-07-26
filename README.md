# Hand MIDI Controller - Professional Edition

A high-performance, real-time hand tracking MIDI controller using MediaPipe and OpenCV. Transform your hand movements into MIDI control signals for music production, VJing, and creative performances.

## ✨ Features

### Core Functionality
- **Dual Hand Tracking**: Independent tracking of both hands with 6 parameters each
- **12 MIDI CC Outputs**: Organized in logical blocks (CC 1-6 left hand, CC 7-12 right hand)
- **Virtual MIDI Device**: Creates "HandMIDI Virtual" device for DAW integration
- **Zero Latency**: Optimized for real-time performance (30+ FPS)

### Advanced Features
- **Click-Drag Region Selection**: Define custom X/Y mapping bounds
- **Retina Display Optimization**: Crisp UI scaling for high-DPI displays
- **Professional UI**: Cyberpunk-styled overlay with real-time parameter visualization
- **Multi-Camera Support**: Cycle between available cameras with 'V' key
- **Smoothing Algorithms**: Exponential moving average for stable output

### Hand Parameters
#### Left Hand (CC 1-6)
1. **X-Axis** (CC 1): Horizontal hand position
2. **Y-Axis** (CC 2): Vertical hand position (inverted for natural control)
3. **Pinch** (CC 3): Thumb-index finger distance
4. **Palm** (CC 4): Hand openness/spread
5. **Rotation** (CC 5): Hand rotation angle
6. **Velocity** (CC 6): Hand movement speed

#### Right Hand (CC 7-12)
7. **X-Axis** (CC 7): Horizontal hand position
8. **Y-Axis** (CC 8): Vertical hand position (inverted for natural control)
9. **Pinch** (CC 9): Thumb-index finger distance
10. **Palm** (CC 10): Hand openness/spread
11. **Rotation** (CC 11): Hand rotation angle
12. **Distance** (CC 12): Distance between both hands

## get it running in 30 seconds

### option 1: automatic setup (recommended)
```bash
cd hand-midi-controller
./setup.sh   # installs everything
./run.sh     # runs it
```

### option 2: manual setup
```bash
# 1. create virtual environment (MUST be python 3.12 or lower)
python3.12 -m venv venv
source venv/bin/activate

# 2. install dependencies
pip install -r requirements.txt

# 3. run it
python hand_midi_controller_final.py
```

that's it. "hand midi controller" should appear in your daw's midi inputs.

## first time setup checklist

1. **check python version** - mediapipe needs 3.12 or lower:
   ```bash
   python3 --version  # if 3.13+, won't work
   python3.12 --version  # use this instead
   ```

2. **install python 3.12 if needed**:
   ```bash
   # macos
   brew install python@3.12
   
   # ubuntu/debian
   sudo apt install python3.12 python3.12-venv
   ```

3. **run the setup**:
   ```bash
   ./setup.sh  # handles everything automatically
   ```

4. **check your daw**:
   - open logic pro / ableton / your daw
   - create new midi track
   - set input to "hand midi controller"
   - load any synth
   - wave your hands!

## 🎮 Controls

| Key | Action |
|-----|--------|
| Q | Quit application |
| V | Cycle between cameras |
| F | Toggle fullscreen |
| O | Toggle overlay display |
| R | Reset region selection |
| Click+Drag | Select custom X/Y region |

## midi mappings

left hand:
- **cc01** - x position
- **cc02** - y position  
- **cc05** - thumb-index pinch
- **cc07** - palm openness
- **cc09** - hand rotation

right hand:
- **cc03** - x position
- **cc04** - y position
- **cc06** - thumb-index pinch
- **cc08** - palm openness  
- **cc10** - hand rotation

## ui modes

run with different modes:
```bash
python hand_midi_controller_final.py --ui minimal  # clean, labels only
python hand_midi_controller_final.py --ui cyberpunk # neon meters  
python hand_midi_controller_final.py --ui debug    # verbose info
```

## performance

if it's laggy:
- use minimal ui mode
- close other camera apps
- reduce smoothing in config
- use model_complexity=0 in config

## custom mapping areas

click and drag on the video to define a control zone. only hand movements in that area will generate midi 0-127. press `c` to clear.

## config

settings save to `hand_midi_config.json`. edit to:
- change cc numbers
- adjust sensitivity
- modify smoothing
- set camera resolution

## common issues & fixes

### "no module named cv2" or similar errors
you probably ran `python` instead of using the virtual environment:
```bash
./run.sh  # use this instead
# or
source venv/bin/activate
python hand_midi_controller_final.py
```

### "python 3.12 not found"
```bash
# check what you have
python3 --version

# install 3.12
brew install python@3.12        # macos
sudo apt install python3.12     # linux
```

### "no hands detected"
- better lighting helps (face a window)
- plain background works best  
- keep hands 1-3 feet from camera
- check camera permissions in system settings

### midi not showing in logic pro
1. quit logic pro completely
2. run the hand midi controller
3. reopen logic pro
4. check: track inspector → input → "hand midi controller"

### still stuck?
```bash
# clean install
rm -rf venv
./setup.sh
./run.sh
```

## advanced

### multiple cameras
press `v` to cycle through available cameras. the app will detect all connected cameras on startup.

### custom cc mappings
edit the cc_mappings in config:
```json
"cc_mappings": {
  "left_x": {"cc": 1, "label": "l_x_pos", "color": [0, 255, 255], "enabled": true}
}
```

### performance tuning
```json
"model_complexity": 0,          // 0=faster, 1=more accurate
"position_smoothing": 3,        // lower = more responsive
"skip_frames": 1,              // process every Nth frame
"camera_width": 640,           // lower resolution = faster
"camera_height": 480
```

---

## 🎨 TouchDesigner Integration

Want to turn your hand gestures into sick reactive visuals? Check out `TOUCHDESIGNER_INTEGRATION.md` for:

- Real-time hand-to-visual mapping
- Velocity-reactive particle systems  
- Distance-controlled camera movements
- Pinch-triggered effects and shaders
- Complete .toe project examples

**Hand tracking + TouchDesigner = absolute peak creative tech!** 🔥

---

made for musicians who like to wave their hands around