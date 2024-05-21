import requests
import logging
import sqlite3

logger = logging.getLogger(__name__)
connection = sqlite3.connect("bot.db")
cursor = connection.cursor()
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS Users (
id INTEGER PRIMARY KEY,
userid TEXT,
artistname TEXT,
artistid TEXT,
artisturl TEXT
)
"""
)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS Releases (
id INTEGER PRIMARY KEY,
artistname TEXT,
artistid TEXT,
releasename TEXT,
releasetype TEXT,
releasedate TEXT,
releaseurl TEXT,
artistsids TEXT,
artisturl TEXT
)
"""
)
connection.commit()
connection.close()
spotoken = ''

def getsptfytoken():  # сгенерить токен споти апи
    result = requests.post(
        url="https://accounts.spotify.com/api/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": "cbc2fe50f47e423d86764c218532c40b",
            "client_secret": "564c3935fe1f43ada56766e6440796fe",
        },
    )
    return (
        result.json()["access_token"]
        if result.status_code == 200
        else print(logger.critical("не удалось схватить токен??"))
    )


def spotysearchnameid(name, spotoken):  # вернуть айди музыканта
    artistid = requests.get(
        url="https://api.spotify.com/v1/search"
        + f"?q={name.replace(' ', '+')}&type=artist",
        headers={"Authorization": f"Bearer {spotoken}"},
    )
    if artistid.status_code != 200:
        return [False, False]
    return (
        [
            artistid.json()["artists"]["items"][0]["name"],
            artistid.json()["artists"]["items"][0]["id"],
        ]
        if artistid.json()["artists"]["items"]
        else [False, False]
    )


def spotysearch(name, spotoken):  # вернуть айди музыканта
    truename = spotysearchnameid(name, spotoken)[0]
    if truename == False:
        return "такого исполнителя нету: " + name
    artistid = requests.get(
        url="https://api.spotify.com/v1/search"
        + f"?q={truename.replace(' ', '+')}&type=artist",
        headers={"Authorization": f"Bearer {spotoken}"},
    )
    return "что я нашёл по запросу:\nhttps://open.spotify.com/artist/" + str(
        artistid.json()["artists"]["items"][0]["id"]
    )

def sortcriteria(release):
    return release[2]

def spotysearchalbums(name, spotoken, include = 'album%2Csingle%2Cappears_on%2Ccompilation',offset = 0,forbd = False,limit=30):
    truename,trueid = spotysearchnameid(name, spotoken)
    if truename == False:
        return "такого исполнителя нету: " + name
    sptalbums = requests.get(
        url=f"https://api.spotify.com/v1/artists/{trueid}/albums?include_groups={include}&limit={limit}&offset={offset}",
        headers={"Authorization": f"Bearer {spotoken}"},
    ).json()
    if 'error' in sptalbums.keys():
        return False
    result = [[truename
                , sptalbums["items"][i]["name"]
                , sptalbums["items"][i]["release_date"]
                , sptalbums["items"][i]["album_group"]
                , sptalbums["items"][i]["external_urls"]["spotify"]] for i in range(len(sptalbums["items"]))
              ] if not forbd else [[truename
                , sptalbums["items"][i]["name"]
                , sptalbums["items"][i]["release_date"]
                , sptalbums["items"][i]["album_group"]
                , sptalbums["items"][i]["external_urls"]["spotify"]
                , ", ".join(i["id"] for i in sptalbums["items"][i]["artists"])
                , ", ".join(i["external_urls"]['spotify'] for i in sptalbums["items"][i]["artists"])] for i in range(len(sptalbums["items"]))]
    return sorted(result, key=sortcriteria, reverse=True)


