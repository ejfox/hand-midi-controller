#!/usr/bin/env python3
import cv2
import mediapipe as mp
import numpy as np
import math
import time
import os
from collections import deque

# Try to import rtmidi for MIDI output
try:
    import rtmidi
    MIDI_AVAILABLE = True
except ImportError:
    MIDI_AVAILABLE = False
    print("[!] rtmidi not available - install with: pip install python-rtmidi")

class HandMIDIController:
    def __init__(self):
        print(">>> hand midi controller")
        print("live midi cc table view")
        
        # Initialize MediaPipe - MAXIMUM PERFORMANCE SETTINGS
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=0,  # lightest model
            min_detection_confidence=0.5,  # lower for speed
            min_tracking_confidence=0.3   # much lower for speed
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # MIDI setup
        self.midi_enabled = False
        self.setup_midi()
        
        # Smoothing
        self.smoothing_window = 3  # PERFORMANCE: Reduce smoothing for speed
        self.left_hand_history = self._create_history()
        self.right_hand_history = self._create_history()
        
        # PERFORMANCE: Pre-allocate arrays for zero-copy operations
        self._frame_buffer = None
        
        # Region selection for X/Y bounds
        self.selection_active = False
        self.selection_start = None
        self.selection_end = None
        self.selection_region = None
        self.mouse_dragging = False
        
        # CC mappings - left hand block, right hand block
        self.cc_mappings = {
            'left_x': {'cc': 1, 'label': 'left_x'},
            'left_y': {'cc': 2, 'label': 'left_y'},
            'left_pinch': {'cc': 3, 'label': 'left_pinch'},
            'left_palm': {'cc': 4, 'label': 'left_palm'},
            'left_rotation': {'cc': 5, 'label': 'left_rot'},
            'left_extra': {'cc': 6, 'label': 'left_extra'},
            'right_x': {'cc': 7, 'label': 'right_x'},
            'right_y': {'cc': 8, 'label': 'right_y'},
            'right_pinch': {'cc': 9, 'label': 'right_pinch'},
            'right_palm': {'cc': 10, 'label': 'right_palm'},
            'right_rotation': {'cc': 11, 'label': 'right_rot'},
            'right_extra': {'cc': 12, 'label': 'right_extra'}
        }
        
        # Current values for table display
        self.current_values = {key: 0 for key in self.cc_mappings}
        
        # FPS tracking
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
        
        # Pinch thresholds
        self.pinch_threshold_close = 0.02
        self.pinch_threshold_open = 0.12
        
    def _create_history(self):
        return {
            'x': deque(maxlen=self.smoothing_window),
            'y': deque(maxlen=self.smoothing_window),
            'thumb_index_dist': deque(maxlen=self.smoothing_window),
            'palm_open': deque(maxlen=self.smoothing_window),
            'rotation': deque(maxlen=self.smoothing_window)
        }
    
    def setup_midi(self):
        if not MIDI_AVAILABLE:
            return
            
        try:
            self.midi_out = rtmidi.MidiOut()
            self.midi_out.open_virtual_port("Hand MIDI Controller")
            self.midi_enabled = True
            print("[+] midi device created: 'Hand MIDI Controller'")
        except Exception as e:
            print(f"[!] midi setup failed: {e}")
    
    def send_midi_cc(self, cc_key, value):
        if not self.midi_enabled:
            return
            
        try:
            cc_num = self.cc_mappings[cc_key]['cc']
            value = max(0, min(127, int(value)))
            self.current_values[cc_key] = value
            
            status_byte = 0xB0  # channel 1
            message = [status_byte, cc_num, value]
            self.midi_out.send_message(message)
        except Exception:
            pass
    
    def smooth_value(self, value, history):
        history.append(value)
        return np.mean(history) if len(history) > 0 else value
    
    def calculate_distance(self, point1, point2):
        return math.sqrt(
            (point1.x - point2.x) ** 2 + 
            (point1.y - point2.y) ** 2 + 
            (point1.z - point2.z) ** 2
        )
    
    def calculate_palm_openness(self, hand_landmarks):
        wrist = hand_landmarks.landmark[0]
        fingertips = [hand_landmarks.landmark[i] for i in [4, 8, 12, 16, 20]]
        finger_bases = [hand_landmarks.landmark[i] for i in [5, 9, 13, 17]]
        
        tip_distances = [self.calculate_distance(wrist, tip) for tip in fingertips]
        base_distances = [self.calculate_distance(wrist, base) for base in finger_bases]
        
        avg_tip = np.mean(tip_distances)
        avg_base = np.mean(base_distances)
        
        if avg_base > 0:
            openness = avg_tip / avg_base
            return max(0, min(127, int((openness - 1.2) * 159)))
        return 64
    
    def calculate_hand_rotation(self, hand_landmarks):
        wrist = hand_landmarks.landmark[0]
        middle_base = hand_landmarks.landmark[9]
        
        dx = middle_base.x - wrist.x
        dy = middle_base.y - wrist.y
        angle = math.atan2(dy, dx)
        
        normalized = int((angle + math.pi) / (2 * math.pi) * 127)
        return max(0, min(127, normalized))
    
    def calculate_pinch_value(self, thumb_index_dist):
        if thumb_index_dist <= self.pinch_threshold_close:
            return 127
        elif thumb_index_dist >= self.pinch_threshold_open:
            return 0
        else:
            range_size = self.pinch_threshold_open - self.pinch_threshold_close
            normalized = (thumb_index_dist - self.pinch_threshold_close) / range_size
            return max(0, min(127, int(127 * (1.0 - normalized))))
    
    def process_hand(self, hand_landmarks, handedness):
        hand_type = handedness.classification[0].label
        
        # Get palm center
        wrist = hand_landmarks.landmark[0]
        middle_base = hand_landmarks.landmark[9]
        palm_x = (wrist.x + middle_base.x) / 2
        palm_y = (wrist.y + middle_base.y) / 2
        
        # Calculate features
        thumb_tip = hand_landmarks.landmark[4]
        index_tip = hand_landmarks.landmark[8]
        thumb_index_dist = self.calculate_distance(thumb_tip, index_tip)
        palm_open = self.calculate_palm_openness(hand_landmarks)
        rotation = self.calculate_hand_rotation(hand_landmarks)
        
        # Choose history based on hand
        history = self.left_hand_history if hand_type == "Left" else self.right_hand_history
        cc_prefix = 'left' if hand_type == "Left" else 'right'
        
        # Position mapping
        midi_x = palm_x * 127
        midi_y = (1 - palm_y) * 127
        
        # Smooth values
        smoothed_x = self.smooth_value(midi_x, history['x'])
        smoothed_y = self.smooth_value(midi_y, history['y'])
        smoothed_dist = self.smooth_value(thumb_index_dist, history['thumb_index_dist'])
        smoothed_palm = self.smooth_value(palm_open, history['palm_open'])
        smoothed_rotation = self.smooth_value(rotation, history['rotation'])
        
        # Calculate pinch
        pinch_midi = self.calculate_pinch_value(smoothed_dist)
        
        # Send MIDI
        self.send_midi_cc(f'{cc_prefix}_x', int(smoothed_x))
        self.send_midi_cc(f'{cc_prefix}_y', int(smoothed_y))
        self.send_midi_cc(f'{cc_prefix}_pinch', pinch_midi)
        self.send_midi_cc(f'{cc_prefix}_palm', int(smoothed_palm))
        self.send_midi_cc(f'{cc_prefix}_rotation', int(smoothed_rotation))
        
        return thumb_tip, index_tip, pinch_midi
    
    def update_fps(self):
        self.fps_counter += 1
        current_time = time.time()
        
        if current_time - self.fps_start_time >= 1.0:
            self.current_fps = self.fps_counter / (current_time - self.fps_start_time)
            self.fps_counter = 0
            self.fps_start_time = current_time
    
    def reset_midi_values(self):
        """Reset all MIDI values to zero when hands are not detected"""
        for hand in ['left', 'right']:
            self.send_midi_cc(f'{hand}_x', 0)
            self.send_midi_cc(f'{hand}_y', 0)
            self.send_midi_cc(f'{hand}_pinch', 0)
            self.send_midi_cc(f'{hand}_palm', 0)
            self.send_midi_cc(f'{hand}_rotation', 0)
    
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events for region selection"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.mouse_dragging = True
            self.selection_start = (x, y)
            self.selection_end = (x, y)
            self.selection_active = False
            
        elif event == cv2.EVENT_MOUSEMOVE and self.mouse_dragging:
            self.selection_end = (x, y)
            
        elif event == cv2.EVENT_LBUTTONUP:
            if self.mouse_dragging and self.selection_start and self.selection_end:
                # Set selection region
                x1, y1 = self.selection_start
                x2, y2 = self.selection_end
                self.selection_region = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
                self.selection_active = True
                print(f"[*] region selected: {self.selection_region}")
            self.mouse_dragging = False
    
    def send_midi_cc(self, cc_name, value):
        """Send MIDI CC value and update current values for display"""
        if cc_name in self.cc_mappings:
            cc_num = self.cc_mappings[cc_name]['cc']
            self.current_values[cc_name] = value
            
            if self.midi_enabled:
                try:
                    self.midi_out.control_change(0, cc_num, value)
                except Exception as e:
                    print(f"[!] MIDI error: {e}")
    
    def process_hand(self, hand_landmarks, handedness):
        """
        Process hand landmarks and extract control values
        
        Args:
            hand_landmarks: MediaPipe hand landmarks
            handedness: Left or right hand classification
            
        Returns:
            tuple: (thumb_tip, index_tip, pinch_value)
        """
        # Get hand label (left/right)
        hand_label = handedness.classification[0].label.lower()
        
        # Extract key landmarks
        wrist = hand_landmarks.landmark[0]
        thumb_tip = hand_landmarks.landmark[4]
        index_tip = hand_landmarks.landmark[8]
        middle_tip = hand_landmarks.landmark[12]
        ring_tip = hand_landmarks.landmark[16]
        pinky_tip = hand_landmarks.landmark[20]
        
        # Calculate X/Y positions (0-127 range for MIDI)
        # Use selection region if active, otherwise full frame
        if self.selection_active and self.selection_region:
            x1, y1, x2, y2 = self.selection_region
            # Map wrist position to selection region
            x_pos = int(np.clip((wrist.x - x1/1920) / ((x2-x1)/1920), 0, 1) * 127)
            y_pos = int(np.clip((wrist.y - y1/1080) / ((y2-y1)/1080), 0, 1) * 127)
        else:
            # Use full frame
            x_pos = int(wrist.x * 127)
            y_pos = int(wrist.y * 127)
        
        # Calculate pinch distance between thumb and index finger
        pinch_distance = np.sqrt((thumb_tip.x - index_tip.x)**2 + (thumb_tip.y - index_tip.y)**2)
        pinch_value = int(np.clip((1 - pinch_distance / 0.3) * 127, 0, 127))
        
        # Calculate palm openness (distance between fingertips)
        palm_spread = np.sqrt((index_tip.x - pinky_tip.x)**2 + (index_tip.y - pinky_tip.y)**2)
        palm_value = int(np.clip(palm_spread / 0.3 * 127, 0, 127))
        
        # Calculate rotation (angle of hand relative to wrist)
        hand_vector = np.array([middle_tip.x - wrist.x, middle_tip.y - wrist.y])
        angle = np.arctan2(hand_vector[1], hand_vector[0])
        rotation_value = int(((angle + np.pi) / (2 * np.pi)) * 127)
        
        # Send MIDI values
        self.send_midi_cc(f'{hand_label}_x', x_pos)
        self.send_midi_cc(f'{hand_label}_y', y_pos)
        self.send_midi_cc(f'{hand_label}_pinch', pinch_value)
        self.send_midi_cc(f'{hand_label}_palm', palm_value)
        self.send_midi_cc(f'{hand_label}_rotation', rotation_value)
        
        return thumb_tip, index_tip, pinch_value
    
    def draw_table_overlay(self, frame):
        """Draw exceptional retina-optimized table overlay with live MIDI values"""
        h, w = frame.shape[:2]
        
        # Scale factors for retina displays
        scale_factor = max(1.0, min(w / 1280, h / 720))  # adaptive scaling
        
        # PERFORMANCE: Pre-allocate overlay once, reuse buffer
        if not hasattr(self, '_overlay_cache'):
            self._overlay_cache = np.zeros_like(frame)
        overlay = self._overlay_cache
        overlay.fill(0)  # Clear previous content
        
        # Adaptive table sizing for retina displays with better positioning
        table_x = int(20 * scale_factor)
        table_y = int(20 * scale_factor)
        table_width = int(380 * scale_factor)
        table_height = int(420 * scale_factor)
        
        # Lighter dark panel with better transparency
        cv2.rectangle(overlay, (table_x, table_y), 
                     (table_x + table_width, table_y + table_height), 
                     (40, 40, 40), -1)
        
        # Refined border with gradient effect
        cv2.rectangle(overlay, (table_x, table_y), 
                     (table_x + table_width, table_y + table_height), 
                     (80, 80, 80), max(1, int(2 * scale_factor)))
        
        # Inner accent border
        cv2.rectangle(overlay, (table_x + 2, table_y + 2), 
                     (table_x + table_width - 2, table_y + table_height - 2), 
                     (120, 140, 120), 1)
        
        # Optimized font settings for retina
        font = cv2.FONT_HERSHEY_DUPLEX
        title_scale = 0.8 * scale_factor
        header_scale = 0.5 * scale_factor
        data_scale = 0.6 * scale_factor
        label_scale = 0.45 * scale_factor
        
        # Title with better positioning
        title_y = table_y + int(35 * scale_factor)
        cv2.putText(overlay, "hand midi controller", 
                   (table_x + int(15 * scale_factor), title_y), 
                   font, title_scale, (220, 220, 220), 
                   max(1, int(2 * scale_factor)), cv2.LINE_AA)
        
        # Subtitle
        subtitle_y = title_y + int(25 * scale_factor)
        cv2.putText(overlay, "live cc table", 
                   (table_x + int(15 * scale_factor), subtitle_y), 
                   font, header_scale, (160, 160, 160), 
                   max(1, int(1 * scale_factor)), cv2.LINE_AA)
        
        # Status indicators with better spacing
        status_y = subtitle_y + int(30 * scale_factor)
        status = "active" if self.midi_enabled else "offline"
        status_color = (100, 220, 100) if self.midi_enabled else (220, 100, 100)
        cv2.putText(overlay, f"status: {status}", 
                   (table_x + int(15 * scale_factor), status_y), 
                   font, header_scale, status_color, 
                   max(1, int(1 * scale_factor)), cv2.LINE_AA)
        
        # FPS with better positioning
        cv2.putText(overlay, f"fps: {self.current_fps:.0f}", 
                   (table_x + int(250 * scale_factor), status_y), 
                   font, header_scale, (180, 180, 180), 
                   max(1, int(1 * scale_factor)), cv2.LINE_AA)
        
        # Enhanced table headers
        header_y = status_y + int(40 * scale_factor)
        header_labels = ["cc#", "control", "value", "level"]
        header_positions = [15, 70, 220, 300]
        
        for i, (label, x_pos) in enumerate(zip(header_labels, header_positions)):
            cv2.putText(overlay, label, 
                       (table_x + int(x_pos * scale_factor), header_y), 
                       font, header_scale, (200, 200, 200), 
                       max(1, int(1 * scale_factor)), cv2.LINE_AA)
        
        # Header separator with better styling
        sep_y = header_y + int(8 * scale_factor)
        cv2.line(overlay, (table_x + int(10 * scale_factor), sep_y), 
                (table_x + table_width - int(10 * scale_factor), sep_y), 
                (100, 100, 100), max(1, int(1 * scale_factor)))
        
        # Data rows with enhanced spacing and visual hierarchy
        row_height = int(28 * scale_factor)
        y_offset = header_y + int(20 * scale_factor)
        
        # Enhanced CC mapping display with visual indicators
        for cc_key, cc_info in self.cc_mappings.items():
            value = self.current_values[cc_key]
            percentage = value / 127.0
            
            # Dynamic color coding based on activity
            if value > 100:
                text_color = (255, 255, 255)  # bright white for high values
                bar_color = (120, 255, 120)  # bright green
                cc_color = (255, 220, 100)   # highlight cc number
            elif value > 20:
                text_color = (220, 220, 220)  # normal white
                bar_color = (150, 200, 150)  # medium green
                cc_color = (200, 200, 200)
            else:
                text_color = (140, 140, 140)  # dim gray
                bar_color = (80, 80, 80)     # dark gray
                cc_color = (120, 120, 120)
            
            # CC number with prominent display
            cv2.putText(overlay, f"{cc_info['cc']:02d}", 
                       (table_x + int(15 * scale_factor), y_offset), 
                       font, data_scale, cc_color, 
                       max(1, int(2 * scale_factor)), cv2.LINE_AA)
            
            # Control name with hand indicator
            hand_indicator = "L" if "left" in cc_key else "R" if "right" in cc_key else ""
            control_text = f"{hand_indicator} {cc_info['label']}"
            cv2.putText(overlay, control_text, 
                       (table_x + int(70 * scale_factor), y_offset), 
                       font, label_scale, text_color, 
                       max(1, int(1 * scale_factor)), cv2.LINE_AA)
            
            # Value with percentage
            value_text = f"{value:03d}"
            cv2.putText(overlay, value_text, 
                       (table_x + int(220 * scale_factor), y_offset), 
                       font, data_scale, text_color, 
                       max(1, int(1 * scale_factor)), cv2.LINE_AA)
            
            # Enhanced progress bar with better visual feedback
            bar_x = table_x + int(300 * scale_factor)
            bar_y = y_offset - int(12 * scale_factor)
            bar_width = int(70 * scale_factor)
            bar_height = int(16 * scale_factor)
            
            # Bar background with subtle border
            cv2.rectangle(overlay, (bar_x, bar_y), 
                         (bar_x + bar_width, bar_y + bar_height), 
                         (40, 40, 40), -1)
            cv2.rectangle(overlay, (bar_x, bar_y), 
                         (bar_x + bar_width, bar_y + bar_height), 
                         (80, 80, 80), 1)
            
            # Value bar with smooth gradient effect
            if value > 0:
                fill_width = int(bar_width * percentage)
                # Create gradient effect for active bars
                for i in range(fill_width):
                    intensity = i / fill_width if fill_width > 0 else 0
                    color_r = int(bar_color[2] * (0.7 + 0.3 * intensity))
                    color_g = int(bar_color[1] * (0.8 + 0.2 * intensity))
                    color_b = int(bar_color[0] * (0.6 + 0.4 * intensity))
                    cv2.line(overlay, 
                            (bar_x + i, bar_y + 2), 
                            (bar_x + i, bar_y + bar_height - 2), 
                            (color_b, color_g, color_r), 1)
            
            y_offset += row_height
        
        # Enhanced control instructions
        instructions = [
            "controls:",
            "q - quit", 
            "v - cycle cameras",
            "t - terminal table"
        ]
        
        inst_y = table_y + table_height - int(80 * scale_factor)
        for instruction in instructions:
            color = (180, 180, 180) if instruction == "controls:" else (140, 140, 140)
            weight = max(1, int(2 * scale_factor)) if instruction == "controls:" else max(1, int(1 * scale_factor))
            cv2.putText(overlay, instruction, 
                       (table_x + int(15 * scale_factor), inst_y), 
                       font, label_scale, color, weight, cv2.LINE_AA)
            inst_y += int(18 * scale_factor)
        
        # Lighter blend for better camera visibility
        cv2.addWeighted(frame, 0.7, overlay, 0.3, 0, frame)
        
        # Draw selection region if active
        if self.selection_active and self.selection_region:
            x1, y1, x2, y2 = self.selection_region
            # Remove overlay from selected region by brightening it
            roi = frame[y1:y2, x1:x2]
            brightened = cv2.addWeighted(roi, 1.3, roi, 0, 10)
            frame[y1:y2, x1:x2] = brightened
            
            # Draw selection border
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.putText(frame, "ACTIVE REGION", (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # Draw current selection while dragging
        if self.mouse_dragging and self.selection_start and self.selection_end:
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
        
        return frame
    
    def draw_hand_markers(self, frame, hand_landmarks, thumb_tip, index_tip, pinch_value):
        """Draw optimized hand markers with retina support and parameter labels"""
        h, w = frame.shape[:2]
        scale_factor = max(1.0, min(w / 1280, h / 720))
        
        # Draw refined hand landmarks
        self.mp_drawing.draw_landmarks(
            frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
            landmark_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
                color=(100, 100, 100), thickness=max(1, int(2 * scale_factor)), 
                circle_radius=max(2, int(3 * scale_factor))),
            connection_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
                color=(140, 140, 140), thickness=max(1, int(2 * scale_factor))))
        
        # Enhanced pinch visualization
        thumb_pixel = (int(thumb_tip.x * w), int(thumb_tip.y * h))
        index_pixel = (int(index_tip.x * w), int(index_tip.y * h))
        
        # Dynamic color and thickness based on pinch strength
        intensity = pinch_value / 127.0
        line_color = (
            int(60 + intensity * 160),   # blue component
            int(140 + intensity * 100),  # green component  
            int(140 + intensity * 115)   # red component
        )
        thickness = max(3, int(intensity * 8 * scale_factor))
        
        # Multi-layer pinch line for better visibility
        cv2.line(frame, thumb_pixel, index_pixel, (0, 0, 0), thickness + 2)  # outline
        cv2.line(frame, thumb_pixel, index_pixel, line_color, thickness)
        
        # Enhanced pinch value display
        mid_x = (thumb_pixel[0] + index_pixel[0]) // 2
        mid_y = (thumb_pixel[1] + index_pixel[1]) // 2
        
        # Background circle with better visibility
        circle_radius = max(20, int(25 * scale_factor))
        cv2.circle(frame, (mid_x, mid_y), circle_radius, (0, 0, 0), -1)
        cv2.circle(frame, (mid_x, mid_y), circle_radius, line_color, max(2, int(2 * scale_factor)))
        
        # Pinch value text with better font scaling
        font_scale = 0.6 * scale_factor
        text_thickness = max(1, int(2 * scale_factor))
        cv2.putText(frame, f"{pinch_value}", 
                   (mid_x - int(15 * scale_factor), mid_y + int(8 * scale_factor)), 
                   cv2.FONT_HERSHEY_DUPLEX, font_scale, line_color, text_thickness, cv2.LINE_AA)
        
        # Add control parameter labels near hand landmarks
        wrist = hand_landmarks.landmark[0]
        wrist_pixel = (int(wrist.x * w), int(wrist.y * h))
        
        # Position label (offset from wrist)
        label_x = wrist_pixel[0] + int(30 * scale_factor)
        label_y = wrist_pixel[1] - int(20 * scale_factor)
        
        # Create semi-transparent background for labels
        label_bg_width = int(80 * scale_factor)
        label_bg_height = int(15 * scale_factor)
        
        # Position label background
        cv2.rectangle(frame, 
                     (label_x - 5, label_y - label_bg_height), 
                     (label_x + label_bg_width, label_y + 5), 
                     (0, 0, 0), -1)
        
        # Position parameter label
        cv2.putText(frame, "position xy", 
                   (label_x, label_y), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.4 * scale_factor, 
                   (180, 180, 180), max(1, int(1 * scale_factor)), cv2.LINE_AA)
    
    def print_table(self):
        """Print live table to terminal (backup method)"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(">>> hand midi controller")
        print(f"status: {'active' if self.midi_enabled else 'offline'} | fps: {self.current_fps:.0f}")
        print("")
        print("cc#  parameter     value  |||||||||||||||||||||||||")
        print("-" * 50)
        
        for cc_key, cc_info in self.cc_mappings.items():
            value = self.current_values[cc_key]
            percentage = value / 127.0
            
            # Create bar visualization
            bar_length = 20
            filled = int(bar_length * percentage)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            print(f"{cc_info['cc']:02d}   {cc_info['label']:<12} {value:03d}  {bar}")
        
        print("")
        print("controls: q=quit, v=cycle cameras")
    
    def run(self):
        print("\n>>> exceptional hand midi controller")
        print("optimized for retina displays and professional use")
        
        # Detect available cameras
        available_cameras = []
        for i in range(5):
            test_cap = cv2.VideoCapture(i)
            if test_cap.isOpened():
                available_cameras.append(i)
                test_cap.release()
        
        if not available_cameras:
            print("[!] no cameras detected")
            return
        
        current_camera_idx = 0
        camera_index = available_cameras[current_camera_idx]
        print(f"using camera {camera_index} of {len(available_cameras)} available")
        
        # High-resolution camera setup for retina displays
        cap = cv2.VideoCapture(camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)   # 1080p for crisp quality
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Single exceptional window setup
        window_name = "hand midi controller | exceptional view"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
        
        # Optimize for retina displays - larger initial size
        initial_width = 1600
        initial_height = 1000
        cv2.resizeWindow(window_name, initial_width, initial_height)
        
        # Position window for optimal viewing
        cv2.moveWindow(window_name, 100, 50)
        
        # Setup mouse callback for region selection
        cv2.setMouseCallback(window_name, self.mouse_callback)
        
        print("\ncontrols:")
        print("  q - quit")
        print("  v - cycle cameras")
        print("  t - terminal table")
        print("  f - toggle fullscreen")
        print("  click+drag - select region for X/Y bounds")
        
        fullscreen = False
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    print("[!] camera disconnected")
                    break
                
                self.update_fps()
                
                # PERFORMANCE: Mirror and convert in one operation
                frame = cv2.flip(frame, 1)
                
                # PERFORMANCE: Skip RGB conversion back to BGR, work directly with RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.hands.process(frame_rgb)
                
                # PERFORMANCE: Only convert back to BGR for display at the very end
                # Use frame_rgb for processing, convert only once at end
                
                # PERFORMANCE: Process hands without redundant drawing
                if results.multi_hand_landmarks and results.multi_handedness:
                    for hand_landmarks, handedness in zip(results.multi_hand_landmarks, 
                                                         results.multi_handedness):
                        thumb_tip, index_tip, pinch_value = self.process_hand(
                            hand_landmarks, handedness)
                        
                        # PERFORMANCE: Draw directly on RGB frame
                        self.draw_hand_markers(frame_rgb, hand_landmarks, thumb_tip, index_tip, pinch_value)
                else:
                    # Zero out all MIDI values when no hands detected
                    self.reset_midi_values()
                
                # PERFORMANCE: Convert to BGR only once and apply overlay
                frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                frame = self.draw_table_overlay(frame)
                
                # Display with optimal settings
                cv2.imshow(window_name, frame)
                
                # PERFORMANCE: Non-blocking input check
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('t'):
                    self.print_table()
                elif key == ord('v'):
                    # Cycle cameras
                    if len(available_cameras) > 1:
                        current_camera_idx = (current_camera_idx + 1) % len(available_cameras)
                        camera_index = available_cameras[current_camera_idx]
                        print(f"[+] switching to camera {camera_index}")
                        
                        cap.release()
                        cap = cv2.VideoCapture(camera_index)
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                        cap.set(cv2.CAP_PROP_FPS, 30)
                    else:
                        print("[i] only one camera available")
                elif key == ord('f'):
                    # Toggle fullscreen
                    fullscreen = not fullscreen
                    if fullscreen:
                        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                        print("[+] fullscreen mode")
                    else:
                        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                        cv2.resizeWindow(window_name, initial_width, initial_height)
                        print("[+] windowed mode")
                
        except KeyboardInterrupt:
            print("\n[!] stopped by user")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            if self.midi_enabled and hasattr(self, 'midi_out'):
                self.midi_out.close_port()
                print("[+] midi port closed cleanly")

if __name__ == "__main__":
    controller = HandMIDIController()
    controller.run()