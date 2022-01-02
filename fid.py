from secrets import DISCORD_BOT_TOKEN
from secrets import FACEIT_API_KEY
from secrets import STEAM_WEB_API_KEY
from secrets import STEAM_PROFILES

import asyncio, logging
import discord, aiohttp
from dataclasses import dataclass

#logging.basicConfig(level = logging.DEBUG)

@dataclass
class MatchDetails:
    state:   str
    tracked: [str] # tracked Discord usernames
    players: [str] # all FACEIT player ids

class FaceitTracker:
    # Cache: Discord username -> FACEIT player id
    players: dict[str, str]          = {}

    # Tracked Discord usernames (only ones with a resolved FACEIT player id)
    tracked: [str]                   = []

    # Ids of a not yet begun FACEIT matches
    matches: dict[str, MatchDetails] = {}

    async def start(self, steam_web_api_key, faceit_api_key):
        self.steam_web_api_key = steam_web_api_key
        self.faceit_api_key    = faceit_api_key
        self.session           = aiohttp.ClientSession()

        # Perform a full update rougly once in a minute.
        full_update    = 60
        ongoing_update = 2

        while True:
            begun = await faceit_tracker.update()
            logging.info('full update: {}'.format(begun))
            if begun:
                await self.on_match_begin(begun)

            await asyncio.sleep(ongoing_update)
            for _ in range(int(full_update / ongoing_update)):
                begun = await faceit_tracker.update_ongoing()
                logging.info('ongoing update: {}'.format(begun))
                if begun:
                    await self.on_match_begin(begun)

                await asyncio.sleep(ongoing_update)

    async def track(self, discord_username):
        logging.debug('called track {}'.format(discord_username))
        if discord_username in self.tracked:
            logging.debug('ignoring track {}: already tracking'.format(discord_username))
            return

        # Ensure a FACEIT player id can be resolved.
        if discord_username not in self.players:
            if discord_username not in STEAM_PROFILES:
                logging.info('no Steam profile mapping found for {}'.format(discord_username))
                return
            steam_profile = STEAM_PROFILES[discord_username]
            steam_id      = await self._steam_id(steam_profile)
            player        = await self._faceit_player_id(steam_id)

            if player is None:
                logging.info('no FACEIT id found for {}'.format(discord_username))
                return

            logging.info('tracking user {} -> {}'.format(discord_username, player))
            self.players[discord_username] = player

        self.tracked.append(discord_username)

    def untrack(self, discord_username):
        logging.debug('called untrack {}'.format(discord_username))
        if discord_username in self.tracked:
            self.tracked.remove(discord_username)

            for match in list(self.matches):
                if discord_username in self.matches[match].tracked:
                    logging.info('removing untracked user {} from tracked ongoing match {}'.format(discord_username, match))
                    self.matches[match].tracked.remove(discord_username)

                    if not users:
                        logging.info('stop tracking match {}: no tracked users'.format(match))
                        del self.matches[match]
                # The user can only be in one match at a time.
                break

    # Returns the Discord usernames of the players whose match just begun.
    async def update(self) -> [str]:
        begun   = []
        updated = []

        # Try to resolve a match for each user.
        for discord_username in self.tracked:
            # Assume update is called frequently enough that a player can't have joined a new match
            # if the previous hadn't yet begun on last call.
            for match, details in self.matches.items():
                # The user is already in a tracked match.
                if discord_username in details.tracked:
                    break
                elif self.players[discord_username] in details.players:
                    logging.info('tracking new user {} in existing match {}'.format(discord_username, match))
                    details.tracked.append(discord_username)
            else:
                # The user wasn't in any tracked match. Test if they have joined a new one.
                player  = self.players[discord_username]

                ongoing = await self._faceit_ongoing(player)

                if ongoing is None:
                    continue

                ongoing_id, ongoing_state, ongoing_players = ongoing

                # The user should have been added by their FACEIT player id to a tracked match if they were in one.
                assert ongoing_id not in self.matches

                if ongoing_state == 'ONGOING':
                    logging.debug('ignoring already begun match {} for {}:'.format(ongoing_id, discord_username))
                    continue

                self.matches[ongoing_id] = MatchDetails(ongoing_state, [discord_username], ongoing_players)
                updated.append(ongoing_id)

        # Update rest of the match states.
        for match in list(self.matches):
            if match not in updated:
                new_state, players = await self._faceit_match(match)
                if self.matches[match].state == 'CHECK_IN':
                    self.matches[match].players = players
                if new_state == 'ONGOING':
                    logging.info('match {} begun for {}'.format(match, self.matches[match].tracked))
                    begun.extend(self.matches[match].tracked)
                    del self.matches[match]
                else:
                    self.matches[match].state = new_state

        return begun

    # Returns the Discord usernames of the players whose match just begun. Only updates known ongoing matches.
    async def update_ongoing(self) -> [str]:
        begun = []

        for match in list(self.matches):
            new_state, players = await self._faceit_match(match)
            if self.matches[match].state == 'CHECK_IN':
                self.matches[match].players = players
            if new_state == 'ONGOING':
                logging.info('match {} begun for {}'.format(match, self.matches[match].tracked))
                begun.extend(self.matches[match].tracked)
                del self.matches[match]
            else:
                self.matches[match].state = new_state

        return begun

    async def _steam_id(self, steam_profile):
        PREFIX = 'https://steamcommunity.com/'
        kind   = steam_profile.removeprefix(PREFIX).split('/')[0]
        value  = steam_profile.removeprefix(PREFIX).split('/')[1]
    
        match kind:
            case 'profiles':
                return value
            case 'id':
                async with self.session.get(
                    'https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={}&vanityurl={}'.format(self.steam_web_api_key, value)
                ) as resp:
                    json = await resp.json()
                return json['response']['steamid']
            case _:
                raise Exception('unknown link type: {}'.format(steam_profile))
    
    async def _faceit_player_id(self, steam_id):
        async with self.session.get(
            'https://open.faceit.com/data/v4/players?game=csgo&game_player_id={}'.format(steam_id),
            headers = { 'Authorization': 'Bearer {}'.format(self.faceit_api_key) }
        ) as resp:
            if await resp.text() == 'Authentication failed':
                raise Exception('invalid FACEIT Data API Key')

            if resp.status == 404:
                return None

            json = await resp.json()
        return json['player_id']
    
    async def _faceit_ongoing(self, player):
        async with self.session.get(
            'https://api.faceit.com/match/v1/matches/groupByState?userId={}'.format(player)
        ) as resp:
            json = await resp.json()
        payload = json['payload']

        if payload == {}:
            # The player isn't in an ongoing match.
            return None

        state = list(payload)[0]
        inner = payload[state][0]

        # Player ids must be fetched later as they aren't available yet.
        if state == 'CHECK_IN':
            return (inner['id'], state, [player])

        players = []
        for team in inner['teams']:
            for player in inner['teams'][team]['roster']:
                players.append(player['id'])

        return (inner['id'], state, players)

    async def _faceit_match(self, match):
        async with self.session.get(
            'https://open.faceit.com/data/v4/matches/{}'.format(match),
            headers = { 'Authorization': 'Bearer {}'.format(self.faceit_api_key) }
        ) as resp:
            if await resp.text() == 'Authentication failed':
                raise Exception('invalid FACEIT Data API Key')

            json = await resp.json()

        state   = json['status']
        players = []
        for team in json['teams']:
            for player in json['teams'][team]['roster']:
                players.append(player['player_id'])

        return (state, players)

    @staticmethod
    async def on_match_begin(users):
        def any_user_in(vc):
           vc_users = map(str, vc.members)
           return any(user in vc_users for user in users)
    
        for guild in client.guilds:
            voice_channel = next(
                (voice_channel for voice_channel in guild.voice_channels
                    if any_user_in(voice_channel)),
                None
            )
            voice_client = await voice_channel.connect()

client                      = discord.Client()
client.intents.voice_states = True
faceit_tracker              = FaceitTracker()

@client.event
async def on_voice_state_update(member, before, after):
    discord_username = str(member)

    if before.channel is None and after.channel is not None:
        await faceit_tracker.track(discord_username)
    elif before.channel is not None and after.channel is None:
        faceit_tracker.untrack(discord_username)

client.loop.create_task(faceit_tracker.start(STEAM_WEB_API_KEY, FACEIT_API_KEY))
client.run(DISCORD_BOT_TOKEN)
