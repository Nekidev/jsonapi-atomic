"""
This module contains the `ModelOperationSet`s.
"""

import typing

import schema

from models import Model, Illustration, Artist, User, type_to_model


def get_model_from_typing_type(_type):
    try:
        # assert models.User.__bases__ == (models.Model,)
        if _type.__bases__[0] == Model:
            return _type
    except AttributeError:
        # A models.Model subclass must have a __bases__ property
        pass

    # Check if it is a type of the `typing` module
    if isinstance(_type, typing._GenericAlias) or isinstance(
        _type, typing._SpecialGenericAlias
    ):
        # assert typing.List[str].__args__ == (str,)
        for _subtype in _type.__args__:
            model_type = get_model_from_typing_type(_subtype)
            try:
                # assert models.User.__bases__ == (models.Model,)
                if model_type.__bases__[0] == Model:
                    return model_type
            except AttributeError:
                pass


class OperationResponse:
    instance: Model | None
    lid: str | None

    def __init__(self, instance: Model | None, lid: str | None = None):
        self.instance = instance
        self.lid = lid


class ModelOperationSet:
    """
    Like a DRF-JA `ModelViewSet`, but instead of having `create`, `retrieve`
    methods it has `add`, `update` and `remove` methods to handle each of the
    possible operations.
    """

    model: Model

    def __init__(self, lid_list: typing.List[typing.Tuple[str, Model]] = []):
        self.lid_list = lid_list

    def get_object_by_lid(self, lid: str) -> Model:
        """
        Returns a model instance my it's lid.
        """

        for item in self.lid_list:
            if item[0] == lid:
                return item[1]

        raise ValueError("The provided `lid` does not point to any resource")

    def add(
        self, ref: dict | None = None, data: dict | typing.List[dict] | None = None
    ):
        """
        Handles operations with an op code of `"add"`. If `ref` is present then
        a relationship is being updated. Otherwise a resource is being created.
        """

        if ref is not None:
            # Validate that `ref` has all the needed properties
            schema.Schema(
                schema.And(
                    {
                        schema.Or("id", "lid"): str,
                        "type": self.model.Meta.resource_name,
                        "relationship": schema.And(
                            str, lambda rel: rel in self.model.Meta.relationship_fields
                        ),
                    },
                    lambda o: not ("id" in o.keys() and "lid" in o.keys()),
                )
            ).validate(ref)

            # Validate that the related resource is valid
            data_schema = schema.And(
                {
                    "type": get_model_from_typing_type(
                        self.model.__annotations__[ref["relationship"]]
                    ).Meta.resource_name,
                    schema.Or("id", "lid"): str,
                },
                lambda o: not ("id" in o.keys() and "lid" in o.keys()),
            )

            schema.Schema(
                [data_schema],
            ).validate(data)

            if "id" in ref:
                instance = self.model.get(pk=ref["id"])
            else:
                instance = self.get_object_by_lid(lid=ref["lid"])
                if not isinstance(instance, self.model):
                    raise Exception(
                        f"`lid` does not point to a resource of type `{self.model}`"
                    )

            for related_instance in [
                type_to_model[item["type"]].get(item["id"])
                if "id" in item
                else self.get_object_by_lid(lid=item["lid"])
                for item in data
            ]:
                getattr(instance, ref["relationship"]).append(related_instance)

            instance.save()

            return OperationResponse(instance)

        else:
            # Validate the data
            attrs_schema = {}
            rels_schema = {}

            # In a real Django project you'd use
            # `rest_framework.serializers.Field` to validate a model.
            for attr in self.model.Meta.editable_attrs:
                attrs_schema.update({attr: self.model.__annotations__[attr]})

            for rel in self.model.Meta.relationship_fields:
                data_schema = schema.And(
                    {
                        "type": get_model_from_typing_type(
                            self.model.__annotations__[rel]
                        ).Meta.resource_name,
                        schema.Or("id", "lid"): str,
                    },
                    lambda o: not ("id" in o.keys() and "lid" in o.keys()),
                )

                rels_schema.update(
                    {rel: {"data": schema.Or(data_schema, [data_schema], None)}}
                )

            schema.Schema(
                schema.And(
                    {
                        "type": self.model.Meta.resource_name,
                        schema.Optional("lid"): str,
                        schema.Optional("attributes"): schema.And(
                            attrs_schema, lambda attrs: len(attrs.keys()) >= 1
                        ),
                        schema.Optional("relationships"): schema.And(
                            rels_schema, lambda rels: len(rels.keys()) >= 1
                        ),
                    },
                    lambda o: not ("id" in o.keys() and "lid" in o.keys())
                    and ("attributes" in o.keys() or "relationships" in o.keys()),
                ),
            ).validate(data)

            all_instances = self.model.all()
            all_instances.sort(key=lambda o: o.id)
            new_pk = (
                str(int(all_instances[len(all_instances) - 1].id) + 1)
                if len(all_instances) > 0
                else "1"
            )

            instance = self.model(id=new_pk, **data.get("attributes", {}))

            if "relationships" in data:
                for rel in data["relationships"].keys():
                    rel_data = data["relationships"]["rel"]["data"]

                    if isinstance(rel_data, list):
                        related_instances = [
                            type_to_model[item["type"]].get(item["id"])
                            if "id" in item
                            else self.get_object_by_lid(lid=item["lid"])
                            for item in data
                        ]

                        setattr(instance, rel, related_instances)

                    else:
                        # Get the related resource
                        related_instance = (
                            type_to_model[
                                get_model_from_typing_type(
                                    getattr(self.model, rel)
                                ).Meta.resource_name
                            ].get(pk=data["id"])
                            if "id" in data
                            else self.get_object_by_lid(lid=data["lid"])
                        )

                        setattr(instance, rel, related_instance)

            instance.save()

            return OperationResponse(instance, lid=data.get("lid", None))

    def update(
        self, ref: dict | None = None, data: dict | typing.List[dict] | None = None
    ):
        """
        Handles operations with an op code of `"update"`. If `ref` is present a
        relationship is being updated (completely replaced), otherwise a
        resource's attributes are being edited.
        """

        if ref is not None:
            # Validate that `ref` has all the needed properties
            schema.Schema(
                schema.And(
                    {
                        schema.Or("id", "lid"): str,
                        "type": self.model.Meta.resource_name,
                        "relationship": schema.And(
                            str, lambda rel: rel in self.model.Meta.relationship_fields
                        ),
                    },
                    lambda o: not ("id" in o.keys() and "lid" in o.keys()),
                )
            ).validate(ref)

            # Validate that the related resource is valid
            data_schema = schema.And(
                {
                    "type": get_model_from_typing_type(
                        self.model.__annotations__[ref["relationship"]]
                    ).Meta.resource_name,
                    schema.Or("id", "lid"): str,
                },
                lambda o: not ("id" in o.keys() and "lid" in o.keys()),
            )

            schema.Schema(
                schema.Or(
                    data_schema,
                    [data_schema],
                    None,
                )
            ).validate(data)

            if "id" in ref:
                instance = self.model.get(pk=ref["id"])
            else:
                instance = self.get_object_by_lid(lid=ref["lid"])
                if not isinstance(instance, self.model):
                    raise Exception(
                        f"`lid` does not point to a resource of type `{self.model}`"
                    )

            if data is None:
                # Set the relationship to `None`
                setattr(instance, ref["relationship"], None)

            elif isinstance(data, list):
                related_instances = [
                    type_to_model[item["type"]].get(item["id"])
                    if "id" in item
                    else self.get_object_by_lid(lid=item["lid"])
                    for item in data
                ]

                setattr(instance, ref["relationship"], related_instances)

            else:
                # Get the related resource
                related_instance = (
                    type_to_model[
                        get_model_from_typing_type(
                            getattr(self.model, ref["relationship"])
                        ).Meta.resource_name
                    ].get(pk=data["id"])
                    if "id" in data
                    else self.get_object_by_lid(lid=data["lid"])
                )

                setattr(instance, ref["relationship"], related_instance)

            instance.save()

            return OperationResponse(instance)

        else:
            # Validate the data
            attrs_schema = {}
            rels_schema = {}

            data_schema = schema.And(
                {
                    "type": get_model_from_typing_type(
                        self.model.__annotations__[ref["relationship"]]
                    ).Meta.resource_name,
                    schema.Or("id", "lid"): str,
                },
                lambda o: not ("id" in o.keys() and "lid" in o.keys()),
            )

            # In a real Django project you'd use
            # `rest_framework.serializers.Field` to validate a model.
            for attr in self.model.Meta.editable_attrs:
                attrs_schema.update({attr: self.model.__annotations__[attr]})

            for rel in self.model.Meta.relationship_fields:
                rels_schema.update(
                    {rel: {"data": schema.Or(data_schema, [data_schema], None)}}
                )

            schema.Schema(
                schema.And(
                    {
                        "type": self.model.Meta.resource_name,
                        schema.Optional("lid"): str,
                        schema.Optional("attributes"): schema.And(
                            attrs_schema, lambda attrs: len(attrs.keys()) >= 1
                        ),
                        schema.Optional("relationships"): schema.And(
                            rels_schema, lambda rels: len(rels.keys()) >= 1
                        ),
                    },
                    lambda o: not ("id" in o.keys() and "lid" in o.keys())
                    and ("attributes" in o.keys() or "relationships" in o.keys()),
                ),
            ).validate(data)

            if "id" in ref:
                instance = self.model.get(pk=ref["id"])
            else:
                instance = self.get_object_by_lid(lid=ref["lid"])
                if not isinstance(instance, self.model):
                    raise Exception(
                        f"`lid` does not point to a resource of type `{self.model}`"
                    )

            for attr in data["attributes"].keys():
                setattr(instance, attr, data["attributes"][attr])

            if "relationships" in data:
                for rel in data["relationships"].keys():
                    rel_data = data["relationships"]["rel"]["data"]

                    if isinstance(rel_data, list):
                        related_instances = [
                            type_to_model[item["type"]].get(item["id"])
                            if "id" in item
                            else self.get_object_by_lid(lid=item["lid"])
                            for item in data
                        ]

                        setattr(instance, rel, related_instances)

                    else:
                        # Get the related resource
                        related_instance = (
                            type_to_model[
                                get_model_from_typing_type(
                                    getattr(self.model, rel)
                                ).Meta.resource_name
                            ].get(pk=data["id"])
                            if "id" in data
                            else self.get_object_by_lid(lid=data["lid"])
                        )

                        setattr(instance, rel, related_instance)

            instance.save()

            return OperationResponse(instance)

    def remove(
        self, ref: dict | None = None, data: dict | typing.List[dict] | None = None
    ):
        """
        Handles operations with an op code of "remove". If `ref` is present
        then there are items of a to-many relationship being removed from it,
        otherwise a resource is being deleted.
        """

        if ref is not None:
            # Validate that `ref` has all the needed properties
            schema.Schema(
                schema.And(
                    {
                        schema.Or("id", "lid"): str,
                        "type": self.model.Meta.resource_name,
                        "relationship": schema.And(
                            str, lambda rel: rel in self.model.Meta.relationship_fields
                        ),
                    },
                    lambda o: not ("id" in o.keys() and "lid" in o.keys()),
                )
            ).validate(ref)

            # Validate that the related resource is valid
            data_schema = schema.And(
                {
                    "type": get_model_from_typing_type(
                        self.model.__annotations__[ref["relationship"]]
                    ).Meta.resource_name,
                    schema.Or("id", "lid"): str,
                },
                lambda o: not ("id" in o.keys() and "lid" in o.keys()),
            )

            schema.Schema(
                [data_schema],
            ).validate(data)

            if "id" in ref:
                instance = self.model.get(pk=ref["id"])
            else:
                instance = self.get_object_by_lid(lid=ref["lid"])
                if not isinstance(instance, self.model):
                    raise Exception(
                        f"`lid` does not point to a resource of type `{self.model}`"
                    )

            id_list = [
                item["id"]
                if "id" in item
                else self.get_object_by_lid(lid=item["lid"]).id
                for item in data
            ]

            setattr(
                instance,
                ref["relationship"],
                [
                    item
                    for item in getattr(instance, ref["relationship"])
                    if item.id not in id_list
                ],
            )
            instance.save()

            return OperationResponse(instance)

        else:
            schema.Schema(
                schema.And(
                    {
                        "type": self.model.Meta.resource_name,
                        schema.Or("id", "lid"): str,
                    },
                ),
            ).validate(data)

            if "id" in ref:
                instance = self.model.get(pk=ref["id"])
            else:
                instance = self.get_object_by_lid(lid=ref["lid"])
                if not isinstance(instance, self.model):
                    raise Exception(
                        f"`lid` does not point to a resource of type `{self.model}`"
                    )
            instance.delete()

            return OperationResponse(instance=None)


class IllustrationOperationSet(ModelOperationSet):
    model = Illustration


class ArtistOperationSet(ModelOperationSet):
    model = Artist


class UserOperationSet(ModelOperationSet):
    model = User


type_to_operation_set = {
    "illustration": IllustrationOperationSet,
    "artist": ArtistOperationSet,
    "user": UserOperationSet,
}
