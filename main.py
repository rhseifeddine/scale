from datetime import datetime
from functools import partial
from kivy.network.urlrequest import UrlRequest as OriginalUrlRequest
import hashlib
import json
import os
import socket
import sys
import traceback
# ============================================
log_file = 'scale_log.txt'
if os.path.exists(log_file):
    try:
        os.remove(log_file)
    except:
        pass

def log_msg(msg, level='INFO'):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_msg = f'[{timestamp}] [{level}] {msg}\n'
    print(formatted_msg)
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(formatted_msg)
    except:
        pass

# ============================================

def get_device_id_s():
    try:
        from kivy.utils import platform
        if platform == 'android':
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            content_resolver = PythonActivity.mActivity.getContentResolver()
            Secure = autoclass('android.provider.Settings$Secure')
            android_id = Secure.getString(content_resolver, Secure.ANDROID_ID)
            return str(android_id) if android_id else 'ANDROID_NO_ID'
        else:
            return 'PC_SCALE_DEV_ID'
    except:
        return 'UNKNOWN_ID'

def generate_expected_key_s(device_id):
    salt = f'magpro_scale_mobile_v7_secure_salt_{device_id}'
    return hashlib.sha256(salt.encode()).hexdigest()

# ============================================
try:
    from kivy.config import Config
    Config.set('graphics', 'width', '400')
    Config.set('graphics', 'height', '800')
    Config.set('kivy', 'log_level', 'info')
    from kivy.core.window import Window
    from kivy.lang import Builder
    from kivy.clock import Clock
    from kivy.properties import StringProperty, ObjectProperty, BooleanProperty
    from kivy.network.urlrequest import UrlRequest
    from kivy.storage.jsonstore import JsonStore
    from kivy.utils import platform
    from kivy.core.clipboard import Clipboard
    from kivy.metrics import dp
    from kivy.uix.recycleview import RecycleView
    from kivy.uix.recycleview.views import RecycleDataViewBehavior
    from kivymd.app import MDApp
    from kivymd.uix.screen import MDScreen
    from kivymd.uix.screenmanager import MDScreenManager
    from kivymd.uix.boxlayout import MDBoxLayout
    from kivymd.uix.floatlayout import MDFloatLayout
    from kivymd.uix.card import MDCard
    from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton, MDFillRoundFlatButton
    from kivymd.uix.label import MDLabel, MDIcon
    from kivymd.uix.textfield import MDTextField
    from kivymd.uix.dialog import MDDialog
    from kivymd.uix.list import MDList, OneLineIconListItem, TwoLineIconListItem, IconLeftWidget
    from kivymd.uix.scrollview import MDScrollView
    from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
    from kivy.core.text import LabelBase
    import arabic_reshaper
    from bidi.algorithm import get_display
except Exception as e:
    log_msg(f'Import Error: {traceback.format_exc()}', 'CRITICAL')
    sys.exit(1)
# ============================================

class CustomUrlRequest(OriginalUrlRequest):

    def __init__(self, url, **kwargs):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        headers = kwargs.get('req_headers', {})
        if not headers:
            headers = {'Content-type': 'application/json'}
        if app and hasattr(app, 'store') and app.store and app.store.exists('config'):
            pin = app.store.get('config').get('server_pin', '')
            if pin:
                headers['X-Server-PIN'] = str(pin)
        kwargs['req_headers'] = headers
        super().__init__(url, **kwargs)

UrlRequest = CustomUrlRequest

class SmartTextField(MDTextField):

    def __init__(self, **kwargs):
        self._raw_text = ''
        self.base_direction = 'ltr'
        self.halign = 'left'
        self._input_reshaper = arabic_reshaper.ArabicReshaper(configuration={'delete_harakat': True, 'support_ligatures': False, 'use_unshaped_instead_of_isolated': True})
        super().__init__(**kwargs)
        self.font_name = 'AppFont'
        self.font_name_hint_text = 'AppFont'
        self.keyboard_suggestions = False
        if self.text:
            self._raw_text = self.text
            self._update_display()

    def insert_text(self, substring, from_undo=False):
        self._raw_text += substring
        self._update_display()

    def do_backspace(self, from_undo=False, mode='bkspc'):
        if not self._raw_text:
            self.text = ''
            return
        self._raw_text = self._raw_text[:-1]
        if not self._raw_text:
            self.text = ''
            self._update_alignment(self._raw_text)
            return
        self._update_display()

    def _update_display(self):
        if self._raw_text:
            try:
                reshaped = self._input_reshaper.reshape(self._raw_text)
                bidi_text = get_display(reshaped)
                self.text = bidi_text
            except Exception:
                self.text = self._raw_text
        else:
            self.text = ''
        self._update_alignment(self._raw_text)
        Clock.schedule_once(self._set_cursor_to_end, 0)

    def _set_cursor_to_end(self, dt):
        self.cursor = (len(self.text), 0)

    def _update_alignment(self, text):
        if not text:
            self.halign = 'left'
            self.base_direction = 'ltr'
            return
        has_arabic = any(('\u0600' <= c <= 'ۿ' or 'ݐ' <= c <= 'ݿ' or 'ﭐ' <= c <= 'ﰿ' or ('ﹰ' <= c <= '\ufeff') for c in text))
        if has_arabic:
            self.halign = 'right'
            self.base_direction = 'rtl'
        else:
            self.halign = 'left'
            self.base_direction = 'ltr'

    def get_value(self):
        if not self._raw_text and self.text:
            return self.text
        return self._raw_text

    def on_text(self, instance, value):
        if not value:
            self._raw_text = ''
        pass

