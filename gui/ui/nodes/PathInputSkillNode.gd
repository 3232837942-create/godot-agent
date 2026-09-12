class_name PathInputSkillNode
extends SkillNode

var browse_dialog: FileDialog


func setup(p_node_id: String, p_node_def: GraphNodeDef) -> void:
	super.setup(p_node_id, p_node_def)

	browse_dialog = FileDialog.new()
	browse_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
	browse_dialog.access = FileDialog.ACCESS_FILESYSTEM
	browse_dialog.size = Vector2i(900, 600)
	add_child(browse_dialog)
	browse_dialog.file_selected.connect(on_browse_selected)
	browse_dialog.dir_selected.connect(on_browse_selected)
	pass


func build_node() -> void:
	for port in node_def.inputs:
		add_input_port_row(port)
	for port in node_def.outputs:
		add_output_port_row(port)
	pass


func add_input_port_row(port: PortDef, allow_manual: bool = true) -> int:
	var slot_index := get_child_count()
	if allow_manual:
		var row := create_path_row(port.id, port.display_label(node_def.catalog_id()), port.port_type)
		add_child(row)
	else:
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


func create_path_row(port_id: String, label_text: String, port_type: int) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var label := Label.new()
	label.text = label_text
	label.custom_minimum_size.x = 80
	row.add_child(label)

	var field := LineEdit.new()
	field.custom_minimum_size.x = 260
	field.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	field.placeholder_text = GuiLocale.text("ui.node.path_placeholder", GuiLocale.port_type_label(PortDef.type_to_string(port_type)))
	row.add_child(field)
	input_fields[port_id] = field

	var browse := Button.new()
	browse.text = "…"
	browse.custom_minimum_size.x = 28
	browse.pressed.connect(func() -> void: open_browse(port_id, port_type))
	row.add_child(browse)

	return row


func open_browse(port_id: String, port_type: int) -> void:
	browse_dialog.set_meta("port_id", port_id)
	match port_type:
		PortDef.TYPE_FOLDER:
			browse_dialog.file_mode = FileDialog.FILE_MODE_OPEN_DIR
		PortDef.TYPE_TEXT:
			browse_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
			browse_dialog.clear_filters()
			browse_dialog.add_filter("*.md", "Markdown")
			browse_dialog.add_filter("*.txt", "Text")
			browse_dialog.add_filter("*.*", "All")
		PortDef.TYPE_AUDIO:
			browse_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
			browse_dialog.clear_filters()
			browse_dialog.add_filter("*.wav", "WAV")
			browse_dialog.add_filter("*.mp3", "MP3")
			browse_dialog.add_filter("*.ogg", "OGG")
			browse_dialog.add_filter("*.flac", "FLAC")
			browse_dialog.add_filter("*.*", "All")
		PortDef.TYPE_IMAGE:
			browse_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
			browse_dialog.clear_filters()
			browse_dialog.add_filter("*.png", "PNG")
			browse_dialog.add_filter("*.jpg", "JPEG")
			browse_dialog.add_filter("*.webp", "WebP")
			browse_dialog.add_filter("*.*", "All")
		PortDef.TYPE_VIDEO:
			browse_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
			browse_dialog.clear_filters()
			browse_dialog.add_filter("*.mp4", "MP4")
			browse_dialog.add_filter("*.mkv", "MKV")
			browse_dialog.add_filter("*.mov", "MOV")
			browse_dialog.add_filter("*.webm", "WebM")
			browse_dialog.add_filter("*.*", "All")
		_:
			browse_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
			browse_dialog.clear_filters()
			browse_dialog.add_filter("*.*", "All")

	browse_dialog.popup_centered()
	pass


func on_browse_selected(path: String) -> void:
	var port_id := str(browse_dialog.get_meta("port_id", ""))
	if port_id.is_empty() or not input_fields.has(port_id):
		return
	var field: LineEdit = input_fields[port_id]
	field.text = path.replace("\\", "/")
	pass
