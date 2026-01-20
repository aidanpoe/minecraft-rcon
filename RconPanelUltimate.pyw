"""
House of Poe - Ultimate Minecraft RCON Control Panel
Full-featured Windows desktop application for Minecraft server management.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, colorchooser, simpledialog
import socket
import struct
import threading
import time
import re
import json
import os
from datetime import datetime, timedelta

# Try to import optional modules
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

try:
    from plyer import notification
    HAS_NOTIFY = True
except ImportError:
    HAS_NOTIFY = False

# =============================================================================
# CONFIGURATION
# =============================================================================
# These are default placeholders - actual values loaded from config
RCON_HOST = ""
RCON_PORT = 25575
RCON_PASSWORD = ""

# Determine the correct path for config files (works for both script and EXE)
def get_app_dir():
    """Get the directory where config files should be stored."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller EXE - use the EXE's directory
        return os.path.dirname(sys.executable)
    else:
        # Running as script - use the script's directory
        return os.path.dirname(__file__)

import sys  # Need sys for frozen check
APP_DIR = get_app_dir()
CONFIG_FILE = os.path.join(APP_DIR, "rcon_config.json")
CREDENTIALS_FILE = os.path.join(APP_DIR, "rcon_credentials.json")

# Minecraft colors
MC_COLORS = {
    'black': '#000000', 'dark_blue': '#0000AA', 'dark_green': '#00AA00',
    'dark_aqua': '#00AAAA', 'dark_red': '#AA0000', 'dark_purple': '#AA00AA',
    'gold': '#FFAA00', 'gray': '#AAAAAA', 'dark_gray': '#555555',
    'blue': '#5555FF', 'green': '#55FF55', 'aqua': '#55FFFF',
    'red': '#FF5555', 'light_purple': '#FF55FF', 'yellow': '#FFFF55', 'white': '#FFFFFF'
}

# BHOP Style Theme Colors (from bhop_style_selector)
BHOP = {
    'bg_dark': '#0f0f12',        # Main background (15,15,18)
    'bg_panel': '#231e12',       # Panel background (35,30,18)
    'bg_button': '#28283a',      # Button background (40,40,48)
    'bg_hover': '#3c5a78',       # Hovered button (60,90,120)
    'gold': '#d6b140',           # Gold accent (214,177,64)
    'gold_light': '#ebcd5f',     # Light gold title (235,205,95)
    'text': '#f0f0f0',           # White text (240,240,240)
    'text_dim': '#969696',       # Dimmed text
    'cyan': '#00b4b4',           # Cyan accent (0,180,180)
    'red': '#c84646',            # Red (200,70,70)
    'red_dark': '#782828',       # Dark red (120,40,40)
    'green': '#2ecc71',          # Green success
    'blue': '#288cc8',           # Blue (40,140,200)
    'purple': '#9b59b6',         # Purple accent
    'orange': '#e6a032',         # Orange (230,160,50)
}

# Gamerules
GAMERULES = [
    ('announceAdvancements', 'Announce advancements in chat', 'bool'),
    ('commandBlockOutput', 'Command blocks show output', 'bool'),
    ('disableElytraMovementCheck', 'Disable elytra movement check', 'bool'),
    ('disableRaids', 'Disable raids', 'bool'),
    ('doDaylightCycle', 'Day/night cycle', 'bool'),
    ('doEntityDrops', 'Entities drop items', 'bool'),
    ('doFireTick', 'Fire spreads', 'bool'),
    ('doImmediateRespawn', 'Immediate respawn', 'bool'),
    ('doInsomnia', 'Phantoms spawn', 'bool'),
    ('doLimitedCrafting', 'Limited crafting (need recipes)', 'bool'),
    ('doMobLoot', 'Mobs drop loot', 'bool'),
    ('doMobSpawning', 'Mobs spawn naturally', 'bool'),
    ('doPatrolSpawning', 'Patrols spawn', 'bool'),
    ('doTileDrops', 'Blocks drop items', 'bool'),
    ('doTraderSpawning', 'Wandering traders spawn', 'bool'),
    ('doWeatherCycle', 'Weather changes', 'bool'),
    ('drowningDamage', 'Drowning damage', 'bool'),
    ('fallDamage', 'Fall damage', 'bool'),
    ('fireDamage', 'Fire damage', 'bool'),
    ('forgiveDeadPlayers', 'Mobs forget dead players', 'bool'),
    ('freezeDamage', 'Freeze damage', 'bool'),
    ('keepInventory', 'Keep inventory on death', 'bool'),
    ('logAdminCommands', 'Log admin commands', 'bool'),
    ('mobGriefing', 'Mob griefing (creeper explosions, etc)', 'bool'),
    ('naturalRegeneration', 'Natural health regeneration', 'bool'),
    ('pvp', 'Player vs Player', 'bool'),
    ('randomTickSpeed', 'Random tick speed', 'int'),
    ('reducedDebugInfo', 'Reduced debug info (F3)', 'bool'),
    ('sendCommandFeedback', 'Send command feedback', 'bool'),
    ('showDeathMessages', 'Show death messages', 'bool'),
    ('spawnRadius', 'Spawn radius', 'int'),
    ('spectatorsGenerateChunks', 'Spectators generate chunks', 'bool'),
    ('universalAnger', 'Universal anger (mobs attack all players)', 'bool'),
]


