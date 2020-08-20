#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import argparse
import ctypes
import os
import platform
import requests
import sys
from configparser import ConfigParser
from io import StringIO
from collections import defaultdict

if sys.version_info <= (2, 6):
    import commands as subprocess
else:
    import subprocess


def load_config():
    """Loads the config file if it exists. Otherwise it creates it with the
    default values at ~/.config/.

    Returns:
        dict: the configuration
    """

    default = defaultdict(str)
    default['nsfw'] = 'False'
    default['time'] = '1d'
    default['display'] = '0'
    default['output'] = '~/Pictures/Wallpapers'

    config_path = os.path.expanduser('~/.config/change_wallpaper_haven.rc')
    section_name = 'root'
    try:
        config = ConfigParser(default)

        if not os.path.exists(config_path):
            with open(config_path, 'w+') as f:
                config.write(f)
            return default
        else:
            with open(config_path, 'r') as stream:
                stream = StringIO('[{section_name}]\n{stream_read}'.format(
                    section_name=section_name, stream_read=stream.read())
                )
                if sys.version_info >= (3, 0):
                    config.read_file(stream)
                else:
                    config.readfp(stream)

                ret = {}

                # Add a value to ret, printing an error message if needed
                def add_to_ret(fun, name):
                    try:
                        ret[name] = fun(section_name, name)
                    except ValueError:
                        err_str = ('Error in config file. Variable {}. ' +
                                   'The default {} will be used.').format(
                            name, default[name])
                        print(err_str)
                        ret[name] = default[name]

                add_to_ret(config.getboolean, 'nsfw')
                add_to_ret(config.getint, 'display')
                add_to_ret(config.get, 'time')
                add_to_ret(config.get, 'output')

                return ret

    except IOError as e:
        print(e)
        return default


config = load_config()


def sorting(astring):
    """Validates the given parameter as being a valid sorting parameter for the
    API. Used by the argument parser.

    Args:
        astring (string): A string that is supposed to be a sorting parameter

    Raises:
        ValueError: raised if the given string is not a sorting parameter

    Returns:
        string: the original string if it's a valid one
    """
    if astring not in ['1d', '3d', '1w', '1M', '3M', '6M', '1y']:
        raise ValueError
    return astring


def parse_args():
    """Parse args with argparse.

    Returns:
        dict: parsed args
    """
    parser = argparse.ArgumentParser(description='Daily Wallhaven Wallpaper')

    parser.add_argument(
        '-t', '--sort', type=sorting, default=config['time'],
        help='Example: 1d, 3d, 1w, 1M, 3M, 6M, 1y'
    )
    parser.add_argument(
        '-n', '--nsfw', action='store_true', default=config['nsfw'],
        help='Enables NSFW tagged posts.'
    )
    parser.add_argument(
        '-d', '--display', type=int, default=config['display'],
        help='Desktop display number on OS X ' +
             '(0: all displays, 1: main display, etc'
    )
    parser.add_argument(
        '-o', '--output', type=str, default=config['output'],
        help='Set the output directory to save the Wallpapers to.')

    return parser.parse_args()


def get_wallpaper():
    """Get link of the wallpaper corresponding to the given arguments. Uses
    https://wallhaven.cc/help/api.

    Stops the program if no images were found.

    Returns:
        string: the wallpaper url
    """

    response = requests.get(
        'https://wallhaven.cc/api/v1/search?' +
        'sorting=toplist' + '&' +
        'topRange=1d' + '&' +
        'atleast=1920x1080'
    )

    if (response.status_code == 200):
        data = response.json()
        try:
            return data['data'][0]['path']
        except Exception:
            sys.exit('Error: API Issue (has it been updated?)')
    else:
        sys.exit('Error: Could not look for images online on wallhaven.cc')


