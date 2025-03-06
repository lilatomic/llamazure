"""Inspector to help explore Azure's OpenAPI documents"""

import json
import os
from pathlib import Path
from typing import Any, Callable, Generator, Tuple


def query_files(root_dir: str, callable_func: Callable[[dict], Generator[Any, None, None]]) -> Generator[Tuple[str, Any], None, None]:
	"""
	Walk through a directory tree, open every `.json` file, deserialize it,
	check if it has the key "swagger" set to "2.0", and yield a tuple of the file path
	and the result of invoking a generator function on the document.

	Parameters:
	root_dir (str): The root directory to start walking from.
	callable_func (Callable[[dict], Generator[Any, None, None]]): The generator function to be called on each JSON document that meets the criteria.

	Yields:
	Tuple[str, Any]: A tuple of the file path and the result from the generator function.
	"""
	bad_files = {"tsconfig.json", "devcontainer.json", "settings.json"}

	for dirpath, dirnames, filenames in os.walk(root_dir):
		if "examples" in dirpath:
			continue
		for filename in filenames:
			if filename.endswith(".json") and filename not in bad_files:
				file_path = os.path.join(dirpath, filename)
				try:
					try:
						with open(file_path, "r", encoding="utf-8") as file:
							yield from process_content(callable_func, file, file_path)
					except UnicodeDecodeError:
						with open(file_path, "r", encoding="latin-1") as file:
							yield from process_content(callable_func, file, file_path)
				except Exception:
					print(f"error processing {file_path}")
					raise


def process_content(callable_func, file, file_path):
	try:
		document = json.load(file)
		if document.get("swagger") == "2.0":
			try:
				for result in callable_func(document):
					yield (file_path, result)
			except (TypeError, AttributeError) as e:
				raise RuntimeError(f"error processing {file_path=}") from e
	except (json.JSONDecodeError, IOError) as e:
		raise RuntimeError(f"Error processing file {file_path}") from e


def find_ref_responses(openapi: dict) -> Generator[Path, None, None]:
	for p_name, p in openapi["paths"].items():
		for method, op in p.items():
			if method == "parameters":
				continue
			for code, response in op["responses"].items():
				if "$ref" in response:
					yield Path(op["operationId"], code)


def find_inline_responses(openapi: dict) -> Generator[Path, None, None]:
	for p_name, p in openapi["paths"].items():
		for method, op in p.items():
			if method == "parameters":
				continue
			for code, response in op["responses"].items():
				if "schema" in response:
					schema = response["schema"]
					if "$ref" not in schema:
						if len(schema) > 1:  # if there's just a key, it's probably just `"type": "object"`
							yield Path(op["operationId"], code)


if __name__ == "__main__":
	for v in query_files("/home/lilatomic/vnd/azrest/specification", find_ref_responses):
		print(v)
