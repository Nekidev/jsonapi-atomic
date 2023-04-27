"""
This module contains "Models" that emulate Django models. The `to_json()`
method would be replaced by DRF serializers in a Django APP.
"""

import typing


class Model:
    id: str

    class Meta:
        resource_name: str
        relationship_fields: typing.List[str]
        reverse_relationships: typing.List[str]
        editable_attrs: typing.List[str]

    def save(self):
        raise NotImplementedError()

    def delete(self):
        raise NotImplementedError()

    def get(pk: str):
        raise NotImplementedError()

    def to_json(self):
        raise NotImplementedError()


class Artist(Model):
    name: str

    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name

    class Meta:
        resource_name = "artist"
        relationship_fields = []
        reverse_relationships = ["user.followed_artists", "illustration.artist"]
        editable_attrs = ["name"]

    def save(self):
        global artist_db
        artist_db[self.id] = self

        for user in User.all():
            if self.id in [artist.id for artist in user.followed_artists]:
                user.followed_artists[
                    [artist.id for artist in user.followed_artists].index(self.id)
                ] = self
                user.save()

        for illustration in Illustration.all():
            try:
                if illustration.artist.id == self.id:
                    illustration.artist = self
                    illustration.save()
            except AttributeError:
                pass

    def delete(self):
        global artist_db

        del artist_db[self.id]

        for user in User.all():
            if self.id in [artist.id for artist in user.followed_artists]:
                del user.followed_artists[
                    [artist.id for artist in user.followed_artists].index(self.id)
                ]
                user.save()

        for illustration in Illustration.all():
            try:
                if illustration.artist.id == self.id:
                    illustration.artist = None
                    illustration.save()
            except AttributeError:
                pass

    @staticmethod
    def get(pk: str):
        global artist_db
        return artist_db[pk]

    @staticmethod
    def all():
        global artist_db
        return [artist_db[id] for id in artist_db.keys()]

    def to_json(self) -> dict:
        return {
            "type": "artist",
            "id": self.id,
            "attributes": {"name": self.name},
            "links": {
                "self": {
                    "href": f"http://localhost:8000/artists/{self.id}",
                    "title": "Artist details",
                    "hreflang": "en-US",
                }
            },
        }


class Illustration(Model):
    url: str
    artist: Artist | None = None

    def __init__(self, id: str, url: str, artist: Artist | None):
        self.id = id
        self.url = url
        self.artist = artist

    class Meta:
        resource_name = "illustration"
        relationship_fields = ["artist"]
        reverse_relationships = []
        editable_attrs = ["url"]

    def save(self):
        global illustration_db
        illustration_db[self.id] = self

    def delete(self):
        global illustration_db
        del illustration_db[self.id]

    @staticmethod
    def get(pk: str):
        global illustration_db
        return illustration_db[pk]

    @staticmethod
    def all():
        global illustration_db
        return [illustration_db[id] for id in illustration_db.keys()]

    def to_json(self) -> dict:
        return {
            "type": "illustration",
            "id": self.id,
            "attributes": {"url": self.url},
            "relationships": {
                "artist": {
                    "data": {"type": "artist", "id": self.artist.id}
                    if self.artist
                    else None
                },
            },
            "links": {
                "self": {
                    "href": f"http://localhost:8000/illustrations/{self.id}",
                    "title": "Illustration details",
                    "hreflang": "en-US",
                }
            },
        }


class User(Model):
    username: str
    email: str
    followed_artists: typing.List[Artist]

    def __init__(
        self,
        id: str,
        username: str,
        email: str,
        followed_artists: typing.List[Artist] = [],
    ):
        self.id = id
        self.username = username
        self.email = email
        self.followed_artists = followed_artists

    class Meta:
        resource_name = "user"
        relationship_fields = ["followed_artists"]
        reverse_relationships = []
        editable_attrs = ["username", "email"]

    def save(self):
        global user_db
        user_db[self.id] = self

    def delete(self):
        global user_db
        del user_db[self.id]

    @staticmethod
    def get(pk: str):
        global user_db
        return user_db[pk]

    @staticmethod
    def all():
        global user_db
        return [user_db[id] for id in user_db.keys()]

    def to_json(self) -> dict:
        return {
            "type": "user",
            "id": self.id,
            "attributes": {
                "username": self.username,
                "email": self.email,
            },
            "relationships": {
                "followed_artists": {
                    "data": [
                        {"type": "artist", "id": artist.id}
                        for artist in self.followed_artists
                    ],
                    "meta": {"count": len(self.followed_artists)},
                },
            },
            "links": {
                "self": {
                    "href": f"http://localhost:8000/users/{self.id}",
                    "title": "User details",
                    "hreflang": "en-US",
                }
            },
        }


global illustration_db
illustration_db = {}

global artist_db
artist_db = {}

global user_db
user_db = {}


type_to_model = {"artist": Artist, "illustration": Illustration, "user": User}