# ============================================
KV_BUILDER = '\n<ProductItem>:\n    orientation: \'vertical\'\n    size_hint_y: None\n    height: dp(100)\n    padding: [dp(10), dp(5)]\n    \n    MDCard:\n        orientation: \'horizontal\'\n        radius: [15]\n        elevation: 2\n        ripple_behavior: True\n        on_release: root.on_tap()\n        md_bg_color: 1, 1, 1, 1\n        padding: dp(10)\n        spacing: dp(15)\n\n        MDFloatLayout:\n            size_hint: None, None\n            size: dp(70), dp(70)\n            pos_hint: {\'center_y\': .5}\n            \n            MDCard:\n                radius: [10]\n                md_bg_color: 0.95, 0.95, 0.95, 1\n                size_hint: 1, 1\n                pos_hint: {\'center_x\': .5, \'center_y\': .5}\n                elevation: 0\n\n            FitImage:\n                source: root.image_url\n                radius: [10]\n                mipmap: True\n                pos_hint: {\'center_x\': .5, \'center_y\': .5}\n                opacity: 1 if root.image_url else 0\n                \n            MDIcon:\n                icon: "scale"\n                halign: "center"\n                font_size: "36sp"\n                theme_text_color: "Hint"\n                pos_hint: {\'center_x\': .5, \'center_y\': .5}\n                opacity: 0 if root.image_url else 1\n\n        MDBoxLayout:\n            orientation: \'vertical\'\n            pos_hint: {\'center_y\': .5}\n            adaptive_height: True\n            spacing: dp(5)\n            \n            MDLabel:\n                text: root.text_name\n                font_style: \'Subtitle1\'\n                bold: True\n                theme_text_color: "Custom"\n                text_color: 0.2, 0.2, 0.2, 1\n                font_name: "AppFont"\n                halign: "left"\n                adaptive_height: True\n                text_size: self.width, None\n                max_lines: 2\n                line_height: 1.1\n            \n            MDLabel:\n                text: root.text_price\n                font_style: \'H6\'\n                theme_text_color: "Custom"\n                text_color: 0, 0.7, 0, 1\n                bold: True\n                font_name: "AppFont"\n                halign: "left"\n                adaptive_height: True\n\n<LoginScreen>:\n    name: \'login\'\n    \n    MDFloatLayout:\n        md_bg_color: 0.98, 0.98, 0.98, 1\n        \n        MDBoxLayout:\n            orientation: \'horizontal\'\n            adaptive_size: True\n            pos_hint: {\'top\': 0.98, \'right\': 0.98}\n            spacing: dp(5)\n            padding: dp(10)\n            \n            MDIcon:\n                icon: \'circle\'\n                theme_text_color: "Custom"\n                text_color: (0, 0.8, 0, 1) if app.is_connected else (0.8, 0, 0, 1)\n                font_size: "14sp"\n                pos_hint: {\'center_y\': 0.5}\n                \n            MDIconButton:\n                icon: \'cog\'\n                on_release: app.open_settings_dialog()\n\n        MDBoxLayout:\n            orientation: \'vertical\'\n            size_hint: 0.85, None\n            height: dp(450)\n            pos_hint: {\'center_x\': 0.5, \'center_y\': 0.5}\n            spacing: dp(20)\n            \n            MDIcon:\n                icon: \'scale-balance\'\n                font_size: \'90sp\'\n                halign: \'center\'\n                theme_text_color: "Primary"\n            \n            MDLabel:\n                text: "MagPro Scale"\n                halign: \'center\'\n                font_style: "H4"\n                bold: True\n                font_name: "AppFont"\n                \n            SmartTextField:\n                id: user_field\n                text: "ADMIN"\n                hint_text: "Utilisateur"\n                icon_right: "account"\n                mode: "fill"\n                font_name: "AppFont"\n                radius: [10, 10, 0, 0]\n\n            SmartTextField:\n                id: pass_field\n                hint_text: "Mot de passe"\n                password: True\n                icon_right: "key"\n                mode: "fill"\n                font_name: "AppFont"\n                radius: [0, 0, 10, 10]\n\n            MDRaisedButton:\n                text: "SE CONNECTER"\n                font_size: "18sp"\n                size_hint_x: 1\n                height: dp(55)\n                font_name: "AppFont"\n                md_bg_color: app.theme_cls.primary_color\n                on_release: app.do_login(user_field.get_value(), pass_field.get_value())\n\n            MDLabel:\n                text: "MagPro Scale v7.5.0 © 2026"\n                halign: \'center\'\n                font_style: "Caption"\n                theme_text_color: "Hint"\n                font_name: "AppFont"\n                size_hint_y: None\n                height: dp(20)\n\n<MainScaleScreen>:\n    name: \'scale\'\n    \n    MDBottomNavigation:\n        id: bottom_nav\n        selected_color_background: "blue"\n        text_color_active: 0, 0, 0, 1\n        font_name: "AppFont"\n\n        MDBottomNavigationItem:\n            name: \'screen_products\'\n            text: \'Produits\'\n            icon: \'package-variant\'\n            \n            MDBoxLayout:\n                orientation: \'vertical\'\n                md_bg_color: 0.98, 0.98, 0.98, 1\n                \n                MDBoxLayout:\n                    size_hint_y: None\n                    height: dp(70)\n                    padding: [dp(10), dp(5)]\n                    spacing: dp(10)\n                    md_bg_color: 1, 1, 1, 1\n                    elevation: 1\n                    \n                    MDIconButton:\n                        icon: \'logout\'\n                        theme_text_color: "Error"\n                        on_release: app.logout()\n                        pos_hint: {\'center_y\': 0.5}\n                        \n                    SmartTextField:\n                        id: search_box\n                        hint_text: "Rechercher..."\n                        mode: "rectangle"\n                        icon_right: "magnify"\n                        font_name: "AppFont"\n                        size_hint_y: None\n                        height: dp(45)\n                        pos_hint: {\'center_y\': 0.5}\n                        on_text: app.filter_products(self.get_value())\n                        \n                    MDIcon:\n                        icon: \'circle\'\n                        theme_text_color: "Custom"\n                        text_color: (0, 0.8, 0, 1) if app.is_connected else (0.8, 0, 0, 1)\n                        font_size: "16sp"\n                        pos_hint: {\'center_y\': 0.5}\n\n                RecycleView:\n                    id: rv\n                    viewclass: \'ProductItem\'\n                    bar_width: dp(0)\n                    \n                    RecycleBoxLayout:\n                        default_size: None, dp(100)\n                        default_size_hint: 1, None\n                        size_hint_y: None\n                        height: self.minimum_height\n                        orientation: \'vertical\'\n                        spacing: dp(2)\n                        padding: [0, dp(10), 0, dp(80)]\n\n        MDBottomNavigationItem:\n            name: \'screen_weigh\'\n            text: \'Balance\'\n            icon: \'scale\'\n            \n            MDBoxLayout:\n                orientation: \'vertical\'\n                spacing: dp(10)\n                padding: dp(15)\n                md_bg_color: 0.98, 0.98, 0.98, 1\n                \n                MDCard:\n                    orientation: \'vertical\'\n                    size_hint_y: None\n                    height: dp(140)\n                    padding: dp(15)\n                    radius: [15]\n                    elevation: 1\n                    md_bg_color: 1, 1, 1, 1\n                    \n                    MDLabel:\n                        text: "PRODUIT SÉLECTIONNÉ"\n                        halign: \'center\'\n                        font_style: \'Overline\'\n                        font_name: "AppFont"\n                        theme_text_color: \'Secondary\'\n                        size_hint_y: None\n                        height: dp(20)\n                        \n                    MDLabel:\n                        id: lbl_name\n                        text: "---"\n                        halign: \'center\'\n                        font_style: \'H5\'\n                        bold: True\n                        font_name: "AppFont"\n                        theme_text_color: "Primary"\n                        shorten: True\n                        size_hint_y: 1\n                        \n                    MDBoxLayout:\n                        size_hint_y: None\n                        height: dp(30)\n                        MDLabel:\n                            text: "PRIX / KG:"\n                            font_name: "AppFont"\n                            halign: \'left\'\n                            font_style: \'Body2\'\n                        MDLabel:\n                            id: lbl_price_unit\n                            text: "0.00 DA"\n                            halign: \'right\'\n                            bold: True\n                            theme_text_color: "Custom"\n                            text_color: 0, 0.6, 0, 1\n                            font_size: "18sp"\n\n                MDGridLayout:\n                    cols: 2\n                    spacing: dp(10)\n                    size_hint_y: None\n                    height: dp(80)\n\n                    MDCard:\n                        padding: dp(5)\n                        radius: [10]\n                        md_bg_color: 1, 1, 1, 1\n                        MDTextField:\n                            id: txt_weight\n                            hint_text: "POIDS (g)"\n                            font_size: "26sp"\n                            halign: \'center\'\n                            input_filter: \'int\'\n                            mode: "line"\n                            line_color_normal: 0,0,0,0\n                            line_color_focus: 0,0,0,0\n                            readonly: True\n                            font_name: "AppFont"\n\n                    MDCard:\n                        padding: dp(10)\n                        radius: [10]\n                        md_bg_color: 0.1, 0.1, 0.1, 1\n                        MDBoxLayout:\n                            orientation: \'vertical\'\n                            MDLabel:\n                                text: "TOTAL"\n                                color: 1, 1, 1, 0.7\n                                font_style: \'Caption\'\n                                halign: \'center\'\n                            MDLabel:\n                                id: lbl_total\n                                text: "0.00"\n                                halign: \'center\'\n                                color: 0, 1, 0, 1\n                                font_style: \'H5\'\n                                bold: True\n\n                MDGridLayout:\n                    cols: 3\n                    spacing: dp(8)\n                    size_hint_y: 1\n                    \n                    MDRaisedButton:\n                        text: "7"\n                        font_size: "24sp"\n                        size_hint: 1, 1\n                        on_release: app.add_digit("7")\n                        md_bg_color: 1, 1, 1, 1\n                        text_color: 0, 0, 0, 1\n                        elevation: 1\n                    MDRaisedButton:\n                        text: "8"\n                        font_size: "24sp"\n                        size_hint: 1, 1\n                        on_release: app.add_digit("8")\n                        md_bg_color: 1, 1, 1, 1\n                        text_color: 0, 0, 0, 1\n                        elevation: 1\n                    MDRaisedButton:\n                        text: "9"\n                        font_size: "24sp"\n                        size_hint: 1, 1\n                        on_release: app.add_digit("9")\n                        md_bg_color: 1, 1, 1, 1\n                        text_color: 0, 0, 0, 1\n                        elevation: 1\n                        \n                    MDRaisedButton:\n                        text: "4"\n                        font_size: "24sp"\n                        size_hint: 1, 1\n                        on_release: app.add_digit("4")\n                        md_bg_color: 1, 1, 1, 1\n                        text_color: 0, 0, 0, 1\n                        elevation: 1\n                    MDRaisedButton:\n                        text: "5"\n                        font_size: "24sp"\n                        size_hint: 1, 1\n                        on_release: app.add_digit("5")\n                        md_bg_color: 1, 1, 1, 1\n                        text_color: 0, 0, 0, 1\n                        elevation: 1\n                    MDRaisedButton:\n                        text: "6"\n                        font_size: "24sp"\n                        size_hint: 1, 1\n                        on_release: app.add_digit("6")\n                        md_bg_color: 1, 1, 1, 1\n                        text_color: 0, 0, 0, 1\n                        elevation: 1\n                        \n                    MDRaisedButton:\n                        text: "1"\n                        font_size: "24sp"\n                        size_hint: 1, 1\n                        on_release: app.add_digit("1")\n                        md_bg_color: 1, 1, 1, 1\n                        text_color: 0, 0, 0, 1\n                        elevation: 1\n                    MDRaisedButton:\n                        text: "2"\n                        font_size: "24sp"\n                        size_hint: 1, 1\n                        on_release: app.add_digit("2")\n                        md_bg_color: 1, 1, 1, 1\n                        text_color: 0, 0, 0, 1\n                        elevation: 1\n                    MDRaisedButton:\n                        text: "3"\n                        font_size: "24sp"\n                        size_hint: 1, 1\n                        on_release: app.add_digit("3")\n                        md_bg_color: 1, 1, 1, 1\n                        text_color: 0, 0, 0, 1\n                        elevation: 1\n                        \n                    MDRaisedButton:\n                        text: "C"\n                        font_size: "24sp"\n                        size_hint: 1, 1\n                        md_bg_color: 0.9, 0.9, 0.9, 1\n                        text_color: 0.8, 0, 0, 1\n                        on_release: app.clear_weight()\n                        elevation: 1\n                    MDRaisedButton:\n                        text: "0"\n                        font_size: "24sp"\n                        size_hint: 1, 1\n                        on_release: app.add_digit("0")\n                        md_bg_color: 1, 1, 1, 1\n                        text_color: 0, 0, 0, 1\n                        elevation: 1\n                    MDIconButton:\n                        icon: "backspace"\n                        size_hint: 1, 1\n                        icon_size: "30sp"\n                        on_release: app.backspace()\n                        theme_text_color: "Custom"\n                        text_color: 0.3, 0.3, 0.3, 1\n\n                MDFillRoundFlatButton:\n                    text: "IMPRIMER"\n                    font_name: "AppFont"\n                    font_size: "20sp"\n                    size_hint_x: 1\n                    height: dp(55)\n                    md_bg_color: 0, 0.7, 0, 1\n                    on_release: app.send_print_command()\n'
# ============================================
class ProductItem(RecycleDataViewBehavior, MDBoxLayout):
    index = None
    text_name = StringProperty('')
    text_price = StringProperty('')
    image_url = StringProperty('')
    product_data = ObjectProperty(None)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.text_name = data.get('text_name', '')
        self.text_price = data.get('text_price', '')
        self.image_url = data.get('image_url', '')
        self.product_data = data.get('product_data')
        return super().refresh_view_attrs(rv, index, data)

    def on_tap(self):
        MDApp.get_running_app().select_product(self.product_data)

