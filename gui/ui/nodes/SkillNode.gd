class_name SkillNode
extends GraphNode

const NODE_MIN_WIDTH := 400

var node_id: String = ""
var node_def: GraphNodeDef
var input_fields: Dictionary[String, LineEdit] = {}
var input_slot_indices: Dictionary[String, int] = {}
var output_slot_indices: Dictionary[String, int] = {}


func setup(p_node_id: String, p_node_def: GraphNodeDef) -> void:
	node_id = p_node_id
	node_def = p_node_def
	title = node_def.display_label()
	resizable = true
	build_node()
	custom_minimum_size.x = NODE_MIN_WIDTH
	set_highlight(false)
	pass


func build_node() -> void:
	pass


func add_input_port_row(port: PortDef, _allow_manual: bool = true) -> int:
	var slot_index := get_child_count()
	var row := create_connect_only_row(port.display_label(node_def.catalog_id()))
	add_child(row)
	input_slot_indices[port.id] = slot_index
	configure_slot(
		slot_index,
		true,
		port.port_type,
		WorkflowColors.port_color(port.port_type),
		false,
		0,
		WorkflowColors.port_slot_idle,
	)
	return slot_index


func add_output_port_row(port: PortDef) -> int:
	var slot_index := get_child_count()
	var row := Label.new()
	row.text = GuiLocale.text("ui.node.output_arrow", port.display_label(node_def.catalog_id()))
	row.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	add_child(row)

	output_slot_indices[port.id] = slot_index
	configure_slot(
		slot_index,
		false,
		0,
		WorkflowColors.port_slot_idle,
		true,
		port.port_type,
		WorkflowColors.port_color(port.port_type),
	)
	return slot_index


func create_connect_only_row(label_text: String) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var label := Label.new()
	label.text = label_text
	label.custom_minimum_size.x = 80
	row.add_child(label)

	var hint := Label.new()
	hint.text = GuiLocale.text("ui.node.connect_upstream")
	hint.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hint.modulate = WorkflowColors.hint
	row.add_child(hint)

	return row


func create_text_row(port_id: String, label_text: String, placeholder: String) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var label := Label.new()
	label.text = label_text
	label.custom_minimum_size.x = 80
	row.add_child(label)

	var field := LineEdit.new()
	field.custom_minimum_size.x = 260
	field.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	field.placeholder_text = placeholder
	row.add_child(field)
	input_fields[port_id] = field

	return row


func configure_slot(
	slot_index: int,
	left_enabled: bool,
	left_type: int,
	left_color: Color,
	right_enabled: bool,
	right_type: int,
	right_color: Color,
) -> void:
	set_slot(slot_index, left_enabled, left_type, left_color, right_enabled, right_type, right_color)
	pass


func get_manual_input(port_id: String) -> String:
	if not input_fields.has(port_id):
		return ""
	var field: LineEdit = input_fields[port_id]
	return field.text.strip_edges()


func apply_manual_inputs(manual_inputs: Dictionary[String, String]) -> void:
	for port_id in manual_inputs.keys():
		if not input_fields.has(port_id):
			continue
		var field: LineEdit = input_fields[port_id]
		field.text = str(manual_inputs[port_id])
	pass


func get_input_slot_index(port_id: String) -> int:
	return input_slot_indices.get(port_id, -1)


func get_output_slot_index(port_id: String = "") -> int:
	if port_id.is_empty():
		if output_slot_indices.is_empty():
			return -1
		return output_slot_indices.values()[0]
	return output_slot_indices.get(port_id, -1)


func get_input_port_at_slot(slot_index: int) -> PortDef:
	for port_id in input_slot_indices.keys():
		if input_slot_indices[port_id] == slot_index:
			return node_def.find_input(port_id)
	return null


func get_output_port_at_slot(slot_index: int) -> PortDef:
	for port_id in output_slot_indices.keys():
		if output_slot_indices[port_id] == slot_index:
			return node_def.find_output(port_id)
	return null


func get_input_port_at_port_index(port_index: int) -> PortDef:
	if port_index < 0 or port_index >= get_input_port_count():
		return null
	var slot_index := get_input_port_slot(port_index)
	return get_input_port_at_slot(slot_index)


func get_output_port_at_port_index(port_index: int) -> PortDef:
	if port_index < 0 or port_index >= get_output_port_count():
		return null
	var slot_index := get_output_port_slot(port_index)
	return get_output_port_at_slot(slot_index)


func is_output_port(port_index: int) -> bool:
	return get_output_port_at_port_index(port_index) != null


func is_input_port(port_index: int) -> bool:
	return get_input_port_at_port_index(port_index) != null


func get_effective_output_port_type(slot_index: int) -> int:
	var port := get_output_port_at_slot(slot_index)
	if port == null:
		return PortDef.TYPE_STRING
	return port.port_type


func get_effective_output_port_type_at_port(port_index: int) -> int:
	if port_index < 0 or port_index >= get_output_port_count():
		return PortDef.TYPE_STRING
	var slot_index := get_output_port_slot(port_index)
	return get_effective_output_port_type(slot_index)


func collect_extra_manual_inputs() -> Dictionary[String, String]:
	return {}


func set_highlight(running: bool) -> void:
	var panel := StyleBoxFlat.new()
	panel.bg_color = WorkflowColors.node_running_bg if running else WorkflowColors.node_bg
	panel.border_color = WorkflowColors.success if running else WorkflowColors.node_border
	panel.set_border_width_all(3 if running else 2)
	panel.set_corner_radius_all(6)
	panel.set_content_margin_all(6)
	add_theme_stylebox_override("panel", panel)
	add_theme_color_override(
		"title_color",
		WorkflowColors.success.lightened(0.35) if running else WorkflowColors.node_title,
	)
	pass
