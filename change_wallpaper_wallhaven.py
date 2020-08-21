#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import argparse
import ctypes
import os
import platform
import requests
import logging
from logging.handlers import RotatingFileHandler
import sys
from configparser import ConfigParser
from io import StringIO
from collections import defaultdict

if sys.version_info <= (2, 6):
    import commands as subprocess
else:
    import subprocess


__SCRIPT_VERSION__ = '1.0.0'
logger = logging.getLogger(__name__)
global config


def load_config():
    """Loads the config file if it exists. Otherwise it creates it with the
    default values at ~/.config/.

    Returns:
        dict: the configuration
    """

    default = defaultdict(str)
    default['apikey'] = ''
    default['sorting'] = 'toplist'
    default['toprange'] = '1d'
    default['order'] = 'desc'
    default['atleast'] = '1920x1080'
    default['categories'] = '100'
    default['purity'] = '100'
    default['display'] = '0'
    default['output'] = '~/Pictures/Wallpapers'

    config_path = os.getcwd() + '/change_wallpaper_haven.rc'
    section_name = 'root'
    try:
        logger.info('Initializing ConfigParcer')
        config = ConfigParser(default)

        if not os.path.exists(config_path):
            logger.info('The config file does not exist, creating it')
            with open(config_path, 'w+') as f:
                config.write(f)
            logger.info('Config file successfully created')
            return default
        else:
            logger.info('Config file already exists, reading it')
            with open(config_path, 'r') as stream:
                stream = StringIO('[{section_name}]\n{stream_read}'.format(
                    section_name=section_name, stream_read=stream.read())
                )
                if sys.version_info >= (3, 0):
                    logger.info('Python >= 3.0 detected')
                    config.read_file(stream)
                else:
                    logger.info('Python < 3.0 detected')
                    config.readfp(stream)

                ret = {}

                # Add a value to ret, printing an error message if needed
                def add_to_ret(fun, name):
                    try:
                        logger.info('Reading value for "' + name + '"')
                        ret[name] = fun(section_name, name)
                    except ValueError:
                        logger.warn('Error in config file. Variable "{}". ' +
                                    'The default "{}" will be used.').format(
                            name, default[name])
                        ret[name] = default[name]

                add_to_ret(config.get, 'apikey')
                add_to_ret(config.get, 'sorting')
                add_to_ret(config.get, 'toprange')
                add_to_ret(config.get, 'order')
                add_to_ret(config.get, 'atleast')
                add_to_ret(config.get, 'categories')
                add_to_ret(config.get, 'purity')
                add_to_ret(config.getint, 'display')
                add_to_ret(config.get, 'output')

                return ret

    except IOError as e:
        logger.error('Error with config file: {}'.format(str(e)))
        return default


def toprange(astring):
    """Validates the given parameter as being a valid toprange parameter for
    the API. Used by the argument parser.

    Args:
        astring (string): A string that is supposed to be a toprange parameter

    Raises:
        ValueError: raised if the given string is not a toprange parameter

    Returns:
        string: the original string if it's a valid one
    """
    if astring not in ['1d', '3d', '1w', '1M', '3M', '6M', '1y']:
        logger.error(astring + ' is not a valid parameter')
        raise ValueError
    return astring


def sorting(astring):
    """Validates the given parameter as being a valid sorting parameter for
    the API. Used by the argument parser.

    Args:
        astring (string): A string that is supposed to be a sorting parameter

    Raises:
        ValueError: raised if the given string is not a sorting parameter

    Returns:
        string: the original string if it's a valid one
    """
    if astring not in ['date_added', 'relevance', 'random', 'views',
                       'favorites', 'toplist']:
        logger.error(astring + ' is not a valid parameter')
        raise ValueError
    return astring


def atleast(astring):
    """Validates the given parameter as being a valid atleast parameter for
    the API. Used by the argument parser.

    Args:
        astring (string): A string that is supposed to be an atleast parameter

    Raises:
        ValueError: raised if the given string is not an atleast parameter

    Returns:
        string: the original string if it's a valid one
    """
    split = astring.split('x')
    if len(split) != 2:
        logger.error(astring + ' is not a valid parameter')
        raise ValueError
    else:
        try:
            int(split[0])
            int(split[1])
        except Exception:
            logger.error(astring + ' is not a valid parameter')
            raise ValueError
    return astring


def order(astring):
    """Validates the given parameter as being a valid order parameter for
    the API. Used by the argument parser.

    Args:
        astring (string): A string that is supposed to be an order parameter

    Raises:
        ValueError: raised if the given string is not an order parameter

    Returns:
        string: the original string if it's a valid one
    """
    if astring not in ['desc', 'asc']:
        logger.error(astring + ' is not a valid parameter')
        raise ValueError
    return astring


