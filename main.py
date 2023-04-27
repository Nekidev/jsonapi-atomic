"""
Main APP
"""

import json
import typing

from flask import Flask, request, jsonify

from jsonapi_schema import schema
from operations import type_to_operation_set
from models import Illustration, Artist, User

app = Flask(__name__)


def get_op_resource_type(op: dict):
    if op.get("ref", None) is not None:
        return op["ref"]["type"]
    else:
        return op["data"]["type"]


@app.route("/")
def endpoints():
    return jsonify(
        {
            "endpoints": [
                "/                  - GET  - Lists all endpoints in this app"
                "/operations        - POST - Make atomic operations here",
                "/artists           - GET  - Lists all artists in the DB",
                "/artists/:id       - GET  - Get an artist's details by it's ID",
                "/illustrations     - GET  - Lists all illustrations in the DB",
                "/illustrations/:id - GET  - Get an illustration's details by it's ID",
                "/users             - GET  - Lists all illustrations in the DB",
                "/users/:id         - GET  - Get an user's details by it's ID",
            ]
        }
    )


@app.route("/operations", methods=["POST"])
def operations():
    schema.validate(request.json)

    lid_list = []
    responses = []
    for op in request.json["atomic:operations"]:
        response = getattr(
            type_to_operation_set[get_op_resource_type(op)](lid_list=lid_list), op["op"]
        )(
            ref=op.get("ref", None),
            data=op.get("data", None),
        )
        if response.lid:
            lid_list.append((response.lid, response.instance))
        responses.append(response)

    return jsonify(
        {
            "jsonapi": {
                "version": "1.1",
                "ext": ["https://jsonapi.org/ext/atomic"],
            },
            "atomic:results": [
                response.instance.to_json()
                for instance in responses
                if response.instance is not None
            ],
        }
    )


@app.route("/artists")
def artists():
    return jsonify(
        {
            "jsonapi": {
                "version": "1.1",
                "ext": ["https://jsonapi.org/ext/atomic"],
            },
            "data": [artist.to_json() for artist in Artist.all()],
        }
    )


@app.route("/artists/<id>")
def artist_detail(id):
    return jsonify(
        {
            "jsonapi": {
                "version": "1.1",
                "ext": ["https://jsonapi.org/ext/atomic"],
            },
            "data": Artist.get(pk=id).to_json(),
        }
    )


@app.route("/illustrations")
def illustrations():
    return jsonify(
        {
            "jsonapi": {
                "version": "1.1",
                "ext": ["https://jsonapi.org/ext/atomic"],
            },
            "data": [illustration.to_json() for illustration in Illustration.all()],
        }
    )


@app.route("/illustrations/<id>")
def illustration_detail(id):
    return jsonify(
        {
            "jsonapi": {
                "version": "1.1",
                "ext": ["https://jsonapi.org/ext/atomic"],
            },
            "data": Illustration.get(pk=id).to_json(),
        }
    )


@app.route("/users")
def users():
    return jsonify(
        {
            "jsonapi": {
                "version": "1.1",
                "ext": ["https://jsonapi.org/ext/atomic"],
            },
            "data": [user.to_json() for user in User.all()],
        }
    )


@app.route("/users/<id>")
def user_detail(id):
    return jsonify(
        {
            "jsonapi": {
                "version": "1.1",
                "ext": ["https://jsonapi.org/ext/atomic"],
            },
            "data": User.get(pk=id).to_json(),
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
