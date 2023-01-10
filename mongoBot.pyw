import sys
import time
import traceback
import base64
import re
import threading
import random
import requests
import json

import pymongo
import mcstatus
import interactions
from interactions.ext.files import command_edit, component_edit, command_send, component_send

from funcs import funcs

try:
    from privVars import *
except ImportError:
    MONGO_URL = "mongodb+srv://..."
    TOKEN = "..."

if MONGO_URL == "mongodb+srv://...":
    print("Please add your mongo url to privVars.py")
    input()
    sys.exit()
if TOKEN == "...":
    print("Please add your bot token to privVars.py")
    input()
    sys.exit()

# Setup
# ---------------------------------------------

bot = interactions.Client(token=TOKEN)

client = pymongo.MongoClient(MONGO_URL, server_api=pymongo.server_api.ServerApi("1"))  # type: ignore

db = client["mc"]
col = db["servers"]
serverList = []
ServerInfo = {}
_port = "25565"

fncs = funcs()

buttons = [
    interactions.Button(
        label="Show Players",
        custom_id="player_show",
        style=interactions.ButtonStyle.PRIMARY,
    )
]
# Funcs
# ---------------------------------------------


def check(host, port="25565"):
    """Checks out a host and adds it to the database if it's not there

    Args:
        host (String): ip of the server

    Returns:
        [list]: {
                    "host":"ipv4 addr",
                    "lastOnline":"unicode time",
                    "lastOnlinePlayers": int,
                    "lastOnlineVersion":"Name Version",
                    "lastOnlineDescription":"Very Good Server",
                    "lastOnlinePing":"unicode time",
                    "lastOnlinePlayersList":["Notch","Jeb"],
                    "lastOnlinePlayersMax": int,
                    "lastOnlineFavicon":"base64 encoded image"
                }
    """

    try:
        server = mcstatus.JavaServer.lookup(host+":"+str(port))

        players = []
        if server.status().players.sample is not None:
            for player in server.status().players.sample: # type: ignore
                url = f"https://api.mojang.com/users/profiles/minecraft/{player.name}"
                jsonResp = requests.get(url)
                if len(jsonResp.text) > 2:
                    jsonResp = jsonResp.json()

                    if jsonResp:
                        players.append(
                            {
                                "name": jsonResp["name"],
                                "uuid": jsonResp["id"],
                            }
                        )

        data = {
            "host": host,
            "lastOnline": time.time(),
            "lastOnlinePlayers": server.status().players.online,
            "lastOnlineVersion": str(re.sub(r"§\S*[|]*\s*", "", server.status().version.name)),
            "lastOnlineDescription": str(re.sub(r"§\S*[|]*\s*", "", re.sub(r"§\S*[|]*\s*", "", str(server.status().description)))),
            "lastOnlinePing": int(server.status().latency * 10),
            "lastOnlinePlayersList": players,
            "lastOnlinePlayersMax": server.status().players.max,
            "lastOnlineVersionProtocol": str(server.status().version.protocol),
            "favicon": server.status().favicon,
        }

        if not col.find_one({"host": host}):
            print("Server not in database, adding...")
            col.insert_one(data)

        for i in list(col.find_one({"host": host})["lastOnlinePlayersList"]): # type: ignore
            if i not in data["lastOnlinePlayersList"]:
                if type(i) == str:
                    url = f"https://api.mojang.com/users/profiles/minecraft/{i}"
                    jsonResp = requests.get(url)
                    if len(jsonResp.text) > 2:
                        jsonResp = jsonResp.json()

                        if jsonResp:
                            data["lastOnlinePlayersList"].append(
                                {
                                    "name": jsonResp["name"],
                                    "uuid": jsonResp["id"],
                                }
                            )
                else:
                    data["lastOnlinePlayersList"].append(i)

        col.update_one({"host": host}, {"$set": data})

        return data
    except Exception as e:
        print(traceback.format_exc(), " | ", host)
        return None


def remove_duplicates():
    """Removes duplicate entries in the database

    Returns:
        None
    """
    for i in col.find():
        if col.count_documents({"host": i["host"]}) > 1:
            col.delete_one({"_id": i["_id"]})


