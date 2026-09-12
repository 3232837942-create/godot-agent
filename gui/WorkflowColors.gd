class_name WorkflowColors
extends RefCounted

## Skills workflow UI colors (gui/ only — do not add to zfoo/theme/Colors).

# Graph
static var canvas := Color(0.09, 0.10, 0.12)
static var node_bg := Color(0.13, 0.14, 0.17, 0.97)
static var node_running_bg := Color(0.12, 0.22, 0.14, 0.98)
static var node_border := Color(0.35, 0.37, 0.42)
static var node_title := Color(0.92, 0.93, 0.95)
static var hint := Color(0.58, 0.60, 0.64)

# Ports (GraphEdit slot handles)
static var port_audio := Color(0.95, 0.55, 0.2)
static var port_image := Color(0.3, 0.85, 0.45)
static var port_video := Color(0.65, 0.45, 0.95)
static var port_text := Color(0.95, 0.85, 0.25)
static var port_folder := Color(0.35, 0.65, 0.95)
static var port_default := Color(0.7, 0.7, 0.7)
static var port_slot_idle := Color.WHITE

# Toolbar & pipeline feedback
static var success := Color("#4CAF50")
static var error := Color("#B00020")
static var warning := Color("#FB8C00")
static var button_text := Color.WHITE


static func port_color(port_type: int) -> Color:
	match port_type:
		PortDef.TYPE_AUDIO:
			return port_audio
		PortDef.TYPE_IMAGE:
			return port_image
		PortDef.TYPE_VIDEO:
			return port_video
		PortDef.TYPE_TEXT:
			return port_text
		PortDef.TYPE_FOLDER:
			return port_folder
		_:
			return port_default
