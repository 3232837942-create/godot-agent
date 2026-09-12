class_name WorkflowNodeData
extends RefCounted

var id: String = ""
var skill_id: String = ""
var position: Array[float] = [0.0, 0.0]
var manual_inputs: Dictionary[String, String] = {}


func position_vector() -> Vector2:
	if position.size() >= 2:
		return Vector2(position[0], position[1])
	return Vector2.ZERO


func set_position_vector(value: Vector2) -> void:
	position = [value.x, value.y]
