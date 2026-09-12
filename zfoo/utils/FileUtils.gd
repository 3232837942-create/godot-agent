class_name FileUtils
extends Object

# Bytes
const ONE_BYTE: int = 1
const BYTES_PER_KB: int = 1024
const BYTES_PER_MB: int = BYTES_PER_KB * 1024
const BYTES_PER_GB: int = BYTES_PER_MB * 1024

# Bits
const BITS_PER_BYTE: int = 8
const BITS_PER_KB: int = BYTES_PER_KB * 8
const BITS_PER_MB: int = BYTES_PER_MB * 8
const BITS_PER_GB: int = BYTES_PER_GB * 8

# Line endings (text files)
const NEWLINE_LF: String = "\n"
const NEWLINE_CR: String = "\r"
const NEWLINE_CRLF: String = "\r\n"

static func normalize_line_endings_to_lf(s: String) -> String:
	return s.replace(NEWLINE_CRLF, NEWLINE_LF).replace(NEWLINE_CR, NEWLINE_LF)


## Returns the absolute path to the folder containing project.godot.
static func get_project_root_path() -> String:
	var dir := ProjectSettings.globalize_path("res://")
	for _i in range(8):
		if FileAccess.file_exists(dir.path_join("project.godot")):
			return dir
		var parent := dir.get_base_dir()
		if parent == dir:
			break
		dir = parent
	return ProjectSettings.globalize_path("res://")

# Append content to the file.
static func write_string_to_file(filePath: String, content: String) -> void:
	var file := FileAccess.open(filePath, FileAccess.WRITE)
	# bread and butter
	file.store_string(content)
	file = null
	pass
	

static func read_file_to_string(filePath: String) -> String:
	# make sure our file exists on users system
	if !FileAccess.file_exists(filePath):
		return StringUtils.EMPTY
	
	# allow reading only for file
	var file := FileAccess.open(filePath, FileAccess.READ)
	
	var content := file.get_as_text()
	file = null
	return content

static func read_file_to_byte_array(filePath: String) -> PackedByteArray:
	# make sure our file exists on users system
	if !FileAccess.file_exists(filePath):
		return PackedByteArray()
	
	# allow reading only for file
	var file := FileAccess.open(filePath, FileAccess.READ)
	
	var buffer := file.get_buffer(file.get_length())
	file = null
	return buffer

static func delete_file(filePath: String) -> void:
	if !FileAccess.file_exists(filePath):
		return
	DirAccess.remove_absolute(filePath)
	pass

# Returns absolute paths of all files in the given folder.
# Set recursive to true to include files in subfolders.
static func get_all_files_in_folder(folderPath: String, recursive: bool = false) -> Array[String]:
	var files: Array[String] = []
	var dir := DirAccess.open(folderPath)
	if dir == null:
		return files
	
	for file_name in dir.get_files():
		files.append(folderPath.path_join(file_name))
	
	if recursive:
		for dir_name in dir.get_directories():
			files.append_array(get_all_files_in_folder(folderPath.path_join(dir_name), true))
	
	return files


# Returns absolute paths of files in the given folder whose names match a glob pattern.
# Supports * and ? wildcards (Godot String.match). Set recursive to true to search subfolders.
static func get_files_in_folder_matching(folderPath: String, globPattern: String, recursive: bool = false) -> Array[String]:
	var pattern := globPattern.strip_edges()
	if pattern.is_empty():
		pattern = "*.*"

	var all_files := get_all_files_in_folder(folderPath, recursive)
	if pattern == "*" or pattern == "*.*":
		all_files.sort()
		return all_files

	var matched: Array[String] = []
	for file_path in all_files:
		if file_path.get_file().match(pattern):
			matched.append(file_path)
	matched.sort()
	return matched


# Returns the absolute path of the newest file in folderPath (non-recursive).
static func get_newest_file_in_folder(folder_path: String) -> String:
	if not DirAccess.dir_exists_absolute(folder_path):
		return ""

	var newest_path := ""
	var newest_time := -1
	for file_path in get_all_files_in_folder(folder_path, false):
		var modified := FileAccess.get_modified_time(file_path)
		if modified > newest_time:
			newest_time = modified
			newest_path = file_path
	return newest_path


# Convert a string into a valid filename using underscores as separators.
# aa bb cc dd -> aa_bb_cc
static func sanitize_filename(name: String) -> String:
	var regex := RegEx.new()

	# Replace all non-alphanumeric characters with '_'
	regex.compile("[^a-zA-Z0-9_-]")

	var result := regex.sub(name, "_", true)

	regex.compile("_+")
	result = regex.sub(result, "_", true)

	result = result.strip_edges()
	result = result.trim_prefix("_")
	result = result.trim_suffix("_")

	if StringUtils.is_blank(result):
		result = "unnamed"

	return result