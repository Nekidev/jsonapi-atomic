# JSON:API atomic operations

This is a tiny implementation of JSON:API that uses the Atomic operations extension. This example has a few bugs but it is able to demonstrate how it works in general.

## Resources

This example has a small database stored in global variables that stores illustrations, artists who made those illustrations, and users who can follow artists.

### `Artist`

Endpoints:
- `/artists`
- `/artists/:id`

Attributes:
- `name`: `str`

Relationships:
*None*

### `Illustration`

Endpoints:
- `/illustrations`
- `/illustrations/:id`

Attributes:
- `url`: `str`

Relationships:
- `artist`: `Artist`

### `User`

Endpoints:
- `/users`
- `/users/:id`

Attributes:
- `username`: `str`
- `email`: `str`

Relationships:
- `followed_artists`: `List[Artist]`


## Making operations

Operations can be POSTed to the `/operations` endpoint. All three operations (`add`, `update`, `remove`) are supported.

For example:
```json
{
    "atomic:operations": [
        {
            "op": "add",
            "data": {
                "type": "artist",
                "lid": "artist-1",
                "attributes": {
                    "name": "John Doe"
                }
            }
        },
        {
            "op": "add",
            "data": {
                "type": "user",
                "lid": "user-1",
                "data": {
                    "username": "JamesDoe",
                    "email": "jamesdoe@doemail.com"
                },
                "relationships": {
                    "followed_artists": {
                        "data": [
                            { "type": "artist", "lid": "artist-1" }
                        ]
                    }
                }
            }
        },
        {
            "op": "add",
            "data": {
                "type": "illustration",
                "lid": "illust-1",
                "data": {
                    "url": "https://example.com/illust.png"
                }
            }
        },
        {
            "op": "update",
            "ref": {
                "type": "illustration",
                "lid": "illust-1",
                "relationship": "artist"
            },
            "data": {
                "type": "artist",
                "lid": "artist-1"
            }
        }
    ]
}
```

> Note: `href` is the only thing that is not supported in this app. You can add it to the operation objects, but it will not have any effect. The target of the operation is decided depending on the resource type of the `ref`/`data` resource types.

## Deployment

To install the APP, run the following commands.

```bash
git clone https://github.com/Nekidev/jsonapi-atomic.git
cd jsonapi-atomic
# Here you can create a virtual environment if you want
pip install schema flask
py main.py
```

That should get the app running in `127.0.0.1:8000`. `/` (index) lists all the endpoints in a non-JSON:API format, so make a GET request to get started!
