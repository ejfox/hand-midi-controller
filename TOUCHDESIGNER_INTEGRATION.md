# TouchDesigner Integration Guide
## Hand MIDI Controller → Reactive Visuals

Transform your hand tracking into sick responsive visuals with TouchDesigner!

## 🔥 What You'll Achieve

- **Real-time hand-to-visual mapping**
- **12 simultaneous control parameters**
- **Velocity-reactive particle systems**
- **Distance-controlled camera movements**
- **Pinch-triggered effects**
- **Palm-controlled shaders**

---

## 🚀 Quick Setup (5 minutes)

### 1. Start Hand MIDI Controller
```bash
cd hand-midi-controller
./run.sh
```
Verify "HandMIDI Virtual" appears in MIDI devices.

### 2. TouchDesigner MIDI Setup

**Add MIDI In CHOP:**
```
1. Create MIDI In CHOP
2. Device: "HandMIDI Virtual" 
3. Active: ON
4. Channel Names: ON
```

### 3. Basic Parameter Mapping

**Extract Hand Parameters:**
```
MIDI In → Select CHOP (extract channels) → Math CHOP (scale 0-1)
```

**Channel Names:**
- `cc1` = Left X-axis
- `cc2` = Left Y-axis  
- `cc3` = Left Pinch
- `cc6` = Left Velocity
- `cc7` = Right X-axis
- `cc12` = Right Distance

---

## 🎨 Visual Effect Examples

### Velocity-Reactive Particles

**Network Setup:**
```
MIDI In → Select (cc6) → Math (power curve) → Particle SOP
```

**Parameters:**
- Velocity → Birth Rate (0-1000)
- Velocity → Initial Speed (0-10)
- Quick movements = particle bursts!

### Distance-Controlled Camera

**Network Setup:**
```
MIDI In → Select (cc12) → Math (smooth) → Camera COMP
```

**Parameters:**
- Distance → Camera Distance (5-50)
- Distance → FOV (30-120)
- Hands apart = zoom out, together = zoom in

### Pinch-Triggered Effects

**Network Setup:**
```
MIDI In → Select (cc3,cc9) → Threshold CHOP → Switch TOP
```

**Logic:**
- Pinch value > 100 = trigger effect
- Use Logic CHOP for complex combinations
- Trigger feedback, trails, explosions

### Palm-Controlled Shaders

**Network Setup:**
```
MIDI In → Select (cc4,cc10) → Ramp TOP → Composite TOP
```

**Effect:**
- Palm openness → Shader intensity
- Left palm → Color temperature
- Right palm → Distortion amount

---

## 🔥 Advanced Setups

### Dual Hand Particle System

```python
# TouchDesigner Python in Execute DAT
def onValueChange(channel, sampleIndex, val, prev):
    # Left hand controls red particles
    if channel.name == 'cc1':  # Left X
        op('redParticles').par.translatex = val * 20 - 10
    elif channel.name == 'cc2':  # Left Y  
        op('redParticles').par.translatey = (1-val) * 20 - 10
    elif channel.name == 'cc6':  # Left Velocity
        op('redParticles').par.birthrate = val * 1000
    
    # Right hand controls blue particles
    elif channel.name == 'cc7':  # Right X
        op('blueParticles').par.translatex = val * 20 - 10
    elif channel.name == 'cc8':  # Right Y
        op('blueParticles').par.translatey = (1-val) * 20 - 10
    
    # Distance controls interaction
    elif channel.name == 'cc12':  # Distance
        force = (1 - val) * 5  # Closer = more attraction
        op('force1').par.strength = force
```

### Audio-Reactive Enhancement

**Combine with Audio:**
```
Audio In → Audio Spectrum → Math CHOP → Add with MIDI values
```

**Result:** Hand gestures modulate audio-reactive visuals!

### Multi-Layer Feedback

**Setup:**
```
Hand MIDI → Multiple render layers → Feedback TOP → Final composite
```

**Mapping:**
- Rotation → Feedback rotation
- Pinch → Feedback scale  
- Palm → Feedback mix amount
- Velocity → Noise intensity

---

## 📱 Example TouchDesigner Project

### Basic Reactive Visual (.toe file structure)

```
/project
├── midi_input/
│   ├── midiIn1 (MIDI In CHOP)
│   ├── select1 (Select CHOP - extract channels)
│   └── math1 (Math CHOP - normalize)
├── effects/
│   ├── particles/ (Particle SOPs)
│   ├── geometry/ (Reactive geometry)
│   ├── shaders/ (Parameter-driven shaders)
│   └── camera/ (Distance-controlled camera)
├── output/
│   ├── render1 (Render TOP)
│   └── out1 (Video output)
└── controls/
    ├── velocity_trigger (Logic CHOP)
    ├── distance_smooth (Filter CHOP)
    └── pinch_threshold (Threshold CHOP)
```

### Parameter Suggestions

**Creative Mappings:**
- **Left X/Y** → Particle spawn position
- **Right X/Y** → Camera look-at target
- **Left Pinch** → Geometry scale/morph
- **Right Pinch** → Shader intensity
- **Left Palm** → Color temperature
- **Right Palm** → Distortion amount
- **Left Rotation** → Scene rotation
- **Right Rotation** → Texture rotation
- **Left Velocity** → Particle birth rate
- **Right Distance** → Field of view/zoom

---

## 🎛️ Performance Tips

### Optimization
- Use **Filter CHOPs** to smooth jittery MIDI values
- **Lag CHOPs** for smooth transitions
- **Threshold CHOPs** for trigger-based effects
- **Math CHOPs** with custom expressions for complex mapping

### Latency Reduction
- Set TouchDesigner to **Performance Mode**
- Minimize unnecessary operators in signal chain
- Use **Cook Type: Always** for MIDI inputs
- Target 60fps for smooth hand tracking response

### Creative Techniques
- **Cross-fade** between different effects based on hand distance
- **Trigger sequences** with pinch gestures
- **Morphing geometry** with palm openness
- **Dynamic lighting** with hand rotation

---

## 🌟 Showcase Ideas

### Live Performance Setup
1. **DJ/VJ Hybrid**: Use hands for both music and visuals
2. **Interactive Installation**: Audience hand control
3. **Dance Performance**: Dancer's hands control visuals
4. **Music Production**: Visual feedback while composing

### Creative Applications
- **Generative Art**: Hand gestures seed algorithms
- **Data Visualization**: Interactive exploration
- **Educational**: Demonstrate physics/audio concepts
- **Therapeutic**: Meditative visual feedback

---

## 🔗 Resources

### TouchDesigner Learning
- [TouchDesigner Fundamentals](https://learn.derivative.ca/)
- [MIDI CHOPs Documentation](https://docs.derivative.ca/MIDI_In_CHOP)
- [Particle Systems Tutorial](https://derivative.ca/community-post/tutorial/particle-systems/62888)

### Community Projects
- Share your setups on [TouchDesigner Forum](https://forum.derivative.ca/)
- Post videos with #HandMIDI #TouchDesigner
- Collaborate on [GitHub](https://github.com/derivative-inc)

---

**This combination is absolutely fucking peak creative tech! 🚀**

Your hands control every aspect of the visual experience in real-time. The velocity and distance parameters especially create incredibly expressive and natural control that traditional MIDI controllers can't match.

*Ready to turn your living room into a cyberpunk visual studio?* 🔥