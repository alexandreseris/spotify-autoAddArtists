import urllib.parse
import datetime
import json

from server import utils


class SpotifyApi:
    # https://developer.spotify.com/documentation/web-api/reference/playlists/add-tracks-to-playlist/
    spotifyMaxInsertPlaylist = 100

    def __init__(
        self,
        clientId,
        clientSecret,
        scopeLs,
        localServerName,
        localServerPort,
        localServerPage,
    ):

        self.clientId = clientId
        self.clientSecret = clientSecret
        self.scopeLs = scopeLs
        self.localServerName = localServerName
        self.localServerPort = localServerPort
        self.localServerPage = localServerPage

        self.redirectUri = "http://" + localServerName + \
            ":" + str(localServerPort) + "/" + localServerPage

        self.stateStr = utils.generateRandomString(length=20)

        self.token = ""
        self.refreshToken = ""
        self.tokenExpire = None
        self.userid = None

    def userConnectionUrl(self):
        # https://developer.spotify.com/documentation/general/guides/authorization-guide/#authorization-code-flow
        # part 1
        print("user connection")
        self.urlRedirectBuild = ("http://" + self.localServerName + ":" +
                                 str(self.localServerPort) + "/" +
                                 self.localServerPage)
        scopeLs = " ".join(self.scopeLs)
        url = "https://accounts.spotify.com/authorize"
        params = {
            "client_id": self.clientId,
            "response_type": "code",
            "redirect_uri": self.redirectUri,
            "state": self.stateStr,
            "scope": scopeLs,
        }
        paramsEncoded = urllib.parse.urlencode(params)
        urlBuild = url + "?" + paramsEncoded
        print(urlBuild)
        return urlBuild

    def registerToken(self, tokenRequestResponse):
        if "refresh_token" in tokenRequestResponse.keys():
            self.refreshToken = tokenRequestResponse["refresh_token"]
        self.token = tokenRequestResponse["access_token"]
        now = datetime.datetime.now()
        self.tokenExpire = now + \
            datetime.timedelta(seconds=tokenRequestResponse["expires_in"] - 2)

    def requestRefreshAndAccessToken(self, spotifyCode, spotifyState):
        # https://developer.spotify.com/documentation/general/guides/authorization-guide/#authorization-code-flow
        # part 2
        print("getting acces and refresh token")
        if self.stateStr != spotifyState:
            raise ValueError(
                "state provided earlier does not match the state string in the redirect url:\n" + \
                "state provided earlier: " + self.stateStr +
                "\staet retrieved in the url: " + spotifyState)
        headers = {
            "Content-Type":
            "application/x-www-form-urlencoded",
            "Authorization":
            "Basic " + utils.b64(self.clientId + ":" + self.clientSecret),
        }
        body = {
            "grant_type": "authorization_code",
            "code": spotifyCode,
            "redirect_uri": self.redirectUri,
        }
        req = utils.request(
            "https://accounts.spotify.com/api/token",
            method="post",
            headers=headers,
            body=body,
            verbose=True,
        )
        self.registerToken(req.json())

    def requestRefreshedAcessToken(self):
        # https://developer.spotify.com/documentation/general/guides/authorization-guide/#authorization-code-flow
        # part 4
        print("getting a new token")
        headers = {
            "Content-Type":
            "application/x-www-form-urlencoded",
            "Authorization":
            "Basic " + utils.b64(self.clientId + ":" + self.clientSecret),
        }
        body = {
            "grant_type": "refresh_token",
            "refresh_token": self.refreshToken
        }
        req = utils.request(
            "https://accounts.spotify.com/api/token",
            method="post",
            headers=headers,
            body=body,
        )
        self.registerToken(req.json())

    def apiCall(
            self,
            url,
            method="get",
            headers={},
            params=None,
            body=None,
            printMessage="",
            nextUrlProp="next",
            nextUrlCheck=lambda nextprop, apireturn: apireturn.get(nextprop),
            numberOfCall=1,
            secondsToWaitAfterReq=0,
            noResponse=False,
            verbose=False):
        if self.tokenExpire < datetime.datetime.now():
            self.requestRefreshedAcessToken()
        if printMessage != "":
            print(printMessage + " request n°" + str(numberOfCall))
        headersDefaultVal = {
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json",
        }
        if method == "get":
            headersDefaultVal["Accept"] = "application/json"
        headersDefaultVal.update(headers)
        headers = headersDefaultVal
        req = utils.request(url,
                            method=method,
                            headers=headers,
                            params=params,
                            body=body,
                            numberOfCall=numberOfCall,
                            secondsToWaitAfterReq=secondsToWaitAfterReq,
                            verbose=verbose)
        if not noResponse:
            apiRes = [req.json()]
            nextUrl = nextUrlCheck(nextUrlProp, apiRes[0])
            if nextUrl is not None:
                # recurse call to retrieve next pages
                apiRes += self.apiCall(
                    nextUrl,
                    method=method,
                    headers=headers,
                    # not passing params original value cause nextUrl got already params encoded
                    params=None,
                    body=body,
                    printMessage=printMessage,
                    nextUrlProp=nextUrlProp,
                    nextUrlCheck=nextUrlCheck,
                    numberOfCall=numberOfCall + 1,
                    secondsToWaitAfterReq=secondsToWaitAfterReq,
                    verbose=verbose)
            return apiRes

    def flattenReqRes(
            self,
            reqRes,
            itemProp="items",
            itemsKeyGetter=lambda itemprop, apireturn: apireturn[itemprop]):
        return [
            item for subList in reqRes
            for item in itemsKeyGetter(itemProp, subList)
        ]

    def getCurrentUserId(self):
        # https://developer.spotify.com/documentation/web-api/reference/users-profile/get-current-users-profile/
        userReq = self.apiCall("https://api.spotify.com/v1/me",
                               printMessage="getting user id")
        return userReq[0]["id"]

    def getCurrentUserPlaylists(self, currentUserId):
        # https://developer.spotify.com/documentation/web-api/reference/playlists/get-a-list-of-current-users-playlists/
        return [(playlistElem["name"], playlistElem["id"])
                for playlistElem in self.flattenReqRes(
                    self.apiCall("https://api.spotify.com/v1/me/playlists",
                                 params={"limit": 50},
                                 printMessage="getting user's playlists"))
                if playlistElem["owner"]["id"] == currentUserId]

    def getCurrentUserArtists(self, silent=True):
        # https://developer.spotify.com/documentation/web-api/reference/follow/get-followed/
        artistGetter = lambda prop, apireturn: apireturn["artists"][prop]
        if silent:
            printMessage = ""
        else:
            printMessage = "getting user's followed artits"
        return self.flattenReqRes(
            self.apiCall(
                "https://api.spotify.com/v1/me/following",
                params={
                    "type": "artist",
                    "limit": 50
                },
                nextUrlCheck=artistGetter,
                printMessage=printMessage,
            ),
            itemsKeyGetter=artistGetter,
        )

    def getArtistAlbum(self,
                       artistId,
                       country=None,
                       includeLs=["album", "single"],
                       silent=True):
        # https://developer.spotify.com/documentation/web-api/reference/artists/get-artists-albums/
        params = {
            "include_groups": ",".join(includeLs),
            "limit": 50,
        }
        if silent:
            printMessage = ""
        else:
            printMessage = "getting artist album"
        if country is not None:
            params["country"] = country
        return self.flattenReqRes(
            self.apiCall(
                "https://api.spotify.com/v1/artists/{}/albums".format(
                    artistId),
                params=params,
                printMessage=printMessage,
            ))

    def getAlbumTrack(self, albumId, country=None, silent=True):
        # https://developer.spotify.com/documentation/web-api/reference/albums/get-albums-tracks/
        params = {"limit": 50}
        if silent:
            printMessage = ""
        else:
            printMessage = "getting album track"
        if country is not None:
            params["market"] = country
        return self.flattenReqRes(
            self.apiCall(
                "https://api.spotify.com/v1/albums/{}/tracks".format(albumId),
                params=params,
                printMessage=printMessage))

    def createPlaylist(self,
                       userId,
                       name,
                       isPublic=True,
                       isCollaborative=False,
                       description=""):
        # https://developer.spotify.com/documentation/web-api/reference/playlists/create-playlist/
        if description == "" or description is None:
            description = name
        return self.apiCall(
            "https://api.spotify.com/v1/users/{}/playlists".format(userId),
            method="post",
            body=json.dumps({
                "name": name,
                "public": isPublic,
                "collaborative": isCollaborative
            }),
            printMessage="creating playlist " + name)

    def deletePlaylist(self, playlistId):
        # https://developer.spotify.com/documentation/web-api/reference/playlists/create-playlist/
        self.apiCall(
            "https://api.spotify.com/v1/playlists/{}/followers".format(
                playlistId),
            method="delete",
            noResponse=True,
            printMessage="deleting playlist " + playlistId)

    def addTrackToPlaylist(self, playlistId, trackUriList):
        # https://developer.spotify.com/documentation/web-api/reference/playlists/add-tracks-to-playlist/
        returnAddTracks = self.apiCall(
            "https://api.spotify.com/v1/playlists/{}/tracks".format(
                playlistId),
            verbose=False,
            method="post",
            body=json.dumps({"uris": trackUriList}))
        return returnAddTracks[0]

    def addTrackToPlaylistPerPaquet(self,
                                    playlistId,
                                    trackUriList,
                                    callback=None):
        returnLs = []
        for paquet in utils.loopPerStep(trackUriList,
                                        self.spotifyMaxInsertPlaylist):
            paquet = list(paquet)
            returnLs.append(self.addTrackToPlaylist(playlistId, paquet))
            if callback is not None:
                callback()
        return returnLs
