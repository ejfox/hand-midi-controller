#!/usr/bin/env python3
"""
Hand MIDI Controller - Professional Edition
==========================================

A high-performance, real-time hand tracking MIDI controller using MediaPipe.
Optimized for low latency, retina displays, and professional music production.

Features:
- Dual hand tracking with 6 parameters per hand
- Click-drag region selection for custom X/Y bounds
- Zero-latency MIDI output via virtual MIDI device
- Retina-optimized visualization with cyberpunk aesthetics
- Performance optimized for 30+ FPS operation

Author: EJ Fox
License: MIT
Version: 2.0.0

Requirements:
- Python 3.8+
- OpenCV 4.5+
- MediaPipe 0.10+
- python-rtmidi 1.5+
- numpy 1.21+
"""

import cv2
import mediapipe as mp
import numpy as np
import os
import sys
import time
from collections import deque
from typing import Optional, Tuple, Dict, List
import logging

try:
    import rtmidi
except ImportError:
    print("[ERROR] python-rtmidi not installed. Run: pip install python-rtmidi")
    sys.exit(1)

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# MediaPipe Performance Settings
MP_MODEL_COMPLEXITY = 0  # 0=Lite, 1=Full, 2=Heavy
MP_MIN_DETECTION_CONFIDENCE = 0.5  # Lower = faster but less accurate
MP_MIN_TRACKING_CONFIDENCE = 0.3   # Lower = faster tracking
MP_MAX_HANDS = 2

# Camera Settings
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080
CAMERA_FPS = 30

# MIDI Configuration
MIDI_DEVICE_NAME = "HandMIDI Virtual"
MIDI_CHANNEL = 0  # MIDI channel (0-15)

# Smoothing and Processing
SMOOTHING_WINDOW = 3  # Frames to average for smoothing
PINCH_THRESHOLD_CLOSE = 0.02  # Distance for pinch detection
PINCH_THRESHOLD_OPEN = 0.12   # Distance for pinch release

# UI Configuration
UI_SCALE_BASE = 1280  # Base resolution for UI scaling
OVERLAY_ALPHA = 0.3   # Overlay transparency (0=invisible, 1=opaque)
TABLE_PADDING = 20    # Padding for UI table
FPS_UPDATE_INTERVAL = 1.0  # Seconds between FPS updates

# Color Scheme (B, G, R format for OpenCV)
COLOR_ACCENT = (255, 255, 0)    # Cyan
COLOR_WARNING = (0, 255, 255)   # Yellow
COLOR_SUCCESS = (0, 255, 0)     # Green
COLOR_ERROR = (0, 0, 255)       # Red
COLOR_TEXT = (220, 220, 220)    # Light gray
COLOR_BACKGROUND = (40, 40, 40) # Dark gray

# ============================================================================
# HAND MIDI CONTROLLER CLASS
# ============================================================================

