# Configuration & Controls Guide

## Quick Start: Using Presets

The easiest way to get started is with the built-in presets. Press **1-5** during operation:

### Preset 1: Performance 🎸
**When to use:** Live performances, jam sessions, reactive visuals
- Maximum responsiveness (minimal smoothing)
- All gestures enabled (velocity, distance, fist, spread)
- Extended finger tracking
- Cyberpunk UI with full meters

**Best for:** High-energy electronic music, VJing, experimental performances

### Preset 2: Studio 🎙️
**When to use:** Recording sessions, DAW automation, production work
- Balanced smoothing for stable recordings
- Velocity tracking for musical dynamics
- Clean minimal UI
- Optimal for consistent takes

**Best for:** Recording MIDI, creating automation, detailed production

### Preset 3: Precise 🎯
**When to use:** Detailed sequencing, fine control, slow movements
- 14-bit MIDI CC for ultra-high resolution
- Maximum smoothing to eliminate jitter
- Tight gesture thresholds
- Ideal for precise parameter control

**Best for:** Sound design, detailed modulation, slow evolving textures

### Preset 4: Experimental 🧪
**When to use:** Exploring the system, testing capabilities
- Every feature enabled
- All finger combinations tracked
- Full debug interface with telemetry
- Discover new control methods

**Best for:** Learning the system, finding your style, experimentation

### Preset 5: Minimal ⚡
**When to use:** Simple setups, learning, low CPU usage
- Position (X/Y) and pinch only
- Lightweight processing
- Clean interface
- Quick setup

**Best for:** First time use, simple instruments, older computers

---

## Real-Time Adjustments

Fine-tune your setup during performance without restarting:

### Smoothing Controls

**Position Smoothing** (`+` / `-` keys)
- **What it does:** Smooths out hand position tracking (X/Y)
- **+** = More smooth (less jittery, slight lag)
- **-** = Less smooth (more responsive, can be jittery)
- **Range:** 1-20 frames
- **Sweet spot:** 3-8 for most uses

**Gesture Smoothing** (`[` / `]` keys)
- **What it does:** Smooths pinch, palm, rotation gestures
- **]** = More smooth (stable values)
- **[** = Less smooth (instant response)
- **Range:** 1-20 frames
- **Sweet spot:** 5-12 for most uses

**Pinch Sensitivity** (`{` / `}` keys)
- **What it does:** Adjusts how sensitive the pinch gesture is
- **{** = More sensitive (wider range)
- **}** = Less sensitive (tighter range)
- **Tip:** Adjust based on your hand size and pinching style

### Finding Your Settings

1. **Start with a preset** - Pick the one closest to your use case
2. **Adjust smoothing first** - Use +/- keys while performing
3. **Watch the MIDI values** - They should be stable but responsive
4. **Fine-tune gestures** - Adjust pinch with {/} if needed
5. **Save with 's'** - Press 's' to save your perfect settings

---

## Advanced MIDI Mappings

### Standard Controls (Always Active)

| CC | Parameter | Description |
|----|-----------|-------------|
| CC1 | Left X | Left hand horizontal position |
| CC2 | Left Y | Left hand vertical position |
| CC3 | Right X | Right hand horizontal position |
| CC4 | Right Y | Right hand vertical position |
| CC5 | Left Pinch | Left thumb-index distance |
| CC6 | Right Pinch | Right thumb-index distance |
| CC7 | Left Palm | Left hand openness |
| CC8 | Right Palm | Right hand openness |
| CC9 | Left Rotation | Left hand rotation angle |
| CC10 | Right Rotation | Right hand rotation angle |

### Extended Gestures (Enable in Presets)

| CC | Parameter | Enable With | Description |
|----|-----------|-------------|-------------|
| CC11 | L Thumb-Middle | `thumb_middle_enabled` | Left thumb to middle finger |
| CC12 | R Thumb-Middle | `thumb_middle_enabled` | Right thumb to middle finger |
| CC13 | L Thumb-Ring | `thumb_ring_enabled` | Left thumb to ring finger |
| CC14 | R Thumb-Ring | `thumb_ring_enabled` | Right thumb to ring finger |
| CC15 | L Thumb-Pinky | `thumb_pinky_enabled` | Left thumb to pinky |
| CC16 | R Thumb-Pinky | `thumb_pinky_enabled` | Right thumb to pinky |
| CC17 | L Fist | `fist_detection` | Left fist closure (0=open, 127=closed) |
| CC18 | R Fist | `fist_detection` | Right fist closure |
| CC19 | L Spread | `spread_detection` | Left finger spread (0=together, 127=spread) |
| CC20 | R Spread | `spread_detection` | Right finger spread |
| CC21 | L Velocity | `velocity_tracking` | Left hand movement speed |
| CC22 | R Velocity | `velocity_tracking` | Right hand movement speed |
| CC23 | Hand Distance | `hand_distance_tracking` | Distance between both hands |

---

## Use Case Examples

### Example 1: Ambient Synth Control
**Preset:** Studio (key 2)
**Adjustments:**
- Increase position smoothing to 12-15 (+ key several times)
- Increase gesture smoothing to 15 (] key several times)
**Map in DAW:**
- Left X → Filter Cutoff
- Left Y → Reverb Mix
- Left Pinch → Volume
- Right X → Delay Time
- Right Y → Chorus Depth

### Example 2: Drum Triggering
**Preset:** Performance (key 1)
**Adjustments:**
- Decrease position smoothing to 2-3 (- key)
- Keep gesture smoothing at 5
**Map in DAW:**
- Left Pinch → Kick Trigger (threshold)
- Right Pinch → Snare Trigger
- Left Fist → Hi-hat Open/Close
- Right Fist → Crash Trigger
- Hand Distance → Filter Sweep

