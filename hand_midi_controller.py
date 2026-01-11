#!/usr/bin/env python3
"""
Hand MIDI Controller - Unified Edition
A feature-rich hand tracking MIDI controller using MediaPipe and rtmidi

Features:
- Real-time hand tracking with MediaPipe
- Virtual MIDI device creation
- Multiple UI modes (minimal, cyberpunk, debug)
- Configurable MIDI mappings
- Adjustable sensitivity
- Visual feedback options

Usage:
    python hand_midi_controller.py                    # Default mode
    python hand_midi_controller.py --ui cyberpunk    # Cyberpunk mode
    python hand_midi_controller.py --ui minimal      # Minimal mode
    python hand_midi_controller.py --debug            # Debug mode with extra info
    python hand_midi_controller.py --help            # Show all options
"""

import cv2
import mediapipe as mp
import numpy as np
import math
import time
import argparse
import json
from collections import deque
from dataclasses import dataclass, asdict
from typing import Dict, Tuple, Optional

# Try to import rtmidi for MIDI output
try:
    import rtmidi
    MIDI_AVAILABLE = True
except ImportError:
    MIDI_AVAILABLE = False
    print("⚠️  rtmidi not available - install with: pip install python-rtmidi")


# MIDI Constants
MIDI_MAX_VALUE = 127
MIDI_MIN_VALUE = 0


