import re
import datetime

from flask import send_from_directory, render_template, request, redirect, url_for

from server.spotify import SpotifyApi
from server.db import Database

import param
import dbPrmAndReq

spotify = SpotifyApi(param.spotifyApiClientId, param.spotifyApiSecret,
                     param.spotifyApiScopeLs, param.localServerName,
                     param.localServerPort, param.localServerPage)
spotifyData = {}

db = Database(dbPrmAndReq.dbFilePath, dbPrmAndReq.dbSchema,
              dbPrmAndReq.dbIndexesAfterMassInsert)


def favicon():
    return send_from_directory("./",
                               'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


def init():
    print("sending init page")
    spotifyUserConnectionUrl = spotify.userConnectionUrl()
    return redirect(spotifyUserConnectionUrl)


def index():
    print("sending home page")
    spotifyCode = request.args.get("code")
    spotifyState = request.args.get("state")
    spotify.requestRefreshAndAccessToken(spotifyCode, spotifyState)
    spotifyData["user"] = spotify.getCurrentUserId()
    spotifyData["playlists"] = spotify.getCurrentUserPlaylists(
        spotifyData["user"])
    return render_template('index.html', spotifyData=spotifyData)


def deleteChoices():
    # really weird hack, if request.form is not copied to a new obj, the third time we acces it, it makes the client not send the third data in the form
    formData = dict(request.form)
    if formData.get("delSpotifyPlaylists") == ["on"]:
        print("deleting local data and spotify playlists")
        db.dropDatabase()
        for playlistName, playlistId in spotifyData["playlists"]:
            if re.search(re.escape(param.playlistSuffix) + r"$", playlistName):
                spotify.deletePlaylist(playlistId)
    retrieveSpotifyData = False
    if formData.get("spotifyRetrieve") == ["on"]:
        print("getting data through spotify api on")
        retrieveSpotifyData = True
    else:
        print("skipping getting data through spotify api")

    livesDelete = False
    if formData.get("livesDelete") == ["on"]:
        print("deleting lives on")
        livesDelete = True
    instrumentalDelete = False
    if formData.get("instrumentalDelete") == ["on"]:
        print("deleting instrumentals on")
        instrumentalDelete = True
    demoDelete = False
    if formData.get("demoDelete") == ["on"]:
        print("deleting demo on")
        demoDelete = True
    remixDelete = False
    if formData.get("remixDelete") == ["on"]:
        print("deleting remixes on")
        remixDelete = True
    duplicatesDelete = False
    if formData.get("duplicatesDelete") == ["on"]:
        print("deleting duplicates on")
        duplicatesDelete = True

    db.connect()
    if retrieveSpotifyData:
        db.removeIndexes()
        artistCount = 0
        albumCount = 0
        trackCount = 0
        artistList = spotify.getCurrentUserArtists()
        artistListLen = len(artistList)
        for artist in artistList:
            artistCount += 1
            print("\n\nartist: " + str(artistCount) + "/" + str(artistListLen))
            artistId = artist["id"]
            artistName = artist["name"].lower()
            artistGenre = " ".join(artist["genres"])
            try:
                # artistUrl = artist["external_urls"]["spotify"]  # thats the web link tho
                artistUrl = artist["uri"]  # thats the app url
            except Exception:
                artistUrl = ""
            # artist insert in db
            db.insertYolo("artist",
                          (artistId, artistName, artistGenre, artistUrl))
            for artistAlbum in spotify.getArtistAlbum(
                    artistId, country=param.countryCode):
                albumCount += 1
                if albumCount % 100 == 0:
                    print("album: " + str(albumCount))
                albumId = artistAlbum["id"]
                albumName = artistAlbum["name"].lower()
                if len(
                        db.select("select 1 from album where id = '{}'".format(
                            albumId))) != 0:
                    print("album {} from {} already treated".format(
                        albumName, artistName))
                else:
                    albumDate = artistAlbum["release_date"]
                    try:
                        albumDateObj = datetime.datetime.strptime(
                            albumDate, "%Y-%m-%d")
                    except:
                        try:
                            albumDateObj = datetime.datetime.strptime(
                                albumDate, "%Y-%m")
                        except:
                            try:
                                albumDateObj = datetime.datetime.strptime(
                                    albumDate, "%Y")
                            except:
                                albumDateObj = None
                    if albumDateObj is None:
                        albumDate = None
                    else:
                        albumDate = int(albumDateObj.strftime("%Y%m%d"))
                    # album insert in db
                    db.insertYolo("album",
                                  (albumId, artistId, albumName, albumDate))
                    for albumTrack in spotify.getAlbumTrack(
                            albumId, country=param.countryCode):
                        trackCount += 1
                        if trackCount % 1000 == 0:
                            print("track: " + str(trackCount))
                        trackIsPlayable = albumTrack["is_playable"]
                        if trackIsPlayable:
                            trackId = albumTrack["id"]
                            trackUri = albumTrack["uri"]
                            trackName = albumTrack["name"].lower()
                            trackDiscNumber = albumTrack["disc_number"]
                            trackNumber = albumTrack["track_number"]
                            trackDuration = albumTrack["duration_ms"]
                            try:
                                trackDuration = int(trackDuration / 1000)
                            except:
                                trackDuration = None
                            # track insert in db
                            db.insertYolo("track", (
                                trackId,
                                albumId,
                                trackName,
                                trackUri,
                                trackDuration,
                                trackDiscNumber,
                                trackNumber,
                                0,
                            ))
        db.addIndexes()
        db.commit()

    if livesDelete or instrumentalDelete or demoDelete or remixDelete or duplicatesDelete:
        print("data count before apuration: artists/albums/tracks")
        print(
            db.select(
                "select (SELECT count(*) FROM artist), (SELECT count(*) FROM album), (SELECT count(*) FROM track);"
            ))

        if livesDelete:
            print("deleting lives albums")
            for idalbum, name in db.select(
                    "select id, name from album where name like '%live%'"):
                if name.lower() == "live" or re.search(
                        r"^live[^\w]|[^\w]live$|[^\w]live[^\w]", name.lower()):
                    db.delete("delete from track where albumId = '{}'".format(
                        idalbum))
                    db.delete(
                        "delete from album where id = '{}'".format(idalbum))
            db.commit()

            print("deleting live tracks")
            for idtrack, name in db.select(
                    "select id, name from track where name like '%live%'"):
                if re.search(r".+\(live\).+|-[^\w]*live\s*$", name.lower()):
                    db.delete(
                        "delete from track where id = '{}'".format(idtrack))
            db.commit()

        if instrumentalDelete:
            print("deleting instrumentals tracks")
            for idtrack, name in db.select(
                    "select id, name from track where name like '%instrumental%'"
            ):
                if name.lower() == "instrumental" or re.search(
                        r"^instrumental[^\w]|[^\w]instrumental$|[^\w]instrumental[^\w]",
                        name.lower()):
                    db.delete(
                        "delete from track where id = '{}'".format(idtrack))
            db.commit()

        if demoDelete:
            print("deleting demos")
            for idtrack, name in db.select(
                    "select id, name from track where name like '%demo%'"):
                if re.search(r".+\(demo\).+|-[^\w]*demo\s*$", name.lower()):
                    db.delete(
                        "delete from track where id = '{}'".format(idtrack))
            db.commit()

        if remixDelete:
            print("deleting remixes")
            for idtrack, name in db.select(
                    "select id, name from track where name like '%demo%'"):
                if re.search(r"^remix[^\w]|[^\w]remix$|[^\w]remix[^\w]",
                             name.lower()):
                    db.delete(
                        "delete from track where id = '{}'".format(idtrack))
            db.commit()

        if duplicatesDelete:
            print("deleting obvious duplicates")
            for trackLine in db.select(dbPrmAndReq.removeDuplicateSimple):
                trackId = trackLine[0]
                db.delete("delete from track where id = '" + trackId + "';")
            db.commit()

            print("deleting tracks already treated")
            for trackLine in db.select(dbPrmAndReq.removeAlreadyTreated):
                trackId = trackLine[0]
                db.delete("delete from track where id = '" + trackId + "';")
            db.commit()

            print(
                "deleting duplicates based on artist and track name, the oldest track is choosed if conflict"
            )
            for trackLine in db.select(dbPrmAndReq.removeSimilarTracks):
                trackId = trackLine[0]
                db.delete("delete from track where id = '" + trackId + "';")
            db.commit()

            print(
                "checks if some track have its name contained in another track. If so, also checks if the two tracks have about the same duration"
            )
            whereClauseList = []
            if livesDelete:
                whereClauseList.append("dbl.trackName not like '%live%' and")
            if instrumentalDelete:
                whereClauseList.append(
                    "dbl.trackName not like '%instrumental%' and")
            if demoDelete:
                whereClauseList.append("dbl.trackName not like '%demo%' and")
            if remixDelete:
                whereClauseList.append("dbl.trackName not like '%remix%' and")
            whereClause = " " + " ".join(whereClauseList) + " "
            requestBuild = dbPrmAndReq.removeSimilarTracksBasedOnName.format(
                whereClause)
            for trackLine in db.select(requestBuild):
                trackId = trackLine[0]
                db.delete("delete from track where id = '" + trackId + "';")
            db.commit()

        print("data count after apuration: artists/albums/tracks")
        print(
            db.select(
                "select (SELECT count(*) FROM artist), (SELECT count(*) FROM album), (SELECT count(*) FROM track);"
            ))
    db.close()
    return redirect(url_for('playlistInput'))


def playlistInput():
    db.connect()
    artistLs = []
    for artistname, artistid, genre, url in db.select(
            "select name, id, genre, url from artist order by name"):
        artistDict = {
            "name": artistname,
            "id": artistid,
            "genreDisplay": "spotify's artist's genre: " + genre,
            "url": url,
            "playlists": []
        }
        for playlistname, playlistid in db.select("select playlist.name, playlist.id from artistPlaylist " + \
            "inner join playlist on artistPlaylist.playlistId = playlist.id " + \
            "where artistPlaylist.artistId = {} order by playlist.name".format(db.formatSqlString(artistid))):

            artistDict["playlists"].append({
                "name": playlistname,
                "id": playlistid
            })
        artistLs.append(artistDict)
    playlistLs = [
        x[0] for x in db.select("select name from playlist order by name;")
    ]
    db.close()
    return render_template('playlistInput.html',
                           artistLs=artistLs,
                           playlistLs=playlistLs)


def playlistValidate():
    return str(request.form.keys())
    db.connect()
    db.delete("delete from artistPlaylist;")
    for artistName in request.form.keys():
        for playlistName in request.form.getlist(artistName):
            if not re.search(r"^\s*$", playlistName):
                artistSearch = db.select(
                    "select id from artist where name = {}".format(
                        db.formatSqlString(artistName)))
                artistId = artistSearch[0][0]
                artistPlaylistSearch = db.select("""
                    select p.name, a.id
                    from artist a
                    inner join artistPlaylist ap on a.id = ap.artistId
                    inner join playlist p on p.id = ap.playlistId
                    where a.id = {} and p.name = {}""".format(
                    db.formatSqlString(artistId),
                    db.formatSqlString(playlistName)))
                if len(artistPlaylistSearch) == 0:
                    playlistSearch = db.select(
                        "select id from playlist where name = {}".format(
                            db.formatSqlString(playlistName)))
                    if len(playlistSearch) == 0:
                        playlistId = db.select(
                            "select max(id) + 1 from playlist")[0][0]
                        if playlistId is None:
                            playlistId = 0
                        db.insert("playlist", (playlistId, playlistName))
                    else:
                        playlistId = playlistSearch[0][0]
                    db.insert("artistPlaylist", (artistId, playlistId))
    db.commit()
    # creating or retrieving playlists
    for playlistName, playlistId in db.select(
            "select playlist.name, playlist.id from playlist order by playlist.name"
    ):
        playlistNameWithSuffix = playlistName + param.playlistSuffix
        if playlistNameWithSuffix not in [
                x[0] for x in spotifyData["playlists"]
        ]:
            playlistId = spotify.createPlaylist(
                spotifyData["user"], playlistNameWithSuffix)[0]["id"]
        else:
            playlistId = [
                x[1] for x in spotifyData["playlists"]
                if x[0] == playlistNameWithSuffix
            ][0]
        # track insert in the playlists
        trackList = db.select("""
            select track.uri
            from track
            inner join album on track.albumId = album.id
            inner join artist on artist.id = album.artistId
            inner join artistPlaylist ap on ap.artistId = artist.id
            inner join playlist on playlist.id = ap.playlistId
            where playlist.name = {} and track.alreadyAdded = 0""".format(
            db.formatSqlString(playlistName)))
        trackList = [x[0] for x in trackList]

        # pretty weird: pass a global var in the function def then the function is executed on a scope where the variable does not exists
        def updateCallback():
            for trackUri in trackList:
                db.update(
                    "update track set alreadyAdded = 1 where uri = {}".format(
                        db.formatSqlString(trackUri)))
            db.commit()

        returnPlaylistAdd = spotify.addTrackToPlaylistPerPaquet(
            playlistId, trackList, callback=updateCallback)
        print(returnPlaylistAdd)

    db.close()
    return redirect(url_for('init'))