### Example 3: Live Video Effects
**Preset:** Performance (key 1)
**Adjustments:**
- Position smoothing at 4-5
- Enable hand distance tracking
**Map in VJ Software:**
- Left X/Y → Video Position
- Right X/Y → Effect Parameters
- Hand Distance → Zoom/Scale
- Left Velocity → Strobe Speed
- Right Velocity → Color Rotation

### Example 4: Sound Design Automation
**Preset:** Precise (key 3)
**Adjustments:**
- Maximum smoothing (20 position, 18 gesture)
- Use custom mapping area for specific range
**Map in DAW:**
- Left X → Macro 1 (very precise)
- Left Y → Macro 2
- All gestures → Different timbre parameters
- Record automation in slow, deliberate movements

---

## Custom Mapping Areas

Click and drag on the video to define a control zone. Only hand movements in that area will be mapped to MIDI 0-127.

**Why use this:**
- Define comfortable performance zones
- Avoid accidental extreme values
- Create "safe" areas for specific gestures
- Map different areas to different instruments

**How to use:**
1. Click and hold on the video
2. Drag to create a rectangle
3. Release to set the area
4. Hand positions outside this area won't change MIDI values
5. Press 'c' to clear and use full camera view

**Pro tip:** Set a smaller area in the center of your camera view where your hands naturally rest. This gives you maximum control precision in your comfortable range.

---

## Keyboard Reference

| Key | Function | Details |
|-----|----------|---------|
| Q | Quit | Exit the application |
| M | UI Mode | Cycle through minimal/cyberpunk/debug |
| V | Camera | Switch between available cameras |
| S | Save | Save current config to `hand_midi_config.json` |
| C | Clear | Clear custom mapping area |
| 1 | Preset | Load Performance preset |
| 2 | Preset | Load Studio preset |
| 3 | Preset | Load Precise preset |
| 4 | Preset | Load Experimental preset |
| 5 | Preset | Load Minimal preset |
| + | Smoothing | Increase position smoothing |
| - | Smoothing | Decrease position smoothing |
| ] | Smoothing | Increase gesture smoothing |
| [ | Smoothing | Decrease gesture smoothing |
| } | Sensitivity | Decrease pinch sensitivity |
| { | Sensitivity | Increase pinch sensitivity |

---

## Configuration File

Settings are saved to `hand_midi_config.json`. You can edit this file directly for advanced customization.

### Important Settings

```json
{
  "position_smoothing": 5,        // Frame averaging for X/Y position
  "gesture_smoothing": 8,         // Frame averaging for gestures
  "velocity_smoothing": 3,        // Frame averaging for velocity
  "pinch_threshold_close": 0.02,  // Pinch closed threshold
  "pinch_threshold_open": 0.12,   // Pinch open threshold
  "palm_sensitivity": 1.0,        // Palm detection multiplier
  "rotation_sensitivity": 1.0,    // Rotation detection multiplier
  "velocity_tracking": false,     // Enable velocity CC
  "hand_distance_tracking": false,// Enable hand distance CC
  "fist_detection": false,        // Enable fist gesture
  "spread_detection": true,       // Enable spread gesture
  "ui_mode": "cyberpunk"         // UI style
}
```

### CC Mappings

You can remap MIDI CC numbers by editing the `cc_mappings` section:

```json
"cc_mappings": {
  "left_x": {
    "cc": 1,              // MIDI CC number
    "label": "l_x",       // Display label
    "color": [120, 180, 200],  // RGB color for UI
    "enabled": true       // Send this CC
  }
}
```

---

## Tips for Best Results

### Lighting
- Use bright, even lighting
- Avoid backlighting (window behind you)
- Natural daylight works great
- Avoid harsh shadows on hands

### Camera Position
- Position camera at chest/face height
- Keep hands 1-3 feet from camera
- Plain background helps tracking
- Avoid busy/patterned backgrounds

### Hand Technique
- Keep fingers visible to camera
- Avoid extreme angles
- Practice smooth movements
- Exaggerate gestures at first

### Performance Tips
- Start with higher smoothing, reduce as you get comfortable
- Use custom mapping areas to define "safe" zones
- Save multiple configs for different songs/setups
- Practice transitions between gestures
- Record your sessions to analyze what works

---

## Troubleshooting

**Jittery MIDI values:**
- Increase smoothing with + and ] keys
- Check lighting (should be bright and even)
- Use custom mapping area to reduce range

**Sluggish response:**
- Decrease smoothing with - and [ keys
- Check camera FPS (should be 30+)
- Close other applications

**Pinch not working well:**
- Adjust sensitivity with { and } keys
- Exaggerate the gesture
- Check your hand is well-lit

**No MIDI appearing in DAW:**
- Restart DAW after starting Hand MIDI Controller
- Check MIDI input is set to "Hand MIDI Controller"
- Verify MIDI channel matches (default is 0/1)

---

## Next Steps

1. **Try each preset** - Spend 5 minutes with each to understand them
2. **Find your base** - Pick the preset closest to your needs
3. **Adjust live** - Use the +/-/[/]/{/} keys while performing
4. **Save your config** - Press 's' when you find settings you like
5. **Map in your DAW** - Assign CCs to synth/effect parameters
6. **Practice** - Muscle memory is key for expressive control
7. **Experiment** - Try unconventional mappings and combinations

**Remember:** The best configuration is the one that feels natural to YOU. Don't be afraid to experiment!
