"""
Schema to validate an `atomic:operations` JSON body sent in a request.
"""

from schema import Schema, And, Or, Use, Optional

resource_schema = Schema(
    {"type": str, Optional(Or("id", "lid")): str, Optional("attributes"): dict}
)

schema = Schema(
    {
        "atomic:operations": [
            And(
                {
                    "op": Or("add", "update", "remove"),
                    Optional("ref"): Or(
                        {
                            "type": str,
                            Or("id", "lid"): str,
                            Optional("relationship"): str,
                        }
                    ),
                    Optional("href"): str,
                    Optional("data"): Or(
                        Optional(resource_schema), [Optional(resource_schema)], None
                    ),
                    Optional("meta"): dict,
                },
                lambda op: not ("ref" in op.keys() and "href" in op.keys())
                and ("ref" in op.keys() or "data" in op.keys()),
            )
        ]
    }
)
