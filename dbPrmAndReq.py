dbFilePath = "dbfile"

dbSchema = [
    """CREATE TABLE playlist (
        id integer NOT NULL, --  no autoincrement apparently it cost much with sqlite and its not really needd anyway
        name text NOT NULL
    );
    """,
    """CREATE TABLE artist (
        id text NOT NULL,
        name text NOT NULL,
        genre text,
        url text
    );""",
    """CREATE TABLE artistPlaylist (
        artistId text NOT NULL,
        playlistId integer NOT NULL
    );""",
    """CREATE TABLE album (
        id text NOT NULL,
        artistId text NOT NULL,
        name text NOT NULL,
        releaseDate integer
    );""",
    """CREATE TABLE track (
        id text NOT NULL,
        albumId text NOT NULL,
        name text NOT NULL,
        uri text NOT NULL,
        duration integer,
        discNumber integer NOT NULL,
        trackNumber integer NOT NULL,
        alreadyAdded integer DEFAULT 0
    );""",
    # pk
    "CREATE UNIQUE INDEX idx_playlist_name on playlist(name);",
    "CREATE UNIQUE INDEX idx_playlist_id on playlist(id);",
    "CREATE UNIQUE INDEX idx_artist_id on artist(id);",
    "CREATE UNIQUE INDEX idx_album_id on album(id);",
    # track's uri is the data used for adding track to a playlist. Unique constraint assure that no track will the added several times. well kinda, check bellow
    "CREATE UNIQUE INDEX idx_track_uri on track(uri);",
    # fk
    "CREATE INDEX idx_artistPlaylist_artistId on artistPlaylist(artistId);",
    "CREATE INDEX idx_artistPlaylist_playlistId on artistPlaylist(playlistId);",
    "CREATE INDEX idx_album_artistId on album(artistId);",
    "CREATE INDEX idx_track_albumId on track(albumId);"
]

dbIndexesAfterMassInsert = [
    {
        "name": "idx_artist_name",
        "def": "artist(name)"
    },
    {
        "name": "idx_album_name",
        "def": "album(name)"
    },
    {
        "name": "idx_track_name",
        "def": "track(name)"
    },
    {
        "name": "idx_track_alreadyAdded",
        "def": "track(alreadyAdded)"
    }
]

# I found out that spotify can return the same album twice, with basically the exact same content but not the same track uri
# so some cleanup is needed here
removeDuplicateSimple = """with dblRaw as (
    select artist.name as artistName, album.name as albumName, track.name as trackName, min(track.id) as mintrackId
    from track
    inner join album on track.albumId = album.id
    inner join artist on artist.id = album.artistId
    group by artist.name, album.name, track.name , track.discNumber, track.trackNumber
    having count(*) > 1
)
select track.id
from track
inner join album on track.albumId = album.id
inner join artist on artist.id = album.artistId
inner join dblRaw on dblRaw.artistName = artist.name and dblRaw.albumName = album.name and dblRaw.trackName = track.name and dblRaw.mintrackId != track.id
;"""

removeAlreadyTreated = """with trackAlreadyAddedRaw as (
    -- on récupère les tracks déjà ajoutés pour être sur qu'on va pas les réajouter (trackDblRaw peut ramner des lignes qui ont déjà été traitées)
    select distinct track.name as trackName, artist.name as artistName
    from track
    inner join album on track.albumId = album.id
    inner join artist on artist.id = album.artistId
    where track.alreadyAdded = 1
)
-- on prend le détail des morceau non ajoutés qui matchent avec des morceau déjà ajoutés pour les supprimer
select track.id
from track
inner join album on track.albumId = album.id
inner join artist on artist.id = album.artistId
inner join trackAlreadyAddedRaw on trackAlreadyAddedRaw.artistName = artist.name and trackAlreadyAddedRaw.trackName = track.name
where track.alreadyAdded = 0;
"""

# extracting duplicate track per artists considering the name.
# the oldest track is retrieved if if a duplicate is found
# if two duplicate track share the same release date, the min(id) is used to make the choice of which to keep
# this is by definition not great bu spotify return A LOT of duplicates
removeSimilarTracks = """with trackDblRaw as (
    select track.name as trackName, artist.name as artistName, min(album.releaseDate) as minDate
    from track
    inner join album on track.albumId = album.id
    inner join artist on artist.id = album.artistId
    where track.alreadyAdded = 0
    group by track.name, artist.name
    having count(*) > 1
), trackDbl as (
    select track.name as trackName, artist.name as artistName, min(track.id) as minId
    from track
    inner join album on track.albumId = album.id
    inner join artist on artist.id = album.artistId
    inner join trackDblRaw on trackDblRaw.trackName = track.name and trackDblRaw.artistName = artist.name and trackDblRaw.minDate = album.releaseDate
    where track.alreadyAdded = 0
    group by track.name, artist.name
)
select track.id
from track
inner join album on track.albumId = album.id
inner join artist on artist.id = album.artistId
inner join trackDbl on trackDbl.artistName = artist.name and trackDbl.trackName = track.name and trackDbl.minId != track.id
where track.alreadyAdded = 0;
"""

# last delete to avoid duplicates. this is the most expansive and it should be executed last as it make a cartesian product
# checks if some track have its name contained in another track. If so, also checks if the two tracks have about the same duration
# this request is agremented by the user choices to remove or not lives, remixes, instrumentals, etc
removeSimilarTracksBasedOnName = """with dbl as (
    select artist.id as artistId, album.id as albumId, track.id as trackId, track.duration, track.name as trackName
    , artist.name as artistName, album.name as albumName
    from track
    inner join album on track.albumId = album.id
    inner join artist on artist.id = album.artistId
), original as (
    select artist.id as artistId, album.id as albumId, track.id as trackId, track.duration, track.name as trackName
    , artist.name as artistName, album.name as albumName
    from track
    inner join album on track.albumId = album.id
    inner join artist on artist.id = album.artistId
)
select dbl.trackId
from dbl
inner join original on
    dbl.trackId != original.trackId and
    dbl.artistId = original.artistId and
    {}
    dbl.trackName like original.trackName || '%' and -- original est contenu dans dbl
    (
        (dbl.duration - (original.duration/25) <= original.duration and dbl.duration > original.duration) or
        (dbl.duration + (original.duration/25) >= original.duration and dbl.duration < original.duration) or
        (dbl.duration == original.duration)
    )
;
"""
