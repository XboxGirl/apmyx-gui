import sys
import yaml
import logging
import os
import traceback
import atexit
import datetime
import faulthandler
import signal

FAULT_LOG_HANDLE = None


def setup_fault_diagnostics():
    """Enable crash diagnostics early enough to catch native segfaults.

    The container mounts /config, so writing there keeps the faulthandler dump
    available after the app process exits and supervisor tears the service down.
    """
    global FAULT_LOG_HANDLE

    log_dir = os.environ.get("APMYX_CRASH_LOG_DIR", "/config/apmyx-runtime/log")
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    pid = os.getpid()

    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"python-faulthandler-{timestamp}-{pid}.log")
        FAULT_LOG_HANDLE = open(log_path, "a", buffering=1, encoding="utf-8", errors="replace")
        FAULT_LOG_HANDLE.write(f"[faulthandler] pid={pid} log={log_path}\n")
        FAULT_LOG_HANDLE.flush()
        faulthandler.enable(file=FAULT_LOG_HANDLE, all_threads=True)
    except Exception as exc:
        log_path = None
        print(f"[faulthandler] failed to open persistent fault log: {exc}", file=sys.stderr, flush=True)
        faulthandler.enable(all_threads=True)

    for signal_name in ("SIGUSR1", "SIGUSR2"):
        dump_signal = getattr(signal, signal_name, None)
        if dump_signal is None:
            continue
        try:
            if FAULT_LOG_HANDLE is not None:
                faulthandler.register(dump_signal, file=FAULT_LOG_HANDLE, all_threads=True, chain=False)
            else:
                faulthandler.register(dump_signal, all_threads=True, chain=False)
        except Exception as exc:
            print(f"[faulthandler] failed to register {signal_name}: {exc}", file=sys.stderr, flush=True)

    return log_path


def close_fault_log():
    global FAULT_LOG_HANDLE
    if FAULT_LOG_HANDLE is not None:
        try:
            FAULT_LOG_HANDLE.flush()
            FAULT_LOG_HANDLE.close()
        finally:
            FAULT_LOG_HANDLE = None


FAULT_LOG_PATH = setup_fault_diagnostics()
atexit.register(close_fault_log)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QFontDatabase, QFont, QIcon
from core.app import AppController
from ui.main_window import MainWindow
from ui.main_window.dialogs import UpdateDialog 


APP_FONT_FAMILY = "Inter Tight"
APP_FALLBACK_FONTS = '"Segoe UI", "Helvetica Neue", "Arial", sans-serif'
APP_FONT = QFont(APP_FONT_FAMILY, 9)

APP_FONT.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

APP_FONT.setStyleStrategy(QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.NoSubpixelAntialias)


FONT_FAMILY_STYLESHEET = f'font-family: "{APP_FONT_FAMILY}", {APP_FALLBACK_FONTS};'


DARK_STYLESHEET = f"""
    * {{
        {FONT_FAMILY_STYLESHEET}
    }}
    QWidget {{
        background-color: #1f1f1f;
        color: #e0e0e0;
    }}
    QMainWindow, QStatusBar {{
        background-color: #1f1f1f;
    }}
    QLineEdit {{
        background-color: #2e2e2e;
        border: 1px solid #444;
        border-radius: 4px;
        padding: 5px;
    }}
    QPushButton {{
        background-color: #4a4a4a;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 5px 10px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: #5a5a5a;
    }}
    QPushButton:pressed {{
        background-color: #6a6a6a;
    }}
    QComboBox {{
        background-color: #3c3c3c;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 3px;
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QScrollArea {{
        background-color: #1f1f1f;
        border: none;
    }}
    QScrollBar:vertical {{
        border: none;
        background: #1f1f1f;
        width: 10px;
        margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle:vertical {{
        background: #555;
        min-height: 20px;
        border-radius: 5px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QDockWidget {{
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
    }}
    QDockWidget::title {{
        background-color: #3c3c3c;
        text-align: center;
        padding: 5px;
    }}
"""

VERSION = "1.0.2"
REPO_OWNER = "rwnk-12"
REPO_NAME = "apmyx-gui"
RELEASES_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases"

def resource_path(relative_path):
    
    try:
        
        base_path = sys._MEIPASS
    except Exception:
    
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    return os.path.join(base_path, relative_path)

def setup_logging():

    log_formatter = logging.Formatter('[PYTHON] %(asctime)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any handlers configured by imported modules to avoid duplicate lines.
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    root_logger.addHandler(console_handler)

    def handle_exception(exc_type, exc_value, exc_traceback):

        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        tb_info = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logging.critical(f"Unhandled exception:\n{tb_info}")
        QApplication.quit()

    sys.excepthook = handle_exception


def load_fonts():
  
    regular_font_path = resource_path('src/assets/Inter/Inter_Tight/InterTight-VariableFont_wght.ttf')
    italic_font_path = resource_path('src/assets/Inter/Inter_Tight/InterTight-Italic-VariableFont_wght.ttf')

    if os.path.exists(regular_font_path):
        if QFontDatabase.addApplicationFont(regular_font_path) == -1:
            logging.warning(f"Failed to load Inter Tight font from: {regular_font_path}")
        else:
            logging.info("Successfully loaded Inter Tight font.")
    else:
        logging.warning(f"Inter Tight font not found at: {regular_font_path}")
        
    if os.path.exists(italic_font_path):
        if QFontDatabase.addApplicationFont(italic_font_path) == -1:
            logging.warning(f"Failed to load Inter Tight Italic font from: {italic_font_path}")
        else:
            logging.info("Successfully loaded Inter Tight Italic font.")
    else:
        logging.warning(f"Inter Tight Italic font not found at: {italic_font_path}")


def load_config():
    
    default_storefront = 'us'
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            storefront = config.get('storefront', default_storefront)
            logging.info(f"Loaded storefront '{storefront}' from config.yaml")
            return storefront.lower()
    except FileNotFoundError:
        logging.warning("config.yaml not found. Using default storefront 'us'.")
        return default_storefront
    except Exception as e:
        logging.error(f"Error loading config.yaml: {e}. Using default storefront 'us'.")
        return default_storefront

def final_cleanup():
    logging.info("Final atexit cleanup triggered.")

    os._exit(0)

atexit.register(final_cleanup)

if __name__ == "__main__":
    
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    setup_logging()
    if FAULT_LOG_PATH:
        logging.info(f"Python faulthandler crash log: {FAULT_LOG_PATH}")

    app = QApplication(sys.argv)
    
    app.setOrganizationName("rwnk-12")
    app.setApplicationName("apmyx-gui")
    
    icon_path = resource_path('src/assets/icon.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        logging.info(f"Application icon set from {icon_path}")
    else:
        logging.warning(f"Application icon not found at: {icon_path}")

    load_fonts()

    app.setFont(APP_FONT)

    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLESHEET)
    logging.info("Applied dark theme with #1f1f1f background color.")

    storefront = load_config()
    
  
    controller = AppController(storefront=storefront)
    
    controller.VERSION = VERSION
    controller.REPO_OWNER = REPO_OWNER
    controller.REPO_NAME = REPO_NAME
    controller.RELEASES_URL = RELEASES_URL

    window = MainWindow(controller)
    window.show()
    
    def handle_update_check(latest, current, url):
        if controller.is_newer_version(latest, current) and latest:
            dialog = UpdateDialog(latest, current, url, window)
            dialog.exec()

    controller.updatecheckfinished.connect(handle_update_check)
    controller.checkforupdates()

    sys.exit(app.exec())