class MCRcon:
    """Minecraft RCON client."""
    
    # Class-level credentials (set by login screen)
    host = ""
    port = 25575
    password = ""
    
    @classmethod
    def set_credentials(cls, host, port, password):
        """Set the RCON credentials."""
        cls.host = host
        cls.port = port
        cls.password = password
    
    @classmethod
    def test_connection(cls, host=None, port=None, password=None):
        """Test RCON connection and return (success, message)."""
        host = host or cls.host
        port = port or cls.port
        password = password or cls.password
        
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((host, port))
            
            # Login
            payload = password.encode('utf-8') + b'\x00\x00'
            packet = struct.pack('<ii', 1, 3) + payload
            s.send(struct.pack('<i', len(packet)) + packet)
            
            resp_len = struct.unpack('<i', s.recv(4))[0]
            resp = s.recv(resp_len)
            resp_id = struct.unpack('<i', resp[:4])[0]
            
            s.close()
            
            if resp_id == -1:
                return False, "Authentication failed - wrong password"
            
            return True, "Connected successfully"
        except socket.timeout:
            return False, "Connection timed out - server may be offline"
        except ConnectionRefusedError:
            return False, "Connection refused - check IP/port or RCON not enabled"
        except socket.gaierror:
            return False, "Invalid server address - check IP"
        except OSError as e:
            if "No route to host" in str(e):
                return False, "No route to host - check network connection"
            return False, f"Network error: {e}"
        except Exception as e:
            return False, f"Connection failed: {e}"
    
    @classmethod
    def send_command(cls, command: str) -> tuple:
        """Send command and return (success, response)."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((cls.host, cls.port))
            
            # Login
            payload = cls.password.encode('utf-8') + b'\x00\x00'
            packet = struct.pack('<ii', 1, 3) + payload
            s.send(struct.pack('<i', len(packet)) + packet)
            
            resp_len = struct.unpack('<i', s.recv(4))[0]
            resp = s.recv(resp_len)
            resp_id = struct.unpack('<i', resp[:4])[0]
            
            if resp_id == -1:
                s.close()
                return False, "AUTH_FAILED"
            
            # Send command
            payload = command.encode('utf-8') + b'\x00\x00'
            packet = struct.pack('<ii', 2, 2) + payload
            s.send(struct.pack('<i', len(packet)) + packet)
            
            resp_len = struct.unpack('<i', s.recv(4))[0]
            resp = s.recv(resp_len)
            response = resp[8:-2].decode('utf-8', errors='ignore')
            
            s.close()
            return True, response
        except Exception as e:
            return False, str(e)


def bhop_button(parent, text, command=None, accent=None, width=11, **kwargs):
    """Create a BHOP-styled button."""
    accent = accent or BHOP['gold']
    btn = tk.Button(parent, text=text, command=command,
                    bg=BHOP['bg_button'], fg=BHOP['text'],
                    activebackground=BHOP['bg_hover'], activeforeground=BHOP['text'],
                    font=('Trebuchet MS', 10, 'bold'), width=width,
                    relief='solid', bd=2, cursor='hand2',
                    highlightbackground=accent, highlightcolor=accent, **kwargs)
    return btn


def bhop_entry(parent, width=30, **kwargs):
    """Create a BHOP-styled entry field."""
    entry = tk.Entry(parent,
                     bg=BHOP['bg_panel'], fg=BHOP['text'],
                     insertbackground=BHOP['gold'],
                     selectbackground=BHOP['gold'], selectforeground=BHOP['bg_dark'],
                     font=('Trebuchet MS', 11), relief='solid', bd=2,
                     highlightbackground=BHOP['gold'], highlightcolor=BHOP['cyan'],
                     width=width, **kwargs)
    return entry


class ScheduledTask:
    """Represents a scheduled task."""
    def __init__(self, name, command, interval_seconds, enabled=True):
        self.name = name
        self.command = command
        self.interval = interval_seconds
        self.enabled = enabled
        self.last_run = None
        self.next_run = datetime.now() + timedelta(seconds=interval_seconds)


class RconApp:
    def __init__(self, root):
        self.root = root
        self.root.title("House of Poe - MC Control Panel")
        self.root.geometry("500x400")  # Start small for login
        self.root.configure(bg=BHOP['bg_dark'])
        
        self.selected_prefix_color = 'gold'
        self.selected_msg_color = 'white'
        self.players = []
        self.previous_players = set()
        self.command_history = []
        self.history_index = -1
        self.scheduled_tasks = []
        self.scheduler_running = True
        self.favorite_commands = []
        self.ascii_library = {}
        self.main_frame = None
        self.login_frame = None
        self.auth_check_failures = 0
        self.server_name = "Minecraft Server"  # Will be fetched from RCON
        
        self.setup_styles()
        
        # Check for saved credentials
        if self.load_credentials():
            # Test saved credentials
            success, msg = MCRcon.test_connection()
            if success:
                self.load_config()
                self.show_main_panel()
            else:
                # Credentials invalid, show login
                self.show_login_screen(error="Saved credentials invalid - please re-enter")
        else:
            # No saved credentials, show login
            self.show_login_screen()
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def load_credentials(self):
        """Load saved RCON credentials. Returns True if credentials exist."""
        if os.path.exists(CREDENTIALS_FILE):
            try:
                with open(CREDENTIALS_FILE, 'r') as f:
                    creds = json.load(f)
                    host = creds.get('host', '')
                    port = creds.get('port', 25575)
                    password = creds.get('password', '')
                    
                    if host and password:
                        MCRcon.set_credentials(host, port, password)
                        return True
            except:
                pass
        return False
    
    def save_credentials(self, host, port, password):
        """Save RCON credentials to file."""
        try:
            with open(CREDENTIALS_FILE, 'w') as f:
                json.dump({
                    'host': host,
                    'port': port,
                    'password': password
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving credentials: {e}")
    
    def show_login_screen(self, error=None):
        """Show the login/setup screen."""
        # Clear any existing frames
        if self.main_frame:
            self.main_frame.destroy()
            self.main_frame = None
        if self.login_frame:
            self.login_frame.destroy()
        
        self.root.geometry("500x520")
        self.root.title("Minecraft RCON - Server Connection")
        
        self.login_frame = tk.Frame(self.root, bg=BHOP['bg_dark'])
        self.login_frame.pack(fill='both', expand=True, padx=30, pady=20)
        
        # Title
        tk.Label(self.login_frame, text="MINECRAFT RCON",
                bg=BHOP['bg_dark'], fg=BHOP['gold_light'],
                font=('Trebuchet MS', 24, 'bold')).pack(pady=(5, 3))
        
        tk.Label(self.login_frame, text="Server Control Panel",
                bg=BHOP['bg_dark'], fg=BHOP['text'],
                font=('Trebuchet MS', 14)).pack(pady=(0, 20))
        
        # Error message if any
        if error:
            tk.Label(self.login_frame, text=f"⚠️ {error}",
                    bg=BHOP['bg_dark'], fg=BHOP['red'],
                    font=('Trebuchet MS', 10)).pack(pady=(0, 10))
        
        # Connection frame
        conn_frame = tk.Frame(self.login_frame, bg=BHOP['bg_panel'],
                             highlightbackground=BHOP['gold'], highlightthickness=2)
        conn_frame.pack(fill='x', pady=10)
        
        inner = tk.Frame(conn_frame, bg=BHOP['bg_panel'])
        inner.pack(fill='x', padx=20, pady=20)
        
        tk.Label(inner, text="Server Connection", bg=BHOP['bg_panel'],
                fg=BHOP['gold'], font=('Trebuchet MS', 14, 'bold')).pack(anchor='w', pady=(0, 15))
        
        # IP Address
        ip_row = tk.Frame(inner, bg=BHOP['bg_panel'])
        ip_row.pack(fill='x', pady=5)
        tk.Label(ip_row, text="Server IP:", bg=BHOP['bg_panel'],
                fg=BHOP['text'], font=('Trebuchet MS', 11), width=14, anchor='e').pack(side='left')
        self.login_ip_entry = tk.Entry(ip_row, bg=BHOP['bg_dark'], fg=BHOP['cyan'],
                                       font=('Consolas', 12), width=25,
                                       insertbackground=BHOP['gold'], relief='solid', bd=2)
        self.login_ip_entry.pack(side='left', padx=10)
        
        # RCON Port
        port_row = tk.Frame(inner, bg=BHOP['bg_panel'])
        port_row.pack(fill='x', pady=5)
        tk.Label(port_row, text="RCON Port:", bg=BHOP['bg_panel'],
                fg=BHOP['text'], font=('Trebuchet MS', 11), width=14, anchor='e').pack(side='left')
        self.login_port_entry = tk.Entry(port_row, bg=BHOP['bg_dark'], fg=BHOP['cyan'],
                                         font=('Consolas', 12), width=10,
                                         insertbackground=BHOP['gold'], relief='solid', bd=2)
        self.login_port_entry.insert(0, "25575")  # Default RCON port
        self.login_port_entry.pack(side='left', padx=10)
        tk.Label(port_row, text="(default: 25575)", bg=BHOP['bg_panel'],
                fg=BHOP['text_dim'], font=('Trebuchet MS', 9)).pack(side='left')
        
        # RCON Password
        pass_row = tk.Frame(inner, bg=BHOP['bg_panel'])
        pass_row.pack(fill='x', pady=5)
        tk.Label(pass_row, text="RCON Password:", bg=BHOP['bg_panel'],
                fg=BHOP['text'], font=('Trebuchet MS', 11), width=14, anchor='e').pack(side='left')
        self.login_pass_entry = tk.Entry(pass_row, bg=BHOP['bg_dark'], fg=BHOP['cyan'],
                                         font=('Consolas', 12), width=25, show='●',
                                         insertbackground=BHOP['gold'], relief='solid', bd=2)
        self.login_pass_entry.pack(side='left', padx=10)
        
        # Show password toggle button (eye icon)
        self.pass_visible = False
        self.eye_btn = tk.Button(pass_row, text="🔒", bg=BHOP['bg_panel'], fg=BHOP['text'],
                                 font=('Segoe UI Emoji', 14), bd=0, cursor='hand2',
                                 activebackground=BHOP['bg_panel'], activeforeground=BHOP['gold'],
                                 command=self.toggle_password_visibility)
        self.eye_btn.pack(side='left', padx=5)
        
        # Status label (more prominent for errors)
        self.login_status = tk.Label(self.login_frame, text="",
                                     bg=BHOP['bg_dark'], fg=BHOP['cyan'],
                                     font=('Trebuchet MS', 11, 'bold'),
                                     wraplength=400)
        self.login_status.pack(pady=10)
        
        # Connect button
        tk.Button(self.login_frame, text="🔌 Connect", command=self.attempt_login,
                 bg=BHOP['green'], fg='white',
                 font=('Trebuchet MS', 14, 'bold'), width=20, height=2,
                 relief='solid', bd=2, cursor='hand2',
                 activebackground='#27ae60', activeforeground='white').pack(pady=15)
        
        # Bind Enter key
        self.login_pass_entry.bind('<Return>', lambda e: self.attempt_login())
        self.login_ip_entry.bind('<Return>', lambda e: self.attempt_login())
        
        # Focus IP entry
        self.login_ip_entry.focus_set()
    
    def toggle_password_visibility(self):
        """Toggle password visibility."""
        if self.pass_visible:
            # Hide password
            self.login_pass_entry.config(show='●')
            self.eye_btn.config(text="🔒")
            self.pass_visible = False
        else:
            # Show password
            self.login_pass_entry.config(show='')
            self.eye_btn.config(text="👁")
            self.pass_visible = True
    
    def attempt_login(self):
        """Attempt to connect with provided credentials."""
        host = self.login_ip_entry.get().strip()
        port_str = self.login_port_entry.get().strip()
        password = self.login_pass_entry.get()
        
        if not host:
            self.login_status.config(text="⚠️ Please enter server IP", fg=BHOP['red'])
            return
        if not password:
            self.login_status.config(text="⚠️ Please enter RCON password", fg=BHOP['red'])
            return
        
        try:
            port = int(port_str)
        except:
            self.login_status.config(text="⚠️ Invalid port number", fg=BHOP['red'])
            return
        
        self.login_status.config(text="🔄 Connecting...", fg=BHOP['cyan'])
        self.root.update()
        
        # Test connection
        success, msg = MCRcon.test_connection(host, port, password)
        
        if success:
            # Save credentials
            MCRcon.set_credentials(host, port, password)
            self.save_credentials(host, port, password)
            self.login_status.config(text="✅ Connected!", fg=BHOP['green'])
            self.root.after(500, self.show_main_panel)
        else:
            self.login_status.config(text=f"❌ {msg}", fg=BHOP['red'])
    
    def show_main_panel(self):
        """Show the main control panel after successful login."""
        # Destroy login frame
        if self.login_frame:
            self.login_frame.destroy()
            self.login_frame = None
        
        # Fetch server name from RCON
        self.fetch_server_name()
        
        # Resize window
        self.root.geometry("1400x900")
        self.root.title(f"{self.server_name} - RCON Control Panel")
        
        # Load config and create main UI
        self.load_config()
        self.create_widgets()
        self.start_background_tasks()
    
    def fetch_server_name(self):
        """Fetch server name/MOTD from the server."""
        try:
            # Try to get server name via list command (often includes server name)
            success, response = MCRcon.send_command('list')
            if success and response:
                # Some servers include name in list output, try to parse it
                # Also try the 'seed' or other commands that might reveal server info
                pass
            
            # Try to get MOTD or server properties if available
            # Using 'tellraw' with server info selector
            success, response = MCRcon.send_command('help motd')
            # This likely won't work, so we'll try another approach
            
            # Check if there's a world name we can get
            success, response = MCRcon.send_command('worldborder get')
            if success and response:
                # World border returns info, server is responding
                # Default to a simple name based on connection
                pass
            
            # For now, use the IP as server identifier if we can't get name
            # User can configure this in a future update
            self.server_name = f"Server ({MCRcon.host})"
            
        except Exception as e:
            self.server_name = "Minecraft Server"
    
    def check_auth_status(self, response):
        """Check if response indicates auth failure and show login if needed."""
        if response == "AUTH_FAILED":
            self.auth_check_failures += 1
            if self.auth_check_failures >= 2:  # Require 2 failures to trigger re-login
                self.show_login_screen(error="Password changed on server - please re-authenticate")
                return False
        else:
            self.auth_check_failures = 0
        return True
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def load_config(self):
        """Load configuration from file."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.favorite_commands = config.get('favorites', [])
                    self.ascii_library = config.get('ascii_library', {})
                    
                    # Load scheduled tasks
                    for task in config.get('scheduled_tasks', []):
                        self.scheduled_tasks.append(ScheduledTask(
                            task['name'], task['command'], task['interval'], task.get('enabled', True)
                        ))
            except:
                pass
    
    def save_config(self):
        """Save configuration to file."""
        config = {
            'favorites': self.favorite_commands,
            'ascii_library': self.ascii_library,
            'scheduled_tasks': [
                {'name': t.name, 'command': t.command, 'interval': t.interval, 'enabled': t.enabled}
                for t in self.scheduled_tasks
            ]
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except:
            pass
    
    def setup_styles(self):
        """Setup ttk styles for BHOP-style dark theme."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # BHOP Color Scheme
        # Background: #0f0f12 (15,15,18) - Nearly black
        # Gold accent: #d6b140 (214,177,64) - Gold/amber
        # Light gold: #ebcd5f (235,205,95) - Title gold
        # Panel bg: #231e12 (35,30,18) - Dark brown panel
        # Button bg: #28283a (40,40,48) - Dark button
        # Cyan: #00b4b4 (0,180,180) - Highlight cyan
        # Text: #f0f0f0 (240,240,240) - White text
        
        bg_dark = '#0f0f12'
        bg_panel = '#231e12'
        bg_button = '#28283a'
        gold = '#d6b140'
        gold_light = '#ebcd5f'
        cyan = '#00b4b4'
        text = '#f0f0f0'
        
        style.configure('TFrame', background=bg_dark)
        style.configure('TLabel', background=bg_dark, foreground=text, font=('Trebuchet MS', 10))
        style.configure('Title.TLabel', font=('Trebuchet MS', 26, 'bold'), foreground=gold_light)
        style.configure('Header.TLabel', font=('Trebuchet MS', 14, 'bold'), foreground=gold)
        style.configure('SubHeader.TLabel', font=('Trebuchet MS', 11, 'bold'), foreground=cyan)
        style.configure('Status.TLabel', font=('Trebuchet MS', 12), foreground=cyan)
        
        style.configure('TNotebook', background=bg_dark)
        style.configure('TNotebook.Tab', 
                       font=('Trebuchet MS', 10, 'bold'), 
                       padding=[18, 8],
                       background=bg_button,
                       foreground=gold)
        style.map('TNotebook.Tab',
                 background=[('selected', bg_panel), ('active', '#3c5a78')],
                 foreground=[('selected', gold_light), ('active', text)])
        
        style.configure('TCheckbutton', background=bg_dark, foreground=text, font=('Trebuchet MS', 10))
        style.map('TCheckbutton', background=[('active', bg_dark)])
        
        # Custom button style
        style.configure('Gold.TButton',
                       font=('Trebuchet MS', 10, 'bold'),
                       background=bg_button,
                       foreground=gold,
                       borderwidth=2,
                       relief='solid',
                       padding=[12, 6])
        style.map('Gold.TButton',
                 background=[('active', '#3c5a78'), ('pressed', bg_panel)],
                 foreground=[('active', text)])
        
        # Entry style
        style.configure('TEntry',
                       fieldbackground=bg_panel,
                       foreground=text,
                       insertcolor=gold,
                       borderwidth=2,
                       relief='solid')
        
        # Scrollbar style
        style.configure('TScrollbar', 
                       background=bg_button, 
                       troughcolor=bg_dark,
                       borderwidth=0)
        
        # LabelFrame
        style.configure('TLabelframe', background=bg_dark, foreground=gold)
        style.configure('TLabelframe.Label', background=bg_dark, foreground=gold, font=('Trebuchet MS', 11, 'bold'))
    
    def create_widgets(self):
        """Create all UI widgets."""
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header
        header = ttk.Frame(self.main_frame)
        header.pack(fill='x', pady=(0, 10))
        
        self.title_label = ttk.Label(header, text=f"🎮 {self.server_name}", style='Title.TLabel')
        self.title_label.pack(side='left')
        
        # Status and server info
        self.status_frame = ttk.Frame(header)
        self.status_frame.pack(side='right')
        
        # Change Server button
        tk.Button(self.status_frame, text="🔌 Change Server", command=self.disconnect_and_login,
                 bg=BHOP['bg_button'], fg=BHOP['text_dim'],
                 font=('Trebuchet MS', 9), relief='solid', bd=1, cursor='hand2',
                 activebackground=BHOP['bg_hover']).pack(side='left', padx=5)
        
        # Server info label
        server_info = f"{MCRcon.host}:{MCRcon.port}"
        tk.Label(self.status_frame, text=f"📡 {server_info}", 
                bg=BHOP['bg_dark'], fg=BHOP['text_dim'],
                font=('Trebuchet MS', 9)).pack(side='left', padx=10)
        
        self.status_label = ttk.Label(self.status_frame, text="● Connecting...", style='Status.TLabel')
        self.status_label.pack(side='left', padx=10)
        
        self.player_count_label = ttk.Label(self.status_frame, text="Players: -/-", style='Status.TLabel')
        self.player_count_label.pack(side='left', padx=10)
        
        # Create notebook
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill='both', expand=True)
        
        # All tabs
        self.create_dashboard_tab(notebook)
        self.create_messages_tab(notebook)
        self.create_players_tab(notebook)
        self.create_world_tab(notebook)
        self.create_gamerules_tab(notebook)
        self.create_scheduler_tab(notebook)
        self.create_console_tab(notebook)
        self.create_fun_tab(notebook)
    
    def disconnect_and_login(self):
        """Disconnect and show login screen to change server."""
        if messagebox.askyesno("Change Server", "Disconnect from current server and connect to a different one?"):
            # Clear credentials file to force re-entry
            if os.path.exists(CREDENTIALS_FILE):
                os.remove(CREDENTIALS_FILE)
            self.show_login_screen()
    
    def create_dashboard_tab(self, notebook):
        """Dashboard with overview and quick actions."""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text='  📊 Dashboard  ')
        
        # Left panel
        left = ttk.Frame(tab)
        left.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        
        # Quick Actions
        ttk.Label(left, text="⚡ Quick Actions", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill='x')
        
        # Row 1
        row1 = ttk.Frame(btn_frame)
        row1.pack(fill='x', pady=3)
        for text, cmd, accent in [("☀️ Day", "time set day", BHOP['gold']), ("🌙 Night", "time set night", BHOP['blue']),
                               ("☀️ Clear", "weather clear", BHOP['gold_light']), ("🌧️ Rain", "weather rain", BHOP['cyan']),
                               ("⛈️ Thunder", "weather thunder", BHOP['bg_hover'])]:
            btn = tk.Button(row1, text=text, command=lambda c=cmd: self.quick_command(c),
                      bg=BHOP['bg_button'], fg=BHOP['text'], activebackground=BHOP['bg_hover'],
                      activeforeground=BHOP['text'], font=('Trebuchet MS', 10, 'bold'), width=11,
                      relief='solid', bd=2, highlightbackground=accent, highlightcolor=accent,
                      cursor='hand2')
            btn.pack(side='left', padx=2)
        
        # Row 2
        row2 = ttk.Frame(btn_frame)
        row2.pack(fill='x', pady=3)
        for text, cmd, accent in [("💾 Save", "save-all", BHOP['green']), ("📋 List", None, BHOP['purple']),
                               ("🚫 Bans", None, BHOP['red']), ("⭐ Ops", None, BHOP['gold']),
                               ("🕐 Time", None, BHOP['cyan']), ("📊 Info", None, BHOP['blue'])]:
            if cmd:
                btn = tk.Button(row2, text=text, command=lambda c=cmd: self.quick_command(c),
                          bg=BHOP['bg_button'], fg=BHOP['text'], activebackground=BHOP['bg_hover'],
                          font=('Trebuchet MS', 10, 'bold'), width=11, relief='solid', bd=2, cursor='hand2')
            elif text == "📋 List":
                btn = tk.Button(row2, text=text, command=self.refresh_players,
                          bg=BHOP['bg_button'], fg=BHOP['text'], activebackground=BHOP['bg_hover'],
                          font=('Trebuchet MS', 10, 'bold'), width=11, relief='solid', bd=2, cursor='hand2')
            elif text == "🚫 Bans":
                btn = tk.Button(row2, text=text, command=self.show_banlist,
                          bg=BHOP['bg_button'], fg=BHOP['text'], activebackground=BHOP['bg_hover'],
                          font=('Trebuchet MS', 10, 'bold'), width=11, relief='solid', bd=2, cursor='hand2')
            elif text == "⭐ Ops":
                btn = tk.Button(row2, text=text, command=self.show_ops,
                          bg=BHOP['bg_button'], fg=BHOP['text'], activebackground=BHOP['bg_hover'],
                          font=('Trebuchet MS', 10, 'bold'), width=11, relief='solid', bd=2, cursor='hand2')
            elif text == "🕐 Time":
                btn = tk.Button(row2, text=text, command=self.query_time,
                          bg=BHOP['bg_button'], fg=BHOP['text'], activebackground=BHOP['bg_hover'],
                          font=('Trebuchet MS', 10, 'bold'), width=11, relief='solid', bd=2, cursor='hand2')
            elif text == "📊 Info":
                btn = tk.Button(row2, text=text, command=self.query_server_info,
                          bg=BHOP['bg_button'], fg=BHOP['text'], activebackground=BHOP['bg_hover'],
                          font=('Trebuchet MS', 10, 'bold'), width=11, relief='solid', bd=2, cursor='hand2')
            btn.pack(side='left', padx=2)
        
        # Row 3 - Danger Zone
        row3 = ttk.Frame(btn_frame)
        row3.pack(fill='x', pady=3)
        tk.Button(row3, text="⏹️ Stop Server", command=self.confirm_stop,
                  bg=BHOP['red_dark'], fg=BHOP['text'], activebackground=BHOP['red'],
                  font=('Trebuchet MS', 10, 'bold'), width=13, relief='solid', bd=2, cursor='hand2').pack(side='left', padx=2)
        tk.Button(row3, text="👢 Kick All", command=self.kick_all,
                  bg=BHOP['bg_button'], fg=BHOP['orange'], activebackground=BHOP['bg_hover'],
                  font=('Trebuchet MS', 10, 'bold'), width=13, relief='solid', bd=2, cursor='hand2').pack(side='left', padx=2)
        
        # Server Info Display
        ttk.Label(left, text="📈 Server Status", style='Header.TLabel').pack(anchor='w', pady=(20, 10))
        
        self.info_display = tk.Label(left, text="Click 'Time' to query server status",
                                      bg=BHOP['bg_panel'], fg=BHOP['cyan'], font=('Consolas', 11),
                                      padx=15, pady=10, anchor='w', justify='left')
        self.info_display.pack(fill='x')
        
        # Players list
        ttk.Label(left, text="👥 Online Players", style='Header.TLabel').pack(anchor='w', pady=(20, 10))
        
        self.players_listbox = tk.Listbox(left, bg=BHOP['bg_dark'], fg=BHOP['cyan'],
                                           font=('Consolas', 12), height=8, selectbackground=BHOP['gold'],
                                           selectforeground=BHOP['bg_dark'], highlightbackground=BHOP['gold'],
                                           highlightthickness=1, relief='solid', bd=1)
        self.players_listbox.pack(fill='both', expand=True)
        self.players_listbox.bind('<Double-1>', self.on_player_double_click)
        self.players_listbox.bind('<<ListboxSelect>>', self.on_player_select)
        
        # Right panel - Player Actions
        right = ttk.Frame(tab, width=320)
        right.pack(side='right', fill='y', padx=10, pady=10)
        right.pack_propagate(False)
        
        # Selected player header
        ttk.Label(right, text="👤 Player Actions", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        self.selected_player_label = tk.Label(right, text="Select a player from the list",
                                               bg=BHOP['bg_dark'], fg=BHOP['text_dim'],
                                               font=('Trebuchet MS', 11, 'italic'))
        self.selected_player_label.pack(anchor='w', pady=(0, 15))
        
        # Player actions frame
        self.player_actions_frame = ttk.Frame(right)
        self.player_actions_frame.pack(fill='both', expand=True)
        
        # Create player action buttons (initially hidden/disabled)
        self.create_player_action_buttons()
        
        # Separator
        ttk.Separator(right, orient='horizontal').pack(fill='x', pady=15)
        
        # Favorites section (smaller, below player actions)
        ttk.Label(right, text="⭐ Quick Commands", style='SubHeader.TLabel').pack(anchor='w', pady=(0, 5))
        
        self.favorites_frame = ttk.Frame(right)
        self.favorites_frame.pack(fill='x')
        
        self.refresh_favorites_list()
        
        # Add favorite button
        add_fav_frame = ttk.Frame(right)
        add_fav_frame.pack(fill='x', pady=5)
        
        self.new_fav_entry = ttk.Entry(add_fav_frame, width=20)
        self.new_fav_entry.pack(side='left', fill='x', expand=True)
        
        tk.Button(add_fav_frame, text="+", command=self.add_favorite,
                  bg=BHOP['bg_button'], fg=BHOP['gold'], font=('Trebuchet MS', 10, 'bold'), width=3,
                  relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=5)
    
    def create_messages_tab(self, notebook):
        """Messages tab with broadcast, titles, action bar."""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text='  📢 Messages  ')
        
        content = ttk.Frame(tab)
        content.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Broadcast Message
        ttk.Label(content, text="📢 Broadcast Message", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        msg_frame = ttk.Frame(content)
        msg_frame.pack(fill='x', pady=5)
        
        ttk.Label(msg_frame, text="Prefix:").pack(side='left')
        self.prefix_entry = ttk.Entry(msg_frame, width=20)
        self.prefix_entry.insert(0, "[House of Poe]")
        self.prefix_entry.pack(side='left', padx=5)
        
        ttk.Label(msg_frame, text="Message:").pack(side='left', padx=(10, 0))
        self.message_entry = ttk.Entry(msg_frame, width=50)
        self.message_entry.pack(side='left', padx=5, fill='x', expand=True)
        
        tk.Button(msg_frame, text="Send", command=self.send_broadcast,
                  bg=BHOP['bg_button'], fg=BHOP['gold'], font=('Trebuchet MS', 10, 'bold'),
                  relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=5)
        
        # Color selection
        color_frame = ttk.Frame(content)
        color_frame.pack(fill='x', pady=5)
        ttk.Label(color_frame, text="Colors:").pack(side='left')
        
        for color_name in ['gold', 'red', 'green', 'aqua', 'light_purple', 'yellow', 'white']:
            tk.Button(color_frame, bg=MC_COLORS[color_name], width=2,
                      command=lambda c=color_name: self.set_msg_color(c)).pack(side='left', padx=2)
        
        # Separator
        ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
        
        # Title Message
        ttk.Label(content, text="📺 Title Message (Big Screen Text)", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        title_frame = ttk.Frame(content)
        title_frame.pack(fill='x', pady=5)
        
        ttk.Label(title_frame, text="Title:").pack(side='left')
        self.title_entry = ttk.Entry(title_frame, width=30)
        self.title_entry.pack(side='left', padx=5)
        
        ttk.Label(title_frame, text="Subtitle:").pack(side='left', padx=(10, 0))
        self.subtitle_entry = ttk.Entry(title_frame, width=30)
        self.subtitle_entry.pack(side='left', padx=5)
        
        tk.Button(title_frame, text="Show Title", command=self.send_title,
                  bg=BHOP['bg_button'], fg=BHOP['purple'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=5)
        
        # Title timing
        timing_frame = ttk.Frame(content)
        timing_frame.pack(fill='x', pady=5)
        
        ttk.Label(timing_frame, text="Fade In:").pack(side='left')
        self.title_fadein = ttk.Entry(timing_frame, width=5)
        self.title_fadein.insert(0, "20")
        self.title_fadein.pack(side='left', padx=5)
        
        ttk.Label(timing_frame, text="Stay:").pack(side='left')
        self.title_stay = ttk.Entry(timing_frame, width=5)
        self.title_stay.insert(0, "60")
        self.title_stay.pack(side='left', padx=5)
        
        ttk.Label(timing_frame, text="Fade Out:").pack(side='left')
        self.title_fadeout = ttk.Entry(timing_frame, width=5)
        self.title_fadeout.insert(0, "20")
        self.title_fadeout.pack(side='left', padx=5)
        
        # Separator
        ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
        
        # Action Bar
        ttk.Label(content, text="📍 Action Bar (Above Hotbar)", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        actionbar_frame = ttk.Frame(content)
        actionbar_frame.pack(fill='x', pady=5)
        
        self.actionbar_entry = ttk.Entry(actionbar_frame, width=60)
        self.actionbar_entry.pack(side='left', padx=5, fill='x', expand=True)
        
        tk.Button(actionbar_frame, text="Send", command=self.send_actionbar,
                  bg=BHOP['bg_button'], fg=BHOP['blue'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=5)
        
        # Separator
        ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
        
        # Private Message
        ttk.Label(content, text="💬 Private Message (Whisper)", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        pm_frame = ttk.Frame(content)
        pm_frame.pack(fill='x', pady=5)
        
        ttk.Label(pm_frame, text="To:").pack(side='left')
        self.pm_player_entry = ttk.Entry(pm_frame, width=20)
        self.pm_player_entry.pack(side='left', padx=5)
        
        ttk.Label(pm_frame, text="Message:").pack(side='left', padx=(10, 0))
        self.pm_message_entry = ttk.Entry(pm_frame, width=40)
        self.pm_message_entry.pack(side='left', padx=5, fill='x', expand=True)
        
        tk.Button(pm_frame, text="Whisper", command=self.send_whisper,
                  bg=BHOP['bg_button'], fg=BHOP['cyan'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=5)
        
        # Quick messages
        ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
        ttk.Label(content, text="⚡ Quick Messages", style='SubHeader.TLabel').pack(anchor='w', pady=(0, 10))
        
        quick_frame = ttk.Frame(content)
        quick_frame.pack(fill='x')
        
        for text, msg, color in [("Welcome!", "Welcome to the server!", "white"),
                                  ("Discord", "Join our Discord: https://discord.gg/HAtqezdy4G", "aqua"),
                                  ("5min Warning", "Server restarting in 5 minutes!", "red"),
                                  ("1min Warning", "Server restarting in 1 minute!", "red")]:
            tk.Button(quick_frame, text=text, command=lambda m=msg, c=color: self.quick_msg(m, c),
                      bg=BHOP['bg_button'], fg=BHOP['text'], font=('Trebuchet MS', 9, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=3)
    
    def create_players_tab(self, notebook):
        """Player management tab."""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text='  👥 Players  ')
        
        content = ttk.Frame(tab)
        content.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Player selection
        ttk.Label(content, text="👤 Player Management", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        name_frame = ttk.Frame(content)
        name_frame.pack(fill='x', pady=5)
        
        ttk.Label(name_frame, text="Player:").pack(side='left')
        self.player_name_combo = ttk.Combobox(name_frame, values=[], width=22)
        self.player_name_combo.pack(side='left', padx=5)
        tk.Button(name_frame, text="🔄", command=self.refresh_player_combo,
                  bg=BHOP['bg_button'], fg=BHOP['gold'], font=('Trebuchet MS', 10), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover'], width=2).pack(side='left', padx=2)
        # Keep player_name_entry as alias for compatibility
        self.player_name_entry = self.player_name_combo
        
        # Actions row 1
        actions1 = ttk.Frame(content)
        actions1.pack(fill='x', pady=5)
        
        tk.Button(actions1, text="👢 Kick", command=self.kick_player,
                  bg="#f39c12", fg='black', font=('Trebuchet MS', 10), width=10).pack(side='left', padx=3)
        tk.Button(actions1, text="🔨 Ban", command=self.ban_player,
                  bg="#e74c3c", fg='white', font=('Trebuchet MS', 10), width=10).pack(side='left', padx=3)
        tk.Button(actions1, text="🔓 Pardon", command=self.pardon_player,
                  bg="#2ecc71", fg='white', font=('Trebuchet MS', 10), width=10).pack(side='left', padx=3)
        tk.Button(actions1, text="⭐ OP", command=self.op_player,
                  bg="#9b59b6", fg='white', font=('Trebuchet MS', 10), width=10).pack(side='left', padx=3)
        tk.Button(actions1, text="DeOP", command=self.deop_player,
                  bg="#7f8c8d", fg='white', font=('Trebuchet MS', 10), width=10).pack(side='left', padx=3)
        
        # Reason
        reason_frame = ttk.Frame(content)
        reason_frame.pack(fill='x', pady=5)
        ttk.Label(reason_frame, text="Reason:").pack(side='left')
        self.kick_reason_entry = ttk.Entry(reason_frame, width=50)
        self.kick_reason_entry.insert(0, "Kicked by admin")
        self.kick_reason_entry.pack(side='left', padx=10, fill='x', expand=True)
        
        # Separator
        ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
        
        # Give items
        ttk.Label(content, text="🎁 Give Items", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        give_frame = ttk.Frame(content)
        give_frame.pack(fill='x', pady=5)
        
        ttk.Label(give_frame, text="Item:").pack(side='left')
        self.give_item_entry = ttk.Entry(give_frame, width=25)
        self.give_item_entry.insert(0, "minecraft:diamond")
        self.give_item_entry.pack(side='left', padx=5)
        
        ttk.Label(give_frame, text="Amount:").pack(side='left')
        self.give_amount_entry = ttk.Entry(give_frame, width=5)
        self.give_amount_entry.insert(0, "64")
        self.give_amount_entry.pack(side='left', padx=5)
        
        tk.Button(give_frame, text="Give", command=self.give_item,
                  bg=BHOP['bg_button'], fg=BHOP['green'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=10)
        
        # Quick items
        quick_items = ttk.Frame(content)
        quick_items.pack(fill='x', pady=5)
        
        for item, label in [("minecraft:diamond", "💎"), ("minecraft:netherite_ingot", "🔩"),
                             ("minecraft:golden_apple", "🍎"), ("minecraft:elytra", "🪽"),
                             ("minecraft:experience_bottle", "✨")]:
            tk.Button(quick_items, text=label, command=lambda i=item: self.quick_give(i),
                      bg=BHOP['bg_panel'], fg='white', font=('Trebuchet MS', 12), width=3).pack(side='left', padx=2)
        
        # Separator
        ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
        
        # Teleport
        ttk.Label(content, text="🌍 Teleport", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        tp_frame = ttk.Frame(content)
        tp_frame.pack(fill='x', pady=5)
        
        ttk.Label(tp_frame, text="From:").pack(side='left')
        self.tp_from_combo = ttk.Combobox(tp_frame, values=[], width=18)
        self.tp_from_combo.pack(side='left', padx=5)
        
        ttk.Label(tp_frame, text="→ To:").pack(side='left', padx=(10, 0))
        self.tp_target_combo = ttk.Combobox(tp_frame, values=[], width=20)
        self.tp_target_combo.pack(side='left', padx=5)
        
        tk.Button(tp_frame, text="🔄", command=self.refresh_tp_players,
                  bg=BHOP['bg_button'], fg=BHOP['gold'], font=('Trebuchet MS', 10), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover'], width=2).pack(side='left', padx=2)
        tk.Button(tp_frame, text="Teleport", command=self.teleport_player,
                  bg=BHOP['bg_button'], fg=BHOP['blue'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=5)
        tk.Button(tp_frame, text="Bring Here", command=self.bring_player,
                  bg=BHOP['bg_button'], fg=BHOP['purple'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=5)
        
        # Separator
        ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
        
        # Whitelist management
        ttk.Label(content, text="📋 Whitelist Management", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        wl_frame = ttk.Frame(content)
        wl_frame.pack(fill='x', pady=5)
        
        tk.Button(wl_frame, text="View Whitelist", command=self.show_whitelist,
                  bg=BHOP['bg_button'], fg=BHOP['blue'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=3)
        tk.Button(wl_frame, text="Add to Whitelist", command=lambda: self.whitelist_action('add'),
                  bg=BHOP['bg_button'], fg=BHOP['green'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=3)
        tk.Button(wl_frame, text="Remove from Whitelist", command=lambda: self.whitelist_action('remove'),
                  bg=BHOP['red_dark'], fg=BHOP['text'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['red']).pack(side='left', padx=3)
        tk.Button(wl_frame, text="Toggle Whitelist", command=self.toggle_whitelist,
                  bg=BHOP['bg_button'], fg=BHOP['gold'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=3)
        
        # Effects
        ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
        ttk.Label(content, text="✨ Apply Effects", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        effect_frame = ttk.Frame(content)
        effect_frame.pack(fill='x', pady=5)
        
        ttk.Label(effect_frame, text="Effect:").pack(side='left')
        self.effect_combo = ttk.Combobox(effect_frame, values=[
            'speed', 'slowness', 'haste', 'strength', 'instant_health', 'instant_damage',
            'jump_boost', 'regeneration', 'resistance', 'fire_resistance', 'water_breathing',
            'invisibility', 'night_vision', 'saturation', 'glowing', 'levitation', 'slow_falling'
        ], width=20)
        self.effect_combo.set('speed')
        self.effect_combo.pack(side='left', padx=5)
        
        ttk.Label(effect_frame, text="Duration (s):").pack(side='left')
        self.effect_duration = ttk.Entry(effect_frame, width=5)
        self.effect_duration.insert(0, "60")
        self.effect_duration.pack(side='left', padx=5)
        
        ttk.Label(effect_frame, text="Level:").pack(side='left')
        self.effect_level = ttk.Entry(effect_frame, width=3)
        self.effect_level.insert(0, "1")
        self.effect_level.pack(side='left', padx=5)
        
        tk.Button(effect_frame, text="Apply", command=self.apply_effect,
                  bg=BHOP['bg_button'], fg=BHOP['purple'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=10)
        tk.Button(effect_frame, text="Clear All", command=self.clear_effects,
                  bg=BHOP['red_dark'], fg=BHOP['text'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['red']).pack(side='left', padx=3)
    
    def create_world_tab(self, notebook):
        """World controls tab."""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text='  🌍 World  ')
        
        content = ttk.Frame(tab)
        content.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Time control
        ttk.Label(content, text="🕐 Time Control", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        time_frame = ttk.Frame(content)
        time_frame.pack(fill='x', pady=5)
        
        for text, val, bg in [("Dawn", "0", "#f39c12"), ("Morning", "1000", "#f1c40f"),
                               ("Noon", "6000", "#e74c3c"), ("Afternoon", "9000", "#e67e22"),
                               ("Dusk", "12000", "#9b59b6"), ("Night", "14000", "#3498db"),
                               ("Midnight", "18000", "#2c3e50")]:
            tk.Button(time_frame, text=text, command=lambda v=val: self.quick_command(f'time set {v}'),
                      bg=BHOP['bg_button'], fg=BHOP['text'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover'], width=10).pack(side='left', padx=2)
        
        # Custom time
        custom_time_frame = ttk.Frame(content)
        custom_time_frame.pack(fill='x', pady=5)
        
        ttk.Label(custom_time_frame, text="Set Time (ticks):").pack(side='left')
        self.custom_time_entry = ttk.Entry(custom_time_frame, width=10)
        self.custom_time_entry.pack(side='left', padx=5)
        tk.Button(custom_time_frame, text="Set", command=self.set_custom_time,
                  bg=BHOP['bg_button'], fg=BHOP['cyan'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=5)
        
        ttk.Label(custom_time_frame, text="Add Days:").pack(side='left', padx=(20, 0))
        self.add_days_entry = ttk.Entry(custom_time_frame, width=5)
        self.add_days_entry.insert(0, "1")
        self.add_days_entry.pack(side='left', padx=5)
        tk.Button(custom_time_frame, text="Add", command=self.add_days,
                  bg=BHOP['bg_button'], fg=BHOP['cyan'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=5)
        
        # Weather
        ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
        ttk.Label(content, text="🌤️ Weather Control", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        weather_frame = ttk.Frame(content)
        weather_frame.pack(fill='x', pady=5)
        
        for text, val, bg in [("☀️ Clear", "clear", "#f1c40f"), ("🌧️ Rain", "rain", "#3498db"),
                               ("⛈️ Thunder", "thunder", "#7f8c8d")]:
            tk.Button(weather_frame, text=text, command=lambda v=val: self.quick_command(f'weather {v}'),
                      bg=bg, fg='black' if bg == '#f1c40f' else 'white',
                      font=('Segoe UI', 11), width=12).pack(side='left', padx=5)
        
        # Weather duration
        dur_frame = ttk.Frame(content)
        dur_frame.pack(fill='x', pady=5)
        
        ttk.Label(dur_frame, text="Duration (seconds):").pack(side='left')
        self.weather_duration = ttk.Entry(dur_frame, width=10)
        self.weather_duration.insert(0, "6000")
        self.weather_duration.pack(side='left', padx=5)
        
        # Difficulty
        ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
        ttk.Label(content, text="⚔️ Difficulty", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        diff_frame = ttk.Frame(content)
        diff_frame.pack(fill='x', pady=5)
        
        for text, val, bg in [("Peaceful", "peaceful", "#2ecc71"), ("Easy", "easy", "#3498db"),
                               ("Normal", "normal", "#f39c12"), ("Hard", "hard", "#e74c3c")]:
            tk.Button(diff_frame, text=text, command=lambda v=val: self.quick_command(f'difficulty {v}'),
                      bg=bg, fg='white' if bg not in ['#f39c12', '#2ecc71'] else 'black',
                      font=('Segoe UI', 11), width=12).pack(side='left', padx=5)
        
        # World Border
        ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
        ttk.Label(content, text="🔲 World Border", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        border_frame = ttk.Frame(content)
        border_frame.pack(fill='x', pady=5)
        
        ttk.Label(border_frame, text="Size:").pack(side='left')
        self.border_size_entry = ttk.Entry(border_frame, width=10)
        self.border_size_entry.insert(0, "10000")
        self.border_size_entry.pack(side='left', padx=5)
        
        tk.Button(border_frame, text="Set Border", command=self.set_world_border,
                  bg=BHOP['bg_button'], fg=BHOP['blue'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=5)
        tk.Button(border_frame, text="Get Border", command=self.get_world_border,
                  bg=BHOP['bg_button'], fg=BHOP['cyan'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=5)
        
        # Spawn
        ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
        ttk.Label(content, text="🏠 World Spawn", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        spawn_frame = ttk.Frame(content)
        spawn_frame.pack(fill='x', pady=5)
        
        for coord, default in [('X', '0'), ('Y', '100'), ('Z', '0')]:
            ttk.Label(spawn_frame, text=f"{coord}:").pack(side='left')
            entry = ttk.Entry(spawn_frame, width=8)
            entry.insert(0, default)
            entry.pack(side='left', padx=5)
            setattr(self, f'spawn_{coord.lower()}_entry', entry)
        
        tk.Button(spawn_frame, text="Set Spawn", command=self.set_world_spawn,
                  bg=BHOP['bg_button'], fg=BHOP['purple'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=10)
    
    def create_gamerules_tab(self, notebook):
        """Gamerules editor tab."""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text='  ⚙️ Gamerules  ')
        
        ttk.Label(tab, text="⚙️ Gamerule Editor", style='Header.TLabel').pack(anchor='w', padx=20, pady=10)
        ttk.Label(tab, text="Click a toggle to change the rule. Changes apply immediately.",
                  foreground='#888888').pack(anchor='w', padx=20)
        
        # Create scrollable frame
        canvas = tk.Canvas(tab, bg=BHOP['bg_dark'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient='vertical', command=canvas.yview)
        scrollable = ttk.Frame(canvas)
        
        scrollable.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scrollable, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True, padx=20, pady=10)
        scrollbar.pack(side='right', fill='y')
        
        # Bind mousewheel
        canvas.bind_all('<MouseWheel>', lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))
        
        self.gamerule_vars = {}
        
        for rule, desc, rule_type in GAMERULES:
            frame = ttk.Frame(scrollable)
            frame.pack(fill='x', pady=3)
            
            if rule_type == 'bool':
                var = tk.BooleanVar()
                self.gamerule_vars[rule] = var
                
                cb = ttk.Checkbutton(frame, text=f"{rule}", variable=var,
                                      command=lambda r=rule, v=var: self.toggle_gamerule(r, v))
                cb.pack(side='left')
                
                ttk.Label(frame, text=f"  -  {desc}", foreground='#888888').pack(side='left')
            else:
                ttk.Label(frame, text=f"{rule}:").pack(side='left')
                
                entry = ttk.Entry(frame, width=8)
                entry.pack(side='left', padx=5)
                self.gamerule_vars[rule] = entry
                
                tk.Button(frame, text="Set", command=lambda r=rule, e=entry: self.set_gamerule_int(r, e),
                          bg=BHOP['bg_button'], fg=BHOP['blue'], font=('Trebuchet MS', 9, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=5)
                
                ttk.Label(frame, text=f"  -  {desc}", foreground='#888888').pack(side='left')
        
        # Refresh button
        tk.Button(tab, text="🔄 Refresh All Gamerules", command=self.refresh_gamerules,
                  bg=BHOP['bg_button'], fg=BHOP['blue'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(pady=10)
    
    def create_scheduler_tab(self, notebook):
        """Scheduled tasks tab."""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text='  ⏰ Scheduler  ')
        
        content = ttk.Frame(tab)
        content.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(content, text="⏰ Scheduled Tasks", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        ttk.Label(content, text="Commands that run automatically at intervals",
                  foreground='#888888').pack(anchor='w')
        
        # Tasks list
        self.tasks_listbox = tk.Listbox(content, bg=BHOP['bg_dark'], fg=BHOP['cyan'],
                                         font=('Consolas', 11), height=10, selectbackground=BHOP['gold'])
        self.tasks_listbox.pack(fill='both', expand=True, pady=10)
        
        # Task controls
        btn_frame = ttk.Frame(content)
        btn_frame.pack(fill='x', pady=5)
        
        tk.Button(btn_frame, text="➕ Add Task", command=self.add_scheduled_task,
                  bg=BHOP['bg_button'], fg=BHOP['green'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=3)
        tk.Button(btn_frame, text="✏️ Edit Task", command=self.edit_scheduled_task,
                  bg=BHOP['bg_button'], fg=BHOP['blue'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=3)
        tk.Button(btn_frame, text="🗑️ Delete Task", command=self.delete_scheduled_task,
                  bg=BHOP['red_dark'], fg=BHOP['text'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['red']).pack(side='left', padx=3)
        tk.Button(btn_frame, text="⏸️ Toggle", command=self.toggle_scheduled_task,
                  bg=BHOP['bg_button'], fg=BHOP['gold'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=3)
        
        # Preset tasks
        ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
        ttk.Label(content, text="📦 Quick Presets", style='SubHeader.TLabel').pack(anchor='w', pady=(0, 10))
        
        preset_frame = ttk.Frame(content)
        preset_frame.pack(fill='x')
        
        presets = [
            ("Save Every 5min", "save-all", 300),
            ("Discord Reminder (10min)", 'tellraw @a [{"text":"[House of Poe] ","color":"gold"},{"text":"Join our Discord: discord.gg/HAtqezdy4G","color":"aqua"}]', 600),
            ("Auto Day (No Night)", "time set day", 600),
        ]
        
        for name, cmd, interval in presets:
            tk.Button(preset_frame, text=name,
                      command=lambda n=name, c=cmd, i=interval: self.add_preset_task(n, c, i),
                      bg=BHOP['bg_button'], fg=BHOP['text'], font=('Trebuchet MS', 9, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=3)
        
        self.refresh_tasks_list()
    
    def create_console_tab(self, notebook):
        """Raw console tab."""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text='  🖥️ Console  ')
        
        content = ttk.Frame(tab)
        content.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(content, text="🖥️ RCON Console", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        # Command input
        cmd_frame = ttk.Frame(content)
        cmd_frame.pack(fill='x', pady=5)
        
        self.console_entry = ttk.Entry(cmd_frame, font=('Consolas', 11))
        self.console_entry.pack(side='left', fill='x', expand=True)
        self.console_entry.bind('<Return>', lambda e: self.run_console_command())
        self.console_entry.bind('<Up>', self.history_up)
        self.console_entry.bind('<Down>', self.history_down)
        
        tk.Button(cmd_frame, text="Run", command=self.run_console_command,
                  bg=BHOP['bg_button'], fg=BHOP['red'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover'], width=10).pack(side='left', padx=5)
        tk.Button(cmd_frame, text="Clear", command=self.clear_console,
                  bg=BHOP['bg_button'], fg=BHOP['text'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover'], width=10).pack(side='left', padx=2)
        
        # Output
        self.console_output = scrolledtext.ScrolledText(content, bg=BHOP['bg_dark'], fg=BHOP['cyan'],
                                                         font=('Consolas', 11), height=20)
        self.console_output.pack(fill='both', expand=True, pady=10)
        self.console_output.insert('end', "Console ready. Type 'help' for commands.\n")
        self.console_output.configure(state='disabled')
        
        # Quick commands
        quick_frame = ttk.Frame(content)
        quick_frame.pack(fill='x')
        
        for cmd in ['help', 'list', 'save-all', 'difficulty', 'seed', 'banlist', 'whitelist list', 'op']:
            tk.Button(quick_frame, text=cmd, command=lambda c=cmd: self.quick_console(c),
                      bg=BHOP['bg_button'], fg=BHOP['text'], font=('Trebuchet MS', 9, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=2)
    
    def create_fun_tab(self, notebook):
        """Fun features tab."""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text='  🎉 Fun  ')
        
        # Create sub-notebook for fun categories
        fun_notebook = ttk.Notebook(tab)
        fun_notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # ASCII Art tab
        ascii_tab = ttk.Frame(fun_notebook)
        fun_notebook.add(ascii_tab, text='  ASCII Art  ')
        
        ttk.Label(ascii_tab, text="🎨 ASCII Art Sender", style='Header.TLabel').pack(anchor='w', padx=20, pady=10)
        
        ascii_btns = ttk.Frame(ascii_tab)
        ascii_btns.pack(fill='x', padx=20)
        
        for art, emoji in [('creeper', '💀'), ('heart', '❤️'), ('star', '⭐'), ('rainbow', '🌈'), ('fancy', '✨')]:
            tk.Button(ascii_btns, text=f"{emoji} {art.title()}", command=lambda a=art: self.send_ascii(a),
                      bg=BHOP['bg_button'], fg=BHOP['text'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover'], width=12).pack(side='left', padx=3)
        
        # Custom ASCII
        ttk.Label(ascii_tab, text="Custom ASCII (one line per row):", style='SubHeader.TLabel').pack(anchor='w', padx=20, pady=(20, 5))
        
        self.custom_ascii_text = scrolledtext.ScrolledText(ascii_tab, bg=BHOP['bg_dark'], fg=BHOP['cyan'],
                                                            font=('Consolas', 11), height=8)
        self.custom_ascii_text.pack(fill='x', padx=20, pady=5)
        
        ascii_send_frame = ttk.Frame(ascii_tab)
        ascii_send_frame.pack(fill='x', padx=20)
        
        ttk.Label(ascii_send_frame, text="Color:").pack(side='left')
        self.ascii_color_combo = ttk.Combobox(ascii_send_frame, values=list(MC_COLORS.keys()), width=15)
        self.ascii_color_combo.set('green')
        self.ascii_color_combo.pack(side='left', padx=5)
        
        tk.Button(ascii_send_frame, text="Send ASCII", command=self.send_custom_ascii,
                  bg=BHOP['bg_button'], fg=BHOP['red'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=10)
        
        # Fake Messages tab
        fake_tab = ttk.Frame(fun_notebook)
        fun_notebook.add(fake_tab, text='  Fake Messages  ')
        
        ttk.Label(fake_tab, text="🎭 Fake System Messages", style='Header.TLabel').pack(anchor='w', padx=20, pady=10)
        
        fake_frame = ttk.Frame(fake_tab)
        fake_frame.pack(fill='x', padx=20, pady=5)
        
        ttk.Label(fake_frame, text="Player:").pack(side='left')
        self.fake_player_entry = ttk.Entry(fake_frame, width=20)
        self.fake_player_entry.pack(side='left', padx=5)
        
        ttk.Label(fake_frame, text="Reason:").pack(side='left', padx=(10, 0))
        self.fake_reason_entry = ttk.Entry(fake_frame, width=30)
        self.fake_reason_entry.insert(0, "Breaking server rules")
        self.fake_reason_entry.pack(side='left', padx=5)
        
        fake_btns = ttk.Frame(fake_tab)
        fake_btns.pack(fill='x', padx=20, pady=10)
        
        tk.Button(fake_btns, text="Fake Ban", command=self.send_fake_ban,
                  bg=BHOP['red_dark'], fg=BHOP['text'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['red']).pack(side='left', padx=3)
        tk.Button(fake_btns, text="Fake Kick", command=self.send_fake_kick,
                  bg=BHOP['bg_button'], fg=BHOP['gold'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=3)
        tk.Button(fake_btns, text="Fake Join", command=self.send_fake_join,
                  bg=BHOP['bg_button'], fg=BHOP['green'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=3)
        tk.Button(fake_btns, text="Fake Leave", command=self.send_fake_leave,
                  bg=BHOP['bg_button'], fg=BHOP['blue'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=3)
        tk.Button(fake_btns, text="Fake Death", command=self.send_fake_death,
                  bg=BHOP['bg_button'], fg=BHOP['purple'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=3)
        
        # Sounds tab
        sounds_tab = ttk.Frame(fun_notebook)
        fun_notebook.add(sounds_tab, text='  Sounds  ')
        
        ttk.Label(sounds_tab, text="🔊 Play Sounds", style='Header.TLabel').pack(anchor='w', padx=20, pady=10)
        
        sound_frame = ttk.Frame(sounds_tab)
        sound_frame.pack(fill='x', padx=20, pady=5)
        
        ttk.Label(sound_frame, text="Sound:").pack(side='left')
        self.sound_combo = ttk.Combobox(sound_frame, values=[
            'entity.wither.spawn', 'entity.ender_dragon.growl', 'entity.lightning_bolt.thunder',
            'entity.wolf.howl', 'entity.ghast.scream', 'entity.creeper.primed',
            'entity.player.levelup', 'block.anvil.land', 'block.bell.use',
            'ui.toast.challenge_complete', 'music.dragon', 'ambient.cave'
        ], width=30)
        self.sound_combo.set('entity.wither.spawn')
        self.sound_combo.pack(side='left', padx=5)
        
        ttk.Label(sound_frame, text="Target:").pack(side='left', padx=(15, 0))
        self.sound_target_combo = ttk.Combobox(sound_frame, values=['@a (All Players)'], width=20)
        self.sound_target_combo.set('@a (All Players)')
        self.sound_target_combo.pack(side='left', padx=5)
        
        tk.Button(sound_frame, text="🔄", command=self.refresh_sound_targets,
                  bg=BHOP['bg_button'], fg=BHOP['gold'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover'], width=2).pack(side='left', padx=2)
        
        tk.Button(sound_frame, text="Play", command=self.play_sound,
                  bg=BHOP['bg_button'], fg=BHOP['blue'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=10)
        
        # Quick sounds
        quick_sounds = ttk.Frame(sounds_tab)
        quick_sounds.pack(fill='x', padx=20, pady=10)
        
        for name, sound in [("⚡ Thunder", "entity.lightning_bolt.thunder"),
                             ("👻 Ghast", "entity.ghast.scream"),
                             ("💀 Wither", "entity.wither.spawn"),
                             ("🐉 Dragon", "entity.ender_dragon.growl"),
                             ("🎉 Level Up", "entity.player.levelup")]:
            tk.Button(quick_sounds, text=name, command=lambda s=sound: self.play_sound_quick(s),
                      bg=BHOP['bg_button'], fg=BHOP['text'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left', padx=3)
        
        # Rainbow Text tab
        rainbow_tab = ttk.Frame(fun_notebook)
        fun_notebook.add(rainbow_tab, text='  Rainbow Text  ')
        
        ttk.Label(rainbow_tab, text="🌈 Rainbow Text Generator", style='Header.TLabel').pack(anchor='w', padx=20, pady=10)
        
        rainbow_frame = ttk.Frame(rainbow_tab)
        rainbow_frame.pack(fill='x', padx=20, pady=5)
        
        self.rainbow_entry = ttk.Entry(rainbow_frame, width=50, font=('Trebuchet MS', 12))
        self.rainbow_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        tk.Button(rainbow_frame, text="🌈 Send Rainbow", command=self.send_rainbow_text,
                  bg=BHOP['bg_button'], fg=BHOP['red'], font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2, cursor='hand2', activebackground=BHOP['bg_hover']).pack(side='left')
        
        # Options
        options_frame = ttk.Frame(rainbow_tab)
        options_frame.pack(fill='x', padx=20, pady=10)
        
        self.rainbow_bold = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Bold", variable=self.rainbow_bold).pack(side='left')
        
        self.rainbow_obfuscated = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Obfuscated", variable=self.rainbow_obfuscated).pack(side='left', padx=10)
    
    # ==========================================================================
    # ACTION METHODS
    # ==========================================================================
    
    def log(self, message, success=True):
        """Log to console output."""
        self.console_output.configure(state='normal')
        timestamp = time.strftime("%H:%M:%S")
        self.console_output.insert('end', f"[{timestamp}] {message}\n")
        self.console_output.see('end')
        self.console_output.configure(state='disabled')
    
    def quick_command(self, cmd):
        """Run a quick command."""
        success, response = MCRcon.send_command(cmd)
        self.log(f"> {cmd}\n  {response or '(success)'}", success)
    
    def quick_console(self, cmd):
        """Set command and run."""
        self.console_entry.delete(0, 'end')
        self.console_entry.insert(0, cmd)
        self.run_console_command()
    
    def run_console_command(self):
        """Run command from console."""
        cmd = self.console_entry.get().strip()
        if not cmd:
            return
        
        self.command_history.append(cmd)
        self.history_index = len(self.command_history)
        
        success, response = MCRcon.send_command(cmd)
        self.log(f"> {cmd}", success)
        if response:
            self.log(f"  {response}", success)
        
        self.console_entry.delete(0, 'end')
    
    def history_up(self, event):
        """Navigate command history up."""
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.console_entry.delete(0, 'end')
            self.console_entry.insert(0, self.command_history[self.history_index])
    
    def history_down(self, event):
        """Navigate command history down."""
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.console_entry.delete(0, 'end')
            self.console_entry.insert(0, self.command_history[self.history_index])
        else:
            self.history_index = len(self.command_history)
            self.console_entry.delete(0, 'end')
    
    def clear_console(self):
        """Clear console output."""
        self.console_output.configure(state='normal')
        self.console_output.delete('1.0', 'end')
        self.console_output.insert('end', "Console cleared.\n")
        self.console_output.configure(state='disabled')
    
    def refresh_players(self):
        """Refresh player list."""
        success, response = MCRcon.send_command('list')
        
        # Check for auth failure
        if not self.check_auth_status(response):
            return
        
        if success:
            self.players_listbox.delete(0, 'end')
            
            match = re.search(r'(\d+) of a max of (\d+)', response)
            if match:
                online, max_p = match.groups()
                self.player_count_label.config(text=f"Players: {online}/{max_p}")
            
            current_players = set()
            if ':' in response:
                players_str = response.split(':')[1].strip()
                if players_str:
                    self.players = [p.strip() for p in players_str.split(',')]
                    current_players = set(self.players)
                    for p in self.players:
                        self.players_listbox.insert('end', f"  👤 {p}")
                else:
                    self.players_listbox.insert('end', "  No players online")
            
            # Check for joins/leaves
            new_players = current_players - self.previous_players
            left_players = self.previous_players - current_players
            
            for p in new_players:
                self.notify(f"{p} joined the server")
            for p in left_players:
                self.notify(f"{p} left the server")
            
            self.previous_players = current_players
            self.status_label.config(text="● Online", foreground=BHOP['cyan'])
        else:
            self.status_label.config(text="● Offline", foreground=BHOP['red'])
    
    def notify(self, message):
        """Send desktop notification."""
        if HAS_NOTIFY:
            try:
                notification.notify(
                    title="House of Poe MC",
                    message=message,
                    timeout=5
                )
            except:
                pass
    
    def on_player_double_click(self, event):
        """Handle double-click on player."""
        selection = self.players_listbox.curselection()
        if selection:
            player = self.players_listbox.get(selection[0]).replace('👤', '').strip()
            self.player_name_entry.delete(0, 'end')
            self.player_name_entry.insert(0, player)
    
    def on_player_select(self, event):
        """Handle player selection - show action options."""
        selection = self.players_listbox.curselection()
        if selection:
            player = self.players_listbox.get(selection[0]).replace('👤', '').strip()
            if player and player != "No players online":
                self.selected_player = player
                self.selected_player_label.config(
                    text=f"Selected: {player}",
                    fg=BHOP['gold'],
                    font=('Trebuchet MS', 13, 'bold')
                )
                self.enable_player_actions(True)
            else:
                self.selected_player = None
                self.selected_player_label.config(
                    text="Select a player from the list",
                    fg=BHOP['text_dim'],
                    font=('Trebuchet MS', 11, 'italic')
                )
                self.enable_player_actions(False)
    
    def create_player_action_buttons(self):
        """Create the player action buttons panel."""
        self.selected_player = None
        self.player_action_buttons = []
        
        # Action buttons with icons, labels, colors and commands
        actions = [
            ("👢 Kick Player", self.kick_selected_player, BHOP['orange']),
            ("🔨 Ban Player", self.ban_selected_player, BHOP['red']),
            ("💬 Whisper", self.whisper_selected_player, BHOP['blue']),
            ("🎁 Give Item", self.give_selected_player, BHOP['green']),
            ("🐲 Spawn Entity", self.spawn_near_player, BHOP['purple']),
            ("🌍 Teleport To", self.tp_to_selected_player, BHOP['cyan']),
            ("📍 Bring Here", self.tp_selected_player_here, BHOP['blue']),
            ("⭐ OP Player", self.op_selected_player, BHOP['gold']),
            ("💥 Strike Lightning", self.strike_lightning_player, BHOP['gold_light']),
        ]
        
        for text, cmd, accent in actions:
            btn = tk.Button(self.player_actions_frame, text=text, command=cmd,
                           bg=BHOP['bg_button'], fg=BHOP['text'],
                           activebackground=BHOP['bg_hover'], activeforeground=BHOP['text'],
                           font=('Trebuchet MS', 10, 'bold'), width=18,
                           relief='solid', bd=2, cursor='hand2', anchor='w',
                           state='disabled', disabledforeground=BHOP['text_dim'])
            btn.pack(fill='x', pady=2)
            self.player_action_buttons.append(btn)
    
    def enable_player_actions(self, enabled):
        """Enable or disable player action buttons."""
        state = 'normal' if enabled else 'disabled'
        for btn in self.player_action_buttons:
            btn.config(state=state)
    
    def kick_selected_player(self):
        """Kick the selected player."""
        if self.selected_player:
            reason = simpledialog.askstring("Kick Reason", f"Reason for kicking {self.selected_player}:", 
                                           initialvalue="Kicked by admin")
            if reason is not None:
                success, response = MCRcon.send_command(f'kick {self.selected_player} {reason}')
                self.log(f"Kicked {self.selected_player}: {response}", success)
                self.refresh_players()
    
    def ban_selected_player(self):
        """Ban the selected player."""
        if self.selected_player:
            reason = simpledialog.askstring("Ban Reason", f"Reason for banning {self.selected_player}:",
                                           initialvalue="Banned by admin")
            if reason is not None:
                success, response = MCRcon.send_command(f'ban {self.selected_player} {reason}')
                self.log(f"Banned {self.selected_player}: {response}", success)
                self.refresh_players()
    
    def whisper_selected_player(self):
        """Send whisper to selected player."""
        if self.selected_player:
            message = simpledialog.askstring("Whisper", f"Message to {self.selected_player}:")
            if message:
                cmd = f'tell {self.selected_player} {message}'
                success, response = MCRcon.send_command(cmd)
                self.log(f"Whispered to {self.selected_player}: {message}", success)
    
    def give_selected_player(self):
        """Give item to selected player."""
        if self.selected_player:
            item = simpledialog.askstring("Give Item", "Item (e.g., minecraft:diamond):",
                                         initialvalue="minecraft:diamond")
            if item:
                amount = simpledialog.askstring("Amount", "Amount:", initialvalue="64")
                if amount:
                    success, response = MCRcon.send_command(f'give {self.selected_player} {item} {amount}')
                    self.log(f"Gave {amount}x {item} to {self.selected_player}", success)
    
    def tp_to_selected_player(self):
        """Teleport to selected player (requires another player name)."""
        if self.selected_player:
            who = simpledialog.askstring("Teleport", f"Who to teleport to {self.selected_player}?")
            if who:
                success, response = MCRcon.send_command(f'tp {who} {self.selected_player}')
                self.log(f"Teleported {who} to {self.selected_player}: {response}", success)
    
    def tp_selected_player_here(self):
        """Teleport selected player to coordinates."""
        if self.selected_player:
            coords = simpledialog.askstring("Teleport", f"Teleport {self.selected_player} to (x y z or player):")
            if coords:
                success, response = MCRcon.send_command(f'tp {self.selected_player} {coords}')
                self.log(f"Teleported {self.selected_player} to {coords}: {response}", success)
    
    def op_selected_player(self):
        """Toggle OP for selected player."""
        if self.selected_player:
            success, response = MCRcon.send_command(f'op {self.selected_player}')
            if 'Nothing changed' in response or 'already' in response.lower():
                success, response = MCRcon.send_command(f'deop {self.selected_player}')
                self.log(f"DeOP {self.selected_player}: {response}", success)
            else:
                self.log(f"OP {self.selected_player}: {response}", success)
    
    def spawn_near_player(self):
        """Spawn an entity near the selected player."""
        if self.selected_player:
            # Show entity picker dialog
            self.show_entity_spawn_dialog()
    
    def show_entity_spawn_dialog(self):
        """Show a dialog to select and spawn entities."""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Spawn Entity Near {self.selected_player}")
        dialog.geometry("400x500")
        dialog.configure(bg=BHOP['bg_dark'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Title
        tk.Label(dialog, text=f"🐲 Spawn Near {self.selected_player}",
                bg=BHOP['bg_dark'], fg=BHOP['gold'],
                font=('Trebuchet MS', 14, 'bold')).pack(pady=10)
        
        # Quick spawn buttons - common entities
        quick_frame = ttk.Frame(dialog)
        quick_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(quick_frame, text="Quick Spawn:", bg=BHOP['bg_dark'], fg=BHOP['text'],
                font=('Trebuchet MS', 10)).pack(anchor='w')
        
        btn_frame = ttk.Frame(quick_frame)
        btn_frame.pack(fill='x', pady=5)
        
        quick_mobs = [
            ("🧟 Zombie", "zombie"), ("💀 Skeleton", "skeleton"), ("🕷️ Spider", "spider"),
            ("💚 Creeper", "creeper"), ("👻 Ghast", "ghast"), ("🔥 Blaze", "blaze"),
            ("🐷 Pig", "pig"), ("🐄 Cow", "cow"), ("🐑 Sheep", "sheep"),
            ("🐺 Wolf", "wolf"), ("🐱 Cat", "cat"), ("🦜 Parrot", "parrot"),
            ("🐉 Ender Dragon", "ender_dragon"), ("💀 Wither", "wither"), ("⚡ Lightning", "lightning_bolt"),
        ]
        
        row = None
        for i, (label, entity) in enumerate(quick_mobs):
            if i % 3 == 0:
                row = ttk.Frame(btn_frame)
                row.pack(fill='x', pady=2)
            tk.Button(row, text=label, width=12,
                     bg=BHOP['bg_button'], fg=BHOP['text'],
                     font=('Trebuchet MS', 9, 'bold'),
                     relief='solid', bd=1, cursor='hand2',
                     activebackground=BHOP['bg_hover'],
                     command=lambda e=entity, d=dialog: self.do_spawn_entity(e, 1, d)).pack(side='left', padx=2)
        
        # Separator
        ttk.Separator(dialog, orient='horizontal').pack(fill='x', pady=10, padx=10)
        
        # Custom entity spawn
        custom_frame = ttk.Frame(dialog)
        custom_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(custom_frame, text="Custom Entity:", bg=BHOP['bg_dark'], fg=BHOP['text'],
                font=('Trebuchet MS', 10)).pack(anchor='w')
        
        entry_frame = ttk.Frame(custom_frame)
        entry_frame.pack(fill='x', pady=5)
        
        tk.Label(entry_frame, text="Entity:", bg=BHOP['bg_dark'], fg=BHOP['text']).pack(side='left')
        entity_entry = tk.Entry(entry_frame, bg=BHOP['bg_panel'], fg=BHOP['text'],
                               font=('Trebuchet MS', 10), width=20,
                               insertbackground=BHOP['gold'])
        entity_entry.insert(0, "minecraft:zombie")
        entity_entry.pack(side='left', padx=5)
        
        tk.Label(entry_frame, text="Count:", bg=BHOP['bg_dark'], fg=BHOP['text']).pack(side='left', padx=(10,0))
        count_entry = tk.Entry(entry_frame, bg=BHOP['bg_panel'], fg=BHOP['text'],
                              font=('Trebuchet MS', 10), width=5,
                              insertbackground=BHOP['gold'])
        count_entry.insert(0, "1")
        count_entry.pack(side='left', padx=5)
        
        def spawn_custom():
            entity = entity_entry.get().strip()
            try:
                count = int(count_entry.get().strip())
            except:
                count = 1
            if entity:
                self.do_spawn_entity(entity, count, dialog)
        
        tk.Button(entry_frame, text="Spawn", bg=BHOP['bg_button'], fg=BHOP['green'],
                 font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2,
                 cursor='hand2', activebackground=BHOP['bg_hover'],
                 command=spawn_custom).pack(side='left', padx=10)
        
        # Close button
        tk.Button(dialog, text="Close", bg=BHOP['bg_button'], fg=BHOP['text'],
                 font=('Trebuchet MS', 10, 'bold'), relief='solid', bd=2,
                 cursor='hand2', activebackground=BHOP['bg_hover'], width=15,
                 command=dialog.destroy).pack(pady=15)
    
    def do_spawn_entity(self, entity, count, dialog=None):
        """Actually spawn the entity near the selected player."""
        if not self.selected_player:
            return
        
        # Remove minecraft: prefix if present for cleaner logging
        entity_name = entity.replace('minecraft:', '')
        
        for i in range(min(count, 50)):  # Limit to 50 to prevent spam
            # Use execute at player to spawn at their location
            cmd = f'execute at {self.selected_player} run summon minecraft:{entity_name} ~ ~ ~'
            success, response = MCRcon.send_command(cmd)
            if not success:
                self.log(f"Failed to spawn {entity_name}: {response}", False)
                break
        
        self.log(f"Spawned {count}x {entity_name} at {self.selected_player}", True)
        
        if dialog:
            dialog.destroy()
    
    def strike_lightning_player(self):
        """Strike lightning at the selected player."""
        if self.selected_player:
            cmd = f'execute at {self.selected_player} run summon minecraft:lightning_bolt ~ ~ ~'
            success, response = MCRcon.send_command(cmd)
            self.log(f"⚡ Lightning struck {self.selected_player}!", success)

    def set_msg_color(self, color):
        """Set message color."""
        self.selected_msg_color = color
    
    def send_broadcast(self):
        """Send broadcast message."""
        prefix = self.prefix_entry.get()
        message = self.message_entry.get().strip()
        
        if not message:
            return
        
        safe_msg = message.replace('"', '\\"')
        safe_prefix = prefix.replace('"', '\\"')
        
        cmd = f'tellraw @a [{{"text":"{safe_prefix} ","color":"{self.selected_prefix_color}","bold":true}},{{"text":"{safe_msg}","color":"{self.selected_msg_color}"}}]'
        success, _ = MCRcon.send_command(cmd)
        
        self.log(f"Broadcast: {message}", success)
        if success:
            self.message_entry.delete(0, 'end')
    
    def send_title(self):
        """Send title message."""
        title = self.title_entry.get().strip()
        subtitle = self.subtitle_entry.get().strip()
        fadein = self.title_fadein.get()
        stay = self.title_stay.get()
        fadeout = self.title_fadeout.get()
        
        # Set times
        MCRcon.send_command(f'title @a times {fadein} {stay} {fadeout}')
        
        if subtitle:
            MCRcon.send_command(f'title @a subtitle {{"text":"{subtitle}","color":"gray"}}')
        
        if title:
            success, _ = MCRcon.send_command(f'title @a title {{"text":"{title}","color":"gold","bold":true}}')
            self.log(f"Title sent: {title}", success)
    
    def send_actionbar(self):
        """Send action bar message."""
        message = self.actionbar_entry.get().strip()
        if message:
            success, _ = MCRcon.send_command(f'title @a actionbar {{"text":"{message}","color":"yellow"}}')
            self.log(f"Action bar: {message}", success)
    
    def send_whisper(self):
        """Send private message."""
        player = self.pm_player_entry.get().strip()
        message = self.pm_message_entry.get().strip()
        
        if player and message:
            success, _ = MCRcon.send_command(f'tell {player} {message}')
            self.log(f"Whisper to {player}: {message}", success)
    
    def quick_msg(self, msg, color='white'):
        """Send quick message."""
        cmd = f'tellraw @a [{{"text":"[House of Poe] ","color":"gold","bold":true}},{{"text":"{msg}","color":"{color}"}}]'
        MCRcon.send_command(cmd)
        self.log(f"Quick message: {msg}", True)
    
    def kick_player(self):
        """Kick a player."""
        player = self.player_name_entry.get().strip()
        reason = self.kick_reason_entry.get().strip()
        if player:
            success, response = MCRcon.send_command(f'kick {player} {reason}')
            self.log(f"Kick {player}: {response}", success)
            self.refresh_players()
    
    def ban_player(self):
        """Ban a player."""
        player = self.player_name_entry.get().strip()
        reason = self.kick_reason_entry.get().strip()
        if player:
            success, response = MCRcon.send_command(f'ban {player} {reason}')
            self.log(f"Ban {player}: {response}", success)
            self.refresh_players()
    
    def pardon_player(self):
        """Pardon a player."""
        player = self.player_name_entry.get().strip()
        if not player:
            messagebox.showwarning("Warning", "Select a player first")
            return
        success, response = MCRcon.send_command(f'pardon {player}')
        self.log(f"Pardon {player}: {response}", success)
    
    def op_player(self):
        """OP a player."""
        player = self.player_name_entry.get().strip()
        if not player:
            messagebox.showwarning("Warning", "Select a player first")
            return
        success, response = MCRcon.send_command(f'op {player}')
        self.log(f"OP {player}: {response}", success)
        if success:
            messagebox.showinfo("Success", f"OP {player}: {response}")
        else:
            messagebox.showerror("Error", f"Failed to OP {player}: {response}")
    
    def deop_player(self):
        """DeOP a player."""
        player = self.player_name_entry.get().strip()
        if not player:
            messagebox.showwarning("Warning", "Select a player first")
            return
        success, response = MCRcon.send_command(f'deop {player}')
        self.log(f"DeOP {player}: {response}", success)
        if success:
            messagebox.showinfo("Success", f"DeOP {player}: {response}")
        else:
            messagebox.showerror("Error", f"Failed to DeOP {player}: {response}")
    
    def give_item(self):
        """Give item to player."""
        player = self.player_name_entry.get().strip()
        item = self.give_item_entry.get().strip()
        amount = self.give_amount_entry.get().strip()
        
        if player and item:
            success, response = MCRcon.send_command(f'give {player} {item} {amount}')
            self.log(f"Give {amount}x {item} to {player}: {response}", success)
    
    def quick_give(self, item):
        """Quick give item."""
        player = self.player_name_entry.get().strip()
        if player:
            MCRcon.send_command(f'give {player} {item} 64')
            self.log(f"Gave 64x {item} to {player}", True)
    
    def refresh_player_combo(self):
        """Refresh the player management dropdown with online players."""
        players = ['@a', '@r', '@p'] + self.players
        self.player_name_combo['values'] = players
        self.log("Refreshed player list", True)
    
    def refresh_tp_players(self):
        """Refresh the teleport player dropdowns with online players."""
        players = ['@a', '@r', '@p'] + self.players
        self.tp_from_combo['values'] = players
        self.tp_target_combo['values'] = players
        self.log("Refreshed teleport player list", True)
    
    def teleport_player(self):
        """Teleport player to target."""
        # Try to get from combo first, fallback to player_name_entry
        from_player = self.tp_from_combo.get().strip()
        if not from_player:
            from_player = self.player_name_entry.get().strip()
        target = self.tp_target_combo.get().strip()
        
        if not from_player:
            messagebox.showwarning("Warning", "Select or enter a player to teleport")
            return
        if not target:
            messagebox.showwarning("Warning", "Enter a destination (player name or x y z)")
            return
            
        success, response = MCRcon.send_command(f'tp {from_player} {target}')
        self.log(f"Teleport {from_player} → {target}: {response}", success)
    
    def bring_player(self):
        """Bring player to coordinates."""
        from_player = self.tp_from_combo.get().strip()
        if not from_player:
            from_player = self.player_name_entry.get().strip()
        target = simpledialog.askstring("Bring Player", "Enter destination coordinates (x y z):")
        if from_player and target:
            success, response = MCRcon.send_command(f'tp {from_player} {target}')
            self.log(f"Brought {from_player} to {target}: {response}", success)
    
    def apply_effect(self):
        """Apply effect to player."""
        player = self.player_name_entry.get().strip()
        effect = self.effect_combo.get()
        duration = self.effect_duration.get()
        level = self.effect_level.get()
        
        if player and effect:
            success, response = MCRcon.send_command(f'effect give {player} minecraft:{effect} {duration} {int(level)-1}')
            self.log(f"Effect {effect} on {player}: {response}", success)
    
    def clear_effects(self):
        """Clear all effects from player."""
        player = self.player_name_entry.get().strip()
        if player:
            success, response = MCRcon.send_command(f'effect clear {player}')
            self.log(f"Cleared effects from {player}: {response}", success)
    
    def show_whitelist(self):
        """Show whitelist."""
        success, response = MCRcon.send_command('whitelist list')
        if success:
            messagebox.showinfo("Whitelist", response)
        self.log(f"Whitelist: {response}", success)
    
    def whitelist_action(self, action):
        """Add or remove from whitelist."""
        player = self.player_name_entry.get().strip()
        if player:
            success, response = MCRcon.send_command(f'whitelist {action} {player}')
            self.log(f"Whitelist {action} {player}: {response}", success)
    
    def toggle_whitelist(self):
        """Toggle whitelist on/off."""
        # Check current status and toggle
        success, response = MCRcon.send_command('whitelist on')
        if 'already' in response.lower():
            success, response = MCRcon.send_command('whitelist off')
        self.log(f"Whitelist toggle: {response}", success)
    
    def kick_all(self):
        """Kick all players."""
        if messagebox.askyesno("Kick All", "Kick all players from the server?"):
            for player in self.players:
                MCRcon.send_command(f'kick {player} Server maintenance')
            self.log("Kicked all players", True)
            self.refresh_players()
    
    def confirm_stop(self):
        """Confirm server stop."""
        if messagebox.askyesno("Stop Server", "Are you sure you want to stop the server?"):
            self.quick_msg("Server shutting down in 5 seconds!", "red")
            self.root.after(5000, lambda: MCRcon.send_command('stop'))
            self.log("Server stop command sent", True)
    
    def show_banlist(self):
        """Show banlist popup."""
        success, response = MCRcon.send_command('banlist')
        if success:
            popup = tk.Toplevel(self.root)
            popup.title("Banned Players")
            popup.geometry("500x400")
            popup.configure(bg=BHOP['bg_dark'])
            
            ttk.Label(popup, text="🚫 Banned Players", style='Header.TLabel').pack(pady=15)
            
            text = scrolledtext.ScrolledText(popup, bg=BHOP['bg_dark'], fg=BHOP['gold'],
                                              font=('Consolas', 11))
            text.pack(fill='both', expand=True, padx=20, pady=(0, 20))
            text.insert('end', response if response else "No players banned.")
            text.configure(state='disabled')
    
    def show_ops(self):
        """Show server operators list popup."""
        from tkinter import filedialog
        
        popup = tk.Toplevel(self.root)
        popup.title("Server Operators")
        popup.geometry("550x500")
        popup.configure(bg=BHOP['bg_dark'])
        
        ttk.Label(popup, text="⭐ Server Operators", style='Header.TLabel').pack(pady=15)
        
        # Button frame at top
        btn_frame = tk.Frame(popup, bg=BHOP['bg_dark'])
        btn_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        text = scrolledtext.ScrolledText(popup, bg=BHOP['bg_dark'], fg=BHOP['gold'],
                                          font=('Consolas', 11))
        text.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        def load_ops_json():
            """Open file dialog to load ops.json"""
            filepath = filedialog.askopenfilename(
                title="Select ops.json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile="ops.json"
            )
            if filepath:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        ops_data = json.load(f)
                    
                    text.configure(state='normal')
                    text.delete('1.0', 'end')
                    text.insert('end', f"📁 Loaded: {filepath}\n")
                    text.insert('end', "─" * 50 + "\n\n")
                    
                    if ops_data:
                        text.insert('end', "⭐ SERVER OPERATORS:\n\n")
                        for i, op in enumerate(ops_data, 1):
                            name = op.get('name', 'Unknown')
                            uuid = op.get('uuid', 'N/A')
                            level = op.get('level', 4)
                            bypass = op.get('bypassesPlayerLimit', False)
                            
                            text.insert('end', f"  {i}. {name}\n")
                            text.insert('end', f"     UUID: {uuid}\n")
                            text.insert('end', f"     Level: {level} | Bypass Limit: {'Yes' if bypass else 'No'}\n\n")
                        
                        text.insert('end', "─" * 50 + "\n")
                        text.insert('end', f"Total Operators: {len(ops_data)}\n")
                    else:
                        text.insert('end', "No operators found in ops.json\n")
                    
                    text.configure(state='disabled')
                    
                except json.JSONDecodeError as e:
                    messagebox.showerror("Error", f"Invalid JSON file: {e}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to read file: {e}")
        
        # Load ops.json button
        tk.Button(btn_frame, text="📂 Open ops.json", command=load_ops_json,
                 bg=BHOP['gold'], fg=BHOP['bg_dark'],
                 font=('Trebuchet MS', 10, 'bold'), cursor='hand2').pack(side='left', padx=5)
        
        # Initial content
        # Try RCON command first
        success, response = MCRcon.send_command('op')
        if success and response and 'Unknown' not in response:
            text.insert('end', f"RCON Response:\n{response}\n\n")
        
        # Show online players
        success, list_response = MCRcon.send_command('list')
        if success and ':' in list_response:
            players_str = list_response.split(':')[1].strip()
            if players_str:
                players = [p.strip() for p in players_str.split(',')]
                text.insert('end', "👥 Online Players:\n")
                for p in players:
                    text.insert('end', f"  • {p}\n")
                text.insert('end', "\n")
        
        text.insert('end', "─" * 50 + "\n")
        text.insert('end', "💡 Click 'Open ops.json' to view the full operator list\n")
        text.insert('end', "   from your server's ops.json file.\n\n")
        text.insert('end', "📌 Op Commands:\n")
        text.insert('end', "   /op <player>   - Grant operator status\n")
        text.insert('end', "   /deop <player> - Remove operator status\n")
        
        text.configure(state='disabled')
        self.log("Opened operators panel", True)
    
    def query_time(self):
        """Query world time."""
        success1, daytime = MCRcon.send_command('time query daytime')
        success2, day = MCRcon.send_command('time query day')
        
        if success1 and success2:
            try:
                daytime_match = re.search(r'(\d+)', daytime)
                day_match = re.search(r'(\d+)', day)
                
                ticks = int(daytime_match.group(1)) if daytime_match else 0
                day_num = int(day_match.group(1)) if day_match else 0
                
                hours = ((ticks + 6000) % 24000) // 1000
                minutes = ((ticks + 6000) % 1000) * 60 // 1000
                
                if hours >= 12:
                    time_str = f"{hours-12 if hours > 12 else 12}:{minutes:02d} PM"
                else:
                    time_str = f"{hours if hours > 0 else 12}:{minutes:02d} AM"
                
                if 0 <= ticks < 6000:
                    period = "Morning ☀️"
                elif 6000 <= ticks < 12000:
                    period = "Afternoon 🌤️"
                elif 12000 <= ticks < 13000:
                    period = "Sunset 🌅"
                elif 13000 <= ticks < 23000:
                    period = "Night 🌙"
                else:
                    period = "Dawn 🌄"
                
                info_text = f"🕐 {time_str} ({period})\n📅 Day {day_num}\n⏱️ {ticks} ticks"
                self.info_display.config(text=info_text)
            except:
                self.info_display.config(text=f"Time: {daytime}\nDay: {day}")
    
    def query_server_info(self):
        """Query server info popup."""
        popup = tk.Toplevel(self.root)
        popup.title("Server Information")
        popup.geometry("600x500")
        popup.configure(bg=BHOP['bg_dark'])
        
        ttk.Label(popup, text="📊 Server Information", style='Header.TLabel').pack(pady=15)
        
        text = scrolledtext.ScrolledText(popup, bg=BHOP['bg_dark'], fg=BHOP['cyan'],
                                          font=('Consolas', 11))
        text.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        info = []
        for label, cmd in [("👥 PLAYERS", "list"), ("🕐 TIME", "time query day"),
                           ("⚔️ DIFFICULTY", "difficulty"), ("🌱 SEED", "seed"),
                           ("🚫 BANS", "banlist"), ("📋 WHITELIST", "whitelist list")]:
            success, response = MCRcon.send_command(cmd)
            info.append(f"{label}\n{response}\n")
        
        text.insert('end', '\n'.join(info))
        text.configure(state='disabled')
    
    def set_custom_time(self):
        """Set custom time."""
        ticks = self.custom_time_entry.get().strip()
        if ticks:
            self.quick_command(f'time set {ticks}')
    
    def add_days(self):
        """Add days to time."""
        days = self.add_days_entry.get().strip()
        if days:
            ticks = int(days) * 24000
            self.quick_command(f'time add {ticks}')
    
    def set_world_border(self):
        """Set world border."""
        size = self.border_size_entry.get().strip()
        if size:
            self.quick_command(f'worldborder set {size}')
    
    def get_world_border(self):
        """Get world border."""
        success, response = MCRcon.send_command('worldborder get')
        self.log(f"World border: {response}", success)
    
    def set_world_spawn(self):
        """Set world spawn."""
        x = self.spawn_x_entry.get()
        y = self.spawn_y_entry.get()
        z = self.spawn_z_entry.get()
        self.quick_command(f'setworldspawn {x} {y} {z}')
    
    def toggle_gamerule(self, rule, var):
        """Toggle a boolean gamerule."""
        value = 'true' if var.get() else 'false'
        success, response = MCRcon.send_command(f'gamerule {rule} {value}')
        self.log(f"Gamerule {rule} = {value}: {response}", success)
    
    def set_gamerule_int(self, rule, entry):
        """Set an integer gamerule."""
        value = entry.get().strip()
        if value:
            success, response = MCRcon.send_command(f'gamerule {rule} {value}')
            self.log(f"Gamerule {rule} = {value}: {response}", success)
    
    def refresh_gamerules(self):
        """Refresh all gamerule values."""
        for rule, desc, rule_type in GAMERULES:
            success, response = MCRcon.send_command(f'gamerule {rule}')
            if success:
                match = re.search(r'is currently set to:\s*(\S+)', response)
                if match:
                    value = match.group(1)
                    if rule_type == 'bool':
                        self.gamerule_vars[rule].set(value.lower() == 'true')
                    else:
                        self.gamerule_vars[rule].delete(0, 'end')
                        self.gamerule_vars[rule].insert(0, value)
        
        self.log("Refreshed gamerules", True)
    
    # Scheduler methods
    def add_scheduled_task(self):
        """Add a new scheduled task."""
        name = simpledialog.askstring("Task Name", "Enter task name:")
        if not name:
            return
        command = simpledialog.askstring("Command", "Enter RCON command:")
        if not command:
            return
        interval = simpledialog.askinteger("Interval", "Interval in seconds:", minvalue=10)
        if not interval:
            return
        
        task = ScheduledTask(name, command, interval)
        self.scheduled_tasks.append(task)
        self.refresh_tasks_list()
        self.save_config()
    
    def add_preset_task(self, name, command, interval):
        """Add a preset task."""
        task = ScheduledTask(name, command, interval)
        self.scheduled_tasks.append(task)
        self.refresh_tasks_list()
        self.save_config()
        self.log(f"Added task: {name}", True)
    
    def edit_scheduled_task(self):
        """Edit selected task."""
        selection = self.tasks_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        task = self.scheduled_tasks[idx]
        
        new_interval = simpledialog.askinteger("Edit Interval", f"New interval for '{task.name}' (seconds):",
                                                initialvalue=task.interval, minvalue=10)
        if new_interval:
            task.interval = new_interval
            self.refresh_tasks_list()
            self.save_config()
    
    def delete_scheduled_task(self):
        """Delete selected task."""
        selection = self.tasks_listbox.curselection()
        if selection:
            idx = selection[0]
            del self.scheduled_tasks[idx]
            self.refresh_tasks_list()
            self.save_config()
    
    def toggle_scheduled_task(self):
        """Toggle task enabled/disabled."""
        selection = self.tasks_listbox.curselection()
        if selection:
            idx = selection[0]
            self.scheduled_tasks[idx].enabled = not self.scheduled_tasks[idx].enabled
            self.refresh_tasks_list()
            self.save_config()
    
    def refresh_tasks_list(self):
        """Refresh tasks listbox."""
        self.tasks_listbox.delete(0, 'end')
        for task in self.scheduled_tasks:
            status = "✅" if task.enabled else "⏸️"
            self.tasks_listbox.insert('end', f"{status} {task.name} - Every {task.interval}s - {task.command[:30]}...")
    
    def run_scheduled_tasks(self):
        """Background thread for scheduled tasks."""
        while self.scheduler_running:
            now = datetime.now()
            for task in self.scheduled_tasks:
                if task.enabled and now >= task.next_run:
                    success, response = MCRcon.send_command(task.command)
                    self.root.after(0, lambda t=task, s=success: self.log(f"[Scheduler] {t.name}: {t.command}", s))
                    task.last_run = now
                    task.next_run = now + timedelta(seconds=task.interval)
            time.sleep(1)
    
    # Favorites
    def refresh_favorites_list(self):
        """Refresh favorites display."""
        for widget in self.favorites_frame.winfo_children():
            widget.destroy()
        
        for cmd in self.favorite_commands:
            frame = ttk.Frame(self.favorites_frame)
            frame.pack(fill='x', pady=2)
            
            tk.Button(frame, text="▶", command=lambda c=cmd: self.quick_command(c),
                      bg=BHOP['bg_button'], fg=BHOP['green'], font=('Trebuchet MS', 8, 'bold'), relief='solid', bd=1, cursor='hand2', activebackground=BHOP['bg_hover'], width=2).pack(side='left')
            ttk.Label(frame, text=cmd[:35], font=('Consolas', 9)).pack(side='left', padx=5)
            tk.Button(frame, text="✕", command=lambda c=cmd: self.remove_favorite(c),
                      bg=BHOP['bg_button'], fg=BHOP['red'], font=('Trebuchet MS', 8, 'bold'), relief='solid', bd=1, cursor='hand2', activebackground=BHOP['bg_hover'], width=2).pack(side='right')
    
    def add_favorite(self):
        """Add command to favorites."""
        cmd = self.new_fav_entry.get().strip()
        if cmd and cmd not in self.favorite_commands:
            self.favorite_commands.append(cmd)
            self.refresh_favorites_list()
            self.save_config()
            self.new_fav_entry.delete(0, 'end')
    
    def remove_favorite(self, cmd):
        """Remove command from favorites."""
        if cmd in self.favorite_commands:
            self.favorite_commands.remove(cmd)
            self.refresh_favorites_list()
            self.save_config()
    
    # Fun methods
    def send_ascii(self, art_type):
        """Send ASCII art."""
        arts = {
            'creeper': ["████████████", "██░░██░░████", "████████████", "██░░░░░░██", "██░░██░░██"],
            'heart': ["  ██  ██  ", "████████████", "████████████", "  ████████", "    ████", "      ██"],
            'star': ["    ★    ", "   ★★★   ", "  ★★★★★  ", " ★★★★★★★ ", "★★★★★★★★★"],
            'rainbow': ["█" * 30],  # Will be sent with rainbow colors
            'fancy': None  # Special handling
        }
        
        if art_type == 'fancy':
            cmd = 'tellraw @a [{"text":"★ ","color":"gold"},{"text":"H","color":"red","bold":true},{"text":"O","color":"gold","bold":true},{"text":"U","color":"yellow","bold":true},{"text":"S","color":"green","bold":true},{"text":"E","color":"aqua","bold":true},{"text":" O","color":"blue","bold":true},{"text":"F","color":"light_purple","bold":true},{"text":" P","color":"red","bold":true},{"text":"O","color":"gold","bold":true},{"text":"E","color":"yellow","bold":true},{"text":" ★","color":"gold"}]'
            MCRcon.send_command(cmd)
            return
        
        if art_type == 'rainbow':
            self.send_rainbow_text_direct("HOUSE OF POE")
            return
        
        lines = arts.get(art_type, [])
        color = {'creeper': 'green', 'heart': 'red', 'star': 'gold'}.get(art_type, 'white')
        
        for line in lines:
            safe = line.replace('"', '\\"')
            MCRcon.send_command(f'tellraw @a {{"text":"{safe}","color":"{color}"}}')
            time.sleep(0.03)
        
        self.log(f"Sent {art_type} ASCII art", True)
    
    def send_custom_ascii(self):
        """Send custom ASCII art."""
        text = self.custom_ascii_text.get('1.0', 'end').strip()
        color = self.ascii_color_combo.get()
        
        for line in text.split('\n'):
            if line:
                safe = line.replace('"', '\\"').replace('\\', '\\\\')
                MCRcon.send_command(f'tellraw @a {{"text":"{safe}","color":"{color}"}}')
                time.sleep(0.03)
        
        self.log("Sent custom ASCII art", True)
    
    def send_rainbow_text(self):
        """Send rainbow text."""
        text = self.rainbow_entry.get().strip()
        if text:
            self.send_rainbow_text_direct(text)
            self.rainbow_entry.delete(0, 'end')
    
    def send_rainbow_text_direct(self, text):
        """Send rainbow colored text."""
        colors = ['red', 'gold', 'yellow', 'green', 'aqua', 'blue', 'light_purple']
        parts = []
        
        bold = self.rainbow_bold.get() if hasattr(self, 'rainbow_bold') else True
        obf = self.rainbow_obfuscated.get() if hasattr(self, 'rainbow_obfuscated') else False
        
        for i, char in enumerate(text):
            color = colors[i % len(colors)]
            safe = char.replace('"', '\\"')
            part = f'{{"text":"{safe}","color":"{color}"'
            if bold:
                part += ',"bold":true'
            if obf:
                part += ',"obfuscated":true'
            part += '}'
            parts.append(part)
        
        cmd = f'tellraw @a [{",".join(parts)}]'
        MCRcon.send_command(cmd)
        self.log(f"Sent rainbow: {text}", True)
    
    def send_fake_ban(self):
        """Send fake ban message."""
        player = self.fake_player_entry.get().strip()
        reason = self.fake_reason_entry.get().strip()
        if player:
            MCRcon.send_command(f'tellraw @a {{"text":"{player} was banned by an operator.","color":"yellow","italic":true}}')
            MCRcon.send_command(f'tellraw @a {{"text":"Reason: {reason}","color":"gray"}}')
    
    def send_fake_kick(self):
        """Send fake kick message."""
        player = self.fake_player_entry.get().strip()
        reason = self.fake_reason_entry.get().strip()
        if player:
            MCRcon.send_command(f'tellraw @a {{"text":"{player} was kicked by an operator.","color":"yellow","italic":true}}')
    
    def send_fake_join(self):
        """Send fake join message."""
        player = self.fake_player_entry.get().strip()
        if player:
            MCRcon.send_command(f'tellraw @a {{"text":"{player} joined the game","color":"yellow"}}')
    
    def send_fake_leave(self):
        """Send fake leave message."""
        player = self.fake_player_entry.get().strip()
        if player:
            MCRcon.send_command(f'tellraw @a {{"text":"{player} left the game","color":"yellow"}}')
    
    def send_fake_death(self):
        """Send fake death message."""
        player = self.fake_player_entry.get().strip()
        if player:
            deaths = [
                f"{player} was slain by a Creeper",
                f"{player} fell from a high place",
                f"{player} drowned",
                f"{player} was killed by magic",
                f"{player} blew up",
            ]
            import random
            MCRcon.send_command(f'tellraw @a {{"text":"{random.choice(deaths)}","color":"gray"}}')
    
    def play_sound(self):
        """Play sound to selected player(s)."""
        sound = self.sound_combo.get()
        target = self.sound_target_combo.get()
        
        # Parse target - extract player selector
        if target.startswith('@a'):
            selector = '@a'
            target_name = 'all players'
        else:
            selector = target
            target_name = target
        
        # Execute as each target player at their position so they hear it
        cmd = f'execute as {selector} at @s run playsound minecraft:{sound} master @s ~ ~ ~ 1.0 1.0'
        success, response = MCRcon.send_command(cmd)
        if success:
            self.log(f"Played sound: {sound} to {target_name}", True)
        else:
            self.log(f"Failed to play sound: {response}", False)
    
    def refresh_sound_targets(self):
        """Refresh the sound target dropdown with online players."""
        targets = ['@a (All Players)']
        if self.players:
            targets.extend(self.players)
        self.sound_target_combo['values'] = targets
        self.log("Refreshed sound target list", True)
    
    def play_sound_quick(self, sound):
        """Quick play sound to selected target."""
        target = self.sound_target_combo.get()
        
        # Parse target - extract player selector
        if target.startswith('@a'):
            selector = '@a'
            target_name = 'all players'
        else:
            selector = target
            target_name = target
        
        cmd = f'execute as {selector} at @s run playsound minecraft:{sound} master @s ~ ~ ~ 1.0 1.0'
        success, response = MCRcon.send_command(cmd)
        if success:
            self.log(f"Played sound: {sound} to {target_name}", True)
        else:
            self.log(f"Failed to play sound: {response}", False)
    
    # Background tasks
    def start_background_tasks(self):
        """Start background threads."""
        # Status updater
        def update_status():
            while True:
                try:
                    self.root.after(0, self.refresh_players)
                except:
                    pass
                time.sleep(15)
        
        threading.Thread(target=update_status, daemon=True).start()
        
        # Scheduler
        threading.Thread(target=self.run_scheduled_tasks, daemon=True).start()
    
    def on_close(self):
        """Handle window close."""
        self.scheduler_running = False
        self.save_config()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = RconApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
