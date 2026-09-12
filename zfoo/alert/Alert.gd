## Floating toast on `gdf_layer`: colored rounded label, horizontally centered, drifts downward, then auto-dismisses.
class_name Alert
extends Label

const default_font_size: int = 32
const default_corner_radius: int = 12
const default_speed: float = 50
const default_wait_time: int = 2700

func _process(delta):
	position.y = position.y + default_speed * delta
	pass


static func create_alert_label(i18n_text: String, color: Color) -> Label:
	var alertLabel: Label = Label.new()
	alertLabel.horizontal_alignment = HorizontalAlignment.HORIZONTAL_ALIGNMENT_CENTER
	alertLabel.vertical_alignment = VerticalAlignment.VERTICAL_ALIGNMENT_CENTER
	alertLabel.text = i18n_text
	alertLabel.add_theme_font_size_override("font_size", default_font_size)
	
	var styleBox: StyleBoxFlat = StyleBoxFlat.new()
	styleBox.bg_color = color
	styleBox.set_corner_radius_all(default_corner_radius)
	# Padding keeps text off the rounded edges.
	styleBox.content_margin_top = 8
	styleBox.content_margin_bottom = 8
	styleBox.content_margin_left = 16
	styleBox.content_margin_right = 16
	alertLabel.add_theme_stylebox_override("normal", styleBox)
	alertLabel.z_index = 1024
	
	alertLabel.set_script(Alert)
	return alertLabel

####################################################################################################
# Alert

## Show a toast for `default_wait_time` ms. Example: `Alert.alert("Saved", Colors.success)`
static func alert(txt: String, color: Color) -> void:
	var alertLabel = create_alert_label(txt, color)
	gdf.gdf_layer.add_child(alertLabel)
	
	# Wait one frame so font/theme metrics and StyleBox padding are resolved before sizing.
	await alertLabel.get_tree().process_frame
	var label_size := alertLabel.get_combined_minimum_size()
	alertLabel.size = label_size
	var viewport_size := alertLabel.get_viewport().get_visible_rect().size
	# Top-left anchor: center by offset, not pivot (early reset_size underestimates width and drifts right).
	alertLabel.position.x = (viewport_size.x - label_size.x) / 2
	
	await ThreadUtils.async_sleep(default_wait_time)
	alertLabel.queue_free()
	pass