def filters(astring):
    """Validates the given parameter as being a valid filters parameter for
    the API. Used by the argument parser.

    Args:
        astring (string): A string that is supposed to be an filters parameter

    Raises:
        ValueError: raised if the given string is not an filters parameter

    Returns:
        string: the original string if it's a valid one
    """
    if len(astring) != 3:
        logger.error(astring + ' is not a valid parameter')
        raise ValueError
    else:
        try:
            int(astring)
        except Exception:
            logger.error(astring + ' is not a valid parameter')
            raise ValueError
    return astring


def parse_args():
    """Parse args with argparse.

    Returns:
        dict: parsed args
    """
    parser = argparse.ArgumentParser(
        description='Daily Wallhaven Wallpaper ' + __SCRIPT_VERSION__
        )

    parser.add_argument(
        '-api', '--apikey', type=str, default=config['apikey'],
        help='Values: your api key, see: https://wallhaven.cc/settings/account'
    )
    parser.add_argument(
        '-s', '--sorting', type=sorting, default=config['sorting'],
        help='Values: date_added, relevance, random, views, favorites, toplist'
    )
    parser.add_argument(
        '-t', '--toprange', type=toprange, default=config['toprange'],
        help='Values: 1d, 3d, 1w, 1M, 3M, 6M, 1y'
    )
    parser.add_argument(
        '-or', '--order', type=order, default=config['order'],
        help='Values: desc, asc'
    )
    parser.add_argument(
        '-al', '--atleast', type=atleast, default=config['atleast'],
        help='Values: 1920x1080 (anything x anything)'
    )
    parser.add_argument(
        '-c', '--categories', type=filters, default=config['categories'],
        help='Values: 100, 110, 111 (general|anime|people), on(1) off(0)'
    )
    parser.add_argument(
        '-p', '--purity', type=filters, default=config['purity'],
        help='Values: 100, 110, 111 (sfw|sketchy|nsfw), on(1) off(0)'
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

    url = (
        'https://wallhaven.cc/api/v1/search?' +
        'sorting=' + config['sorting'] + '&' +
        'topRange=' + config['toprange'] + '&' +
        'purity=' + config['purity'] + '&' +
        'atleast=' + config['atleast'] + '&' +
        'categories=' + config['categories'] + '&' +
        'order=' + config['order']
    )

    response = requests.get(url)

    if (response.status_code == 200):
        data = response.json()
        try:
            return data['data'][0]['path']
        except Exception:
            logger.error(
                'Could not read the API. You either made more than ' +
                '45 requests per minutes, or the API got updated.')
            logger.error(
                'In that case, go to ' +
                'https://github.com/N3ROO/Daily-Wallhaven-Wallpaper and ' +
                'download the latest version or open a new issue')
            sys.exit('Error: API Issue (has it been updated?)')
    else:
        logger.error('Could not reach ' + url + ' - ' + response.status_code)
        logger.error('Are you connected to the Internet?')
        sys.exit('Error: Could not reach wallhaven.cc')


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
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s ' +
                                  '-- %(levelname)s ' +
                                  '-- [%(filename)s:%(lineno)s ' +
                                  '-- %(funcName)s() ] ' +
                                  '-- %(message)s')

    # Console logging
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # File logging
    filename = 'latest_log.log'
    file_handler = RotatingFileHandler(filename, 'w', encoding="UTF-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info('Using Daily Wallhaven Wallpaper v.' + __SCRIPT_VERSION__)

    config = load_config()

    args = parse_args()
    supported_linux_desktop_envs = ['gnome', 'mate', 'kde', 'lubuntu', 'i3']

    # Get top image link
    image_url = get_wallpaper()

    # Image info
    image_id = image_url.split('/')[-1].split('.')[0]
    image_type = image_url.split('.')[-1]

    # Get location where image will be saved
    save_dir = args.output
    if '~' in save_dir:
        save_dir = save_dir.replace('~', os.path.expanduser('~'))
        save_location = '{save_dir}/{id}.{image_type}'.format(
            save_dir=save_dir,
            id=image_id,
            image_type=image_type
        )

    if not os.path.isfile(save_location):
        # Request image if it does not exist yet
        logger.info('Downloading image from ' + image_url)
        response = requests.get(image_url, allow_redirects=False)

        # If image is available, proceed to save
        if response.status_code == 200:
            if not os.path.isfile(save_location):
                # Create directory if it doesn't exist
                dir = os.path.dirname(save_location)
                if not os.path.exists(dir):
                    os.makedirs(dir)

                # Write to disk
                with open(save_location, 'wb') as fo:
                    for chunk in response.iter_content(4096):
                        fo.write(chunk)
        else:
            logger.info('Could not download image, err' + response.status_code)
            sys.exit('Error: Image url is not available, exiting')
    else:
        logger.info('The wallpaper already exists at ' + save_location)

    # Change wallpaper to the new one

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
