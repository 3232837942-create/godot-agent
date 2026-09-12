class_name InputSourceNode
extends PathInputSkillNode

## Shared by all input source nodes; port types and display labels come from config and locale.


func build_node() -> void:
	if node_def.outputs.is_empty():
		return
	var port := node_def.outputs[0]
	var row := create_path_row(port.id, port.display_label(node_def.catalog_id()), port.port_type)
	add_child(row)
	output_slot_indices[port.id] = 0
	configure_slot(
		0,
		false,
		0,
		WorkflowColors.port_slot_idle,
		true,
		port.port_type,
		WorkflowColors.port_color(port.port_type),
	)
	pass
