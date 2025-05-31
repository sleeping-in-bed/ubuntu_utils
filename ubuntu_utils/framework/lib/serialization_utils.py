import functools
import io
import json
import pickle
import re
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml


def _check_int_or_float(input_str: str) -> type:
    int_pattern = r"^[-+]?\d+$"
    float_pattern = r"^[-+]?\d+(\.\d+)?$"

    if re.match(int_pattern, input_str):
        return int
    elif re.match(float_pattern, input_str):
        return float
    else:
        return str


def _convert_json_dict_key_to_number(data: Any) -> Any:
    if isinstance(data, dict):
        # if data type is dict, convert it
        converted_dict = {}
        for key, value in data.items():
            if type(key) == str:
                trans_type = _check_int_or_float(key)
                key = trans_type(key)
            # process the values in dict, using recursion
            value = _convert_json_dict_key_to_number(value)
            converted_dict[key] = value
        return converted_dict
    elif isinstance(data, (list, tuple, set)):
        # if date type is list, tuple or set, process it recursively
        converted_list = []
        for item in data:
            converted_item = _convert_json_dict_key_to_number(item)
            converted_list.append(converted_item)
        return type(data)(converted_list)
    else:
        # if it's other type, don't process
        return data


def _get_empty_data_structure(
    data_type: type | None,
) -> dict | list | tuple | set | None:
    if data_type is None:
        return None
    types = (dict, list, tuple, set)
    if data_type in types:
        return data_type()
    else:
        raise TypeError(f"Unsupported data type {data_type}")


def _get_data(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(self, data: str | bytes = None, *args, **kwargs) -> Any:
        if not data:
            if not self.path:
                raise AssertionError(
                    "For loading data, please provide the data or file path."
                )
            try:
                data = Path(self.path).read_bytes()
            except FileNotFoundError:  # when file not found
                return _get_empty_data_structure(self.data_type)
        return func(self, data, *args, **kwargs)

    return wrapper


def _dump(self: Any, data: bytes | str) -> bytes | str:
    if self.path:
        if isinstance(data, str):
            Path(self.path).write_text(data, encoding=self.encoding)
        else:
            Path(self.path).write_bytes(data)
    return data


class Serializer:
    def __init__(
        self, path: str | Path = None, encoding: str = "utf-8", data_type: type = None
    ):
        self.path, self.encoding, self.data_type = path, encoding, data_type

    @_get_data
    def _load(self, data: str | bytes, lib: ModuleType, **kwargs) -> Any:
        if lib in [json, yaml] and isinstance(data, bytes):
            data = data.decode(self.encoding)
        if lib is json:
            try:
                deserialized_data = json.loads(data, **kwargs)
            except json.decoder.JSONDecodeError:  # when data is empty
                return _get_empty_data_structure(self.data_type)
        elif lib is yaml:
            deserialized_data = yaml.safe_load(data)
        elif lib is pickle:
            try:
                deserialized_data = pickle.loads(data, **kwargs)
            except EOFError:  # when data is empty
                return _get_empty_data_structure(self.data_type)
        else:
            raise AssertionError
        return deserialized_data

    def load_yaml(self, data: str = None, **kwargs) -> Any:
        return self._load(data, yaml, **kwargs)

    def load_json(
        self, data: str = None, trans_key_to_num: bool = False, **kwargs
    ) -> Any:
        json_data = self._load(data, json, **kwargs)
        if trans_key_to_num:
            return _convert_json_dict_key_to_number(json_data)
        return json_data

    def load_pickle(self, data: bytes = None, **kwargs) -> Any:
        return self._load(data, pickle, **kwargs)

    def dump_yaml(self, data: Any, allow_unicode: bool = True, **kwargs) -> str:
        string_io = io.StringIO()
        yaml.dump(data, string_io, allow_unicode=allow_unicode, **kwargs)
        data = string_io.getvalue()
        return _dump(self, data)

    def dump_json(
        self,
        data: Any,
        indent: int = 4,
        ensure_ascii: bool = False,
        minimum: bool = True,
        **kwargs,
    ) -> str:
        self_kwargs = {"ensure_ascii": ensure_ascii}
        if minimum:
            self_kwargs["separators"] = (",", ":")
        else:
            self_kwargs["indent"] = indent
        kwargs.update(self_kwargs)
        data = json.dumps(data, **kwargs)
        return _dump(self, data)

    def dump_pickle(self, data: Any, **kwargs) -> bytes:
        data = pickle.dumps(data, **kwargs)
        return _dump(self, data)
