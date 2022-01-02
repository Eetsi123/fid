from os import environ

DISCORD_BOT_TOKEN = environ['DISCORD_BOT_TOKEN'] # https://discord.com/developers/applications
FACEIT_API_KEY    = environ['FACEIT_API_KEY']    # https://developers.faceit.com/apps
STEAM_WEB_API_KEY = environ['STEAM_WEB_API_KEY'] # https://steamcommunity.com/dev/apikey

# At least on of these needs to be on a voice channel for the match start to be detected.
STEAM_PROFILES    = {
    'Akke#1087':              'https://steamcommunity.com/id/Akkemonsteri',
    'EHmeister=DD#2146':      'https://steamcommunity.com/id/EHmeister',
    'Eetsi123#2859':          'https://steamcommunity.com/id/eetsi123',
    'Haavi#7514':             'https://steamcommunity.com/id/HaaviTheMlg',
    'Helloo#7792':            'https://steamcommunity.com/id/hello17',
    'Jage#0424':              'https://steamcommunity.com/id/Jagecron',
    'Kapy#7076':              'https://steamcommunity.com/id/Kapy12',
    'Mikazuu#6315':           'https://steamcommunity.com/id/mikazuu',
    'Perunakelloヅヅヅ#7782': 'https://steamcommunity.com/profiles/76561198201677379',
    'Ronizzi#4638':           'https://steamcommunity.com/id/ronizzi',
    'ela#6568':               'https://steamcommunity.com/id/elastis',
    'emppu120#1968':          'https://steamcommunity.com/id/emppu120',
}

# Set to None to disable downloading and use local file.
AUDIO_SOURCE      = 'https://cdn-frontend.faceit.com/web/static/media/found-tone.3fd8806a.mp3'
AUDIO_FILE        = 'faceit.mp3'