class HandMIDIController:
    """
    Professional hand tracking MIDI controller with advanced features.
    
    This class implements a complete hand tracking to MIDI conversion system
    with real-time visualization, region selection, and performance optimization.
    """
    
    def __init__(self):
        """Initialize the Hand MIDI Controller with all subsystems."""
        self.logger = self._setup_logging()
        self.logger.info("Initializing Hand MIDI Controller v2.0.0")
        
        # Initialize MediaPipe
        self._init_mediapipe()
        
        # Initialize MIDI
        self._init_midi()
        
        # Initialize tracking state
        self._init_tracking_state()
        
        # Initialize UI state
        self._init_ui_state()
        
        # Performance monitoring
        self._init_performance_monitoring()
        
        self.logger.info("Initialization complete")
    
    # ------------------------------------------------------------------------
    # Initialization Methods
    # ------------------------------------------------------------------------
    
    def _setup_logging(self) -> logging.Logger:
        """Configure logging for debugging and monitoring."""
        logging.basicConfig(
            level=logging.INFO,
            format='[%(levelname)s] %(asctime)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        return logging.getLogger(__name__)
    
    def _init_mediapipe(self):
        """Initialize MediaPipe hand tracking with optimized settings."""
        self.logger.info("Initializing MediaPipe hand tracking")
        
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Create hand detector with performance-optimized settings
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=MP_MAX_HANDS,
            model_complexity=MP_MODEL_COMPLEXITY,
            min_detection_confidence=MP_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=MP_MIN_TRACKING_CONFIDENCE
        )
    
    def _init_midi(self):
        """Initialize MIDI output with virtual device."""
        self.logger.info("Initializing MIDI subsystem")
        
        self.midi_enabled = False
        self.midi_out = None
        
        try:
            self.midi_out = rtmidi.MidiOut()
            
            # Try to open existing virtual port
            available_ports = self.midi_out.get_ports()
            virtual_port_found = False
            
            for i, port in enumerate(available_ports):
                if MIDI_DEVICE_NAME in port:
                    self.midi_out.open_port(i)
                    virtual_port_found = True
                    self.logger.info(f"Connected to existing virtual MIDI port: {port}")
                    break
            
            # Create new virtual port if not found
            if not virtual_port_found:
                self.midi_out.open_virtual_port(MIDI_DEVICE_NAME)
                self.logger.info(f"Created virtual MIDI port: {MIDI_DEVICE_NAME}")
            
            self.midi_enabled = True
            
        except Exception as e:
            self.logger.error(f"MIDI initialization failed: {e}")
            self.logger.warning("Running without MIDI output")
    
    def _init_tracking_state(self):
        """Initialize hand tracking state and history."""
        # MIDI CC mappings - organized by hand blocks
        self.cc_mappings = {
            # Left hand block (CC 1-6)
            'left_x':        {'cc': 1,  'label': 'L X-axis'},
            'left_y':        {'cc': 2,  'label': 'L Y-axis'},
            'left_pinch':    {'cc': 3,  'label': 'L Pinch'},
            'left_palm':     {'cc': 4,  'label': 'L Palm'},
            'left_rotation': {'cc': 5,  'label': 'L Rotate'},
            'left_extra':    {'cc': 6,  'label': 'L Velocity'},
            
            # Right hand block (CC 7-12)
            'right_x':        {'cc': 7,  'label': 'R X-axis'},
            'right_y':        {'cc': 8,  'label': 'R Y-axis'},
            'right_pinch':    {'cc': 9,  'label': 'R Pinch'},
            'right_palm':     {'cc': 10, 'label': 'R Palm'},
            'right_rotation': {'cc': 11, 'label': 'R Rotate'},
            'right_extra':    {'cc': 12, 'label': 'R Distance'},
        }
        
        # Current MIDI values for display
        self.current_values = {key: 0 for key in self.cc_mappings}
        
        # Smoothing history for each hand
        self.left_hand_history = self._create_smoothing_history()
        self.right_hand_history = self._create_smoothing_history()
        
        # Hand detection state
        self.hands_detected = {'left': False, 'right': False}
        self.last_detection_time = {'left': 0, 'right': 0}
        
        # Enhanced parameters for "extra" CC slots
        self.hand_positions = {'left': None, 'right': None}  # Store positions for distance calc
        self.hand_velocities = {'left': deque(maxlen=5), 'right': deque(maxlen=5)}  # Velocity history
        self.last_hand_positions = {'left': None, 'right': None}  # For velocity calculation
    
    def _init_ui_state(self):
        """Initialize UI state variables."""
        # Region selection state - OPTIMIZED
        self.selection_active = False
        self.selection_start = None
        self.selection_end = None
        self.selection_region = None
        self.mouse_dragging = False
        
        # Performance optimizations for region selection
        self._region_dirty = False  # Only redraw when changed
        self._selection_overlay = None  # Pre-rendered selection overlay
        self._region_bounds_cache = None  # Cached normalized bounds
        
        # UI display state
        self.show_overlay = True
        self.fullscreen = False
        
        # Frame dimensions (updated on first frame)
        self.frame_width = CAMERA_WIDTH
        self.frame_height = CAMERA_HEIGHT
        
        # Pre-allocated buffers for performance
        self._overlay_cache = None
    
    def _init_performance_monitoring(self):
        """Initialize performance monitoring variables."""
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0.0
        
        # Performance metrics
        self.frame_times = deque(maxlen=60)  # Last 60 frame times
        self.processing_times = deque(maxlen=60)  # Processing time per frame
    
    def _create_smoothing_history(self) -> Dict[str, deque]:
        """Create history buffers for parameter smoothing."""
        return {
            'x': deque(maxlen=SMOOTHING_WINDOW),
            'y': deque(maxlen=SMOOTHING_WINDOW),
            'pinch': deque(maxlen=SMOOTHING_WINDOW),
            'palm': deque(maxlen=SMOOTHING_WINDOW),
            'rotation': deque(maxlen=SMOOTHING_WINDOW)
        }
    
    # ------------------------------------------------------------------------
    # MIDI Processing Methods
    # ------------------------------------------------------------------------
    
    def send_midi_cc(self, cc_name: str, value: int):
        """
        Send MIDI CC message and update current values.
        
        Args:
            cc_name: Name of the CC parameter (e.g., 'left_x')
            value: MIDI value (0-127)
        """
        if cc_name not in self.cc_mappings:
            return
        
        # Clamp value to valid MIDI range
        value = np.clip(value, 0, 127)
        
        # Update current value for display
        self.current_values[cc_name] = value
        
        # Send MIDI if enabled
        if self.midi_enabled and self.midi_out:
            try:
                cc_num = self.cc_mappings[cc_name]['cc']
                self.midi_out.send_message([
                    0xB0 | MIDI_CHANNEL,  # Control Change
                    cc_num,
                    value
                ])
            except Exception as e:
                self.logger.error(f"MIDI send error: {e}")
    
    def reset_midi_values(self):
        """Reset all MIDI values to zero when hands are not detected."""
        for hand in ['left', 'right']:
            if not self.hands_detected[hand]:
                # Only reset if hand hasn't been detected for a while
                if time.time() - self.last_detection_time[hand] > 0.5:
                    self.send_midi_cc(f'{hand}_x', 0)
                    self.send_midi_cc(f'{hand}_y', 0)
                    self.send_midi_cc(f'{hand}_pinch', 0)
                    self.send_midi_cc(f'{hand}_palm', 0)
                    self.send_midi_cc(f'{hand}_rotation', 0)
                    self.send_midi_cc(f'{hand}_extra', 0)
    
    # ------------------------------------------------------------------------
    # Hand Processing Methods
    # ------------------------------------------------------------------------
    
    def process_hand(self, hand_landmarks, handedness) -> Tuple[object, object, int]:
        """
        Process hand landmarks and extract MIDI control values.
        
        This method performs the core hand tracking to MIDI conversion,
        including position mapping, gesture detection, and smoothing.
        
        Args:
            hand_landmarks: MediaPipe hand landmarks
            handedness: Hand classification (left/right)
            
        Returns:
            Tuple of (thumb_tip, index_tip, pinch_value)
        """
        # Determine which hand we're processing
        hand_label = handedness.classification[0].label.lower()
        hand_history = self.left_hand_history if hand_label == 'left' else self.right_hand_history
        
        # Update detection state
        self.hands_detected[hand_label] = True
        self.last_detection_time[hand_label] = time.time()
        
        # Extract key landmarks
        landmarks = hand_landmarks.landmark
        wrist = landmarks[0]
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]
        pinky_tip = landmarks[20]
        
        # -------------------------------
        # X/Y Position Processing - OPTIMIZED
        # -------------------------------
        if self.selection_active and self._region_bounds_cache:
            # Use pre-calculated normalized bounds for maximum performance
            cache = self._region_bounds_cache
            
            # Map wrist position to selected region using cached normalized values
            x_norm = (wrist.x - cache['x1_norm']) / cache['width_norm']
            y_norm = (wrist.y - cache['y1_norm']) / cache['height_norm']
            
            # Clamp and convert to MIDI with Y-axis correction
            x_pos = int(np.clip(x_norm, 0, 1) * 127)
            y_pos = int(np.clip(1 - y_norm, 0, 1) * 127)  # Invert Y for natural control
        else:
            # Use full frame with Y-axis correction
            x_pos = int(np.clip(wrist.x, 0, 1) * 127)
            y_pos = int(np.clip(1 - wrist.y, 0, 1) * 127)  # Invert Y for natural control
        
        # Apply smoothing
        x_pos = self._smooth_value(x_pos, hand_history['x'])
        y_pos = self._smooth_value(y_pos, hand_history['y'])
        
        # -------------------------------
        # Pinch Detection
        # -------------------------------
        pinch_distance = np.sqrt(
            (thumb_tip.x - index_tip.x)**2 + 
            (thumb_tip.y - index_tip.y)**2
        )
        
        # Hysteresis for stable pinch detection
        if pinch_distance < PINCH_THRESHOLD_CLOSE:
            pinch_raw = 127
        elif pinch_distance > PINCH_THRESHOLD_OPEN:
            pinch_raw = 0
        else:
            # Linear interpolation
            pinch_raw = int((1 - (pinch_distance - PINCH_THRESHOLD_CLOSE) / 
                           (PINCH_THRESHOLD_OPEN - PINCH_THRESHOLD_CLOSE)) * 127)
        
        pinch_value = self._smooth_value(pinch_raw, hand_history['pinch'])
        
        # -------------------------------
        # Palm Openness
        # -------------------------------
        palm_spread = np.sqrt(
            (index_tip.x - pinky_tip.x)**2 + 
            (index_tip.y - pinky_tip.y)**2
        )
        palm_raw = int(np.clip(palm_spread / 0.3, 0, 1) * 127)
        palm_value = self._smooth_value(palm_raw, hand_history['palm'])
        
        # -------------------------------
        # Hand Rotation
        # -------------------------------
        hand_vector = np.array([
            middle_tip.x - wrist.x,
            middle_tip.y - wrist.y
        ])
        angle = np.arctan2(hand_vector[1], hand_vector[0])
        rotation_raw = int(((angle + np.pi) / (2 * np.pi)) * 127)
        rotation_value = self._smooth_value(rotation_raw, hand_history['rotation'])
        
        # -------------------------------
        # Enhanced Extra Parameters
        # -------------------------------
        current_pos = np.array([wrist.x, wrist.y])
        
        # Calculate velocity for this hand
        velocity_value = self._calculate_hand_velocity(hand_label, current_pos)
        
        # Calculate distance between hands (for right hand extra param)
        distance_value = self._calculate_hand_distance()
        
        # Store current position for next frame
        self.hand_positions[hand_label] = current_pos
        
        # Send all MIDI values
        self.send_midi_cc(f'{hand_label}_x', x_pos)
        self.send_midi_cc(f'{hand_label}_y', y_pos)
        self.send_midi_cc(f'{hand_label}_pinch', pinch_value)
        self.send_midi_cc(f'{hand_label}_palm', palm_value)
        self.send_midi_cc(f'{hand_label}_rotation', rotation_value)
        
        # Assign enhanced parameters
        if hand_label == 'left':
            self.send_midi_cc('left_extra', velocity_value)  # Left hand velocity
        else:
            self.send_midi_cc('right_extra', distance_value)  # Distance between hands
        
        return thumb_tip, index_tip, pinch_value
    
    def _smooth_value(self, value: int, history: deque) -> int:
        """Apply exponential moving average smoothing."""
        history.append(value)
        if len(history) == 0:
            return value
        
        # Weighted average with more weight on recent values
        weights = np.exp(np.linspace(-1, 0, len(history)))
        weights /= weights.sum()
        
        return int(np.average(list(history), weights=weights))
    
    def _calculate_hand_velocity(self, hand_label: str, current_pos: np.ndarray) -> int:
        """
        Calculate hand movement velocity for expressive control.
        
        Returns MIDI value (0-127) based on movement speed.
        """
        if self.last_hand_positions[hand_label] is None:
            self.last_hand_positions[hand_label] = current_pos
            return 0
        
        # Calculate distance moved since last frame
        distance = np.linalg.norm(current_pos - self.last_hand_positions[hand_label])
        
        # Store velocity and smooth it
        velocity_history = self.hand_velocities[hand_label]
        velocity_history.append(distance)
        
        # Update last position
        self.last_hand_positions[hand_label] = current_pos
        
        # Calculate smoothed velocity (scale by ~1000 for MIDI range)
        if len(velocity_history) > 0:
            avg_velocity = np.mean(velocity_history) * 1000
            return int(np.clip(avg_velocity, 0, 127))
        
        return 0
    
    def _calculate_hand_distance(self) -> int:
        """
        Calculate distance between both hands for stereo control.
        
        Returns MIDI value (0-127) based on hand separation.
        """
        left_pos = self.hand_positions.get('left')
        right_pos = self.hand_positions.get('right')
        
        # Both hands must be detected
        if left_pos is None or right_pos is None:
            return 0
        
        # Calculate distance between hands
        distance = np.linalg.norm(left_pos - right_pos)
        
        # Map distance to MIDI range (0.5 = max separation expected)
        distance_midi = int(np.clip(distance / 0.5 * 127, 0, 127))
        
        return distance_midi
    
    # ------------------------------------------------------------------------
    # UI and Visualization Methods
    # ------------------------------------------------------------------------
    
    def mouse_callback(self, event: int, x: int, y: int, flags: int, param):
        """
        OPTIMIZED mouse callback for region selection.
        
        Uses dirty flags and caching for 60fps performance.
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            self.mouse_dragging = True
            self.selection_start = (x, y)
            self.selection_end = (x, y)
            self.selection_active = False
            self._region_dirty = True
            
        elif event == cv2.EVENT_MOUSEMOVE and self.mouse_dragging:
            # Only update if mouse moved significantly (reduces redraws)
            if self.selection_end is None or \
               abs(x - self.selection_end[0]) > 2 or abs(y - self.selection_end[1]) > 2:
                self.selection_end = (x, y)
                self._region_dirty = True
            
        elif event == cv2.EVENT_LBUTTONUP:
            if self.mouse_dragging and self.selection_start and self.selection_end:
                x1, y1 = self.selection_start
                x2, y2 = self.selection_end
                
                # Ensure proper ordering and minimum size
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)
                
                # Validate region size (minimum 100x100 pixels)
                if (x2 - x1) > 100 and (y2 - y1) > 100:
                    self.selection_region = (x1, y1, x2, y2)
                    self.selection_active = True
                    self._update_region_cache()
                    self.logger.info(f"Region selected: {self.selection_region}")
                else:
                    self.selection_region = None
                    self.selection_active = False
                    self._region_bounds_cache = None
                    
            self.mouse_dragging = False
            self._region_dirty = True
    
    def _update_region_cache(self):
        """Pre-calculate normalized region bounds for performance."""
        if self.selection_region:
            x1, y1, x2, y2 = self.selection_region
            # Normalize to 0-1 range for faster processing
            self._region_bounds_cache = {
                'x1_norm': x1 / self.frame_width,
                'y1_norm': y1 / self.frame_height,
                'x2_norm': x2 / self.frame_width,
                'y2_norm': y2 / self.frame_height,
                'width_norm': (x2 - x1) / self.frame_width,
                'height_norm': (y2 - y1) / self.frame_height
            }
    
    def draw_ui_overlay(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw the main UI overlay with MIDI values and status.
        
        This method creates the cyberpunk-styled overlay showing all
        MIDI parameters, FPS, and system status.
        """
        if not self.show_overlay:
            return frame
        
        h, w = frame.shape[:2]
        
        # Update frame dimensions and region cache if changed
        if self.frame_width != w or self.frame_height != h:
            self.frame_width = w
            self.frame_height = h
            # Update region cache with new dimensions
            if self.selection_active and self.selection_region:
                self._update_region_cache()
        
        # Calculate adaptive scale factor for different resolutions
        scale_factor = max(1.0, min(w / UI_SCALE_BASE, h / 720))
        
        # Initialize overlay buffer if needed
        if self._overlay_cache is None or self._overlay_cache.shape != frame.shape:
            self._overlay_cache = np.zeros_like(frame)
        
        overlay = self._overlay_cache
        overlay.fill(0)
        
        # -------------------------------
        # Draw main panel
        # -------------------------------
        panel_x = int(TABLE_PADDING * scale_factor)
        panel_y = int(TABLE_PADDING * scale_factor)
        panel_width = int(400 * scale_factor)
        panel_height = int(480 * scale_factor)
        
        # Background
        cv2.rectangle(overlay, 
                     (panel_x, panel_y),
                     (panel_x + panel_width, panel_y + panel_height),
                     COLOR_BACKGROUND, -1)
        
        # Border
        cv2.rectangle(overlay,
                     (panel_x, panel_y),
                     (panel_x + panel_width, panel_y + panel_height),
                     COLOR_ACCENT, max(1, int(2 * scale_factor)))
        
        # -------------------------------
        # Draw header
        # -------------------------------
        font = cv2.FONT_HERSHEY_DUPLEX
        title_scale = 0.8 * scale_factor
        header_scale = 0.5 * scale_factor
        
        # Title
        title_y = panel_y + int(35 * scale_factor)
        cv2.putText(overlay, "HAND MIDI CONTROLLER",
                   (panel_x + int(15 * scale_factor), title_y),
                   font, title_scale, COLOR_TEXT, 
                   max(1, int(2 * scale_factor)), cv2.LINE_AA)
        
        # Status line
        status_y = title_y + int(30 * scale_factor)
        status_text = f"STATUS: {'ACTIVE' if self.midi_enabled else 'OFFLINE'}"
        status_color = COLOR_SUCCESS if self.midi_enabled else COLOR_ERROR
        
        cv2.putText(overlay, status_text,
                   (panel_x + int(15 * scale_factor), status_y),
                   font, header_scale, status_color,
                   1, cv2.LINE_AA)
        
        # FPS counter
        fps_text = f"FPS: {self.current_fps:.0f}"
        cv2.putText(overlay, fps_text,
                   (panel_x + int(200 * scale_factor), status_y),
                   font, header_scale, COLOR_TEXT,
                   1, cv2.LINE_AA)
        
        # -------------------------------
        # Draw MIDI parameters
        # -------------------------------
        param_y = status_y + int(40 * scale_factor)
        row_height = int(32 * scale_factor)
        
        # Column headers
        cv2.putText(overlay, "CC#",
                   (panel_x + int(15 * scale_factor), param_y),
                   font, header_scale, COLOR_TEXT,
                   1, cv2.LINE_AA)
        
        cv2.putText(overlay, "PARAM",
                   (panel_x + int(60 * scale_factor), param_y),
                   font, header_scale, COLOR_TEXT,
                   1, cv2.LINE_AA)
        
        cv2.putText(overlay, "VALUE",
                   (panel_x + int(200 * scale_factor), param_y),
                   font, header_scale, COLOR_TEXT,
                   1, cv2.LINE_AA)
        
        param_y += int(25 * scale_factor)
        
        # Draw separator
        cv2.line(overlay,
                (panel_x + int(10 * scale_factor), param_y),
                (panel_x + panel_width - int(10 * scale_factor), param_y),
                COLOR_TEXT, 1)
        
        param_y += int(15 * scale_factor)
        
        # Draw each parameter
        for cc_name, cc_info in self.cc_mappings.items():
            value = self.current_values[cc_name]
            
            # Determine hand and color
            is_left = cc_name.startswith('left')
            param_color = (255, 200, 100) if is_left else (100, 200, 255)
            
            # CC number
            cv2.putText(overlay, f"{cc_info['cc']:02d}",
                       (panel_x + int(15 * scale_factor), param_y),
                       font, header_scale, param_color,
                       1, cv2.LINE_AA)
            
            # Parameter name
            cv2.putText(overlay, cc_info['label'],
                       (panel_x + int(60 * scale_factor), param_y),
                       font, header_scale, param_color,
                       1, cv2.LINE_AA)
            
            # Value
            cv2.putText(overlay, f"{value:03d}",
                       (panel_x + int(200 * scale_factor), param_y),
                       font, header_scale, param_color,
                       1, cv2.LINE_AA)
            
            # Progress bar
            bar_x = panel_x + int(250 * scale_factor)
            bar_width = int(120 * scale_factor)
            bar_height = int(12 * scale_factor)
            bar_y_offset = param_y - int(10 * scale_factor)
            
            # Background
            cv2.rectangle(overlay,
                         (bar_x, bar_y_offset),
                         (bar_x + bar_width, bar_y_offset + bar_height),
                         (60, 60, 60), -1)
            
            # Filled portion
            if value > 0:
                fill_width = int((value / 127.0) * bar_width)
                cv2.rectangle(overlay,
                             (bar_x, bar_y_offset),
                             (bar_x + fill_width, bar_y_offset + bar_height),
                             param_color, -1)
            
            param_y += row_height
        
        # -------------------------------
        # Apply overlay to frame
        # -------------------------------
        cv2.addWeighted(frame, 1.0 - OVERLAY_ALPHA, overlay, OVERLAY_ALPHA, 0, frame)
        
        # -------------------------------
        # Draw selection region - PERFORMANCE OPTIMIZED
        # -------------------------------
        self._draw_selection_overlay(frame, scale_factor)
        
        return frame
    
    def _draw_selection_overlay(self, frame: np.ndarray, scale_factor: float):
        """
        ULTRA-OPTIMIZED selection region rendering.
        
        Uses dirty flags, pre-computed overlays, and minimal operations.
        """
        # Active region visualization (low cost)
        if self.selection_active and self.selection_region:
            x1, y1, x2, y2 = self.selection_region
            
            # PERFORMANCE: Skip expensive brightening, just draw border
            # Draw crisp border
            cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_ACCENT, 2)
            
            # Minimal corner indicators (much faster than full brightening)
            corner_size = int(12 * scale_factor)
            cv2.rectangle(frame, (x1, y1), (x1 + corner_size, y1 + corner_size), COLOR_ACCENT, -1)
            cv2.rectangle(frame, (x2 - corner_size, y1), (x2, y1 + corner_size), COLOR_ACCENT, -1)
            cv2.rectangle(frame, (x1, y2 - corner_size), (x1 + corner_size, y2), COLOR_ACCENT, -1)
            cv2.rectangle(frame, (x2 - corner_size, y2 - corner_size), (x2, y2), COLOR_ACCENT, -1)
            
            # Simple text label
            font = cv2.FONT_HERSHEY_SIMPLEX
            label_y = y1 - 8 if y1 > 25 else y2 + 20
            cv2.putText(frame, "ACTIVE", (x1, label_y), font, 0.5 * scale_factor, COLOR_ACCENT, 1)
        
        # Dragging visualization (only when dragging)
        elif self.mouse_dragging and self.selection_start and self.selection_end:
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            
            # Ensure proper ordering for display
            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)
            
            # Fast dashed rectangle effect
            dash_length = 8
            
            # Top and bottom lines
            for x in range(x1, x2, dash_length * 2):
                cv2.line(frame, (x, y1), (min(x + dash_length, x2), y1), COLOR_WARNING, 2)
                cv2.line(frame, (x, y2), (min(x + dash_length, x2), y2), COLOR_WARNING, 2)
            
            # Left and right lines
            for y in range(y1, y2, dash_length * 2):
                cv2.line(frame, (x1, y), (x1, min(y + dash_length, y2)), COLOR_WARNING, 2)
                cv2.line(frame, (x2, y), (x2, min(y + dash_length, y2)), COLOR_WARNING, 2)
            
            # Size indicator
            width, height = x2 - x1, y2 - y1
            size_text = f"{width}x{height}"
            cv2.putText(frame, size_text, (x1 + 5, y1 + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4 * scale_factor, COLOR_WARNING, 1)
    
    def draw_hand_visualization(self, frame: np.ndarray, hand_landmarks,
                               thumb_tip, index_tip, pinch_value: int):
        """
        Draw hand landmarks and gesture visualization.
        
        Includes pinch indicator, hand connections, and parameter labels.
        """
        h, w = frame.shape[:2]
        scale_factor = max(1.0, min(w / UI_SCALE_BASE, h / 720))
        
        # Draw hand skeleton with custom styling
        self.mp_drawing.draw_landmarks(
            frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
            landmark_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
                color=(100, 100, 100),
                thickness=max(1, int(2 * scale_factor)),
                circle_radius=max(2, int(3 * scale_factor))
            ),
            connection_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
                color=(140, 140, 140),
                thickness=max(1, int(2 * scale_factor))
            )
        )
        
        # Draw pinch visualization
        thumb_px = (int(thumb_tip.x * w), int(thumb_tip.y * h))
        index_px = (int(index_tip.x * w), int(index_tip.y * h))
        
        # Dynamic line based on pinch strength
        intensity = pinch_value / 127.0
        line_color = (
            int(60 + intensity * 195),   # B
            int(140 + intensity * 115),  # G
            int(140 + intensity * 115)   # R
        )
        line_thickness = max(2, int((3 + intensity * 4) * scale_factor))
        
        cv2.line(frame, thumb_px, index_px, line_color, line_thickness)
        
        # Draw pinch indicators at tips
        if pinch_value > 64:
            cv2.circle(frame, thumb_px, 
                      int(8 * scale_factor), COLOR_ACCENT, -1)
            cv2.circle(frame, index_px,
                      int(8 * scale_factor), COLOR_ACCENT, -1)
    
    # ------------------------------------------------------------------------
    # Performance Monitoring
    # ------------------------------------------------------------------------
    
    def update_fps(self):
        """Update FPS counter with accurate timing."""
        self.fps_counter += 1
        current_time = time.time()
        
        elapsed = current_time - self.fps_start_time
        if elapsed >= FPS_UPDATE_INTERVAL:
            self.current_fps = self.fps_counter / elapsed
            self.fps_counter = 0
            self.fps_start_time = current_time
            
            # Log performance stats periodically
            if len(self.frame_times) > 0:
                avg_frame_time = np.mean(self.frame_times) * 1000
                self.logger.debug(f"Avg frame time: {avg_frame_time:.1f}ms")
    
    # ------------------------------------------------------------------------
    # Main Processing Loop
    # ------------------------------------------------------------------------
    
    def run(self):
        """
        Main application loop.
        
        Handles camera initialization, frame processing, and user interaction.
        """
        print("\n" + "="*60)
        print("HAND MIDI CONTROLLER - PROFESSIONAL EDITION")
        print("="*60)
        print("Version 2.0.0 | Optimized for Performance")
        print("="*60 + "\n")
        
        # Detect available cameras
        available_cameras = self._detect_cameras()
        if not available_cameras:
            self.logger.error("No cameras detected!")
            return
        
        camera_index = available_cameras[0]
        current_camera_idx = 0
        
        # Initialize camera with optimal settings
        cap = self._initialize_camera(camera_index)
        if cap is None:
            return
        
        # Create window
        window_name = "Hand MIDI Controller | Professional"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
        cv2.resizeWindow(window_name, 1600, 1000)
        cv2.moveWindow(window_name, 100, 50)
        
        # Set up mouse callback
        cv2.setMouseCallback(window_name, self.mouse_callback)
        
        # Print controls
        self._print_controls()
        
        try:
            self._main_loop(cap, window_name, available_cameras, current_camera_idx)
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
        finally:
            self._cleanup(cap)
    
    def _detect_cameras(self) -> List[int]:
        """Detect available camera devices."""
        cameras = []
        for i in range(5):  # Check first 5 indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cameras.append(i)
                cap.release()
                self.logger.info(f"Camera {i} detected")
        return cameras
    
    def _initialize_camera(self, index: int) -> Optional[cv2.VideoCapture]:
        """Initialize camera with optimal settings."""
        cap = cv2.VideoCapture(index)
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
        
        # Verify camera is working
        ret, test_frame = cap.read()
        if not ret:
            self.logger.error(f"Failed to read from camera {index}")
            cap.release()
            return None
        
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        self.logger.info(f"Camera initialized: {actual_w}x{actual_h} @ {actual_fps}fps")
        
        return cap
    
    def _print_controls(self):
        """Print control instructions."""
        print("\nCONTROLS:")
        print("-" * 50)
        print("  Q            - Quit")
        print("  V            - Cycle cameras")
        print("  F            - Toggle fullscreen")
        print("  O            - Toggle overlay")
        print("  R            - Reset region selection")
        print("")
        print("  REGION SELECTION:")
        print("  Click+Drag   - Select custom X/Y mapping area")
        print("                 (minimum 100x100 pixels)")
        print("  Cyan corners - Active region indicator")
        print("  Yellow dash  - Selection in progress")
        print("-" * 50 + "\n")
    
    def _main_loop(self, cap: cv2.VideoCapture, window_name: str,
                   available_cameras: List[int], current_camera_idx: int):
        """Main processing loop."""
        while cap.isOpened():
            loop_start = time.time()
            
            # Read frame
            ret, frame = cap.read()
            if not ret:
                self.logger.error("Camera disconnected")
                break
            
            # Update FPS counter
            self.update_fps()
            
            # Flip for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Convert to RGB for MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process hands
            processing_start = time.time()
            results = self.hands.process(frame_rgb)
            
            # Reset detection state
            self.hands_detected = {'left': False, 'right': False}
            
            # Process detected hands
            if results.multi_hand_landmarks and results.multi_handedness:
                for hand_landmarks, handedness in zip(
                    results.multi_hand_landmarks,
                    results.multi_handedness
                ):
                    thumb_tip, index_tip, pinch_value = self.process_hand(
                        hand_landmarks, handedness
                    )
                    
                    # Draw on RGB frame for efficiency
                    self.draw_hand_visualization(
                        frame_rgb, hand_landmarks,
                        thumb_tip, index_tip, pinch_value
                    )
            
            # Reset MIDI for undetected hands
            self.reset_midi_values()
            
            # Convert back to BGR for display
            frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            
            # Apply UI overlay
            frame = self.draw_ui_overlay(frame)
            
            # Record performance metrics
            processing_time = time.time() - processing_start
            self.processing_times.append(processing_time)
            
            # Display frame
            cv2.imshow(window_name, frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('v') and len(available_cameras) > 1:
                # Cycle cameras
                current_camera_idx = (current_camera_idx + 1) % len(available_cameras)
                cap.release()
                cap = self._initialize_camera(available_cameras[current_camera_idx])
                self.logger.info(f"Switched to camera {available_cameras[current_camera_idx]}")
            elif key == ord('f'):
                # Toggle fullscreen
                self.fullscreen = not self.fullscreen
                if self.fullscreen:
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN,
                                        cv2.WINDOW_FULLSCREEN)
                else:
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN,
                                        cv2.WINDOW_NORMAL)
            elif key == ord('o'):
                # Toggle overlay
                self.show_overlay = not self.show_overlay
                self.logger.info(f"Overlay {'enabled' if self.show_overlay else 'disabled'}")
            elif key == ord('r'):
                # Reset region selection with user feedback
                self.selection_active = False
                self.selection_region = None
                self._region_bounds_cache = None
                self._region_dirty = True
                print("✓ Region selection reset")
                self.logger.info("Region selection reset")
            
            # Record frame time
            frame_time = time.time() - loop_start
            self.frame_times.append(frame_time)
    
    def _cleanup(self, cap: cv2.VideoCapture):
        """Clean up resources."""
        self.logger.info("Shutting down...")
        
        # Release camera
        if cap:
            cap.release()
        
        # Close windows
        cv2.destroyAllWindows()
        
        # Close MIDI
        if self.midi_out:
            # Send all notes off
            for i in range(128):
                self.midi_out.send_message([0xB0 | MIDI_CHANNEL, 123, 0])
            
            self.midi_out.close_port()
        
        # Clean up MediaPipe
        self.hands.close()
        
        # Print performance summary
        if len(self.frame_times) > 0:
            avg_frame_time = np.mean(self.frame_times) * 1000
            avg_processing_time = np.mean(self.processing_times) * 1000
            
            print("\nPERFORMANCE SUMMARY:")
            print("-" * 40)
            print(f"Average FPS: {self.current_fps:.1f}")
            print(f"Average frame time: {avg_frame_time:.1f}ms")
            print(f"Average processing time: {avg_processing_time:.1f}ms")
            print("-" * 40)
        
        self.logger.info("Cleanup complete")


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Application entry point."""
    try:
        controller = HandMIDIController()
        controller.run()
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        logging.exception("Fatal error in main")
        sys.exit(1)


if __name__ == "__main__":
    main()