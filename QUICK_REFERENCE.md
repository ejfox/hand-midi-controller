# Quick Reference Card

## 🎹 Keyboard Shortcuts

### Presets (Number Keys)
```
1  →  Performance    (live, high sensitivity, all gestures)
2  →  Studio         (recording, balanced, smooth)
3  →  Precise        (14-bit, maximum precision)
4  →  Experimental   (all features enabled)
5  →  Minimal        (basic controls only)
```

### Real-Time Adjustments
```
+/-  →  Position Smoothing      (hand X/Y position)
[/]  →  Gesture Smoothing       (pinch, palm, rotation)
{/}  →  Pinch Sensitivity       (open threshold)
```

### General Controls
```
Q  →  Quit
M  →  Cycle UI modes (minimal/cyberpunk/debug)
V  →  Switch cameras
S  →  Save config
C  →  Clear custom area
```

---

## 🎛️ MIDI CC Quick Map

### Always Active (Basic Controls)
```
Left Hand               Right Hand
CC1  - X Position       CC3  - X Position
CC2  - Y Position       CC4  - Y Position
CC5  - Pinch            CC6  - Pinch
CC7  - Palm Open        CC8  - Palm Open
CC9  - Rotation         CC10 - Rotation
```

### Advanced (Enable in Presets)
```
Left Hand               Right Hand
CC11 - Thumb-Middle     CC12 - Thumb-Middle
CC13 - Thumb-Ring       CC14 - Thumb-Ring
CC15 - Thumb-Pinky      CC16 - Thumb-Pinky
CC17 - Fist             CC18 - Fist
CC19 - Spread           CC20 - Spread
CC21 - Velocity         CC22 - Velocity

Both Hands
CC23 - Hand Distance
```

---

## 🎯 When to Use Each Preset

**Performance (1)** - Live shows, jamming, VJing
- Fast response, all gestures active
- Best for: Electronic music, reactive visuals

**Studio (2)** - Recording, automation, production
- Stable output, balanced smoothing
- Best for: DAW work, precise recording

**Precise (3)** - Sound design, slow movements
- Ultra-smooth, 14-bit resolution
- Best for: Parameter automation, modulation

**Experimental (4)** - Learning, exploring
- Everything enabled, full debug info
- Best for: Finding your workflow

**Minimal (5)** - Simple setups, first use
- X/Y + Pinch only
- Best for: Getting started, low CPU

---

## 💡 Quick Tips

### Getting Started
1. Press **1** for Performance preset
2. Wave hands, observe MIDI values
3. Adjust smoothing with **+/-** if needed
4. Press **S** to save your settings

### For Smooth Output
- Increase smoothing: **+** and **]**
- Good lighting helps tracking
- Use custom area (click-drag)

### For Responsive Control
- Decrease smoothing: **-** and **[**
- Performance preset (key **1**)
- Keep hands steady

### Troubleshooting
- Jittery → Increase smoothing (**+** **]**)
- Laggy → Decrease smoothing (**-** **[**)
- Pinch issues → Adjust with **{** **}**

---

## 📊 Smoothing Guide

```
Value   Feel            Use For
1-3     Instant/Jittery Live drums, triggers
4-6     Responsive      General performance
7-10    Balanced        Most recording
11-15   Smooth          Ambient, slow movements
16-20   Very Smooth     Automation, no shake
```

---

## 🎨 DAW Mapping Ideas

### Synth Control
```
Left X  → Filter Cutoff
Left Y  → Resonance
Pinch   → Volume/VCA
Palm    → Filter Type/Mode
```

### Effect Control
```
Right X → Delay Time
Right Y → Reverb Mix
Pinch   → Wet/Dry
Spread  → Modulation Rate
```

### Drum Triggering
```
L Pinch → Kick (on/off)
R Pinch → Snare (on/off)
L Fist  → Hi-hat Open/Close
R Fist  → Crash Trigger
```

### Video/Visuals
```
L X/Y   → Position/Transform
R X/Y   → Color/Effect params
Distance→ Zoom/Scale
Velocity→ Strobe/Animation speed
```

---

## 🔧 Config File Location

Settings saved to: `hand_midi_config.json`

Example presets: `example_presets.json`

Full guide: `CONFIGURATION_GUIDE.md`

---

**Remember:** The best settings are the ones that feel right to YOU.
Start with a preset, adjust live, save when perfect!