def bdsubs(name,dosub : bool, userid, spotoken):
    truename,trueid = spotysearchnameid(name, spotoken)
    if truename == False:
        return "такого исполнителя нету: " + name
    connection = sqlite3.connect("bot.db")
    cursor = connection.cursor()
    cursor.execute('SELECT artistid FROM Users WHERE artistid = ? and userid =?',(trueid,userid))
    usersubstatus = cursor.fetchall()
    if not usersubstatus and dosub:
        cursor.execute('INSERT INTO Users (userid, artistname, artistid, artisturl) VALUES (?, ?, ?, ?)', (userid, truename, trueid, "https://open.spotify.com/artist/" + trueid))
        cursor.execute('SELECT artistname FROM Releases WHERE artistname = ?',(truename,))
        addinfo = cursor.fetchall()
        connection.commit()
        connection.close()
        if not addinfo:
            addreleases(truename, spotoken)
        else:
            checkupdates(spotoken, singlecheck=True, artistname=truename)
        return "Вы подписались на "+ truename + "\n" + "https://open.spotify.com/artist/" + trueid
    elif usersubstatus and dosub:
        connection.commit()
        connection.close()
        return "Вы уже подписаны на " + truename + "\n" + "https://open.spotify.com/artist/" + trueid
    elif usersubstatus and dosub == False:
        cursor.execute('DELETE FROM Users WHERE artistid = ? and userid = ?', (trueid,userid))
        connection.commit()
        connection.close()
        delreleases(truename, spotoken)
        return "Вы отписались от " + truename + "\n" + "https://open.spotify.com/artist/" + trueid
    elif not usersubstatus and dosub == False:
        connection.commit()
        connection.close()
        return "Вы не подписаны на " + truename + "\n" + "https://open.spotify.com/artist/" + trueid




def addreleases(name, spotoken):
    connection = sqlite3.connect("bot.db")
    cursor = connection.cursor()
    truename,trueid = spotysearchnameid(name, spotoken)
    offset = 0
    limit = 50
    while True:
        releases = spotysearchalbums(truename, spotoken, forbd=True, offset=offset,limit = limit)
        print(releases)
        if not releases:
            break
        for i in releases:
            artistname, releasename, releasedate, releasetype, releaseurl, artistsids, artisturls = i
            cursor.execute('INSERT INTO Releases (artistname, artistid, releasename, releasetype, releasedate, releaseurl, artistsids, artisturl) VALUES (?, ?, ?, ?, ?, ?, ?,?)', (artistname, trueid, releasename, releasetype, releasedate, releaseurl, artistsids, artisturls))
        offset += 50
    connection.commit()
    connection.close()
def delreleases(name, spotoken):
    truename= spotysearchnameid(name, spotoken)[0]
    connection = sqlite3.connect("bot.db")
    cursor = connection.cursor()
    cursor.execute('SELECT artistname FROM Users WHERE artistname = ?',(truename,))
    userdata = cursor.fetchall()
    if not userdata:
        cursor.execute('DELETE FROM Releases WHERE artistname = ?', (truename,))
    else:
        return False
    connection.commit()
    connection.close()


def showsubsmethod(userid):
    connection = sqlite3.connect("bot.db")
    cursor = connection.cursor()
    cursor.execute('SELECT artistname, artisturl FROM Users WHERE userid = ?', (userid,))
    info = cursor.fetchall()
    return "Ваши подписки:\n" + "\n".join(' - '.join(i) for i in info)

def checkupdates(spotoken,singlecheck=False, artistname = 'artistname'):
    connection = sqlite3.connect("bot.db")
    cursor = connection.cursor()
    updaterel = []
    if not singlecheck:
        cursor.execute('SELECT distinct artistname FROM Users')
        info = cursor.fetchall()
        print(info)
    else:
        info = [[artistname]]
    for i in info:
        newreleases = []
        cursor.execute('SELECT releaseurl FROM Releases WHERE artistname = ?',(i[0],))
        oldreleases = cursor.fetchall()
        oldreleases = [j[0] for j in oldreleases]
        offset = 0
        while True:
            list = spotysearchalbums(i[0], spotoken,include = 'album%2Csingle%2Cappears_on%2Ccompilation', forbd=True, offset=offset, limit=50)
            print("запуск из чекапдейтов",i)
            if not list:
                break
            newreleases += list
            offset += 50
        for j in newreleases:
            if j[4] not in oldreleases:
                updaterel += [j]
    updateresult = {}
    for i in updaterel:
        trueid = spotysearchnameid(i[0], spotoken)[1]
        truename, releasename, releasedate, releasetype, releaseurl, artistsids, artisturls = i
        cursor.execute('SELECT userid FROM Users where artistid = ?',(trueid,))
        userlist = cursor.fetchall()
        for j in userlist:
            if j[0] not in updateresult.keys():
                updateresult[j[0]] = []
            updateresult[j[0]] += ['\n'.join(i[:5])]
        cursor.execute(
            'INSERT INTO Releases (artistname, artistid, releasename, releasetype, releasedate, releaseurl, artistsids, artisturl) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (truename, trueid, releasename, releasetype, releasedate, releaseurl, artistsids, artisturls))
    connection.commit()
    connection.close()
    print("прочекал апдейты")
    return updateresult
