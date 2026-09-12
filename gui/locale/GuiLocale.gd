class_name GuiLocale
extends RefCounted

const LOCALE_DIR := "res://gui/locale/"
const LOCALE_ZH := "zh-CN"
const LOCALE_EN := "en-US"

static var current_locale: String = LOCALE_EN
static var strings: Dictionary = {}


static func _static_init() -> void:
	load_locale(LOCALE_EN)
	pass


static func load_locale(locale: String) -> void:
	var path := LOCALE_DIR + locale + ".json"
	var text := FileAccess.get_file_as_string(path)
	if text.is_empty():
		Log.error("gui locale missing or empty:[{}]", path)
		return

	var parsed: Variant = JSON.parse_string(text)
	if parsed == null or not parsed is Dictionary:
		Log.error("gui locale json parse failed:[{}]", path)
		return

	strings = parsed as Dictionary
	current_locale = locale
	pass


static func text(key: String, ...args: Array) -> String:
	var resolved := resolve(key)
	if args.is_empty():
		return resolved
	return resolved.format(args, StringUtils.EMPTY_JSON)


static func resolve(key: String, fallback: String = "") -> String:
	var parts := key.split(".")
	var current: Variant = strings
	for part in parts:
		if current is Dictionary and current.has(part):
			current = current[part]
		else:
			if not fallback.is_empty():
				return fallback
			return key
	if current is String:
		return current
	if not fallback.is_empty():
		return fallback
	return key


static func category_label(category_id: String) -> String:
	return resolve("category." + category_id, category_id)


static func node_label(catalog_id: String) -> String:
	if current_locale == LOCALE_EN:
		return catalog_id
	return resolve("node." + catalog_id, catalog_id)


static func node_port_label(catalog_id: String, port_id: String, port_type: String = "") -> String:
	var node_port_key := "node_port." + catalog_id + "." + port_id
	var text := resolve(node_port_key, "")
	if text != node_port_key:
		return text

	var port_key := "port." + port_id
	text = resolve(port_key, "")
	if text != port_key:
		return text

	if not port_type.is_empty():
		return port_type_label(port_type)
	return port_id


static func port_type_label(type_name: String) -> String:
	return resolve("port_type." + type_name, type_name)
