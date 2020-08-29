# spotify-autoAddArtists

*tested on python 3.6*
Simply get all your followed artists, specify zero, one or several playlist per artist and create the playlists automatically
The app also allows to remove the live, instrumentals, demo tracks and remove the duplicates (it's based on track's name so that's not very reliable tho)

## Installation

- you obviously need a spotify account
- [register](https://developer.spotify.com/documentation/general/guides/app-settings/#register-your-app) the app on spotify (the name is not really important). Note the client id and secret for later. Add a redirection url on your app (for instance `http://localhost:8888/index`) and note that url for later. The redirection page should not be the root page (no `http://localhost:8888/` in the example)
- rename the `param.py.example` file to `param.py` and open it
- the file is used to parameterize the app behavior; some explanations for each variables
- - first get the client id, client secret and the url you used for the redirection url on the app registration (I'll use `http://localhost:8888/index` as example)
- - `localServerName` is the name of the server used on the url (it should be `localhost` anyway)
- - `localServerPort` is the port of the url (`8888` in the example)
- - `localServerPage` is the page of the url (`index` in the example)
- - `spotifyApiClientId` is the spotify id you retrieved earlier
- - `spotifyApiSecret` is the spotify client secret you retrieved earlier
- - `spotifyApiScopeLs` is the list of permissions you wish to give to the application. The default should be good enough, but if you need to change that here's the [spotify doc](https://developer.spotify.com/documentation/general/guides/authorization-guide/#list-of-scopes)
- - `countryCode` is the code on two characters of your country ([cf wikipedia](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2))
- - `playlistSuffix` is the string that will be added at the end of each playlist created with the app so the app you yourself can easily identify them
- you can (and probably should) create a [python virtual environnement](https://docs.python.org/3/library/venv.html) to install and run the app
- - `python -m venv yourVenvName # create the virtual env`
- - `cd yourVenvName`
- - `./Scripts/activate # activate the venv`
- install the dependencies of the app with `pip install -r requirements.txt`

## How to run

- don't forget to activate the venv if you decided to use one
- use `python run.py` to start the application
- the script will create a flask debug server accessible on the address and port you provided earlier (in the example `http://localhost:8888`). You just need to browse to the corresponding url (the url is logged on the terminal if needed)
- simply follow the instructions provided on the web pages. If you need you can take a look at the terminal to get more detaileds infos
- the programm can take quite a while depending on how many artist you follow and the choice you made regarding delete options
- once you returned to the first page, the app is done and you should see on your spotify account the new playlists :)

### To do

- build a real model tho