def verify(search, info):
    """Verifies a search

    Args:
        search [dict], len > 0: {
            "host":"ipv4 addr",
            "lastOnline":"unicode time",
            "lastOnlinePlayers": int,
            "lastOnlineVersion":"Name Version",
            "lastOnlineDescription":"Very Good Server",
            "lastOnlinePing":"unicode time",
            "lastOnlinePlayersList":["Notch","Jeb"],
            "lastOnlinePlayersMax": int,
            "favicon":"base64 encoded image"
        }
        info [list], len > 0: {
            "host":"ipv4 addr", # optional
            "lastOnline":"unicode time", # optional
            "lastOnlinePlayers": int, # optional
            "lastOnlineVersion":"Name Version", # optional
            "lastOnlineDescription":"Very Good Server", # optional
            "lastOnlinePing":"unicode time", # optional
            "lastOnlinePlayersList":["Notch","Jeb"], # optional
            "lastOnlinePlayersMax": int, # optional
            "favicon":"base64 encoded image" # optional
        }

    Returns:
        [list]: {
            "host":"ipv4 addr",
            "lastOnline":"unicode time",
            "lastOnlinePlayers": int,
            "lastOnlineVersion":"Name Version",
            "lastOnlineDescription":"Very Good Server",
            "lastOnlinePing":"unicode time",
            "lastOnlinePlayersList":["Notch","Jeb"],
            "lastOnlinePlayersMax": int,
            "favicon":"base64 encoded image"
        }
    """
    out = []
    _items = list(search.items())
    for server in info:
        flag = True
        for _item in _items:
            key = str(_item[0])
            value = str(_item[1])
            if key in server:
                if str(value).lower() not in str(server[key]).lower():
                    flag = False
                    break
        if flag:
            out.append(server)
            
    print(str(len(out)) + " servers match")

    random.shuffle(out);return out

def _find(search, port="25565"):
    # find the server given the parameters
    if search != {}:
        servers = list(col.find())
    else:
        return {
            "host": "Server not found",
            "lastOnline": 0,
            "lastOnlinePlayers": -1,
            "lastOnlineVersion": "Server not found",
            "lastOnlineDescription": "Server not found",
            "lastOnlinePing": -1,
            "lastOnlinePlayersList": [],
            "lastOnlinePlayersMax": -1,
            "favicon": "Server not found"
        }


    for server in servers:
        _items = list(search.items())
        try:
            for _item in _items:
                if _item[0] in server:
                    if str(_item[1]).lower() in str(server[_item[0]]).lower():
                        global _info
                        serverList.append(server)
                        break
        except Exception:
            print(traceback.format_exc())
            print(server, _items, type(server), type(_items))
            break


    server = col.find_one(search) # legacy backup
    _info = verify(search, serverList)

    if len(_info) > 0:
        info = random.choice(_info)
    else:
        info = server

    # for server in _info:
    #     # update the servers
    #     check(server["host"], port)

    return _info, info

def genEmbed(_serverList):
    """Generates an embed for the server list

    Args:
        serverList [list]: {
            "host":"ipv4 addr",
            "lastOnline":"unicode time",
            "lastOnlinePlayers": int,
            "lastOnlineVersion":"Name Version",
            "lastOnlineDescription":"Very Good Server",
            "lastOnlinePing":"unicode time",
            "lastOnlinePlayersList":["Notch","Jeb"],
            "lastOnlinePlayersMax": int,
            "favicon":"base64 encoded image"
        }

    Returns:
        [
            [interactions.Embed]: The embed,
            _file: favicon file,
            button: interaction button,
        ]
    """
    random.shuffle(_serverList)
    info = _serverList[0]
    
    numServers = len(_serverList)
    online = True if check(info["host"], str(_port)) else False

    try:
        _serverList.pop(0)
    except IndexError:
        pass

    # setup the embed
    embed = interactions.Embed(
        title=("🟢 " if online else "🔴 ")+info["host"],
        description='`'+info["lastOnlineDescription"]+'`',
        color=(0x00FF00 if online else 0xFF0000),
        type="rich",
        fields=[
            interactions.EmbedField(name="Players", value=f"{info['lastOnlinePlayers']}/{info['lastOnlinePlayersMax']}", inline=True),
            interactions.EmbedField(name="Version", value=info["lastOnlineVersion"], inline=True),
            interactions.EmbedField(name="Ping", value=str(info["lastOnlinePing"]), inline=True),
            interactions.EmbedField(name="Last Online", value=f"{(time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(info['lastOnline']))) if info['host'] != 'Server not found.' else '0/0/0 0:0:0'}", inline=False),
        ],
        footer=interactions.EmbedFooter(text="Server ID: "+(str(col.find_one({"host":info["host"]})["_id"])[9:-1] if info["host"] != "Server not found." else "-1")+'\n Out of {} servers'.format(numServers)) # type: ignore
    )
    

    try: # this adds the favicon in the most overcomplicated way possible
        if online: # type: ignore
            stats = check(info["host"],str(_port)) # type: ignore

            fav = stats["favicon"] # type: ignore
            if fav is not None:
                bits = fav.split(",")[1]

                with open("server-icon.png", "wb") as f:
                    f.write(base64.b64decode(bits))
                _file = interactions.File(filename="server-icon.png")
                embed.set_thumbnail(url="attachment://server-icon.png")

                print("Favicon added")
            else:
                _file = None
        else:
            _file = None
    except Exception:
        print(traceback.format_exc(),info)
        _file = None

    players = check(info['host'])['lastOnlinePlayersList'] # type: ignore

    buttons = [
        interactions.Button(
            label='Show Players',
            custom_id='show_players',
            style=interactions.ButtonStyle.PRIMARY,
            disabled=(len(players) == 0),
        ),
        interactions.Button(
            label='Next Server',
            custom_id='rand_select',
            style=interactions.ButtonStyle.PRIMARY,
            disabled=(len(_serverList) == 0),
        ),
    ]

    row = interactions.ActionRow(components=buttons) # type: ignore

    return embed, _file, row
    

