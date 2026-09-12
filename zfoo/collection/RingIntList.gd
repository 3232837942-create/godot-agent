class_name RingIntList
extends RefCounted

var capacity: int = 0
var buffer: PackedInt64Array = PackedInt64Array()
var head: int = 0
var count: int = 0

func _init(_capacity: int) -> void:
	assert(_capacity >= 1)
	capacity = _capacity
	buffer.resize(capacity)
	pass

func add(value: int) -> void:
	if count < capacity:
		buffer[(head + count) % capacity] = value
		count += 1
	else:
		buffer[head] = value
		head = (head + 1) % capacity
	pass

func remove_latest() -> void:
	if count == 0:
		return
	count -= 1
	pass

func remove_value(value: int) -> void:
	if count == 0:
		return
	var remove_idx := -1
	for i in count:
		if buffer[(head + i) % capacity] == value:
			remove_idx = i
			break
	if remove_idx == -1:
		return
	for i in range(remove_idx + 1, count):
		buffer[(head + i - 1) % capacity] = buffer[(head + i) % capacity]
	count -= 1
	pass

func clear() -> void:
	head = 0
	count = 0
	pass

func is_empty() -> bool:
	return count == 0

func is_full() -> bool:
	return count == capacity

func size() -> int:
	return count

func latest() -> int:
	if count == 0:
		return -1
	return buffer[(head + count - 1) % capacity]

func to_array() -> Array[int]:
	var result: Array[int] = []
	for i in count:
		result.append(buffer[(head + i) % capacity])
	return result
