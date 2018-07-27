"""
common functions for interacting with Rest objects to build swagger docs
"""
import copy, re

# most CRUD operations will have following possibly responses
crud_responses = {
    "200": {
        "description":"successfully created object",
        "content": {
            "application/json":{
                "schema": {
                    "$ref": "#/components/schemas/generic_write"
                    }
                },
            },
    },
    "400": {
        "description": "bad request",
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/bad_request",
                },
            }
        },
    },
    "401": { "description": "unauthenticated"},
    "403": { "description": "forbidden resource"},
    "404": { "description": "resource not found"},
}
# for now 400/401/403/404 are a little annoying, let's leave them out
crud_responses.pop("400", None)
crud_responses.pop("401", None)
crud_responses.pop("403", None)
crud_responses.pop("404", None)

generic_read = {
    "type": "object",
    "properties": {
        "count": {
            "type": "integer",
            "description": "number of objects returned"
        },
        "objects": {
            "type": "array",
            "description": "list of objects returned"
        },
    },
}
generic_post = copy.deepcopy(crud_responses)
generic_post["200"]["content"]["application/json"]["schema"]\
    ["$ref"] = "#/components/schemas/generic_post"
generic_post["200"]["description"] = "successful post operation"
generic_get = {"200": {"description":"successful operation"}}

def swagger_generic_path(cls, path, method, summary):
    # add simple route to swagger doc
    if not hasattr(cls, "_swagger"): setattr(cls, "_swagger", {})
    if path not in cls._swagger: cls._swagger[path] = {}
    op = method.lower()
    cls._swagger[path][op] = {
        "summary": summary,
        "tags": [cls._classname],
    }
    if op == "post": cls._swagger[path][op]["responses"] = generic_post
    else: cls._swagger[path][op]["responses"] = generic_get
    # if any attributes exists within path, add them as parameters
    path_params = []
    for match in re.finditer("/{(?P<a>[^}]+)}", path):
        if match.group("a") in cls._attributes:
            path_params.append(match.group("a"))
    cls._swagger[path][op]["parameters"] = build_swagger_parameters(cls,
        paths=path_params)

def swagger_create(cls, path):
    # add swagger doc to class object for create operation
    if not hasattr(cls, "_swagger"): setattr(cls, "_swagger", {})
    if path not in cls._swagger: cls._swagger[path] = {}
    schema_200 = "#/components/schemas/generic_write"
    if cls._access["expose_id"]: 
        schema_200 = "#/components/schemas/create_id"
    op = "post"
    cls._swagger[path][op] = {
        "summary":"create %s" % cls._classname,
        "tags": [cls._classname],
        "requestBody": {
            "required": len(cls._keys)>0,
            "content": {
                "application/json": {
                    "schema": build_swagger_schema(cls, "write")
                }
            }
        },
        "responses": copy.deepcopy(crud_responses)
    }
    cls._swagger[path][op]["responses"]["200"]["content"]\
        ["application/json"]["schema"]["$ref"] = schema_200

def swagger_read(cls, path, bulk=False):
    # add swagger doc to class object for read operation
    if not hasattr(cls, "_swagger"): setattr(cls, "_swagger", {})
    if path not in cls._swagger: cls._swagger[path] = {}
    op = "get"
    cls._swagger[path][op] = {
        "tags": [cls._classname],
        "responses": copy.deepcopy(crud_responses),
        }
    if bulk:
        cls._swagger[path][op]["summary"] = "bulk read %s" % cls._classname
        cls._swagger[path][op]["parameters"] = build_swagger_parameters(
            cls, full=True, query=True)
    else:
        cls._swagger[path][op]["summary"] = "read %s" % cls._classname
        cls._swagger[path][op]["parameters"] = build_swagger_parameters(
            cls, path=True)

    swagger_desc = "list of %s objects" % cls._classname
    gr = copy.deepcopy(generic_read)
    gr["properties"]["objects"]["items"]= build_swagger_schema(cls,"read")
    gr["properties"]["objects"]["description"] = swagger_desc
    cls._swagger[path]["get"]["responses"]["200"]["content"]\
        ["application/json"]["schema"] = gr

def swagger_update(cls, path, bulk=False):
    # add swagger doc to class object for update operation
    if not hasattr(cls, "_swagger"): setattr(cls, "_swagger", {})
    if path not in cls._swagger: cls._swagger[path] = {}

    op = "patch"
    cls._swagger[path][op] = {
        "tags": [cls._classname],
        "requestBody": {
            "required": len(cls._keys)>0,
            "content": {
                "application/json": {
                    "schema": build_swagger_schema(cls, "write")
                }
            },
        },
        "responses": copy.deepcopy(crud_responses)
    }
    if bulk:
        cls._swagger[path][op]["summary"] = "bulk update %s" % cls._classname
        cls._swagger[path][op]["parameters"] = build_swagger_parameters(
            cls, query=True)
    else:
        cls._swagger[path][op]["summary"] = "update %s" % cls._classname
        cls._swagger[path][op]["parameters"] = build_swagger_parameters(
            cls, path=True)