def detect_desktop_environment():
    """Get current Desktop Environment http://stackoverflow.com/questions/
    2035657/what-is-my-current-desktop-environment

    Returns:
        dict: environment
    """
    environment = {}
    if os.environ.get('KDE_FULL_SESSION') == 'true':
        environment['name'] = 'kde'
        environment['command'] = """
qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript '
    var allDesktops = desktops();
    print (allDesktops);
    for (i=0;i<allDesktops.length;i++) {{
        d = allDesktops[i];
        d.wallpaperPlugin = "org.kde.image";
        d.currentConfigGroup = Array("Wallpaper",
                                "org.kde.image",
                                "General");
        d.writeConfig("Image", "file:///{save_location}")
    }}
'
                """
    elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
        environment['name'] = 'gnome'
        environment['command'] = \
            ('gsettings set ' +
             'org.gnome.desktop.background picture-uri file://{save_location}')
    elif os.environ.get('DESKTOP_SESSION') == 'Lubuntu':
        environment['name'] = 'lubuntu'
        environment['command'] = \
            ('pcmanfm -w ' +
             '{save_location} --wallpaper-mode=fit')
    elif os.environ.get('DESKTOP_SESSION') == 'mate':
        environment['name'] = 'mate'
        environment['command'] = \
            ('gsettings set ' +
             'org.mate.background picture-filename {save_location}')
    elif os.environ.get('DESKTOP_SESSION') == 'i3':
        environment['name'] = 'i3'
        environment['command'] = 'feh --bg-scale {save_location}'
    else:
        try:
            info = subprocess.getoutput('xprop -root _DT_SAVE_MODE')
            if ' = "xfce4"' in info:
                environment['name'] = 'xfce'
        except (OSError, RuntimeError):
            environment = None
            pass
    return environment


if __name__ == '__main__':
    args = parse_args()
    supported_linux_desktop_envs = ['gnome', 'mate', 'kde', 'lubuntu', 'i3']

    # Get top image link
    image_url = get_wallpaper()

    # Request image
    response = requests.get(image_url, allow_redirects=False)

    # If image is available, proceed to save
    if response.status_code == 200:
        # Get location where image will be saved
        save_dir = args.output
        if '~' in save_dir:
            save_dir = save_dir.replace('~', os.path.expanduser('~'))

        image_id = image_url.split('/')[-1].split('.')[0]
        image_type = image_url.split('.')[-1]
        save_location = '{save_dir}/{id}.{image_type}'.format(
            save_dir=save_dir,
            id=image_id,
            image_type=image_type
        )

        if not os.path.isfile(save_location):
            # Create directory if it doesn't exist
            dir = os.path.dirname(save_location)
            if not os.path.exists(dir):
                os.makedirs(dir)

            # Write to disk
            with open(save_location, 'wb') as fo:
                for chunk in response.iter_content(4096):
                    fo.write(chunk)

        # Check OS and environments
        platform_name = platform.system()
        if platform_name.startswith('Lin'):

            # Check desktop environments for linux
            desktop_environment = detect_desktop_environment()
            if ((desktop_environment and desktop_environment['name'])
                    in supported_linux_desktop_envs):
                os.system(desktop_environment['command'].format(
                    save_location=save_location)
                )
            else:
                print('Unsupported desktop environment')

        # Windows
        if platform_name.startswith('Win'):
            # Python 3.x
            if sys.version_info >= (3, 0):
                ctypes.windll.user32.SystemParametersInfoW(
                    20, 0, save_location, 3
                )
            # Python 2.x
            else:
                ctypes.windll.user32.SystemParametersInfoA(
                    20, 0, save_location, 3
                )

        # OS X/macOS
        if platform_name.startswith('Darwin'):
            if args.display == 0:
                command = """
                        osascript -e 'tell application "System Events"
                            set desktopCount to count of desktops
                            repeat with desktopNumber from 1 to desktopCount
                                tell desktop desktopNumber
                                    set picture to "{save_location}"
                                end tell
                            end repeat
                        end tell'
                          """.format(save_location=save_location)
            else:
                command = """osascript -e 'tell application "System Events"
                                set desktopCount to count of desktops
                                tell desktop {display}
                                    set picture to "{save_location}"
                                end tell
                            end tell'""".format(display=args.display,
                                                save_location=save_location)
            os.system(command)
    else:
        sys.exit('Error: Image url is not available, ' +
                 'the program is now exiting.')
