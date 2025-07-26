#!/usr/bin/env python3
"""
Motion Line Controller - Minimal Edition
========================================

A minimalist motion detection MIDI controller that triggers when objects cross a line.

Features:
- Single detection line (click to position)
- MIDI note on crossing
- Position CC (Y coordinate)
- Velocity CC (crossing speed)
- Clear visual feedback

Controls:
- Click to position detection line
- Q to quit
- V to toggle vertical/horizontal line

MIDI Output:
- Note 60 (C4) when object crosses
- CC 1: Y position (0-127)
- CC 2: Crossing velocity (0-127)
"""

import cv2
import numpy as np
import time
from collections import deque
import sys

try:
    import rtmidi
    MIDI_AVAILABLE = True
except ImportError:
    MIDI_AVAILABLE = False
    print("⚠️  Install rtmidi: pip install python-rtmidi")

class MotionLineController:
    def __init__(self):
        print("🎵 Motion Line Controller - Minimal Edition")
        print("Click to position detection line, move objects across it!")
        
        # Detection line settings
        self.line_x = 320  # Default center X
        self.line_y = 240  # Default center Y
        self.is_vertical = True  # True = vertical line, False = horizontal
        
        # Motion detection
        self.prev_frame = None
        self.motion_threshold = 30  # Minimum motion to detect
        self.line_thickness = 3
        
        # Crossing detection
        self.crossing_history = deque(maxlen=10)  # Track crossings
        self.last_crossing_time = 0
        self.min_crossing_interval = 0.1  # Minimum time between crossings
        
        # MIDI setup
        self.midi_enabled = False
        self.midi_out = None
        self.setup_midi()
        
        # Visual feedback
        self.last_trigger_time = 0
        self.trigger_flash_duration = 0.3
        
    def setup_midi(self):
        """Initialize MIDI output"""
        if not MIDI_AVAILABLE:
            return
            
        try:
            self.midi_out = rtmidi.MidiOut()
            
            # Create virtual MIDI port
            self.midi_out.open_virtual_port("Motion Line Controller")
            self.midi_enabled = True
            print("✓ MIDI enabled: Motion Line Controller")
            
        except Exception as e:
            print(f"⚠️  MIDI error: {e}")
    
    def send_midi_note(self, note=60, velocity=127):
        """Send MIDI note on/off"""
        if self.midi_enabled:
            try:
                # Note on
                self.midi_out.send_message([0x90, note, velocity])
                # Note off after short duration
                self.midi_out.send_message([0x80, note, 0])
            except Exception as e:
                print(f"MIDI send error: {e}")
    
    def send_midi_cc(self, cc, value):
        """Send MIDI CC message"""
        if self.midi_enabled:
            try:
                value = max(0, min(127, int(value)))
                self.midi_out.send_message([0xB0, cc, value])
            except Exception as e:
                print(f"MIDI CC error: {e}")
    
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks to position detection line"""
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.is_vertical:
                self.line_x = x
                print(f"📍 Vertical line positioned at X={x}")
            else:
                self.line_y = y
                print(f"📍 Horizontal line positioned at Y={y}")
    
    def detect_motion(self, frame):
        """Detect motion along the detection line"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        
        if self.prev_frame is None:
            self.prev_frame = gray
            return None, 0
        
        # Calculate frame difference
        diff = cv2.absdiff(self.prev_frame, gray)
        
        # Extract motion along the detection line
        if self.is_vertical:
            # Vertical line - check motion across X at line_x
            line_motion = diff[:, max(0, min(self.line_x, diff.shape[1]-1))]
            line_coord = self.line_x
        else:
            # Horizontal line - check motion across Y at line_y  
            line_motion = diff[max(0, min(self.line_y, diff.shape[0]-1)), :]
            line_coord = self.line_y
        
        # Find motion peaks above threshold
        motion_points = np.where(line_motion > self.motion_threshold)[0]
        
        self.prev_frame = gray
        
        if len(motion_points) > 0:
            # Calculate crossing position and intensity
            if self.is_vertical:
                crossing_pos = np.mean(motion_points)  # Y position
                max_intensity = np.max(line_motion[motion_points])
            else:
                crossing_pos = np.mean(motion_points)  # X position  
                max_intensity = np.max(line_motion[motion_points])
            
            return crossing_pos, max_intensity
        
        return None, 0
    
    def process_crossing(self, position, intensity, frame_height):
        """Process detected crossing and send MIDI"""
        current_time = time.time()
        
        # Prevent rapid-fire triggering
        if current_time - self.last_crossing_time < self.min_crossing_interval:
            return
        
        # Calculate MIDI values
        if self.is_vertical:
            # Vertical line: Y position maps to CC
            pos_midi = int(np.clip((1 - position / frame_height) * 127, 0, 127))
        else:
            # Horizontal line: X position maps to CC
            pos_midi = int(np.clip(position / 640 * 127, 0, 127))  # Assume 640 width
        
        # Velocity based on motion intensity
        velocity_midi = int(np.clip(intensity / 100 * 127, 10, 127))
        
        # Send MIDI
        self.send_midi_note(60, velocity_midi)  # Note C4
        self.send_midi_cc(1, pos_midi)         # Position
        self.send_midi_cc(2, velocity_midi)    # Velocity
        
        # Visual feedback
        self.last_trigger_time = current_time
        self.last_crossing_time = current_time
        
        # Console feedback
        direction = "vertical" if self.is_vertical else "horizontal"
        print(f"🎵 Crossing detected! {direction} line | Pos: {pos_midi} | Vel: {velocity_midi}")
    
    def draw_interface(self, frame):
        """Draw minimal, clear interface"""
        h, w = frame.shape[:2]
        current_time = time.time()
        
        # Draw detection line
        line_color = (0, 255, 255)  # Cyan
        
        if self.is_vertical:
            # Vertical line
            cv2.line(frame, (self.line_x, 0), (self.line_x, h), line_color, self.line_thickness)
            
            # Line label
            cv2.putText(frame, "DETECTION LINE", (self.line_x + 10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, line_color, 2)
            cv2.putText(frame, f"X={self.line_x}", (self.line_x + 10, 55), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, line_color, 1)
        else:
            # Horizontal line
            cv2.line(frame, (0, self.line_y), (w, self.line_y), line_color, self.line_thickness)
            
            # Line label
            cv2.putText(frame, "DETECTION LINE", (10, self.line_y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, line_color, 2)
            cv2.putText(frame, f"Y={self.line_y}", (10, self.line_y + 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, line_color, 1)
        
        # Flash effect when triggered
        if current_time - self.last_trigger_time < self.trigger_flash_duration:
            flash_alpha = 1.0 - (current_time - self.last_trigger_time) / self.trigger_flash_duration
            flash_overlay = np.zeros_like(frame)
            flash_overlay[:] = (0, 255, 0)  # Green flash
            cv2.addWeighted(frame, 1.0, flash_overlay, flash_alpha * 0.3, 0, frame)
            
            # Trigger indicator
            cv2.putText(frame, "TRIGGERED!", (w//2 - 80, h//2), 
                       cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 0), 3)
        
        # Instructions
        instructions = [
            "Click to position detection line",
            "V = toggle vertical/horizontal",
            "Q = quit",
            "",
            f"MIDI: {'ON' if self.midi_enabled else 'OFF'}",
            f"Mode: {'Vertical' if self.is_vertical else 'Horizontal'}"
        ]
        
        for i, text in enumerate(instructions):
            color = (255, 255, 255) if text else (100, 100, 100)
            if "MIDI: ON" in text:
                color = (0, 255, 0)
            elif "MIDI: OFF" in text:
                color = (0, 0, 255)
                
            cv2.putText(frame, text, (10, h - 120 + i * 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return frame
    
    def run(self):
        """Main loop"""
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        window_name = "Motion Line Controller"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, self.mouse_callback)
        
        print("\n🚀 Motion Line Controller Started!")
        print("Controls:")
        print("  Click - Position detection line")
        print("  V - Toggle vertical/horizontal")
        print("  Q - Quit")
        print("\nMIDI Output:")
        print("  Note 60 (C4) - Crossing trigger")
        print("  CC 1 - Position (0-127)")
        print("  CC 2 - Velocity (0-127)")
        print()
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Mirror for natural interaction
                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]
                
                # Detect motion crossing
                crossing_pos, intensity = self.detect_motion(frame)
                
                # Process crossing if detected
                if crossing_pos is not None:
                    self.process_crossing(crossing_pos, intensity, h)
                
                # Draw interface
                frame = self.draw_interface(frame)
                
                # Display
                cv2.imshow(window_name, frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('v'):
                    self.is_vertical = not self.is_vertical
                    direction = "vertical" if self.is_vertical else "horizontal"
                    print(f"🔄 Switched to {direction} detection line")
                
        except KeyboardInterrupt:
            print("\n👋 Interrupted by user")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            if self.midi_out:
                self.midi_out.close_port()
            print("\n✓ Motion Line Controller stopped")

def main():
    """Entry point"""
    controller = MotionLineController()
    controller.run()

if __name__ == "__main__":
    main()