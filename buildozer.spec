[app]
title = MagPro Scale
package.name = magproscale
package.domain = org.magproscale
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
version = 7.5.0
requirements = python3,kivy,kivymd,requests,urllib3,pillow,arabic-reshaper,python-bidi==0.4.2,six,future,certifi,chardet,idna,android,jnius
icon.filename = apk_icon3.png
orientation = portrait
fullscreen = 0
android.permissions = INTERNET, ACCESS_NETWORK_STATE, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.api = 34
android.minapi = 21
android.enable_androidx = True
android.gradle_dependencies = androidx.core:core:1.10.1
android.accept_sdk_license = True
android.skip_update = False
android.logcat_filters = *:S python:D
android.archs = arm64-v8a
android.add_compilation = True
android.allow_backup = True
android.release_artifact = apk
android.manifest.application_attributes = android:usesCleartextTraffic="true"

[buildozer]
log_level = 2
warn_on_root = 1
