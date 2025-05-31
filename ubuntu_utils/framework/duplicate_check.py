import ast
from collections.abc import Iterable
from pathlib import Path

from .settings import Settings


class DuplicateCheck:
    """
    Check if the same codes exist in one function.
    Equality is determined by determining whether each line is the same after removing the blanks on both sides.
    Only file 'commands_file' will be checked.
    Only lines containing 'root_process_instance_name.root_process_attr' will be checked.
    """

    class DuplicateCodeError(Exception):
        def __init__(self, function_name: str, duplicate_code_list: list[str]):
            self.function_name = function_name
            self.duplicate_code_list = duplicate_code_list

        def __str__(self):
            return f"Function {self.function_name} has same codes:\n{self.duplicate_code_list}"

    def __init__(
        self,
        root_process: type,
        commands_file: Path = Settings.src_dir / "commands.py",
        exclude_attrs: Iterable[str] = (),
        include_attrs: Iterable[str] = (),
    ):
        if include_attrs:
            self.root_process_attrs = list(include_attrs)
        else:
            self.root_process_attrs = [
                attr
                for attr in dir(root_process)
                if not attr.startswith("__") and attr not in exclude_attrs
            ]
        self.commands_file = commands_file

    def _extract_functions_and_code(self):
        source_code = self.commands_file.read_text()
        parsed_ast = ast.parse(source_code)
        functions_and_code = {}
        for node in ast.walk(parsed_ast):
            if isinstance(node, ast.FunctionDef):
                function_name = node.name
                function_code = ast.get_source_segment(source_code, node)
                functions_and_code[function_name] = function_code
        return functions_and_code

    def _filter_code(self, code_list: list[str]) -> list[str]:
        filtered_code = []
        feature_string_list = [
            f"{Settings.root_process_instance_name}.{attr}"
            for attr in self.root_process_attrs
        ]

        for code in code_list:
            for feature in feature_string_list:
                if feature in code:
                    filtered_code.append(code.strip())
                    break
        return filtered_code

    @staticmethod
    def _find_duplicates(lst: list) -> list:
        unique_items = set(lst)
        duplicates = []

        if len(unique_items) != len(lst):
            for item in unique_items:
                if lst.count(item) > 1:
                    duplicates.append(item)

        return duplicates

    def check(self):
        function_dict = self._extract_functions_and_code()
        for function_name, function_code in function_dict.items():
            code_list = function_code.split("\n")
            filtered_code_list = self._filter_code(code_list)
            duplicates = self._find_duplicates(filtered_code_list)
            if duplicates:
                raise self.DuplicateCodeError(function_name, duplicates)
