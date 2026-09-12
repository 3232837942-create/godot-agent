class_name StringBuilder
extends RefCounted

## Mutable string buffer. Collects fragments in a PackedStringArray and joins once in build_string().

var parts: PackedStringArray = PackedStringArray()


## Appends text. Returns self for chaining.
func append(text: String) -> StringBuilder:
	parts.append(text)
	return self


## Appends text only when not empty. Returns self for chaining.
func append_if_not_empty(text: String) -> StringBuilder:
	if StringUtils.is_not_empty(text):
		parts.append(text)
	return self


## Appends text followed by a newline. Returns self for chaining.
func append_line(text: String = "") -> StringBuilder:
	parts.append(text + StringUtils.LS)
	return self


## Clears all buffered fragments.
func clear() -> void:
	parts.clear()
	pass


## Returns true when no fragments have been appended.
func is_empty() -> bool:
	return parts.is_empty()


## Returns the number of buffered fragments.
func size() -> int:
	return parts.size()


## Returns the total character count across all fragments.
func length() -> int:
	var total := 0
	for part: String in parts:
		total += part.length()
	return total


## Joins buffered fragments into one string.
func build_string() -> String:
	return "".join(parts)


## Joins buffered fragments with a separator.
func build_joined(separator: String) -> String:
	return separator.join(parts)