@dataclass
class Config:
    """Configuration for Hand MIDI Controller"""
    # UI Settings
    ui_mode: str = "cyberpunk"  # minimal, cyberpunk, debug
    show_fps: bool = True
    show_landmarks: bool = True
    show_cc_values: bool = True
    show_meters: bool = True
    window_width: int = 640
    window_height: int = 480
    
    # MIDI Settings
    virtual_port_name: str = "Hand MIDI Controller"
    midi_channel: int = 0
    send_14bit_cc: bool = False  # Use 14-bit MIDI CC for higher resolution
    
    # Hand Tracking Settings
    max_hands: int = 2
    detection_confidence: float = 0.7
    tracking_confidence: float = 0.5
    model_complexity: int = 1  # 0=lite, 1=full
    
    # Smoothing Settings
    position_smoothing: int = 5      # Window size for position smoothing
    gesture_smoothing: int = 8       # Window size for gesture smoothing
    velocity_smoothing: int = 3      # Window size for velocity smoothing
    enable_prediction: bool = True   # Enable motion prediction
    
    # Pinch Control Settings
    pinch_threshold_close: float = 0.02
    pinch_threshold_open: float = 0.12
    pinch_curve: str = "linear"      # linear, exponential, s_curve
    pinch_invert: bool = False       # Invert pinch values
    
    # Palm Settings
    palm_sensitivity: float = 1.0    # Multiplier for palm openness
    palm_curve: str = "linear"       # Response curve
    palm_deadzone: float = 0.05      # Dead zone at center
    
    # Position Settings  
    position_scale_x: float = 1.0    # Scale factor for X movement
    position_scale_y: float = 1.0    # Scale factor for Y movement
    position_deadzone: float = 0.02  # Dead zone at center
    position_invert_x: bool = False  # Invert X axis
    position_invert_y: bool = False  # Invert Y axis
    
    # Position Mapping Area (click-to-draw rectangle)
    use_custom_area: bool = False    # Use custom area instead of full camera
    custom_area_x1: int = 0          # Top-left X
    custom_area_y1: int = 0          # Top-left Y  
    custom_area_x2: int = 640        # Bottom-right X
    custom_area_y2: int = 480        # Bottom-right Y
    
    # Rotation Settings
    rotation_sensitivity: float = 1.0
    rotation_offset: float = 0.0     # Rotation offset in radians
    rotation_range: float = 3.14159  # Full rotation range (pi = 180°)
    
    # Velocity Settings
    velocity_scale: float = 500.0    # Velocity scaling factor (tune for your camera/setup)
    
    # Distance Settings
    max_hand_distance: float = 1.4   # Maximum normalized hand distance (diagonal)
    
    # Gesture Detection Thresholds
    fist_threshold_closed: float = 0.15   # Distance for closed fist
    fist_threshold_open: float = 0.25     # Distance for open hand
    spread_threshold_closed: float = 0.05  # Finger distance when closed
    spread_threshold_open: float = 0.15    # Finger distance when spread
    finger_distance_near: float = 0.02     # Near threshold for finger distances
    finger_distance_far: float = 0.15      # Far threshold for finger distances
    
    # Inter-finger Distance Settings
    thumb_index_enabled: bool = True
    thumb_middle_enabled: bool = False
    thumb_ring_enabled: bool = False
    thumb_pinky_enabled: bool = False
    index_middle_enabled: bool = False
    
    # Advanced Gesture Settings
    fist_detection: bool = False     # Detect closed fist
    pointing_detection: bool = False # Detect pointing gesture
    spread_detection: bool = True    # Detect finger spread
    velocity_tracking: bool = False  # Track hand movement velocity
    hand_distance_tracking: bool = False  # Track distance between hands
    
    # Camera Settings
    camera_index: int = 0
    camera_width: int = 1280        # higher res
    camera_height: int = 720         # 720p
    camera_fps: int = 30
    camera_exposure: int = -1        # Auto exposure if -1
    
    # Performance Settings
    target_fps: int = 30
    skip_frames: int = 0             # Skip N frames between processing
    max_cpu_usage: float = 80.0      # Target max CPU usage %
    
    # Debug Settings
    log_midi_messages: bool = False
    log_hand_data: bool = False
    show_performance_stats: bool = False
    
    # CC Mappings and Color Schemes
    cc_mappings: Dict = None
    color_scheme: str = "default"    # default, warm, cool, neon
    
    def __post_init__(self):
        if self.cc_mappings is None:
            self.cc_mappings = {
                # Basic hand position
                'left_x': {'cc': 1, 'label': 'l_x', 'color': (120, 180, 200), 'enabled': True},
                'left_y': {'cc': 2, 'label': 'l_y', 'color': (120, 200, 150), 'enabled': True},
                'right_x': {'cc': 3, 'label': 'r_x', 'color': (200, 120, 180), 'enabled': True},
                'right_y': {'cc': 4, 'label': 'r_y', 'color': (200, 150, 120), 'enabled': True},
                
                # Pinch gestures
                'left_pinch': {'cc': 5, 'label': 'l_pinch', 'color': (140, 160, 200), 'enabled': True},
                'right_pinch': {'cc': 6, 'label': 'r_pinch', 'color': (200, 160, 140), 'enabled': True},
                
                # Palm openness
                'left_palm': {'cc': 7, 'label': 'l_palm', 'color': (150, 200, 120), 'enabled': True},
                'right_palm': {'cc': 8, 'label': 'r_palm', 'color': (200, 120, 150), 'enabled': True},
                
                # Hand rotation
                'left_rotation': {'cc': 9, 'label': 'l_rot', 'color': (120, 150, 200), 'enabled': True},
                'right_rotation': {'cc': 10, 'label': 'r_rot', 'color': (200, 150, 150), 'enabled': True},
                
                # Additional inter-finger distances
                'left_thumb_middle': {'cc': 11, 'label': 'L_TM_DIST', 'color': (128, 255, 255), 'enabled': False},
                'right_thumb_middle': {'cc': 12, 'label': 'R_TM_DIST', 'color': (255, 128, 255), 'enabled': False},
                'left_thumb_ring': {'cc': 13, 'label': 'L_TR_DIST', 'color': (128, 255, 128), 'enabled': False},
                'right_thumb_ring': {'cc': 14, 'label': 'R_TR_DIST', 'color': (255, 128, 128), 'enabled': False},
                'left_thumb_pinky': {'cc': 15, 'label': 'L_TP_DIST', 'color': (255, 255, 128), 'enabled': False},
                'right_thumb_pinky': {'cc': 16, 'label': 'R_TP_DIST', 'color': (128, 128, 255), 'enabled': False},
                
                # Advanced gestures
                'left_fist': {'cc': 17, 'label': 'L_FIST', 'color': (200, 200, 0), 'enabled': False},
                'right_fist': {'cc': 18, 'label': 'R_FIST', 'color': (200, 0, 200), 'enabled': False},
                'left_spread': {'cc': 19, 'label': 'L_SPREAD', 'color': (0, 200, 200), 'enabled': False},
                'right_spread': {'cc': 20, 'label': 'R_SPREAD', 'color': (200, 100, 100), 'enabled': False},
                
                # Velocity and distance
                'left_velocity': {'cc': 21, 'label': 'L_VEL', 'color': (180, 180, 255), 'enabled': False},
                'right_velocity': {'cc': 22, 'label': 'R_VEL', 'color': (255, 180, 180), 'enabled': False},
                'hand_distance': {'cc': 23, 'label': 'HAND_DIST', 'color': (255, 255, 180), 'enabled': False}
            }
    
    @classmethod
    def create_preset(cls, preset_name: str) -> 'Config':
        """Create a configuration preset for specific use cases"""
        config = cls()
        
        if preset_name == "performance":
            # High sensitivity, all gestures enabled for live performance
            config.ui_mode = "cyberpunk"
            config.pinch_threshold_close = 0.015
            config.pinch_threshold_open = 0.15
            config.position_smoothing = 3  # Less smoothing for responsiveness
            config.gesture_smoothing = 5
            config.palm_sensitivity = 1.5
            config.rotation_sensitivity = 1.2
            
            # Enable extra gestures
            config.thumb_middle_enabled = True
            config.thumb_ring_enabled = True
            config.spread_detection = True
            config.fist_detection = True
            config.velocity_tracking = True
            config.hand_distance_tracking = True
            
            # Enable corresponding CC mappings
            # TODO: Consider making this more maintainable by using feature flags
            # e.g., if config.fist_detection and 'fist' in key
            for key in config.cc_mappings:
                # Use exact matches to avoid false positives
                if key in ['left_thumb_middle', 'right_thumb_middle',
                          'left_thumb_ring', 'right_thumb_ring',
                          'left_spread', 'right_spread',
                          'left_fist', 'right_fist',
                          'left_velocity', 'right_velocity',
                          'hand_distance']:
                    config.cc_mappings[key]['enabled'] = True
                    
        elif preset_name == "studio":
            # Balanced settings for studio recording
            config.ui_mode = "minimal"
            config.position_smoothing = 8  # More smoothing for stability
            config.gesture_smoothing = 10
            config.pinch_threshold_close = 0.025
            config.pinch_threshold_open = 0.10
            config.palm_sensitivity = 0.8
            config.show_landmarks = False  # Clean recording view
            
            # Enable velocity for dynamics but keep it simple
            config.velocity_tracking = True
            config.cc_mappings['left_velocity']['enabled'] = True
            config.cc_mappings['right_velocity']['enabled'] = True
            
        elif preset_name == "precise":
            # Maximum precision with 14-bit MIDI
            config.send_14bit_cc = True
            config.position_smoothing = 15
            config.gesture_smoothing = 12
            config.pinch_threshold_close = 0.01
            config.pinch_threshold_open = 0.08
            config.position_deadzone = 0.01
            config.palm_deadzone = 0.02
            
            # Enable all primary controls with high precision
            config.velocity_tracking = True
            config.hand_distance_tracking = True
            config.cc_mappings['left_velocity']['enabled'] = True
            config.cc_mappings['right_velocity']['enabled'] = True
            config.cc_mappings['hand_distance']['enabled'] = True
            
        elif preset_name == "experimental":
            # All features enabled for experimentation
            config.ui_mode = "debug"
            config.thumb_middle_enabled = True
            config.thumb_ring_enabled = True
            config.thumb_pinky_enabled = True
            config.index_middle_enabled = True
            config.fist_detection = True
            config.pointing_detection = True
            config.spread_detection = True
            config.velocity_tracking = True
            config.hand_distance_tracking = True
            config.log_hand_data = True
            
            # Enable all CC mappings
            for key in config.cc_mappings:
                config.cc_mappings[key]['enabled'] = True
                
        elif preset_name == "minimal":
            # Basic setup with minimal features
            config.ui_mode = "minimal"
            config.show_meters = False
            config.show_landmarks = False
            
            # Only basic gestures
            for key in config.cc_mappings:
                if key not in ['left_x', 'left_y', 'right_x', 'right_y', 'left_pinch', 'right_pinch']:
                    config.cc_mappings[key]['enabled'] = False
                    
        return config
    
    def save(self, filepath: str):
        """Save configuration to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'Config':
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data)


class HandMIDIController:
    """Unified Hand MIDI Controller with multiple UI modes"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Print startup message based on UI mode
        self._print_startup_message()
        
        # Initialize MediaPipe
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=config.max_hands,
            model_complexity=config.model_complexity,
            min_detection_confidence=config.detection_confidence,
            min_tracking_confidence=config.tracking_confidence
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Initialize MIDI
        self.midi_enabled = False
        self.midi_out = None
        self.setup_midi()
        
        # Initialize smoothing
        self.left_hand_history = self._create_history_dict()
        self.right_hand_history = self._create_history_dict()
        
        # Position tracking for velocity and distance
        self.left_hand_pos_history = deque(maxlen=self.config.velocity_smoothing)
        self.right_hand_pos_history = deque(maxlen=self.config.velocity_smoothing)
        self.last_left_pos = None
        self.last_right_pos = None
        self.both_hands_detected = False
        
        # Current CC values for visualization
        self.current_cc_values = {key: 0 for key in self.config.cc_mappings}
        
        # Performance tracking
        self.fps_start_time = time.time()
        self.fps_counter = 0
        self.current_fps = 0
        
        # Mouse interaction for custom area selection
        self.drawing_area = False
        self.area_start_point = None
        self.area_temp_end = None
        
        # UI Colors
        self.colors = {
            'cyberpunk': {
                'primary': (80, 200, 120),     # Subtle green
                'secondary': (160, 160, 160),  # Gray
                'accent': (120, 180, 255),     # Light blue
                'bg': (20, 25, 20)            # Dark background
            },
            'minimal': {
                'primary': (220, 220, 220),    # Light gray
                'secondary': (140, 140, 140),  # Medium gray
                'accent': (100, 180, 100),     # Muted green
                'bg': (25, 25, 25)            # Dark gray
            },
            'debug': {
                'primary': (180, 180, 180),    # Light gray
                'secondary': (140, 140, 140),  # Medium gray
                'accent': (120, 160, 200),     # Light blue
                'bg': (30, 30, 30)            # Dark gray
            }
        }
    
    def _print_startup_message(self):
        """Print startup message based on UI mode"""
        if self.config.ui_mode == "cyberpunk":
            print(">>> hand midi controller")
            print("neural interface active...")
        elif self.config.ui_mode == "minimal":
            print("hand midi controller - minimal mode")
            print("clean interface for focused performance")
        else:  # debug
            print("hand midi controller - debug mode")
            print("verbose output enabled")
        print("mediapipe hand tracking initialized")
    
    def _create_history_dict(self) -> Dict:
        """Create history dictionary for smoothing"""
        return {
            'x': deque(maxlen=self.config.position_smoothing),
            'y': deque(maxlen=self.config.position_smoothing),
            'thumb_index_dist': deque(maxlen=self.config.gesture_smoothing),
            'palm_open': deque(maxlen=self.config.gesture_smoothing),
            'rotation': deque(maxlen=self.config.gesture_smoothing)
        }
    
    def setup_midi(self):
        """Setup MIDI output using rtmidi"""
        if not MIDI_AVAILABLE:
            print("[!] midi output disabled - rtmidi not available")
            return
            
        try:
            self.midi_out = rtmidi.MidiOut()
            
            # List available ports
            print("\navailable midi ports:")
            available_ports = self.midi_out.get_ports()
            for i, port in enumerate(available_ports):
                print(f"  [{i}] {port}")
            
            # Create virtual MIDI port
            self.midi_out.open_virtual_port(self.config.virtual_port_name)
            
            print(f"\n[+] virtual midi device created: '{self.config.virtual_port_name}'")
            print("    this will appear as a midi input device in your daw")
            
            self.midi_enabled = True
            
        except Exception as e:
            print(f"[!] midi setup failed: {e}")
            self.midi_enabled = False
    
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events for area selection"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing_area = True
            self.area_start_point = (x, y)
            self.area_temp_end = (x, y)
            
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing_area:
                self.area_temp_end = (x, y)
                
        elif event == cv2.EVENT_LBUTTONUP:
            if self.drawing_area:
                self.drawing_area = False
                # Set the custom area coordinates
                x1, y1 = self.area_start_point
                x2, y2 = (x, y)
                
                # Ensure proper ordering (top-left to bottom-right)
                self.config.custom_area_x1 = min(x1, x2)
                self.config.custom_area_y1 = min(y1, y2)
                self.config.custom_area_x2 = max(x1, x2)
                self.config.custom_area_y2 = max(y1, y2)
                self.config.use_custom_area = True
                
                # Pre-calculate scaling factors for performance
                self._update_area_scaling()
                
                print(f"[+] custom area set: ({self.config.custom_area_x1}, {self.config.custom_area_y1}) to ({self.config.custom_area_x2}, {self.config.custom_area_y2})")
                print("    hand positions will be mapped relative to this area")
                
                # Clear drawing state
                self.area_start_point = None
                self.area_temp_end = None
    
    def _update_area_scaling(self):
        """Pre-calculate area scaling factors for performance"""
        if self.config.use_custom_area:
            # Convert pixel coordinates to normalized coordinates
            self._area_norm_x1 = self.config.custom_area_x1 / self.config.camera_width
            self._area_norm_y1 = self.config.custom_area_y1 / self.config.camera_height
            area_norm_x2 = self.config.custom_area_x2 / self.config.camera_width
            area_norm_y2 = self.config.custom_area_y2 / self.config.camera_height
            
            # Calculate scaling factors
            area_norm_width = area_norm_x2 - self._area_norm_x1
            area_norm_height = area_norm_y2 - self._area_norm_y1
            
            self._area_scale_x = 1.0 / area_norm_width if area_norm_width > 0 else 1.0
            self._area_scale_y = 1.0 / area_norm_height if area_norm_height > 0 else 1.0
    
    def smooth_value(self, value: float, history: deque) -> float:
        """Apply smoothing using moving average"""
        history.append(value)
        return np.mean(history) if len(history) > 0 else value
    
    def send_midi_cc(self, cc_key: str, value: int):
        """Send MIDI CC message"""
        if not self.midi_enabled:
            return
            
        try:
            cc_info = self.config.cc_mappings[cc_key]
            cc_num = cc_info['cc']
            
            # Clamp value to valid MIDI range
            value = max(MIDI_MIN_VALUE, min(MIDI_MAX_VALUE, int(value)))
            
            # Store for visualization
            self.current_cc_values[cc_key] = value
            
            # Create and send MIDI message
            status_byte = 0xB0 + self.config.midi_channel
            message = [status_byte, cc_num, value]
            self.midi_out.send_message(message)
            
            # Debug output if enabled
            if self.config.ui_mode == "debug":
                print(f"MIDI CC {cc_num}: {value} ({cc_key})")
                
        except Exception as e:
            if self.config.ui_mode == "debug":
                print(f"MIDI send error: {e}")
    
    def calculate_distance(self, point1, point2) -> float:
        """Calculate 3D distance between two landmarks"""
        return math.sqrt(
            (point1.x - point2.x) ** 2 + 
            (point1.y - point2.y) ** 2 + 
            (point1.z - point2.z) ** 2
        )
    
    def calculate_palm_openness(self, hand_landmarks) -> float:
        """Calculate how open the palm is (0-127)"""
        wrist = hand_landmarks.landmark[0]
        
        # Get fingertips and bases
        fingertips = [hand_landmarks.landmark[i] for i in [4, 8, 12, 16, 20]]
        finger_bases = [hand_landmarks.landmark[i] for i in [5, 9, 13, 17]]
        
        # Calculate average distances
        tip_distances = [self.calculate_distance(wrist, tip) for tip in fingertips]
        base_distances = [self.calculate_distance(wrist, base) for base in finger_bases]
        
        avg_tip_distance = np.mean(tip_distances)
        avg_base_distance = np.mean(base_distances)
        
        if avg_base_distance > 0:
            openness = avg_tip_distance / avg_base_distance
            # Normalize to 0-127 range
            normalized = max(0, min(127, int((openness - 1.2) * 159)))
            return normalized
        return 64
    
    def calculate_hand_rotation(self, hand_landmarks) -> float:
        """Calculate hand rotation (0-127)"""
        wrist = hand_landmarks.landmark[0]
        middle_base = hand_landmarks.landmark[9]
        
        dx = middle_base.x - wrist.x
        dy = middle_base.y - wrist.y
        angle = math.atan2(dy, dx)
        
        # Normalize to 0-127
        normalized = int((angle + math.pi) / (2 * math.pi) * 127)
        return max(0, min(127, normalized))
    
    def calculate_pinch_value(self, thumb_index_dist: float) -> int:
        """Calculate pinch MIDI value with configurable thresholds"""
        if thumb_index_dist <= self.config.pinch_threshold_close:
            return 127
        elif thumb_index_dist >= self.config.pinch_threshold_open:
            return 0
        else:
            # Linear interpolation
            range_size = self.config.pinch_threshold_open - self.config.pinch_threshold_close
            normalized = (thumb_index_dist - self.config.pinch_threshold_close) / range_size
            return max(0, min(127, int(127 * (1.0 - normalized))))
    
    def calculate_velocity(self, current_pos: Tuple[float, float], 
                          last_pos: Optional[Tuple[float, float]]) -> int:
        """Calculate hand movement velocity (0-127)"""
        if last_pos is None:
            return 0
        
        # Calculate distance moved
        dx = current_pos[0] - last_pos[0]
        dy = current_pos[1] - last_pos[1]
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Scale to MIDI range using configured scale factor
        velocity = min(127, int(distance * self.config.velocity_scale))
        return velocity
    
    def calculate_hand_distance(self, left_pos: Optional[Tuple[float, float]], 
                                right_pos: Optional[Tuple[float, float]]) -> int:
        """Calculate distance between both hands (0-127)"""
        if left_pos is None or right_pos is None:
            return 0
        
        # Calculate 2D distance between hands
        dx = left_pos[0] - right_pos[0]
        dy = left_pos[1] - right_pos[1]
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Normalize to MIDI range using configured max distance
        normalized = min(1.0, distance / self.config.max_hand_distance)
        return int(normalized * 127)
    
    def calculate_fist(self, hand_landmarks) -> int:
        """Detect closed fist gesture (0=open, 127=closed)"""
        # TODO: Consider extracting threshold validation to helper method
        # to reduce code duplication across gesture calculations
        wrist = hand_landmarks.landmark[0]
        
        # Get all fingertips
        fingertips = [hand_landmarks.landmark[i] for i in [4, 8, 12, 16, 20]]
        
        # Calculate average distance from wrist to fingertips
        distances = [self.calculate_distance(wrist, tip) for tip in fingertips]
        avg_distance = np.mean(distances)
        
        # Use configurable thresholds
        if avg_distance < self.config.fist_threshold_closed:  # Very close = fist
            return MIDI_MAX_VALUE
        elif avg_distance > self.config.fist_threshold_open:  # Far = open hand
            return MIDI_MIN_VALUE
        else:
            # Linear interpolation with safety check
            threshold_range = self.config.fist_threshold_open - self.config.fist_threshold_closed
            if threshold_range <= 0:
                return MIDI_MIN_VALUE  # Invalid config, default to open
            normalized = (self.config.fist_threshold_open - avg_distance) / threshold_range
            return max(MIDI_MIN_VALUE, min(MIDI_MAX_VALUE, int(normalized * MIDI_MAX_VALUE)))
    
    def calculate_spread(self, hand_landmarks) -> int:
        """Detect finger spread (0=closed, 127=spread)"""
        # Get fingertips
        thumb = hand_landmarks.landmark[4]
        index = hand_landmarks.landmark[8]
        middle = hand_landmarks.landmark[12]
        ring = hand_landmarks.landmark[16]
        pinky = hand_landmarks.landmark[20]
        
        # Calculate distances between adjacent fingers
        distances = [
            self.calculate_distance(thumb, index),
            self.calculate_distance(index, middle),
            self.calculate_distance(middle, ring),
            self.calculate_distance(ring, pinky)
        ]
        
        avg_spread = np.mean(distances)
        
        # Use configurable thresholds
        if avg_spread < self.config.spread_threshold_closed:  # Fingers together
            return MIDI_MIN_VALUE
        elif avg_spread > self.config.spread_threshold_open:  # Fingers spread
            return MIDI_MAX_VALUE
        else:
            # Linear interpolation with safety check
            threshold_range = self.config.spread_threshold_open - self.config.spread_threshold_closed
            if threshold_range <= 0:
                return MIDI_MIN_VALUE  # Invalid config, default to closed
            normalized = (avg_spread - self.config.spread_threshold_closed) / threshold_range
            return max(MIDI_MIN_VALUE, min(MIDI_MAX_VALUE, int(normalized * MIDI_MAX_VALUE)))
    
    def calculate_thumb_finger_distance(self, hand_landmarks, finger_tip_index: int) -> int:
        """Calculate distance between thumb and specified finger tip"""
        thumb_tip = hand_landmarks.landmark[4]
        finger_tip = hand_landmarks.landmark[finger_tip_index]
        distance = self.calculate_distance(thumb_tip, finger_tip)
        
        # Use configurable thresholds
        if distance >= self.config.finger_distance_far:
            return MIDI_MIN_VALUE
        elif distance <= self.config.finger_distance_near:
            return MIDI_MAX_VALUE
        else:
            # Linear interpolation with safety check
            threshold_range = self.config.finger_distance_far - self.config.finger_distance_near
            if threshold_range <= 0:
                return MIDI_MIN_VALUE  # Invalid config, default to far
            normalized = (self.config.finger_distance_far - distance) / threshold_range
            return max(MIDI_MIN_VALUE, min(MIDI_MAX_VALUE, int(normalized * MIDI_MAX_VALUE)))
    
    def process_hand(self, hand_landmarks, handedness) -> Tuple:
        """Process hand landmarks and send MIDI data"""
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
        
        # Map positions relative to custom area if enabled
        if self.config.use_custom_area and hasattr(self, '_area_scale_x'):
            # Use pre-calculated scaling factors for better performance
            rel_x = (palm_x - self._area_norm_x1) * self._area_scale_x
            rel_y = (palm_y - self._area_norm_y1) * self._area_scale_y
            
            # Clamp to 0-1 range
            rel_x = max(0, min(1, rel_x))
            rel_y = max(0, min(1, rel_y))
            
            midi_x = rel_x * 127
            midi_y = (1 - rel_y) * 127  # Invert Y axis
        else:
            # Standard full-camera mapping
            midi_x = palm_x * 127
            midi_y = (1 - palm_y) * 127
        
        # Smooth values
        smoothed_x = self.smooth_value(midi_x, history['x'])
        smoothed_y = self.smooth_value(midi_y, history['y'])
        smoothed_dist = self.smooth_value(thumb_index_dist, history['thumb_index_dist'])
        smoothed_palm = self.smooth_value(palm_open, history['palm_open'])
        smoothed_rotation = self.smooth_value(rotation, history['rotation'])
        
        # Calculate pinch value
        pinch_midi = self.calculate_pinch_value(smoothed_dist)
        
        # Send basic MIDI messages
        self.send_midi_cc(f'{cc_prefix}_x', int(smoothed_x))
        self.send_midi_cc(f'{cc_prefix}_y', int(smoothed_y))
        self.send_midi_cc(f'{cc_prefix}_pinch', pinch_midi)
        self.send_midi_cc(f'{cc_prefix}_palm', int(smoothed_palm))
        self.send_midi_cc(f'{cc_prefix}_rotation', int(smoothed_rotation))
        
        # Calculate and send advanced gestures if enabled
        if self.config.fist_detection:
            fist_value = self.calculate_fist(hand_landmarks)
            self.send_midi_cc(f'{cc_prefix}_fist', fist_value)
        
        if self.config.spread_detection:
            spread_value = self.calculate_spread(hand_landmarks)
            self.send_midi_cc(f'{cc_prefix}_spread', spread_value)
        
        # Calculate additional finger distances if enabled
        if self.config.thumb_middle_enabled:
            thumb_middle_dist = self.calculate_thumb_finger_distance(hand_landmarks, 12)
            self.send_midi_cc(f'{cc_prefix}_thumb_middle', thumb_middle_dist)
        
        if self.config.thumb_ring_enabled:
            thumb_ring_dist = self.calculate_thumb_finger_distance(hand_landmarks, 16)
            self.send_midi_cc(f'{cc_prefix}_thumb_ring', thumb_ring_dist)
        
        if self.config.thumb_pinky_enabled:
            thumb_pinky_dist = self.calculate_thumb_finger_distance(hand_landmarks, 20)
            self.send_midi_cc(f'{cc_prefix}_thumb_pinky', thumb_pinky_dist)
        
        # Track velocity if enabled
        if self.config.velocity_tracking:
            current_pos = (palm_x, palm_y)
            last_pos = self.last_left_pos if hand_type == "Left" else self.last_right_pos
            velocity = self.calculate_velocity(current_pos, last_pos)
            self.send_midi_cc(f'{cc_prefix}_velocity', velocity)
        
        # Always store position for next frame (used by both velocity and distance calculation)
        if hand_type == "Left":
            self.last_left_pos = (palm_x, palm_y)
        else:
            self.last_right_pos = (palm_x, palm_y)
        
        return palm_x, palm_y, thumb_tip, index_tip, pinch_midi
    
    def update_fps(self):
        """Update FPS counter"""
        self.fps_counter += 1
        current_time = time.time()
        
        if current_time - self.fps_start_time >= 1.0:
            self.current_fps = self.fps_counter / (current_time - self.fps_start_time)
            self.fps_counter = 0
            self.fps_start_time = current_time
    
    def draw_minimal_ui(self, frame):
        """Draw minimal UI overlay"""
        h, w = frame.shape[:2]
        colors = self.colors['minimal']
        
        # FPS counter if enabled
        if self.config.show_fps:
            cv2.putText(frame, f"fps: {self.current_fps:.0f}", (10, h-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
        
        # Always show CC mappings for easy reference
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Left side - left hand CCs
        y_offset = 30
        cv2.putText(frame, "[ left hand ]", (10, y_offset), font, 0.5, (200, 200, 200), 1)
        y_offset += 25
        
        left_ccs = ['left_x', 'left_y', 'left_pinch', 'left_palm', 'left_rotation']
        for cc_key in left_ccs:
            cc_info = self.config.cc_mappings[cc_key]
            value = int(self.current_cc_values.get(cc_key, 0))
            # Show CC number prominently
            text = f"cc{cc_info['cc']:02d}: {value:03d}"
            color = (255, 255, 255) if value > 0 else (80, 80, 80)
            cv2.putText(frame, text, (10, y_offset), font, 0.6, color, 1)
            # Small label
            cv2.putText(frame, f" {cc_info['label'].lower()}", (90, y_offset), font, 0.4, (150, 150, 150), 1)
            y_offset += 22
        
        # Right side - right hand CCs
        y_offset = 30
        cv2.putText(frame, "[ right hand ]", (w-150, y_offset), font, 0.5, (200, 200, 200), 1)
        y_offset += 25
        
        right_ccs = ['right_x', 'right_y', 'right_pinch', 'right_palm', 'right_rotation']
        for cc_key in right_ccs:
            cc_info = self.config.cc_mappings[cc_key]
            value = int(self.current_cc_values.get(cc_key, 0))
            # Show CC number prominently
            text = f"cc{cc_info['cc']:02d}: {value:03d}"
            color = (255, 255, 255) if value > 0 else (80, 80, 80)
            cv2.putText(frame, text, (w-150, y_offset), font, 0.6, color, 1)
            # Small label
            cv2.putText(frame, f" {cc_info['label'].lower()}", (w-70, y_offset), font, 0.4, (150, 150, 150), 1)
            y_offset += 22
        
        # MIDI status indicator
        midi_status = "midi: on" if self.midi_enabled else "midi: off"
        status_color = (0, 255, 0) if self.midi_enabled else (0, 0, 255)
        cv2.putText(frame, midi_status, (w//2 - 30, h-10), font, 0.5, status_color, 1)
        
        return frame
    
    def draw_cyberpunk_ui(self, frame):
        """Draw cyberpunk-style UI overlay"""
        h, w = frame.shape[:2]
        colors = self.colors['cyberpunk']
        
        # Create overlay
        overlay = frame.copy()
        
        # Header
        header_height = 80
        cv2.rectangle(overlay, (0, 0), (w, header_height), colors['bg'], -1)
        cv2.rectangle(overlay, (0, 0), (w, header_height), colors['primary'], 2)
        
        # Title
        title = "hand midi controller"
        font = cv2.FONT_HERSHEY_DUPLEX
        text_size = cv2.getTextSize(title, font, 0.8, 2)[0]
        text_x = (w - text_size[0]) // 2
        cv2.putText(overlay, title, (text_x, 35), font, 0.8, colors['primary'], 2, cv2.LINE_AA)
        
        # Status
        status = "midi: active" if self.midi_enabled else "midi: offline"
        status_color = colors['primary'] if self.midi_enabled else (180, 100, 100)
        cv2.putText(overlay, status, (20, 60), font, 0.6, status_color, 1, cv2.LINE_AA)
        
        # FPS
        if self.config.show_fps:
            cv2.putText(overlay, f"fps: {self.current_fps:.1f}", (w - 100, 60), 
                       font, 0.6, colors['accent'], 1, cv2.LINE_AA)
        
        # CC Meters
        if self.config.show_meters:
            meter_x = w - 400  # more space from edge
            meter_y = header_height + 20
            meter_width = 350  # wider meters
            meter_height = 30  # taller
            
            # only show enabled CCs to save space
            enabled_ccs = {k: v for k, v in self.config.cc_mappings.items() if v.get('enabled', True)}
            
            for cc_key, cc_info in enabled_ccs.items():
                value = self.current_cc_values.get(cc_key, 0)
                percentage = value / 127.0
                
                # Background
                cv2.rectangle(overlay, (meter_x, meter_y), 
                             (meter_x + meter_width, meter_y + meter_height), 
                             (0, 30, 0), -1)
                cv2.rectangle(overlay, (meter_x, meter_y), 
                             (meter_x + meter_width, meter_y + meter_height), 
                             cc_info['color'], 1)
                
                # Value bar
                bar_width = int(meter_width * percentage)
                if bar_width > 0:
                    cv2.rectangle(overlay, (meter_x + 2, meter_y + 2), 
                                 (meter_x + bar_width - 2, meter_y + meter_height - 2), 
                                 cc_info['color'], -1)
                
                # CC number (big and clear)
                cc_text = f"cc{cc_info['cc']:02d}"
                cv2.putText(overlay, cc_text, (meter_x - 70, meter_y + 22), 
                           cv2.FONT_HERSHEY_DUPLEX, 0.7, cc_info['color'], 2, cv2.LINE_AA)
                
                # Value
                value_text = f"{value:03d} ({percentage:.0%})"
                cv2.putText(overlay, value_text, (meter_x + 10, meter_y + 22), 
                           cv2.FONT_HERSHEY_DUPLEX, 0.5, (220, 220, 220), 1, cv2.LINE_AA)
                
                meter_y += meter_height + 2  # tighter spacing
        
        # Blend overlay
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        return frame
    
    def draw_debug_ui(self, frame):
        """Draw debug UI with extra information"""
        h, w = frame.shape[:2]
        colors = self.colors['debug']
        
        # Create semi-transparent overlay for text background
        overlay = np.zeros_like(frame)
        
        # Debug info panel
        panel_width = 300
        cv2.rectangle(overlay, (0, 0), (panel_width, h), colors['bg'], -1)
        
        # Text info
        y_offset = 30
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # System info
        cv2.putText(overlay, "=== SYSTEM ===", (10, y_offset), font, 0.6, colors['primary'], 1)
        y_offset += 25
        cv2.putText(overlay, f"FPS: {self.current_fps:.1f}", (10, y_offset), font, 0.5, colors['secondary'], 1)
        y_offset += 20
        cv2.putText(overlay, f"MIDI: {'ON' if self.midi_enabled else 'OFF'}", (10, y_offset), font, 0.5, colors['secondary'], 1)
        y_offset += 30
        
        # CC Values
        cv2.putText(overlay, "=== midi cc ===", (10, y_offset), font, 0.6, colors['primary'], 1)
        y_offset += 25
        
        for cc_key, value in self.current_cc_values.items():
            cc_info = self.config.cc_mappings[cc_key]
            color = cc_info['color'] if value > 0 else colors['secondary']
            text = f"cc{cc_info['cc']:02d} {cc_info['label'].lower()}: {value:03d}"
            cv2.putText(overlay, text, (10, y_offset), font, 0.4, color, 1)
            y_offset += 18
        
        y_offset += 10
        
        # Config info
        cv2.putText(overlay, "=== config ===", (10, y_offset), font, 0.6, colors['primary'], 1)
        y_offset += 25
        cv2.putText(overlay, f"pinch: {self.config.pinch_threshold_close:.3f}-{self.config.pinch_threshold_open:.3f}", 
                   (10, y_offset), font, 0.4, colors['secondary'], 1)
        y_offset += 18
        cv2.putText(overlay, f"smooth: pos={self.config.position_smoothing} gest={self.config.gesture_smoothing}", 
                   (10, y_offset), font, 0.4, colors['secondary'], 1)
        y_offset += 18
        
        # Feature status
        features = []
        if self.config.velocity_tracking:
            features.append("velocity")
        if self.config.hand_distance_tracking:
            features.append("distance")
        if self.config.fist_detection:
            features.append("fist")
        if self.config.spread_detection:
            features.append("spread")
        
        if features:
            cv2.putText(overlay, f"features: {', '.join(features)}", 
                       (10, y_offset), font, 0.4, colors['accent'], 1)
            y_offset += 18
        
        # Blend overlay
        cv2.addWeighted(overlay, 0.7, frame, 1.0, 0, frame)
        
        return frame
    
    def draw_custom_area_overlay(self, frame):
        """Draw custom area selection overlay"""
        # Draw existing custom area if set
        if self.config.use_custom_area:
            x1, y1 = self.config.custom_area_x1, self.config.custom_area_y1
            x2, y2 = self.config.custom_area_x2, self.config.custom_area_y2
            
            # Draw rectangle outline
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw semi-transparent overlay outside the area
            overlay = frame.copy()
            # Darken areas outside the custom area
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], y1), (0, 0, 0), -1)  # Top
            cv2.rectangle(overlay, (0, y2), (frame.shape[1], frame.shape[0]), (0, 0, 0), -1)  # Bottom
            cv2.rectangle(overlay, (0, y1), (x1, y2), (0, 0, 0), -1)  # Left
            cv2.rectangle(overlay, (x2, y1), (frame.shape[1], y2), (0, 0, 0), -1)  # Right
            
            cv2.addWeighted(frame, 0.7, overlay, 0.3, 0, frame)
            
            # Add label
            cv2.putText(frame, "custom mapping area", (x1 + 5, y1 + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
        # Draw temporary rectangle while drawing
        if self.drawing_area and self.area_start_point and self.area_temp_end:
            x1, y1 = self.area_start_point
            x2, y2 = self.area_temp_end
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
            cv2.putText(frame, "drawing area...", (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # Show instructions
        if not self.config.use_custom_area and not self.drawing_area:
            cv2.putText(frame, "click and drag to set custom mapping area", 
                       (10, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        elif self.config.use_custom_area:
            cv2.putText(frame, "press 'c' to clear custom area", 
                       (10, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def draw_ui(self, frame):
        """Draw UI based on current mode"""
        if self.config.ui_mode == "minimal":
            frame = self.draw_minimal_ui(frame)
        elif self.config.ui_mode == "cyberpunk":
            frame = self.draw_cyberpunk_ui(frame)
        elif self.config.ui_mode == "debug":
            frame = self.draw_debug_ui(frame)
        
        # Always draw custom area overlay on top
        self.draw_custom_area_overlay(frame)
        
        # Draw config status bar at bottom
        self.draw_config_status(frame)
        
        return frame
    
    def draw_config_status(self, frame):
        """Draw configuration status bar at bottom of screen"""
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - 25), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Configuration info
        status_text = f"smooth:{self.config.position_smoothing}/{self.config.gesture_smoothing} | pinch:{self.config.pinch_threshold_open:.2f}"
        
        # Add active features
        active_features = []
        if self.config.velocity_tracking:
            active_features.append("vel")
        if self.config.hand_distance_tracking:
            active_features.append("dist")
        if self.config.fist_detection:
            active_features.append("fist")
        if self.config.spread_detection:
            active_features.append("sprd")
        
        if active_features:
            status_text += f" | features: {','.join(active_features)}"
        
        cv2.putText(frame, status_text, (10, h - 8), font, 0.4, (200, 200, 200), 1)
    
    def draw_hand_visualization(self, frame, hand_landmarks, palm_x, palm_y, 
                               thumb_tip, index_tip, pinch_value):
        """Draw hand visualization elements"""
        h, w = frame.shape[:2]
        
        # Draw pinch visualization
        thumb_pixel = (int(thumb_tip.x * w), int(thumb_tip.y * h))
        index_pixel = (int(index_tip.x * w), int(index_tip.y * h))
        
        # Color based on UI mode and pinch strength
        if self.config.ui_mode == "cyberpunk":
            pinch_intensity = pinch_value / 127.0
            line_color = (int(255 * pinch_intensity), int(255 * (1 - pinch_intensity)), 255)
            
            # Glow effect
            for thickness in [8, 6, 4, 2]:
                cv2.line(frame, thumb_pixel, index_pixel, line_color, thickness)
        else:
            # Simple line for minimal/debug modes
            line_color = (0, int(pinch_value * 2), 255 - int(pinch_value * 2))
            cv2.line(frame, thumb_pixel, index_pixel, line_color, 3)
        
        # Pinch value text
        mid_x = (thumb_pixel[0] + index_pixel[0]) // 2
        mid_y = (thumb_pixel[1] + index_pixel[1]) // 2
        
        if self.config.show_cc_values:
            # Background for readability
            cv2.rectangle(frame, (mid_x - 25, mid_y - 15), (mid_x + 25, mid_y + 5), (0, 0, 0), -1)
            cv2.putText(frame, f"{pinch_value:03d}", (mid_x - 20, mid_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, line_color, 1)
    
    def run(self):
        """Main application loop"""
        print(f"\n>>> starting hand midi controller")
        print(f"ui mode: {self.config.ui_mode}")
        print("controls:")
        print("  'q' - quit")
        print("  'm' - cycle ui modes")
        print("  's' - save current config")
        print("  'c' - clear custom mapping area")
        print("  'v' - cycle video devices")
        print("  '1-5' - load preset (1=performance, 2=studio, 3=precise, 4=experimental, 5=minimal)")
        print("  '+/-' - adjust position smoothing")
        print("  '[/]' - adjust gesture smoothing")
        print("  '{/}' - adjust pinch sensitivity")
        print("  'click and drag' - set custom mapping area")
        
        # Check available cameras
        print("\ndetecting available cameras...")
        available_cameras = []
        for i in range(5):  # Check first 5 indices
            test_cap = cv2.VideoCapture(i)
            if test_cap.isOpened():
                available_cameras.append(i)
                test_cap.release()
        
        if available_cameras:
            print(f"found {len(available_cameras)} camera(s): {available_cameras}")
        else:
            print("[!] no cameras detected")
            return
        
        # Initialize camera
        print(f"using camera index: {self.config.camera_index}")
        cap = cv2.VideoCapture(self.config.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.camera_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.camera_height)
        
        # Set up mouse callback for area selection
        window_name = f"Hand MIDI Controller - {self.config.ui_mode.title()} Mode"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)  # resizable window
        cv2.resizeWindow(window_name, 1400, 900)  # bigger default size
        cv2.setMouseCallback(window_name, self.mouse_callback)
        
        ui_modes = ["minimal", "cyberpunk", "debug"]
        current_mode_index = ui_modes.index(self.config.ui_mode)
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Update FPS
                self.update_fps()
                
                # Flip for mirror effect
                frame = cv2.flip(frame, 1)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Process with MediaPipe
                results = self.hands.process(frame_rgb)
                
                # Convert back to BGR
                frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                
                # Process hands
                if results.multi_hand_landmarks and results.multi_handedness:
                    for hand_landmarks, handedness in zip(results.multi_hand_landmarks, 
                                                         results.multi_handedness):
                        # Draw landmarks if enabled
                        if self.config.show_landmarks:
                            self.mp_drawing.draw_landmarks(
                                frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                                self.mp_drawing_styles.get_default_hand_connections_style())
                        
                        # Process hand data
                        palm_x, palm_y, thumb_tip, index_tip, pinch_value = self.process_hand(
                            hand_landmarks, handedness)
                        
                        # Draw visualization
                        self.draw_hand_visualization(frame, hand_landmarks, palm_x, palm_y,
                                                   thumb_tip, index_tip, pinch_value)
                    
                    # Calculate hand distance if both hands detected and enabled
                    if self.config.hand_distance_tracking and self.last_left_pos and self.last_right_pos:
                        hand_distance = self.calculate_hand_distance(self.last_left_pos, self.last_right_pos)
                        self.send_midi_cc('hand_distance', hand_distance)
                
                # Draw UI
                frame = self.draw_ui(frame)
                
                # Show frame
                window_name = f"Hand MIDI Controller - {self.config.ui_mode.title()} Mode"
                cv2.imshow(window_name, frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('m'):
                    # Cycle UI modes
                    current_mode_index = (current_mode_index + 1) % len(ui_modes)
                    self.config.ui_mode = ui_modes[current_mode_index]
                    print(f"[+] switched to {self.config.ui_mode} mode")
                elif key == ord('s'):
                    # Save config
                    config_file = "hand_midi_config.json"
                    self.config.save(config_file)
                    print(f"[+] config saved to {config_file}")
                elif key == ord('c'):
                    # Clear custom area
                    if self.config.use_custom_area:
                        self.config.use_custom_area = False
                        # Clear scaling factors
                        if hasattr(self, '_area_scale_x'):
                            delattr(self, '_area_scale_x')
                        print("[+] custom area cleared - using full camera view")
                    else:
                        print("[i] no custom area set")
                elif key == ord('v'):
                    # Cycle video devices
                    if len(available_cameras) > 1:
                        current_camera_idx = available_cameras.index(self.config.camera_index)
                        next_camera_idx = (current_camera_idx + 1) % len(available_cameras)
                        self.config.camera_index = available_cameras[next_camera_idx]
                        
                        # Reinitialize camera
                        cap.release()
                        cap = cv2.VideoCapture(self.config.camera_index)
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.camera_width)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.camera_height)
                        
                        print(f"[+] switched to camera {self.config.camera_index}")
                    else:
                        print("[i] only one camera available")
                elif key == ord('1'):
                    # Load performance preset
                    self.config = Config.create_preset("performance")
                    print("[+] loaded PERFORMANCE preset - high sensitivity, all gestures enabled")
                elif key == ord('2'):
                    # Load studio preset
                    self.config = Config.create_preset("studio")
                    print("[+] loaded STUDIO preset - balanced, smooth for recording")
                elif key == ord('3'):
                    # Load precise preset
                    self.config = Config.create_preset("precise")
                    print("[+] loaded PRECISE preset - 14-bit MIDI, maximum smoothing")
                elif key == ord('4'):
                    # Load experimental preset
                    self.config = Config.create_preset("experimental")
                    print("[+] loaded EXPERIMENTAL preset - all features enabled")
                elif key == ord('5'):
                    # Load minimal preset
                    self.config = Config.create_preset("minimal")
                    print("[+] loaded MINIMAL preset - basic controls only")
                elif key == ord('+') or key == ord('='):
                    # Increase position smoothing
                    self.config.position_smoothing = min(20, self.config.position_smoothing + 1)
                    print(f"[+] position smoothing: {self.config.position_smoothing}")
                elif key == ord('-') or key == ord('_'):
                    # Decrease position smoothing
                    self.config.position_smoothing = max(1, self.config.position_smoothing - 1)
                    print(f"[-] position smoothing: {self.config.position_smoothing}")
                elif key == ord('['):
                    # Decrease gesture smoothing
                    self.config.gesture_smoothing = max(1, self.config.gesture_smoothing - 1)
                    print(f"[-] gesture smoothing: {self.config.gesture_smoothing}")
                elif key == ord(']'):
                    # Increase gesture smoothing
                    self.config.gesture_smoothing = min(20, self.config.gesture_smoothing + 1)
                    print(f"[+] gesture smoothing: {self.config.gesture_smoothing}")
                elif key == ord('{'):
                    # Decrease pinch open threshold (more sensitive)
                    self.config.pinch_threshold_open = max(0.05, self.config.pinch_threshold_open - 0.01)
                    print(f"[+] pinch more sensitive: open={self.config.pinch_threshold_open:.3f}")
                elif key == ord('}'):
                    # Increase pinch open threshold (less sensitive)
                    self.config.pinch_threshold_open = min(0.20, self.config.pinch_threshold_open + 0.01)
                    print(f"[-] pinch less sensitive: open={self.config.pinch_threshold_open:.3f}")
                    
        except KeyboardInterrupt:
            print("\n[!] stopped by user")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            if self.midi_out:
                self.midi_out.close_port()
                print("[+] midi port closed")


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Hand MIDI Controller - Control MIDI with hand gestures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run with default settings
  %(prog)s --ui minimal              # Run with minimal UI
  %(prog)s --ui cyberpunk            # Run with cyberpunk UI
  %(prog)s --debug                   # Run in debug mode
  %(prog)s --config my_config.json   # Load custom config
  %(prog)s --pinch-min 0.01 --pinch-max 0.15  # Adjust pinch sensitivity
        """
    )
    
    parser.add_argument('--ui', choices=['minimal', 'cyberpunk', 'debug'],
                        default='cyberpunk', help='UI mode')
    parser.add_argument('--debug', action='store_true', 
                        help='Enable debug mode (overrides --ui)')
    parser.add_argument('--config', type=str, 
                        help='Load configuration from JSON file')
    parser.add_argument('--save-config', type=str, 
                        help='Save current configuration to JSON file')
    parser.add_argument('--no-landmarks', action='store_true',
                        help='Disable hand landmark visualization')
    parser.add_argument('--no-meters', action='store_true',
                        help='Disable CC meter display')
    parser.add_argument('--no-fps', action='store_true',
                        help='Disable FPS counter')
    parser.add_argument('--camera', type=int, default=0,
                        help='Camera index (default: 0)')
    parser.add_argument('--width', type=int, default=640,
                        help='Camera width (default: 640)')
    parser.add_argument('--height', type=int, default=480,
                        help='Camera height (default: 480)')
    parser.add_argument('--smoothing', type=int, default=5,
                        help='Smoothing window size (default: 5)')
    parser.add_argument('--pinch-min', type=float, default=0.02,
                        help='Minimum pinch threshold (default: 0.02)')
    parser.add_argument('--pinch-max', type=float, default=0.12,
                        help='Maximum pinch threshold (default: 0.12)')
    parser.add_argument('--midi-channel', type=int, default=0,
                        help='MIDI channel 0-15 (default: 0)')
    parser.add_argument('--port-name', type=str, default='Hand MIDI Controller',
                        help='Virtual MIDI port name')
    
    args = parser.parse_args()
    
    # Create or load config
    if args.config:
        config = Config.load(args.config)
        print(f"Loaded config from {args.config}")
    else:
        config = Config()
    
    # Apply command line arguments
    if args.debug:
        config.ui_mode = "debug"
    else:
        config.ui_mode = args.ui
    
    config.show_landmarks = not args.no_landmarks
    config.show_meters = not args.no_meters
    config.show_fps = not args.no_fps
    config.camera_index = args.camera
    config.camera_width = args.width
    config.camera_height = args.height
    config.smoothing_window = args.smoothing
    config.pinch_threshold_close = args.pinch_min
    config.pinch_threshold_open = args.pinch_max
    config.midi_channel = args.midi_channel
    config.virtual_port_name = args.port_name
    
    # Save config if requested
    if args.save_config:
        config.save(args.save_config)
        print(f"Config saved to {args.save_config}")
        return
    
    # Check dependencies
    if not MIDI_AVAILABLE:
        print("\n⚠️  WARNING: rtmidi not installed - MIDI output will be disabled")
        print("Install with: pip install python-rtmidi")
        response = input("Continue without MIDI? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Run the controller
    controller = HandMIDIController(config)
    controller.run()


if __name__ == "__main__":
    main()