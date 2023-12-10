import os

import click


def count_occurrences(filepath, search_string):
	try:
		with open(filepath, "r", errors="ignore") as file:
			content = file.read()
			return content.count(search_string)
	except Exception as e:
		print(f"Error reading file {filepath}: {str(e)}")
		return 0


def search_files(directory, search_string, file_occurrences):
	for filename in os.listdir(directory):
		filepath = os.path.join(directory, filename)

		if os.path.isdir(filepath):
			# Recursively search in subdirectories
			file_occurrences = search_files(filepath, search_string, file_occurrences)
		elif os.path.isfile(filepath):
			# Count occurrences of the search string in the file
			occurrences = count_occurrences(filepath, search_string)

			# Update the maximum occurrences for the file
			file_occurrences[filename] = max(file_occurrences.get(filename, 0), occurrences)

	return file_occurrences


@click.command()
@click.option("--start-directory", default=".", help="The directory to start the search.")
@click.option("--search-string", prompt="Enter the search string", help="The string to search for in files.")
def main(start_directory, search_string):
	"""Search for count occurrences of a string, deduplicating by file name"""
	# Perform the search
	file_occurrences = search_files(start_directory, search_string, {})

	# Sort files by number of occurrences
	sorted_files = sorted(file_occurrences.items(), key=lambda x: x[1], reverse=True)

	# Print the sorted files and their occurrences
	print("Files sorted by number of occurrences:")
	for file_name, occurrences in sorted_files:
		if occurrences > 0:
			print(f"{file_name}: {occurrences}")

	# Print the count of files with 0 occurrences
	files_with_zero_occurrences = sum(1 for occurrences in file_occurrences.values() if occurrences == 0)
	print(f"Files with 0 occurrences: {files_with_zero_occurrences}")


if __name__ == "__main__":
	main()  # pylint: disable=no-value-for-param