# Commands
# ---------------------------------------------


@bot.command(
    name="find",
    description="Find a server",
    options=[
        interactions.Option(
            name="_id",
            type=interactions.OptionType.STRING,
            description="The ID of the server",
            required=False,
        ),
        interactions.Option(
            name="host",
            description="The host of the server",
            type=interactions.OptionType.STRING,
            required=False,
        ),
        interactions.Option(
            name="port",
            description="The port of the server",
            type=interactions.OptionType.INTEGER,
            required=False,
        ),
        interactions.Option(
            name="player",
            description="The player to search for **WIP**",
            type=interactions.OptionType.STRING,
            required=False,
        ),
        interactions.Option(
            name="version",
            description="The version of the server",
            type=interactions.OptionType.STRING,
            required=False,
        ),
        interactions.Option(
            name="motd",
            description="The motd of the server",
            type=interactions.OptionType.STRING,
            required=False,
        ),
        interactions.Option(
            name="maxplayers",
            description="The max players of the server",
            type=interactions.OptionType.INTEGER,
            required=False,
        ),
    ],
)
async def find(ctx: interactions.CommandContext, _id: str = None, player: str = None, version: str = None, host: str = None, port: int = 25565, motd: str = None, maxplayers: int = None):  # type: ignore
    """Find a server

    Args:
        _id (str, optional): The ID of the server. Defaults to None.
        host (str, optional): The host of the server. Defaults to None.
        Player (str, optional): The player to search for. Defaults to None.
        version (str, optional): The version of the server. Defaults to None.
        motd (str, optional): The motd of the server. Defaults to None.
        port (int, optional): The port of the server. Defaults to 25565.
    """

    print("find", _id, host, port, player, version, motd, maxplayers)
    
    # send as embed
    await ctx.defer()

    search = {}
    info = ""
    # if parameters are given, add them to the search

    if _id:
        search["_id"] = _id
    if host:
        search["host"] = host.lower()
        check(host, str(port))
    if player:
        search["lastOnlinepsList"] = [player]
    if version:
        search["lastOnlineVersion"] = version.lower()
    if motd:
        search["lastOnlineDescription"] = motd.lower()
    if maxplayers:
        search["lastOnlinePlayersMax"] = maxplayers

    
    try:
        global _serverList
        global ServerInfo
        global _port

        info = {}
        _serverList = []
        _info_ = _find(search, str(port))

        _serverList = list(_info_[0]) # type: ignore
        info = _info_[1] # type: ignore
        ServerInfo = info
        numServers = len(serverList) # type: ignore


        _port = port

        await command_send(ctx, embeds=[interactions.Embed(title="Searching...",description="Sorting through "+str(numServers)+" servers...")])

        # setup the embed
    
        embed = genEmbed(_info)
        _file = embed[1]
        comps = embed[2]
        embed = embed[0]

        
        
        # send the embed sometimes with the favicon
        if _file: # type: ignore
            await command_edit(ctx, embeds=[embed], files=[_file], components=comps) # type: ignore
        else:
            await command_edit(ctx, embeds=[embed], components=comps) # type: ignore
    except Exception as e:
        fncs.log(e)
        await command_send(ctx, embeds=[interactions.Embed(title="Error", description="An error occured while searching. Please try again later and check the logs for more details.", color=0xFF0000)])
        print(f"----\n{e}\n====\n{traceback.format_exc()}\n====\n{type(info)}\n====\n{info}\n====\n====\n{_info}\n====\n----") # type: ignore
        


    threading.Thread(target=remove_duplicates).start()
    print("Duplicates removed")