def swagger_delete(cls, path, bulk=False):
    # add swagger doc to class object for delete operation
    if not hasattr(cls, "_swagger"): setattr(cls, "_swagger", {})
    if path not in cls._swagger: cls._swagger[path] = {}

    op = "delete"
    cls._swagger[path][op] = {
        "tags": [cls._classname],
        "responses": copy.deepcopy(crud_responses)
    }
    if bulk:
        cls._swagger[path][op]["summary"] = "bulk delete %s" % cls._classname
        cls._swagger[path][op]["parameters"] = build_swagger_parameters(
            cls, query=True)
    else:
        cls._swagger[path][op]["summary"] = "delete %s" % cls._classname
        cls._swagger[path][op]["parameters"] = build_swagger_parameters(
            cls, path=True)


def build_swagger_attribute(attr):
    # for single attribute return schema
    parent = {
        "description": attr.get("description", "")
    }
    p = {}
    if attr["type"] is list: 
        parent["type"] = "array"
        parent["items"] = {}
        p = parent["items"]
        subtype = attr["subtype"]
    else:
        p = parent
        subtype = attr["type"]
    p["type"] = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        dict: "object",
        list: "array"
    }.get(subtype, "string")    

    # check for regex validator
    if subtype is str and attr["regex"] is not None:
        p["pattern"] = attr["regex"]

    # check for min/max validator
    if subtype is float or subtype is int:
        if attr["min"] is not None:
            p["minimum"] = attr["min"]
            if attr["max"] is None: p["exclusiveMinimum"] = True
        if attr["max"] is not None:
            p["maximum"] = attr["max"]
            if attr["min"] is None: p["exclusiveMaximum"] = True
        if subtype is float: p["format"] = "double"

    # force user to use a particular value from list
    if attr["values"] is not None and len(attr["values"])>0:
        p["enum"] = attr["values"]

    # add object sub-data
    if subtype is dict and attr["meta"] is not None and len(attr["meta"])>0:
        p["properties"] = {}
        for a in sorted(attr["meta"]): 
            p["properties"][a] = build_swagger_attribute(attr["meta"][a])
    return parent

def build_swagger_schema(cls, op="read"):
    # receive Rest cls instance and build swagger properties used for body
    # in create/update/delete along with response for read

    # sort attributes by name with keys (required) first
    a_keys , a_non_keys = [], []
    for a in sorted(cls._attributes):
        if cls._attributes[a]["key"]: a_keys.append(a)
        else: a_non_keys.append(a)

    schema = {
        "type": "object",
        "required": a_keys,
        "properties": {}
    }
    for a in a_keys+a_non_keys:
        attr = cls._attributes[a]
        if op == "read" and not attr["read"] or \
            op == "write" and not attr["write"]: continue
        schema["properties"][a] = build_swagger_attribute(attr)
        schema["properties"][a]["example"] = cls.get_attribute_default(a)
    if cls._access["expose_id"] and op!="write":
        schema["properties"]["_id"] = {
            "description": "%s unique id" % cls._classname,
            "type": "string"
        }
    return schema

def build_swagger_parameters(cls, path=False,query=False,full=False,paths=[]):
    """ receive Rest cls instance and build swagger parameters used within path
        for key lookup along with possible query parameters.
            path(bool)  create path parameter for all keys
            query(bool) create query parameters (filter only)
            full(bool)  add all possible query parameters if query also true
            paths(list) manual list of path attributes names to create
    """
    parameters = []
    if path or len(paths)>0:
        if len(paths) == 0: paths = cls._keys
        for a in paths:
            attr = cls._attributes[a]
            s = {
                str: "string",
                int: "integer",
                float: "number",
                bool: "boolean"
            }.get(attr["type"], "string")
            parameters.append({
                "in": "path",
                "name": a,
                "required": True,
                "description": attr.get("description", ""),
                "schema": build_swagger_attribute(attr)
            })
        if cls._access["expose_id"]: 
            parameters.append({
                "in": "path",
                "name": "_id",
                "required": True,
                "description": "%s unique id" % cls._classname,
                "schema": {
                    "type": "string"
                },
            })

    if query:
        # for read there are multiples query parameters available. For update
        # and delete (write) only show 'filter' option
        parameters.append({
            "$ref": "#/components/parameters/filter"
        })
        if full:
            parameters+= [
                {"$ref": "#/components/parameters/sort"},
                {"$ref": "#/components/parameters/page"},
                {"$ref": "#/components/parameters/page-size"},
                {"$ref": "#/components/parameters/count"},
                {"$ref": "#/components/parameters/include"},
            ]

    return parameters