class LoginScreen(MDScreen):
    pass

class MainScaleScreen(MDScreen):
    pass

class ScaleApp(MDApp):
    is_connected = BooleanProperty(False)
    selected_product = None
    all_products = []
    dialog = None
    dialog_loading = None
    dialog_exit = None
    wifi_ip = '192.168.1.100'
    ethernet_ip = ''
    server_port = '5000'
    sticker_size = '40x20'
    available_ips = []
    current_ip_index = 0
    license_store = None
    cache_store = None
    activation_dialog_ref = None
    heartbeat_event = None
    stop_heartbeat = False

    def build(self):
        self.theme_cls.primary_palette = 'Blue'
        self.theme_cls.accent_palette = 'Amber'
        self.theme_cls.theme_style = 'Light'
        self.title = 'MagPro Scale'
        try:
            self.data_dir = self.user_data_dir
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)
            self.image_cache_dir = os.path.join(self.data_dir, 'img_cache')
            if not os.path.exists(self.image_cache_dir):
                os.makedirs(self.image_cache_dir)
        except Exception as e:
            log_msg(f'FS Error: {e}', 'ERROR')
        global KV_BUILDER
        font_path = 'font.ttf'
        if os.path.exists(font_path):
            try:
                LabelBase.register(name='AppFont', fn_regular=font_path, fn_bold=font_path)
            except Exception as e:
                log_msg(f'Error registering font: {e}', 'ERROR')
                KV_BUILDER = KV_BUILDER.replace('font_name: "AppFont"', '')
        else:
            log_msg('font.ttf not found. Using system defaults.', 'WARNING')
            KV_BUILDER = KV_BUILDER.replace('font_name: "AppFont"', '')
        try:
            self.reshaper = arabic_reshaper.ArabicReshaper(configuration={'delete_harakat': True, 'support_ligatures': True})
        except:
            pass
        self.load_settings()
        Builder.load_string(KV_BUILDER)
        self.sm = MDScreenManager()
        self.sm.add_widget(LoginScreen())
        self.sm.add_widget(MainScaleScreen())
        return self.sm

    def load_settings(self):
        try:
            self.store = JsonStore(os.path.join(self.data_dir, 'scale_settings.json'))
            self.license_store = JsonStore(os.path.join(self.data_dir, 'scale_license.json'))
            self.cache_store = JsonStore(os.path.join(self.data_dir, 'products_cache.json'))
            if self.store.exists('config'):
                config = self.store.get('config')
                self.wifi_ip = config.get('wifi_ip', self.wifi_ip)
                self.ethernet_ip = config.get('eth_ip', self.ethernet_ip)
                self.sticker_size = config.get('sticker_size', self.sticker_size)
            self.available_ips = []
            if self.wifi_ip and self.is_valid_ip(self.wifi_ip):
                self.available_ips.append(self.wifi_ip)
            if self.ethernet_ip and self.is_valid_ip(self.ethernet_ip):
                self.available_ips.append(self.ethernet_ip)
            if not self.available_ips:
                self.available_ips = ['192.168.1.100']
        except:
            pass

    def is_valid_ip(self, ip):
        if not ip:
            return False
        import re
        if re.search('[a-zA-Z]', ip):
            return True
        try:
            import socket
            socket.inet_aton(ip)
            return True
        except:
            return False

    def api_base_for_ip(self, ip_string):
        import re
        if not ip_string:
            return ''
        if re.search('[a-zA-Z]', ip_string):
            clean_host = ip_string.replace('https://', '').replace('http://', '').strip('/')
            return f'https://{clean_host}'
        return f'http://{ip_string}:{self.server_port}'

    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.INTERNET, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
            from android.runnable import run_on_ui_thread
            from jnius import autoclass

            @run_on_ui_thread
            def set_keep_screen_on():
                try:
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    PythonActivity.mActivity.getWindow().addFlags(128)
                    log_msg('Screen Keep On Set Successfully', 'INFO')
                except Exception as e:
                    log_msg(f'Screen Keep On Error: {e}', 'ERROR')
            set_keep_screen_on()
        Window.bind(on_keyboard=self.on_keyboard_handler)
        from kivy.clock import Clock
        Clock.schedule_once(self._deferred_start, 0.5)

    def _deferred_start(self, dt):
        status, days_left = self.check_license_validity()
        if status in ['EXPIRED', 'TAMPERED']:
            self.show_activation_dialog(trial_expired=True)
            return
        elif status == 'TRIAL':
            self.show_activation_dialog(trial_expired=False, days_left=days_left)
            return
        elif status == 'ACTIVATED':
            self.continue_trial(None)

    def continue_trial(self, dialog_ref):
        if dialog_ref:
            dialog_ref.dismiss()
        self.start_heartbeat()
        if self.sm.has_screen('login'):
            login_screen = self.sm.get_screen('login')
            if self.store.exists('credentials'):
                creds = self.store.get('credentials')
                user = creds.get('username', 'ADMIN')
                pwd = creds.get('password', '')
                login_screen.ids.user_field.text = user
                login_screen.ids.pass_field.text = pwd
                if user:
                    from kivy.clock import Clock
                    Clock.schedule_once(lambda dt: self.do_login(user, pwd), 1)

    def on_keyboard_handler(self, window, key, *args):
        if key == 27:
            if self.sm.current == 'scale':
                screen = self.root.get_screen('scale')
                if self.selected_product:
                    self.selected_product = None
                    screen.ids.bottom_nav.switch_tab('screen_products')
                return True
            elif self.sm.current == 'login':
                return True
        return False

    def start_heartbeat(self):
        if not self.heartbeat_event:
            self.stop_heartbeat = False
            import threading
            threading.Thread(target=self.heartbeat_loop, daemon=True).start()
            self.heartbeat_event = True

    def heartbeat_loop(self):
        import time
        from kivy.clock import Clock
        while not self.stop_heartbeat:
            Clock.schedule_once(lambda dt: self._run_socket_ping_logic(), 0)
            time.sleep(5)

    def _run_socket_ping_logic(self):
        self._ping_wifi()

    def _ping_wifi(self):
        if not self.wifi_ip:
            self._ping_ethernet()
            return
        url = f'http://{self.wifi_ip}:{self.server_port}/api/ping'
        UrlRequest(url, on_success=lambda r, res: self._finalize_ping(True, self.wifi_ip), on_failure=lambda r, e: self._ping_ethernet(), on_error=lambda r, e: self._ping_ethernet(), timeout=2)

    def _ping_ethernet(self):
        if not self.ethernet_ip:
            self._finalize_ping(False, None)
            return
        import re
        if re.search('[a-zA-Z]', self.ethernet_ip):
            clean_host = self.ethernet_ip.replace('https://', '').replace('http://', '').strip('/')
            url = f'https://{clean_host}/api/ping'
        else:
            url = f'http://{self.ethernet_ip}:{self.server_port}/api/ping'

        def check_fail(req, err):
            if req.resp_status == 403:
                self.show_alert('Erreur', 'Code PIN du Serveur Incorrect!')
            self._finalize_ping(False, None)
        UrlRequest(url, on_success=lambda r, res: self._finalize_ping(True, self.ethernet_ip), on_failure=check_fail, on_error=check_fail, timeout=4)

    def _finalize_ping(self, success, confirmed_ip):
        self.is_connected = success
        if success and confirmed_ip:
            self.current_ip_index = 0
            if confirmed_ip not in self.available_ips:
                self.available_ips.insert(0, confirmed_ip)
            else:
                self.available_ips.remove(confirmed_ip)
                self.available_ips.insert(0, confirmed_ip)

    def on_stop(self):
        self.stop_heartbeat = True

    def check_connection_status(self, dt):
        if not self.available_ips:
            self.is_connected = False
            return
        ip = self.available_ips[self.current_ip_index]
        url = f'{self.api_base_for_ip(ip)}/api/products'
        UrlRequest(url, method='HEAD', on_success=lambda r, res: setattr(self, 'is_connected', True), on_failure=lambda r, e: setattr(self, 'is_connected', False), on_error=lambda r, e: setattr(self, 'is_connected', False), timeout=1.5)

    def get_device_id(self):
        try:
            from kivy.utils import platform
            if platform == 'android':
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                content_resolver = PythonActivity.mActivity.getContentResolver()
                Secure = autoclass('android.provider.Settings$Secure')
                android_id = Secure.getString(content_resolver, Secure.ANDROID_ID)
                return str(android_id) if android_id else 'ANDROID_NO_ID'
            else:
                return 'PC_SCALE_DEV_ID'
        except:
            return 'UNKNOWN_ID'

    def get_hidden_sys_file(self):
        import os
        from kivy.utils import platform
        if platform == 'android':
            try:
                from jnius import autoclass
                Environment = autoclass('android.os.Environment')
                public_dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS).getAbsolutePath()
                return os.path.join(public_dir, '.magpro_scale_sys.dat')
            except Exception:
                return os.path.join(self.data_dir, '.magpro_scale_sys.dat')
        else:
            return os.path.join(os.path.expanduser('~'), '.magpro_scale_sys.dat')

    def load_persistent_data(self):
        import json
        import os
        path = self.get_hidden_sys_file()
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {'trial_start': None, 'attempts': 0}

    def save_persistent_data(self, data):
        import json
        import os
        path = self.get_hidden_sys_file()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f'Failed to save persistent data: {e}')

    def check_license_validity(self):
        try:
            stored_key = None
            if hasattr(self, 'license_store') and self.license_store and self.license_store.exists('license'):
                stored_key = self.license_store.get('license').get('activ_key')
            device_id = self.get_device_id()
            salt = f'magpro_scale_mobile_v7_secure_salt_{device_id}'
            import hashlib
            expected_key = hashlib.sha256(salt.encode()).hexdigest()
            if stored_key and stored_key == expected_key:
                return ('ACTIVATED', 0)
            from datetime import datetime
            now = datetime.now()
            p_data = self.load_persistent_data()
            install_date_str = p_data.get('trial_start')
            if not install_date_str:
                install_date_str = now.strftime('%Y-%m-%d %H:%M:%S')
                p_data['trial_start'] = install_date_str
                self.save_persistent_data(p_data)
            try:
                install_date = datetime.strptime(install_date_str, '%Y-%m-%d %H:%M:%S')
            except Exception:
                install_date = now
            days_used = (now - install_date).days
            if days_used < 0:
                return ('TAMPERED', 0)
            if days_used <= 7:
                days_left = 7 - days_used
                return ('TRIAL', days_left)
            else:
                return ('EXPIRED', 0)
        except Exception as e:
            print(f'Erreur de vérification de licence: {e}')
            return ('EXPIRED', 0)

    def validate_activation(self, key_input, dialog_ref=None):
        try:
            device_id = self.get_device_id()
            salt = f'magpro_scale_mobile_v7_secure_salt_{device_id}'
            import hashlib
            expected_key = hashlib.sha256(salt.encode()).hexdigest()
            if key_input.strip() == expected_key:
                self.license_store.put('license', activ_key=expected_key)
                self.show_alert('Succès', 'Activation réussie ! Bienvenue.')
                if dialog_ref:
                    dialog_ref.dismiss()
                from kivy.clock import Clock
                Clock.schedule_once(self._deferred_start, 0.5)
            else:
                self.show_alert('Erreur', 'Clé invalide. Veuillez vérifier.')
        except Exception as e:
            self.show_alert('Erreur', f"Erreur lors de l'activation: {e}")

    def show_activation_dialog(self, trial_expired=True, days_left=0):
        from kivy.core.clipboard import Clipboard
        from kivymd.uix.button import MDFillRoundFlatIconButton
        device_id = self.get_device_id()
        content = MDBoxLayout(orientation='vertical', spacing='12dp', size_hint_y=None, adaptive_height=True, padding=['20dp', '20dp', '20dp', '10dp'])
        icon_name = 'shield-lock' if trial_expired else 'shield-check'
        icon_color = (0.8, 0, 0, 1) if trial_expired else self.theme_cls.primary_color
        content.add_widget(MDIcon(icon=icon_name, halign='center', font_size='64sp', theme_text_color='Custom', text_color=icon_color, pos_hint={'center_x': 0.5}))
        if trial_expired:
            title_text = "Période d'essai terminée"
            sub_text = "L'application est verrouillée.\nVeuillez l'activer."
            title_color = 'Error'
        else:
            title_text = f'Essai : {days_left} Jour(s) restant(s)'
            sub_text = "Profitez de votre essai ou activez l'application."
            title_color = 'Primary'
        content.add_widget(MDLabel(text=title_text, halign='center', font_style='H5', bold=True, theme_text_color=title_color, adaptive_height=True))
        content.add_widget(MDLabel(text=sub_text, halign='center', font_style='Caption', theme_text_color='Secondary', adaptive_height=True))
        id_card = MDCard(orientation='vertical', radius=[10], padding=['15dp', '12dp', '15dp', '12dp'], md_bg_color=(0.96, 0.96, 0.96, 1), elevation=0, size_hint_y=None, adaptive_height=True, spacing='5dp')
        id_card.add_widget(MDLabel(text="ID d'appareil :", halign='left', font_style='Caption', theme_text_color='Secondary', adaptive_height=True))
        id_row = MDBoxLayout(orientation='horizontal', spacing='10dp', adaptive_height=True)
        field_id = MDTextField(text=device_id, readonly=True, font_size='16sp', mode='line', active_line=False, size_hint_x=0.85, pos_hint={'center_y': 0.5})
        btn_copy = MDIconButton(icon='content-copy', theme_text_color='Custom', text_color=self.theme_cls.primary_color, on_release=lambda x: Clipboard.copy(device_id), pos_hint={'center_y': 0.5}, icon_size='22sp')
        id_row.add_widget(field_id)
        id_row.add_widget(btn_copy)
        id_card.add_widget(id_row)
        content.add_widget(id_card)
        key_row = MDBoxLayout(orientation='horizontal', spacing='10dp', adaptive_height=True)
        self.field_key = MDTextField(hint_text='Saisir la clé', mode='rectangle', size_hint_x=0.85, pos_hint={'center_y': 0.5})
        btn_paste = MDIconButton(icon='content-paste', theme_text_color='Custom', text_color=self.theme_cls.primary_color, on_release=lambda x: setattr(self.field_key, 'text', Clipboard.paste()), pos_hint={'center_y': 0.5}, icon_size='22sp')
        key_row.add_widget(self.field_key)
        key_row.add_widget(btn_paste)
        content.add_widget(key_row)
        btn_activate = MDRaisedButton(text="ACTIVER L'APPLICATION", md_bg_color=(0, 0.7, 0, 1), font_size='16sp', elevation=1, size_hint_x=1, size_hint_y=None, height='52dp', on_release=lambda x: self.validate_activation(self.field_key.text, self.activation_dialog_ref))
        content.add_widget(btn_activate)
        self.online_act_btn = MDFillRoundFlatIconButton(icon='earth', text='Activer en ligne', md_bg_color=(0.1, 0.5, 0.8, 1), theme_text_color='Custom', text_color=(1, 1, 1, 1), icon_color=(1, 1, 1, 1), font_size='15sp', size_hint_x=1, size_hint_y=None, height='45dp', on_release=self.request_online_activation_mobile)
        content.add_widget(self.online_act_btn)
        if not trial_expired:
            btn_trial = MDFlatButton(text="Continuer l'essai gratuit", theme_text_color='Custom', text_color=self.theme_cls.primary_color, size_hint_x=1, size_hint_y=None, height='40dp', on_release=lambda x: self.continue_trial(self.activation_dialog_ref))
            content.add_widget(btn_trial)
        self.activation_dialog_ref = MDDialog(title='', type='custom', content_cls=content, size_hint=(0.9, None), auto_dismiss=False, radius=[16, 16, 16, 16])
        self.activation_dialog_ref.open()

    def request_online_activation_mobile(self, instance=None):
        if self.online_act_btn.disabled:
            return
        p_data = self.load_persistent_data()
        attempts = p_data.get('attempts', 0)
        if attempts >= 5:
            self.show_alert('Erreur', 'Limite atteinte (5). Fonctionnalité bloquée.')
            self.online_act_btn.text = 'Bloqué'
            self.online_act_btn.icon = 'cancel'
            self.online_act_btn.disabled = True
            return
        p_data['attempts'] = attempts + 1
        self.save_persistent_data(p_data)
        self.online_act_btn.text = 'Vérification...'
        self.online_act_btn.icon = 'sync'
        self.online_act_btn.disabled = True
        import threading
        threading.Thread(target=self._online_activation_worker_mobile, daemon=True).start()

    def _online_activation_worker_mobile(self):
        import requests
        import time
        import hashlib
        from kivy.clock import Clock
        BOT_TOKEN = "GITHUB_SECRET_TELEGRAM_BOT_TOKEN"
        MASTER_ADMIN_ID = "GITHUB_SECRET_TELEGRAM_ADMIN_ID"
        device_id = self.get_device_id()
        try:
            requests.get('https://api.telegram.org', timeout=5)
        except:
            def no_internet(dt):
                self.show_alert('Erreur', 'Pas de connexion Internet')
                self.online_act_btn.text = 'Activer en ligne'
                self.online_act_btn.icon = 'earth'
                self.online_act_btn.disabled = False
            Clock.schedule_once(no_internet, 0)
            return
        Clock.schedule_once(lambda dt: setattr(self.online_act_btn, 'text', 'Envoi de la demande...'), 0)
        msg = f'📱 **طلب تفعيل تطبيق الميزان (MagPro Scale)**\n\n💻 **رقم الجهاز (ID):** `{device_id}`'
        reply_markup = {
            "inline_keyboard": [
                [{"text": "✅ تفعيل التطبيق", "callback_data": f"ACT_OK|SCALE|{device_id}"}],
                [{"text": "❌ رفض الطلب", "callback_data": f"ACT_NO|SCALE|{device_id}"}]
            ]
        }
        try:
            requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', json={'chat_id': MASTER_ADMIN_ID, 'text': msg, 'parse_mode': 'Markdown', 'reply_markup': reply_markup}, timeout=10)
        except:
            def no_server(dt):
                self.show_alert('Erreur', "Échec d'envoi au serveur")
                self.online_act_btn.text = 'Activer en ligne'
                self.online_act_btn.icon = 'earth'
                self.online_act_btn.disabled = False
            Clock.schedule_once(no_server, 0)
            return
        Clock.schedule_once(lambda dt: setattr(self.online_act_btn, 'text', 'En attente... (Ne pas fermer)'), 0)
        offset = None
        try:
            resp = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates', timeout=10).json()
            if resp.get('result'):
                offset = resp['result'][-1]['update_id'] + 1
        except:
            pass
        timeout_end = time.time() + 900
        is_activated = False
        while time.time() < timeout_end:
            if not hasattr(self, 'activation_dialog_ref') or not self.activation_dialog_ref:
                return
            try:
                params = {'timeout': 10, 'allowed_updates': ['message', 'callback_query']}
                if offset:
                    params['offset'] = offset
                resp = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates', params=params, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    for result in data.get('result', []):
                        offset = result['update_id'] + 1
                        if 'callback_query' in result:
                            cb = result['callback_query']
                            cb_data = cb.get('data', '')
                            cb_id = cb.get('id')
                            msg_id = cb.get('message', {}).get('message_id')
                            parts = cb_data.split('|')
                            if len(parts) == 3 and parts[1] == 'SCALE' and parts[2] == device_id:
                                if parts[0] == 'ACT_OK':
                                    salt = f'magpro_scale_mobile_v7_secure_salt_{device_id}'
                                    expected_key = hashlib.sha256(salt.encode()).hexdigest().lower()
                                    requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery', json={'callback_query_id': cb_id, 'text': 'تم تفعيل الميزان ✅'})
                                    requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/editMessageText', json={'chat_id': MASTER_ADMIN_ID, 'message_id': msg_id, 'text': msg + '\n\n✅ **الحالة: تم التفعيل بنجاح**', 'parse_mode': 'Markdown'})
                                    is_activated = True
                                    def apply_activation_ui(dt):
                                        if hasattr(self, 'field_key'):
                                            self.field_key.text = expected_key
                                        if hasattr(self, 'online_act_btn'):
                                            self.online_act_btn.text = 'Activé!'
                                            self.online_act_btn.icon = 'check-circle'
                                        self.validate_activation(expected_key, self.activation_dialog_ref)
                                    Clock.schedule_once(apply_activation_ui, 0)
                                    return
                                elif parts[0] == 'ACT_NO':
                                    requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery', json={'callback_query_id': cb_id, 'text': 'تم الرفض ❌'})
                                    requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/editMessageText', json={'chat_id': MASTER_ADMIN_ID, 'message_id': msg_id, 'text': msg + '\n\n❌ **الحالة: تم الرفض**', 'parse_mode': 'Markdown'})
                                    def apply_reject_ui(dt):
                                        self.show_alert('Refusé', "L'administrateur a refusé la demande.")
                                        if hasattr(self, 'online_act_btn'):
                                            self.online_act_btn.text = "Activer en ligne"
                                            self.online_act_btn.icon = 'earth'
                                            self.online_act_btn.disabled = False
                                    Clock.schedule_once(apply_reject_ui, 0)
                                    return
                        message = result.get('message', {})
                        text = str(message.get('text', '')).strip()
                        chat_id = str(message.get('chat', {}).get('id', ''))
                        if chat_id == MASTER_ADMIN_ID and text and (len(text) >= 32):
                            received_key = text.strip().lower()
                            salt = f'magpro_scale_mobile_v7_secure_salt_{device_id}'
                            expected_key = hashlib.sha256(salt.encode()).hexdigest().lower()
                            if received_key == expected_key:
                                is_activated = True
                                requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', json={'chat_id': MASTER_ADMIN_ID, 'text': f'✅ **تم تفعيل تطبيق الميزان بنجاح!**\n💻 رقم الجهاز: `{device_id}`', 'parse_mode': 'Markdown'})
                                def apply_activation_ui_manual(dt):
                                    if hasattr(self, 'field_key'):
                                        self.field_key.text = text.strip()
                                    if hasattr(self, 'online_act_btn'):
                                        self.online_act_btn.text = 'Activé!'
                                        self.online_act_btn.icon = 'check-circle'
                                    self.validate_activation(text.strip(), self.activation_dialog_ref)
                                Clock.schedule_once(apply_activation_ui_manual, 0)
                                return
            except Exception:
                pass
            time.sleep(3)
        if not is_activated:
            def timeout_ui(dt):
                self.show_alert('Attention', "Délai d'attente expiré.")
                if hasattr(self, 'online_act_btn'):
                    self.online_act_btn.text = 'Activer en ligne'
                    self.online_act_btn.icon = 'earth'
                    self.online_act_btn.disabled = False
            Clock.schedule_once(timeout_ui, 0)

    def fix_text(self, text):
        if not text or not isinstance(text, str):
            return str(text) if text is not None else ''
        if any(('\u0600' <= c <= 'ۿ' for c in text)):
            try:
                reshaped_text = self.reshaper.reshape(text)
                return get_display(reshaped_text)
            except Exception:
                return text
        return text

    def get_active_url(self, endpoint):
        if not self.available_ips:
            return None
        ip = self.available_ips[self.current_ip_index]
        return f'{self.api_base_for_ip(ip)}{endpoint}'

    def switch_ip_and_retry(self, endpoint, method, body, headers, success_callback, failure_callback, original_req=None):
        self.current_ip_index += 1
        if self.current_ip_index >= len(self.available_ips):
            self.current_ip_index = 0
            self.is_connected = False
            if failure_callback:
                failure_callback(original_req, 'Connexion perdue')
            return
        new_ip = self.available_ips[self.current_ip_index]
        url = f'{self.api_base_for_ip(new_ip)}{endpoint}'
        UrlRequest(url, req_body=body, req_headers=headers, method=method, on_success=lambda r, res: self._wrap_success(r, res, success_callback), on_error=lambda r, err: self.switch_ip_and_retry(endpoint, method, body, headers, success_callback, failure_callback, r), on_failure=lambda r, err: self.switch_ip_and_retry(endpoint, method, body, headers, success_callback, failure_callback, r), timeout=2)

    def send_request(self, endpoint, method='GET', body=None, headers=None, on_success=None, on_failure=None):
        if headers is None:
            headers = {'Content-type': 'application/json'}
        url = self.get_active_url(endpoint)
        if not url:
            if on_failure:
                on_failure(None, 'Aucune IP configurée')
            return
        UrlRequest(url, req_body=body, req_headers=headers, method=method, on_success=lambda r, res: self._wrap_success(r, res, on_success), on_error=lambda r, err: self.switch_ip_and_retry(endpoint, method, body, headers, on_success, on_failure, r), on_failure=lambda r, err: self.switch_ip_and_retry(endpoint, method, body, headers, on_success, on_failure, r), timeout=2)

    def _wrap_success(self, req, res, original_callback):
        self.is_connected = True
        if original_callback:
            original_callback(req, res)

    def open_settings_dialog(self):
        content_box = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(520))
        scroll = MDScrollView()
        list_layout = MDList()
        import webbrowser
        status, days_left = self.check_license_validity()
        from kivy.core.clipboard import Clipboard
        if status == 'ACTIVATED':
            l_title = 'Licence : Activée'
            l_icon = 'shield-check'
            l_color = (0, 0.7, 0, 1)
            device_id = self.get_device_id()
            import hashlib
            activ_key = hashlib.sha256(f'magpro_scale_mobile_v7_secure_salt_{device_id}'.encode()).hexdigest()

            def copy_action(inst):
                Clipboard.copy(activ_key)
                self.show_alert('Copié', "Clé d'activation copiée dans le presse-papiers")
            lic_card = MDCard(orientation='vertical', padding=dp(15), spacing=dp(10), size_hint_y=None, adaptive_height=True, md_bg_color=(0.95, 0.98, 0.95, 1), radius=[8], ripple_behavior=True)
            lic_card.bind(on_release=copy_action)
            top_row = MDBoxLayout(orientation='horizontal', adaptive_height=True, spacing=dp(10))
            top_row.add_widget(MDIcon(icon=l_icon, theme_text_color='Custom', text_color=l_color, font_size='24sp', pos_hint={'center_y': 0.5}))
            top_row.add_widget(MDLabel(text=l_title, font_style='Subtitle1', bold=True, theme_text_color='Custom', text_color=l_color, pos_hint={'center_y': 0.5}))
            lic_card.add_widget(top_row)
            lic_card.add_widget(MDLabel(text='Clé (Appuyez pour copier):', font_style='Caption', theme_text_color='Secondary'))
            lic_card.add_widget(MDLabel(text=activ_key, font_style='Caption', theme_text_color='Primary', font_name='Roboto', bold=True, adaptive_height=True))
            list_layout.add_widget(MDBoxLayout(size_hint_y=None, height=dp(5)))
            list_layout.add_widget(lic_card)
            list_layout.add_widget(MDBoxLayout(size_hint_y=None, height=dp(10)))
        else:
            l_title = f'Essai : {days_left} jours restants'
            l_icon = 'shield-alert'
            l_color = (1, 0.6, 0, 1)
            device_id = self.get_device_id()

            def copy_action(inst):
                Clipboard.copy(device_id)
                self.show_alert('Copié', 'ID copié dans le presse-papiers')
            lic_card = MDCard(orientation='vertical', padding=dp(15), spacing=dp(10), size_hint_y=None, adaptive_height=True, md_bg_color=(1, 0.95, 0.9, 1), radius=[8], ripple_behavior=True)
            lic_card.bind(on_release=copy_action)
            top_row = MDBoxLayout(orientation='horizontal', adaptive_height=True, spacing=dp(10))
            top_row.add_widget(MDIcon(icon=l_icon, theme_text_color='Custom', text_color=l_color, font_size='24sp', pos_hint={'center_y': 0.5}))
            top_row.add_widget(MDLabel(text=l_title, font_style='Subtitle1', bold=True, theme_text_color='Custom', text_color=l_color, pos_hint={'center_y': 0.5}))
            lic_card.add_widget(top_row)
            lic_card.add_widget(MDLabel(text='ID Appareil (Appuyez pour copier):', font_style='Caption', theme_text_color='Secondary'))
            lic_card.add_widget(MDLabel(text=device_id, font_style='Caption', theme_text_color='Primary', font_name='Roboto', bold=True, adaptive_height=True))
            list_layout.add_widget(MDBoxLayout(size_hint_y=None, height=dp(5)))
            list_layout.add_widget(lic_card)
            list_layout.add_widget(MDBoxLayout(size_hint_y=None, height=dp(10)))
        header_app = OneLineIconListItem(text='Application', bg_color=(0.95, 0.95, 0.95, 1))
        header_app.add_widget(IconLeftWidget(icon='cellphone-arrow-down'))
        list_layout.add_widget(header_app)
        item_update = TwoLineIconListItem(text='Mise à jour', secondary_text='Télécharger la nouvelle version', on_release=lambda x: [self.dialog.dismiss(), webbrowser.open('https://scale.magpro-soft.com/')])
        item_update.add_widget(IconLeftWidget(icon='cloud-download'))
        list_layout.add_widget(item_update)
        header_net = OneLineIconListItem(text='Configuration Réseau', bg_color=(0.95, 0.95, 0.95, 1))
        header_net.add_widget(IconLeftWidget(icon='lan'))
        list_layout.add_widget(header_net)
        saved_pin = self.store.get('config').get('server_pin', '') if self.store.exists('config') else ''
        self.tf_wifi = MDTextField(text=self.wifi_ip, hint_text='IP WIFI (Local)', mode='rectangle')
        item_wifi = MDBoxLayout(padding=dp(20), size_hint_y=None, height=dp(80))
        item_wifi.add_widget(self.tf_wifi)
        list_layout.add_widget(item_wifi)
        self.tf_eth = MDTextField(text=self.ethernet_ip, hint_text='IP ETHERNET (Ext/Internet)', mode='rectangle')
        item_eth = MDBoxLayout(padding=dp(20), size_hint_y=None, height=dp(80))
        item_eth.add_widget(self.tf_eth)
        list_layout.add_widget(item_eth)
        self.tf_pin = MDTextField(text=str(saved_pin), hint_text='Code PIN (Cloudflare)', mode='rectangle', password=True, icon_right='lock-outline')
        item_pin = MDBoxLayout(padding=dp(20), size_hint_y=None, height=dp(80))
        item_pin.add_widget(self.tf_pin)
        list_layout.add_widget(item_pin)

        def on_eth_change(instance, text):
            import re
            if re.search('[a-zA-Z]', text):
                self.tf_pin.opacity = 1
                self.tf_pin.disabled = False
            else:
                self.tf_pin.opacity = 0
                self.tf_pin.disabled = True
        self.tf_eth.bind(text=on_eth_change)
        on_eth_change(self.tf_eth, self.tf_eth.text)
        header_print = OneLineIconListItem(text='Configuration Étiquette', bg_color=(0.95, 0.95, 0.95, 1))
        header_print.add_widget(IconLeftWidget(icon='printer-settings'))
        list_layout.add_widget(header_print)
        size_box = MDBoxLayout(orientation='horizontal', spacing=dp(10), padding=dp(20), size_hint_y=None, height=dp(60), pos_hint={'center_x': 0.5})

        def set_size(inst):
            self.sticker_size = inst.text
            self.show_alert('Info', f'Taille définie: {self.sticker_size}')
            self.dialog.dismiss()
            self.open_settings_dialog()
        current_size = self.sticker_size
        for s in ['40x20', '45x35', '60x40']:
            if s == current_size:
                btn = MDRaisedButton(text=s, md_bg_color=(0, 0.7, 0, 1), elevation=2)
            else:
                btn = MDRaisedButton(text=s, md_bg_color=(0.8, 0.8, 0.8, 1), text_color=(0, 0, 0, 1), elevation=0)
            btn.bind(on_release=set_size)
            size_box.add_widget(btn)
        list_layout.add_widget(size_box)
        scroll.add_widget(list_layout)
        content_box.add_widget(scroll)

        def force_text_wrap(dt):
            from kivymd.uix.list import BaseListItem
            for item in list_layout.children:
                if isinstance(item, BaseListItem):
                    for child in item.walk():
                        if isinstance(child, MDLabel):
                            child.shorten = False
                            child.max_lines = 3
                            child.bind(width=lambda inst, width: setattr(inst, 'text_size', (width, None)))
        Clock.schedule_once(force_text_wrap, 0.1)

        def save(x):
            self.wifi_ip = self.tf_wifi.text.strip()
            self.ethernet_ip = self.tf_eth.text.strip()
            server_pin = self.tf_pin.text.strip()
            self.available_ips = []
            if self.wifi_ip and self.is_valid_ip(self.wifi_ip):
                self.available_ips.append(self.wifi_ip)
            if self.ethernet_ip and self.is_valid_ip(self.ethernet_ip):
                self.available_ips.append(self.ethernet_ip)
            self.current_ip_index = 0
            self.store.put('config', wifi_ip=self.wifi_ip, eth_ip=self.ethernet_ip, sticker_size=self.sticker_size, server_pin=server_pin)
            if self.dialog:
                self.dialog.dismiss()
            self.show_alert('Succès', 'Paramètres enregistrés')
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self._run_socket_ping_logic(), 0.5)
        self.dialog = MDDialog(title='Paramètres', type='custom', content_cls=content_box, buttons=[MDFlatButton(text='ANNULER', on_release=lambda x: self.dialog.dismiss()), MDRaisedButton(text='SAUVEGARDER', md_bg_color=(0, 0.7, 0, 1), on_release=save)], size_hint=(0.95, 0.9))
        self.dialog.open()

    def do_login(self, username, password):
        if not username:
            self.show_alert('Erreur', 'Nom utilisateur requis')
            return
        body = json.dumps({'username': username, 'password': password})
        self.dialog_loading = MDDialog(text='Connexion en cours...', auto_dismiss=False)
        self.dialog_loading.open()
        self.send_request('/api/login', 'POST', body, on_success=self.on_login_success, on_failure=self.on_login_fail)

    def on_login_success(self, req, res):
        if self.dialog_loading:
            self.dialog_loading.dismiss()
        if res.get('status') == 'success':
            self.store.put('credentials', username=self.root.get_screen('login').ids.user_field.get_value(), password=self.root.get_screen('login').ids.pass_field.get_value())
            self.root.current = 'scale'
            self.fetch_products()
        else:
            self.show_alert('Échec', 'Identifiants incorrects')

    def on_login_fail(self, req, err):
        if self.dialog_loading:
            self.dialog_loading.dismiss()
        self.show_alert('Erreur', 'Serveur inaccessible')

    def logout(self):
        self.root.current = 'login'
        self.selected_product = None

    def fetch_products(self):
        self.send_request('/api/products?limit=999999', 'GET', on_success=self.on_products_loaded, on_failure=self.on_products_fail)

    def on_products_fail(self, req, err):
        log_msg(f'Products Fail: {err}', 'ERROR')
        if self.cache_store.exists('products_data'):
            cached = self.cache_store.get('products_data').get('items', [])
            if cached:
                self.show_alert('Mode Hors Ligne', 'Chargement depuis le cache local.')
                self.on_products_loaded(None, cached)
                return
        self.show_alert('Erreur', f'Échec du chargement:\n{err}')

    def get_cached_image_url(self, image_path_from_server):
        if not image_path_from_server:
            return ''
        try:
            import os
            filename = os.path.basename(image_path_from_server.replace('\\', '/'))
            local_path = os.path.join(self.image_cache_dir, filename)
            if os.path.exists(local_path):
                return local_path
            if not self.available_ips:
                return ''
            ip = self.available_ips[self.current_ip_index]
            img_url = f'{self.api_base_for_ip(ip)}/api/images/{filename}'
            UrlRequest(img_url, on_success=lambda r, res: open(local_path, 'wb').write(res))
            return img_url
        except:
            return ''

    def on_products_loaded(self, req, res):
        if isinstance(res, dict):
            if 'data' in res and isinstance(res['data'], list):
                res = res['data']
            elif 'products' in res and isinstance(res['products'], list):
                res = res['products']
            else:
                res = list(res.values())
        if not isinstance(res, list):
            res = []
        if res and isinstance(res, list):
            self.cache_store.put('products_data', items=res)
        self.all_products = []
        valid_units = ['kg', 'g', 'gramme', 'kilogramme', 'كغ', 'غرام', 'kilo', 'لتر', 'l', 'litre']
        server_image_filenames = set()
        for p in res:
            try:
                price = float(str(p.get('price', 0)).replace(',', '.'))
            except:
                price = 0.0
            if price <= 0:
                continue
            unit = str(p.get('unit', '')).lower().strip()
            if not any((u in unit for u in valid_units)):
                continue
            img_path = p.get('image', '')
            if img_path:
                filename = os.path.basename(img_path.replace('\\', '/'))
                server_image_filenames.add(filename)
            self.all_products.append({'id': p['id'], 'name': p['name'], 'price': price, 'image': img_path, 'ref': str(p.get('ref', ''))})
        if os.path.exists(self.image_cache_dir):
            try:
                cached_files = os.listdir(self.image_cache_dir)
                for f in cached_files:
                    if f not in server_image_filenames:
                        try:
                            full_path = os.path.join(self.image_cache_dir, f)
                            os.remove(full_path)
                        except:
                            pass
            except Exception as e:
                pass
        self.update_rv(self.all_products)
        if not self.all_products:
            self.show_alert('Info', 'Aucun produit pesable trouvé (kg, g...).')

    def update_rv(self, products):
        data = []
        for p in products:
            img_src = self.get_cached_image_url(p['image'])
            data.append({'text_name': self.fix_text(p['name']), 'text_price': f"{p['price']:.2f} DA", 'image_url': img_src, 'product_data': p})
        self.root.get_screen('scale').ids.rv.data = data
        self.root.get_screen('scale').ids.rv.refresh_from_data()

    def filter_products(self, text):
        if not text:
            self.update_rv(self.all_products)
            return
        q = text.lower()
        filtered = [p for p in self.all_products if q in p['name'].lower()]
        self.update_rv(filtered)

    def select_product(self, product):
        self.selected_product = product
        screen = self.root.get_screen('scale')
        screen.ids.bottom_nav.switch_tab('screen_weigh')
        screen.ids.lbl_name.text = self.fix_text(product['name'])
        screen.ids.lbl_price_unit.text = f"{product['price']:.2f} DA"
        self.clear_weight()

    def add_digit(self, digit):
        if not self.selected_product:
            return
        screen = self.root.get_screen('scale')
        curr = screen.ids.txt_weight.text
        if len(curr) >= 5:
            return
        screen.ids.txt_weight.text = curr + digit
        self.calculate_total()

    def backspace(self):
        screen = self.root.get_screen('scale')
        curr = screen.ids.txt_weight.text
        if curr:
            screen.ids.txt_weight.text = curr[:-1]
            self.calculate_total()

    def clear_weight(self):
        self.root.get_screen('scale').ids.txt_weight.text = ''
        self.calculate_total()

    def calculate_total(self):
        screen = self.root.get_screen('scale')
        w_str = screen.ids.txt_weight.text
        try:
            if not w_str:
                screen.ids.lbl_total.text = '0.00 DA'
                return
            weight = float(w_str)
            price = self.selected_product['price']
            total = weight / 1000.0 * price
            from decimal import Decimal, ROUND_HALF_UP
            d_total = Decimal(str(total)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            screen.ids.lbl_total.text = f'{d_total} DA'
        except:
            screen.ids.lbl_total.text = '0.00 DA'

    def send_print_command(self):
        if not self.selected_product:
            self.show_alert('Attention', 'Veuillez sélectionner un produit')
            return
        w_str = self.root.get_screen('scale').ids.txt_weight.text
        if not w_str:
            self.show_alert('Attention', 'Veuillez saisir le poids')
            return
        try:
            w_mm, h_mm = map(int, self.sticker_size.split('x'))
        except:
            w_mm, h_mm = (40, 20)
        data = json.dumps({'product_id': self.selected_product['id'], 'weight': int(w_str), 'width_mm': w_mm, 'height_mm': h_mm})
        self.dialog_loading = MDDialog(text='Impression en cours...', auto_dismiss=False)
        self.dialog_loading.open()
        self.send_request('/api/print_scale_label', 'POST', data, on_success=self.on_print_success, on_failure=self.on_print_fail)

    def on_print_success(self, req, res):
        if self.dialog_loading:
            self.dialog_loading.dismiss()
        self.show_alert('Succès', 'Commande envoyée')
        self.clear_weight()
        self.selected_product = None
        self.root.get_screen('scale').ids.bottom_nav.switch_tab('screen_products')

    def on_print_fail(self, req, err):
        if self.dialog_loading:
            self.dialog_loading.dismiss()
        self.show_alert('Erreur', "Vérifiez l'imprimante ou la connexion")

    def show_alert(self, title, text):
        if self.dialog:
            self.dialog.dismiss()
        self.dialog = MDDialog(title=title, text=text, buttons=[MDFlatButton(text='OK', on_release=lambda x: self.dialog.dismiss())])
        self.dialog.open()

def send_error_to_telegram(error_traceback, error_type='Erreur Système'):
    import threading
    import requests
    from kivy.utils import platform
    import datetime

    def _send_worker():
        BOT_TOKEN = "GITHUB_SECRET_TELEGRAM_BOT_TOKEN"
        MASTER_ADMIN_ID = "GITHUB_SECRET_TELEGRAM_ADMIN_ID"
        if "GITHUB_SECRET" in BOT_TOKEN:
            return 
        device_id = get_device_id_s()
        time_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        safe_traceback = error_traceback
        if len(safe_traceback) > 3500:
            safe_traceback = '... [TRUNCATED] ...\n' + safe_traceback[-3500:]
        msg = f'🚨 **تنبيه خطأ برمجي (CRASH REPORT) - SCALE** 🚨\n\n📱 **الجهاز:** `{device_id}`\n⏰ **الوقت:** `{time_now}`\n📌 **نوع الخطأ:** {error_type}\n\n🛠 **التفاصيل:**\n```python\n{safe_traceback}\n```'
        try:
            requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', json={'chat_id': MASTER_ADMIN_ID, 'text': msg, 'parse_mode': 'Markdown'}, timeout=10)
        except:
            pass
    threading.Thread(target=_send_worker, daemon=True).start()

def console_excepthook(exc_type, exc_value, exc_tb):
    import traceback
    print('!!! CONSOLE ERROR ENGINE !!!')
    traceback.print_exception(exc_type, exc_value, exc_tb)
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    send_error_to_telegram(error_msg, error_type='Console Exception Hook')

sys.excepthook = console_excepthook
if __name__ == '__main__':
    try:
        ScaleApp().run()
    except Exception as e:
        import traceback
        import os
        error_msg = traceback.format_exc()
        print('CRITICAL ERROR:', error_msg)
        send_error_to_telegram(error_msg, error_type='App Critical Crash')
        try:
            with open('crash_log.txt', 'w', encoding='utf-8') as f:
                f.write(error_msg)
        except:
            pass
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            files_dir = PythonActivity.mActivity.getExternalFilesDir(None).getAbsolutePath()
            log_path = os.path.join(files_dir, 'magpro_crash.txt')
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(error_msg)
        except:
            pass