@bot.component("show_players")
async def show_players(ctx: interactions.ComponentContext):  # type: ignore
    await ctx.defer()

    # get current message

    global ServerInfo
    info = ServerInfo

    players = list(info["lastOnlinePlayersList"])

    embed = interactions.Embed(
        title="Players", 
        description="{} players online".format(len(players)),
    )

    for player in players:
        try:
            if str(player).startswith("{"):
                # player is dict type
                player = json.loads(str(player).replace("'", '"'))
                embed.add_field(name=player["name"], value="`{}`".format(player["uuid"]), inline=True)
            else:
                # player is str type
                embed.add_field(name=player, value="`{}`".format(player), inline=True)
        except Exception:
            print(traceback.format_exc())
            print(player)
            break

    await component_send(ctx, embeds=[embed], ephemeral=True)

@bot.component("rand_select")
async def rand_select(ctx: interactions.ComponentContext):
    await ctx.defer(edit_origin=True)
    
    global _serverList

    embed = genEmbed(_serverList)
    _file = embed[1]
    button = embed[2]
    embed = embed[0]

    if _file:
        await component_edit(ctx, embeds=[embed], files=[_file], components=button)
    else:
        await component_edit(ctx, embeds=[embed], components=button)



@bot.command(
    name="stats",
    description="Get stats about the database",
)
async def stats(ctx: interactions.CommandContext):  # type: ignore
    await ctx.defer()
    try:
        """Get stats about the database"""
        players = 0
        for i in col.find():
            players += i["lastOnlinePlayers"]
        serverCount = col.count_documents({})

        text = f"Total servers: `{serverCount}`\nTotal players: `{players}`\nMost common version: `...`"

        await ctx.send(embeds=[interactions.Embed(title="Stats", description=text)])  # type: ignore
        print("Getting most common version...")

        versions = []

        for i in col.find():
            versions.append(i["lastOnlineVersion"])

        versions.sort(key=versions.count, reverse=True)


        print(
            f"Total servers: {serverCount}\nTotal players: {players}\nMost common version: {str(versions[0:10])[1:-1]}"
        )

        # edit the message
        text = "Total servers: `{}`\nTotal players: `{}`\nMost common version:\n```{}```".format(serverCount,players,('\n'.join(versions[0:5])))

        await ctx.edit(embeds=[interactions.Embed(title="Stats", description=text)])  # type: ignore
    except Exception as e:
        print(f"====\nError: {e}\n====")
        fncs.log(f"Error: {e}")

        await ctx.send(embeds=[interactions.Embed(title="Error", description="Error getting stats, check the console and log for more info.")])  # type: ignore


    threading.Thread(target=remove_duplicates).start()
    print("Duplicates removed")



@bot.command(name="restart")
async def restart(ctx: interactions.CommandContext):  # type: ignore
    """Restart the bot"""
    
    fncs.log("Restarting...")
    await ctx.send("Restarting...")
    sys.exit(0)



@bot.command(name="help")
async def help(ctx: interactions.CommandContext):  # type: ignore
    """Get help"""
    await ctx.send(
        embeds=[
            interactions.Embed(
                title="Help",
                description="""Commands: \n`/find` - Find a server\n*Returns:*\n`    (desc, db _id, players, version, ping, players online, last online (y/m/d h:m:s))`\n`/stats` - Get stats about the database\n`/restart` - Restart the bot\n`/help` - Get help\n""",
            )
        ]
    )


# Run the bot
# ---------------------------------------------


if __name__ == "__main__":
    while True:
        try:
            bot.start()
        except Exception as e:
            if e == KeyboardInterrupt:
                break
            else:
                print(e)
                fncs.log(e)
                time.sleep(30)
                break
